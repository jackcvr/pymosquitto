import logging

import paho.mqtt.client as mqtt

from . import config as c

logging.basicConfig(level=logging.INFO)


def on_connect(client, userdata, flags, rc, props):
    logging.info("Connected with result code: %s", rc)
    client.subscribe(c.TOPIC)


def on_message(client, userdata, msg):
    logging.info("RECV %s: %s", msg.topic, msg.payload)


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message
client.connect_async(c.HOST, c.PORT, 60)
client.loop_forever()
