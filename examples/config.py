import os

HOST = os.getenv("MQTT_HOST", "localhost")
PORT = os.getenv("MQTT_PORT", 1883)
TOPIC = os.getenv("MQTT_TOPIC", "#")
QOS = int(os.getenv("MQTT_QOS", 0))
