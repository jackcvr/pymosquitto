import ctypes as C
import errno
from ctypes.util import find_library

import pytest
from pymosquitto.bindings import libmosq, strerror, connack_string, reason_string, call
from pymosquitto.constants import ErrorCode, ConnackCode, ReasonCode

libc = C.CDLL(find_library("c"), use_errno=True)


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


def test_call():
    text = b"test"
    ret = call(libc.printf, text)
    assert ret == len(text)


def test_call_error():
    with pytest.raises(OSError) as e:
        call(libc.read, C.byref(C.c_int()), use_errno=True)
    assert e.value.errno == errno.EBADF


def test_strerror():
    msg = strerror(ErrorCode.NOMEM)
    assert msg == "Out of memory."


def test_connack_string():
    msg = connack_string(ConnackCode.REFUSED_NOT_AUTHORIZED)
    assert msg == "Connection Refused: not authorised."


def test_reason_string():
    msg = reason_string(ReasonCode.BANNED)
    assert msg == "Banned"
