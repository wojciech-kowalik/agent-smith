import pytest

from llm import factory


def test_unknown_engine_is_rejected(monkeypatch):
    monkeypatch.setenv("ENGINE", "NOPE")
    with pytest.raises(ValueError, match="ENGINE must be one of"):
        factory.create_llm_client()


def test_engine_is_case_insensitive_and_dispatched(monkeypatch):
    monkeypatch.setenv("ENGINE", "llama_cpp")
    monkeypatch.setitem(factory.ENGINES, "LLAMA_CPP", lambda: "llama-client")
    assert factory.create_llm_client() == "llama-client"


def test_gemini_is_the_default_engine(monkeypatch):
    monkeypatch.setitem(factory.ENGINES, "GEMINI", lambda: "gemini-client")
    assert factory.create_llm_client() == "gemini-client"
