from types import SimpleNamespace
import logging
import asyncio

import pytest

from pymosquitto.aio import AsyncMQTTClient


@pytest.fixture(scope="session")
def client_factory(token):
    def _factory():
        client = AsyncMQTTClient(userdata=SimpleNamespace(), logger=logging.getLogger())
        client.username_pw_set(token)
        return client

    return _factory


@pytest.mark.asyncio
async def test_async_adapter(client_factory, host, port):
    count = 3

    async with client_factory() as client:
        await client.connect(host, port)
        await client.subscribe("test", qos=1)

        for i in range(count):
            await client.publish("test", str(i), qos=1)

        async def recv():
            messages = []
            async for msg in client.recv_messages():
                messages.append(msg)
                if len(messages) == count:
                    break
            return messages

        async with asyncio.timeout(1):
            messages = await client.loop.create_task(recv())
        assert [msg.payload for msg in messages] == [b"0", b"1", b"2"]
