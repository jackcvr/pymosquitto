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
from pymosquitto import Client


def on_message(client, userdata, msg):
    print(msg)


client = Client()
client.on_connect = lambda *_: client.subscribe("#", 1)
client.on_message = on_message
client.connect_async("localhost", 1883)
client.loop_forever()
```

Async client example:

```python
import asyncio

from pymosquitto.aio import AsyncClient


async def main():
    async with AsyncClient() as client:
        await client.connect("localhost", 1883)
        await client.subscribe("#", 1)
        async for msg in client.read_messages():
            print(msg)


asyncio.run(main())
```

Check out more examples in `tests` directory.


## Benchmarks

Receiving 1 million messages with QoS 0.

*The memory plots exclude the Python interpreter overhead (~10.2 MB).

![benchmark-results](./results.png)

Losers excluded:

![benchmark-results-fast](./results_fast.png)

**benchmark.csv**

```text
Module;Time;RSS
pymosq;0:04.23;18552
pymosq_async;0:09.39;25004
paho;0:08.84;23544
gmqtt;0:03.97;24780
mqttools;0:06.49;27944
aiomqtt;0:53.48;578296
amqtt;1:02.94;756716
```


## License

MIT
