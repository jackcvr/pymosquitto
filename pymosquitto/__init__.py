import ctypes as C
from ctypes.util import find_library
import atexit
import weakref
import threading
import logging
import typing as t

lib = C.cdll.LoadLibrary(find_library("mosquitto"))
lib.mosquitto_new.use_errno = True  # type: ignore[attr-defined]
lib.mosquitto_new.restype = C.c_void_p
lib.mosquitto_strerror.restype = C.c_char_p
lib.mosquitto_connack_string.restype = C.c_char_p

CONNECT_FUNC = C.CFUNCTYPE(None, C.c_void_p, C.c_void_p, C.c_int)
lib.mosquitto_connect_callback_set.argtypes = (C.c_void_p, CONNECT_FUNC)

DISCONNECT_FUNC = C.CFUNCTYPE(None, C.c_void_p, C.c_void_p, C.c_int)
lib.mosquitto_disconnect_callback_set.argtypes = (C.c_void_p, DISCONNECT_FUNC)


class MQTTMessage(t.NamedTuple):
    mid: int
    topic: str
    payload: bytes
    qos: int
    retain: bool


class MosqMessage(C.Structure):
    _fields_ = (
        ("mid", C.c_int),
        ("topic", C.c_char_p),
        ("payload", C.c_void_p),
        ("payloadlen", C.c_int),
        ("qos", C.c_int),
        ("retain", C.c_bool),
    )

    def as_mqtt_message(self):
        return MQTTMessage(
            mid=self.mid,
            topic=C.string_at(self.topic).decode(),
            payload=C.string_at(self.payload, self.payloadlen),
            qos=self.qos,
            retain=self.retain,
        )


MESSAGE_FUNC = C.CFUNCTYPE(None, C.c_void_p, C.c_void_p, C.POINTER(MosqMessage))
lib.mosquitto_message_callback_set.argtypes = (C.c_void_p, MESSAGE_FUNC)

PUBLISH_FUNC = C.CFUNCTYPE(None, C.c_void_p, C.c_void_p, C.c_int)
lib.mosquitto_publish_callback_set.argtypes = (C.c_void_p, PUBLISH_FUNC)


def strerror(rc):
    return C.c_char_p(lib.mosquitto_strerror(rc)).value.decode()


def connack_string(rc):
    return C.c_char_p(lib.mosquitto_connack_string(rc)).value.decode()


C.set_errno(0)
lib.mosquitto_lib_init()
atexit.register(lib.mosquitto_lib_cleanup)

_instances: weakref.WeakValueDictionary[C.c_void_p, "MQTTClient"] = (
    weakref.WeakValueDictionary()
)


@CONNECT_FUNC
def _on_connect(mosq, _, reason):
    client = _instances[mosq]
    reason_msg = connack_string(reason)
    if reason != 0:
        client.logger.warning("Connection failed: %s", reason_msg)
        return
    with client.cond:
        client.is_connected = True
        client.logger.info("Connected: %s", reason_msg)
        client.cond.notify_all()
    client.on_connect(reason)


@DISCONNECT_FUNC
def _on_disconnect(mosq, _, reason):
    client = _instances[mosq]
    with client.cond:
        client.is_connected = False
        if reason == 0:
            client.logger.info("Disconnected")
        else:
            client.logger.warning("Disconnected: %s", connack_string(reason))
        client.cond.notify_all()
    client.on_disconnect(reason)


@MESSAGE_FUNC
def _on_message(mosq, _, msg):
    client = _instances[mosq]
    msg = msg.contents.as_mqtt_message()
    client.logger.debug("RECV: %s", msg)
    client.on_message(msg)


@PUBLISH_FUNC
def _on_publish(mosq, _, mid):
    if mosq not in _instances:
        return
    client = _instances[mosq]
    client.logger.debug("PUB_DONE [mid=%d]", mid)
    client.on_publish(mid)


class CLibError(RuntimeError):
    pass


class MQTTClient:
    DEFAULT_PORT = 1883
    DEFAULT_KEEPALIVE = 60

    def __init__(self, client_id=None, logger=None):
        if client_id:
            client_id = client_id.encode()
        self._mosq = lib.mosquitto_new(client_id, True, None)
        if not self._mosq:
            rc = C.get_errno()
            raise RuntimeError(f"Failed to create Mosquitto instance: {strerror(rc)}")
        self.logger = logger or logging.getLogger()
        self.topics = {}
        self.handlers = None
        self.is_connected = False
        self.cond = threading.Condition(threading.Lock())
        self._in_thread = False
        self._set_callbacks()
        _instances[self._mosq] = self

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def __del__(self):
        self.close()

    def run(self, func, *args):
        rc = func(self._mosq, *args)
        if rc != 0:
            msg = strerror(rc)
            raise CLibError(f"{func.__name__} failed with error: {rc}/{msg}")

    def _set_callbacks(self):
        self.run(lib.mosquitto_connect_callback_set, _on_connect)
        self.run(lib.mosquitto_disconnect_callback_set, _on_disconnect)
        self.run(lib.mosquitto_message_callback_set, _on_message)
        self.run(lib.mosquitto_publish_callback_set, _on_publish)

    def connect(self, host, port=DEFAULT_PORT, keepalive=DEFAULT_KEEPALIVE):
        self.run(lib.mosquitto_connect, host.encode(), port, keepalive)

    def connect_async(self, host, port=DEFAULT_PORT, keepalive=DEFAULT_KEEPALIVE):
        self.run(lib.mosquitto_connect_async, host.encode(), port, keepalive)

    def wait_connection(self, timeout=None):
        with self.cond:
            self.cond.wait_for(lambda: self.is_connected, timeout=timeout)

    def subscribe(self, topic, qos=0):
        with self.cond:
            self.topics[topic] = qos
            if self.is_connected:
                self.run(lib.mosquitto_subscribe, None, topic.encode(), qos)
                self.logger.info("SUB/%d %s", qos, topic)

    def loop_start(self):
        with self.cond:
            self.run(lib.mosquitto_loop_start)
            self._in_thread = True

    def loop_forever(self):
        self.run(lib.mosquitto_loop_forever, -1, 1)

    def close(self):
        with self.cond:
            if not self._mosq:
                return
            if self.is_connected:
                self.run(lib.mosquitto_disconnect)
                self.cond.wait_for(lambda: not self.is_connected, timeout=1)
            if self._in_thread:
                self.run(lib.mosquitto_loop_stop, True)
            self.run(lib.mosquitto_destroy)
            self._mosq = None

    def publish(self, topic, payload, qos=0):
        c_mid = C.c_int(0)
        self.run(
            lib.mosquitto_publish,
            C.byref(c_mid),
            topic.encode(),
            len(payload),
            C.c_char_p(payload.encode()),
            qos,
            False,
        )
        self.logger.debug(
            "PUB_SENT[mid=%d qos=%d] %s: %s", c_mid.value, qos, topic, payload
        )
        return c_mid.value

    def add_topic_handler(self, topic, func):
        if self.handlers is None:
            from .utils import TopicMatcher

            self.handlers = TopicMatcher()
        self.handlers[topic] = func

    def topic_handler(self, topic):
        def decorator(func):
            self.add_topic_handler(topic, func)
            return func

        return decorator

    def remove_topic_handler(self, topic):
        del self.handlers[topic]

    def on_connect(self, rc):
        for topic, qos in self.topics.items():
            self.subscribe(topic, qos)

    def on_disconnect(self, rc):
        pass

    def on_publish(self, mid):
        pass

    def on_message(self, msg):
        if not self.handlers:
            return
        for handler in self.handlers.find(msg.topic):
            try:
                handler(self, msg)
            except Exception as e:
                self.logger.exception(e)
