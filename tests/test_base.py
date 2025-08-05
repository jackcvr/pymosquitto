import pytest

from pymosquitto import base


def test_init_and_destroy():
    client = base.Mosquitto()
    fin = client._finalizer
    assert fin.alive
    del client
    assert not fin.alive


def test_connect():
    client = base.Mosquitto()
    with pytest.raises(ConnectionRefusedError):
        client.connect("localhost")


def test_connect_async():
    client = base.Mosquitto()
    with pytest.raises(ConnectionRefusedError):
        client.connect_async("localhost")
    with pytest.raises(ConnectionRefusedError):
        client.reconnect_async()
