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
- Token counter after every answer
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
`LLAMA_CONTEXT_SIZE` is also the limit shown by the token counter. A bigger context needs more memory (the KV cache grows with it); if the model fails to load with `Failed to create llama_context`, lower it or reduce `LLAMA_GPU_LAYERS`. For Gemini the counter assumes a 32768-token limit.

**Engine selection:** the client is picked from the `ENGINE` variable (case-insensitive): `GEMINI` uses `ChatGoogleGenerativeAI`, `LLAMA_CPP` uses `ChatLlamaCpp` (both created in `src/llm/`).

### Example: using LLaMA

1. Set the environment variables in `.env`:
```bash
ENGINE=LLAMA_CPP
MODEL_NAME=llama-3.1-8b-instruct
LLAMA_MODEL_PATH=/Users/tomaszku/Library/Caches/llama.cpp/bartowski_Meta-Llama-3.1-8B-Instruct-GGUF_Meta-Llama-3.1-8B-Instruct-Q8_0.gguf
LLAMA_GPU_LAYERS=1
LLAMA_CONTEXT_SIZE=2048
```

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

The tests cover the `llm/` layer (history conversion, streaming chat session, token counting, engine selection, Gemini and llama.cpp configuration). They use fake chat models, so they need no API key, network or GGUF file.

## make

```bash
make setup               # create .venv and install dependencies
make run                 # start Agent Smith (creates .env from .env.example if missing)
make run SESSION_ID=<id> # resume a session
make test                # run the tests
make clean               # remove .venv
```

## running

- run: `make run` (or activate the venv with `source .venv/bin/activate` and run `python src/run.py`)
- resume a session: `make run SESSION_ID=<ID>` (or `python src/run.py --session-id=<ID>`)

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

Exported PDFs are written to `~/.smith/output/`.

## Troubleshooting

- Something looks wrong? Inspect the files in `~/.smith/` and check your `.env`.
- `404 NOT_FOUND` from Gemini: the model name in `MODEL_NAME` is not available for your key (models get retired). List the models your key can use at https://aistudio.google.com.
- `503 UNAVAILABLE`: the model is overloaded. Smith retries automatically; set `GEMINI_FALLBACK_MODEL` to switch to another model when it keeps failing.
- `Failed to create llama_context` / `Failed to load model` with LLaMA: not enough memory for the model plus the context. Lower `LLAMA_CONTEXT_SIZE` or `LLAMA_GPU_LAYERS`, or close other programs using the GPU.
- If a request fails, the chat stays open and you can just send the message again.

## Project layout

```
src/
  run.py, chat.py        entry point and main loop
  cli/                   prompt, console output, CLI arguments
  command_handler.py     slash commands (implementations in commands/)
  session/               SessionManager and ChatSession
  llm/                   LangChain-based LLMClient, engines (Gemini, llama.cpp), config validation
  assistant/             assistant definition and system prompt
  files/                 config, session files, WAL, PDF generation (files/pdf/, bundled Lato fonts)
  pdf.py                 small demo script for the PDF generator
tests/                   pytest suite (fake chat models)
.github/workflows/       CI: runs the tests on every push and PR
Makefile                 setup, run, test, clean
```

## Architecture

### Session management

The application uses a two-class session management system:

#### **`ChatSession`** (a single chat session)
Represents one chat session and contains:
- **Unique session identifier** (`session_id`)
- **Conversation history** (all messages)
- **LLM session** (`LangChainChatSession`, engine-independent)
- **Management methods**:
  - `send_message(text)` - sends a message to the model
  - `save_to_file()` / `load_from_file(id)` - persistence
  - `get_history()` / `clear_history()` - history management
  - `pop_last_exchange()` - removes the last exchange
  - `count_tokens()` / `get_remaining_tokens()` - token counting
  - `is_empty()` - checks whether the session has any content

#### **`SessionManager`** (session orchestration)
Manages the session lifecycle and the currently active session:
- Creates new sessions
- Switches between sessions
- Automatically saves sessions when switching
- Handles initialization from the CLI
- Ensures cleanup when the program exits

**Key change:** All session state is encapsulated in classes. No global variables are used to store session state.

### LLM client abstraction

All model handling goes through LangChain chat models (`BaseChatModel`), so both engines share one code path:

- **`LLMClient`** (`llm/client.py`) - wraps a chat model: creates chat sessions, counts tokens, reports the model name and (for local models) the real context window
- **`LangChainChatSession`** (`llm/chat_session.py`) - keeps the history and streams every answer with `model.stream()`; the history is updated only after a successful answer, so a failed request can be retried
- **`llm/history.py`** - converts the stored history format (`{"role": "user|model", "parts": [{"text": ...}]}`) to LangChain messages; existing session files keep working
- **`llm/factory.py`** - picks the engine from `ENGINE`

#### **Gemini engine** (`llm/gemini.py`, `ChatGoogleGenerativeAI`)
- Requires an API key (`GEMINI_API_KEY`)
- Optionally routes requests through a proxy (`GEMINI_PROXY_URL`)
- Optionally uses a fallback model (`GEMINI_FALLBACK_MODEL`, via LangChain `with_fallbacks`) when a request to the main model times out (`GEMINI_TIMEOUT` seconds per request) or still returns a server error (5xx, e.g. 503) after all retries; the fallback is tried per request, so the history is kept
- Automatically retries transient errors up to 5 attempts with exponential backoff
- Thinking is disabled (`thinking_budget=0`)
- Tokens are counted with the Gemini token counting API

#### **llama.cpp engine** (`llm/llama.py`, `ChatLlamaCpp`)
- Runs local GGUF models through llama-cpp-python, no internet connection needed
- Configurable parameters: GPU layers, context size (the token counter uses `LLAMA_CONTEXT_SIZE` as its limit)
- The model's built-in chat template (e.g. Llama 3.1's) is applied to the system prompt and history
- Tokens are counted with the model's own tokenizer

**Selection:** `ChatSession` calls `create_llm_client()` (`llm/factory.py`), which picks the engine from the `ENGINE` environment variable.
