import logging
import asyncio

import pytest

from pymosquitto.constants import ConnackCode
from pymosquitto.aio import AsyncClient, TrueAsyncClient

CLIENT_CLASSES = [AsyncClient, TrueAsyncClient]


@pytest.fixture(scope="session")
def client_factory(token):
    def _factory(cls):
        client = cls(logger=logging.getLogger())
        client.mosq.username_pw_set(token, "")
        return client

    return _factory


@pytest.mark.asyncio
@pytest.mark.parametrize("cls", CLIENT_CLASSES)
async def test_pub_sub(cls, client_factory, host, port):
    count = 3

    async with client_factory(cls) as client:
        await client.connect(host, port)
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
async def test_multi_connect(cls, client_factory, host, port):
    async with client_factory(cls) as client:
        task = client.loop.create_task(client.connect(host, port))
        rc1 = await client.connect(host, port)
        rc2 = await task
        assert rc1 == rc2 == ConnackCode.ACCEPTED
