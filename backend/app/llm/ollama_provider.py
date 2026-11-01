"""
AI Research Assistant — Ollama LLM Provider

Integrates with a local Ollama instance for development.
"""

from __future__ import annotations

import ollama as ollama_client
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.llm.base import BaseLLMProvider, LLMMessage, LLMResponse


class OllamaProvider(BaseLLMProvider):
    """LLM provider backed by a local Ollama server."""

    def __init__(self) -> None:
        self._model = settings.OLLAMA_MODEL
        self._client = ollama_client.AsyncClient(host=settings.OLLAMA_BASE_URL)
        logger.info(f"Ollama provider initialized — model: {self._model}")

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
        """Generate a response using the local Ollama model."""

        # Build the message list
        formatted_messages = []
        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})
        for msg in messages:
            formatted_messages.append({"role": msg.role, "content": msg.content})

        logger.debug(
            f"Ollama request: model={self._model}, "
            f"messages={len(formatted_messages)}, temp={temperature}"
        )

        options = {"temperature": temperature}
        if max_tokens:
            options["num_predict"] = max_tokens

        response = await self._client.chat(
            model=self._model,
            messages=formatted_messages,
            options=options,
        )

        content = response["message"]["content"]

        # Ollama provides token counts in some versions
        prompt_tokens = response.get("prompt_eval_count", 0)
        completion_tokens = response.get("eval_count", 0)

        return LLMResponse(
            content=content,
            model=self._model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            finish_reason="stop",
        )

    def get_model_name(self) -> str:
        return f"ollama/{self._model}"
