# PyMosquitto

A lightweight Python MQTT client implemented as a thin wrapper around libmosquitto.

It provides an efficient synchronous client (`client.Client`) and two variants of asynchronous clients:

- `aio.AsyncClient` - async interface to libmosquitto loop running in its own thread. It's faster, but consumes a little bit more memory.
- `aio.TrueAsyncClient` - manages all events in asyncio loop by utilizing `mosquitto_loop_{read,write,misc}` functions.


## Dependencies

- python3.8+
- libmosquitto1


## Installation

- pip install pymosquitto


## TODO

- add v5 support


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

Receiving one million messages with QoS 0.

*The memory plots exclude the Python interpreter overhead (~8.7 MB).

![benchmark-results](./results.png)

Losers excluded:

![benchmark-results-fast](./results_fast.png)

**benchmark.csv**

```text
Module;Time;RSS
pymosq;0:04.51;18432
pymosq_async;0:07.43;25424
pymosq_true_async;0:09.28;25000
paho;0:08.74;23400
gmqtt;0:04.16;24688
mqttools;0:06.17;27804
aiomqtt;0:52.38;578184
amqtt;1:01.23;767248
```


## License

MIT
