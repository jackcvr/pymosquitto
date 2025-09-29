import ctypes as C
import os

from .constants import LIBMOSQ_PATH

libmosq = C.CDLL(LIBMOSQ_PATH, use_errno=True)


def bind(restype, func, *argtypes):
    func.restype = restype
    func.argtypes = argtypes
    return func


###
### Library version, init, and cleanup
###

# int mosquitto_lib_init(void)
bind(C.c_int, libmosq.mosquitto_lib_init)

# int mosquitto_lib_cleanup(void)
bind(C.c_int, libmosq.mosquitto_lib_cleanup)

# int mosquitto_lib_version(int *major, int *minor, int *revision)
bind(
    C.c_int,
    libmosq.mosquitto_lib_version,
    C.POINTER(C.c_int),
    C.POINTER(C.c_int),
    C.POINTER(C.c_int),
)

###
### Client creation, destruction, and reinitialisation
###

# struct mosquitto *mosquitto_new(const char *id, bool clean_start, void *userdata)
bind(C.c_void_p, libmosq.mosquitto_new, C.c_char_p, C.c_bool, C.py_object)

###
### Utility functions
###

# const char *mosquitto_strerror(int mosq_errno)
bind(C.c_char_p, libmosq.mosquitto_strerror, C.c_int)

# const char *mosquitto_connack_string(int connack_code)
bind(C.c_char_p, libmosq.mosquitto_connack_string, C.c_int)

# const char *mosquitto_reason_string(int reason_code)
bind(C.c_char_p, libmosq.mosquitto_reason_string, C.c_int)

# int mosquitto_topic_matches_sub(const char *sub, const char *topic, bool *result)
bind(
    C.c_int,
    libmosq.mosquitto_topic_matches_sub,
    C.c_char_p,
    C.c_char_p,
    C.POINTER(C.c_bool),
)


def strerror(errno):
    return libmosq.mosquitto_strerror(errno).decode()


def connack_string(code):
    return libmosq.mosquitto_connack_string(code).decode()


def reason_string(code):
    return libmosq.mosquitto_reason_string(code).decode()


def encode(args):
    return [arg.encode() if isinstance(arg, str) else arg for arg in args]


def call(func, *args, use_errno=False, auto_encode=False, auto_decode=False):
    if auto_encode and any(arg == C.c_char_p for arg in func.argtypes):
        args = encode(args)
    if use_errno:
        C.set_errno(0)
    ret = func(*args)
    if use_errno:
        err = C.get_errno()
        if err != 0:
            raise OSError(err, os.strerror(err))
    if auto_decode and func.restype == C.c_char_p:
        ret = ret.deccode()
    return ret


class MQTTMessageStruct(C.Structure):
    _fields_ = (
        ("mid", C.c_int),
        ("topic", C.c_char_p),
        ("payload", C.c_void_p),
        ("payloadlen", C.c_int),
        ("qos", C.c_int),
        ("retain", C.c_bool),
    )


ON_CONNECT = C.CFUNCTYPE(None, C.c_void_p, C.py_object, C.c_int)
ON_CONNECT_WITH_FLAGS = C.CFUNCTYPE(None, C.c_void_p, C.py_object, C.c_int, C.c_int)
ON_CONNECT_V5 = C.CFUNCTYPE(None, C.c_void_p, C.py_object, C.c_int, C.c_int, C.c_void_p)
ON_DISCONNECT = C.CFUNCTYPE(None, C.c_void_p, C.py_object, C.c_int)
ON_DISCONNECT_V5 = C.CFUNCTYPE(None, C.c_void_p, C.py_object, C.c_int, C.c_void_p)
ON_PUBLISH = C.CFUNCTYPE(None, C.c_void_p, C.py_object, C.c_int)
ON_PUBLISH_V5 = C.CFUNCTYPE(None, C.c_void_p, C.py_object, C.c_int, C.c_void_p)
ON_MESSAGE = C.CFUNCTYPE(None, C.c_void_p, C.py_object, C.POINTER(MQTTMessageStruct))
ON_MESSAGE_V5 = C.CFUNCTYPE(
    None, C.c_void_p, C.py_object, C.POINTER(MQTTMessageStruct), C.c_void_p
)
ON_SUBSCRIBE = C.CFUNCTYPE(
    None, C.c_void_p, C.py_object, C.c_int, C.c_int, C.POINTER(C.c_int)
)
ON_SUBSCRIBE_V5 = C.CFUNCTYPE(
    None, C.c_void_p, C.py_object, C.c_int, C.c_int, C.POINTER(C.c_int), C.c_void_p
)
ON_UNSUBSCRIBE = C.CFUNCTYPE(None, C.c_void_p, C.py_object, C.c_int)
ON_UNSUBSCRIBE_V5 = C.CFUNCTYPE(None, C.c_void_p, C.py_object, C.c_int, C.c_void_p)
ON_LOG = C.CFUNCTYPE(None, C.c_void_p, C.py_object, C.c_int, C.c_char_p)
