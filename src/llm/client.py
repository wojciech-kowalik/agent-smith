"""
Engine-independent LLM client: a thin wrapper around a LangChain chat model.
"""

from typing import Callable, Dict, List, Optional
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.runnables import Runnable
from cli import console
from .chat_session import LangChainChatSession
from .history import history_to_messages


class LLMClient:
    """
    What the rest of the app needs from a model: chat sessions, token counting,
    a display name and (for local models) the real context window.
    """

    def __init__(self, model: BaseChatModel, model_name: str, ready_message: str,
                 context_size: Optional[int] = None, runnable: Optional[Runnable] = None,
                 token_counter: Optional[Callable[[List[BaseMessage]], int]] = None):
        """
        Args:
            model: The chat model (used for token counting)
            runnable: What actually answers; `model` itself unless it is wrapped
                (e.g. with fallbacks, which hides the model's token counting)
            token_counter: Overrides the model's own token counting
        """
        self.model = model
        self.runnable = runnable or model
        self._token_counter = token_counter or model.get_num_tokens_from_messages
        self.model_name = model_name
        self._ready_message = ready_message
        self._context_size = context_size

    def create_chat_session(self, system_instruction: str, history: Optional[List[Dict]] = None) -> LangChainChatSession:
        """Creates a chat session on this model, continuing the given history."""
        return LangChainChatSession(self.runnable, system_instruction, history)

    def count_history_tokens(self, history: List[Dict]) -> int:
        """Counts tokens of the history with the model's own tokenizer / token counting API."""
        if not history:
            return 0
        messages = history_to_messages(history)
        try:
            return self._token_counter(messages)
        except Exception as e:
            console.print_error(f"Error while counting tokens: {e}")
            # Rough estimate: ~4 characters per token
            return sum(len(str(m.content)) for m in messages) // 4

    def get_context_size(self) -> Optional[int]:
        """Context window of a local model (LLAMA_CONTEXT_SIZE); None when the engine does not report one."""
        return self._context_size

    def get_model_name(self) -> str:
        return self.model_name

    def ready_for_use_message(self) -> str:
        return self._ready_message
