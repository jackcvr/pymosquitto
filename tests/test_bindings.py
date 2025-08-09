import ctypes as C

import pytest
from pymosquitto.bindings import lib

EXCLUDE = (
    "mosquitto_lib_init",
    "mosquitto_new",
    "mosquitto_lib_cleanup",
)


def _strerror(rc):
    return lib.mosquitto_strerror(rc).decode()


@pytest.fixture(scope="module")
def mosq():
    rc = lib.mosquitto_lib_init()
    if rc != 0:
        raise Exception(f"mosquitto_lib_init error: {_strerror(rc)}")
    try:
        obj = lib.mosquitto_new(None, True, None)
        rc = C.get_errno()
        if rc != 0:
            raise Exception(f"mosquitto_new error: {_strerror(rc)}")
        yield obj
    finally:
        lib.mosquitto_lib_cleanup()


lib_functions = [
    getattr(lib, name)
    for name in dir(lib)
    if name.startswith("mosquitto_") and name not in EXCLUDE
]


@pytest.mark.parametrize("func", lib_functions)
def test_functions(func, mosq):
    args = [t() for t in func.argtypes]
    if args and func.argtypes[0] == C.c_void_p:
        args[0] = mosq
    func(*args)  # expecting no segfaults
