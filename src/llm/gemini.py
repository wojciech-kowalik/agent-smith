"""
Google Gemini engine (langchain-google-genai).
"""

import os
from typing import Optional
from dotenv import load_dotenv
from google.genai import errors as genai_errors
from langchain_google_genai import ChatGoogleGenerativeAI
from cli import console
from .client import LLMClient
from .gemini_validation import GeminiConfig

PREPARING_MESSAGE = "🤖 Preparing the Gemini client..."


def _timeout_exceptions() -> tuple:
    """Timeout exception classes of the HTTP library used by google-genai (httpx2 by default, or httpx)."""
    classes = []
    for module_name in ("httpx2", "httpx"):
        try:
            classes.append(__import__(module_name).TimeoutException)
        except (ImportError, AttributeError):
            pass
    return tuple(classes)


# Failures after which the fallback model is tried (not auth / bad request / unknown model errors)
FALLBACK_TRIGGERS = (genai_errors.ServerError, TimeoutError, *_timeout_exceptions())


def _chat_model(model_name: str, config: GeminiConfig) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=model_name,
        api_key=config.gemini_api_key,
        base_url=config.gemini_proxy_url,
        timeout=config.gemini_timeout,
        max_retries=5,  # transient errors (429 / 5xx) with exponential backoff
        thinking_budget=0,
    )


def create_gemini_client() -> LLMClient:
    """Builds the Gemini client from environment variables."""
    load_dotenv()
    config = GeminiConfig(
        model_name=os.getenv('MODEL_NAME', 'gemini-3.8-flash'),
        gemini_api_key=os.getenv('GEMINI_API_KEY', ''),
        gemini_proxy_url=os.getenv('GEMINI_PROXY_URL'),
        gemini_fallback_model=os.getenv('GEMINI_FALLBACK_MODEL'),
        gemini_timeout=os.getenv('GEMINI_TIMEOUT') or 30
    )
    console.print_info(PREPARING_MESSAGE)

    model = _chat_model(config.model_name, config)
    runnable = model
    fallback = config.gemini_fallback_model
    if fallback and fallback != config.model_name:
        runnable = model.with_fallbacks([_chat_model(fallback, config)], exceptions_to_handle=FALLBACK_TRIGGERS)

    key = config.gemini_api_key
    masked_key = "****" if len(key) <= 8 else f"{key[:4]}...{key[-4:]}"
    proxy_info = f", Proxy: {config.gemini_proxy_url}" if config.gemini_proxy_url else ""
    fallback_info = f", Fallback: {fallback}" if fallback else ""
    ready = f"✅ Gemini client ready to use (Model: {config.model_name}, Key: {masked_key}{proxy_info}{fallback_info})"
    return LLMClient(model, config.model_name, ready, runnable=runnable)
