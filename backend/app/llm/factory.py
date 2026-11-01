"""
AI Research Assistant — LLM Provider Factory

Selects the appropriate LLM provider based on configuration.
NEVER silently falls back to the builtin provider — always surfaces
real errors so the chat endpoint can report them to the user.
"""

from __future__ import annotations

from loguru import logger

from app.core.config import settings
from app.llm.base import BaseLLMProvider


_provider_instance: BaseLLMProvider | None = None


def get_llm_provider() -> BaseLLMProvider:
    """
    Return the configured LLM provider (singleton).

    The provider is determined by ``settings.LLM_PROVIDER``:
        - "gemini" → Google Gemini API (recommended, free tier available)
        - "openai" → OpenAI API
        - "ollama" → local Ollama server
        - "builtin" → built-in static responses (NOT a real LLM)

    If the configured external provider fails to initialize, the error
    is raised so it can be surfaced to the user.  The old behavior of
    silently falling back to the builtin provider was the root cause of
    the "same answer for every question" bug.
    """
    global _provider_instance

    if _provider_instance is not None:
        return _provider_instance

    provider_name = settings.LLM_PROVIDER.lower().strip()

    if provider_name == "gemini":
        from app.llm.gemini_provider import GeminiProvider
        _provider_instance = GeminiProvider()

    elif provider_name == "openai":
        from app.llm.openai_provider import OpenAIProvider
        _provider_instance = OpenAIProvider()

    elif provider_name == "ollama":
        from app.llm.ollama_provider import OllamaProvider
        _provider_instance = OllamaProvider()

    elif provider_name == "builtin":
        from app.llm.builtin_provider import BuiltinProvider
        logger.warning(
            "Using built-in provider — this returns STATIC responses, "
            "not real AI answers.  Set LLM_PROVIDER=gemini in .env for "
            "actual AI responses."
        )
        _provider_instance = BuiltinProvider()

    else:
        raise ValueError(
            f"Unknown LLM provider: '{provider_name}'. "
            f"Valid options: gemini, openai, ollama, builtin. "
            f"Set LLM_PROVIDER in your .env file."
        )

    logger.info(f"LLM provider: {_provider_instance.get_model_name()}")
    return _provider_instance


def reset_provider() -> None:
    """Reset the cached provider instance (useful for testing or reconfiguration)."""
    global _provider_instance
    _provider_instance = None
