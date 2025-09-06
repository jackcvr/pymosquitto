import asyncio

from pymosquitto.bindings import MosquittoError, connack_string, MQTTMessage
from pymosquitto.client import Mosquitto
from pymosquitto.constants import ConnackCode, ErrorCode, LogLevel


class AsyncMQTTClient:
    MISC_SLEEP_TIME = 1

    def __init__(self, *args, logger=None, loop=None, **kwargs):
        self._logger = logger
        self._loop = loop or asyncio.get_event_loop()
        self._client = Mosquitto(*args, **kwargs)
        self._misc_task = None
        self._cond = asyncio.Condition()
        self._conn_rc = None
        self._disconn_rc = None
        self._pub_mids = {}
        self._sub_mids = {}
        self._unsub_mids = {}
        self._messages = asyncio.Queue()
        self._set_callbacks()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        try:
            await self.disconnect()
        except MosquittoError as e:
            if e.code != ErrorCode.NO_CONN:
                raise e from None

    def __getattr__(self, name):
        return getattr(self._client, name)

    @property
    def client(self):
        return self._client

    @property
    def loop(self):
        return self._loop

    @property
    def messages(self):
        return self._messages

    def _set_callbacks(self):
        self._client.connect_callback_set(self._on_connect)
        self._client.disconnect_callback_set(self._on_disconnect)
        self._client.subscribe_callback_set(self._on_subscribe)
        self._client.unsubscribe_callback_set(self._on_unsubscribe)
        self._client.publish_callback_set(self._on_publish)
        self._client.message_callback_set(self._on_message)
        self._client.log_callback_set(self._on_log)

    def _on_connect(self, mosq, userdata, rc):
        self._setattr("_conn_rc", rc)

    def _on_disconnect(self, mosq, userdata, rc):
        fd = self._client.socket()
        if fd:
            self._loop.remove_reader(fd)
            self._loop.remove_writer(fd)
        if self._misc_task and not self._misc_task.done():
            self._misc_task.cancel()
            self._misc_task = None
        self._messages.put_nowait(None)
        self._setattr("_disconn_rc", rc)

    def _setattr(self, attr, value):
        async def notify():
            async with self._cond:
                setattr(self, attr, value)
                self._cond.notify_all()

        self._loop.create_task(notify())

    def _on_publish(self, mosq, userdata, mid):
        self._resolve_future(self._pub_mids, mid, mid)

    def _on_subscribe(self, mosq, userdata, mid, qos_count, granted_qos):
        self._resolve_future(
            self._sub_mids,
            mid,
            (mid, qos_count, [granted_qos[i] for i in range(qos_count)]),
        )

    def _on_unsubscribe(self, mosq, userdata, mid):
        self._resolve_future(self._unsub_mids, mid, mid)

    @staticmethod
    def _resolve_future(mapping, mid, value):
        fut = mapping.get(mid)
        if fut is not None and not fut.done():
            fut.set_result(value)

    def _on_message(self, mosq, userdata, msg):
        self._messages.put_nowait(MQTTMessage.from_struct(msg))

    def _on_log(self, mosq, userdata, level, msg):
        if self._logger:
            self._logger.debug("MOSQ/%s %s", LogLevel(level).name, msg.decode())

    async def connect(self, *args, **kwargs):
        async with self._cond:
            self._conn_rc = None
            self._client.connect(*args, **kwargs)
            fd = self._client.socket()
            if fd:
                self._loop.add_reader(fd, self._loop_read)
            else:
                raise RuntimeError("No socket")
            self._check_writable()

            await self._cond.wait_for(lambda: self._conn_rc is not None)
            if self._conn_rc != ConnackCode.ACCEPTED:
                self._loop.remove_reader(fd)
                raise ConnectionError(connack_string(self._conn_rc))

            self._misc_task = self._loop.create_task(self.misc_loop())
            return self._conn_rc

    def _loop_read(self):
        try:
            self._client.loop_read()
        except BlockingIOError:
            pass
        finally:
            self._check_writable()

    def _check_writable(self):
        if self._client.want_write():
            fd = self._client.socket()
            if fd:

                def cb():
                    self._client.loop_write()
                    self._loop.remove_writer(fd)

                self._loop.add_writer(fd, cb)

    async def misc_loop(self):
        while True:
            try:
                self._client.loop_misc()
                await asyncio.sleep(self.MISC_SLEEP_TIME)
            except asyncio.CancelledError:
                break

    async def disconnect(self):
        async with self._cond:
            self._disconn_rc = None
            self._client.disconnect()
            self._check_writable()
            await self._cond.wait_for(lambda: self._disconn_rc is not None)
            return self._disconn_rc

    async def publish(self, *args, **kwargs):
        mid = self._client.publish(*args, **kwargs)
        self._pub_mids[mid] = self._loop.create_future()
        self._check_writable()
        await self._await_future(self._pub_mids, mid)
        return mid

    async def subscribe(self, *args, **kwargs):
        mid = self._client.subscribe(*args, **kwargs)
        self._sub_mids[mid] = self._loop.create_future()
        self._check_writable()
        await self._await_future(self._sub_mids, mid)
        return mid

    async def unsubscribe(self, *args, **kwargs):
        mid = self._client.unsubscribe(*args, **kwargs)
        self._unsub_mids[mid] = self._loop.create_future()
        self._check_writable()
        await self._await_future(self._unsub_mids, mid)
        return mid

    @staticmethod
    async def _await_future(mapping, mid):
        try:
            await mapping[mid]
        finally:
            del mapping[mid]

    async def recv_messages(self):
        while True:
            msg = await self._messages.get()
            if msg is None:
                break
            yield msg
