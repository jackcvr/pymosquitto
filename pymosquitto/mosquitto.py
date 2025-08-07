import ctypes as C
from ctypes.util import find_library


class CMessage(C.Structure):
    _fields_ = (
        ("mid", C.c_int),
        ("topic", C.c_char_p),
        ("payload", C.c_void_p),
        ("payloadlen", C.c_int),
        ("qos", C.c_int),
        ("retain", C.c_bool),
    )


CONNECT_CALLBACK = C.CFUNCTYPE(None, C.c_void_p, C.c_void_p, C.c_int)
DISCONNECT_CALLBACK = C.CFUNCTYPE(None, C.c_void_p, C.c_void_p, C.c_int)
SUBSCRIBE_CALLBACK = C.CFUNCTYPE(
    None, C.c_void_p, C.c_void_p, C.c_int, C.c_int, C.POINTER(C.c_int)
)
UNSUBSCRIBE_CALLBACK = C.CFUNCTYPE(None, C.c_void_p, C.c_void_p, C.c_int)
MESSAGE_CALLBACK = C.CFUNCTYPE(None, C.c_void_p, C.c_void_p, C.POINTER(CMessage))
PUBLISH_CALLBACK = C.CFUNCTYPE(None, C.c_void_p, C.c_void_p, C.c_int)


lib = C.cdll.LoadLibrary(find_library("mosquitto"))

# const char *mosquitto_strerror(int mosq_errno)
lib.mosquitto_strerror.argtypes = (C.c_int,)
lib.mosquitto_strerror.restype = C.c_char_p

# const char *mosquitto_connack_string(int connack_code)
lib.mosquitto_connack_string.argtypes = (C.c_int,)
lib.mosquitto_connack_string.restype = C.c_char_p

# int mosquitto_lib_init(void)
lib.mosquitto_lib_init.argtypes = tuple()
lib.mosquitto_lib_init.restype = C.c_int

# int mosquitto_lib_cleanup(void)
lib.mosquitto_lib_cleanup.argtypes = tuple()
lib.mosquitto_lib_cleanup.restype = C.c_int

# struct mosquitto *mosquitto_new(const char *id, bool clean_start, void *userdata)
lib.mosquitto_new.argtypes = (C.c_char_p, C.c_bool, C.py_object)
lib.mosquitto_new.restype = C.c_void_p
lib.mosquitto_new.use_errno = True  # type: ignore[attr-defined]

# void mosquitto_destroy(struct mosquitto *mosq)
lib.mosquitto_destroy.argtypes = (C.c_void_p,)
lib.mosquitto_destroy.restype = None

# int mosquitto_connect(struct mosquitto *mosq, const char *host, int port, int keepalive)
lib.mosquitto_connect.argtypes = (C.c_void_p, C.c_char_p, C.c_int, C.c_int)
lib.mosquitto_connect.restype = C.c_int

# int mosquitto_connect_async(struct mosquitto *mosq, const char *host, int port, int keepalive)
lib.mosquitto_connect_async.argtypes = (C.c_void_p, C.c_char_p, C.c_int, C.c_int)
lib.mosquitto_connect_async.restype = C.c_int

# int mosquitto_disconnect(struct mosquitto *mosq)
lib.mosquitto_disconnect.argtypes = (C.c_void_p,)
lib.mosquitto_disconnect.restype = C.c_int

# int mosquitto_subscribe(struct mosquitto *mosq, int *mid, const char *sub, int qos)
lib.mosquitto_subscribe.argtypes = (C.c_void_p, C.POINTER(C.c_int), C.c_char_p, C.c_int)
lib.mosquitto_subscribe.restype = C.c_int

# int mosquitto_loop_start(struct mosquitto *mosq)
lib.mosquitto_loop_start.argtypes = (C.c_void_p,)
lib.mosquitto_loop_start.restype = C.c_int

# int mosquitto_loop_stop(struct mosquitto *mosq, bool force)
lib.mosquitto_loop_stop.argtypes = (C.c_void_p, C.c_bool)
lib.mosquitto_loop_stop.restype = C.c_int

# int mosquitto_loop_forever(struct mosquitto *mosq, int timeout, int max_packets)
lib.mosquitto_loop_forever.argtypes = (C.c_void_p, C.c_int, C.c_int)
lib.mosquitto_loop_forever.restype = C.c_int

# int mosquitto_publish(struct mosquitto *mosq, int *mid, const char *topic, int payloadlen, const void *payload, int qos, bool retain)
lib.mosquitto_publish.argtypes = (
    C.c_void_p,
    C.POINTER(C.c_int),
    C.c_char_p,
    C.c_int,
    C.c_void_p,
    C.c_int,
    C.c_bool,
)
lib.mosquitto_publish.restype = C.c_int

# void mosquitto_connect_callback_set(struct mosquitto *mosq, void (*on_connect)(struct mosquitto *, void *, int))
lib.mosquitto_connect_callback_set.argtypes = (C.c_void_p, CONNECT_CALLBACK)
lib.mosquitto_connect_callback_set.restype = None

# void mosquitto_disconnect_callback_set(struct mosquitto *mosq, void (*on_disconnect)(struct mosquitto *, void *, int))
lib.mosquitto_disconnect_callback_set.argtypes = (C.c_void_p, DISCONNECT_CALLBACK)
lib.mosquitto_disconnect_callback_set.restype = None

# void mosquitto_subscribe_callback_set(struct mosquitto *mosq, void (*on_subscribe)(struct mosquitto *, void *, int, int, const int *))
lib.mosquitto_subscribe_callback_set.argtypes = (C.c_void_p, SUBSCRIBE_CALLBACK)
lib.mosquitto_subscribe_callback_set.restype = None

# void mosquitto_unsubscribe_callback_set(struct mosquitto *mosq, void (*on_unsubscribe)(struct mosquitto *, void *, int))
lib.mosquitto_unsubscribe_callback_set.argtypes = (C.c_void_p, UNSUBSCRIBE_CALLBACK)
lib.mosquitto_unsubscribe_callback_set.restype = None

# void mosquitto_message_callback_set(struct mosquitto *mosq, void (*on_message)(struct mosquitto *, void *, const struct mosquitto_message *))
lib.mosquitto_message_callback_set.argtypes = (C.c_void_p, MESSAGE_CALLBACK)
lib.mosquitto_message_callback_set.restype = None

# void mosquitto_publish_callback_set(struct mosquitto *mosq, void (*on_publish)(struct mosquitto *, void *, int))
lib.mosquitto_publish_callback_set.argtypes = (C.c_void_p, PUBLISH_CALLBACK)
lib.mosquitto_publish_callback_set.restype = None
