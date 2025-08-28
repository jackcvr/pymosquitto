# PyMosquitto

Lightweight Python MQTT client implemented as a simple wrapper over libmosquitto.


## Dependencies

- python3.8+
- libmosquitto1


## Installation

- pip install pymosquitto


## Usage

```python
from pymosquitto.client import MQTTClient


def on_message(client, userdata, msg):
    print(msg)


client = MQTTClient()
client.on_connect = lambda *_: client.subscribe("#", 1)
client.on_message = on_message
client.connect_async("localhost", 1883)
client.loop_forever()
```


## Benchmarks

Receiving 1 million messages with QoS 0.

*The Python interpreter overhead(10.420 MB) has been excluded from the memory plot.

![benchmark-results](./results.png)

**PyMosquitto**

```text
Elapsed (wall clock) time (h:mm:ss or m:ss): 0:05.87
Maximum resident set size (kbytes): 17668
```

**Paho-MQTT**

```text
Elapsed (wall clock) time (h:mm:ss or m:ss): 0:09.66
Maximum resident set size (kbytes): 23480
```


## License

MIT
