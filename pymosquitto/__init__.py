import ctypes as C
import atexit
import weakref
import threading
import logging
import typing as t

lib = C.cdll.LoadLibrary("libmosquitto.so")
lib.mosquitto_new.use_errno = True  # type: ignore[attr-defined]
lib.mosquitto_new.restype = C.c_void_p
lib.mosquitto_strerror.restype = C.c_char_p
lib.mosquitto_connack_string.restype = C.c_char_p

CONNECT_CB = C.CFUNCTYPE(None, C.c_void_p, C.c_void_p, C.c_int)
lib.mosquitto_connect_callback_set.argtypes = (C.c_void_p, CONNECT_CB)

DISCONNECT_CB = C.CFUNCTYPE(None, C.c_void_p, C.c_void_p, C.c_int)
lib.mosquitto_disconnect_callback_set.argtypes = (C.c_void_p, DISCONNECT_CB)


class Message(t.NamedTuple):
    mid: int
    topic: str
    payload: bytes
    qos: int = 0
    retain: bool = False


class MosqMessage(C.Structure):
    _fields_ = (
        ("mid", C.c_int),
        ("topic", C.c_char_p),
        ("payload", C.c_void_p),
        ("payloadlen", C.c_int),
        ("qos", C.c_int),
        ("retain", C.c_bool),
    )

    def as_tuple(self):
        return Message(
            mid=self.mid,
            topic=C.string_at(self.topic).decode(),
            payload=C.string_at(self.payload, self.payloadlen),
            qos=self.qos,
            retain=self.retain,
        )


MESSAGE_CB = C.CFUNCTYPE(None, C.c_void_p, C.c_void_p, C.POINTER(MosqMessage))
lib.mosquitto_message_callback_set.argtypes = (C.c_void_p, MESSAGE_CB)

PUBLISH_CB = C.CFUNCTYPE(None, C.c_void_p, C.c_void_p, C.c_int)
lib.mosquitto_publish_callback_set.argtypes = (C.c_void_p, PUBLISH_CB)


def strerror(rc):
    return C.c_char_p(lib.mosquitto_strerror(rc)).value.decode()


def connack_string(rc):
    return C.c_char_p(lib.mosquitto_connack_string(rc)).value.decode()


C.set_errno(0)
lib.mosquitto_lib_init()
atexit.register(lib.mosquitto_lib_cleanup)

_clients: weakref.WeakValueDictionary[C.c_void_p, "MQTTClient"] = (
    weakref.WeakValueDictionary()
)


@CONNECT_CB
def _on_connect(mosq, _, reason):
    client = _clients[mosq]
    reason_msg = connack_string(reason)
    if reason != 0:
        client.logger.warning("Connection failed: %s", reason_msg)
        return
    with client.cond:
        client.is_connected = True
        client.logger.info("Connected: %s", reason_msg)
        client.cond.notify_all()
    for topic, qos in client.topics.items():
        client.subscribe(topic, qos)
    client.on_connect(reason)


@DISCONNECT_CB
def _on_disconnect(mosq, _, reason):
    client = _clients[mosq]
    with client.cond:
        client.is_connected = False
        if reason == 0:
            client.logger.info("Disconnected")
        else:
            client.logger.warning("Disconnected: %s", connack_string(reason))
        client.cond.notify_all()
    client.on_disconnect(reason)


@MESSAGE_CB
def _on_message(mosq, _, msg):
    client = _clients[mosq]
    msg = msg.contents.as_tuple()
    client.logger.debug("RECV: %s", msg)
    client.on_message(msg)


@PUBLISH_CB
def _on_publish(mosq, _, mid):
    if mosq not in _clients:
        return
    client = _clients[mosq]
    client.logger.debug("PUB: %d", mid)
    client.on_publish(mid)


class MQTTClient:
    def __init__(self, client_id=None, logger=None):
        if client_id:
            client_id = client_id.encode()
        self._mosq = lib.mosquitto_new(client_id, True, None)
        if not self._mosq:
            raise RuntimeError(f"Failed to create Mosquitto client: {C.get_errno()}")
        self.logger = logger or logging.getLogger()
        self.topics = {}
        self.cond = threading.Condition(threading.Lock())
        self.is_connected = False
        self._in_thread = False
        self.run(lib.mosquitto_connect_callback_set, _on_connect)
        self.run(lib.mosquitto_disconnect_callback_set, _on_disconnect)
        self.run(lib.mosquitto_message_callback_set, _on_message)
        self.run(lib.mosquitto_publish_callback_set, _on_publish)
        _clients[self._mosq] = self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def run(self, func, *args):
        rc = func(self._mosq, *args)
        if rc != 0:
            msg = strerror(rc)
            raise RuntimeError(f"{func.__name__} failed with error: {rc}/{msg}")

    def connect(self, host, port=1883, keepalive=60):
        self.run(lib.mosquitto_connect, host.encode(), port, keepalive)

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

    def stop(self):
        with self.cond:
            if self.is_connected:
                self.run(lib.mosquitto_disconnect)
                self.cond.wait_for(lambda: not self.is_connected, timeout=1)
            if self._in_thread:
                self.run(lib.mosquitto_loop_stop, True)
            self.run(lib.mosquitto_destroy)

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
        self.logger.debug("PUB/%d %s: %s", qos, topic, payload)
        return c_mid.value

    def on_connect(self, rc):
        pass

    def on_disconnect(self, rc):
        pass

    def on_publish(self, mid):
        pass

    def on_message(self, msg):
        pass
