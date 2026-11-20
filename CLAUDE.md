# CLAUDE.md

Smith is a Python CLI chat app with persistent sessions. It supports Google Gemini (cloud) and local LLaMA (GGUF) models behind one interface. User-facing docs are in `README.md`.

## Setup & run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # Gemini: GEMINI_API_KEY, MODEL_NAME; LLaMA: LLAMA_MODEL_PATH + model params
python src/run.py                      # new session
python src/run.py --session-id=<id>    # resume a session
```

Tests (also run by GitHub Actions on every push and PR): `pip install -r requirements-dev.txt && pytest` (`tests/`, fake chat models, no API key or GGUF needed). No linter is configured.

## Architecture

Flow: prompt_toolkit UI → command handler → session manager → chat session → LLM client → model (API or GGUF).

- `src/run.py` → `src/chat.py`: entry point and main loop (UI in `src/cli/`: `args.py`, `console.py`, `prompt.py`).
- `src/command_handler.py` + `src/commands/`: slash commands. New commands follow the existing pattern in `commands/`.
- `src/session/`: `session_manager.py` (session lifecycle and active session), `chat_session.py` (one conversation's history and state).
- `src/llm/`: LangChain-based. `client.py` (`LLMClient`), `chat_session.py` (streaming session), `history.py`, `factory.py` (engine from `ENGINE`), engines `gemini.py` and `llama.py` with `*_validation.py`.
- `src/assistant/`: assistant definition and system prompt (`assistent.py`, `smith.py`).
- `src/files/`: `config.py`, `session_files.py`, `wal.py` (write-ahead log).
- PDF export: `src/pdf.py`, `src/files/pdf/` (bundled Lato fonts).

## Slash commands

```
/session list | display | summary | new | clear | pop
/switch <ID>
/help
/exit, /quit
```

## Data & debugging

Data lives in `~/.smith/`:
- `smith-wal.json`: transaction log for all sessions
- `<session-id>-log.json`: per-session data
- `output/`: exported files

When something looks wrong, inspect those files and check `.env`.

## Conventions

- Update `README.md` whenever behavior changes.
- Follow existing patterns and conventions; keep commit messages focused on the "why".
- Keep session state encapsulated in classes, not globals.
