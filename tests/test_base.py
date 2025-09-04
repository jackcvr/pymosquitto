from pymosquitto import base


def test_finalizer():
    client = base.Mosquitto()
    fin = client._finalizer
    assert fin.alive
    del client
    assert not fin.alive
