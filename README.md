# Agent Smith

> *"Mr. Anderson..."* - Agent Smith is a command-line chat assistant named after the famous Agent from The Matrix.

<p align="center">
  <img src="docs/agent-smith.jpg" alt="Agent Smith mannequin from the Matrix films" width="300">
  <br>
  <sub>Agent Smith mannequin from the Matrix films. Photo by <a href="https://commons.wikimedia.org/wiki/File:Smith_Matrix_mannequins_(cropped).jpg">Marcin Wichary</a>, <a href="https://creativecommons.org/licenses/by/2.5/">CC BY 2.5</a>, via Wikimedia Commons.</sub>
</p>

**Agent Smith** is a Python CLI chat app with persistent sessions. It talks to Google Gemini (cloud) or to a local LLaMA model (GGUF) through LangChain chat models behind one common interface, so you can switch the engine without changing how you use the app.

## Features

- Interactive prompt with syntax highlighting and auto-completion of slash commands
- Persistent sessions: every conversation is saved in `~/.smith/` and can be resumed later by ID
- Two engines behind one interface: Google Gemini (default) and local LLaMA (works offline)
- Resilient Gemini client: optional proxy, automatic retries, per-request timeout and an optional fallback model
- Streaming output with both engines: the answer appears token by token as the model generates it
- Token counter after every answer, plus the generation speed in tokens per second
- Export of a session to PDF (`/pdf`)
- Write-ahead log of all prompts and answers (`smith-wal.json`)
- Animated progress bar while waiting for the model

## Quick start

```bash
make run                  # creates .venv, installs dependencies and .env, then starts the app
```

On the first run `make run` creates `.env` from `.env.example`; edit it first (put your `GEMINI_API_KEY` in it) with `make .env`, then `make run`. Without `make`:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # then put your GEMINI_API_KEY in it
python src/run.py
```

You get the API key at https://aistudio.google.com/apikey. Type a message and press Enter; type `/help` to see the available commands and `/exit` to leave (the session is saved automatically).

## setup/requirements

- create a venv: `python -m venv .venv`
- activate the venv: `source .venv/bin/activate`
- install dependencies: `pip install -r requirements.txt` (`requirements-dev.txt` adds `pytest`)

Or simply `make setup`.

### dependencies

- `langchain-core` - common chat model interface (messages, streaming, fallbacks)
- `langchain-google-genai` - Google Gemini integration
- `langchain-community` - `ChatLlamaCpp` integration for local models
- `llama-cpp-python` - runs local LLaMA models (GGUF)
- `python-dotenv` - loads environment variables from `.env`
- `colorama` - colored terminal output
- `prompt-toolkit` - interactive terminal prompt
- `pydantic` - validation of the configuration
- `fpdf2` and `markdown` - PDF export

## LLM client configuration

The application supports two types of LLM models. The engine is chosen with the `ENGINE` variable (`GEMINI` by default, or `LLAMA_CPP`).

### Google Gemini (default)
Create a `.env` file with the following variables:
```bash
ENGINE=GEMINI
GEMINI_API_KEY=your_gemini_api_key_here
MODEL_NAME=gemini-3.8-flash # must match an available Gemini model
GEMINI_PROXY_URL=https://my-proxy.example.com # optional, must start with http:// or https://
GEMINI_FALLBACK_MODEL=gemini-3.7-flash # optional, used when the main model times out or keeps failing with 5xx errors
GEMINI_TIMEOUT=30 # optional, max seconds to wait for one request to Gemini (default 30)
```
`GEMINI_PROXY_URL` is optional: when set, Gemini API requests are sent to this base URL instead of the default Google endpoint.

### Local LLaMA (llama-cpp-python)
For local LLaMA models, set:
```bash
ENGINE=LLAMA_CPP
MODEL_NAME=llama-3.1-8b-instruct
LLAMA_MODEL_PATH=/path/to/your/model.gguf
LLAMA_GPU_LAYERS=1       # optional, default 1 (use a high number such as 99 to offload everything to the GPU)
LLAMA_CONTEXT_SIZE=2048  # optional, default 2048
```
`LLAMA_CONTEXT_SIZE` is also the limit shown by the token counter. When a conversation fills 80% of the context window the app prints a yellow warning after the answer (a stronger one once the limit is exceeded); the history is not trimmed automatically. A bigger context needs more memory (the KV cache grows with it); if the model fails to load with `Failed to create llama_context`, lower it or reduce `LLAMA_GPU_LAYERS`. For Gemini the counter assumes a 32768-token limit.

**Engine selection:** the client is picked from the `ENGINE` variable (case-insensitive): `GEMINI` uses `ChatGoogleGenerativeAI`, `LLAMA_CPP` uses `ChatLlamaCpp` (both created in `src/llm/`).

### Example: using LLaMA

1. Set the environment variables in `.env`:
```bash
ENGINE=LLAMA_CPP
MODEL_NAME=llama-3.1-8b-instruct
LLAMA_MODEL_PATH=/path/to/your/model.gguf
LLAMA_GPU_LAYERS=1
LLAMA_CONTEXT_SIZE=2048
```

`LLAMA_MODEL_PATH` is a placeholder: point it to a `.gguf` file on your machine (for example a model downloaded by llama.cpp or LM Studio, or one you downloaded yourself from Hugging Face). The path differs between setups, so do not commit your own.

2. Run the application - the llama.cpp engine is used because of `ENGINE=LLAMA_CPP`:
```bash
python src/run.py
```

3. The local model is loaded from `LLAMA_MODEL_PATH`.

## tests

```bash
make test                              # or: pip install -r requirements-dev.txt && pytest
```

GitHub Actions (`.github/workflows/tests.yml`) runs them on every push and pull request.

The tests cover the PDF export (code blocks, tables, Polish characters) and the `llm/` layer (history conversion, streaming chat session, token counting, engine selection, Gemini and llama.cpp configuration). They use fake chat models, so they need no API key, network or GGUF file.

## benchmark

`make benchmark` runs `benchmark/bench.py`: 8 short tasks (arithmetic, knowledge, logic, code, bug finding, regex, translation, a longer text) through `make ask`, printing the time, the answer length and an automatic OK/FAIL per task. Start `make serve` first, otherwise every task also pays the model load time. It is a smoke test, not a quality evaluation.

## make

```bash
make setup               # create .venv and install dependencies
make run                 # start Agent Smith (creates .env from .env.example if missing)
make run SESSION_ID=<id> # resume a session
make serve               # keep the model loaded in VRAM (make stop releases it)
make ask "question"      # one-shot: print only the answer (Q="question" also works)
                         #   STDIN=1 adds piped input as context, SESSION_ID=<id> continues a session
make test                # run the tests
make benchmark           # time and score the model on 8 short tasks (see below)
make clean               # remove .venv
```

## running

- run: `make run` (or activate the venv with `source .venv/bin/activate` and run `python src/run.py`)
- resume a session: `make run SESSION_ID=<ID>` (or `python src/run.py --session-id=<ID>`)

### One-shot mode (`--ask`)

Besides the interactive chat, Smith can answer a single question and exit - handy as a helper for scripts or other tools such as Claude Code:

```bash
python src/run.py --ask "How do I reverse a list in Python?"
git diff | python src/run.py --ask "Review this diff" --stdin   # --stdin: piped text is added as context
echo "What does this error mean?" | python src/run.py -p   # no argument: the question comes from stdin
python src/run.py --ask "And in Rust?" --session-id=<ID>   # continue (and save to) an existing session
git diff | make ask "Review this diff" STDIN=1         # the same through make
```

- stdin is read only with `--stdin` or when the question is `-`/missing, so a caller holding an idle pipe open (e.g. Claude Code) never hangs.
- stdout contains **only the answer**; model info and errors go to stderr, so the output is safe to capture.
- Exit code: `0` answered, `1` model/session error, `2` empty question.
- Nothing is saved to `~/.smith/` unless a session ID is given (`--session-id=<ID>` / `SESSION_ID=<ID>`; the WAL still logs the exchange). With an ID **every call continues the same conversation**: the first call with a new ID creates the session under that ID, the next calls load its history, add the new exchange and save it again - with or without the server. A session ID may contain letters, digits, `.`, `_` and `-`. An unreadable (corrupt) session file is reported as an error and never overwritten.
- Only the answer is returned (no streaming, progress bar or token stats). Without the server (below) the model is loaded on every call, so a local GGUF model takes a few seconds to start.

### Keeping the model loaded (`make serve` / `make stop`)

```bash
make serve    # load the model once and keep it in VRAM (in the background; log: ~/.smith/server.log)
make ask "question"   # now answers in about a second - it uses the server automatically
make status   # is the server running?
make stop     # stop the server and release the model from memory
```

(`python src/run.py --serve | --stop | --status` do the same.)

On start (in `~/.smith/server.log`) and in `make status` the server reports the GPU and its memory (`src/gpu.py`):

```
GPU 0: NVIDIA GeForce RTX 3060 | VRAM total 12288 MiB, used 10394 MiB, free 1516 MiB
Smith (pid 28073) holds 9802 MiB of VRAM
```

On **macOS** the GPU shares the system memory (unified memory, Metal), so there is no separate VRAM: the report shows the chip, the total/used/free system memory (`sysctl`, `vm_stat`) and the memory the Smith process uses (its resident set, `ps`):

```
GPU 0: Apple M2 Pro (19 GPU cores) | unified memory (shared with the system) total 32768 MiB, used 27300 MiB, free 5468 MiB
Smith (pid 4242) holds 9600 MiB of unified memory
```

| Platform | Source | Shown |
|---|---|---|
| Linux + NVIDIA | `nvidia-smi` | card model, VRAM total/used/free, VRAM held by Smith |
| macOS (Apple Silicon / Intel) | `system_profiler`, `sysctl`, `vm_stat`, `ps` | chip, unified memory total/used/free, memory used by Smith |
| anything else (e.g. AMD on Linux) | - | a note that no GPU information is available |

`make stop` waits until the server process is gone and then shows the GPU again, with how much VRAM was released:

```
GPU 0: NVIDIA GeForce RTX 3060 | VRAM total 12288 MiB, used 582 MiB, free 11328 MiB
Smith (pid 28331) released 9802 MiB of VRAM
```

- The model stays in memory until you run `make stop` (or kill the process) - it is never unloaded automatically. It holds the VRAM (about 10 GB for the 14B model), so stop it when you want the GPU for something else, e.g. LM Studio.
- Parallel callers are safe: one model has one context, so requests are answered one at a time and the rest wait in a queue. Without the server, parallel `--ask` calls each try to load their own copy of the model and fail when the VRAM is not enough.
- `--ask` falls back to loading the model itself when the server is not running. Answers served by the server print a reminder on stderr to stop it when you are done.
- The server listens on a Unix socket in `~/.smith/` (`smith.sock`), so only your user can reach it.

To let Claude Code use it, add a note like this to your project's `CLAUDE.md`: *"For a second opinion from the local model run `python /path/to/agent-smith/src/run.py --ask "<question>"` (pipe context on stdin with `--stdin`)."*

After you send a prompt, an animated progress bar with elapsed time is shown while Smith waits for the model's answer. It is skipped when output is not a terminal (e.g. piped).


## Supported slash commands:

```
/exit
/quit
/help
/switch <ID>
/session list
/session display
/session pop
/session clear
/session new
/session remove
/pdf
```

## Session files

Sessions are stored in `~/.smith/`:
- `<session-id>-log.json` - conversation history
- `smith-wal.json` - Write-Ahead Log (all transactions)

Exported PDFs are written to `~/.smith/output/` by default. Code blocks and tables from the answers are rendered too (tables without borders). Set `SMITH_OUTPUT_DIR` in `.env` (e.g. `SMITH_OUTPUT_DIR=~/Documents/smith`) to use another folder; it is created if missing. This helps when the browser cannot open hidden folders (snap Firefox shows "access denied" for `~/.smith/`).

## Troubleshooting

- Something looks wrong? Inspect the files in `~/.smith/` and check your `.env`.
- `404 NOT_FOUND` from Gemini: the model name in `MODEL_NAME` is not available for your key (models get retired). List the models your key can use at https://aistudio.google.com.
- `503 UNAVAILABLE`: the model is overloaded. Smith retries automatically; set `GEMINI_FALLBACK_MODEL` to switch to another model when it keeps failing.
- `Failed to create llama_context` / `Failed to load model` with LLaMA: not enough memory for the model plus the context. Lower `LLAMA_CONTEXT_SIZE` or `LLAMA_GPU_LAYERS`, or close other programs using the GPU (check with `nvidia-smi`; LM Studio's server keeps the model in VRAM while it runs). `LLAMA_GPU_LAYERS=0` runs on the CPU only: slower, but needs no VRAM.
- If a request fails, the chat stays open and you can just send the message again.
