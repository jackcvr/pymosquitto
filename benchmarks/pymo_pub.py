import time
import threading
from pymosquitto import MQTTClient

from . import config as c

TOPIC = "test-topic"
MESSAGE = "test-message"


def publisher(client, topic, msg):
    client.wait_connection()
    time.sleep(1)
    while client.is_connected:
        client.publish(topic, msg)
        time.sleep(10)


with MQTTClient() as mqtt:
    t = threading.Thread(target=publisher, args=(mqtt, TOPIC, MESSAGE), daemon=True)
    t.start()
    mqtt.connect_async(c.HOST, c.PORT)
    mqtt.loop_forever()
    t.join()
