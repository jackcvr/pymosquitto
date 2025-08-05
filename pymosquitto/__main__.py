import sys
import logging

from . import MQTTClient

logging.basicConfig(level=logging.DEBUG)


with MQTTClient() as mqtt:
    mqtt.connect(sys.argv[1])
    mqtt.subscribe(sys.argv[2], 0)
    mqtt.loop_forever()
