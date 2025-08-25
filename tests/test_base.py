import pytest

from pymosquitto import base
from pymosquitto.constants import ErrorCode, ConnackCode, ReasonCode


def test_strerror():
    msg = base.strerror(ErrorCode.NOMEM)
    assert msg == "Out of memory."


def test_connack_string():
    msg = base.connack_string(ConnackCode.REFUSED_NOT_AUTHORIZED)
    assert msg == "Connection Refused: not authorised."


def test_reason_string():
    msg = base.reason_string(ReasonCode.BANNED)
    assert msg == "Banned"


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
