import pytest

from llm.chat_session import LLMResponse


@pytest.mark.parametrize("tokens, seconds", [
    (None, 2.0),   # tokens unknown
    (0, 2.0),      # nothing generated
    (50, 0.0),     # no measurable time
    (50, -1.0),    # nonsense time
])
def test_speed_is_none_without_tokens_or_time(tokens, seconds):
    assert LLMResponse("text", tokens, seconds).tokens_per_second is None


def test_speed_is_tokens_divided_by_seconds():
    assert LLMResponse("text", 50, 2.0).tokens_per_second == 25.0


def test_defaults_mean_unknown_speed():
    response = LLMResponse("text")
    assert response.output_tokens is None
    assert response.tokens_per_second is None
