import ctypes as C

from pymosquitto.bindings import libmosq, strerror, connack_string, reason_string
from pymosquitto.constants import ErrorCode, ConnackCode, ReasonCode


def test_init_and_cleanup():
    assert libmosq.mosquitto_lib_init() == 0
    mosq = None
    try:
        C.set_errno(0)
        mosq = libmosq.mosquitto_new(None, True, None)
        assert C.get_errno() == 0
    finally:
        if mosq:
            libmosq.mosquitto_destroy(mosq)
        libmosq.mosquitto_lib_cleanup()


def test_strerror():
    msg = strerror(ErrorCode.NOMEM)
    assert msg == "Out of memory."


def test_connack_string():
    msg = connack_string(ConnackCode.REFUSED_NOT_AUTHORIZED)
    assert msg == "Connection Refused: not authorised."


def test_reason_string():
    msg = reason_string(ReasonCode.BANNED)
    assert msg == "Banned"
