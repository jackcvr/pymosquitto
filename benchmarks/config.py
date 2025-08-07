import os

HOST = "localhost"
PORT = 1883
TOPIC = "benchmark"
QOS = int(os.getenv("MQTT_QOS", 0))
LIMIT = int(os.getenv("MQTT_LIMIT", 1_000_000))
