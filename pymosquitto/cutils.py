import os
from pymosquitto.constants import LIBMOSQ_MIN_MAJOR_VERSION


def os_error(code: int):
    return OSError(code, os.strerror(code))


def check_libmosq_version(version: tuple):
    if version[0] < LIBMOSQ_MIN_MAJOR_VERSION:
        raise RuntimeError(
            f"libmosquitto version {LIBMOSQ_MIN_MAJOR_VERSION}+ is required"
        )
