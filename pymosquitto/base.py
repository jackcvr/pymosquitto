import ctypes as C
import atexit
import weakref

from .bindings import (
    libmosq,
    call,
    mosq_call,
    CONNECT_CALLBACK,
    DISCONNECT_CALLBACK,
    SUBSCRIBE_CALLBACK,
    UNSUBSCRIBE_CALLBACK,
    PUBLISH_CALLBACK,
    MESSAGE_CALLBACK,
    LOG_CALLBACK,
    MQTTMessage,
)
from .constants import LogLevel

_libmosq_inited = False


class Callback:
    def __init__(self, deco):
        self._deco = deco
        self._lib_func = None
        self._func = None
        self._callback = None

    def __set_name__(self, owner, name):
        if not name.startswith("on_"):
            raise ValueError("Callback names must start with 'on_'")
        self._lib_func = getattr(libmosq, f"mosquitto_{name[3:]}_callback_set")

    def __set__(self, obj, func):
        self._func = func
        if self._func is None:
            self._callback = self._deco(0)
        elif self._deco is MESSAGE_CALLBACK:

            def _adapter(_, userdata, msg):
                func(obj, userdata, MQTTMessage.from_struct(msg))

            self._callback = self._deco(_adapter)
        else:
            self._callback = self._deco(lambda _, *args: func(obj, *args))
        self._lib_func(obj.c_mosq_p, self._callback)

    def __get__(self, obj, objtype=None):
        return self._func


class Function:
    def __init__(self):
        self._lib_func = None

    def __set_name__(self, owner, name):
        self._lib_func = getattr(libmosq, f"mosquitto_{name}")

    def __get__(self, obj, objtype=None):
        def _call(*args):
            args = [arg.encode() if isinstance(arg, str) else arg for arg in args]
            return obj.call(self._lib_func, *args)

        return _call


class Mosquitto:
    def __init__(self, client_id=None, clean_start=True, userdata=None, logger=None):
        global _libmosq_inited

        if not _libmosq_inited:
            libmosq.mosquitto_lib_init()
            atexit.register(libmosq.mosquitto_lib_cleanup)
            _libmosq_inited = True

        if client_id is not None:
            client_id = client_id.encode()
        self._userdata = userdata
        self._logger = logger
        self._c_mosq_p = call(
            libmosq.mosquitto_new,
            client_id,
            clean_start,
            self._userdata,
            use_errno=True,
        )
        self._finalizer = weakref.finalize(self, self.finalize, self._c_mosq_p)
        self._set_default_callbacks()

    @property
    def c_mosq_p(self):
        return self._c_mosq_p

    @property
    def userdata(self):
        return self._userdata

    @staticmethod
    def finalize(c_mosq_p):
        call(libmosq.mosquitto_message_callback_set, c_mosq_p, MESSAGE_CALLBACK(0))
        call(libmosq.mosquitto_destroy, c_mosq_p)

    def destroy(self):
        if self._finalizer.alive:
            self._finalizer()

    def call(self, func, *args):
        if self._logger:
            self._logger.debug("CALL: %s%s", func.__name__, (self._c_mosq_p,) + args)
        return mosq_call(func, self._c_mosq_p, *args)

    def _set_default_callbacks(self):
        if self._logger:
            self.on_log = self._on_log

    def _on_log(self, mosq, userdata, level, msg):
        self._logger.debug("MOSQ/%s %s", LogLevel(level).name, msg.decode())

    on_connect = Callback(CONNECT_CALLBACK)
    on_disconnect = Callback(DISCONNECT_CALLBACK)
    on_subscribe = Callback(SUBSCRIBE_CALLBACK)
    on_unsubscribe = Callback(UNSUBSCRIBE_CALLBACK)
    on_publish = Callback(PUBLISH_CALLBACK)
    on_message = Callback(MESSAGE_CALLBACK)
    on_log = Callback(LOG_CALLBACK)

    will_set = Function()
    will_clear = Function()
    username_pw_set = Function()
    tls_set = Function()
    tls_insecure_set = Function()
    tls_opts_set = Function()
    tls_psk_set = Function()
    reconnect_async = Function()
    reconnect_delay_set = Function()
    disconnect = Function()
    loop_start = Function()
    loop_stop = Function()
    want_write = Function()
    threaded_set = Function()
    loop_read = Function()
    loop_write = Function()
    loop_misc = Function()

    def connect(self, host, port=1883, keepalive=60):
        return self.call(
            libmosq.mosquitto_connect,
            host.encode(),
            port,
            keepalive,
        )

    def connect_async(self, host, port=1883, keepalive=60):
        return self.call(
            libmosq.mosquitto_connect_async,
            host.encode(),
            port,
            keepalive,
        )

    def socket(self):
        fd = call(libmosq.mosquitto_socket, self._c_mosq_p)
        return None if fd == -1 else fd

    def loop_forever(self, timeout=-1):
        return self.call(libmosq.mosquitto_loop_forever, timeout, 1)

    def publish(self, topic, payload, qos=0, retain=False):
        mid = C.c_int(0)
        if isinstance(payload, str):
            payload = payload.encode()
        self.call(
            libmosq.mosquitto_publish,
            C.byref(mid),
            topic.encode(),
            len(payload),
            C.c_char_p(payload),
            qos,
            retain,
        )
        return mid.value

    def subscribe(self, topic, qos=0):
        mid = C.c_int(0)
        self.call(libmosq.mosquitto_subscribe, C.byref(mid), topic.encode(), qos)
        return mid.value

    def unsubscribe(self, topic):
        mid = C.c_int(0)
        self.call(libmosq.mosquitto_unsubscribe, C.byref(mid), topic.encode())
        return mid.value


def topic_matches_sub(sub, topic):
    res = C.c_bool(False)
    call(
        libmosq.mosquitto_topic_matches_sub, sub.encode(), topic.encode(), C.byref(res)
    )
    return res.value
