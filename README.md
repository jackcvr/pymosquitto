# PyMosquitto

~~Reincarnation of~~ Python ctypes binding for libmosquitto C library.

Because memory matters.

**Development in progress**

## Usage

benchmarks/pymo_sub.py

```python
import logging

from pymosquitto import MQTTClient

from . import config as c

logging.basicConfig(level=logging.DEBUG)

with MQTTClient() as mqtt:
    mqtt.connect_async(c.HOST, c.PORT)
    mqtt.subscribe(c.TOPIC, c.QOS)

    @mqtt.topic_handler(c.TOPIC)
    def test_handler(client, msg):
        print(msg.topic, repr(msg.payload))

    mqtt.loop_forever()
```

See more examples in bechmarks/ directory.

## License

MIT
