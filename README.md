# PyMosquitto

A lightweight Python MQTT client implemented as a thin wrapper around libmosquitto.

It provides an efficient synchronous client (`client.Mosquitto`) and two variants of asynchronous clients:

- `aio.AsyncMosquitto` - async interface to libmosquitto loop running in its own thread. It's faster, but consumes a little bit more memory.
- `aio.TrueAsyncMosquitto` - manages all events in asyncio loop by utilizing `mosquitto_loop_{read,write,misc}` functions.


## Dependencies

- python3.8+
- libmosquitto1


## Installation

- pip install pymosquitto


## Usage

```python
from pymosquitto import Mosquitto


def on_message(client, userdata, msg):
    print(msg)


client = Mosquitto()
client.on_connect = lambda *_: client.subscribe("#", 1)
client.on_message = on_message
client.connect_async("localhost", 1883)
client.loop_forever()
```

Async client example:

```python
import asyncio

from pymosquitto.aio import AsyncMosquitto


async def main():
    async with AsyncMosquitto() as client:
        await client.connect("localhost", 1883)
        await client.subscribe("#", 1)
        async for msg in client.read_messages():
            print(msg)


asyncio.run(main())
```

Check out more examples in `tests` directory.


## Benchmarks

Receiving one million messages with QoS 0.

*The memory plots exclude the Python interpreter overhead (~10.3 MB).

![benchmark-results](./results.png)

Losers excluded:

![benchmark-results-fast](./results_fast.png)

**benchmark.csv**

```text
Module;Time;RSS
pymosq;0:04.84;18940
pymosq_async;0:08.06;25560
pymosq_true_async;0:10.78;25092
paho;0:09.07;23620
gmqtt;0:04.63;24740
mqttools;0:06.57;28068
aiomqtt;0:56.60;578380
amqtt;1:02.72;757084
```


## License

MIT
