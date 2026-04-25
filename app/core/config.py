"""
Core Configuration — reads from environment variables via pydantic-settings.

All settings MUST be defined here. Do NOT use os.getenv() elsewhere in the codebase.
"""
from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    APP_NAME: str = "AI Commerce Platform"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_DEBUG: bool = True
    APP_SECRET_KEY: str
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # --- Database ---
    DATABASE_URL: str

    # --- Redis ---
    REDIS_URL: str
    REDIS_CACHE_TTL: int = 3600

    # --- JWT ---
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # --- AI Providers ---
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-pro"

    ACTIVE_LLM_PROVIDER: Literal["openai", "gemini", "mock"] = "openai"

    # --- Shopify ---
    SHOPIFY_API_VERSION: str = "2024-04"
    SHOPIFY_WEBHOOK_SECRET: str = ""
    SHOPIFY_SYNC_MODE: Literal["live", "mock"] = "live"
    # Optional local dev / scripts (see scripts/shopify_backend_smoke.py). Empty in production.
    SHOPIFY_SMOKE_DOMAIN: str = Field(
        default="",
        validation_alias=AliasChoices("SHOPIFY_SMOKE_DOMAIN", "SHOPIFY_DOMAIN"),
    )
    SHOPIFY_SMOKE_ACCESS_TOKEN: str = Field(
        default="",
        validation_alias=AliasChoices("SHOPIFY_SMOKE_ACCESS_TOKEN", "SHOPIFY_ADMIN_ACCESS_TOKEN"),
        description="Admin API token (shpat_/shpca_), not shpss_ client secret",
    )
    SHOPIFY_SMOKE_WEBHOOK_SECRET: str = Field(
        default="",
        validation_alias=AliasChoices(
            "SHOPIFY_SMOKE_WEBHOOK_SECRET",
            "SHOPIFY_STORE_WEBHOOK_SECRET",
            "WEBHOOK_SIGNING_SECRET",
        ),
    )
    SHOPIFY_APP_CLIENT_ID: str = ""
    SHOPIFY_APP_CLIENT_SECRET: str = Field(
        default="",
        validation_alias=AliasChoices(
            "SHOPIFY_APP_CLIENT_SECRET",
            "SHOPIFY_CLIENT_SECRET",
            "ADMIN_API_ACCESS",
        ),
    )
    DEV_TENANT_API_KEY: str = ""  # ComAI X-API-KEY for curl / manual testing

    # --- Meta / WhatsApp ---
    META_ACCESS_TOKEN: str = ""
    META_PHONE_NUMBER_ID: str = ""
    META_WEBHOOK_VERIFY_TOKEN: str = ""

    # --- Celery ---
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # --- Vector Store ---
    VECTOR_STORE_PROVIDER: Literal["pgvector", "pinecone"] = "pgvector"
    PINECONE_API_KEY: str = ""
    PINECONE_ENVIRONMENT: str = ""
    PINECONE_INDEX_NAME: str = "ai-commerce"

    # --- Logging ---
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: Literal["json", "text"] = "json"

    # --- CORS ---
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v):
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    @model_validator(mode="after")
    def validate_provider_keys(self) -> "Settings":
        if self.ACTIVE_LLM_PROVIDER == "openai" and not self.OPENAI_API_KEY.strip():
            raise ValueError("OPENAI_API_KEY is required when ACTIVE_LLM_PROVIDER=openai")
        if self.ACTIVE_LLM_PROVIDER == "gemini" and not self.GEMINI_API_KEY.strip():
            raise ValueError("GEMINI_API_KEY is required when ACTIVE_LLM_PROVIDER=gemini")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()
