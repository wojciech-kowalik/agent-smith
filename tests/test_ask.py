import io

import pytest

import ask
from cli.args import parse_args
from llm.chat_session import LLMResponse


class FakeStdin(io.StringIO):
    def __init__(self, text="", tty=False):
        super().__init__(text)
        self._tty = tty

    def isatty(self):
        return self._tty


class FakeSession:
    def __init__(self, text="the answer", fail=False):
        self.saved = False
        self.asked = None
        self._text, self._fail = text, fail

    def send_message(self, text, on_token=None):
        if self._fail:
            raise RuntimeError("model down")
        self.asked = text
        print("noise that must not reach stdout")
        return LLMResponse(self._text)

    def save_to_file(self):
        self.saved = True
        return True, None


@pytest.fixture(autouse=True)
def no_server(monkeypatch):
    # Never talk to a real Smith server that may be running on the developer's machine
    monkeypatch.setattr(ask.server, "request", lambda payload, path=None: None)


@pytest.fixture
def session(monkeypatch):
    s = FakeSession()
    monkeypatch.setattr(ask, "open_session", lambda session_id, llm_client=None: s)
    return s


def test_ask_flag_parsing():
    assert parse_args([]).ask is None
    assert parse_args(["--ask", "hi"]).ask == "hi"
    assert parse_args(["-p"]).ask == "-"
    assert parse_args(["--ask", "hi", "--session-id", "x"]).session_id == "x"


def test_stdout_has_only_the_answer(session, capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin", FakeStdin(tty=True))
    assert ask.run_ask("hello") == 0
    out, err = capsys.readouterr()
    assert out == "the answer\n"
    assert "noise" in err
    assert session.asked == "hello"


def test_piped_stdin_is_added_as_context(session, monkeypatch):
    monkeypatch.setattr("sys.stdin", FakeStdin("diff text"))
    ask.run_ask("review this", use_stdin=True)
    assert session.asked == "review this\n\ndiff text"


def test_stdin_is_not_read_unless_requested(session, monkeypatch):
    class Hanging(FakeStdin):
        def read(self, *a):
            raise AssertionError("must not block on stdin")
    monkeypatch.setattr("sys.stdin", Hanging("idle pipe"))
    ask.run_ask("hello")
    assert session.asked == "hello"


def test_question_from_stdin(session, monkeypatch):
    monkeypatch.setattr("sys.stdin", FakeStdin("from pipe"))
    ask.run_ask("-")
    assert session.asked == "from pipe"


def test_empty_question_fails(session, capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin", FakeStdin(tty=True))
    assert ask.run_ask("-") == 2
    assert capsys.readouterr().out == ""


def test_not_saved_without_session_id(session, monkeypatch):
    monkeypatch.setattr("sys.stdin", FakeStdin(tty=True))
    ask.run_ask("hello")
    assert not session.saved
    ask.run_ask("hello", "abc")
    assert session.saved


def test_failure_goes_to_stderr_with_nonzero_exit(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", FakeStdin(tty=True))
    monkeypatch.setattr(ask, "open_session", lambda session_id, llm_client=None: FakeSession(fail=True))
    assert ask.run_ask("hello") == 1
    out, err = capsys.readouterr()
    assert out == ""
    assert "model down" in err
