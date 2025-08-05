FROM debian:bookworm-slim

RUN apt-get update \
    && apt-get install -y \
      mosquitto-clients \
      libmosquitto-dev \
      python3-pip \
      procps

RUN pip3 install --break-system-packages paho-mqtt

ENV PYTHONUNBUFFERED=1
