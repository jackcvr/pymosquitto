import threading
import ctypes as C

from .base import (
    Mosquitto,
    to_python,
    connack_string,
    MQTTMessage,
    MosquittoError,
    ErrorCode,
    LogLevel,
)
from .cutils import call


class CallbackSetter:
    def __set_name__(self, owner, name):
        if not name.startswith("on_"):
            raise ValueError(
                "Bad name: callback property name should start with 'on_' prefix"
            )
        self.callback_name = f"_{name[3:]}_callback"

    def __get__(self, obj, objtype=None):
        def decorator(func):
            setattr(obj, self.callback_name, func)
            return func

        decorator.__name__ = f"{self.callback_name}_decorator"
        return decorator

    def __set__(self, obj, func):
        setattr(obj, self.callback_name, func)


class MQTTClient(Mosquitto):
    def __init__(self, *args, logger=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = logger
        self._topics = {}
        self._handlers = None
        self._cond = threading.Condition()
        self._is_connected = False
        self._set_lib_callbacks()
        # user callbacks
        self._connect_callback = None
        self._disconnect_callback = None
        self._subscribe_callback = None
        self._unsubscribe_callback = None
        self._publish_callback = None
        self._message_callback = None
        self._log_callback = None

    on_connect = CallbackSetter()
    on_disconnect = CallbackSetter()
    on_subscribe = CallbackSetter()
    on_unsubscribe = CallbackSetter()
    on_publish = CallbackSetter()
    on_message = CallbackSetter()
    on_log = CallbackSetter()

    @property
    def topics(self):
        return self._topics

    @property
    def is_connected(self):
        return self._is_connected

    def _call(self, func, *args):
        if self._logger:
            self._logger.debug(
                "C call: %s%s",
                func.__name__,
                (self._c_mosq_p,) + args,
            )
        super()._call(func, *args)

    def _set_lib_callbacks(self):
        self.connect_callback_set(self._on_connect)
        self.disconnect_callback_set(self._on_disconnect)
        self.subscribe_callback_set(self._on_subscribe)
        self.unsubscribe_callback_set(self._on_unsubscribe)
        self.publish_callback_set(self._on_publish)
        self.message_callback_set(self._on_message)
        self.log_callback_set(self._on_log)

    def wait_until_connected(self, timeout=None):
        with self._cond:
            return self._cond.wait_for(lambda: self._is_connected, timeout=timeout)

    def loop_forever(self, timeout=-1, *, _direct=False):
        if _direct:
            super().loop_forever(timeout)
            return

        import signal

        libc = C.CDLL(None)
        HANDLER_FUNC = C.CFUNCTYPE(None, C.c_int)
        libc.signal.argtypes = [C.c_int, HANDLER_FUNC]
        libc.signal.restype = HANDLER_FUNC

        @HANDLER_FUNC
        def _stop(signum):
            if self._logger:
                self._logger.debug("Caught signal: %s", signal.Signals(signum).name)
            try:
                self.disconnect()
            except MosquittoError as e:
                if e.code != ErrorCode.NO_CONN:
                    raise e from None

        for sig in (signal.SIGALRM, signal.SIGTERM, signal.SIGINT):
            call(libc.signal, sig, _stop, use_errno=True)

        super().loop_forever(timeout)

    def subscribe(self, topic, qos=0, *, _direct=False):
        if _direct:
            return super().subscribe(topic, qos)
        with self._cond:
            self._topics[topic] = qos
            if self._is_connected:
                return super().subscribe(topic, qos)
            return None

    def unsubscribe(self, topic, *, _direct=False):
        if _direct:
            return super().unsubscribe(topic)
        with self._cond:
            if topic in self._topics:
                del self._topics[topic]
            if self._is_connected:
                return super().unsubscribe(topic)
            return None

    def add_topic_handler(self, topic, func):
        if self._handlers is None:
            self._handlers = self._handlers_factory()
        self._handlers[topic] = func

    def remove_topic_handler(self, topic):
        del self._handlers[topic]

    def on_topic(self, topic):
        def decorator(func):
            self.add_topic_handler(topic, func)
            return func

        return decorator

    @staticmethod
    def _handlers_factory():
        from .utils import SafeTopicMatcher

        return SafeTopicMatcher(threading.Lock())

    # -----------
    # CALLBACKS
    # -----------

    def _on_connect(self, mosq, userdata, rc):
        info = connack_string(rc)
        with self._cond:
            if rc == 0:
                self._is_connected = True
                if self._logger:
                    self._logger.info("Connected: %s", info)
                for topic, qos in self._topics.items():
                    self.subscribe(topic, qos)
            else:
                self._is_connected = False
                if self._logger:
                    self._logger.warning("Connection failed: %s", info)
            if self._connect_callback:
                self._connect_callback(self, to_python(userdata), rc)
            self._cond.notify_all()

    def _on_disconnect(self, mosq, userdata, rc):
        with self._cond:
            self._is_connected = False
            if self._logger:
                if rc == 0:
                    self._logger.info("Disconnected")
                else:
                    self._logger.warning("Disconnected: %s", connack_string(rc))
            if self._disconnect_callback:
                self._disconnect_callback(self, to_python(userdata), rc)
            self._cond.notify_all()

    def _on_subscribe(self, mosq, userdata, mid, qos_count, granted_qos):
        qos_list = [granted_qos[i] for i in range(qos_count)]
        if self._logger:
            self._logger.debug("SUB: (mid=%d granted_qos=%s)", mid, qos_list)
        if self._subscribe_callback:
            self._subscribe_callback(self, to_python(userdata), mid, qos_list)

    def _on_unsubscribe(self, mosq, userdata, mid):
        if self._logger:
            self._logger.debug("UNSUB: (mid=%d)", mid)
        if self._unsubscribe_callback:
            self._unsubscribe_callback(self, to_python(userdata), mid)

    def _on_publish(self, mosq, userdata, mid):
        if self._logger:
            self._logger.debug("PUB: (mid=%d)", mid)
        if self._publish_callback:
            self._publish_callback(self, to_python(userdata), mid)

    def _on_message(self, mosq, userdata, msg):
        msg = MQTTMessage.from_c(msg)
        if self._logger:
            self._logger.debug("RECV: %s", msg)
        if self._message_callback:
            self._message_callback(self, to_python(userdata), msg)
        else:
            if not self._handlers:
                return
            userdata = to_python(userdata)
            for handler in self._handlers.find(msg.topic):
                try:
                    handler(self, userdata, msg)
                except Exception as e:
                    self._logger.exception(e)

    def _on_log(self, mosq, userdata, level, msg):
        if self._log_callback:
            self._log_callback(self, to_python(userdata), LogLevel(level), msg.decode())
