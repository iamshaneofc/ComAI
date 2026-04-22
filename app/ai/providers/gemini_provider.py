"""
Gemini implementation of BaseLLMProvider (async wrappers around sync SDK calls).
"""
from __future__ import annotations

import asyncio

import google.generativeai as genai
import structlog

from app.ai.providers.base import BaseLLMProvider, LLMResponse
from app.core.config import settings

logger = structlog.get_logger(__name__)


class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        key = api_key if api_key is not None else settings.GEMINI_API_KEY
        genai.configure(api_key=key)
        self.model_name = model if model is not None else settings.GEMINI_MODEL

    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        max_tokens = kwargs.get("max_tokens", 512)
        temperature = kwargs.get("temperature", 0.7)
        system_prompt = kwargs.get("system_prompt")
        user_content = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        def _sync_call():
            model = genai.GenerativeModel(self.model_name)
            return model.generate_content(
                user_content,
                generation_config={
                    "max_output_tokens": max_tokens,
                    "temperature": temperature,
                },
            )

        response = await asyncio.to_thread(_sync_call)
        text = (response.text or "").strip()
        usage = getattr(response, "usage_metadata", None)
        pt = int(getattr(usage, "prompt_token_count", 0) or 0) if usage else 0
        ct = int(getattr(usage, "candidates_token_count", 0) or 0) if usage else 0

        logger.info("Gemini response received", model=self.model_name, prompt_tokens=pt, completion_tokens=ct)

        return LLMResponse(
            text=text,
            model=self.model_name,
            prompt_tokens=pt,
            completion_tokens=ct,
            total_tokens=pt + ct,
        )

    async def embed(self, text: str) -> list[float]:
        def _sync_embed():
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
            )
            return result["embedding"]

        return await asyncio.to_thread(_sync_embed)
