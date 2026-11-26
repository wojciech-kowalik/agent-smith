"""Smith server: keeps the model loaded in memory (VRAM) between one-shot questions.

Without it every `--ask` loads the whole model and frees it again. With `--serve` one process
holds the model and answers requests over a Unix socket; `--ask` uses it automatically when it
is running (and falls back to loading the model itself when it is not).

Requests are served one at a time (one model, one context): parallel callers do not fail, they
wait in a queue. The model stays in memory until `--stop` (or SIGTERM) ends the process.
"""
import json
import os
import signal
import socket
import socketserver
import sys
import threading
import time

from files.config import LOG_DIR
from gpu import gpu_report, memory_label, process_memory_mib

SOCKET_PATH = os.path.join(LOG_DIR, 'smith.sock')


def request(payload: dict, path: str = SOCKET_PATH) -> dict | None:
    """Sends one request to the running server and returns its reply (None: no server running)."""
    conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        conn.connect(path)
    except (FileNotFoundError, ConnectionRefusedError):
        conn.close()
        return None
    with conn:
        conn.sendall(json.dumps(payload).encode('utf-8'))
        conn.shutdown(socket.SHUT_WR)  # end of the request
        raw = b''.join(iter(lambda: conn.recv(65536), b''))
    if not raw:
        return {"error": "the Smith server closed the connection (was it stopped?)"}
    return json.loads(raw)


class SmithServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True

    def __init__(self, path: str, llm_client):
        self.llm_client = llm_client
        self.inference_lock = threading.Lock()  # one generation at a time
        super().__init__(path, _Handler)

    def handle_payload(self, payload: dict) -> dict:
        command = payload.get("cmd")
        if command == "status":
            return {"ok": True, "model": self.llm_client.get_model_name(), "busy": self.inference_lock.locked(),
                    "gpu": gpu_report(os.getpid()), "pid": os.getpid(),
                    "held_mib": process_memory_mib(os.getpid())}
        if command == "stop":
            with self.inference_lock:  # let a running generation finish first
                threading.Thread(target=self.shutdown, daemon=True).start()
            return {"ok": True}
        from ask import open_session  # lazy: ask imports this module
        with self.inference_lock:
            session = open_session(payload.get("session_id"), self.llm_client)
            response = session.send_message(payload["question"])
            if payload.get("session_id"):
                success, error = session.save_to_file()
                if not success and error:
                    print(f"Error saving session: {error}", file=sys.stderr)
        return {"text": response.text}


class _Handler(socketserver.StreamRequestHandler):
    def handle(self):
        try:
            reply = self.server.handle_payload(json.loads(self.rfile.read()))
        except Exception as e:
            reply = {"error": str(e)}
        self.wfile.write(json.dumps(reply).encode('utf-8'))


def _drop_socket_file(path: str):
    if os.path.exists(path):
        os.unlink(path)


def serve(path: str = SOCKET_PATH) -> int:
    """Loads the model and answers requests until stopped. Returns the exit code."""
    if request({"cmd": "status"}, path) is not None:
        print("The Smith server is already running.", file=sys.stderr)
        return 1
    _drop_socket_file(path)  # left over from a crashed server

    from llm import create_llm_client
    client = create_llm_client()
    print(client.ready_for_use_message(), flush=True)
    for line in gpu_report(os.getpid()):  # measured after loading: shows what the model took
        print(line, flush=True)

    server = SmithServer(path, client)
    signal.signal(signal.SIGTERM, lambda *_: threading.Thread(target=server.shutdown, daemon=True).start())
    print(f"Smith server ready on {path}. Stop it with: python src/run.py --stop", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        _drop_socket_file(path)
    print("Smith server stopped; the model is released from memory.", flush=True)
    return 0


def status(path: str = SOCKET_PATH) -> int:
    reply = request({"cmd": "status"}, path)
    if reply is None:
        print("The Smith server is not running (the model is not held in memory).")
        return 1
    print(f"The Smith server is running (model: {reply['model']}, {'busy' if reply['busy'] else 'idle'}).")
    for line in reply.get("gpu", []):
        print(line)
    return 0


def _wait_for_exit(pid: int, timeout: float = 60.0) -> bool:
    """True once the process `pid` is gone (its VRAM is released only then)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        time.sleep(0.2)
    return False


def stop(path: str = SOCKET_PATH) -> int:
    before = request({"cmd": "status"}, path)
    if before is None or request({"cmd": "stop"}, path) is None:
        print("The Smith server is not running; nothing to stop.")
        return 0
    print("The Smith server is stopping; the model will be released from memory.")
    if not _wait_for_exit(before["pid"]):
        print(f"Warning: the server (pid {before['pid']}) is still running after 60 s.", file=sys.stderr)
        return 1
    print("The Smith server stopped; the model is released from memory.")
    for line in gpu_report():
        print(line)
    if before.get("held_mib"):
        print(f"Smith (pid {before['pid']}) released {before['held_mib']} MiB of {memory_label()}")
    return 0
