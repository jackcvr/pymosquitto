import paho.mqtt.client as mqtt

from . import config as c


def on_connect(client, userdata, flags, rc, props):
    if rc != 0:
        raise RuntimeError("Connection failed")
    for i in range(c.LIMIT):
        client.publish(c.TOPIC, i, qos=c.QOS)


def on_publish(client, userdata, mid, rc, props):
    global count
    count += 1
    if count == c.LIMIT:
        client.disconnect()


count = 0
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_publish = on_publish
client.connect_async(c.HOST, c.PORT, 60)
client.loop_forever()
