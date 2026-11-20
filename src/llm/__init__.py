"""
LLM module: LangChain-based clients for Gemini and local llama.cpp models.
"""

from .client import LLMClient
from .factory import create_llm_client

__all__ = ['LLMClient', 'create_llm_client']
