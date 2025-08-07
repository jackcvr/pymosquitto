from pymosquitto import MQTTClient

from .config import HOST, PORT, TOPIC, QOS

with MQTTClient() as client:

    @client.topic_handler(TOPIC)
    def _(client, userdata, msg):
        print(msg.topic, repr(msg.payload))

    client.connect_async(HOST, PORT)
    client.subscribe(TOPIC, QOS)
    client.loop_forever()
