#!/bin/sh
set -e

export PREFIX=${PREFIX:-"pymosq"}
export MQTT_QOS=${MQTT_QOS:-"0"}
export MQTT_LIMIT=${MQTT_LIMIT:-"1000000"}
export PUB_INTERVAL=${PUB_INTERVAL:-"0"}

COMPOSE="docker compose -f docker-compose.bench.yml"

cleanup() {
    $COMPOSE down --remove-orphans
}

trap cleanup EXIT INT TERM

$COMPOSE down --remove-orphans
$COMPOSE build
$COMPOSE up
