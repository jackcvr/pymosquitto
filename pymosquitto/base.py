import ctypes as C
import atexit
import weakref
import os

from .bindings import (
    libmosq,
    CONNECT_CALLBACK,
    DISCONNECT_CALLBACK,
    SUBSCRIBE_CALLBACK,
    UNSUBSCRIBE_CALLBACK,
    MESSAGE_CALLBACK,
    PUBLISH_CALLBACK,
    LOG_CALLBACK,
    strerror,
    call,
)
from .constants import ErrorCode


class AutoOSError(Exception):
    def __new__(cls, code):
        return OSError(code, os.strerror(code))


class MosquittoError(Exception):
    def __init__(self, func, code):
        self.func_name = func.__name__
        self.code = code

    def __str__(self):
        return f"{self.func_name} failed: {self.code}, {strerror(self.code)}"


_libmosq_inited = False


class Mosquitto:
    def __init__(self, client_id=None, clean_start=True, userdata=None):
        global _libmosq_inited

        if not _libmosq_inited:
            libmosq.mosquitto_lib_init()
            atexit.register(libmosq.mosquitto_lib_cleanup)
            _libmosq_inited = True

        if client_id:
            client_id = client_id.encode()
        self._userdata = userdata
        self._c_mosq_p, err = call(
            libmosq.mosquitto_new, client_id, clean_start, self._userdata
        )
        if err != 0:
            raise AutoOSError(err)
        self._finalizer = weakref.finalize(
            self, libmosq.mosquitto_destroy, self._c_mosq_p
        )
        self.__connect_callback = None
        self.__disconnect_callback = None
        self.__subscribe_callback = None
        self.__unsubscribe_callback = None
        self.__publish_callback = None
        self.__message_callback = None
        self.__log_callback = None

    @property
    def userdata(self):
        return self._userdata

    def _call(self, func, *args, use_errno=False):
        if use_errno:
            ret, err = call(func, self._c_mosq_p, *args)
            if ret == ErrorCode.ERRNO:
                raise AutoOSError(err)
        else:
            ret = func(self._c_mosq_p, *args)
        if ret == 0:
            return ret
        elif isinstance(ret, int):
            raise MosquittoError(func, ret)
        return ret

    def destroy(self):
        if self._finalizer.alive:
            self._finalizer()

    def username_pw_set(self, username=None, password=None):
        if username is not None:
            username = username.encode()
        if password is not None:
            password = password.encode()
        self._call(libmosq.mosquitto_username_pw_set, username, password)

    def connect(self, host, port=1883, keepalive=60):
        self._call(
            libmosq.mosquitto_connect, host.encode(), port, keepalive, use_errno=True
        )

    def connect_async(self, host, port=1883, keepalive=60):
        self._call(
            libmosq.mosquitto_connect_async,
            host.encode(),
            port,
            keepalive,
            use_errno=True,
        )

    def reconnect_async(self):
        self._call(libmosq.mosquitto_reconnect_async, use_errno=True)

    def reconnect_delay_set(
        self, reconnect_delay, reconnect_delay_max, reconnect_exponential_backoff=False
    ):
        self._call(
            libmosq.mosquitto_reconnect_delay_set,
            reconnect_delay,
            reconnect_delay_max,
            reconnect_exponential_backoff,
        )

    def disconnect(self):
        self._call(libmosq.mosquitto_disconnect)

    def loop_start(self):
        self._call(libmosq.mosquitto_loop_start)

    def loop_stop(self, force=False):
        self._call(libmosq.mosquitto_loop_stop, force)

    def loop_forever(self, timeout=-1):
        self._call(libmosq.mosquitto_loop_forever, timeout, 1)

    def subscribe(self, topic, qos=0):
        mid = C.c_int(0)
        self._call(libmosq.mosquitto_subscribe, C.byref(mid), topic.encode(), qos)
        return mid.value

    def unsubscribe(self, topic):
        mid = C.c_int(0)
        self._call(libmosq.mosquitto_unsubscribe, C.byref(mid), topic.encode())
        return mid.value

    def publish(self, topic, payload, qos=0, retain=False):
        mid = C.c_int(0)
        if isinstance(payload, str):
            payload = payload.encode()
        self._call(
            libmosq.mosquitto_publish,
            C.byref(mid),
            topic.encode(),
            len(payload),
            C.c_char_p(payload),
            qos,
            retain,
        )
        return mid.value

    def connect_callback_set(self, callback):
        self.__connect_callback = CONNECT_CALLBACK(callback)
        self._call(libmosq.mosquitto_connect_callback_set, self.__connect_callback)

    def disconnect_callback_set(self, callback):
        self.__disconnect_callback = DISCONNECT_CALLBACK(callback)
        self._call(
            libmosq.mosquitto_disconnect_callback_set, self.__disconnect_callback
        )

    def subscribe_callback_set(self, callback):
        self.__subscribe_callback = SUBSCRIBE_CALLBACK(callback)
        self._call(libmosq.mosquitto_subscribe_callback_set, self.__subscribe_callback)

    def unsubscribe_callback_set(self, callback):
        self.__unsubscribe_callback = UNSUBSCRIBE_CALLBACK(callback)
        self._call(
            libmosq.mosquitto_unsubscribe_callback_set, self.__unsubscribe_callback
        )

    def publish_callback_set(self, callback):
        self.__publish_callback = PUBLISH_CALLBACK(callback)
        self._call(libmosq.mosquitto_publish_callback_set, self.__publish_callback)

    def message_callback_set(self, callback):
        self.__message_callback = MESSAGE_CALLBACK(callback)
        self._call(libmosq.mosquitto_message_callback_set, self.__message_callback)

    def log_callback_set(self, callback):
        self.__log_callback = LOG_CALLBACK(callback)
        self._call(libmosq.mosquitto_log_callback_set, self.__log_callback)
