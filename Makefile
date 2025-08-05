TRAP	:= trap '$(MAKE) clean' EXIT;
DC 		:= docker compose
DC_RUN	:= $(DC) run --rm

PREFIX       ?= pymosq
MQTT_QOS     ?= 0
MQTT_LIMIT   ?= 1000000
PUB_INTERVAL ?= 0

export PREFIX MQTT_QOS MQTT_LIMIT PUB_INTERVAL

test:
	$(DC_RUN) py pytest -s

bench: clean
	$(TRAP) \
		$(DC_RUN) pub && \
		$(DC) logs sub

.PHONY: build
build:
	$(DC_RUN) py rm -rf dist/
	$(DC_RUN) py sh -c "python -m build && twine upload -r testpypi dist/*"

publish:
	$(DC_RUN) py twine upload dist/*

clean:
	docker compose down --remove-orphans
