# PyMosquitto

A lightweight Python MQTT client implemented as a thin wrapper around libmosquitto.

It provides an efficient synchronous client (`client.Client`) and two variants of asynchronous clients:

- `aio.AsyncClient` - async interface to libmosquitto loop running in its own thread.
It's a little bit faster, supposedly more reliable, but consumes a little bit more memory.
- `aio.TrueAsyncClient` - manages all events in asyncio loop by utilizing `mosquitto_loop_read, mosquitto_loop_write, mosquitto_loop_misc` functions.


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

*The memory plots exclude the Python interpreter overhead (~10.2 MB).

![benchmark-results](./results.png)

Losers excluded:

![benchmark-results-fast](./results_fast.png)

**benchmark.csv**

```text
Module;Time;RSS
pymosq;0:04.20;18144
pymosq_async;0:07.36;25604
pymosq_true_async;0:10.01;24896
paho;0:08.94;23472
gmqtt;0:04.40;24768
mqttools;0:06.20;27664
aiomqtt;0:54.12;577624
amqtt;1:04.37;745276
```


## License

MIT
