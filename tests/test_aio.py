import asyncio

import pytest

from pymosquitto.constants import ConnackCode
from pymosquitto.aio import AsyncClient, TrueAsyncClient

import constants as c

CLIENT_CLASSES = [AsyncClient, TrueAsyncClient]


@pytest.fixture(scope="session")
def client_factory():
    def _factory(cls):
        client = cls()
        if c.USERNAME or c.PASSWORD:
            client.mosq.username_pw_set(c.USERNAME, c.PASSWORD)
        return client

    return _factory


@pytest.mark.asyncio
@pytest.mark.parametrize("cls", CLIENT_CLASSES)
async def test_pub_sub(cls, client_factory):
    count = 3

    async with client_factory(cls) as client:
        await client.connect(c.HOST, c.PORT)
        await client.subscribe("test", qos=1)

        for i in range(count):
            await client.publish("test", str(i), qos=1)

        async def recv():
            messages = []
            async for msg in client.read_messages():
                messages.append(msg)
                if len(messages) == count:
                    break
            return messages

        async with asyncio.timeout(1):
            messages = await client.loop.create_task(recv())
        assert [msg.payload for msg in messages] == [b"0", b"1", b"2"]


@pytest.mark.asyncio
@pytest.mark.parametrize("cls", CLIENT_CLASSES)
async def test_multi_connect(cls, client_factory):
    async with client_factory(cls) as client:
        task = client.loop.create_task(client.connect(c.HOST, c.PORT))
        rc1 = await client.connect(c.HOST, c.PORT)
        rc2 = await task
        assert rc1 == rc2 == ConnackCode.ACCEPTED
