import signal
import typing as t
import queue

from pymosquitto import helpers as h

_signal_handlers: dict[int, t.Any] = {}


def test_topic_matches_sub():
    assert h.topic_matches_sub("a/b/#", "a/b/c")
    assert not h.topic_matches_sub("a/b/#", "a/a")


def test_router():
    _res = []

    def abc(res):
        res.append("abc")

    router = h.Router()
    router.set_topic_callback("a/b/c", abc)

    @router.on_topic("c/b/a")
    def cba(res):
        res.append("cba")

    router.run("a/b/c", _res)
    assert _res == ["abc"]
    router.run("c/b/a", _res)
    assert _res == ["abc", "cba"]


def test_csignal():
    q = queue.Queue()

    def handler(*args):
        q.put_nowait(args)

    assert not h.csignal(signal.SIGHUP, handler)
    signal.raise_signal(signal.SIGHUP)
    assert q.get(timeout=1) == (signal.SIGHUP,)
