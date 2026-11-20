import pytest

import chat
from llm.chat_session import LLMResponse


class FakeSession:
    assistant_name = "SMITH"

    def __init__(self, response):
        self._response = response

    def send_message(self, text, on_token=None):
        if on_token:
            on_token(self._response.text)
        return self._response

    def get_token_info(self):
        return 10, 90, 100

    def save_to_file(self):
        return True, None


class FakeManager:
    def __init__(self, session):
        self._session = session

    def get_current_session(self):
        return self._session


@pytest.fixture
def run_loop(monkeypatch):
    """Runs one user message through chat.main_loop and returns the info lines it printed."""
    def _run(response):
        inputs = iter(["hello"])

        def fake_input():
            try:
                return next(inputs)
            except StopIteration:
                raise EOFError

        info = []
        monkeypatch.setattr(chat, "get_session_manager", lambda: FakeManager(FakeSession(response)))
        monkeypatch.setattr(chat, "get_user_input", fake_input)
        monkeypatch.setattr(chat.console, "print_stats", info.append)
        chat.main_loop()
        return info
    return _run


def test_speed_line_is_printed_after_the_token_counter(run_loop):
    info = run_loop(LLMResponse("answer", output_tokens=51, generation_seconds=1.5))
    token_line = next(i for i, line in enumerate(info) if line.startswith("Tokens: 10"))
    assert info[token_line + 1] == "Speed: 34.0 tokens/s (51 tokens in 1.5s)"


def test_speed_line_is_skipped_when_tokens_unknown(run_loop):
    info = run_loop(LLMResponse("answer"))
    assert any(line.startswith("Tokens: 10") for line in info)
    assert not any(line.startswith("Speed:") for line in info)
