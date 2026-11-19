---
description: Create the Python venv if missing and install dependencies
allowed-tools: Bash(python3 -m venv:*), Bash(.venv/bin/pip:*), Bash(.venv/bin/python:*), Bash(test:*)
---

Set up the project's Python virtual environment in `.venv`:

1. If `.venv` does not exist, create it with `python3 -m venv .venv`.
2. Install dependencies with `.venv/bin/pip install -r requirements.txt`.
3. Report the Python version (`.venv/bin/python --version`) and whether the install succeeded. If `llama-cpp-python` fails to build, say so and suggest installing the rest without it.

Note: each Bash call is a fresh shell, so call `.venv/bin/python` / `.venv/bin/pip` directly instead of `source .venv/bin/activate`. Remind the user to run `source .venv/bin/activate` in their own terminal.
