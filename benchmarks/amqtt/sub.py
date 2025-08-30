import asyncio

from amqtt.client import MQTTClient

from benchmarks import config as c


async def main():
    count = 0
    client = MQTTClient()
    await client.connect(f"mqtt://{c.HOST}:{c.PORT}/")
    await client.subscribe([(c.TOPIC, c.QOS)])
    while count < c.LIMIT:
        await client.deliver_message()
        # count += 1
        # if count % 10 == 0:
        #     print(count)
    print("DONE")
    await client.disconnect()


asyncio.run(main())
