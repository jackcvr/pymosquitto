FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y gcc libmosquitto1 gdb procps time libmosquitto-dev

COPY . .

RUN pip install -e .[dev]
