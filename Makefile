.ONESHELL:

TRAP	:= trap '$(MAKE) -s clean' EXIT
DC 		:= docker compose
DC_RUN	:= $(DC) run --rm

PREFIX       ?= pymosq
MQTT_QOS     ?= 0
MQTT_LIMIT   ?= 1000000
PUB_AMOUNT	 ?= 3000000
PUB_INTERVAL ?= 0

export PREFIX MQTT_QOS MQTT_LIMIT PUB_INTERVAL

test: build_image
	$(DC_RUN) py pytest -s

bench: clean
	$(DC) build
	$(MAKE) bench-pymosq
	sleep 1
	$(MAKE) bench-paho
	sleep 1
	$(MAKE) PUB_AMOUNT=100000000 bench-amqtt

bench-%:
	$(TRAP)
	PREFIX=$* $(DC_RUN) pub
	$(DC) logs sub

.PHONY: build
build:
	$(DC_RUN) py rm -rf dist/
	$(DC_RUN) py sh -c "python -m build && twine upload --verbose -r testpypi dist/*"

publish:
	$(DC_RUN) py twine upload dist/*

clean:
	docker compose down --remove-orphans
