import ctypes as C
import typing as t

from .bindings import call, libmosq, bind

SIGNAL_WRAPPER = C.CFUNCTYPE(None, C.c_int)

libc = None
_signal_handlers: dict[int, t.Any] = {}


def topic_matches_sub(sub: str, topic: str) -> bool:
    res = C.c_bool(False)
    call(
        libmosq.mosquitto_topic_matches_sub, sub.encode(), topic.encode(), C.byref(res)
    )
    return res.value


class Router:
    def __init__(self) -> None:
        self._handlers: dict[str, t.Callable] = {}

    def run(self, topic: str, *args: t.Any, **kwargs: t.Any) -> None:
        for callback in self.topic_callbacks(topic):
            callback(*args, **kwargs)

    def topic_callbacks(self, topic: str) -> t.Iterator[t.Callable]:
        for sub, func in self._handlers.items():
            if topic_matches_sub(sub, topic):
                yield func

    def set_topic_callback(self, topic: str, callback: t.Callable) -> None:
        if callback is None:
            if topic in self._handlers:
                del self._handlers[topic]
        else:
            self._handlers[topic] = callback

    def on_topic(self, topic: str) -> t.Callable:
        def decorator(func: t.Callable) -> t.Callable:
            self.set_topic_callback(topic, func)
            return func

        return decorator


# this function might be helpful if you call `run_forever` in the main thread
def csignal(signum: int, func: t.Callable) -> t.Callable:
    global libc

    libc = libc or C.CDLL(None)
    libsignal = bind(SIGNAL_WRAPPER, libc.signal, C.c_int, SIGNAL_WRAPPER)

    func = SIGNAL_WRAPPER(func)
    _signal_handlers[signum] = func
    return call(libsignal, signum, func, use_errno=True)
