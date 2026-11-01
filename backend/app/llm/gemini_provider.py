"""
AI Research Assistant — Google Gemini LLM Provider

Production-grade provider for Google's Gemini API.
Provides accurate, research-quality responses using Gemini models.
Free tier available at https://aistudio.google.com/apikey
"""

from __future__ import annotations

import asyncio
from functools import partial

from loguru import logger
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.llm.base import BaseLLMProvider, LLMMessage, LLMResponse


def _is_transient_gemini_error(e: BaseException) -> bool:
    err_str = str(e).lower()
    # Daily quota exhaustion is permanent for the day on that specific model;
    # do NOT waste retry cycles on it—immediately fall through to the next model.
    if "daily limit" in err_str or "quota exceeded" in err_str:
        return False
    code = getattr(e, "code", getattr(e, "status_code", 0))
    if code in (429, 503):
        return True
    return any(phrase in err_str for phrase in ("high demand", "resource exhausted", "unavailable", "503", "429"))


class GeminiProvider(BaseLLMProvider):
    """LLM provider backed by the Google Gemini API."""

    def __init__(self) -> None:
        if not settings.GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY is required for the Gemini provider. "
                "Get a free key at https://aistudio.google.com/apikey "
                "and set it in your .env file."
            )
        self._model_name = settings.GEMINI_MODEL or "gemini-3.5-flash-lite"
        self._api_key = settings.GEMINI_API_KEY

        # High-availability model candidate cascade (verified on free tier)
        fallbacks = [
            self._model_name,
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite",
            "gemini-flash-lite-latest",
            "gemini-3.5-flash",
        ]
        seen = set()
        self._fallback_models: list[str] = []
        for m in fallbacks:
            if m and m not in seen:
                seen.add(m)
                self._fallback_models.append(m)

        # Import and configure the Google GenAI client
        try:
            from google import genai
            self._client = genai.Client(api_key=self._api_key)
        except ImportError:
            raise ImportError(
                "google-genai is required for the Gemini provider. "
                "Install with: pip install google-genai"
            )

        logger.info(f"Gemini provider initialized — primary model: {self._model_name}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1.5, min=1, max=10),
        retry=retry_if_exception(_is_transient_gemini_error),
        reraise=True,
    )
    async def _call_gemini_model(
        self,
        model: str,
        contents: list,
        gen_config,
    ):
        """Invoke generate_content for a specific model with retries."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            partial(
                self._client.models.generate_content,
                model=model,
                contents=contents,
                config=gen_config,
            ),
        )

    async def generate(
        self,
        messages: list[LLMMessage],
        max_tokens: int | None = None,
        temperature: float = 0.7,
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """Generate a response using the Google Gemini API with fallback models."""
        from google.genai import types

        # Build contents list ensuring valid parts and non-empty content
        contents = []
        for msg in messages:
            content_text = msg.content if msg.content and msg.content.strip() else " "
            role = "user" if msg.role == "user" else "model"
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=content_text)],
                )
            )

        # Build generation config
        gen_config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens or settings.LLM_MAX_TOKENS,
        )

        # Add system instruction if provided
        if system_prompt:
            gen_config.system_instruction = system_prompt

        response = None
        used_model = self._model_name
        last_error = None

        for candidate_model in self._fallback_models:
            try:
                logger.debug(
                    f"Gemini request: model={candidate_model}, "
                    f"messages={len(contents)}, temp={temperature}"
                )
                response = await self._call_gemini_model(candidate_model, contents, gen_config)
                used_model = candidate_model
                break
            except Exception as e:
                last_error = e
                err_code = getattr(e, "code", getattr(e, "status_code", None))
                logger.warning(
                    f"Gemini candidate '{candidate_model}' failed (code={err_code}): {e}. "
                    f"Trying next fallback model..."
                )

        if response is None:
            if last_error:
                raise last_error
            raise RuntimeError("Gemini failed to return a response from any candidate model.")

        # Extract the response text
        response_text = response.text or ""

        if not response_text.strip():
            # Some responses have candidates with text in parts
            try:
                if response.candidates:
                    for candidate in response.candidates:
                        if candidate.content and candidate.content.parts:
                            for part in candidate.content.parts:
                                if hasattr(part, "text") and part.text:
                                    response_text = part.text
                                    break
                        if response_text.strip():
                            break
            except Exception:
                pass

        if not response_text.strip():
            raise RuntimeError(
                "Gemini returned an empty response. This may indicate "
                "the content was blocked by safety filters or the model "
                "is unavailable. Check your GEMINI_API_KEY and GEMINI_MODEL."
            )

        # Extract token usage if available
        prompt_tokens = 0
        completion_tokens = 0
        if response.usage_metadata:
            prompt_tokens = response.usage_metadata.prompt_token_count or 0
            completion_tokens = response.usage_metadata.candidates_token_count or 0

        logger.info(
            f"Gemini response received — "
            f"prompt_tokens={prompt_tokens}, completion_tokens={completion_tokens}, "
            f"response_length={len(response_text)}"
        )

        return LLMResponse(
            content=response_text,
            model=used_model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            finish_reason="stop",
        )

    def get_model_name(self) -> str:
        return f"gemini/{self._model_name}"
