"""
AI Research Assistant — LLM Base Provider

Abstract interface for all LLM providers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LLMMessage:
    """A single message in a conversation."""

    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class LLMResponse:
    """Response from an LLM provider."""

    content: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    finish_reason: str = "stop"


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate(
        self,
        messages: list[LLMMessage],
        max_tokens: int | None = None,
        temperature: float = 0.7,
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """
        Generate a response given a list of messages.

        Args:
            messages: Conversation history as LLMMessage objects.
            max_tokens: Maximum tokens in the response.
            temperature: Sampling temperature (0 = deterministic, 1 = creative).
            system_prompt: Optional system prompt to prepend.

        Returns:
            An LLMResponse with the generated content and metadata.
        """
        ...

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the name of the model being used."""
        ...
