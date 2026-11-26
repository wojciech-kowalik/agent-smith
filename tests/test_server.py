import io
import threading

import pytest

import ask
import server
from llm.chat_session import LLMResponse


class FakeClient:
    def get_model_name(self):
        return "fake-model"


class FakeSession:
    def __init__(self, text):
        self.text = text
        self.saved = False

    def send_message(self, text, on_token=None):
        return LLMResponse(f"{self.text}:{text}")

    def save_to_file(self):
        self.saved = True
        return True, None


@pytest.fixture
def running_server(tmp_path, monkeypatch):
    path = str(tmp_path / "s.sock")
    sessions = []

    def fake_open(session_id, llm_client=None):
        assert isinstance(llm_client, FakeClient)  # the shared, already loaded model
        sessions.append(FakeSession("answer"))
        return sessions[-1]

    monkeypatch.setattr(ask, "open_session", fake_open)
    srv = server.SmithServer(path, FakeClient())
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield path, sessions
    srv.shutdown()
    srv.server_close()


def test_no_server_means_no_reply(tmp_path):
    assert server.request({"cmd": "status"}, str(tmp_path / "none.sock")) is None


def test_status_and_question(running_server):
    path, _ = running_server
    reply = server.request({"cmd": "status"}, path)
    assert (reply["ok"], reply["model"], reply["busy"]) == (True, "fake-model", False)
    assert reply["gpu"]  # GPU lines (or the "not available" note)
    assert server.request({"question": "hi"}, path) == {"text": "answer:hi"}


def test_session_is_saved_only_with_session_id(running_server):
    path, sessions = running_server
    server.request({"question": "a"}, path)
    server.request({"question": "b", "session_id": "x"}, path)
    assert [s.saved for s in sessions] == [False, True]


def test_parallel_requests_are_all_answered(running_server):
    path, _ = running_server
    replies = [None] * 6

    def worker(i):
        replies[i] = server.request({"question": str(i)}, path)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(10)
    assert [r["text"] for r in replies] == [f"answer:{i}" for i in range(6)]


def test_stop_ends_the_server_loop(tmp_path):
    path = str(tmp_path / "s.sock")
    srv = server.SmithServer(path, FakeClient())
    done = threading.Event()
    threading.Thread(target=lambda: (srv.serve_forever(), done.set()), daemon=True).start()
    assert server.request({"cmd": "stop"}, path) == {"ok": True}
    assert done.wait(5)
    srv.server_close()


def test_ask_uses_the_server_and_reminds_about_stopping(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO())
    monkeypatch.setattr(server, "request", lambda payload, path=None: {"text": "from server"})
    monkeypatch.setattr(ask, "open_session", lambda *a, **k: pytest.fail("must not load the model"))
    assert ask.run_ask("hello") == 0
    out, err = capsys.readouterr()
    assert out == "from server\n"
    assert "make stop" in err


def test_ask_reports_server_errors(monkeypatch, capsys):
    monkeypatch.setattr(server, "request", lambda payload, path=None: {"error": "boom"})
    assert ask.run_ask("hello") == 1
    out, err = capsys.readouterr()
    assert out == "" and "boom" in err


def test_stop_reports_released_vram(monkeypatch, capsys):
    replies = iter([{"ok": True, "pid": 4242, "held_mib": 9700}, {"ok": True}])
    monkeypatch.setattr(server, "request", lambda payload, path=None: next(replies))
    monkeypatch.setattr(server, "_wait_for_exit", lambda pid, timeout=60.0: True)
    monkeypatch.setattr(server, "gpu_report", lambda pid=None, run=None: ["GPU 0: card | VRAM total 1 MiB, used 0 MiB, free 1 MiB"])
    assert server.stop() == 0
    out = capsys.readouterr().out
    assert "GPU 0: card" in out
    assert "released 9700 MiB of VRAM" in out


def test_stop_without_server_does_nothing(monkeypatch, capsys):
    monkeypatch.setattr(server, "request", lambda payload, path=None: None)
    assert server.stop() == 0
    assert "nothing to stop" in capsys.readouterr().out
