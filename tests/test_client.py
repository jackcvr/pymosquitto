import logging
import threading
import os
from types import SimpleNamespace

import pytest

from pymosquitto.base import MosquittoError
from pymosquitto.client import MQTTClient
from pymosquitto import constants as c

HOST = "mqtt.flespi.io"
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
        userdata.is_connected.set()

    client = client_factory()
    is_connected = threading.Event()
    client.userdata.is_connected = is_connected
    client.on_connect = _on_connect
    client.connect(HOST)
    client.loop_start()
    assert is_connected.wait(1)
    client.userdata.__dict__.clear()
    try:
        yield client
    finally:
        try:
            client.disconnect()
        except MosquittoError as e:
            if e.code != c.ErrorCode.NO_CONN:
                raise e


def test_pub_sub(client):
    pass
