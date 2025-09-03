import errno

import pytest

from pymosquitto import base


def test_auto_oserror():
    with pytest.raises(OSError) as e:
        raise base.AutoOSError(22)
    assert e.value.errno == errno.EINVAL


def test_init_and_destroy():
    client = base.Mosquitto()
    fin = client._finalizer
    assert fin.alive
    del client
    assert not fin.alive


def test_connect_refused():
    client = base.Mosquitto()
    with pytest.raises(ConnectionRefusedError):
        client.connect("localhost")


def test_connect_async_refused():
    client = base.Mosquitto()
    with pytest.raises(ConnectionRefusedError):
        client.connect_async("localhost")
    with pytest.raises(ConnectionRefusedError):
        client.reconnect_async()
