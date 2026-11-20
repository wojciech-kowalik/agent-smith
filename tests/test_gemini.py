import pytest
from langchain_core.runnables import RunnableWithFallbacks
from pydantic import ValidationError

from llm.gemini import FALLBACK_TRIGGERS, create_gemini_client
from google.genai import errors as genai_errors


@pytest.fixture
def gemini_env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "abcdefghijkl")
    monkeypatch.setenv("MODEL_NAME", "gemini-main")


def test_missing_api_key_is_rejected():
    with pytest.raises(ValidationError):
        create_gemini_client()


def test_invalid_proxy_url_is_rejected(gemini_env, monkeypatch):
    monkeypatch.setenv("GEMINI_PROXY_URL", "ftp://proxy")
    with pytest.raises(ValidationError):
        create_gemini_client()


def test_client_without_fallback(gemini_env):
    client = create_gemini_client()
    assert client.get_model_name() == "gemini-main"
    assert client.runnable is client.model
    assert "abcd...ijkl" in client.ready_for_use_message()
    assert "abcdefghijkl" not in client.ready_for_use_message()
    assert client.get_context_size() is None


def test_fallback_model_wraps_runnable_but_not_model(gemini_env, monkeypatch):
    monkeypatch.setenv("GEMINI_FALLBACK_MODEL", "gemini-backup")
    client = create_gemini_client()
    assert isinstance(client.runnable, RunnableWithFallbacks)
    assert client.model is not client.runnable
    assert "Fallback: gemini-backup" in client.ready_for_use_message()


def test_fallback_equal_to_main_model_is_ignored(gemini_env, monkeypatch):
    monkeypatch.setenv("GEMINI_FALLBACK_MODEL", "gemini-main")
    client = create_gemini_client()
    assert client.runnable is client.model


def test_proxy_and_timeout_are_passed_to_the_model(gemini_env, monkeypatch):
    monkeypatch.setenv("GEMINI_PROXY_URL", "https://proxy.example.com")
    monkeypatch.setenv("GEMINI_TIMEOUT", "12")
    model = create_gemini_client().model
    assert model.base_url == "https://proxy.example.com"
    assert model.timeout == 12
    assert model.max_retries == 5


def test_fallback_triggers_cover_server_errors_and_timeouts_only():
    assert genai_errors.ServerError in FALLBACK_TRIGGERS
    assert TimeoutError in FALLBACK_TRIGGERS
    assert genai_errors.ClientError not in FALLBACK_TRIGGERS
