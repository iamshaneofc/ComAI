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

    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        self.embedding_model = settings.OPENAI_EMBEDDING_MODEL

    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """
        Send prompt to OpenAI and return structured response.

        The prompt string is pre-built by PromptBuilder and contains
        the full conversation context — we just need to complete it.
        """
        max_tokens = kwargs.get("max_tokens", 512)
        temperature = kwargs.get("temperature", 0.7)

        logger.debug("Calling OpenAI", model=self.model, max_tokens=max_tokens)

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
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
