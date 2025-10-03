import signal
import queue

import pytest

from pymosquitto import helpers as h


def test_topic_matches_sub():
    assert h.topic_matches_sub("a/b/#", "a/b/c")
    assert not h.topic_matches_sub("a/b/#", "a/a")


@pytest.mark.parametrize(
    "sub,topic",
    [
        ("foo/bar", "foo/bar"),
        ("foo/+", "foo/bar"),
        ("foo/+/baz", "foo/bar/baz"),
        ("foo/+/#", "foo/bar/baz"),
        ("A/B/+/#", "A/B/B/C"),
        ("#", "foo/bar/baz"),
        ("#", "/foo/bar"),
        ("/#", "/foo/bar"),
        ("$SYS/bar", "$SYS/bar"),
    ],
)
def test_matching(sub, topic):
    assert h.topic_matches_sub(sub, topic)


@pytest.mark.parametrize(
    "sub,topic",
    [
        ("test/6/#", "test/3"),
        ("foo/bar", "foo"),
        ("foo/+", "foo/bar/baz"),
        ("foo/+/baz", "foo/bar/bar"),
        ("foo/+/#", "fo2/bar/baz"),
        ("/#", "foo/bar"),
        ("#", "$SYS/bar"),
        ("$BOB/bar", "$SYS/bar"),
    ],
)
def test_not_matching(sub, topic):
    assert not h.topic_matches_sub(sub, topic)


def test_topic_matcher():
    def a():
        pass

    def ab():
        pass

    matcher = h.TopicMatcher()
    matcher.set_topic_callback("a/#", a)
    matcher.set_topic_callback("a/b/#", ab)

    @matcher.on_topic("c/b/a")
    def cba():
        pass

    assert list(matcher.find("a/b/d")) == [a, ab]
    assert list(matcher.find("c/b/a")) == [cba]


def test_csignal():
    q = queue.Queue()

    def handler(*args):
        q.put_nowait(args)

    assert not h.csignal(signal.SIGHUP, handler)
    signal.raise_signal(signal.SIGHUP)
    assert q.get(timeout=1) == (signal.SIGHUP,)
