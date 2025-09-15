FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y libmosquitto1 time

ADD . ./

RUN pip install -e .[dev]
