# CLAUDE.md

Smith is a Python CLI chat app with persistent sessions. It supports Google Gemini (cloud) and local LLaMA (GGUF) models behind one interface. User-facing docs are in `README.md`.

## Setup & run

Use the `Makefile` (it manages `.venv`, installs `requirements-dev.txt` once and creates `.env` from `.env.example` if missing):

```bash
make setup                # create .venv, install dependencies (+ pytest)
make run                  # new session
make run SESSION_ID=<id>  # resume a session
make test                 # run the tests
make clean                # remove .venv
```

Manual equivalent: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements-dev.txt`, then `python src/run.py [--session-id=<id>]`.

`.env`: Gemini needs `GEMINI_API_KEY`, `MODEL_NAME`; LLaMA needs `ENGINE=LLAMA_CPP`, `LLAMA_MODEL_PATH` + model params (`LLAMA_GPU_LAYERS`, `LLAMA_CONTEXT_SIZE`; a bigger context needs more VRAM, the cache grows with it).

## Tests & CI

`pytest` (`tests/`, config in `pytest.ini`) uses fake chat models, so no API key or GGUF file is needed. GitHub Actions (`.github/workflows/tests.yml`) runs it on every push and PR (without `llama-cpp-python`, which compiles from source). `main` requires the `pytest` check to pass before merging. No linter is configured.

## Architecture

Flow: prompt_toolkit UI → command handler → session manager → chat session → LLM client → model (API or GGUF).

- `src/run.py` → `src/chat.py`: entry point and main loop (UI in `src/cli/`: `args.py`, `console.py`, `prompt.py`).
- `src/command_handler.py` + `src/commands/`: slash commands. New commands follow the existing pattern in `commands/`.
- `src/session/`: `session_manager.py` (session lifecycle and active session), `chat_session.py` (one conversation's history and state).
- `src/llm/`: LangChain-based. `client.py` (`LLMClient`), `chat_session.py` (streaming session), `history.py`, `factory.py` (engine from `ENGINE`), engines `gemini.py` and `llama.py` with `*_validation.py`. `send_message` returns an `LLMResponse` (`text`, `output_tokens`, `tokens_per_second`); `chat.py` prints the speed line after each answer. The `Tokens`/`Speed` lines use `console.print_stats`, colored with `PROMPT_TEXT_COLOR` (shared with the prompt style).
- `src/assistant/`: assistant definition and system prompt (`assistent.py`, `smith.py`).
- `src/files/`: `config.py`, `session_files.py`, `wal.py` (write-ahead log).
- PDF export (`/pdf`): `src/commands/session_to_pdf.py` → `src/files/pdf/pdf.py` (bundled Lato fonts); `src/pdf.py` is only a demo script.

## Slash commands

```
/session list | display | pop | clear | new | remove
/switch <ID>
/pdf
/help
/exit, /quit
```

## Data & debugging

Data lives in `~/.smith/`:
- `smith-wal.json`: transaction log for all sessions
- `<session-id>-log.json`: per-session data
- `output/`: exported PDFs (`/pdf`)

When something looks wrong, inspect those files and check `.env`.

## Conventions

- Update `README.md` whenever behavior changes.
- Follow existing patterns and conventions; keep commit messages focused on the "why". Commit messages follow Conventional Commits (`type(scope): subject`, e.g. `feat(llm): ...`, `docs(readme): ...`).
- Keep session state encapsulated in classes, not globals.
