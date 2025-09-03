import ctypes as C
import typing as t

from pymosquitto.constants import LIBMOSQ_PATH, LIBMOSQ_MIN_MAJOR_VERSION

libmosq = C.CDLL(LIBMOSQ_PATH, use_errno=True)

libmosq.mosquitto_lib_version.argtypes = (
    C.POINTER(C.c_int),
    C.POINTER(C.c_int),
    C.POINTER(C.c_int),
)
libmosq.mosquitto_lib_version.restype = C.c_int

_libmosq_version = (C.c_int(), C.c_int(), C.c_int())
libmosq.mosquitto_lib_version(
    C.byref(_libmosq_version[0]),
    C.byref(_libmosq_version[1]),
    C.byref(_libmosq_version[2]),
)
LIBMOSQ_VERSION = (
    _libmosq_version[0].value,
    _libmosq_version[1].value,
    _libmosq_version[2].value,
)
del _libmosq_version

if LIBMOSQ_VERSION[0] < LIBMOSQ_MIN_MAJOR_VERSION:
    raise RuntimeError(f"libmosquitto version {LIBMOSQ_MIN_MAJOR_VERSION}+ is required")


class CMessage(C.Structure):
    _fields_ = (
        ("mid", C.c_int),
        ("topic", C.c_char_p),
        ("payload", C.c_void_p),
        ("payloadlen", C.c_int),
        ("qos", C.c_int),
        ("retain", C.c_bool),
    )


class MQTTMessage(t.NamedTuple):
    mid: int
    topic: str
    payload: bytes
    qos: int = 0
    retain: bool = False

    @classmethod
    def from_cmessage(cls, msg):
        contents = msg.contents
        return cls(
            mid=contents.mid,
            topic=C.string_at(contents.topic).decode(),
            payload=C.string_at(contents.payload, contents.payloadlen),
            qos=contents.qos,
            retain=contents.retain,
        )


CONNECT_CALLBACK = C.CFUNCTYPE(None, C.c_void_p, C.py_object, C.c_int)
DISCONNECT_CALLBACK = C.CFUNCTYPE(None, C.c_void_p, C.py_object, C.c_int)
SUBSCRIBE_CALLBACK = C.CFUNCTYPE(
    None, C.c_void_p, C.py_object, C.c_int, C.c_int, C.POINTER(C.c_int)
)
UNSUBSCRIBE_CALLBACK = C.CFUNCTYPE(None, C.py_object, C.c_void_p, C.c_int)
PUBLISH_CALLBACK = C.CFUNCTYPE(None, C.py_object, C.c_void_p, C.c_int)
MESSAGE_CALLBACK = C.CFUNCTYPE(None, C.py_object, C.c_void_p, C.POINTER(CMessage))
LOG_CALLBACK = C.CFUNCTYPE(None, C.py_object, C.c_void_p, C.c_int, C.c_char_p)

# const char *mosquitto_strerror(int mosq_errno)
libmosq.mosquitto_strerror.argtypes = (C.c_int,)
libmosq.mosquitto_strerror.restype = C.c_char_p

# const char *mosquitto_connack_string(int connack_code)
libmosq.mosquitto_connack_string.argtypes = (C.c_int,)
libmosq.mosquitto_connack_string.restype = C.c_char_p

# const char *mosquitto_reason_string(int reason_code)
libmosq.mosquitto_reason_string.argtypes = (C.c_int,)
libmosq.mosquitto_reason_string.restype = C.c_char_p

# int mosquitto_lib_init(void)
libmosq.mosquitto_lib_init.argtypes = tuple()
libmosq.mosquitto_lib_init.restype = C.c_int

# int mosquitto_lib_cleanup(void)
libmosq.mosquitto_lib_cleanup.argtypes = tuple()
libmosq.mosquitto_lib_cleanup.restype = C.c_int

# struct mosquitto *mosquitto_new(const char *id, bool clean_start, void *userdata)
libmosq.mosquitto_new.argtypes = (C.c_char_p, C.c_bool, C.py_object)
libmosq.mosquitto_new.restype = C.c_void_p

# void mosquitto_destroy(struct mosquitto *mosq)
libmosq.mosquitto_destroy.argtypes = (C.c_void_p,)
libmosq.mosquitto_destroy.restype = None

# int mosquitto_username_pw_set(struct mosquitto *mosq, const char *username, const char *password)
libmosq.mosquitto_username_pw_set.argtypes = (C.c_void_p, C.c_char_p, C.c_char_p)
libmosq.mosquitto_username_pw_set.restype = C.c_int

# int mosquitto_connect(struct mosquitto *mosq, const char *host, int port, int keepalive)
libmosq.mosquitto_connect.argtypes = (C.c_void_p, C.c_char_p, C.c_int, C.c_int)
libmosq.mosquitto_connect.restype = C.c_int

# int mosquitto_connect_async(struct mosquitto *mosq, const char *host, int port, int keepalive)
libmosq.mosquitto_connect_async.argtypes = (C.c_void_p, C.c_char_p, C.c_int, C.c_int)
libmosq.mosquitto_connect_async.restype = C.c_int

# int mosquitto_reconnect_async(struct mosquitto *mosq)
libmosq.mosquitto_reconnect_async.argtypes = (C.c_void_p,)
libmosq.mosquitto_reconnect_async.restype = C.c_int

# int mosquitto_reconnect_delay_set(struct mosquitto *mosq, unsigned int reconnect_delay, unsigned int reconnect_delay_max, bool reconnect_exponential_backoff)
libmosq.mosquitto_reconnect_delay_set.argtypes = (
    C.c_void_p,
    C.c_uint,
    C.c_uint,
    C.c_bool,
)
libmosq.mosquitto_reconnect_delay_set.restype = C.c_int

# int mosquitto_disconnect(struct mosquitto *mosq)
libmosq.mosquitto_disconnect.argtypes = (C.c_void_p,)
libmosq.mosquitto_disconnect.restype = C.c_int

# int mosquitto_subscribe(struct mosquitto *mosq, int *mid, const char *sub, int qos)
libmosq.mosquitto_subscribe.argtypes = (
    C.c_void_p,
    C.POINTER(C.c_int),
    C.c_char_p,
    C.c_int,
)
libmosq.mosquitto_subscribe.restype = C.c_int

# int mosquitto_unsubscribe(struct mosquitto *mosq, int *mid, const char *sub)
libmosq.mosquitto_unsubscribe.argtypes = (C.c_void_p, C.POINTER(C.c_int), C.c_char_p)
libmosq.mosquitto_unsubscribe.restype = C.c_int

# int mosquitto_loop_start(struct mosquitto *mosq)
libmosq.mosquitto_loop_start.argtypes = (C.c_void_p,)
libmosq.mosquitto_loop_start.restype = C.c_int

# int mosquitto_loop_stop(struct mosquitto *mosq, bool force)
libmosq.mosquitto_loop_stop.argtypes = (C.c_void_p, C.c_bool)
libmosq.mosquitto_loop_stop.restype = C.c_int

# int mosquitto_loop_forever(struct mosquitto *mosq, int timeout, int max_packets)
libmosq.mosquitto_loop_forever.argtypes = (C.c_void_p, C.c_int, C.c_int)
libmosq.mosquitto_loop_forever.restype = C.c_int

# int mosquitto_publish(struct mosquitto *mosq, int *mid, const char *topic, int payloadlen, const void *payload, int qos, bool retain)
libmosq.mosquitto_publish.argtypes = (
    C.c_void_p,
    C.POINTER(C.c_int),
    C.c_char_p,
    C.c_int,
    C.c_void_p,
    C.c_int,
    C.c_bool,
)
libmosq.mosquitto_publish.restype = C.c_int

# void mosquitto_connect_callback_set(struct mosquitto *mosq, void (*on_connect)(struct mosquitto *, void *, int))
libmosq.mosquitto_connect_callback_set.argtypes = (C.c_void_p, CONNECT_CALLBACK)
libmosq.mosquitto_connect_callback_set.restype = None

# void mosquitto_disconnect_callback_set(struct mosquitto *mosq, void (*on_disconnect)(struct mosquitto *, void *, int))
libmosq.mosquitto_disconnect_callback_set.argtypes = (C.c_void_p, DISCONNECT_CALLBACK)
libmosq.mosquitto_disconnect_callback_set.restype = None

# void mosquitto_subscribe_callback_set(struct mosquitto *mosq, void (*on_subscribe)(struct mosquitto *, void *, int, int, const int *))
libmosq.mosquitto_subscribe_callback_set.argtypes = (C.c_void_p, SUBSCRIBE_CALLBACK)
libmosq.mosquitto_subscribe_callback_set.restype = None

# void mosquitto_unsubscribe_callback_set(struct mosquitto *mosq, void (*on_unsubscribe)(struct mosquitto *, void *, int))
libmosq.mosquitto_unsubscribe_callback_set.argtypes = (C.c_void_p, UNSUBSCRIBE_CALLBACK)
libmosq.mosquitto_unsubscribe_callback_set.restype = None

# void mosquitto_publish_callback_set(struct mosquitto *mosq, void (*on_publish)(struct mosquitto *, void *, int))
libmosq.mosquitto_publish_callback_set.argtypes = (C.c_void_p, PUBLISH_CALLBACK)
libmosq.mosquitto_publish_callback_set.restype = None

# void mosquitto_message_callback_set(struct mosquitto *mosq, void (*on_message)(struct mosquitto *, void *, const struct mosquitto_message *))
libmosq.mosquitto_message_callback_set.argtypes = (C.c_void_p, MESSAGE_CALLBACK)
libmosq.mosquitto_message_callback_set.restype = None

# void mosquitto_log_callback_set(struct mosquitto *mosq, void (*on_log)(struct mosquitto *, void *, int, const char *))
libmosq.mosquitto_log_callback_set.argtypes = (C.c_void_p, LOG_CALLBACK)


def strerror(rc):
    return libmosq.mosquitto_strerror(rc).decode()


def connack_string(rc):
    return libmosq.mosquitto_connack_string(rc).decode()


def reason_string(rc):
    return libmosq.mosquitto_reason_string(rc).decode()


def call(func, *args):
    C.set_errno(0)
    ret = func(*args)
    return ret, C.get_errno()
