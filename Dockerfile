FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y gcc libmosquitto1 gdb procps time

COPY . .

RUN pip install -e .[dev]
