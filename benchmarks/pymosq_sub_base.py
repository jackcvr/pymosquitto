from pymosquitto.base import Mosquitto, MQTTMessage

from . import config as c


def on_connect(mosq, userdata, rc):
    print("CONNECTED")
    client.subscribe(c.TOPIC, c.QOS)


def on_message(mosq, userdata, msg):
    global count
    msg = MQTTMessage.from_c(msg)
    print("MSG", msg)
    count += 1
    if count == c.LIMIT:
        client.disconnect()


count = 0
client = Mosquitto()
client.connect_callback_set(on_connect)
client.message_callback_set(on_message)
client.connect(c.HOST, c.PORT)
client.loop_forever()
