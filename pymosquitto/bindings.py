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

# int mosquitto_property_add_byte(mosquitto_property **proplist, int identifier, uint8_t value)
bind(
    C.c_int,
    libmosq.mosquitto_property_add_byte,
    C.POINTER(C.c_void_p),
    C.c_int,
    C.c_uint8,
)

# int mosquitto_property_add_int16(mosquitto_property **proplist, int identifier, uint16_t value)
bind(
    C.c_int,
    libmosq.mosquitto_property_add_int16,
    C.POINTER(C.c_void_p),
    C.c_int,
    C.c_uint16,
)

# int mosquitto_property_add_int32(mosquitto_property **proplist, int identifier, uint32_t value)
bind(
    C.c_int,
    libmosq.mosquitto_property_add_int32,
    C.POINTER(C.c_void_p),
    C.c_int,
    C.c_int32,
)

# int mosquitto_property_add_varint(mosquitto_property **proplist, int identifier, uint32_t value)
bind(
    C.c_int,
    libmosq.mosquitto_property_add_varint,
    C.POINTER(C.c_void_p),
    C.c_int,
    C.c_uint32,
)

# int mosquitto_property_add_binary(mosquitto_property **proplist, int identifier, const void *value, uint16_t len)
bind(
    C.c_int,
    libmosq.mosquitto_property_add_binary,
    C.POINTER(C.c_void_p),
    C.c_int,
    C.c_void_p,
    C.c_uint16,
)

# int mosquitto_property_add_string(mosquitto_property **proplist, int identifier, const char *value)
bind(
    C.c_int,
    libmosq.mosquitto_property_add_string,
    C.POINTER(C.c_void_p),
    C.c_int,
    C.c_char_p,
)

# int mosquitto_property_add_string_pair(mosquitto_property **proplist, int identifier, const char *name, const char *value)
bind(
    C.c_int,
    libmosq.mosquitto_property_add_string_pair,
    C.POINTER(C.c_void_p),
    C.c_int,
    C.c_char_p,
    C.c_char_p,
)

# int mosquitto_property_identifier(const mosquitto_property *property)
bind(C.c_int, libmosq.mosquitto_property_identifier, C.c_void_p)

# mosquitto_property* mosquitto_property_next(const mosquitto_property *property)
bind(C.c_void_p, libmosq.mosquitto_property_next, C.c_void_p)

# int mosquitto_property_read_byte(const mosquitto_property *props, int identifier, uint8_t *value, bool skip_first)
bind(
    C.c_int,
    libmosq.mosquitto_property_read_byte,
    C.c_void_p,
    C.c_int,
    C.POINTER(C.c_uint8),
    C.c_bool,
)

# int mosquitto_property_read_int16(const mosquitto_property *props, int identifier, uint16_t *value, bool skip_first)
bind(
    C.c_int,
    libmosq.mosquitto_property_read_int16,
    C.c_void_p,
    C.c_int,
    C.POINTER(C.c_uint16),
    C.c_bool,
)

# int mosquitto_property_read_int32(const mosquitto_property *props, int identifier, uint32_t *value, bool skip_first)
bind(
    C.c_int,
    libmosq.mosquitto_property_read_int32,
    C.c_void_p,
    C.c_int,
    C.POINTER(C.c_uint32),
    C.c_bool,
)

# int mosquitto_property_read_varint(const mosquitto_property *props, int identifier, uint32_t *value, bool skip_first)
bind(
    C.c_int,
    libmosq.mosquitto_property_read_varint,
    C.c_void_p,
    C.c_int,
    C.POINTER(C.c_uint32),
    C.c_bool,
)

# int mosquitto_property_read_binary(const mosquitto_property *props, int identifier, void **value, uint16_t *len, bool skip_first)
bind(
    C.c_int,
    libmosq.mosquitto_property_read_binary,
    C.c_void_p,
    C.c_int,
    C.POINTER(C.c_void_p),
    C.POINTER(C.c_uint16),
    C.c_bool,
)

# int mosquitto_property_read_string(const mosquitto_property *props, int identifier, char **value, bool skip_first)
bind(
    C.c_int,
    libmosq.mosquitto_property_read_string,
    C.c_void_p,
    C.c_int,
    C.POINTER(C.c_char_p),
    C.c_bool,
)

# int mosquitto_property_read_string_pair(const mosquitto_property *props, int identifier, char **name, char **value, bool skip_first)
bind(
    C.c_int,
    libmosq.mosquitto_property_read_string_pair,
    C.c_void_p,
    C.c_int,
    C.POINTER(C.c_char_p),
    C.POINTER(C.c_char_p),
    C.c_bool,
)

# void mosquitto_property_free_all(mosquitto_property **proplist)
bind(None, libmosq.mosquitto_property_free_all, C.POINTER(C.c_void_p))

# int mosquitto_property_copy_all(mosquitto_property **dest, const mosquitto_property *src)
bind(C.c_int, libmosq.mosquitto_property_copy_all, C.POINTER(C.c_void_p), C.c_void_p)

# int mosquitto_property_check_command(int command, int identifier)
bind(C.c_int, libmosq.mosquitto_property_check_command, C.c_int, C.c_int)

# int mosquitto_property_check_all(int command, const mosquitto_property *props)
bind(C.c_int, libmosq.mosquitto_property_check_all, C.c_int, C.c_void_p)

# const char *mosquitto_property_identifier_to_string(int identifier)
bind(C.c_char_p, libmosq.mosquitto_property_identifier_to_string, C.c_int)

# int mosquitto_string_to_property_info(const char *propname, int *identifier, int *type)
bind(
    C.c_int,
    libmosq.mosquitto_string_to_property_info,
    C.c_char_p,
    C.POINTER(C.c_int),
    C.POINTER(C.c_int),
)


class MQTTMessageStruct(C.Structure):
    _fields_ = (
        ("mid", C.c_int),
        ("topic", C.c_char_p),
        ("payload", C.c_void_p),
        ("payloadlen", C.c_int),
        ("qos", C.c_int),
        ("retain", C.c_bool),
    )


class MQTTStringStruct(C.Structure):
    _fields_ = [
        ("v", C.c_void_p),
        ("len", C.c_uint16),
    ]


class MQTT5PropertyValueStruct(C.Union):
    _fields_ = [
        ("i8", C.c_uint8),
        ("i16", C.c_uint16),
        ("i32", C.c_uint32),
        ("varint", C.c_uint32),
        ("bin", MQTTStringStruct),
        ("s", MQTTStringStruct),
    ]


class MQTT5PropertyStruct(C.Structure):
    pass


MQTT5PropertyStruct._fields_ = [
    ("next", C.POINTER(MQTT5PropertyStruct)),
    ("value", MQTT5PropertyValueStruct),
    ("name", MQTTStringStruct),
    ("identifier", C.c_int32),
    ("client_generated", C.c_bool),
]

ON_CONNECT = C.CFUNCTYPE(None, C.c_void_p, C.py_object, C.c_int)
ON_CONNECT_WITH_FLAGS = C.CFUNCTYPE(None, C.c_void_p, C.py_object, C.c_int, C.c_int)
ON_CONNECT_V5 = C.CFUNCTYPE(
    None, C.c_void_p, C.py_object, C.c_int, C.c_int, C.POINTER(MQTT5PropertyStruct)
)
ON_DISCONNECT = C.CFUNCTYPE(None, C.c_void_p, C.py_object, C.c_int)
ON_DISCONNECT_V5 = C.CFUNCTYPE(
    None, C.c_void_p, C.py_object, C.c_int, C.POINTER(MQTT5PropertyStruct)
)
ON_PUBLISH = C.CFUNCTYPE(None, C.c_void_p, C.py_object, C.c_int)
ON_PUBLISH_V5 = C.CFUNCTYPE(
    None, C.c_void_p, C.py_object, C.c_int, C.POINTER(MQTT5PropertyStruct)
)
ON_MESSAGE = C.CFUNCTYPE(None, C.c_void_p, C.py_object, C.POINTER(MQTTMessageStruct))
ON_MESSAGE_V5 = C.CFUNCTYPE(
    None,
    C.c_void_p,
    C.py_object,
    C.POINTER(MQTTMessageStruct),
    C.POINTER(MQTT5PropertyStruct),
)
ON_SUBSCRIBE = C.CFUNCTYPE(
    None, C.c_void_p, C.py_object, C.c_int, C.c_int, C.POINTER(C.c_int)
)
ON_SUBSCRIBE_V5 = C.CFUNCTYPE(
    None,
    C.c_void_p,
    C.py_object,
    C.c_int,
    C.c_int,
    C.POINTER(C.c_int),
    C.POINTER(MQTT5PropertyStruct),
)
ON_UNSUBSCRIBE = C.CFUNCTYPE(None, C.c_void_p, C.py_object, C.c_int)
ON_UNSUBSCRIBE_V5 = C.CFUNCTYPE(
    None, C.c_void_p, C.py_object, C.c_int, C.POINTER(MQTT5PropertyStruct)
)
ON_LOG = C.CFUNCTYPE(None, C.c_void_p, C.py_object, C.c_int, C.c_char_p)


def call(func, *args, use_errno=False, auto_encode=False, auto_decode=False):
    if auto_encode and any(arg == C.c_char_p for arg in func.argtypes):
        args = [arg.encode() if isinstance(arg, str) else arg for arg in args]
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


def strerror(errno):
    return libmosq.mosquitto_strerror(errno).decode()


def connack_string(code):
    return libmosq.mosquitto_connack_string(code).decode()


def reason_string(code):
    return libmosq.mosquitto_reason_string(code).decode()
