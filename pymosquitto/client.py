import ctypes as C

from pymosquitto.bindings import call, MQTTMessage, MosquittoError

from .base import Mosquitto, topic_matches_sub
from .constants import LogLevel, ConnackCode, ErrorCode

SENTINEL = object()


class UserCallback:
    def __set_name__(self, owner, name):
        self._name = f"_{name}_callback"

    def __get__(self, obj, objtype=None):
        return getattr(obj, self._name, None)

    def __set__(self, obj, func):
        setattr(obj, self._name, func)


class MQTTClient(Mosquitto):
    def __init__(self, *args, logger=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = logger
        self._handlers = {}  # dict[str, func]
        self._set_default_callbacks()

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

    def _on_connect(self, mosq, userdata, rc):
        if self.on_connect:
            self.on_connect(self, userdata, ConnackCode(rc))

    def _on_disconnect(self, mosq, userdata, rc):
        if self.on_disconnect:
            self.on_disconnect(self, userdata, rc)

    def _on_subscribe(self, mosq, userdata, mid, qos_count, granted_qos):
        if self.on_subscribe:
            self.on_subscribe(
                self,
                userdata,
                mid,
                qos_count,
                [granted_qos[i] for i in range(qos_count)],
            )

    def _on_unsubscribe(self, mosq, userdata, mid):
        if self.on_unsubscribe:
            self.on_unsubscribe(self, userdata, mid)

    def _on_publish(self, mosq, userdata, mid):
        if self.on_publish:
            self.on_publish(self, userdata, mid)

    def _on_message(self, mosq, userdata, msg):
        msg = MQTTMessage.from_struct(msg)
        if self._logger:
            self._logger.debug("RECV: %s", msg)
        if self.on_message:
            self.on_message(self, userdata, msg)
        else:
            for func in self._topic_handlers(msg.topic):
                try:
                    func(self, self.userdata, msg)
                except Exception as e:
                    self._logger.exception(e)

    def _topic_handlers(self, topic):
        for sub, func in self._handlers.items():
            if topic_matches_sub(sub, topic):
                yield func

    def _on_log(self, mosq, userdata, level, msg):
        if self.on_log:
            self.on_log(self, userdata, LogLevel(level), msg.decode())
        elif self._logger:
            self._logger.debug("MOSQ/%s %s", LogLevel(level).name, msg.decode())

    def disconnect(self, strict=True):
        try:
            super().disconnect()
        except MosquittoError as e:
            if strict or e.code != ErrorCode.NO_CONN:
                raise e from None

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
            self.disconnect(strict=False)

        for sig in (signal.SIGALRM, signal.SIGTERM, signal.SIGINT):
            call(libc.signal, sig, _stop, use_errno=True)

        super().loop_forever(timeout)

    def on_topic(self, topic, func=SENTINEL):
        if func is SENTINEL:

            def decorator(func):
                self.on_topic(topic, func)
                return func

            return decorator

        if func is not None:
            self._handlers[topic] = func
        elif topic in self._handlers:
            del self._handlers[topic]
        return None
