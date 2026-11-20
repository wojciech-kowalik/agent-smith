from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from llm.history import entry_text, history_to_messages, make_entry


def test_make_entry_and_text_roundtrip():
    assert entry_text(make_entry("user", "hi")) == "hi"


def test_entry_text_handles_missing_parts():
    assert entry_text({"role": "user"}) == ""
    assert entry_text({"role": "user", "parts": []}) == ""


def test_history_to_messages_maps_roles_and_adds_system_prompt():
    history = [make_entry("user", "a"), make_entry("model", "b")]
    messages = history_to_messages(history, "sys")
    assert [type(m) for m in messages] == [SystemMessage, HumanMessage, AIMessage]
    assert [m.content for m in messages] == ["sys", "a", "b"]


def test_history_to_messages_without_system_prompt_skips_empty_entries():
    history = [make_entry("user", ""), make_entry("user", "a")]
    messages = history_to_messages(history)
    assert [m.content for m in messages] == ["a"]
