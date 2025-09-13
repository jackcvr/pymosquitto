import asyncio
import aiomqtt

from benchmarks import config as c


async def main():
    count = 0
    async with aiomqtt.Client(c.HOST) as client:
        await client.subscribe(c.TOPIC, c.QOS)
        async for _ in client.messages:
            count += 1
            if count == c.LIMIT:
                print("DONE")
                break


asyncio.run(main())
