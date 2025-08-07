#!/bin/sh
set -e

COMPOSE="docker compose -f docker-compose.bench.yml"

cleanup() {
    $COMPOSE down --remove-orphans
}

trap cleanup EXIT INT TERM

$COMPOSE down --remove-orphans \
    && $COMPOSE up -d --build \
    && $COMPOSE logs -f
