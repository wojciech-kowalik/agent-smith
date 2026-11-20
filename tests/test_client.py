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
