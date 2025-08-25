import ctypes as C
import errno

from pymosquitto.cutils import call, load_library

libc = load_library("c")


def test_call():
    ptr = C.cast(C.pointer(C.c_int()), C.c_void_p)
    _, err = call(libc.read, ptr)
    assert err == errno.EBADF
