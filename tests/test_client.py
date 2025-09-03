import logging
import threading
import os
from types import SimpleNamespace

import pytest

from pymosquitto.base import MosquittoError
from pymosquitto.client import MQTTClient
from pymosquitto import constants as c

HOST = os.getenv("MQTT_HOST", "mqtt.flespi.io")
PORT = int(os.getenv("MQTT_PORT", "1883"))
TOKEN = os.getenv("FLESPI_TOKEN")


def client_factory():
    client = MQTTClient(userdata=SimpleNamespace(), logger=logging.getLogger())
    client.username_pw_set(TOKEN)
    return client


@pytest.fixture(scope="module")
def client():
    def _on_connect(client, userdata, rc):
        if rc != c.ConnackCode.ACCEPTED:
            raise RuntimeError(f"Client connection error: {rc}")
        is_connected.set()

    client = client_factory()
    is_connected = threading.Event()
    client.on_connect = _on_connect
    client.connect(HOST, PORT)
    client.loop_start()
    assert is_connected.wait(1)
    client.on_connect = None
    try:
        yield client
    finally:
        try:
            client.disconnect()
        except MosquittoError as e:
            if e.code != c.ErrorCode.NO_CONN:
                raise e


@pytest.fixture(autouse=True)
def cleanup(client):
    try:
        yield
    finally:
        client.on_publish = None
        client.on_subscribe = None
        client.on_message = None


def test_on_message(client):
    def _on_pub(client, userdata, mid):
        userdata.pub_mid = mid
        is_pub.set()

    def _on_sub(client, userdata, mid, count, qos):
        userdata.sub_mid = mid
        userdata.sub_count = count
        userdata.sub_qos = qos
        is_sub.set()

    def _on_message(client, userdata, message):
        userdata.message = message
        is_recv.set()

    is_sub = threading.Event()
    is_pub = threading.Event()
    is_recv = threading.Event()
    client.on_publish = _on_pub
    client.on_subscribe = _on_sub
    client.on_message = _on_message
    client.subscribe("test", 1)

    assert is_sub.wait(1)
    assert client.userdata.sub_mid
    assert client.userdata.sub_count == 1
    assert client.userdata.sub_qos == [1]

    client.publish("test", "123", qos=1)
    assert is_pub.wait(1)
    assert client.userdata.pub_mid

    assert is_recv.wait(1)
    assert client.userdata.message.payload == b"123"


def test_on_topic(client):
    def _on_sub(client, userdata, mid, count, qos):
        is_sub.set()

    def _on_topic(client, userdata, message):
        userdata.message = message
        is_recv.set()

    is_sub = threading.Event()
    is_recv = threading.Event()
    client.on_subscribe = _on_sub
    client.add_topic_handler("test/me/#", _on_topic)
    client.subscribe("test/#", 1)

    assert is_sub.wait(1)
    client.publish("test/notme", "123", qos=1)
    client.publish("test/me/one", "333", qos=1)

    assert is_recv.wait(1)
    assert client.userdata.message.payload == b"333"
