import pytest

from pymosquitto.utils import TopicMatcher


def test_topic_matcher_find():
    topics = TopicMatcher()
    topics["test"] = 1
    topics["test/#"] = 2
    topics["chest"] = 3
    assert list(topics.find("test")) == [1, 2]
    assert list(topics.find("test/two")) == [2]
    assert list(topics.find("chest")) == [3]


def test_topic_matcher_get():
    topics = TopicMatcher()
    topics["test"] = 1
    topics["test/#"] = 2
    assert topics["test"] == 1
    assert topics["test/#"] == 2


def test_topic_matcher_del():
    topics = TopicMatcher()
    topics["test"] = 1
    assert topics["test"] == 1
    del topics["test"]
    with pytest.raises(KeyError):
        _ = topics["test"]
