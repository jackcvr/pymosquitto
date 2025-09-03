import ctypes as C
import errno
from ctypes.util import find_library

import pytest
from pymosquitto.bindings import libmosq, strerror, connack_string, reason_string, call
from pymosquitto.constants import ErrorCode, ConnackCode, ReasonCode

libc = C.CDLL(find_library("c"), use_errno=True)


EXCLUDE = (
    "mosquitto_lib_init",
    "mosquitto_lib_cleanup",
    "mosquitto_new",
    "mosquitto_destroy",
)


@pytest.fixture(scope="module")
def mosq():
    rc = libmosq.mosquitto_lib_init()
    if rc != 0:
        raise Exception(f"mosquitto_lib_init error: {strerror(rc)}")
    obj = None
    try:
        C.set_errno(0)
        obj = libmosq.mosquitto_new(None, True, None)
        rc = C.get_errno()
        if rc != 0:
            raise Exception(f"mosquitto_new error: {strerror(rc)}")
        yield obj
    finally:
        if obj:
            libmosq.mosquitto_destroy(obj)
        libmosq.mosquitto_lib_cleanup()


def test_call():
    ptr = C.cast(C.pointer(C.c_int()), C.c_void_p)
    _, err = call(libc.read, ptr)
    assert err == errno.EBADF


def test_strerror():
    msg = strerror(ErrorCode.NOMEM)
    assert msg == "Out of memory."


def test_connack_string():
    msg = connack_string(ConnackCode.REFUSED_NOT_AUTHORIZED)
    assert msg == "Connection Refused: not authorised."


def test_reason_string():
    msg = reason_string(ReasonCode.BANNED)
    assert msg == "Banned"


lib_functions = [
    getattr(libmosq, name)
    for name in dir(libmosq)
    if name.startswith("mosquitto_") and name not in EXCLUDE
]


@pytest.mark.parametrize("func", lib_functions)
def test_segfaults(func, mosq):
    args = [t() for t in func.argtypes]
    if args and func.argtypes[0] == C.c_void_p:
        args[0] = mosq
    func(*args)  # expecting no segfaults
