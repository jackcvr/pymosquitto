import os

import pytest

HOST = os.getenv("MQTT_HOST", "mqtt.flespi.io")
PORT = int(os.getenv("MQTT_PORT", "1883"))
TOKEN = os.getenv("FLESPI_TOKEN")


@pytest.fixture(scope="session")
def host():
    return HOST


@pytest.fixture(scope="session")
def port():
    return PORT


@pytest.fixture(scope="session")
def token():
    return TOKEN
