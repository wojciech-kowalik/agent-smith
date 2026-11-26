VENV := .venv
PYTHON := $(VENV)/bin/python
STAMP := $(VENV)/.installed

SERVER_LOG := $(HOME)/.smith/server.log

.PHONY: help setup run ask serve stop status test clean

help:
	@echo "make setup               create .venv and install dependencies (+ pytest)"
	@echo "make run                 start Agent Smith in a new session"
	@echo "make run SESSION_ID=<id> resume a session"
	@echo "make ask \"...\"          one-shot: print only the answer (STDIN=1 adds piped input, SESSION_ID=<id> keeps history)"
	@echo "make serve               keep the model loaded in VRAM (make ask then answers instantly)"
	@echo "make stop                stop the server and release the model from memory"
	@echo "make status              is the server running?"
	@echo "make test                run the tests"
	@echo "make clean               remove .venv"

# Reinstalls only when a requirements file changes
$(STAMP): requirements.txt requirements-dev.txt
	@test -d $(VENV) || python3 -m venv $(VENV)
	$(PYTHON) -m pip install -r requirements-dev.txt
	@touch $(STAMP)

setup: $(STAMP)

.env:
	cp .env.example .env
	@echo "Created .env from .env.example - fill in GEMINI_API_KEY or the LLaMA settings."

run: $(STAMP) .env
	$(PYTHON) src/run.py $(if $(SESSION_ID),--session-id=$(SESSION_ID))

# `make ask "question"`: the words after `ask` are the question (Q= still works and wins)
ifneq ($(filter ask,$(MAKECMDGOALS)),)
ASK_WORDS := $(filter-out ask,$(MAKECMDGOALS))
Q ?= $(ASK_WORDS)
%:
	@:
endif

ask: $(STAMP) .env
	@test -n "$(Q)" || { echo 'usage: make ask "question"' >&2; exit 2; }
	@$(PYTHON) src/run.py --ask "$(Q)" $(if $(STDIN),--stdin) $(if $(SESSION_ID),--session-id=$(SESSION_ID))

# Starts the server in the background and waits until the model is loaded (log: ~/.smith/server.log)
serve: $(STAMP) .env
	@$(PYTHON) src/run.py --status >/dev/null 2>&1 && { echo "The Smith server is already running."; exit 0; }; \
	mkdir -p $(dir $(SERVER_LOG)); \
	setsid nohup $(PYTHON) src/run.py --serve > $(SERVER_LOG) 2>&1 < /dev/null & \
	for i in $$(seq 1 180); do \
		$(PYTHON) src/run.py --status >/dev/null 2>&1 && { echo "The Smith server is ready (model loaded)."; $(PYTHON) src/run.py --status; exit 0; }; \
		sleep 1; \
	done; \
	echo "The Smith server did not start; see $(SERVER_LOG)" >&2; exit 1

stop: $(STAMP)
	@$(PYTHON) src/run.py --stop

status: $(STAMP)
	@$(PYTHON) src/run.py --status

test: $(STAMP)
	$(PYTHON) -m pytest

clean:
	rm -rf $(VENV)
