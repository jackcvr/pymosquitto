DC 			:= docker compose
DC_RUN		:= $(DC) run --rm
DC_DOWN 	:= $(DC) down --remove-orphans
DISCARD 	:= 1>/dev/null 2>&1
SED_VALUE 	:= sed -E 's/.*: //'
PYTHON		?= .venv/bin/python
LEVEL		?= INFO
PYTEST 		= pytest -s --log-cli-level=$(LEVEL)

MODULE       ?= pymosq
MQTT_QOS     ?= 0
MQTT_LIMIT   ?= 1000000
PUB_AMOUNT	 ?= 3000000
PUB_INTERVAL ?= 0

export MODULE \
	MQTT_QOS \
	MQTT_LIMIT \
	PUB_INTERVAL

.PHONY: build test bench-all bench plot pack publish clean

build:
	$(DC) build

test:
	$(DC_RUN) py $(PYTEST)

test-%:
	$(DC_RUN) py $(PYTEST) -k $*

bench-all:
	@PY_RSS=$$($(DC_RUN) py 2>&1 | grep "Maximum resident set size" | $(SED_VALUE)) \
		&& echo "Python RSS: $$PY_RSS" \
		&& echo "Module;Time;RSS" > benchmark.csv
	@for module in pymosq pymosq_async paho gmqtt mqttools aiomqtt amqtt; do \
		LINE=$$($(MAKE) -s bench-$$module); \
		echo "$$LINE"; \
		echo "$$LINE" >>benchmark.csv; \
	done

bench-%:
	@$(MAKE) -s build $(DISCARD)
	@trap '$(DC_DOWN) $(DISCARD)' EXIT INT TERM \
		&& export MODULE=$* \
		&& OUTPUT=$$($(DC_RUN) sub 2>&1) \
		&& TIME=$$(echo "$$OUTPUT" | grep "Elapsed (wall clock)" | $(SED_VALUE)) \
		&& RSS=$$(echo "$$OUTPUT" | grep "Maximum resident set size" | $(SED_VALUE)) \
		&& echo "$$MODULE;$$TIME;$$RSS" || echo "$$MODULE;0;0"

plot:
	$(PYTHON) ./make_plot.py

pack: dist

dist: test
	$(DC_RUN) py sh -c "python -m build && twine upload --verbose -r testpypi dist/*"

publish:
	$(DC_RUN) py twine upload dist/*

clean:
	$(DC_DOWN)
	-$(DC_RUN) py rm -rf dist/
