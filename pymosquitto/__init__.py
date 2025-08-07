import ctypes as C
import atexit
import threading
import typing as t
import weakref

from .mosquitto import (
    lib,
    CONNECT_CALLBACK,
    DISCONNECT_CALLBACK,
    SUBSCRIBE_CALLBACK,
    UNSUBSCRIBE_CALLBACK,
    MESSAGE_CALLBACK,
    PUBLISH_CALLBACK,
)


class CError(RuntimeError):
    def __init__(self, func, code):
        self.func = func
        self.code = code

    def __str__(self):
        return f"{self.func.__name__} failed: {self.code}, {strerror(self.code)}"


def strerror(rc):
    return C.c_char_p(lib.mosquitto_strerror(rc)).value.decode()


def connack_string(rc):
    return C.c_char_p(lib.mosquitto_connack_string(rc)).value.decode()


def cast_py_value(obj):
    return C.cast(obj, C.py_object).value


def c_run(c_func, *args):
    rc = c_func(*args)
    if rc is not None and rc != 0:
        raise CError(c_func, rc)


class MQTTMessage(t.NamedTuple):
    mid: int
    topic: str
    payload: bytes
    qos: int = 0
    retain: bool = False

    @classmethod
    def from_c_message(cls, c_msg):
        return cls(
            mid=c_msg.mid,
            topic=C.string_at(c_msg.topic).decode(),
            payload=C.string_at(c_msg.payload, c_msg.payloadlen),
            qos=c_msg.qos,
            retain=c_msg.retain,
        )


C.set_errno(0)
c_run(lib.mosquitto_lib_init)
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
            raise CError(lib.mosquitto_new, C.get_errno())
        weakref.finalize(self, c_run, lib.mosquitto_destroy, self._mosq)
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

    def _run(self, c_func, *args):
        if self.logger:
            self.logger.debug(
                "Executing C function: %s%s",
                c_func.__name__,
                (self._mosq,) + args,
            )
        c_run(c_func, self._mosq, *args)

    def _set_lib_callbacks(self):
        self._wrap_lib_callbacks()
        self._run(lib.mosquitto_connect_callback_set, self._lib_on_connect)
        self._run(lib.mosquitto_disconnect_callback_set, self._lib_on_disconnect)
        self._run(lib.mosquitto_subscribe_callback_set, self._lib_on_subscribe)
        self._run(lib.mosquitto_unsubscribe_callback_set, self._lib_on_unsubscribe)
        self._run(lib.mosquitto_publish_callback_set, self._lib_on_publish)
        self._run(lib.mosquitto_message_callback_set, self._lib_on_message)

    def _wrap_lib_callbacks(self):
        self._lib_on_connect = CONNECT_CALLBACK(self._lib_on_connect)
        self._lib_on_disconnect = DISCONNECT_CALLBACK(self._lib_on_disconnect)
        self._lib_on_subscribe = SUBSCRIBE_CALLBACK(self._lib_on_subscribe)
        self._lib_on_unsubscribe = UNSUBSCRIBE_CALLBACK(self._lib_on_unsubscribe)
        self._lib_on_publish = PUBLISH_CALLBACK(self._lib_on_publish)
        self._lib_on_message = MESSAGE_CALLBACK(self._lib_on_message)

    def connect(self, host, port=DEFAULT_PORT, keepalive=DEFAULT_KEEPALIVE):
        self._run(lib.mosquitto_connect, host.encode(), port, keepalive)

    def connect_async(self, host, port=DEFAULT_PORT, keepalive=DEFAULT_KEEPALIVE):
        self._run(lib.mosquitto_connect_async, host.encode(), port, keepalive)

    def wait_connection(self, timeout=None):
        with self.cond:
            return self.cond.wait_for(lambda: self.is_connected, timeout=timeout)

    def disconnect(self):
        self._run(lib.mosquitto_disconnect)

    def loop_start(self):
        with self.cond:
            self._run(lib.mosquitto_loop_start)
            self._is_threaded = True

    def loop_stop(self, force=False):
        with self.cond:
            self._run(lib.mosquitto_loop_stop, force)
            self._is_threaded = False

    def loop_forever(self):
        import signal

        def stop(*_):
            try:
                self.disconnect()
            except CError as e:
                if e.code != 4:
                    raise e from None
            else:
                import sys

                sys.exit(1)

        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, stop)

        self._run(lib.mosquitto_loop_forever, -1, 1)

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
                self.loop_stop(force=True)
            self._mosq = None

    def subscribe(self, topic, qos=0):
        with self.cond:
            self.topics[topic] = qos
            if self.is_connected:
                self._subscribe(topic, qos)

    def _subscribe(self, topic, qos=0):
        self._run(lib.mosquitto_subscribe, None, topic.encode(), qos)
        if self.logger:
            self.logger.debug("SUB_SENT: (topic=%s qos=%d)", topic, qos)

    def publish(self, topic, payload, qos=0):
        c_mid = C.c_int(0)
        self._run(
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
            self._on_connect(userdata)
            self.cond.notify_all()

    def _on_connect(self, userdata):
        for topic, qos in self.topics.items():
            self._subscribe(topic, qos)
        if self.on_connect:
            self.on_connect(self, cast_py_value(userdata))

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
        msg = MQTTMessage.from_c_message(msg.contents)
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
