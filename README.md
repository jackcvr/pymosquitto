# PyMosquitto

Lightweight Python MQTT client wrapping libmosquitto C library via ctypes.

**Development in progress**:

TODO:

- tests
- benchmarks

## Dependencies

- python3.8+
- libmosquitto-dev

## Installation

- TODO

## Usage

examples/pymo_sub.py

```python
from pymosquitto import MQTTClient

from . import config as c

with MQTTClient() as client:

    @client.topic_handler(c.TOPIC)
    def _(client, userdata, msg):
        print(msg.topic, repr(msg.payload))

    client.connect_async(c.HOST, c.PORT)
    client.subscribe(c.TOPIC, c.QOS)
    client.loop_forever()

```

See more in the `examples/` and `benchmarks/` directories.

## License

MIT
