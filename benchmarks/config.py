import os

HOST = "localhost"
PORT = 1883
TOPIC = "benchmark"
QOS = int(os.getenv("MQTT_QOS") or 0)
LIMIT = int(os.getenv("MQTT_LIMIT") or 1_000_000)
INTERVAL = int(os.getenv("PUB_INTERVAL") or 0)
