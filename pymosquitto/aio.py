import asyncio
import weakref

from pymosquitto.bindings import MosquittoError, connack_string
from pymosquitto.client import Mosquitto
from pymosquitto.constants import ConnackCode, ErrorCode


class AsyncClient(Mosquitto):
    MISC_SLEEP_TIME = 1

    def __init__(self, *args, loop=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._loop = loop or asyncio.get_event_loop()
        self._fd = None
        self._misc_task = None
        self._cond = asyncio.Condition()
        self._conn_rc = None
        self._disconn_rc = None
        self._pub_mids = weakref.WeakValueDictionary()
        self._sub_mids = weakref.WeakValueDictionary()
        self._unsub_mids = weakref.WeakValueDictionary()
        self._messages = asyncio.Queue()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        try:
            await self.disconnect()
        except MosquittoError as e:
            if e.code != ErrorCode.NO_CONN:
                raise e from None

    @property
    def loop(self):
        return self._loop

    @property
    def messages(self):
        return self._messages

    def _set_default_callbacks(self):
        super()._set_default_callbacks()
        self.on_connect = self._on_connect
        self.on_disconnect = self._on_disconnect
        self.on_subscribe = self._on_subscribe
        self.on_unsubscribe = self._on_unsubscribe
        self.on_publish = self._on_publish
        self.on_message = self._on_message

    def _on_connect(self, mosq, userdata, rc):
        self._loop.create_task(self._setattr("_conn_rc", rc))

    def _on_disconnect(self, mosq, userdata, rc):
        fd = self.socket()
        if fd:
            self._loop.remove_reader(fd)
            self._loop.remove_writer(fd)
        if self._misc_task and not self._misc_task.done():
            self._misc_task.cancel()
            self._misc_task = None
        self._messages.put_nowait(None)
        self._loop.create_task(self._setattr("_disconn_rc", rc))
        self._fd = None

    def _on_publish(self, mosq, userdata, mid):
        self._resolve_future(self._pub_mids, mid, mid)

    def _on_subscribe(self, mosq, userdata, mid, qos_count, granted_qos):
        self._resolve_future(self._sub_mids, mid, granted_qos)

    def _on_unsubscribe(self, mosq, userdata, mid):
        self._resolve_future(self._unsub_mids, mid, mid)

    @staticmethod
    def _resolve_future(mapping, mid, value):
        fut = mapping.get(mid)
        if fut is not None and not fut.done():
            fut.set_result(value)

    def _on_message(self, mosq, userdata, msg):
        self._messages.put_nowait(msg)

    async def connect(self, *args, **kwargs):
        async with self._cond:
            self._conn_rc = None
            super().connect(*args, **kwargs)
            self._fd = self.socket()
            if self._fd:
                self._loop.add_reader(self._fd, self._loop_read)
            else:
                raise RuntimeError("No socket")

            await self._cond.wait_for(lambda: self._conn_rc is not None)
            if self._conn_rc != ConnackCode.ACCEPTED:
                self._loop.remove_reader(self._fd)
                raise ConnectionError(connack_string(self._conn_rc))

            self._misc_task = self._loop.create_task(self.misc_loop())
            return self._conn_rc

    async def disconnect(self):
        async with self._cond:
            self._disconn_rc = None
            super().disconnect()
            await self._cond.wait_for(lambda: self._disconn_rc is not None)
            return self._disconn_rc

    async def publish(self, *args, **kwargs):
        mid = super().publish(*args, **kwargs)
        fut = self._loop.create_future()
        self._pub_mids[mid] = fut
        await fut
        return mid

    async def subscribe(self, *args, **kwargs):
        mid = super().subscribe(*args, **kwargs)
        fut = self._loop.create_future()
        self._sub_mids[mid] = fut
        await fut
        return mid

    async def unsubscribe(self, *args, **kwargs):
        mid = super().unsubscribe(*args, **kwargs)
        fut = self._loop.create_future()
        self._unsub_mids[mid] = fut
        await fut
        return mid

    async def read_messages(self):
        while True:
            msg = await self._messages.get()
            if msg is None:
                return
            yield msg

    def _loop_read(self):
        try:
            self.loop_read()
        except BlockingIOError:
            pass
        finally:
            self._check_writable()

    def _check_writable(self):
        if self._fd and self.want_write():

            def cb():
                self.loop_write()
                self._loop.remove_writer(self._fd)

            self._loop.add_writer(self._fd, cb)

    async def misc_loop(self):
        while True:
            try:
                self._check_writable()
                self.loop_misc()
                await asyncio.sleep(self.MISC_SLEEP_TIME)
            except asyncio.CancelledError:
                break

    async def _setattr(self, attr, value):
        async with self._cond:
            setattr(self, attr, value)
            self._cond.notify_all()
