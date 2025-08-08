import threading

from pymosquitto.client import MQTTClient

from . import config as c

logger = None


def sleep():
    pass


if c.INTERVAL:
    import logging
    import time

    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger()

    def sleep():
        time.sleep(c.INTERVAL)


def on_publish(client, userdata, mid):
    global count
    count += 1
    if count == c.LIMIT:
        client.disconnect()


def publish(client):
    client.wait_until_connected()
    for i in range(c.LIMIT):
        sleep()
        client.publish(c.TOPIC, str(i), qos=c.QOS)


count = 0
client = MQTTClient(logger=logger)
t = threading.Thread(target=publish, args=(client,))
t.start()
client.on_publish = on_publish
client.connect_async(c.HOST, c.PORT)
client.loop_forever()
