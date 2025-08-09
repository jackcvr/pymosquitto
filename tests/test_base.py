import threading

import pytest
from pymosquitto import base
from pymosquitto.base import MosquittoError


def _offload(func, *args, **kwargs):
    t = threading.Thread(target=func, args=args, kwargs=kwargs)
    t.start()
    return t


def test_strerror():
    msg = base.strerror(base.ErrorCode.NOMEM)
    assert msg == "Out of memory."


def test_connack_string():
    msg = base.connack_string(base.ConnackCode.REFUSED_NOT_AUTHORIZED)
    assert msg == "Connection Refused: not authorised."


def test_reason_string():
    msg = base.reason_string(base.ReasonCode.BANNED)
    assert msg == "Banned"


def test_init_and_destroy():
    client = base.Mosquitto()
    fin = client._finalizer
    assert fin.alive
    del client
    assert not fin.alive


def test_connect():
    done = threading.Event()

    def _on_disconnect(client, userdata, rc):
        print("DSFDSF", rc)
        done.set()

    client = base.Mosquitto()
    client.disconnect_callback_set(_on_disconnect)

    with pytest.raises(MosquittoError) as e:
        client.connect("localhost")
    # time.sleep(1)
    print("ERR", e.value)
    assert e.value.code == base.ErrorCode.ERRNO  # FIX IT
