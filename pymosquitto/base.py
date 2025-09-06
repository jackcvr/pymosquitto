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
)


_libmosq_inited = False


def callback_setter(lib_func, deco):
    cb_name = lib_func.__name__[10:-4]  # trim mosquitto_ and _set

    def setter(self, func):
        if func:
            func = deco(func)
            setattr(self, f"__{cb_name}", func)
        else:
            func = deco(lambda *_: None)
        lib_func(self._c_mosq_p, func)

    setter.__name__ = f"{cb_name}_setter"
    return setter


class Mosquitto:
    def __init__(self, client_id=None, clean_start=True, userdata=None):
        global _libmosq_inited

        if not _libmosq_inited:
            libmosq.mosquitto_lib_init()
            atexit.register(libmosq.mosquitto_lib_cleanup)
            _libmosq_inited = True

        if client_id is not None:
            client_id = client_id.encode()
        self._userdata = userdata
        self._c_mosq_p = call(
            libmosq.mosquitto_new,
            client_id,
            clean_start,
            self._userdata,
            use_errno=True,
        )
        self._finalizer = weakref.finalize(
            self, libmosq.mosquitto_destroy, self._c_mosq_p
        )

    connect_callback_set = callback_setter(
        libmosq.mosquitto_connect_callback_set, CONNECT_CALLBACK
    )
    disconnect_callback_set = callback_setter(
        libmosq.mosquitto_disconnect_callback_set, DISCONNECT_CALLBACK
    )
    subscribe_callback_set = callback_setter(
        libmosq.mosquitto_subscribe_callback_set, SUBSCRIBE_CALLBACK
    )
    unsubscribe_callback_set = callback_setter(
        libmosq.mosquitto_unsubscribe_callback_set, UNSUBSCRIBE_CALLBACK
    )
    publish_callback_set = callback_setter(
        libmosq.mosquitto_publish_callback_set, PUBLISH_CALLBACK
    )
    message_callback_set = callback_setter(
        libmosq.mosquitto_message_callback_set, MESSAGE_CALLBACK
    )
    log_callback_set = callback_setter(libmosq.mosquitto_log_callback_set, LOG_CALLBACK)

    @property
    def userdata(self):
        return self._userdata

    def _call(self, func, *args, use_errno=False):
        return mosq_call(func, self._c_mosq_p, *args, use_errno=use_errno)

    def destroy(self):
        if self._finalizer.alive:
            self._finalizer()

    def socket(self):
        fd = call(libmosq.mosquitto_socket, self._c_mosq_p)
        if fd == -1:
            return None
        return fd

    def want_write(self):
        return call(libmosq.mosquitto_want_write, self._c_mosq_p)

    def loop_read(self):
        return mosq_call(libmosq.mosquitto_loop_read, self._c_mosq_p, 1, use_errno=True)

    def loop_write(self):
        return mosq_call(
            libmosq.mosquitto_loop_write, self._c_mosq_p, 1, use_errno=True
        )

    def loop_misc(self):
        return self._call(libmosq.mosquitto_loop_misc)

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

    def subscribe(self, topic, qos=0):
        mid = C.c_int(0)
        self._call(libmosq.mosquitto_subscribe, C.byref(mid), topic.encode(), qos)
        return mid.value

    def unsubscribe(self, topic):
        mid = C.c_int(0)
        self._call(libmosq.mosquitto_unsubscribe, C.byref(mid), topic.encode())
        return mid.value


def topic_matches_sub(sub, topic):
    res = C.c_bool(False)
    call(
        libmosq.mosquitto_topic_matches_sub, sub.encode(), topic.encode(), C.byref(res)
    )
    return res.value
