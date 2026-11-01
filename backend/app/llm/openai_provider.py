"""
AI Research Assistant — OpenAI LLM Provider

Production-grade provider for OpenAI-compatible APIs.
"""

from __future__ import annotations

from loguru import logger
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.llm.base import BaseLLMProvider, LLMMessage, LLMResponse


class OpenAIProvider(BaseLLMProvider):
    """LLM provider backed by the OpenAI API."""

    def __init__(self) -> None:
        if not settings.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY is required for the OpenAI provider. "
                "Set it in your .env file."
            )
        self._model = settings.OPENAI_MODEL
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        logger.info(f"OpenAI provider initialized — model: {self._model}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def generate(
        self,
        messages: list[LLMMessage],
        max_tokens: int | None = None,
        temperature: float = 0.7,
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """Generate a response using the OpenAI API."""

        formatted_messages = []
        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})
        for msg in messages:
            formatted_messages.append({"role": msg.role, "content": msg.content})

        logger.debug(
            f"OpenAI request: model={self._model}, "
            f"messages={len(formatted_messages)}, temp={temperature}"
        )

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=formatted_messages,
            max_tokens=max_tokens or settings.LLM_MAX_TOKENS,
            temperature=temperature,
        )

        choice = response.choices[0]
        usage = response.usage

        return LLMResponse(
            content=choice.message.content or "",
            model=self._model,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            total_tokens=usage.total_tokens if usage else 0,
            finish_reason=choice.finish_reason or "stop",
        )

    def get_model_name(self) -> str:
        return f"openai/{self._model}"
