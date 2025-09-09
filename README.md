# PyMosquitto

A lightweight Python MQTT client implemented as a thin wrapper around libmosquitto.


## Dependencies

- python3.8+
- libmosquitto1


## Installation

- pip install pymosquitto


## TODO

- implement the remaining bindings


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

Async client example:

```python
import asyncio

from pymosquitto.aio import AsyncMQTTClient


async def main():
    async with AsyncMQTTClient() as client:
        await client.connect("localhost", 1883)
        await client.subscribe("#", 1)
        async for msg in client.read_messages():
            print(msg)


asyncio.run(main())
```

Check out more examples in `tests/test_client.py`.


## Benchmarks

Receiving 1 million messages with QoS 0.

*The memory plots exclude the Python interpreter overhead (~10.2 MB).

![benchmark-results](./results.png)

Losers excluded:

![benchmark-results-fast](./results_fast.png)

**benchmark.csv**

```text
Module;Time;RSS
pymosq;0:04.26;18316
pymosq_async;0:09.36;24852
paho;0:09.06;23556
gmqtt;0:04.33;25176
mqttools;0:06.72;28116
aiomqtt;0:53.69;578288
amqtt;1:06.86;736724
```


## License

MIT
