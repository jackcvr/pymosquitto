from pymosquitto import MQTTClient

from . import config as c

count = 0

with MQTTClient() as client:

    @client.on_connect_handler
    def _(client, userdata):
        for i in range(c.LIMIT):
            client.publish(c.TOPIC, str(i), qos=c.QOS)

    @client.on_publish_handler
    def _(client, userdata, msg):
        global count
        count += 1
        if count == c.LIMIT:
            client.disconnect()

    client.connect_async(c.HOST, c.PORT)
    client.loop_forever()
