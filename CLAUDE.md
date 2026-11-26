# CLAUDE.md

Smith is a Python CLI chat app with persistent sessions. It supports Google Gemini (cloud) and local LLaMA (GGUF) models behind one interface. User-facing docs are in `README.md`.

## Setup & run

Use the `Makefile` (it manages `.venv`, installs `requirements-dev.txt` once and creates `.env` from `.env.example` if missing):

```bash
make setup                # create .venv, install dependencies (+ pytest)
make run                  # new session
make run SESSION_ID=<id>  # resume a session
make ask "question"       # one-shot: only the answer on stdout (Q="question" also works) (STDIN=1, SESSION_ID=<id> optional)
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
- `src/ask.py`: one-shot mode (`--ask`/`-p`): answer only on stdout, everything else on stderr, no save without `--session-id`.
- `src/server.py`: optional model server (`--serve`/`--stop`/`--status`, `make serve|stop|status`): one process keeps the model in VRAM and answers over a Unix socket (`~/.smith/smith.sock`, log `~/.smith/server.log`); requests are queued (one generation at a time); `--ask` uses it when running, otherwise loads the model itself. `src/gpu.py` builds the GPU/memory report shown on start, in `make status` and after `make stop` (`nvidia-smi` on Linux/NVIDIA; on macOS unified memory via `sysctl`/`vm_stat`/`ps`; external commands go through an injectable `run`, so tests need no GPU).
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

## Calling Smith from another agent (e.g. Claude Code)

One-shot mode returns only the answer on stdout (logs go to stderr, exit code 0 = OK). Use it for a second opinion from the local model:

```bash
make --no-print-directory -C <path-to-agent-smith> ask "<question>" 2>/dev/null
git diff | make --no-print-directory -C <path-to-agent-smith> ask "Review this diff" STDIN=1 2>/dev/null
```

- Quote the question (a question that is exactly a make target name, e.g. `test`, would run that target; use `Q=` then); add `STDIN=1` only when piping context (stdin is not read otherwise, so it never hangs).
- Stateless by default; `SESSION_ID=<id>` continues and saves a session.
- The model runs fully in VRAM (`LLAMA_GPU_LAYERS=99`, context 8192): if loading fails with a GPU memory error, another program (LM Studio) holds the VRAM - unload it with `~/.lmstudio/bin/lms unload qwen2.5-coder-14b-instruct`. Do not lower the GPU layers.
- Keep the input within the 8192-token context.
- Without the server every call loads the model (a few seconds, ~9 GB VRAM) and frees it on exit; parallel calls then fail with a GPU memory error. For several questions or parallel callers start the server first: `make --no-print-directory -C <path-to-agent-smith> serve` (model stays in VRAM, answers in ~1 s, parallel calls are queued, `make ask` uses it automatically).
- **Reminder for the managing agent: the server holds ~10 GB of VRAM until it is stopped. When the session with Smith is over, release the model with `make --no-print-directory -C <path-to-agent-smith> stop`** (check with `make status`). Stop it earlier when the user wants the GPU for something else (e.g. LM Studio). Every `make ask` answered by the server prints this reminder on stderr.

## Data & debugging

Data lives in `~/.smith/`:
- `smith-wal.json`: transaction log for all sessions
- `<session-id>-log.json`: per-session data
- `output/`: exported PDFs (`/pdf`)

When something looks wrong, inspect those files and check `.env`.

## Conventions

- Update `README.md` whenever behavior changes.
- Follow existing patterns and conventions; keep commit messages focused on the "why".
- Commit messages MUST pass commitlint (`@commitlint/config-conventional`): `type(scope): subject`.
  - `type`: one of `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`; lowercase
  - `scope`: optional, lowercase (e.g. `llm`, `readme`)
  - `subject`: imperative mood, lowercase start, no trailing period; the whole header at most 100 characters
  - separate the body and footer from the header with a blank line; body lines at most 100 characters
  - e.g. `feat(llm): show generation speed in tokens per second`, `docs(readme): sync with the code`
- Keep session state encapsulated in classes, not globals.
