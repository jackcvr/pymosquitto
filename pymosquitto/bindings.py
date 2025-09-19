import ctypes as C
import os

from .constants import LIBMOSQ_PATH

libmosq = C.CDLL(LIBMOSQ_PATH, use_errno=True)


def encode(args):
    return [arg.encode() if isinstance(arg, str) else arg for arg in args]


def bind(restype, func, *argtypes, auto_encode=False, auto_decode=False):
    func.restype = restype
    func.argtypes = argtypes

    auto_encode = auto_encode and any(arg == C.c_char_p for arg in argtypes)
    auto_decode = auto_decode and restype == C.c_char_p

    if auto_encode or auto_decode:

        def wrapper(*args):
            if auto_encode:
                args = encode(args)
            ret = func(*args)
            if auto_decode:
                ret = ret.decode()
            return ret

        wrapper.__name__ = func.__name__
        wrapper.restype = restype
        wrapper.argtypes = argtypes
        return wrapper

    return func


###
### Library version, init, and cleanup
###

# int mosquitto_lib_version(int *major, int *minor, int *revision)
bind(
    C.c_int,
    libmosq.mosquitto_lib_version,
    C.POINTER(C.c_int),
    C.POINTER(C.c_int),
    C.POINTER(C.c_int),
)

# int mosquitto_lib_init(void)
bind(C.c_int, libmosq.mosquitto_lib_init)

# int mosquitto_lib_cleanup(void)
bind(C.c_int, libmosq.mosquitto_lib_cleanup)

###
### Client creation, destruction, and reinitialisation
###

# struct mosquitto *mosquitto_new(const char *id, bool clean_start, void *userdata)
bind(C.c_void_p, libmosq.mosquitto_new, C.c_char_p, C.c_bool, C.py_object)

###
### Utility functions
###

# const char *mosquitto_strerror(int mosq_errno)
strerror = bind(C.c_char_p, libmosq.mosquitto_strerror, C.c_int, auto_decode=True)

# const char *mosquitto_connack_string(int connack_code)
connack_string = bind(
    C.c_char_p, libmosq.mosquitto_connack_string, C.c_int, auto_decode=True
)

# const char *mosquitto_reason_string(int reason_code)
reason_string = bind(
    C.c_char_p, libmosq.mosquitto_reason_string, C.c_int, auto_decode=True
)

# int mosquitto_topic_matches_sub(const char *sub, const char *topic, bool *result)
bind(
    C.c_int,
    libmosq.mosquitto_topic_matches_sub,
    C.c_char_p,
    C.c_char_p,
    C.POINTER(C.c_bool),
    auto_encode=False,
)


def call(func, *args, use_errno=False):
    if use_errno:
        C.set_errno(0)
    ret = func(*args)
    if use_errno:
        err = C.get_errno()
        if err != 0:
            raise OSError(err, os.strerror(err))
    return ret
