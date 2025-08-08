import paho.mqtt.client as mqtt

from . import config as c


def on_connect(client, userdata, flags, rc, props):
    print("CONNECTED", rc)
    client.subscribe(c.TOPIC, qos=c.QOS)


def on_message(client, userdata, msg):
    global count
    count += 1
    print("MSG", msg)
    if count == c.LIMIT:
        client.disconnect()


count = 0
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message
client.connect_async(c.HOST, c.PORT, 60)
client.loop_forever()
