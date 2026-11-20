"""
Picks the LLM engine from the ENGINE environment variable.
"""

import os
from typing import Callable, Dict
from .client import LLMClient
from .gemini import create_gemini_client
from .llama import create_llama_client

ENGINES: Dict[str, Callable[[], LLMClient]] = {
    'LLAMA_CPP': create_llama_client,
    'GEMINI': create_gemini_client,
}


def create_llm_client() -> LLMClient:
    """
    Creates the client of the engine named in ENGINE (GEMINI by default).

    Raises:
        ValueError: If ENGINE is not a known engine
    """
    engine = os.getenv('ENGINE', 'GEMINI').upper()
    if engine not in ENGINES:
        raise ValueError(f"ENGINE must be one of: {', '.join(ENGINES)}, got: {engine}")
    return ENGINES[engine]()
