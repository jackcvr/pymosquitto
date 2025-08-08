import ctypes as C
import atexit
import weakref
import typing as t

from .bindings import (
    lib,
    CONNECT_CALLBACK,
    DISCONNECT_CALLBACK,
    SUBSCRIBE_CALLBACK,
    UNSUBSCRIBE_CALLBACK,
    MESSAGE_CALLBACK,
    PUBLISH_CALLBACK,
)


class MosquittoError(RuntimeError):
    def __init__(self, func, code):
        self.func = func
        self.code = code

    def __str__(self):
        return f"{self.func.__name__} failed: {self.code}, {strerror(self.code)}"


class MQTTMessage(t.NamedTuple):
    mid: int
    topic: str
    payload: bytes
    qos: int = 0
    retain: bool = False

    @classmethod
    def from_cmessage(cls, cmsg):
        contents = cmsg.contents
        return cls(
            mid=contents.mid,
            topic=C.string_at(contents.topic).decode(),
            payload=C.string_at(contents.payload, contents.payloadlen),
            qos=contents.qos,
            retain=contents.retain,
        )


def strerror(rc):
    return C.c_char_p(lib.mosquitto_strerror(rc)).value.decode()


def connack_string(rc):
    return C.c_char_p(lib.mosquitto_connack_string(rc)).value.decode()


def to_python(obj):
    return C.cast(obj, C.py_object).value


def lib_run(func, *args):
    rc = func(*args)
    if rc is not None and rc != 0:
        raise MosquittoError(func, rc)


C.set_errno(0)
lib_run(lib.mosquitto_lib_init)
atexit.register(lib.mosquitto_lib_cleanup)


class Mosquitto:
    def __init__(self, client_id=None, clean_start=True, userdata=None):
        if client_id:
            client_id = client_id.encode()
        self._mosq = lib.mosquitto_new(client_id, clean_start, userdata)
        if not self._mosq:
            raise MosquittoError(lib.mosquitto_new, C.get_errno())
        self._finalizer = weakref.finalize(
            self, lib_run, lib.mosquitto_destroy, self._mosq
        )
        self.__connect_callback = None
        self.__disconnect_callback = None
        self.__subscribe_callback = None
        self.__unsubscribe_callback = None
        self.__publish_callback = None
        self.__message_callback = None

    def _run(self, lib_func, *args):
        lib_run(lib_func, self._mosq, *args)

    def destroy(self):
        if self._finalizer.alive:
            self._finalizer()

    def connect(self, host, port=1883, keepalive=60):
        self._run(lib.mosquitto_connect, host.encode(), port, keepalive)

    def connect_async(self, host, port=1883, keepalive=60):
        self._run(lib.mosquitto_connect_async, host.encode(), port, keepalive)

    def disconnect(self):
        self._run(lib.mosquitto_disconnect)

    def loop_start(self):
        self._run(lib.mosquitto_loop_start)

    def loop_stop(self, force=False):
        self._run(lib.mosquitto_loop_stop, force)

    def loop_forever(self, timeout=-1, max_packets=1):
        self._run(lib.mosquitto_loop_forever, timeout, max_packets)

    def subscribe(self, topic, qos=0):
        c_mid = C.c_int(0)
        self._run(lib.mosquitto_subscribe, C.byref(c_mid), topic.encode(), qos)
        return c_mid.value

    def publish(self, topic, payload, qos=0, retain=False):
        c_mid = C.c_int(0)
        self._run(
            lib.mosquitto_publish,
            C.byref(c_mid),
            topic.encode(),
            len(payload),
            C.c_char_p(payload.encode()),
            qos,
            retain,
        )
        return c_mid.value

    def connect_callback_set(self, callback):
        self.__connect_callback = CONNECT_CALLBACK(callback)
        self._run(lib.mosquitto_connect_callback_set, self.__connect_callback)

    def disconnect_callback_set(self, callback):
        self.__disconnect_callback = DISCONNECT_CALLBACK(callback)
        self._run(lib.mosquitto_disconnect_callback_set, self.__disconnect_callback)

    def subscribe_callback_set(self, callback):
        self.__subscribe_callback = SUBSCRIBE_CALLBACK(callback)
        self._run(lib.mosquitto_subscribe_callback_set, self.__subscribe_callback)

    def unsubscribe_callback_set(self, callback):
        self.__unsubscribe_callback = UNSUBSCRIBE_CALLBACK(callback)
        self._run(lib.mosquitto_unsubscribe_callback_set, self.__unsubscribe_callback)

    def publish_callback_set(self, callback):
        self.__publish_callback = PUBLISH_CALLBACK(callback)
        self._run(lib.mosquitto_publish_callback_set, self.__publish_callback)

    def message_callback_set(self, callback):
        self.__message_callback = MESSAGE_CALLBACK(callback)
        self._run(lib.mosquitto_message_callback_set, self.__message_callback)
