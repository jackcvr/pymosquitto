# PyMosquitto

Lightweight Python MQTT client wrapping libmosquitto C library via ctypes.

**Development in progress**:

TODO:

- add on log callback
- add more benchmarks and graphs

## Dependencies

- python3.8+
- libmosquitto1

## Installation

- TODO

## Usage

```python
from pymosquitto.client import MQTTClient


def on_message(client, userdata, msg):
    print(msg)


count = 0
client = MQTTClient()
client.on_message = on_message
client.subscribe_lazy("#", 1)
client.connect_async("localhost", 1883)
client.loop_forever()
```

See more in the `benchmarks/` directory.

## Benchmarks

Publishing and receiving 1 mil messages with QoS 0.

PyMosquitto | PUB

```bash
Elapsed (wall clock) time (h:mm:ss or m:ss):0:04.13
Maximum resident set size (kbytes): 169816
```

PyMosquitto | SUB
```bash
Elapsed (wall clock) time (h:mm:ss or m:ss): 0:04.31
Maximum resident set size (kbytes): 13464
```

Paho-MQTT | PUB
```bash
Elapsed (wall clock) time (h:mm:ss or m:ss): 0:23.50
Maximum resident set size (kbytes): 2145204
```

Paho-MQTT | SUB

```bash
Elapsed (wall clock) time (h:mm:ss or m:ss): 0:24.87
Maximum resident set size (kbytes): 19560
```

As a result pymosquitto:

- uses ~6MB less memory than PahoMQTT on IDLE
- ~6x times faster


## License

MIT
