import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

from llm.chat_session import LangChainChatSession
from llm.history import make_entry


def test_streams_pieces_and_returns_full_answer(make_client):
    session = make_client("Hello there friend").create_chat_session("sys")
    pieces = []
    response = session.send_message("hi", on_token=pieces.append)
    assert response.text == "Hello there friend"
    assert len(pieces) > 1
    assert "".join(pieces) == "Hello there friend"


def test_works_without_on_token(make_client):
    session = make_client("answer").create_chat_session("sys")
    assert session.send_message("q").text == "answer"


def test_history_is_updated_in_stored_format(make_client):
    session = make_client("a1", "a2").create_chat_session("sys")
    session.send_message("q1")
    session.send_message("q2")
    assert session.get_history() == [
        make_entry("user", "q1"), make_entry("model", "a1"),
        make_entry("user", "q2"), make_entry("model", "a2"),
    ]


def test_existing_history_is_continued_and_not_mutated(make_client):
    initial = [make_entry("user", "old"), make_entry("model", "older")]
    session = make_client("new").create_chat_session("sys", initial)
    session.send_message("q")
    assert len(session.get_history()) == 4
    assert len(initial) == 2


def test_model_receives_system_prompt_history_and_new_message():
    seen = []

    class Recorder(GenericFakeChatModel):
        def _stream(self, messages, *args, **kwargs):
            seen.extend(messages)
            return super()._stream(messages, *args, **kwargs)

    from langchain_core.messages import AIMessage
    model = Recorder(messages=iter([AIMessage(content="ok")]))
    session = LangChainChatSession(model, "sys", [make_entry("user", "a"), make_entry("model", "b")])
    session.send_message("c")
    assert [(m.type, m.content) for m in seen] == [("system", "sys"), ("human", "a"), ("ai", "b"), ("human", "c")]


def test_failed_call_leaves_history_unchanged(make_client):
    session = make_client().create_chat_session("sys")  # model has no answers -> raises
    with pytest.raises(Exception):
        session.send_message("q")
    assert session.get_history() == []
