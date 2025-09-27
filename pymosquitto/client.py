import ctypes as C
import atexit
from dataclasses import dataclass
import typing as t
import weakref
import types

from .constants import LogLevel, LIBMOSQ_MIN_MAJOR_VERSION, ErrorCode, ConnackCode
from .bindings import bind, call, libmosq, strerror, MQTTMessageStruct
from .bindings import (
    ON_CONNECT,
    ON_CONNECT_WITH_FLAGS,
    ON_CONNECT_V5,
    ON_DISCONNECT,
    ON_DISCONNECT_V5,
    ON_LOG,
    ON_UNSUBSCRIBE_V5,
    ON_UNSUBSCRIBE,
    ON_SUBSCRIBE_V5,
    ON_SUBSCRIBE,
    ON_MESSAGE,
    ON_PUBLISH_V5,
    ON_PUBLISH,
    ON_MESSAGE_V5,
)

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

if libmosq.mosquitto_lib_init() != 0:
    raise RuntimeError("libmosquitto initialization failed")
atexit.register(libmosq.mosquitto_lib_cleanup)


class LibMosqError(Exception):
    def __init__(self, code):
        self.code = ErrorCode(code)

    def __str__(self):
        return f"libmosquitto error: {self.code.value}/{self.code.name}/{strerror(self.code)}"


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

    def __get__(self, obj, objtype=None):
        method_name = self._func.__name__

        if not hasattr(obj, method_name):
            _obj = weakref.proxy(obj)
            func = self._func
            is_mosq = self._is_mosq

            def method(self_, *args):
                return self_.call(func, *args, is_mosq=is_mosq)

            setattr(obj, method_name, types.MethodType(method, _obj))

        return getattr(obj, method_name)


class Callback:
    def __init__(self, setter, decorator, wrapper):
        self._setter = bind(None, setter, C.c_void_p, decorator)
        self._decorator = decorator
        self._wrapper = wrapper
        self._wrapped_callback = None

    def __set_name__(self, owner, name):
        self._attr_name = f"__{name[3:]}_callback"

    def __set__(self, obj, callback):
        setattr(obj, self._attr_name, callback)
        if callback and not self._wrapped_callback:
            self._wrapped_callback = self._decorator(self._wrapper)
        elif not callback:
            self._wrapped_callback = self._decorator(0)
        self._setter(obj.mosq_ptr, self._wrapped_callback)

    def __get__(self, obj, objtype=None):
        return getattr(obj, self._attr_name)


def _connect_callback_wrapper(mosq, userdata, rc):
    client = clients.get(mosq, None)
    if client and client.on_connect:
        client.on_connect(client, client.userdata(), ConnackCode(rc))


def _connect_with_flags_callback_wrapper(mosq, userdata, rc, flags):
    client = clients.get(mosq, None)
    if client and client.on_connect_with_flags:
        client.on_connect_with_flags(client, client.userdata(), ConnackCode(rc), flags)


def _connect_v5_callback_wrapper(mosq, userdata, rc, flags, props):
    client = clients.get(mosq, None)
    if client and client.on_connect_v5:
        client.on_connect_v5(client, client.userdata(), ConnackCode(rc), flags, props)


def _disconnect_callback_wrapper(mosq, userdata, rc):
    client = clients.get(mosq, None)
    if client and client.on_disconnect:
        client.on_disconnect(client, client.userdata(), ConnackCode(rc))


def _disconnect_v5_callback_wrapper(mosq, userdata, rc, props):
    client = clients.get(mosq, None)
    if client and client.on_disconnect_v5:
        client.on_disconnect_v5(client, client.userdata(), ConnackCode(rc), props)


def _publish_callback_wrapper(mosq, userdata, mid):
    client = clients.get(mosq, None)
    if client and client.on_publish:
        client.on_publish(client, client.userdata(), mid)


def _publish_v5_callback_wrapper(mosq, userdata, mid, props):
    client = clients.get(mosq, None)
    if client and client.on_publish_v5:
        client.on_publish_v5(client, client.userdata(), mid, props)


def _message_callback_wrapper(mosq, userdata, msg):
    client = clients.get(mosq, None)
    if client and client.on_message:
        client.on_message(client, client.userdata(), MQTTMessage.from_struct(msg))


def _message_v5_callback_wrapper(mosq, userdata, msg, props):
    client = clients.get(mosq, None)
    if client and client.on_message_v5:
        client.on_message_v5(
            client, client.userdata(), MQTTMessage.from_struct(msg), props
        )


def _subscribe_callback_wrapper(mosq, userdata, mid, count, granted_qos):
    client = clients.get(mosq, None)
    if client and client.on_subscribe:
        client.on_subscribe(
            client,
            client.userdata(),
            mid,
            count,
            [granted_qos[i] for i in range(count)],
        )


def _subscribe_v5_callback_wrapper(mosq, userdata, mid, count, granted_qos, props):
    client = clients.get(mosq, None)
    if client and client.on_subscribe_v5:
        client.on_subscribe_v5(
            client,
            client.userdata(),
            mid,
            count,
            [granted_qos[i] for i in range(count)],
            props,
        )


def _unsubscribe_callback_wrapper(mosq, userdata, mid):
    client = clients.get(mosq, None)
    if client and client.on_unsubscribe:
        client.on_unsubscribe(client, client.userdata(), mid)


def _unsubscribe_v5_callback_wrapper(mosq, userdata, mid, props):
    client = clients.get(mosq, None)
    if client and client.on_unsubscribe_v5:
        client.on_unsubscribe_v5(client, client.userdata(), mid, props)


def _log_callback_wrapper(mosq, userdata, level, msg):
    client = clients.get(mosq, None)
    if client and client.on_log:
        client.on_log(client, client.userdata(), LogLevel(level), msg.decode())
    elif client and client.logger:
        client.logger.debug("MOSQ/%s %s", LogLevel(level).name, msg.decode())


clients: weakref.WeakValueDictionary[int, t.Any] = weakref.WeakValueDictionary()


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
            None,
            use_errno=True,
        )
        clients[self._mosq_ptr] = self

    @property
    def mosq_ptr(self):
        return self._mosq_ptr

    @property
    def logger(self):
        return self._logger

    def __del__(self):
        self.user_data_set(None)
        self.destroy()

    def call(self, func, *args, is_mosq=True, **kwargs):
        if self._logger:
            self._logger.debug("CALL: %s%s", func.__name__, (self._mosq_ptr,) + args)
        ret = call(func, self._mosq_ptr, *args, **kwargs)
        if is_mosq and func.restype == C.c_int and ret != ErrorCode.SUCCESS:
            raise LibMosqError(ret)
        return ret

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
    on_connect = Callback(
        libmosq.mosquitto_connect_callback_set,
        ON_CONNECT,
        _connect_callback_wrapper,
    )
    on_connect_with_flags = Callback(
        libmosq.mosquitto_connect_with_flags_callback_set,
        ON_CONNECT_WITH_FLAGS,
        _connect_with_flags_callback_wrapper,
    )
    on_connect_v5 = Callback(
        libmosq.mosquitto_connect_v5_callback_set,
        ON_CONNECT_V5,
        _connect_v5_callback_wrapper,
    )
    on_disconnect = Callback(
        libmosq.mosquitto_disconnect_callback_set,
        ON_DISCONNECT,
        _disconnect_callback_wrapper,
    )
    on_disconnect_v5 = Callback(
        libmosq.mosquitto_disconnect_v5_callback_set,
        ON_DISCONNECT_V5,
        _disconnect_v5_callback_wrapper,
    )
    on_publish = Callback(
        libmosq.mosquitto_publish_callback_set,
        ON_PUBLISH,
        _publish_callback_wrapper,
    )
    on_publish_v5 = Callback(
        libmosq.mosquitto_publish_v5_callback_set,
        ON_PUBLISH_V5,
        _publish_v5_callback_wrapper,
    )
    on_message = Callback(
        libmosq.mosquitto_message_callback_set,
        ON_MESSAGE,
        _message_callback_wrapper,
    )
    on_message_v5 = Callback(
        libmosq.mosquitto_message_v5_callback_set,
        ON_MESSAGE_V5,
        _message_v5_callback_wrapper,
    )
    on_subscribe = Callback(
        libmosq.mosquitto_subscribe_callback_set,
        ON_SUBSCRIBE,
        _subscribe_callback_wrapper,
    )
    on_subscribe_v5 = Callback(
        libmosq.mosquitto_subscribe_v5_callback_set,
        ON_SUBSCRIBE_V5,
        _subscribe_v5_callback_wrapper,
    )
    on_unsubscribe = Callback(
        libmosq.mosquitto_unsubscribe_callback_set,
        ON_UNSUBSCRIBE,
        _unsubscribe_callback_wrapper,
    )
    on_unsubscribe_v5 = Callback(
        libmosq.mosquitto_unsubscribe_v5_callback_set,
        ON_UNSUBSCRIBE_V5,
        _unsubscribe_v5_callback_wrapper,
    )
    on_log = Callback(
        libmosq.mosquitto_log_callback_set,
        ON_LOG,
        _log_callback_wrapper,
    )

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

    def userdata(self):
        return self._userdata
