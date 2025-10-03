import os

HOST, _port = os.getenv("MQTT_URL", "broker.hivemq.com:1883").split(":")
PORT = int(_port)
USERNAME = os.getenv("MQTT_USERNAME", "")
PASSWORD = os.getenv("MQTT_PASSWORD", "")
