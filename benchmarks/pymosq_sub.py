import time
import types

from pymosquitto import MQTTClient

from . import config as c

data = types.SimpleNamespace(count=0, start_time=None)

with MQTTClient(userdata=data) as client:

    @client.on_message_handler
    def _(client, userdata, msg):
        if userdata.count == 0:
            userdata.start_time = time.monotonic()
        userdata.count += 1
        if userdata.count == c.LIMIT:
            print(f"Done[qos={c.QOS}]:", time.monotonic() - userdata.start_time)
            client.close()

    client.connect_async(c.HOST, c.PORT)
    client.subscribe(c.TOPIC, c.QOS)
    client.loop_forever()
