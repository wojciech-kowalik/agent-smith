"""
Conversion between the on-disk history format and LangChain messages.

Sessions are stored as [{"role": "user|model", "parts": [{"text": "..."}]}, ...]
(see files/session_files.py). Keeping that format means existing session files keep working.
"""

from typing import Any, Dict, List
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage


def entry_text(entry: Dict[str, Any]) -> str:
    """Returns the text of one stored history entry ('' if it has none)."""
    parts = entry.get("parts") or []
    return parts[0].get("text", "") if parts else ""


def make_entry(role: str, text: str) -> Dict[str, Any]:
    """Builds one history entry in the stored format."""
    return {"role": role, "parts": [{"text": text}]}


def history_to_messages(history: List[Dict], system_instruction: str = "") -> List[BaseMessage]:
    """Converts stored history (optionally preceded by a system prompt) to LangChain messages."""
    messages: List[BaseMessage] = [SystemMessage(content=system_instruction)] if system_instruction else []
    for entry in history:
        text = entry_text(entry)
        if not text:
            continue
        messages.append(AIMessage(content=text) if entry.get("role") == "model" else HumanMessage(content=text))
    return messages
