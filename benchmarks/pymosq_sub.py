from pymosquitto.client import MQTTClient

from . import config as c

logger = None

if c.INTERVAL:
    import logging

    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger()


def on_message(client, userdata, msg):
    global count
    count += 1
    if count == c.LIMIT:
        print("DONE")
        client.disconnect()


count = 0
client = MQTTClient(logger=logger)
client.on_connect = lambda *_: client.subscribe(c.TOPIC, c.QOS)
client.on_message = on_message
client.on_log = lambda *args: print(args)
client.connect_async(c.HOST, c.PORT)
client.loop_forever()
