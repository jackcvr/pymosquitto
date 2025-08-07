import threading
import time
import types

from pymosquitto import MQTTClient

from . import config as c

is_done = threading.Event()
data = types.SimpleNamespace(count=0, start_time=None)

with MQTTClient(userdata=data) as client:

    @client.on_publish_handler
    def _(client, userdata, msg):
        userdata.count += 1
        if userdata.count == c.LIMIT:
            print(f"Done[qos={c.QOS}]:", time.monotonic() - userdata.start_time)
            is_done.set()

    client.connect_async(c.HOST, c.PORT)
    client.loop_start()

    client.wait_connection()
    data.start_time = time.monotonic()
    for i in range(c.LIMIT):
        client.publish(c.TOPIC, str(i), qos=c.QOS)
    is_done.wait()
