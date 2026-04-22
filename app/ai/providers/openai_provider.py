"""
OpenAI Provider — GPT-4o implementation of BaseLLMProvider.

Phase 1: simple chat completion with a single user message.
Phase 2: add streaming, function calling, retry logic.

Rules:
    - No DB access
    - No business logic
    - Returns raw LLM text — formatting is done in the service layer
"""
import structlog
from openai import AsyncOpenAI

from app.ai.providers.base import BaseLLMProvider, LLMResponse
from app.core.config import settings

logger = structlog.get_logger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT implementation — uses async client for non-blocking calls."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        key = api_key if api_key is not None else settings.OPENAI_API_KEY
        self.client = AsyncOpenAI(api_key=key)
        self.model = model if model is not None else settings.OPENAI_MODEL
        self.embedding_model = settings.OPENAI_EMBEDDING_MODEL

    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """
        Send prompt to OpenAI and return structured response.

        If ``system_prompt`` is passed in kwargs, it is sent as a separate system
        message and ``prompt`` should be the user/context body only (no embedded
        system block). Otherwise the legacy single user message is used.
        """
        max_tokens = kwargs.get("max_tokens", 512)
        temperature = kwargs.get("temperature", 0.7)
        system_prompt = kwargs.get("system_prompt")

        logger.debug("Calling OpenAI", model=self.model, max_tokens=max_tokens)

        if system_prompt:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]
        else:
            messages = [{"role": "user", "content": prompt}]

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        choice = response.choices[0]
        usage = response.usage

        logger.info(
            "OpenAI response received",
            model=self.model,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
        )

        return LLMResponse(
            text=choice.message.content.strip(),
            model=self.model,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
        )

    async def embed(self, text: str) -> list[float]:
        """Generate embedding vector for semantic search (Phase 2)."""
        response = await self.client.embeddings.create(
            model=self.embedding_model,
            input=text,
        )
        return response.data[0].embedding
