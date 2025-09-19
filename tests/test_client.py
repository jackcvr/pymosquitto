import threading
import time
from types import SimpleNamespace

import pytest

from pymosquitto.client import Client, LibMosqError
from pymosquitto import constants as c


@pytest.fixture(scope="session")
def client_factory(token):
    def _factory(**kwargs):
        client = Client(**kwargs)
        client.username_pw_set(token, "")
        return client

    return _factory


@pytest.fixture(scope="module")
def client(client_factory, host, port):
    def _on_connect(client, userdata, rc):
        if rc != c.ConnackCode.ACCEPTED:
            raise RuntimeError(f"Client connection error: {rc.value}/{rc.name}")
        is_connected.set()

    client = client_factory(userdata=SimpleNamespace())
    is_connected = threading.Event()
    client.on_connect = _on_connect
    client.connect(host, port)
    client.loop_start()
    assert is_connected.wait(1)
    client.on_connect = None
    try:
        yield client
    finally:
        try:
            client.disconnect()
        except LibMosqError as e:
            if e.code != c.ErrorCode.NO_CONN:
                raise e


def test_del():
    is_del = False

    class MyClient(Client):
        def __del__(self):
            super().__del__()
            nonlocal is_del
            is_del = True

    client = MyClient()
    assert not is_del
    del client
    assert is_del


def test_userdata(client):
    data = client.userdata()
    client.user_data_set(None)
    assert client.userdata() is None
    client.user_data_set(data)
    assert client.userdata() is data


def test_unset_callbacks(client):
    def _on_message(client, userdata, message):
        is_recv.set()

    is_recv = threading.Event()
    client.on_publish = None
    client.on_message = _on_message
    client.subscribe("test", 1)
    client.publish("test", "123", qos=1)
    assert is_recv.wait(1)
    time.sleep(0.1)


def test_on_message(client):
    def _on_pub(client, userdata, mid):
        userdata.pub_mid = mid
        is_pub.set()

    def _on_sub(client, userdata, mid, count, qos):
        userdata.sub_mid = mid
        userdata.sub_count = count
        userdata.sub_qos = [qos[i] for i in range(count)]
        is_sub.set()

    def _on_message(client, userdata, msg):
        userdata.msg = msg
        is_recv.set()

    is_sub = threading.Event()
    is_pub = threading.Event()
    is_recv = threading.Event()
    client.on_publish = _on_pub
    client.on_subscribe = _on_sub
    client.on_message = _on_message
    client.subscribe("test", 1)

    assert is_sub.wait(1)
    udata = client.userdata()
    assert udata.sub_mid
    assert udata.sub_count == 1
    assert udata.sub_qos == [1]

    client.publish("test", "123", qos=1)
    assert is_pub.wait(1)
    assert udata.pub_mid

    assert is_recv.wait(1)
    assert udata.msg.payload == b"123"
