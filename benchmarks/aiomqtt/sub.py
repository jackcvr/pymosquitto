import asyncio
import aiomqtt

from benchmarks import config as c


async def main():
    async with aiomqtt.Client(c.HOST) as client:
        await client.subscribe(c.TOPIC, c.QOS)
        async for _ in client.messages:
            global count
            count += 1
            if count == c.LIMIT:
                print("DONE")
                return


count = 0
asyncio.run(main())
