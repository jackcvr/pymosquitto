import ctypes as C
import atexit
import os
import weakref
import typing as t
import enum

from .cutils import call

from .bindings import (
    libmosq,
    CONNECT_CALLBACK,
    DISCONNECT_CALLBACK,
    SUBSCRIBE_CALLBACK,
    UNSUBSCRIBE_CALLBACK,
    MESSAGE_CALLBACK,
    PUBLISH_CALLBACK,
    LOG_CALLBACK,
)


class ErrorCode(enum.IntEnum):
    AUTH_CONTINUE = -4
    NO_SUBSCRIBERS = -3
    SUB_EXISTS = -2
    CONN_PENDING = -1
    SUCCESS = 0
    NOMEM = 1
    PROTOCOL = 2
    INVAL = 3
    NO_CONN = 4
    CONN_REFUSED = 5
    NOT_FOUND = 6
    CONN_LOST = 7
    TLS = 8
    PAYLOAD_SIZE = 9
    NOT_SUPPORTED = 10
    AUTH = 11
    ACL_DENIED = 12
    UNKNOWN = 13
    ERRNO = 14
    EAI = 15
    PROXY = 16
    PLUGIN_DEFER = 17
    MALFORMED_UTF8 = 18
    KEEPALIVE = 19
    LOOKUP = 20
    MALFORMED_PACKET = 21
    DUPLICATE_PROPERTY = 22
    TLS_HANDSHAKE = 23
    QOS_NOT_SUPPORTED = 24
    OVERSIZE_PACKET = 25
    OCSP = 26
    TIMEOUT = 27
    RETAIN_NOT_SUPPORTED = 28
    TOPIC_ALIAS_INVALID = 29
    ADMINISTRATIVE_ACTION = 30
    ALREADY_EXISTS = 31


class ConnackCode(enum.IntEnum):
    ACCEPTED = 0
    REFUSED_PROTOCOL_VERSION = 1
    REFUSED_IDENTIFIER_REJECTED = 2
    REFUSED_SERVER_UNAVAILABLE = 3
    REFUSED_BAD_USERNAME_PASSWORD = 4
    REFUSED_NOT_AUTHORIZED = 5


class ReasonCode(enum.IntEnum):
    SUCCESS = 0
    NORMAL_DISCONNECTION = 0
    GRANTED_QOS0 = 0
    GRANTED_QOS1 = 1
    GRANTED_QOS2 = 2
    DISCONNECT_WITH_WILL_MSG = 4
    NO_MATCHING_SUBSCRIBERS = 16
    NO_SUBSCRIPTION_EXISTED = 17
    CONTINUE_AUTHENTICATION = 24
    REAUTHENTICATE = 25
    UNSPECIFIED = 128
    MALFORMED_PACKET = 129
    PROTOCOL_ERROR = 130
    IMPLEMENTATION_SPECIFIC = 131
    UNSUPPORTED_PROTOCOL_VERSION = 132
    CLIENTID_NOT_VALID = 133
    BAD_USERNAME_OR_PASSWORD = 134
    NOT_AUTHORIZED = 135
    SERVER_UNAVAILABLE = 136
    SERVER_BUSY = 137
    BANNED = 138
    SERVER_SHUTTING_DOWN = 139
    BAD_AUTHENTICATION_METHOD = 140
    KEEP_ALIVE_TIMEOUT = 141
    SESSION_TAKEN_OVER = 142
    TOPIC_FILTER_INVALID = 143
    TOPIC_NAME_INVALID = 144
    PACKET_ID_IN_USE = 145
    PACKET_ID_NOT_FOUND = 146
    RECEIVE_MAXIMUM_EXCEEDED = 147
    TOPIC_ALIAS_INVALID = 148
    PACKET_TOO_LARGE = 149
    MESSAGE_RATE_TOO_HIGH = 150
    QUOTA_EXCEEDED = 151
    ADMINISTRATIVE_ACTION = 152
    PAYLOAD_FORMAT_INVALID = 153
    RETAIN_NOT_SUPPORTED = 154
    QOS_NOT_SUPPORTED = 155
    USE_ANOTHER_SERVER = 156
    SERVER_MOVED = 157
    SHARED_SUBS_NOT_SUPPORTED = 158
    CONNECTION_RATE_EXCEEDED = 159
    MAXIMUM_CONNECT_TIME = 160
    SUBSCRIPTION_IDS_NOT_SUPPORTED = 161
    WILDCARD_SUBS_NOT_SUPPORTED = 162


class LogLevel(enum.IntEnum):
    NONE = 0
    INFO = 1 << 0
    NOTICE = 1 << 1
    WARNING = 1 << 2
    ERR = 1 << 3
    DEBUG = 1 << 4
    SUBSCRIBE = 1 << 5
    UNSUBSCRIBE = 1 << 6
    WEBSOCKETS = 1 << 7
    INTERNAL = 0x80000000
    ALL = 0xFFFFFFFF


class MosquittoError(Exception):
    def __init__(self, func, code):
        self.func_name = func.__name__
        self.code = code

    def __str__(self):
        return f"{self.func_name} failed: {self.code}, {strerror(self.code)}"


class MQTTMessage(t.NamedTuple):
    mid: int
    topic: str
    payload: bytes
    qos: int = 0
    retain: bool = False

    @classmethod
    def from_c(cls, cmsg):
        contents = cmsg.contents
        return cls(
            mid=contents.mid,
            topic=C.string_at(contents.topic).decode(),
            payload=C.string_at(contents.payload, contents.payloadlen),
            qos=contents.qos,
            retain=contents.retain,
        )


def strerror(rc):
    return libmosq.mosquitto_strerror(rc).decode()


def connack_string(rc):
    return libmosq.mosquitto_connack_string(rc).decode()


def reason_string(rc):
    return libmosq.mosquitto_reason_string(rc).decode()


def to_python(obj):
    return C.cast(obj, C.py_object).value


call(libmosq.mosquitto_lib_init)
atexit.register(libmosq.mosquitto_lib_cleanup)


class Mosquitto:
    def __init__(self, client_id=None, clean_start=True, userdata=None):
        if client_id:
            client_id = client_id.encode()
        self._mosq = call(
            libmosq.mosquitto_new, client_id, clean_start, userdata, use_errno=True
        )
        self._finalizer = weakref.finalize(
            self, call, libmosq.mosquitto_destroy, self._mosq
        )
        self.__connect_callback = None
        self.__disconnect_callback = None
        self.__subscribe_callback = None
        self.__unsubscribe_callback = None
        self.__publish_callback = None
        self.__message_callback = None
        self.__log_callback = None

    def _call(self, func, *args, use_errno=False):
        rc = call(func, self._mosq, *args, use_errno=use_errno)
        if rc == ErrorCode.ERRNO:
            errno = C.get_errno()
            raise OSError(errno, os.strerror(errno))
        if rc == 0:
            return rc
        elif isinstance(rc, int):
            raise MosquittoError(func, rc)
        return rc

    def destroy(self):
        if self._finalizer.alive:
            self._finalizer()

    def connect(self, host, port=1883, keepalive=60):
        self._call(libmosq.mosquitto_connect, host.encode(), port, keepalive)

    def connect_async(self, host, port=1883, keepalive=60):
        self._call(libmosq.mosquitto_connect_async, host.encode(), port, keepalive)

    def reconnect_async(self):
        self._call(libmosq.mosquitto_reconnect_async)

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
        c_mid = C.c_int(0)
        self._call(libmosq.mosquitto_subscribe, C.byref(c_mid), topic.encode(), qos)
        return c_mid.value

    def unsubscribe(self, topic):
        c_mid = C.c_int(0)
        self._call(libmosq.mosquitto_unsubscribe, C.byref(c_mid), topic.encode())
        return c_mid.value

    def publish(self, topic, payload, qos=0, retain=False):
        c_mid = C.c_int(0)
        self._call(
            libmosq.mosquitto_publish,
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
