from pymosquitto import MQTTClient

from . import config as c

with MQTTClient() as client:

    @client.on_connect_handler
    def _(client, userdata, rc):
        print("Connected:", rc)

    @client.topic_handler(c.TOPIC)
    def _(client, userdata, msg):
        print(msg.topic, repr(msg.payload))

    client.connect_async(c.HOST, c.PORT)
    client.subscribe(c.TOPIC, c.QOS)
    client.loop_forever()
