import ctypes as C

from pymosquitto.bindings import call, MosquittoError

from .base import Mosquitto, topic_matches_sub
from .constants import ErrorCode

SENTINEL = object()


class Client(Mosquitto):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._handlers = {}  # dict[str, func]
        self._set_default_callbacks()

    def _set_default_callbacks(self):
        super()._set_default_callbacks()
        self.on_message = self._on_message

    def _on_message(self, mosq, userdata, msg):
        if self._logger:
            self._logger.debug("RECV: %s", msg)
        for func in self.topic_handlers(msg.topic):
            func(self, self.userdata, msg)

    def topic_handlers(self, topic):
        for sub, func in self._handlers.items():
            if topic_matches_sub(sub, topic):
                yield func

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
                self._logger.debug(
                    "Caught signal: %d/%s", signum, signal.Signals(signum).name
                )
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

        if func is None:
            if topic in self._handlers:
                del self._handlers[topic]
        else:
            self._handlers[topic] = func
        return None
