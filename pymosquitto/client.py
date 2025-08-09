import threading

from .base import Mosquitto, to_python, connack_string, MQTTMessage, MosquittoError

MOSQ_ERR_NO_CONN = 4


class CallbackSetter:
    def __set_name__(self, owner, name):
        self.callback_name = f"_{name[3:]}_callback"

    def __get__(self, obj, objtype=None):
        def decorator(func):
            setattr(obj, self.callback_name, func)
            return func

        decorator.__name__ = f"{self.callback_name}_decorator"
        return decorator

    def __set__(self, obj, func):
        setattr(obj, self.callback_name, func)


class MQTTClient(Mosquitto):
    DEFAULT_PORT = 1883
    DEFAULT_KEEPALIVE = 60

    def __init__(self, *args, logger=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = logger
        self._topics = {}
        self._handlers = None
        self._cond = threading.Condition()
        self._is_connected = False
        self._set_lib_callbacks()
        # user callbacks
        self._connect_callback = None
        self._disconnect_callback = None
        self._subscribe_callback = None
        self._unsubscribe_callback = None
        self._publish_callback = None
        self._message_callback = None

    on_connect = CallbackSetter()
    on_disconnect = CallbackSetter()
    on_subscribe = CallbackSetter()
    on_unsubscribe = CallbackSetter()
    on_publish = CallbackSetter()
    on_message = CallbackSetter()

    @property
    def is_connected(self):
        return self._is_connected

    def _call(self, lib_func, *args):
        if self._logger:
            self._logger.debug(
                "C call: %s%s",
                lib_func.__name__,
                (self._mosq,) + args,
            )
        super()._call(lib_func, *args)

    def _set_lib_callbacks(self):
        self.connect_callback_set(self._on_connect)
        self.disconnect_callback_set(self._on_disconnect)
        self.subscribe_callback_set(self._on_subscribe)
        self.unsubscribe_callback_set(self._on_unsubscribe)
        self.publish_callback_set(self._on_publish)
        self.message_callback_set(self._on_message)

    def connect(self, host, port=DEFAULT_PORT, keepalive=DEFAULT_KEEPALIVE):
        super().connect(host, port, keepalive)

    def connect_async(self, host, port=DEFAULT_PORT, keepalive=DEFAULT_KEEPALIVE):
        super().connect_async(host, port, keepalive)

    def wait_until_connected(self, timeout=None):
        with self._cond:
            return self._cond.wait_for(lambda: self._is_connected, timeout=timeout)

    def loop_forever(self, timeout=-1, max_packets=1):
        import signal

        def stop(*_):
            try:
                self.disconnect()
            except MosquittoError as e:
                if e.code != MOSQ_ERR_NO_CONN:
                    raise e from None
            else:
                import sys

                sys.exit(0)

        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, stop)

        super().loop_forever()

    def subscribe_lazy(self, topic, qos=0):
        with self._cond:
            self._topics[topic] = qos
            if self._is_connected:
                self.subscribe(topic, qos)

    def add_topic_handler(self, topic, func):
        if self._handlers is None:
            from .utils import TopicMatcher

            self._handlers = TopicMatcher()
        self._handlers[topic] = func

    def remove_topic_handler(self, topic):
        del self._handlers[topic]

    def on_topic(self, topic):
        def decorator(func):
            self.add_topic_handler(topic, func)
            return func

        return decorator

    # -----------
    # CALLBACKS
    # -----------

    def _on_connect(self, mosq, userdata, rc):
        info = connack_string(rc)
        with self._cond:
            if rc == 0:
                self._is_connected = True
                if self._logger:
                    self._logger.info("Connected: %s", info)
                for topic, qos in self._topics.items():
                    self.subscribe(topic, qos)
            else:
                self._is_connected = False
                if self._logger:
                    self._logger.warning("Connection failed: %s", info)
            if self._connect_callback:
                self._connect_callback(self, to_python(userdata), rc)
            self._cond.notify_all()

    def _on_disconnect(self, mosq, userdata, rc):
        with self._cond:
            self._is_connected = False
            if self._logger:
                if rc == 0:
                    self._logger.info("Disconnected")
                else:
                    self._logger.warning("Disconnected: %s", connack_string(rc))
            if self._disconnect_callback:
                self._disconnect_callback(self, to_python(userdata), rc)
            self._cond.notify_all()

    def _on_subscribe(self, mosq, userdata, mid, qos_count, granted_qos):
        qos_list = [granted_qos[i] for i in range(qos_count)]
        if self._logger:
            self._logger.debug("SUB: (mid=%d granted_qos=%s)", mid, qos_list)
        if self._subscribe_callback:
            self._subscribe_callback(self, to_python(userdata), mid, qos_list)

    def _on_unsubscribe(self, mosq, userdata, mid):
        if self._logger:
            self._logger.debug("UNSUB: (mid=%d)", mid)
        if self._unsubscribe_callback:
            self._unsubscribe_callback(self, to_python(userdata), mid)

    def _on_publish(self, mosq, userdata, mid):
        if self._logger:
            self._logger.debug("PUB: (mid=%d)", mid)
        if self._publish_callback:
            self._publish_callback(self, to_python(userdata), mid)

    def _on_message(self, mosq, userdata, msg):
        msg = MQTTMessage.from_c(msg)
        if self._logger:
            self._logger.debug("RECV: %s", msg)
        if self._message_callback:
            self._message_callback(self, to_python(userdata), msg)
        else:
            if not self._handlers:
                return
            userdata = to_python(userdata)
            for handler in self._handlers.find(msg.topic):
                try:
                    handler(self, userdata, msg)
                except Exception as e:
                    self._logger.exception(e)
