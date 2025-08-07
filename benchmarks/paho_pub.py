import time
import types
import threading

import paho.mqtt.client as mqtt

from . import config as c


def on_connect(client, userdata, flags, rc, props):
    if rc == 0:
        is_connected.set()
    else:
        raise RuntimeError("Connection failed")


def on_publish(client, userdata, mid, rc, props):
    userdata.count += 1
    if userdata.count == c.LIMIT:
        print(f"Done[qos={c.QOS}]:", time.monotonic() - userdata.start_time)
        is_done.set()


data = types.SimpleNamespace(count=0, start_time=None)
is_connected = threading.Event()
is_done = threading.Event()

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, userdata=data)
client.on_connect = on_connect
client.on_publish = on_publish
client.connect_async(c.HOST, c.PORT, 60)
client.loop_start()

is_connected.wait()
data.start_time = time.monotonic()
for i in range(c.LIMIT):
    client.publish(c.TOPIC, i, qos=c.QOS)
is_done.wait()
