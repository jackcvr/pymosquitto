import ctypes as C
import os
from dataclasses import dataclass

from pymosquitto.constants import LIBMOSQ_PATH, LIBMOSQ_MIN_MAJOR_VERSION, ErrorCode

libmosq = C.CDLL(LIBMOSQ_PATH, use_errno=True)

###
### Library version, init, and cleanup
###

# int mosquitto_lib_version(int *major, int *minor, int *revision)
libmosq.mosquitto_lib_version.argtypes = (
    C.POINTER(C.c_int),
    C.POINTER(C.c_int),
    C.POINTER(C.c_int),
)
libmosq.mosquitto_lib_version.restype = C.c_int

# int mosquitto_lib_init(void)
libmosq.mosquitto_lib_init.argtypes = tuple()
libmosq.mosquitto_lib_init.restype = C.c_int

# int mosquitto_lib_cleanup(void)
libmosq.mosquitto_lib_cleanup.argtypes = tuple()
libmosq.mosquitto_lib_cleanup.restype = C.c_int

###
### Client creation, destruction, and reinitialisation
###

# struct mosquitto *mosquitto_new(const char *id, bool clean_start, void *userdata)
libmosq.mosquitto_new.argtypes = (C.c_char_p, C.c_bool, C.py_object)
libmosq.mosquitto_new.restype = C.c_void_p

# void mosquitto_destroy(struct mosquitto *mosq)
libmosq.mosquitto_destroy.argtypes = (C.c_void_p,)
libmosq.mosquitto_destroy.restype = None

###
### Username and password
###

# int mosquitto_username_pw_set(struct mosquitto *mosq, const char *username, const char *password)
libmosq.mosquitto_username_pw_set.argtypes = (C.c_void_p, C.c_char_p, C.c_char_p)
libmosq.mosquitto_username_pw_set.restype = C.c_int

###
### Connecting, reconnecting, disconnecting
###

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

###
### Publishing, subscribing, unsubscribing
###

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

###
### Network loop (managed by libmosquitto)
###

# int mosquitto_loop_start(struct mosquitto *mosq)
libmosq.mosquitto_loop_start.argtypes = (C.c_void_p,)
libmosq.mosquitto_loop_start.restype = C.c_int

# int mosquitto_loop_stop(struct mosquitto *mosq, bool force)
libmosq.mosquitto_loop_stop.argtypes = (C.c_void_p, C.c_bool)
libmosq.mosquitto_loop_stop.restype = C.c_int

# int mosquitto_loop_forever(struct mosquitto *mosq, int timeout, int max_packets)
libmosq.mosquitto_loop_forever.argtypes = (C.c_void_p, C.c_int, C.c_int)
libmosq.mosquitto_loop_forever.restype = C.c_int

###
### Network loop (for use in other event loops)
###

# int mosquitto_loop_read(struct mosquitto *mosq, int max_packets)
libmosq.mosquitto_loop_read.argtypes = (C.c_void_p, C.c_int)
libmosq.mosquitto_loop_read.restype = C.c_int

# int mosquitto_loop_write(struct mosquitto *mosq, int max_packets)
libmosq.mosquitto_loop_write.argtypes = (C.c_void_p, C.c_int)
libmosq.mosquitto_loop_write.restype = C.c_int

# int mosquitto_loop_misc(struct mosquitto *mosq)
libmosq.mosquitto_loop_misc.argtypes = (C.c_void_p,)
libmosq.mosquitto_loop_misc.restype = C.c_int

###
### Network loop (helper functions)
###

# int mosquitto_socket(struct mosquitto *mosq)
libmosq.mosquitto_socket.argtypes = (C.c_void_p,)
libmosq.mosquitto_socket.restype = C.c_int

# bool mosquitto_want_write(struct mosquitto *mosq)
libmosq.mosquitto_want_write.argtypes = (C.c_void_p,)
libmosq.mosquitto_want_write.restype = C.c_bool

# int mosquitto_threaded_set(struct mosquitto *mosq, bool threaded)
libmosq.mosquitto_threaded_set.argtypes = (C.c_void_p, C.c_bool)
libmosq.mosquitto_threaded_set.restype = C.c_int


###
### Callbacks
###


class MQTTMessageStruct(C.Structure):
    _fields_ = (
        ("mid", C.c_int),
        ("topic", C.c_char_p),
        ("payload", C.c_void_p),
        ("payloadlen", C.c_int),
        ("qos", C.c_int),
        ("retain", C.c_bool),
    )


CONNECT_CALLBACK = C.CFUNCTYPE(None, C.c_void_p, C.py_object, C.c_int)
DISCONNECT_CALLBACK = C.CFUNCTYPE(None, C.c_void_p, C.py_object, C.c_int)
SUBSCRIBE_CALLBACK = C.CFUNCTYPE(
    None, C.c_void_p, C.py_object, C.c_int, C.c_int, C.POINTER(C.c_int)
)
UNSUBSCRIBE_CALLBACK = C.CFUNCTYPE(None, C.c_void_p, C.py_object, C.c_int)
PUBLISH_CALLBACK = C.CFUNCTYPE(None, C.c_void_p, C.py_object, C.c_int)
MESSAGE_CALLBACK = C.CFUNCTYPE(
    None, C.c_void_p, C.py_object, C.POINTER(MQTTMessageStruct)
)
LOG_CALLBACK = C.CFUNCTYPE(None, C.c_void_p, C.py_object, C.c_int, C.c_char_p)

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

###
### Utility functions
###

# const char *mosquitto_strerror(int mosq_errno)
libmosq.mosquitto_strerror.argtypes = (C.c_int,)
libmosq.mosquitto_strerror.restype = C.c_char_p

# const char *mosquitto_connack_string(int connack_code)
libmosq.mosquitto_connack_string.argtypes = (C.c_int,)
libmosq.mosquitto_connack_string.restype = C.c_char_p

# const char *mosquitto_reason_string(int reason_code)
libmosq.mosquitto_reason_string.argtypes = (C.c_int,)
libmosq.mosquitto_reason_string.restype = C.c_char_p

# int mosquitto_topic_matches_sub(const char *sub, const char *topic, bool *result);
libmosq.mosquitto_topic_matches_sub.argtypes = (
    C.c_char_p,
    C.c_char_p,
    C.POINTER(C.c_bool),
)
libmosq.mosquitto_topic_matches_sub.restype = C.c_int

### END OF BINDINGS


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


def strerror(rc):
    return libmosq.mosquitto_strerror(rc).decode()


def connack_string(rc):
    return libmosq.mosquitto_connack_string(rc).decode()


def reason_string(rc):
    return libmosq.mosquitto_reason_string(rc).decode()


class MosquittoError(Exception):
    def __init__(self, func, code):
        self.func = func
        self.code = ErrorCode(code)

    def __str__(self):
        return f"{self.func.__name__} failed: {self.code}/{strerror(self.code)}"


def call_errno(func, *args):
    C.set_errno(0)
    ret = func(*args)
    return ret, C.get_errno()


def call(func, *args, use_errno=False):
    if use_errno:
        ret, err = call_errno(func, *args)
        if err != 0:
            raise OSError(err, os.strerror(err))
        return ret
    return func(*args)


def mosq_call(func, *args, use_errno=False):
    if use_errno:
        ret, err = call_errno(func, *args)
        if ret == ErrorCode.ERRNO and err != 0:
            raise OSError(err, os.strerror(err))
    else:
        ret = func(*args)
    if func.restype == C.c_int and ret != 0:
        raise MosquittoError(func, ret)
    return ret


@dataclass(frozen=True, slots=True)
class MQTTMessage:
    mid: int
    topic: str
    payload: bytes
    qos: int
    retain: bool

    @classmethod
    def from_struct(cls, msg: MQTTMessageStruct):
        cnt = msg.contents
        return cls(
            cnt.mid,
            C.string_at(cnt.topic).decode(),
            C.string_at(cnt.payload, cnt.payloadlen),
            cnt.qos,
            cnt.retain,
        )
