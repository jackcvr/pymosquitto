# PyMosquitto

Python ctypes binding for libmosquitto C library.

**Stage**: in active development.

## Usage

```python
from pymosquitto import MQTTClient


with MQTTClient() as mqtt:
    mqtt.connect("localhost", 1883)
    mqtt.subscribe("topic", 0)
    mqtt.loop_forever()
```

## License

MIT
