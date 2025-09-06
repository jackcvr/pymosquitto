import asyncio

import mqttools

from benchmarks import config as c


async def main():
    async with mqttools.Client(c.HOST, c.PORT) as client:
        await client.subscribe(c.TOPIC, c.QOS)
        count = 0
        while True:
            msg = await client.messages.get()
            if msg is None:
                break
            count += 1
            if count == c.LIMIT:
                print("DONE")
                break


asyncio.run(main())
