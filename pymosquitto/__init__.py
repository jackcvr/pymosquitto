import ctypes as C
from ctypes.util import find_library
import atexit
import threading
import typing as t
import weakref


class CError(RuntimeError):
    pass


class MQTTMessage(t.NamedTuple):
    mid: int
    topic: str
    payload: bytes
    qos: int = 0
    retain: bool = False


class MosqMessage(C.Structure):
    _fields_ = (
        ("mid", C.c_int),
        ("topic", C.c_char_p),
        ("payload", C.c_void_p),
        ("payloadlen", C.c_int),
        ("qos", C.c_int),
        ("retain", C.c_bool),
    )

    def as_mqtt_message(self):
        return MQTTMessage(
            mid=self.mid,
            topic=C.string_at(self.topic).decode(),
            payload=C.string_at(self.payload, self.payloadlen),
            qos=self.qos,
            retain=self.retain,
        )


def strerror(rc):
    return C.c_char_p(lib.mosquitto_strerror(rc)).value.decode()


def connack_string(rc):
    return C.c_char_p(lib.mosquitto_connack_string(rc)).value.decode()


def cast_py_value(obj):
    return C.cast(obj, C.py_object).value


CONNECT_CALLBACK = C.CFUNCTYPE(None, C.c_void_p, C.c_void_p, C.c_int)
DISCONNECT_CALLBACK = C.CFUNCTYPE(None, C.c_void_p, C.c_void_p, C.c_int)
SUBSCRIBE_CALLBACK = C.CFUNCTYPE(
    None, C.c_void_p, C.c_void_p, C.c_int, C.c_int, C.POINTER(C.c_int)
)
UNSUBSCRIBE_CALLBACK = C.CFUNCTYPE(None, C.c_void_p, C.c_void_p, C.c_int)
MESSAGE_CALLBACK = C.CFUNCTYPE(None, C.c_void_p, C.c_void_p, C.POINTER(MosqMessage))
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

C.set_errno(0)
__rc = lib.mosquitto_lib_init()
if __rc != 0:
    raise RuntimeError(f"mosquitto_lib_init failed: {__rc}/{strerror(__rc)}")
atexit.register(lib.mosquitto_lib_cleanup)


def _make_handler_decorator(attr):
    def decorator(self, func):
        setattr(self, attr, func)
        return func

    return decorator


class MQTTClient:
    DEFAULT_PORT = 1883
    DEFAULT_KEEPALIVE = 60

    def __init__(self, client_id=None, userdata=None, logger=None):
        if client_id:
            client_id = client_id.encode()
        self._mosq = lib.mosquitto_new(client_id, True, userdata)
        if not self._mosq:
            rc = C.get_errno()
            raise RuntimeError(f"Failed to create Mosquitto instance: {strerror(rc)}")
        weakref.finalize(self, self.run, lib.mosquitto_destroy)
        self.logger = logger
        self.cond = threading.Condition()
        self.topics = {}
        self.handlers = None
        self.is_connected = False
        self._is_threaded = False
        # user callbacks
        self.on_connect = None
        self.on_disconnect = None
        self.on_subscribe = None
        self.on_unsubscribe = None
        self.on_publish = None
        self.on_message = None
        self._set_lib_callbacks()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def run(self, func, *args):
        rc = func(self._mosq, *args)
        if self.logger:
            self.logger.debug(
                "Executed C function: %s%s: %r", func.__name__, (self._mosq,) + args, rc
            )
        if rc is not None and rc != 0:
            msg = strerror(rc)
            raise CError(f"{func.__name__} failed: {rc}, {msg}")

    def _set_lib_callbacks(self):
        self._wrap_lib_callbacks()
        self.run(lib.mosquitto_connect_callback_set, self._lib_on_connect)
        self.run(lib.mosquitto_disconnect_callback_set, self._lib_on_disconnect)
        self.run(lib.mosquitto_subscribe_callback_set, self._lib_on_subscribe)
        self.run(lib.mosquitto_unsubscribe_callback_set, self._lib_on_unsubscribe)
        self.run(lib.mosquitto_publish_callback_set, self._lib_on_publish)
        self.run(lib.mosquitto_message_callback_set, self._lib_on_message)

    def _wrap_lib_callbacks(self):
        self._lib_on_connect = CONNECT_CALLBACK(self._lib_on_connect)
        self._lib_on_disconnect = DISCONNECT_CALLBACK(self._lib_on_disconnect)
        self._lib_on_subscribe = SUBSCRIBE_CALLBACK(self._lib_on_subscribe)
        self._lib_on_unsubscribe = UNSUBSCRIBE_CALLBACK(self._lib_on_unsubscribe)
        self._lib_on_publish = PUBLISH_CALLBACK(self._lib_on_publish)
        self._lib_on_message = MESSAGE_CALLBACK(self._lib_on_message)

    def connect(self, host, port=DEFAULT_PORT, keepalive=DEFAULT_KEEPALIVE):
        self.run(lib.mosquitto_connect, host.encode(), port, keepalive)

    def connect_async(self, host, port=DEFAULT_PORT, keepalive=DEFAULT_KEEPALIVE):
        self.run(lib.mosquitto_connect_async, host.encode(), port, keepalive)

    def wait_connection(self, timeout=None):
        with self.cond:
            self.cond.wait_for(lambda: self.is_connected, timeout=timeout)

    def disconnect(self, timeout=1):
        self.run(lib.mosquitto_disconnect)

    def loop_start(self):
        with self.cond:
            self.run(lib.mosquitto_loop_start)
            self._is_threaded = True

    def loop_stop(self, force=False):
        with self.cond:
            self.run(lib.mosquitto_loop_stop, force)
            self._is_threaded = False

    def loop_forever(self):
        self.run(lib.mosquitto_loop_forever, -1, 1)

    def close(self):
        if not hasattr(self, "_mosq"):
            return
        with self.cond:
            if not self._mosq:
                return
            if self.is_connected:
                self.disconnect()
                self.cond.wait_for(lambda: not self.is_connected, timeout=1)
            if self._is_threaded:
                self.loop_stop(True)
            self._mosq = None

    def subscribe(self, topic, qos=0):
        with self.cond:
            self.topics[topic] = qos
            if self.is_connected:
                self._subscribe(topic, qos)

    def _subscribe(self, topic, qos=0):
        self.run(lib.mosquitto_subscribe, None, topic.encode(), qos)
        if self.logger:
            self.logger.debug("SUB_SENT: (topic=%s qos=%d)", topic, qos)

    def publish(self, topic, payload, qos=0):
        c_mid = C.c_int(0)
        self.run(
            lib.mosquitto_publish,
            C.byref(c_mid),
            topic.encode(),
            len(payload),
            C.c_char_p(payload.encode()),
            qos,
            False,
        )
        if self.logger:
            self.logger.debug(
                "PUB_SENT: (mid=%d topic=%s qos=%d payload=%s)",
                c_mid.value,
                topic,
                qos,
                payload,
            )
        return c_mid.value

    def add_topic_handler(self, topic, func):
        if self.handlers is None:
            from .utils import TopicMatcher

            self.handlers = TopicMatcher()
        self.handlers[topic] = func

    def topic_handler(self, topic):
        def decorator(func):
            self.add_topic_handler(topic, func)
            return func

        return decorator

    def remove_topic_handler(self, topic):
        del self.handlers[topic]

    # -----------
    # CALLBACKS
    # -----------

    def _lib_on_connect(self, mosq, userdata, rc):
        rc_desc = connack_string(rc)
        if rc != 0:
            if self.logger:
                self.logger.warning("Connection failed: %s", rc_desc)
            return
        with self.cond:
            self.is_connected = True
            if self.logger:
                self.logger.info("Connected: %s", rc_desc)
            self._on_connect(userdata, rc)
            self.cond.notify_all()

    def _on_connect(self, userdata, rc):
        for topic, qos in self.topics.items():
            self._subscribe(topic, qos)
        if self.on_connect:
            self.on_connect(self, cast_py_value(userdata), rc)

    def _lib_on_disconnect(self, mosq, userdata, rc):
        with self.cond:
            self.is_connected = False
            if self.logger:
                if rc == 0:
                    self.logger.info("Disconnected")
                else:
                    self.logger.warning("Disconnected: %s", connack_string(rc))
            self._on_disconnect(userdata, rc)
            self.cond.notify_all()

    def _on_disconnect(self, userdata, rc):
        if self.on_disconnect:
            self.on_disconnect(self, cast_py_value(userdata), rc)

    def _lib_on_subscribe(self, mosq, userdata, mid, qos_count, granted_qos):
        qos_list = [granted_qos[i] for i in range(qos_count)]
        if self.logger:
            self.logger.debug("SUB: (mid=%d granted_qos=%s)", mid, qos_list)
        self._on_subscribe(userdata, mid, qos_list)

    def _on_subscribe(self, userdata, mid, qos_list):
        if self.on_subscribe:
            self.on_subscribe(self, cast_py_value(userdata), mid, qos_list)

    def _lib_on_unsubscribe(self, mosq, userdata, mid):
        if self.logger:
            self.logger.debug("UNSUB: (mid=%d)", mid)
        self._on_unsubscribe(userdata, mid)

    def _on_unsubscribe(self, userdata, mid):
        if self.on_unsubscribe:
            self.on_unsubscribe(self, cast_py_value(userdata), mid)

    def _lib_on_publish(self, mosq, userdata, mid):
        if self.logger:
            self.logger.debug("PUB: (mid=%d)", mid)
        self._on_publish(userdata, mid)

    def _on_publish(self, userdata, mid):
        if self.on_publish:
            self.on_publish(self, cast_py_value(userdata), mid)

    def _lib_on_message(self, mosq, userdata, msg):
        msg = msg.contents.as_mqtt_message()
        if self.logger:
            self.logger.debug("RECV: %s", msg)
        self._on_message(userdata, msg)

    def _on_message(self, userdata, msg):
        if self.on_message:
            self.on_message(self, cast_py_value(userdata), msg)
        else:
            if not self.handlers:
                return
            userdata = cast_py_value(userdata)
            for handler in self.handlers.find(msg.topic):
                try:
                    handler(self, userdata, msg)
                except Exception as e:
                    self.logger.exception(e)

    on_connect_handler = _make_handler_decorator("on_connect")
    on_disconnect_handler = _make_handler_decorator("on_disconnect")
    on_subscribe_handler = _make_handler_decorator("on_subscribe")
    on_unsubscribe_handler = _make_handler_decorator("on_unsubscribe")
    on_publish_handler = _make_handler_decorator("on_publish")
    on_message_handler = _make_handler_decorator("on_message")
