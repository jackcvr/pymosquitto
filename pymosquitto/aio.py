import asyncio
import weakref
from collections import deque
import abc

from pymosquitto.bindings import connack_string
from pymosquitto.client import Client, LibMosqError
from pymosquitto.constants import ConnackCode, ErrorCode


class BaseAsyncClient(abc.ABC):
    def __init__(self, *args, loop=None, **kwargs):
        self._mosq = Client(*args, **kwargs)
        self._loop = loop or asyncio.get_event_loop()
        self._conn_future = None
        self._disconn_future = None
        self._pub_mids = weakref.WeakValueDictionary()
        self._sub_mids = weakref.WeakValueDictionary()
        self._unsub_mids = weakref.WeakValueDictionary()
        self._messages = asyncio.Queue()
        self._put_msg = self._messages.put_nowait
        self._get_msg = self._messages.get
        self._set_default_callbacks()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        try:
            await self.disconnect()
        except LibMosqError as e:
            if e.code != ErrorCode.NO_CONN:
                raise e from None

    @property
    def mosq(self):
        return self._mosq

    @property
    def loop(self):
        return self._loop

    @property
    def messages(self):
        return self._messages

    def _set_default_callbacks(self):
        self._mosq.on_connect = self._on_connect
        self._mosq.on_disconnect = self._on_disconnect
        self._mosq.on_subscribe = self._on_subscribe
        self._mosq.on_unsubscribe = self._on_unsubscribe
        self._mosq.on_publish = self._on_publish
        self._mosq.on_message = self._on_message

    def _on_connect(self, mosq, userdata, rc):
        self._conn_future.set_result(rc)

    def _on_disconnect(self, mosq, userdata, rc):
        self._put_msg(None)
        if self._disconn_future:
            self._disconn_future.set_result(rc)

    def _on_publish(self, mosq, userdata, mid):
        self._pub_mids[mid].set_result(mid)

    def _on_subscribe(self, mosq, userdata, mid, qos_count, granted_qos):
        self._sub_mids[mid].set_result(granted_qos)

    def _on_unsubscribe(self, mosq, userdata, mid):
        self._unsub_mids[mid].set_result(mid)

    def _on_message(self, mosq, userdata, msg):
        self._put_msg(msg)

    async def connect(self, *args, **kwargs):
        if self._conn_future:
            return await self._conn_future
        self._conn_future = self._loop.create_future()
        self._mosq.connect(*args, **kwargs)
        rc = await self._conn_future
        self._conn_future = None
        if rc != ConnackCode.ACCEPTED:
            raise ConnectionError(connack_string(rc))
        return rc

    async def disconnect(self):
        if self._disconn_future:
            return await self._disconn_future
        self._disconn_future = self._loop.create_future()
        self._mosq.disconnect()
        rc = await self._disconn_future
        self._disconn_future = None
        return rc

    async def publish(self, *args, **kwargs):
        mid = self._mosq.publish(*args, **kwargs)
        await self._wait_future(self._pub_mids, mid)
        return mid

    async def subscribe(self, *args, **kwargs):
        mid = self._mosq.subscribe(*args, **kwargs)
        await self._wait_future(self._sub_mids, mid)
        return mid

    async def unsubscribe(self, *args, **kwargs):
        mid = self._mosq.unsubscribe(*args, **kwargs)
        await self._wait_future(self._unsub_mids, mid)
        return mid

    async def _wait_future(self, mapping, mid):
        fut = self._loop.create_future()
        mapping[mid] = fut
        await fut

    async def read_messages(self):
        while True:
            msg = await self._get_msg()
            if msg is None:
                return
            yield msg


class AsyncClient(BaseAsyncClient):
    def __init__(self, *args, buffer_size=2000, flush_interval=0.05, **kwargs):
        super().__init__(*args, **kwargs)
        self._buffer_size = buffer_size
        self._flush_interval = flush_interval
        self._buffer = deque()
        self._buffer_full = asyncio.Event()
        self._flush_task = None

    async def __aenter__(self):
        self._mosq.loop_start()
        return await super().__aenter__()

    def _on_connect(self, mosq, userdata, rc):
        self._loop.call_soon_threadsafe(super()._on_connect, mosq, userdata, rc)
        if not self._flush_task:
            self._flush_task = self._loop.call_soon_threadsafe(
                self._loop.create_task, self._flush_messages()
            )

    def _on_disconnect(self, mosq, userdata, rc):
        self._loop.call_soon_threadsafe(super()._on_disconnect, mosq, userdata, rc)
        if self._flush_task:
            self._flush_task.cancel()
            self._flush_task = None

    def _on_publish(self, mosq, userdata, mid):
        self._loop.call_soon_threadsafe(super()._on_publish, mosq, userdata, mid)

    def _on_subscribe(self, mosq, userdata, mid, qos_count, granted_qos):
        self._loop.call_soon_threadsafe(
            super()._on_subscribe, mosq, userdata, mid, qos_count, granted_qos
        )

    def _on_unsubscribe(self, mosq, userdata, mid):
        self._loop.call_soon_threadsafe(super()._on_unsubscribe, mosq, userdata, mid)

    def _on_message(self, mosq, userdata, msg):
        self._buffer.append(msg)
        if len(self._buffer) >= self._buffer_size:
            self._loop.call_soon_threadsafe(self._buffer_full.set)

    async def _flush_messages(self):
        try:
            while True:
                while self._buffer:
                    msg = self._buffer.popleft()
                    self._put_msg(msg)
                # either wait for the buffer to fill up or timeout after flush_interval
                task = self._loop.create_task(self._buffer_full.wait())
                done, pending = await asyncio.wait({task}, timeout=self._flush_interval)
                if done:
                    self._buffer_full.clear()
                else:
                    task.cancel()
        except asyncio.CancelledError:
            pass


class TrueAsyncClient(BaseAsyncClient):
    MISC_SLEEP_TIME = 1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fd = None
        self._misc_task = None

    def _on_disconnect(self, mosq, userdata, rc):
        fd = self._mosq.socket()
        if fd:
            self._loop.remove_reader(fd)
            self._loop.remove_writer(fd)
        if self._misc_task and not self._misc_task.done():
            self._misc_task.cancel()
            self._misc_task = None
        self._fd = None
        super()._on_disconnect(mosq, userdata, rc)

    def _on_publish(self, mosq, userdata, mid):
        super()._on_publish(mosq, userdata, mid)
        self._check_writable()

    def _on_subscribe(self, mosq, userdata, mid, qos_count, granted_qos):
        super()._on_subscribe(mosq, userdata, mid, qos_count, granted_qos)
        self._check_writable()

    def _on_unsubscribe(self, mosq, userdata, mid):
        super()._on_unsubscribe(mosq, userdata, mid)
        self._check_writable()

    async def connect(self, *args, **kwargs):
        task = self._loop.create_task(super().connect(*args, **kwargs))
        self._loop.call_later(0, self._add_reader)
        rc = await task
        self._misc_task = self._loop.create_task(self._misc_loop())
        return rc

    def _add_reader(self):
        self._fd = self._mosq.socket()
        if self._fd:
            self._loop.add_reader(self._fd, self._loop_read)
        else:
            raise RuntimeError("No socket")

    def _loop_read(self):
        try:
            self._mosq.loop_read(1)
        except BlockingIOError:
            pass

    async def _misc_loop(self):
        while True:
            try:
                self._check_writable()
                self._mosq.loop_misc()
                await asyncio.sleep(self.MISC_SLEEP_TIME)
            except asyncio.CancelledError:
                break

    def _check_writable(self):
        if self._fd and self._mosq.want_write():
            self._loop.add_writer(self._fd, self._loop_write)

    def _loop_write(self):
        self._mosq.loop_write()
        self._loop.remove_writer(self._fd)
