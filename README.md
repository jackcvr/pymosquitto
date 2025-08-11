# PyMosquitto

Lightweight Python MQTT client wrapping libmosquitto C library via ctypes.

**Development in progress**:

TODO:

- rewrite TopicMatcher on C
- add more benchmarks and graphs
- create documentation


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
client.subscribe("#", 1)
client.connect_async("localhost", 1883)
client.loop_forever()
```


## Benchmarks

Receiving 1 million messages with QoS 0.

**PyMosquitto**
```bash
Elapsed (wall clock) time (h:mm:ss or m:ss): 0:04.82
Maximum resident set size (kbytes): 13704
```

**Paho-MQTT**

```bash
Elapsed (wall clock) time (h:mm:ss or m:ss): 0:11.19
Maximum resident set size (kbytes): 19804
```

**aMQTT**
```bash
Elapsed (wall clock) time (h:mm:ss or m:ss): 1:02.55
Maximum resident set size (kbytes): 28200

```


## License

MIT
