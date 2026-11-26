"""One-shot mode (`--ask`): send a single question and print only the answer.

Meant for scripts and other tools (e.g. Claude Code): stdout carries just the answer,
everything else (model info, errors) goes to stderr, and the exit code tells if it worked.
"""
import contextlib
import sys

import server
from session.chat_session import ChatSession
from assistant import create_smith_assistant


SERVER_REMINDER = ("[smith] The Smith server keeps the model in VRAM. When you are done with Smith, "
                   "free it with: make stop (python src/run.py --stop)")


def read_question(ask_value: str, use_stdin: bool = False, stdin=None) -> str:
    """The question from --ask, or from stdin when the value is '-'.

    Stdin is read only on request ('-' or --stdin): a caller that leaves an idle pipe open
    (Claude Code, cron) would otherwise hang the program forever. With --stdin the piped text
    is appended to the question as context (`git diff | run.py --ask "review this" --stdin`).
    """
    if ask_value != '-' and not use_stdin:
        return ask_value
    stdin = stdin or sys.stdin
    piped = "" if stdin.isatty() else stdin.read().strip()
    if ask_value == '-':
        return piped
    return f"{ask_value}\n\n{piped}" if piped else ask_value


def run_ask(ask_value: str, session_id: str | None = None, use_stdin: bool = False) -> int:
    """Answers one question. Returns the process exit code (0 = answer printed)."""
    question = read_question(ask_value, use_stdin)
    if not question:
        print("Error: empty question (pass it after --ask or pipe it on stdin).", file=sys.stderr)
        return 2

    # A running Smith server already holds the model: no loading, and parallel callers just queue
    reply = server.request({"question": question, "session_id": session_id})
    if reply is not None:
        if "error" in reply:
            print(f"Error: {reply['error']}", file=sys.stderr)
            return 1
        print(reply["text"])
        print(SERVER_REMINDER, file=sys.stderr)
        return 0

    # Anything the app prints while starting up and generating must not pollute the answer
    with contextlib.redirect_stdout(sys.stderr):
        try:
            session = open_session(session_id)
            response = session.send_message(question)
            if session_id:
                success, error = session.save_to_file()
                if not success and error:
                    print(f"Error saving session: {error}", file=sys.stderr)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    print(response.text)
    return 0


def open_session(session_id: str | None, llm_client=None) -> ChatSession:
    """A fresh session, or the saved one. `llm_client` reuses an already loaded model."""
    assistant = create_smith_assistant()
    if not session_id:
        return ChatSession(assistant=assistant, llm_client=llm_client)
    session, error = ChatSession.load_from_file(assistant=assistant, session_id=session_id, llm_client=llm_client)
    if error:
        raise RuntimeError(error)
    return session
