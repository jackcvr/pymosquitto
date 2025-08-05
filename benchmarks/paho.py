import logging

import paho.mqtt.client as mqtt


def on_connect(client, userdata, flags, rc, props):
    logging.info("Connected with result code: %s", rc)
    client.subscribe(TOPIC)


def on_message(client, userdata, msg):
    logging.info("RECV %s: %s", msg.topic, msg.payload)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    TOPIC = sys.argv[2]

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect_async(sys.argv[1], 1883, 60)
    client.loop_forever()
