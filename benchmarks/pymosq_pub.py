import time

from pymosquitto.client import MQTTClient

from . import config as c

logger = None


def sleep():
    pass


if c.INTERVAL:
    import logging

    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger()

    def sleep():
        time.sleep(c.INTERVAL)


def on_publish(client, userdata, mid):
    global count
    count += 1
    if count == c.LIMIT:
        print("DONE")
        time.sleep(1)
        client.disconnect()


count = 0
client = MQTTClient(logger=logger)
client.on_publish = on_publish
client.connect(c.HOST, c.PORT)
for i in range(c.LIMIT):
    sleep()
    client.publish(c.TOPIC, str(i), qos=c.QOS)
client.loop_forever()
