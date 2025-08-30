import asyncio

from gmqtt import Client as MQTTClient

from benchmarks import config as c


def on_connect(client, flags, rc, properties):
    client.subscribe(c.TOPIC, qos=c.QOS)


def on_message(client, topic, payload, qos, properties):
    global count
    count += 1
    if count == c.LIMIT:
        print("DONE")
        stop.set()


count = 0
stop = asyncio.Event()


async def main(host):
    client = MQTTClient("gmqtt")
    client.on_connect = on_connect
    client.on_message = on_message
    await client.connect(host)
    await stop.wait()
    await client.disconnect()


asyncio.run(main(c.HOST))
