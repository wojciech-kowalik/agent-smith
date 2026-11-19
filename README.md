# Smith

> *"Mr. Anderson..."* - Smith is a command-line chat assistant named after the famous Agent.

<p align="center">
  <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/c/c2/Smith_Matrix_mannequins_%28cropped%29.jpg/500px-Smith_Matrix_mannequins_%28cropped%29.jpg" alt="Agent Smith mannequin from the Matrix films" width="300">
  <br>
  <sub>Agent Smith mannequin from the Matrix films. Photo by <a href="https://commons.wikimedia.org/wiki/File:Smith_Matrix_mannequins_(cropped).jpg">Marcin Wichary</a>, <a href="https://creativecommons.org/licenses/by/2.5/">CC BY 2.5</a>, via Wikimedia Commons.</sub>
</p>

**Smith** is a Python CLI chat app with persistent sessions. It talks to Google Gemini (cloud) or to a local LLaMA model (GGUF) through one common interface, so you can switch the engine without changing how you use the app.

## Features

- Interactive prompt with syntax highlighting and auto-completion of slash commands
- Persistent sessions: every conversation is saved in `~/.smith/` and can be resumed later by ID
- Two engines behind one interface: Google Gemini (default) and local LLaMA (works offline)
- Resilient Gemini client: optional proxy, automatic retries, total response timeout and an optional fallback model
- Token counter after every answer
- Export of a session to PDF (`/pdf`)
- Write-ahead log of all prompts and answers (`smith-wal.json`)
- Animated progress bar while waiting for the model

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # then put your GEMINI_API_KEY in it
python src/run.py
```

You get the API key at https://aistudio.google.com/apikey. Type a message and press Enter; type `/help` to see the available commands and `/exit` to leave (the session is saved automatically).

# setup/requirements

- create a venv: `python -m venv .venv`
- activate the venv: `source .venv/bin/activate`
- install dependencies: `pip install -r requirements.txt`

### dependencies

- `google-genai` - Google Gemini API client
- `llama-cpp-python` - client for local LLaMA models (GGUF)
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
GEMINI_TIMEOUT=30 # optional, max seconds to wait for a whole response incl. retries (default 30)
```
`GEMINI_PROXY_URL` is optional: when set, Gemini API requests are sent to this base URL instead of the default Google endpoint.

### Local LLaMA (llama-cpp-python)
For local LLaMA models, set:
```bash
ENGINE=LLAMA_CPP
MODEL_NAME=llama-3.1-8b-instruct
LLAMA_MODEL_PATH=/path/to/your/model.gguf
LLAMA_GPU_LAYERS=1
LLAMA_CONTEXT_SIZE=2048
```

**Engine selection:** the client is picked from the `ENGINE` variable: `GEMINI` uses `GeminiLLMClient`, `LLAMA_CPP` uses `LlamaClient`.

### Example: using LLaMA

1. Set the environment variables in `.env`:
```bash
ENGINE=LLAMA_CPP
MODEL_NAME=llama-3.1-8b-instruct
LLAMA_MODEL_PATH=/Users/tomaszku/Library/Caches/llama.cpp/bartowski_Meta-Llama-3.1-8B-Instruct-GGUF_Meta-Llama-3.1-8B-Instruct-Q8_0.gguf
LLAMA_GPU_LAYERS=1
LLAMA_CONTEXT_SIZE=2048
```

2. Run the application - LlamaClient is used because of `ENGINE=LLAMA_CPP`:
```bash
python src/run.py
```

3. The local model is loaded from `LLAMA_MODEL_PATH`.

## running

- activate the venv: `source .venv/bin/activate`
- run: `python src/run.py`
- resume a session: `python src/run.py --session-id=<ID>`

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
- If a request fails, the chat stays open and you can just send the message again.

## Project layout

```
src/
  run.py, chat.py        entry point and main loop
  cli/                   prompt, console output, CLI arguments
  command_handler.py     slash commands (implementations in commands/)
  session/               SessionManager and ChatSession
  llm/                   GeminiLLMClient, LlamaClient and config validation
  assistant/             assistant definition and system prompt
  files/                 config, session files, WAL, PDF export
```

## Architecture

### Session management

The application uses a two-class session management system:

#### **`ChatSession`** (a single chat session)
Represents one chat session and contains:
- **Unique session identifier** (`session_id`)
- **Conversation history** (all messages)
- **LLM session** (internal Google GenAI object)
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

The application supports different LLM model types through a unified interface:

#### **`GeminiLLMClient`** (Google Gemini API)
- Supports Gemini models through the Google API
- Requires an API key (`GEMINI_API_KEY`)
- Optionally routes requests through a proxy (`GEMINI_PROXY_URL`)
- Optionally switches to a fallback model (`GEMINI_FALLBACK_MODEL`) when the main model does not finish a response within `GEMINI_TIMEOUT` seconds in total (retries and slow responses included) or still returns a server error (5xx, e.g. 503) after all retries, and prints a notice naming both models; the switch lasts for the rest of that chat session and keeps the history
- Automatically retries transient errors (HTTP 429/500/502/503/504) up to 5 attempts with exponential backoff
- Supports Gemini features: thinking budget, structured responses

#### **`LlamaClient`** (local LLaMA models)
- Supports local GGUF models through llama-cpp-python
- Requires no internet connection
- Configurable parameters: GPU layers, context size (the token counter uses `LLAMA_CONTEXT_SIZE` as its limit)
- Uses `create_chat_completion`, so the model's built-in chat template (e.g. Llama 3.1's) is applied to the system prompt and history
- Interface compatible with GeminiLLMClient

**Selection:** `ChatSession` picks the right client from the `ENGINE` environment variable.
