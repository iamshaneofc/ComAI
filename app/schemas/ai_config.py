"""
Store-level AI provider configuration (API). Secrets are never returned in responses.
"""
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


ProviderLiteral = Literal["openai", "gemini"]


class StoreAIConfigResponse(BaseModel):
    id: UUID | None
    store_id: UUID
    provider: str
    default_model: str
    has_tenant_api_key: bool = Field(
        description="True if an encrypted tenant API key is stored (value is never returned)",
    )


class StoreAIConfigPatch(BaseModel):
    """Partial update; use model_fields_set in service to detect explicitly set fields (e.g. api_key)."""

    provider: ProviderLiteral | None = None
    default_model: str | None = Field(
        None,
        min_length=1,
        max_length=128,
        description="Model id for the chosen provider (e.g. gpt-4o, gemini-2.0-flash).",
    )
    api_key: str | None = Field(
        None,
        max_length=8192,
        description="Omit field to leave unchanged; empty or whitespace-only clears stored key",
    )

    @field_validator("default_model", "api_key", mode="before")
    @classmethod
    def strip_optional_strings(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("api_key")
    @classmethod
    def api_key_length_when_set(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return v
        if len(v) < 8:
            raise ValueError("api_key must be at least 8 characters when set")
        return v

    @model_validator(mode="after")
    def at_least_one_field(self) -> "StoreAIConfigPatch":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self
