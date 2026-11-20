from llm.history import make_entry


def test_basic_accessors(make_client):
    client = make_client(context_size=4096)
    assert client.get_model_name() == "fake-model"
    assert client.ready_for_use_message() == "ready"
    assert client.get_context_size() == 4096


def test_context_size_is_none_by_default(make_client):
    assert make_client().get_context_size() is None


def test_count_tokens_empty_history_is_zero(make_client):
    assert make_client().count_history_tokens([]) == 0


def test_custom_token_counter_is_used(make_client):
    client = make_client(token_counter=lambda messages: 42)
    assert client.count_history_tokens([make_entry("user", "hi")]) == 42


def test_token_counter_failure_falls_back_to_estimate(make_client):
    def boom(messages):
        raise RuntimeError("no tokenizer")

    client = make_client(token_counter=boom)
    # 40 characters -> ~10 tokens
    assert client.count_history_tokens([make_entry("user", "x" * 40)]) == 10


def test_runnable_answers_but_model_counts_tokens():
    from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
    from langchain_core.messages import AIMessage
    from llm import LLMClient

    def fake(text):
        return GenericFakeChatModel(messages=iter([AIMessage(content=text)]))

    client = LLMClient(fake("from-model"), "m", "ready", runnable=fake("from-runnable"),
                       token_counter=lambda messages: 7)
    assert client.create_chat_session("sys").send_message("q").text == "from-runnable"
    assert client.count_history_tokens([make_entry("user", "hi")]) == 7


def test_answer_tokens_are_not_counted_by_default(make_client):
    # API engines must not make an extra network call just for the speed statistics
    calls = []
    client = make_client("answer", token_counter=lambda m: calls.append(m) or 9)
    response = client.create_chat_session("sys").send_message("q")
    assert response.output_tokens is None
    assert calls == []


def test_answer_tokens_are_counted_with_the_token_counter_when_enabled(make_client):
    seen = []
    client = make_client("one two", token_counter=lambda m: seen.append([x.content for x in m]) or 9,
                         count_answer_tokens=True)
    response = client.create_chat_session("sys").send_message("q")
    assert response.output_tokens == 9
    assert seen == [["one two"]]
