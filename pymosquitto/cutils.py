import ctypes as C
from ctypes.util import find_library


def load_library(name, use_errno=True):
    path = find_library(name)
    if path is None:
        return None
    return C.CDLL(path, use_errno=use_errno)


def call(func, *args):
    C.set_errno(0)
    ret = func(*args)
    return ret, C.get_errno()
