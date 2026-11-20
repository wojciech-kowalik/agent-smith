"""
Engine-independent chat session built on a LangChain chat model (or a runnable wrapping one).
"""

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional
from langchain_core.runnables import Runnable
from langchain_core.messages import HumanMessage
from .history import history_to_messages, make_entry


@dataclass
class LLMResponse:
    """Response of one exchange; `.text` is the full answer."""
    text: str


class LangChainChatSession:
    """
    Keeps one conversation's history (stored format) and talks to any LangChain chat model.
    The answer is always streamed; without `on_token` it is simply collected.
    """

    def __init__(self, model: Runnable, system_instruction: str, history: Optional[List[Dict]] = None):
        self._model = model
        self._system_instruction = system_instruction
        self._history: List[Dict] = list(history or [])

    def send_message(self, text: str, on_token: Optional[Callable[[str], None]] = None) -> LLMResponse:
        """
        Sends a user message and returns the full answer.
        The history is updated only when the model answered, so a failed call can be retried.

        Args:
            text: User's message
            on_token: Optional callback called with each piece of the answer as it arrives
        """
        messages = history_to_messages(self._history, self._system_instruction)
        messages.append(HumanMessage(content=text))

        pieces: List[str] = []
        for chunk in self._model.stream(messages):
            if chunk.text:
                pieces.append(chunk.text)
                if on_token:
                    on_token(chunk.text)
        answer = "".join(pieces).strip()

        self._history.append(make_entry("user", text))
        self._history.append(make_entry("model", answer))
        return LLMResponse(answer)

    def get_history(self) -> List[Dict]:
        """Returns the conversation history in the stored format."""
        return self._history
