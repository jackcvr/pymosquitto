import time

import paho.mqtt.client as mqtt

from . import config as c


def sleep():
    pass


if c.INTERVAL:

    def sleep():
        time.sleep(c.INTERVAL)


def on_publish(client, userdata, mid, rc, props):
    global count
    count += 1
    if count == c.LIMIT:
        print("DONE")
        time.sleep(1)
        client.disconnect()


count = 0
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_publish = on_publish
client.connect(c.HOST, c.PORT, 60)
for i in range(c.LIMIT):
    sleep()
    client.publish(c.TOPIC, str(i), qos=c.QOS)
client.loop_forever()
