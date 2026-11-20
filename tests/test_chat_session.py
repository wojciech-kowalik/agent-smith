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


def test_response_has_no_speed_when_tokens_unknown(make_client):
    response = make_client("some answer").create_chat_session("sys").send_message("q")
    assert response.output_tokens is None
    assert response.tokens_per_second is None


def test_tokens_counted_locally_give_speed(make_client):
    client = make_client("Hello there friend", token_counter=lambda messages: 30, count_answer_tokens=True)
    response = client.create_chat_session("sys").send_message("q")
    assert response.output_tokens == 30
    assert response.generation_seconds > 0
    assert response.tokens_per_second == 30 / response.generation_seconds


def test_reported_usage_is_preferred_over_local_counting():
    from langchain_core.messages import AIMessageChunk
    from langchain_core.runnables import RunnableLambda

    def stream(_messages):
        yield AIMessageChunk(content="Hi ")
        yield AIMessageChunk(content="there", usage_metadata={"input_tokens": 5, "output_tokens": 9, "total_tokens": 14})

    model = RunnableLambda(lambda m: None)
    model.stream = lambda messages: stream(messages)
    session = LangChainChatSession(model, "sys", count_output_tokens=lambda text: 1)
    assert session.send_message("q").output_tokens == 9


def test_speed_statistics_do_not_break_empty_answers():
    from langchain_core.messages import AIMessageChunk
    from langchain_core.runnables import RunnableLambda

    model = RunnableLambda(lambda m: None)
    model.stream = lambda messages: iter([AIMessageChunk(content="")])
    response = LangChainChatSession(model, "sys", count_output_tokens=lambda t: 1).send_message("q")
    assert response.text == ""
    assert response.tokens_per_second is None


class FakeClock:
    """Replaces time.perf_counter: every call advances the clock by `step` seconds."""

    def __init__(self, step=1.0):
        self.now, self.step = 0.0, step

    def __call__(self):
        self.now += self.step
        return self.now


def _streaming_model(*chunks):
    from langchain_core.messages import AIMessageChunk
    from langchain_core.runnables import RunnableLambda

    model = RunnableLambda(lambda m: None)
    model.stream = lambda messages: iter([AIMessageChunk(content=c) for c in chunks])
    return model


def test_generation_time_runs_from_first_to_last_piece(monkeypatch):
    # perf_counter calls: start=1, piece1=2, piece2=3, piece3=4 -> generation 4 - 2 = 2s
    monkeypatch.setattr("llm.chat_session.time.perf_counter", FakeClock())
    session = LangChainChatSession(_streaming_model("a", "b", "c"), "sys", count_output_tokens=lambda t: 6)
    response = session.send_message("q")
    assert response.generation_seconds == 2.0
    assert response.tokens_per_second == 3.0


def test_single_piece_is_timed_over_the_whole_request(monkeypatch):
    # start=1, piece=2 -> 1s from the start of the request
    monkeypatch.setattr("llm.chat_session.time.perf_counter", FakeClock())
    session = LangChainChatSession(_streaming_model("whole answer"), "sys", count_output_tokens=lambda t: 4)
    response = session.send_message("q")
    assert response.generation_seconds == 1.0
    assert response.tokens_per_second == 4.0


def test_last_reported_usage_wins():
    from langchain_core.messages import AIMessageChunk
    from langchain_core.runnables import RunnableLambda

    def usage(n):
        return {"input_tokens": 1, "output_tokens": n, "total_tokens": 1 + n}

    model = RunnableLambda(lambda m: None)
    model.stream = lambda messages: iter([
        AIMessageChunk(content="a", usage_metadata=usage(3)),
        AIMessageChunk(content="b", usage_metadata=usage(7)),
    ])
    assert LangChainChatSession(model, "sys").send_message("q").output_tokens == 7


def test_local_counter_receives_the_answer_text():
    seen = []
    session = LangChainChatSession(_streaming_model("Hello ", "world"), "sys",
                                   count_output_tokens=lambda text: seen.append(text) or 2)
    session.send_message("q")
    assert seen == ["Hello world"]


def test_stats_do_not_change_the_history(make_client):
    client = make_client("Hello there", token_counter=lambda m: 5, count_answer_tokens=True)
    session = client.create_chat_session("sys")
    session.send_message("q")
    assert session.get_history() == [make_entry("user", "q"), make_entry("model", "Hello there")]
