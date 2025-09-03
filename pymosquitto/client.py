import threading
import ctypes as C

from .base import (
    Mosquitto,
    MosquittoError,
    ErrorCode,
    AutoOSError,
)
from pymosquitto.bindings import call, MQTTMessage
from .constants import LogLevel, ConnackCode


class UserCallback:
    def __set_name__(self, owner, name):
        if not name.startswith("on_"):
            raise ValueError(f"Bad callback name: {name}")
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
        self._handlers = None
        self._set_default_callbacks()
        # user callbacks
        self._connect_callback = None
        self._disconnect_callback = None
        self._subscribe_callback = None
        self._unsubscribe_callback = None
        self._publish_callback = None
        self._message_callback = None
        self._log_callback = None

    on_connect = UserCallback()
    on_disconnect = UserCallback()
    on_subscribe = UserCallback()
    on_unsubscribe = UserCallback()
    on_publish = UserCallback()
    on_message = UserCallback()
    on_log = UserCallback()

    def _call(self, func, *args, use_errno=False):
        if self._logger:
            self._logger.debug(
                "C call: %s%s",
                func.__name__,
                (self._c_mosq_p,) + args,
            )
        super()._call(func, *args, use_errno=use_errno)

    def _set_default_callbacks(self):
        self.connect_callback_set(self._on_connect)
        self.disconnect_callback_set(self._on_disconnect)
        self.subscribe_callback_set(self._on_subscribe)
        self.unsubscribe_callback_set(self._on_unsubscribe)
        self.publish_callback_set(self._on_publish)
        self.message_callback_set(self._on_message)
        self.log_callback_set(self._on_log)

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
            _, err = call(libc.signal, sig, _stop)
            if err != 0:
                raise AutoOSError(err)

        super().loop_forever(timeout)

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
        if self._connect_callback:
            self._connect_callback(self, userdata, ConnackCode(rc))

    def _on_disconnect(self, mosq, userdata, rc):
        if self._disconnect_callback:
            self._disconnect_callback(self, userdata, rc)

    def _on_subscribe(self, mosq, userdata, mid, qos_count, granted_qos):
        if self._subscribe_callback:
            self._subscribe_callback(self, userdata, mid, qos_count, granted_qos)

    def _on_unsubscribe(self, mosq, userdata, mid):
        if self._unsubscribe_callback:
            self._unsubscribe_callback(self, userdata, mid)

    def _on_publish(self, mosq, userdata, mid):
        if self._publish_callback:
            self._publish_callback(self, userdata, mid)

    def _on_message(self, mosq, userdata, msg):
        msg = MQTTMessage.from_cmessage(msg)
        if self._message_callback:
            self._message_callback(self, userdata, msg)
        else:
            if not self._handlers:
                return
            _userdata = None
            for handler in self._handlers.find(msg.topic):
                _userdata = _userdata or userdata
                try:
                    handler(self, userdata, msg)
                except Exception as e:
                    self._logger.exception(e)

    def _on_log(self, mosq, userdata, level, msg):
        if self._log_callback:
            self._log_callback(self, userdata, LogLevel(level), msg.decode())
        elif self._logger:
            self._logger.debug("MOSQ/%s %s", LogLevel(level).name, msg.decode())
