import errno

import pytest

from pymosquitto.constants import LIBMOSQ_MIN_MAJOR_VERSION
from pymosquitto import cutils as cu


def test_os_error():
    with pytest.raises(OSError) as e:
        raise cu.os_error(2)
    assert e.value.errno == errno.ENOENT


def test_check_libmosq_version():
    with pytest.raises(RuntimeError) as e:
        cu.check_libmosq_version((1, 0, 0))
    assert (
        str(e.value) == f"libmosquitto version {LIBMOSQ_MIN_MAJOR_VERSION}+ is required"
    )
