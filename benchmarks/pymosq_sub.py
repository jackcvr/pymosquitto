from pymosquitto import MQTTClient

from . import config as c

count = 0

with MQTTClient() as client:

    @client.on_message_handler
    def _(client, userdata, msg):
        global count
        count += 1
        if count == c.LIMIT:
            client.disconnect()

    client.connect_async(c.HOST, c.PORT)
    client.subscribe(c.TOPIC, c.QOS)
    client.loop_forever()
