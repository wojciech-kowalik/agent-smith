"""
Engine-independent chat session built on a LangChain chat model (or a runnable wrapping one).
"""

import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional
from langchain_core.messages import HumanMessage
from langchain_core.runnables import Runnable
from .history import history_to_messages, make_entry


@dataclass
class LLMResponse:
    """
    Response of one exchange; `.text` is the full answer.

    output_tokens: tokens the model generated (None when they are unknown)
    generation_seconds: time spent generating them (first token to last; the whole
        request when the answer arrived in one piece)
    """
    text: str
    output_tokens: Optional[int] = None
    generation_seconds: float = 0.0

    @property
    def tokens_per_second(self) -> Optional[float]:
        """Generation speed, or None when tokens or time are unknown."""
        if not self.output_tokens or self.generation_seconds <= 0:
            return None
        return self.output_tokens / self.generation_seconds


class LangChainChatSession:
    """
    Keeps one conversation's history (stored format) and talks to any LangChain chat model.
    The answer is always streamed; without `on_token` it is simply collected.
    """

    def __init__(self, model: Runnable, system_instruction: str, history: Optional[List[Dict]] = None,
                 count_output_tokens: Optional[Callable[[str], int]] = None):
        """
        Args:
            count_output_tokens: Counts the tokens of an answer when the engine does not
                report them in the stream (llama.cpp); used for the speed statistics
        """
        self._model = model
        self._system_instruction = system_instruction
        self._history: List[Dict] = list(history or [])
        self._count_output_tokens = count_output_tokens

    def send_message(self, text: str, on_token: Optional[Callable[[str], None]] = None) -> LLMResponse:
        """
        Sends a user message and returns the full answer with generation statistics.
        The history is updated only when the model answered, so a failed call can be retried.

        Args:
            text: User's message
            on_token: Optional callback called with each piece of the answer as it arrives
        """
        messages = history_to_messages(self._history, self._system_instruction)
        messages.append(HumanMessage(content=text))

        started = time.perf_counter()
        first_piece_at: Optional[float] = None
        last_piece_at = started
        reported_tokens: Optional[int] = None
        pieces: List[str] = []

        for chunk in self._model.stream(messages):
            usage = getattr(chunk, "usage_metadata", None)
            if usage and usage.get("output_tokens"):
                reported_tokens = usage["output_tokens"]  # cumulative: the last value wins
            if chunk.text:
                now = time.perf_counter()
                first_piece_at = first_piece_at or now
                last_piece_at = now
                pieces.append(chunk.text)
                if on_token:
                    on_token(chunk.text)
        answer = "".join(pieces).strip()

        # Time from the first to the last piece = pure generation; one piece = whole request
        if first_piece_at is None:
            generation_seconds = 0.0
        elif first_piece_at == last_piece_at:
            generation_seconds = last_piece_at - started
        else:
            generation_seconds = last_piece_at - first_piece_at
        output_tokens = reported_tokens
        if output_tokens is None and self._count_output_tokens and answer:
            output_tokens = self._count_output_tokens(answer)

        self._history.append(make_entry("user", text))
        self._history.append(make_entry("model", answer))
        return LLMResponse(answer, output_tokens, generation_seconds)

    def get_history(self) -> List[Dict]:
        """Returns the conversation history in the stored format."""
        return self._history
