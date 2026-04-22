"""
LLM Provider Factory — selects provider based on ACTIVE_LLM_PROVIDER config.

Rules:
    - AI providers are stateless — no DB access
    - All providers implement the BaseLLMProvider interface
    - Switch providers via config, not code changes
"""
from app.ai.providers.base import BaseLLMProvider
from app.core.config import settings


def get_llm_provider() -> BaseLLMProvider:
    """Returns the configured LLM provider instance."""
    provider = settings.ACTIVE_LLM_PROVIDER

    if provider == "openai":
        from app.ai.providers.openai_provider import OpenAIProvider
        return OpenAIProvider()
    elif provider == "gemini":
        from app.ai.providers.gemini_provider import GeminiProvider
        return GeminiProvider()
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
