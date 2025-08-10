import ctypes as C
import errno

import pytest

from pymosquitto.cutils import call, load_library

libc = load_library("c")


def test_call_success():
    n = call(libc.printf, C.c_char_p(b""))
    assert n == 0


def test_call_error():
    n = call(libc.printf, C.c_char_p())
    assert n == -1


def test_call_errno():
    with pytest.raises(OSError) as e:
        call(libc.read, C.c_void_p(), use_errno=True)
    assert e.value.errno == errno.EFAULT
