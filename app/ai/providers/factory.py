"""
LLM Provider Factory — selects provider based on ACTIVE_LLM_PROVIDER config.

Rules:
    - AI providers are stateless — no DB access
    - All providers implement the BaseLLMProvider interface
    - Switch providers via config, not code changes
"""
from app.ai.providers.base import BaseLLMProvider
from app.core.config import settings


def get_llm_provider(
    *,
    provider: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> BaseLLMProvider:
    """
    Returns an LLM provider instance.

    Overrides are applied per call (not cached) so tenant-specific keys/models stay isolated.
    ``api_key=None`` means use the environment default for that provider.
    """
    name = (provider or settings.ACTIVE_LLM_PROVIDER).lower()

    if name == "openai":
        from app.ai.providers.openai_provider import OpenAIProvider

        return OpenAIProvider(api_key=api_key, model=model)
    if name == "gemini":
        from app.ai.providers.gemini_provider import GeminiProvider

        return GeminiProvider(api_key=api_key, model=model)
    raise ValueError(f"Unknown LLM provider: {name}")
