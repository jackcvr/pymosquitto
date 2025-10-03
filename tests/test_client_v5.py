import threading

import pytest

from pymosquitto.constants import ConnackCode, ProtocolVersion, MQTT5PropertyID
from pymosquitto.client import PropertyFactory

import constants as c


@pytest.fixture
def client(client_factory):
    def _on_connect(client, userdata, rc):
        if rc != ConnackCode.ACCEPTED:
            raise RuntimeError(f"Client connection error: {rc.value}/{rc.name}")
        is_connected.set()

    client = client_factory(protocol=ProtocolVersion.MQTTv5)
    is_connected = threading.Event()
    client.on_connect = _on_connect
    client.connect(c.HOST, c.PORT)
    client.loop_start()
    assert is_connected.wait(1)
    client.on_connect = None
    try:
        yield client
    finally:
        client.disconnect(strict=False)


def test_on_connect_v5(client_factory):
    def _on_connect(client, userdata, rc, flags, props):
        if rc != ConnackCode.ACCEPTED:
            raise RuntimeError(f"Client connection error: {rc.value}/{rc.name}")
        is_connected.set()

    is_connected = threading.Event()
    client = client_factory(protocol=ProtocolVersion.MQTTv5)
    client.on_connect_v5 = _on_connect

    client.connect(c.HOST, c.PORT)
    client.loop_start()
    assert is_connected.wait(1)
    client.disconnect()


def test_on_callbacks_v5(client):
    def _on_pub(client, userdata, mid, props):
        userdata.pub_mid = mid
        is_pub.set()

    def _on_sub(client, userdata, mid, count, granted_qos, props):
        userdata.sub_mid = mid
        userdata.sub_count = count
        userdata.sub_granted_qos = granted_qos
        is_sub.set()

    def _on_message(client, userdata, msg, props):
        assert (
            props.find(MQTT5PropertyID.MESSAGE_EXPIRY_INTERVAL).value.i32 == test_value
        )
        userdata.msg = msg
        is_recv.set()

    is_sub = threading.Event()
    is_pub = threading.Event()
    is_recv = threading.Event()
    client.on_publish_v5 = _on_pub
    client.on_subscribe_v5 = _on_sub
    client.on_message_v5 = _on_message
    client.subscribe("test", 1)

    assert is_sub.wait(1)
    udata = client.userdata()
    assert udata.sub_mid
    assert udata.sub_count == 1
    assert udata.sub_granted_qos == [1]

    test_value = 69
    prop = PropertyFactory.INT32(MQTT5PropertyID.MESSAGE_EXPIRY_INTERVAL, test_value)
    client.publish("test", "123", qos=1, props=prop)
    assert is_pub.wait(1)
    assert udata.pub_mid

    assert is_recv.wait(1)
    assert udata.msg.payload == b"123"
