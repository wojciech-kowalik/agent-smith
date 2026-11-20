VENV := .venv
PYTHON := $(VENV)/bin/python
STAMP := $(VENV)/.installed

.PHONY: help setup run test clean

help:
	@echo "make setup               create .venv and install dependencies (+ pytest)"
	@echo "make run                 start Agent Smith in a new session"
	@echo "make run SESSION_ID=<id> resume a session"
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

test: $(STAMP)
	$(PYTHON) -m pytest

clean:
	rm -rf $(VENV)
