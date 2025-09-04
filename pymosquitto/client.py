import ctypes as C

from pymosquitto.bindings import call, MQTTMessage, MosquittoError

from .base import Mosquitto, topic_matches_sub
from .constants import LogLevel, ConnackCode, ErrorCode


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
        self._handlers = {}  # dict[str, func]
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
            self._logger.debug("CALL: %s%s", func.__name__, (self._c_mosq_p,) + args)
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
            call(libc.signal, sig, _stop, use_errno=True)

        super().loop_forever(timeout)

    def on_topic(self, topic, func=None):
        if func is None:

            def decorator(func):
                self.on_topic(topic, func)
                return func

            return decorator

        self._handlers[topic] = func
        return None

    def on_topic_remove(self, topic):
        del self._handlers[topic]

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
            self._subscribe_callback(
                self,
                userdata,
                mid,
                qos_count,
                [granted_qos[i] for i in range(qos_count)],
            )

    def _on_unsubscribe(self, mosq, userdata, mid):
        if self._unsubscribe_callback:
            self._unsubscribe_callback(self, userdata, mid)

    def _on_publish(self, mosq, userdata, mid):
        if self._publish_callback:
            self._publish_callback(self, userdata, mid)

    def _on_message(self, mosq, userdata, msg):
        msg = MQTTMessage(msg)
        if self._logger:
            self._logger.debug("RECV: %s", msg)
        if self._message_callback:
            self._message_callback(self, userdata, msg)
        else:
            if not self._handlers:
                return
            for sub, func in self._handlers.items():
                if not topic_matches_sub(sub, msg.topic):
                    continue
                try:
                    func(self, userdata, msg)
                except Exception as e:
                    self._logger.exception(e)

    def _on_log(self, mosq, userdata, level, msg):
        if self._log_callback:
            self._log_callback(self, userdata, LogLevel(level), msg.decode())
        elif self._logger:
            self._logger.debug("MOSQ/%s %s", LogLevel(level).name, msg.decode())
