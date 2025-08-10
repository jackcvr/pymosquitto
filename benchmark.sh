#!/bin/sh
set -e

export PUB=${PUB:-"pymosq"}
export SUB=${SUB:-"pymosq"}
export MQTT_LIMIT=1000000
export MQTT_QOS=0
export PUB_INTERVAL=0

COMPOSE="docker compose -f docker-compose.bench.yml"

cleanup() {
    $COMPOSE down --remove-orphans
}

trap cleanup EXIT INT TERM

$COMPOSE down --remove-orphans
$COMPOSE build
$COMPOSE up -d broker
sleep 1

$COMPOSE up
