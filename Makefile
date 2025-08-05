DC 		:= docker compose
DC_RUN	:= $(DC) run --rm
DC_DOWN := $(DC) down --remove-orphans

MODULE       ?= pymosq
MQTT_QOS     ?= 0
MQTT_LIMIT   ?= 1000000
PUB_AMOUNT	 ?= 3000000
PUB_INTERVAL ?= 0

export MODULE \
	MQTT_QOS \
	MQTT_LIMIT \
	PUB_INTERVAL

.PHONY: build
build:
	$(DC) build

test:
	$(DC_RUN) py pytest -s

bench-all:
	@PY_RSS=$$($(DC_RUN) py 2>&1 | grep "Maximum resident set size" | sed -E 's/.*: //') \
		&& echo "Python RSS: $$PY_RSS" \
		&& echo "Module;Time;RSS" > benchmark.csv
	@for module in pymosq paho gmqtt aiomqtt amqtt; do \
		LINE=$$($(MAKE) -s MODULE=$$module bench); \
		echo "$$LINE"; \
		echo "$$LINE" >>benchmark.csv; \
	done

bench:
	@$(DC) build 1>/dev/null 2>&1
	@trap '$(DC_DOWN) 1>/dev/null 2>&1' EXIT INT TERM \
		&& OUTPUT=$$($(DC_RUN) sub 2>&1) \
		&& TIME=$$(echo "$$OUTPUT" | grep "Elapsed (wall clock)" | sed -E 's/.*: //') \
		&& RSS=$$(echo "$$OUTPUT" | grep "Maximum resident set size" | sed -E 's/.*: //') \
		&& echo "$$MODULE;$$TIME;$$RSS" || echo "$$MODULE;0;0"

plot:
	.venv/bin/python ./make_plot.py

pack: dist

dist:
	$(DC_RUN) py sh -c "python -m build && twine upload --verbose -r testpypi dist/*"

publish:
	$(DC_RUN) py twine upload dist/*

clean:
	$(DC_DOWN)
	-$(DC_RUN) py rm -rf dist/
