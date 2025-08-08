from pymosquitto.client import MQTTClient

from . import config as c


def on_message(client, userdata, msg):
    global count
    print("MSG", msg)
    count += 1
    if count == c.LIMIT:
        client.disconnect()


count = 0
client = MQTTClient()
client.on_message = on_message
client.subscribe_lazy(c.TOPIC, c.QOS)
client.connect_async(c.HOST, c.PORT)
client.loop_forever()
