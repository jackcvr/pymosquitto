import ctypes as C
import atexit
from dataclasses import dataclass
import typing as t

from .constants import LogLevel, LIBMOSQ_MIN_MAJOR_VERSION
from .bindings import bind, call, libmosq

__version = (C.c_int(), C.c_int(), C.c_int())
libmosq.mosquitto_lib_version(
    C.byref(__version[0]),
    C.byref(__version[1]),
    C.byref(__version[2]),
)
LIBMOSQ_VERSION = tuple([__version[i].value for i in range(3)])
del __version

if LIBMOSQ_VERSION[0] < LIBMOSQ_MIN_MAJOR_VERSION:
    raise RuntimeError(f"libmosquitto version {LIBMOSQ_MIN_MAJOR_VERSION}+ is required")

libmosq.mosquitto_lib_init()
atexit.register(libmosq.mosquitto_lib_cleanup)


class MQTTMessageStruct(C.Structure):
    _fields_ = (
        ("mid", C.c_int),
        ("topic", C.c_char_p),
        ("payload", C.c_void_p),
        ("payloadlen", C.c_int),
        ("qos", C.c_int),
        ("retain", C.c_bool),
    )


if t.TYPE_CHECKING:
    LP_MQTTMessageStruct: t.TypeAlias = type[C._Pointer[MQTTMessageStruct]]
else:
    LP_MQTTMessageStruct: t.TypeAlias = C.POINTER(MQTTMessageStruct)


@dataclass(frozen=True, slots=True)
class MQTTMessage:
    mid: int
    topic: str
    payload: bytes
    qos: int
    retain: bool

    @classmethod
    def from_struct(cls, msg: LP_MQTTMessageStruct) -> "MQTTMessage":
        cnt = t.cast(MQTTMessageStruct, msg.contents)
        return cls(
            cnt.mid,
            C.string_at(cnt.topic).decode(),
            C.string_at(cnt.payload, cnt.payloadlen),
            cnt.qos,
            cnt.retain,
        )


class Method:
    def __init__(
        self, restype, func, *argtypes, auto_encode=True, auto_decode=True, is_mosq=True
    ):
        self._func = bind(
            restype, func, *argtypes, auto_encode=auto_encode, auto_decode=auto_decode
        )
        self._is_mosq = is_mosq

    @property
    def func(self):
        return self._func

    def __get__(self, obj, objtype=None):
        self._obj = obj
        return self

    def __call__(self, *args):
        return self._obj.call(self._func, *args, is_mosq=self._is_mosq)


class Callback:
    def __init__(self, func, wrapper):
        self._func = bind(None, func, C.c_void_p, wrapper)
        self._wrapper = wrapper
        self._callback = None
        self._wrapped_callback = None

    def __set__(self, obj, callback):
        self._callback = callback
        if self._func.__name__ == libmosq.mosquitto_message_callback_set.__name__:

            def adapter(_, userdata, msg):
                callback(obj, userdata, MQTTMessage.from_struct(msg))

            self._wrapped_callback = self._wrapper(adapter)
        elif self._callback:
            self._wrapped_callback = self._wrapper(
                lambda _, *args: self._callback(obj, *args)
            )
        else:
            self._wrapped_callback = self._wrapper(self._callback or 0)
        obj.call(self._func, self._wrapped_callback)

    def __get__(self, obj, objtype=None):
        return self._callback


class Client:
    def __init__(self, client_id=None, clean_start=True, userdata=None, logger=None):
        if client_id is not None:
            client_id = client_id.encode()
        self._userdata = userdata
        self._logger = logger
        self._mosq_ptr = call(
            libmosq.mosquitto_new,
            client_id,
            clean_start,
            self._userdata,
            use_errno=True,
        )
        self._set_default_callbacks()

    @property
    def mosq_ptr(self):
        return self._mosq_ptr

    def __del__(self):
        self.user_data_set(None)
        self.destroy()

    def call(self, func, *args, **kwargs):
        if self._logger:
            self._logger.debug("CALL: %s%s", func.__name__, (self._mosq_ptr,) + args)
        return call(func, self._mosq_ptr, *args, **kwargs)

    def _set_default_callbacks(self):
        if self._logger:
            self.on_log = self._on_log

    def _on_log(self, mosq, userdata, level, msg):
        self._logger.debug("MOSQ/%s %s", LogLevel(level).name, msg.decode())

    # void mosquitto_destroy(struct mosquitto *mosq)
    destroy = Method(None, libmosq.mosquitto_destroy, C.c_void_p)

    # Will
    # int mosquitto_will_set(struct mosquitto *mosq, const char *topic, int payloadlen, const void *payload, int qos, bool retain)
    will_set = Method(
        C.c_int,
        libmosq.mosquitto_will_set,
        C.c_void_p,
        C.c_char_p,
        C.c_int,
        C.c_char_p,
        C.c_int,
        C.c_bool,
    )
    # int mosquitto_will_set_v5(struct mosquitto *mosq, const char *topic, int payloadlen, const void *payload, int qos, bool retain, const mosquitto_property *props)
    will_set_v5 = Method(
        C.c_int,
        libmosq.mosquitto_will_set_v5,
        C.c_void_p,
        C.c_char_p,
        C.c_int,
        C.c_char_p,
        C.c_int,
        C.c_bool,
        C.c_void_p,
    )
    # int mosquitto_will_clear(struct mosquitto *mosq)
    will_clear = Method(C.c_int, libmosq.mosquitto_will_clear, C.c_void_p)

    # Username and password
    # int mosquitto_username_pw_set(struct mosquitto *mosq, const char *username, const char *password)
    username_pw_set = Method(
        C.c_int, libmosq.mosquitto_username_pw_set, C.c_void_p, C.c_char_p, C.c_char_p
    )

    # Connecting, reconnecting, disconnecting
    # int mosquitto_connect(struct mosquitto *mosq, const char *host, int port, int keepalive)
    _connect = Method(
        C.c_int,
        libmosq.mosquitto_connect,
        C.c_void_p,
        C.c_char_p,
        C.c_int,
        C.c_int,
        auto_encode=False,
    )
    # int mosquitto_connect_bind(struct mosquitto *mosq, const char *host, int port, int keepalive, const char *bind_address)
    connect_bind = Method(
        C.c_int,
        libmosq.mosquitto_connect_bind,
        C.c_void_p,
        C.c_char_p,
        C.c_int,
        C.c_int,
        C.c_char_p,
    )
    # int mosquitto_connect_bind_v5(struct mosquitto *mosq, const char *host, int port, int keepalive, const char *bind_address, const mosquitto_property *props)
    connect_bind_v5 = Method(
        C.c_int,
        libmosq.mosquitto_connect_bind_v5,
        C.c_void_p,
        C.c_char_p,
        C.c_int,
        C.c_int,
        C.c_char_p,
        C.c_void_p,
    )
    # int mosquitto_connect_async(struct mosquitto *mosq, const char *host, int port, int keepalive)
    _connect_async = Method(
        C.c_int,
        libmosq.mosquitto_connect_async,
        C.c_void_p,
        C.c_char_p,
        C.c_int,
        C.c_int,
        auto_encode=False,
    )
    # int mosquitto_connect_bind_async(struct mosquitto *mosq, const char *host, int port, int keepalive, const char *bind_address)
    connect_bind_async = Method(
        C.c_int,
        libmosq.mosquitto_connect_bind_async,
        C.c_void_p,
        C.c_char_p,
        C.c_int,
        C.c_int,
        C.c_char_p,
    )
    # int mosquitto_connect_srv(struct mosquitto *mosq, const char *host, int keepalive, const char *bind_address)
    connect_srv = Method(
        C.c_int,
        libmosq.mosquitto_connect_srv,
        C.c_void_p,
        C.c_char_p,
        C.c_int,
        C.c_char_p,
    )
    # int mosquitto_reconnect(struct mosquitto *mosq)
    reconnect = Method(C.c_int, libmosq.mosquitto_reconnect, C.c_void_p)
    # int mosquitto_reconnect_async(struct mosquitto *mosq)
    reconnect_async = Method(C.c_int, libmosq.mosquitto_reconnect_async, C.c_void_p)
    # int mosquitto_disconnect(struct mosquitto *mosq)
    disconnect = Method(C.c_int, libmosq.mosquitto_disconnect, C.c_void_p)
    # int mosquitto_disconnect_v5(struct mosquitto *mosq, int reason_code, const mosquitto_property *props)
    disconnect_v5 = Method(
        C.c_int, libmosq.mosquitto_disconnect_v5, C.c_void_p, C.c_int, C.c_void_p
    )

    # Publishing, subscribing, unsubscribing
    # int mosquitto_publish(struct mosquitto *mosq, int *mid, const char *topic, int payloadlen, const void *payload, int qos, bool retain)
    _publish = Method(
        C.c_int,
        libmosq.mosquitto_publish,
        C.c_void_p,
        C.POINTER(C.c_int),
        C.c_char_p,
        C.c_int,
        C.c_void_p,
        C.c_int,
        C.c_bool,
        auto_encode=False,
    )
    # int mosquitto_publish_v5(struct mosquitto *mosq, int *mid, const char *topic, int payloadlen, const void *payload, int qos, bool retain, const mosquitto_property *props)
    publish_v5 = Method(
        C.c_int,
        libmosq.mosquitto_publish_v5,
        C.c_void_p,
        C.POINTER(C.c_int),
        C.c_char_p,
        C.c_int,
        C.c_void_p,
        C.c_int,
        C.c_bool,
        C.c_void_p,
    )
    # int mosquitto_subscribe(struct mosquitto *mosq, int *mid, const char *sub, int qos)
    _subscribe = Method(
        C.c_int,
        libmosq.mosquitto_subscribe,
        C.c_void_p,
        C.POINTER(C.c_int),
        C.c_char_p,
        C.c_int,
        auto_encode=False,
    )
    # int mosquitto_subscribe_v5(struct mosquitto *mosq, int *mid, const char *sub, int qos, const mosquitto_property *props)
    subscribe_v5 = Method(
        C.c_int,
        libmosq.mosquitto_subscribe_v5,
        C.c_void_p,
        C.POINTER(C.c_int),
        C.c_char_p,
        C.c_int,
        C.c_void_p,
    )
    # int mosquitto_subscribe_multiple(struct mosquitto *mosq, int *mid, int sub_count, const char **subs, int qos, int options, const mosquitto_property *props)
    subscribe_multiple = Method(
        C.c_int,
        libmosq.mosquitto_subscribe_multiple,
        C.c_void_p,
        C.POINTER(C.c_int),
        C.c_int,
        C.POINTER(C.c_char_p),
        C.c_int,
        C.c_int,
        C.c_void_p,
    )
    # int mosquitto_unsubscribe(struct mosquitto *mosq, int *mid, const char *sub)
    _unsubscribe = Method(
        C.c_int,
        libmosq.mosquitto_unsubscribe,
        C.c_void_p,
        C.POINTER(C.c_int),
        C.c_char_p,
        auto_encode=False,
    )
    # int mosquitto_unsubscribe_v5(struct mosquitto *mosq, int *mid, const char *sub, const mosquitto_property *props)
    unsubscribe_v5 = Method(
        C.c_int,
        libmosq.mosquitto_unsubscribe_v5,
        C.c_void_p,
        C.POINTER(C.c_int),
        C.c_char_p,
        C.c_void_p,
    )
    # int mosquitto_unsubscribe_multiple(struct mosquitto *mosq, int *mid, int sub_count, const char **subs, const mosquitto_property *props)
    unsubscribe_multiple = Method(
        C.c_int,
        libmosq.mosquitto_unsubscribe_multiple,
        C.c_void_p,
        C.POINTER(C.c_int),
        C.c_int,
        C.POINTER(C.c_char_p),
        C.c_void_p,
    )

    # Network loop (managed by libmosquitto)
    # int mosquitto_loop_forever(struct mosquitto *mosq, int timeout, int max_packets)
    _loop_forever = Method(
        C.c_int, libmosq.mosquitto_loop_forever, C.c_void_p, C.c_int, C.c_int
    )
    # int mosquitto_loop_start(struct mosquitto *mosq)
    loop_start = Method(C.c_int, libmosq.mosquitto_loop_start, C.c_void_p)
    # int mosquitto_loop_stop(struct mosquitto *mosq, bool force)
    loop_stop = Method(C.c_int, libmosq.mosquitto_loop_stop, C.c_void_p, C.c_bool)
    # int mosquitto_loop(struct mosquitto *mosq, int timeout, int max_packets)
    loop = Method(C.c_int, libmosq.mosquitto_loop, C.c_void_p, C.c_int, C.c_int)

    # Network loop (for use in other event loops)
    # int mosquitto_loop_read(struct mosquitto *mosq, int max_packets)
    loop_read = Method(C.c_int, libmosq.mosquitto_loop_read, C.c_void_p, C.c_int)
    # int mosquitto_loop_write(struct mosquitto *mosq, int max_packets)
    loop_write = Method(C.c_int, libmosq.mosquitto_loop_write, C.c_void_p, C.c_int)
    # int mosquitto_loop_misc(struct mosquitto *mosq)
    loop_misc = Method(C.c_int, libmosq.mosquitto_loop_misc, C.c_void_p)

    # Network loop (helper functions)
    # int mosquitto_socket(struct mosquitto *mosq)
    _socket = Method(C.c_int, libmosq.mosquitto_socket, C.c_void_p, is_mosq=False)
    # bool mosquitto_want_write(struct mosquitto *mosq)
    want_write = Method(
        C.c_int, libmosq.mosquitto_want_write, C.c_void_p, is_mosq=False
    )
    # int mosquitto_threaded_set(struct mosquitto *mosq, bool threaded)
    threaded_set = Method(C.c_int, libmosq.mosquitto_threaded_set, C.c_void_p, C.c_bool)

    # Client options
    # int mosquitto_opts_set(struct mosquitto *mosq, enum mosq_opt_t option, void *value)
    opts_set = Method(
        C.c_int, libmosq.mosquitto_opts_set, C.c_void_p, C.c_int, C.c_void_p
    )
    # int mosquitto_int_option(struct mosquitto *mosq, enum mosq_opt_t option, int value)
    int_option = Method(
        C.c_int, libmosq.mosquitto_int_option, C.c_void_p, C.c_int, C.c_int
    )
    # int mosquitto_string_option(struct mosquitto *mosq, enum mosq_opt_t option, const char *value)
    string_option = Method(
        C.c_int, libmosq.mosquitto_string_option, C.c_void_p, C.c_int, C.c_char_p
    )
    # int mosquitto_void_option(struct mosquitto *mosq, enum mosq_opt_t option, void *value)
    void_option = Method(
        C.c_int, libmosq.mosquitto_void_option, C.c_void_p, C.c_int, C.c_void_p
    )
    # int mosquitto_reconnect_delay_set(struct mosquitto *mosq, unsigned int reconnect_delay, unsigned int reconnect_delay_max, bool reconnect_exponential_backoff)
    reconnect_delay_set = Method(
        C.c_int,
        libmosq.mosquitto_reconnect_delay_set,
        C.c_void_p,
        C.c_uint,
        C.c_uint,
        C.c_bool,
    )
    # int mosquitto_max_inflight_messages_set(struct mosquitto *mosq, unsigned int max_inflight_messages)
    max_inflight_messages_set = Method(
        C.c_int, libmosq.mosquitto_max_inflight_messages_set, C.c_void_p, C.c_uint
    )
    # int mosquitto_message_retry_set(struct mosquitto *mosq, unsigned int message_retry)
    message_retry_set = Method(
        C.c_int, libmosq.mosquitto_message_retry_set, C.c_void_p, C.c_uint
    )
    # int mosquitto_user_data_set(struct mosquitto *mosq, void *userdata)
    _user_data_set = Method(
        C.c_int, libmosq.mosquitto_user_data_set, C.c_void_p, C.py_object
    )
    # void *mosquitto_userdata(struct mosquitto *mosq)
    _userdata = Method(C.py_object, libmosq.mosquitto_userdata, C.c_void_p)

    # TLS support
    # int mosquitto_tls_set(struct mosquitto *mosq, const char *cafile, const char *capath, const char *certfile, const char *keyfile, int (*pw_callback)(char *buf, int size, int rwflag, void *userdata))
    tls_set = Method(
        C.c_int,
        libmosq.mosquitto_tls_set,
        C.c_void_p,
        C.c_char_p,
        C.c_char_p,
        C.c_char_p,
        C.c_char_p,
    )
    # int mosquitto_tls_insecure_set(struct mosquitto *mosq, bool value)
    tls_insecure_set = Method(
        C.c_int, libmosq.mosquitto_tls_insecure_set, C.c_void_p, C.c_bool
    )
    # int mosquitto_tls_opts_set(struct mosquitto *mosq, int cert_reqs, const char *tls_version, const char *ciphers)
    tls_opts_set = Method(
        C.c_int,
        libmosq.mosquitto_tls_opts_set,
        C.c_void_p,
        C.c_int,
        C.c_char_p,
        C.c_char_p,
    )
    # int mosquitto_tls_psk_set(struct mosquitto *mosq, const char *psk, const char *identity, const char *ciphers)
    tls_psk_set = Method(
        C.c_int,
        libmosq.mosquitto_tls_psk_set,
        C.c_void_p,
        C.c_char_p,
        C.c_char_p,
        C.c_char_p,
    )
    # void *mosquitto_ssl_get(struct mosquitto *mosq)
    ssl_get = Method(C.c_void_p, libmosq.mosquitto_ssl_get, C.c_void_p)

    # Callbacks
    # void mosquitto_connect_callback_set(struct mosquitto *mosq, void (*on_connect)(struct mosquitto *, void *, int))
    ON_CONNECT = C.CFUNCTYPE(None, C.c_void_p, C.py_object, C.c_int)
    on_connect = Callback(libmosq.mosquitto_connect_callback_set, ON_CONNECT)

    # void mosquitto_connect_with_flags_callback_set(struct mosquitto *mosq, void (*on_connect_with_flags)(struct mosquitto *, void *, int, int))
    ON_CONNECT_WITH_FLAGS = C.CFUNCTYPE(None, C.c_void_p, C.py_object, C.c_int, C.c_int)
    on_connect_with_flags = Callback(
        libmosq.mosquitto_connect_with_flags_callback_set, ON_CONNECT_WITH_FLAGS
    )

    # void mosquitto_connect_v5_callback_set(struct mosquitto *mosq, void (*on_connect_v5)(struct mosquitto *, void *, int, int, const mosquitto_property *))
    ON_CONNECT_V5 = C.CFUNCTYPE(
        None, C.c_void_p, C.py_object, C.c_int, C.c_int, C.c_void_p
    )
    on_connect_v5 = Callback(libmosq.mosquitto_connect_v5_callback_set, ON_CONNECT_V5)

    # void mosquitto_disconnect_callback_set(struct mosquitto *mosq, void (*on_disconnect)(struct mosquitto *, void *, int))
    ON_DISCONNECT = C.CFUNCTYPE(None, C.c_void_p, C.py_object, C.c_int)
    on_disconnect = Callback(libmosq.mosquitto_disconnect_callback_set, ON_DISCONNECT)

    # void mosquitto_disconnect_v5_callback_set(struct mosquitto *mosq, void (*on_disconnect_v5)(struct mosquitto *, void *, int, const mosquitto_property *))
    ON_DISCONNECT_V5 = C.CFUNCTYPE(None, C.c_void_p, C.py_object, C.c_int, C.c_void_p)
    on_disconnect_v5 = Callback(
        libmosq.mosquitto_disconnect_v5_callback_set, ON_DISCONNECT_V5
    )

    # void mosquitto_publish_callback_set(struct mosquitto *mosq, void (*on_publish)(struct mosquitto *, void *, int))
    ON_PUBLISH = C.CFUNCTYPE(None, C.c_void_p, C.py_object, C.c_int)
    on_publish = Callback(libmosq.mosquitto_publish_callback_set, ON_PUBLISH)

    # void mosquitto_publish_v5_callback_set(struct mosquitto *mosq, void (*on_publish_v5)(struct mosquitto *, void *, int, const mosquitto_property *))
    ON_PUBLISH_V5 = C.CFUNCTYPE(None, C.c_void_p, C.py_object, C.c_int, C.c_void_p)
    on_publish_v5 = Callback(libmosq.mosquitto_publish_v5_callback_set, ON_PUBLISH_V5)

    # void mosquitto_message_callback_set(struct mosquitto *mosq, void (*on_message)(struct mosquitto *, void *, const struct mosquitto_message *))
    ON_MESSAGE = C.CFUNCTYPE(
        None, C.c_void_p, C.py_object, C.POINTER(MQTTMessageStruct)
    )
    on_message = Callback(libmosq.mosquitto_message_callback_set, ON_MESSAGE)

    # void mosquitto_message_v5_callback_set(struct mosquitto *mosq, void (*on_message_v5)(struct mosquitto *, void *, const struct mosquitto_message *, const mosquitto_property *))
    ON_MESSAGE_V5 = C.CFUNCTYPE(
        None, C.c_void_p, C.py_object, C.POINTER(MQTTMessageStruct), C.c_void_p
    )
    on_message_v5 = Callback(libmosq.mosquitto_message_v5_callback_set, ON_MESSAGE_V5)

    # void mosquitto_subscribe_callback_set(struct mosquitto *mosq, void (*on_subscribe)(struct mosquitto *, void *, int, int, const int *))
    ON_SUBSCRIBE = C.CFUNCTYPE(
        None, C.c_void_p, C.py_object, C.c_int, C.c_int, C.POINTER(C.c_int)
    )
    on_subscribe = Callback(libmosq.mosquitto_subscribe_callback_set, ON_SUBSCRIBE)

    # void mosquitto_subscribe_v5_callback_set(struct mosquitto *mosq, void (*on_subscribe_v5)(struct mosquitto *, void *, int, int, const int *, const mosquitto_property *))
    ON_SUBSCRIBE_V5 = C.CFUNCTYPE(
        None, C.c_void_p, C.py_object, C.c_int, C.c_int, C.POINTER(C.c_int), C.c_void_p
    )
    on_subscribe_v5 = Callback(
        libmosq.mosquitto_subscribe_v5_callback_set, ON_SUBSCRIBE_V5
    )

    # void mosquitto_unsubscribe_callback_set(struct mosquitto *mosq, void (*on_unsubscribe)(struct mosquitto *, void *, int))
    ON_UNSUBSCRIBE = C.CFUNCTYPE(None, C.c_void_p, C.py_object, C.c_int)
    on_unsubscribe = Callback(
        libmosq.mosquitto_unsubscribe_callback_set, ON_UNSUBSCRIBE
    )

    # void mosquitto_unsubscribe_v5_callback_set(struct mosquitto *mosq, void (*on_unsubscribe_v5)(struct mosquitto *, void *, int, const mosquitto_property *))
    ON_UNSUBSCRIBE_V5 = C.CFUNCTYPE(None, C.c_void_p, C.py_object, C.c_int, C.c_void_p)
    on_unsubscribe_v5 = Callback(
        libmosq.mosquitto_unsubscribe_v5_callback_set, ON_UNSUBSCRIBE_V5
    )

    # void mosquitto_log_callback_set(struct mosquitto *mosq, void (*on_log)(struct mosquitto *, void *, int, const char *))
    ON_LOG = C.CFUNCTYPE(None, C.c_void_p, C.py_object, C.c_int, C.c_char_p)
    on_log = Callback(libmosq.mosquitto_log_callback_set, ON_LOG)

    # SOCKS5 proxy functions
    # int mosquitto_socks5_set(struct mosquitto *mosq, const char *host, int port, const char *username, const char *password)
    socks5_set = Method(
        C.c_int,
        libmosq.mosquitto_socks5_set,
        C.c_void_p,
        C.c_char_p,
        C.c_int,
        C.c_char_p,
        C.c_char_p,
    )

    def connect(self, host, port=1883, keepalive=60):
        return self._connect(host.encode(), port, keepalive)

    def connect_async(self, host, port=1883, keepalive=60):
        return self._connect_async(host.encode(), port, keepalive)

    def socket(self):
        fd = self._socket()
        return None if fd == -1 else fd

    def loop_forever(self, timeout=-1):
        return self._loop_forever(timeout, 1)

    def publish(self, topic, payload, qos=0, retain=False):
        mid = C.c_int(0)
        if isinstance(payload, str):
            payload = payload.encode()
        self._publish(
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
        self._subscribe(C.byref(mid), topic.encode(), qos)
        return mid.value

    def unsubscribe(self, topic):
        mid = C.c_int(0)
        self._unsubscribe(C.byref(mid), topic.encode())
        return mid.value

    def user_data_set(self, userdata):
        self._userdata = userdata
        self._user_data_set(self._userdata)

    def userdata(self):
        return self._userdata
