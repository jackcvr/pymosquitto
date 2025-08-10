import pytest

from pymosquitto.client import MQTTClient


def test_subscribe_lazy():
    client = MQTTClient()
    client.subscribe_lazy("test1")
    client.subscribe_lazy("test2")
    assert client._topics == {"test1": 0, "test2": 0}


@pytest.mark.parametrize(
    "setter_name",
    [
        "on_connect",
        "on_disconnect",
        "on_subscribe",
        "on_unsubscribe",
        "on_publish",
        "on_message",
    ],
)
def test_callbacks_set(setter_name):
    callback_name = f"_{setter_name[3:]}_callback"

    def cb1():
        pass

    client = MQTTClient()
    setattr(client, setter_name, cb1)
    assert getattr(client, callback_name) is cb1

    setter_decorator = getattr(client, setter_name)

    @setter_decorator
    def cb2():
        pass

    assert getattr(client, callback_name) is cb2
