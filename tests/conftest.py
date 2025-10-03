from types import SimpleNamespace
import logging
import threading

import pytest

from pymosquitto.constants import ConnackCode
from pymosquitto.client import Client

import constants as c

default_logger = logging.getLogger()


@pytest.fixture(scope="session")
def client_factory():
    def _factory(logger=default_logger, userdata=SimpleNamespace(), **kwargs):
        client = Client(logger=logger, userdata=userdata, **kwargs)
        if c.USERNAME or c.PASSWORD:
            client.username_pw_set(c.USERNAME, c.PASSWORD)
        return client

    return _factory


@pytest.fixture
def client(client_factory):
    def _on_connect(client, userdata, rc):
        if rc != ConnackCode.ACCEPTED:
            raise RuntimeError(f"Client connection error: {rc.value}/{rc.name}")
        is_connected.set()

    client = client_factory()
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
