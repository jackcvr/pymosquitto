import os
import ctypes as C
from ctypes.util import find_library


def load_library(name, use_errno=True):
    path = find_library(name)
    if path is None:
        return None
    return C.CDLL(path, use_errno=use_errno)


def call(func, *args, use_errno=False):
    if use_errno:
        C.set_errno(0)
    res = func(*args)
    if use_errno:
        errno = C.get_errno()
        if errno != 0:
            raise OSError(errno, os.strerror(errno))
    return res
