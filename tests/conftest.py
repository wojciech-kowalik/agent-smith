import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from llm import LLMClient


def fake_model(*answers: str) -> GenericFakeChatModel:
    return GenericFakeChatModel(messages=iter([AIMessage(content=a) for a in answers]))


@pytest.fixture
def make_client():
    def _make(*answers: str, **kwargs) -> LLMClient:
        return LLMClient(fake_model(*answers), "fake-model", "ready", **kwargs)
    return _make


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    # Tests must not depend on (or load) the developer's real .env
    monkeypatch.setattr("llm.gemini.load_dotenv", lambda *a, **k: False)
    monkeypatch.setattr("llm.llama.load_dotenv", lambda *a, **k: False)
    for name in ("ENGINE", "MODEL_NAME", "GEMINI_API_KEY", "GEMINI_PROXY_URL", "GEMINI_FALLBACK_MODEL",
                 "GEMINI_TIMEOUT", "LLAMA_MODEL_PATH", "LLAMA_MODEL_NAME"):
        monkeypatch.delenv(name, raising=False)
