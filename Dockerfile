FROM python:3.8-slim

RUN apt-get update \
    && apt-get install -y gdb libmosquitto-dev procps

RUN pip install --break-system-packages paho-mqtt

ENV PYTHONUNBUFFERED=1
