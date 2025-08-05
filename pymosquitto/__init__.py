import ctypes as C
from ctypes.util import find_library
import atexit
import threading
import logging
import typing as t


class CLibError(RuntimeError):
    pass


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


def strerror(rc):
    return C.c_char_p(lib.mosquitto_strerror(rc)).value.decode()


def connack_string(rc):
    return C.c_char_p(lib.mosquitto_connack_string(rc)).value.decode()


CONNECT_CALLBACK = C.CFUNCTYPE(None, C.c_void_p, C.c_void_p, C.c_int)
DISCONNECT_CALLBACK = C.CFUNCTYPE(None, C.c_void_p, C.c_void_p, C.c_int)
SUBSCRIBE_CALLBACK = C.CFUNCTYPE(
    None, C.c_void_p, C.c_void_p, C.c_int, C.c_int, C.POINTER(C.c_int)
)
UNSUBSCRIBE_CALLBACK = C.CFUNCTYPE(None, C.c_void_p, C.c_void_p, C.c_int)
MESSAGE_CALLBACK = C.CFUNCTYPE(None, C.c_void_p, C.c_void_p, C.POINTER(MosqMessage))
PUBLISH_CALLBACK = C.CFUNCTYPE(None, C.c_void_p, C.c_void_p, C.c_int)

lib = C.cdll.LoadLibrary(find_library("mosquitto"))
lib.mosquitto_new.use_errno = True  # type: ignore[attr-defined]
lib.mosquitto_new.restype = C.c_void_p
lib.mosquitto_strerror.restype = C.c_char_p
lib.mosquitto_connack_string.restype = C.c_char_p
lib.mosquitto_connect_callback_set.argtypes = (C.c_void_p, CONNECT_CALLBACK)
lib.mosquitto_disconnect_callback_set.argtypes = (C.c_void_p, DISCONNECT_CALLBACK)
lib.mosquitto_subscribe_callback_set.argtypes = (C.c_void_p, SUBSCRIBE_CALLBACK)
lib.mosquitto_unsubscribe_callback_set.argtypes = (C.c_void_p, UNSUBSCRIBE_CALLBACK)
lib.mosquitto_message_callback_set.argtypes = (C.c_void_p, MESSAGE_CALLBACK)
lib.mosquitto_publish_callback_set.argtypes = (C.c_void_p, PUBLISH_CALLBACK)

C.set_errno(0)
lib.mosquitto_lib_init()
atexit.register(lib.mosquitto_lib_cleanup)


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
        self._wrap_callbacks()
        self.run(lib.mosquitto_connect_callback_set, self._lib_on_connect)
        self.run(lib.mosquitto_disconnect_callback_set, self._lib_on_disconnect)
        self.run(lib.mosquitto_subscribe_callback_set, self._lib_on_subscribe)
        self.run(lib.mosquitto_unsubscribe_callback_set, self._lib_on_unsubscribe)
        self.run(lib.mosquitto_publish_callback_set, self._lib_on_publish)
        self.run(lib.mosquitto_message_callback_set, self._lib_on_message)

    def _wrap_callbacks(self):
        self._lib_on_connect = CONNECT_CALLBACK(self._lib_on_connect)
        self._lib_on_disconnect = DISCONNECT_CALLBACK(self._lib_on_disconnect)
        self._lib_on_subscribe = SUBSCRIBE_CALLBACK(self._lib_on_subscribe)
        self._lib_on_unsubscribe = UNSUBSCRIBE_CALLBACK(self._lib_on_unsubscribe)
        self._lib_on_publish = PUBLISH_CALLBACK(self._lib_on_publish)
        self._lib_on_message = MESSAGE_CALLBACK(self._lib_on_message)

    def connect(self, host, port=DEFAULT_PORT, keepalive=DEFAULT_KEEPALIVE):
        self.run(lib.mosquitto_connect, host.encode(), port, keepalive)

    def connect_async(self, host, port=DEFAULT_PORT, keepalive=DEFAULT_KEEPALIVE):
        self.run(lib.mosquitto_connect_async, host.encode(), port, keepalive)

    def wait_connection(self, timeout=None):
        with self.cond:
            self.cond.wait_for(lambda: self.is_connected, timeout=timeout)

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

    def subscribe(self, topic, qos=0):
        with self.cond:
            self.topics[topic] = qos
            if self.is_connected:
                self.run(lib.mosquitto_subscribe, None, topic.encode(), qos)
                self.logger.debug("SUB_SENT: (topic=%s qos=%d)", topic, qos)

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
            "PUB_SENT: (mid=%d topic=%s qos=%d payload=%s)",
            c_mid.value,
            topic,
            qos,
            payload,
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

    # -----------
    # CALLBACKS
    # -----------

    def _lib_on_connect(self, mosq, obj, rc):
        rc_desc = connack_string(rc)
        if rc != 0:
            self.logger.warning("Connection failed: %s", rc_desc)
            return
        with self.cond:
            self.is_connected = True
            self.logger.info("Connected: %s", rc_desc)
            self.cond.notify_all()
        self._on_connect(rc)

    def _on_connect(self, rc):
        for topic, qos in self.topics.items():
            self.subscribe(topic, qos)

    def _lib_on_disconnect(self, mosq, obj, rc):
        with self.cond:
            self.is_connected = False
            if rc == 0:
                self.logger.info("Disconnected")
            else:
                self.logger.warning("Disconnected: %s", connack_string(rc))
            self.cond.notify_all()
        self._on_disconnect(rc)

    def _on_disconnect(self, rc):
        pass

    def _lib_on_subscribe(self, mosq, obj, mid, qos_count, granted_qos):
        qos_list = [granted_qos[i] for i in range(qos_count)]
        self.logger.info("SUB: (mid=%d granted_qos=%s)", mid, qos_list)
        self._on_subscribe(mid, qos_list)

    def _on_subscribe(self, mid, qos_list):
        pass

    def _lib_on_unsubscribe(self, mosq, obj, mid):
        self.logger.debug("UNSUB: (mid=%d)", mid)
        self._on_unsubscribe(mid)

    def _on_unsubscribe(self, mid):
        pass

    def _lib_on_publish(self, mosq, obj, mid):
        self.logger.debug("PUB: (mid=%d)", mid)
        self._on_publish(mid)

    def _on_publish(self, mid):
        pass

    def _lib_on_message(self, mosq, obj, msg):
        msg = msg.contents.as_mqtt_message()
        self.logger.debug("RECV: %s", msg)
        self._on_message(msg)

    def _on_message(self, msg):
        if not self.handlers:
            return
        for handler in self.handlers.find(msg.topic):
            try:
                handler(self, msg)
            except Exception as e:
                self.logger.exception(e)
