import time
import types

import paho.mqtt.client as mqtt

from . import config as c


def on_connect(client, userdata, flags, rc, props):
    client.subscribe(c.TOPIC, qos=c.QOS)


def on_message(client, userdata, msg):
    if userdata.count == 0:
        userdata.start_time = time.monotonic()
    userdata.count += 1
    if userdata.count == c.LIMIT:
        print(f"Done[qos={c.QOS}]:", time.monotonic() - userdata.start_time)
        client.disconnect()


data = types.SimpleNamespace(count=0, start_time=None)
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, userdata=data)
client.on_connect = on_connect
client.on_message = on_message
client.connect_async(c.HOST, c.PORT, 60)
client.loop_forever()
