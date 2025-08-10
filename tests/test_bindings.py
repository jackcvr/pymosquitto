import ctypes as C

import pytest
from pymosquitto.bindings import libmosq

EXCLUDE = (
    "mosquitto_lib_init",
    "mosquitto_lib_cleanup",
    "mosquitto_new",
    "mosquitto_destroy",
)


def _strerror(rc):
    return libmosq.mosquitto_strerror(rc).decode()


@pytest.fixture(scope="module")
def mosq():
    rc = libmosq.mosquitto_lib_init()
    if rc != 0:
        raise Exception(f"mosquitto_lib_init error: {_strerror(rc)}")
    obj = None
    try:
        C.set_errno(0)
        obj = libmosq.mosquitto_new(None, True, None)
        rc = C.get_errno()
        if rc != 0:
            raise Exception(f"mosquitto_new error: {_strerror(rc)}")
        yield obj
    finally:
        if obj:
            libmosq.mosquitto_destroy(obj)
        libmosq.mosquitto_lib_cleanup()


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
