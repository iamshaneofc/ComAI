"""
Encrypt/decrypt optional per-tenant LLM API keys at rest (store_ai_configs.api_key_encrypted).

Uses Fernet with a key derived deterministically from APP_SECRET_KEY (SHA-256 digest,
url-safe base64-encoded to 32 bytes). Rotating APP_SECRET_KEY invalidates stored keys;
re-encrypt tenant keys after rotation.

If api_key_encrypted is NULL or decryption fails, AgentResolver falls back to env vars
(OPENAI_API_KEY, GEMINI_API_KEY, etc.) — see app.services.agent_resolver.
"""
from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _fernet_key_from_secret(secret: str) -> bytes:
    """Derive a 32-byte url-safe key material for Fernet from application secret."""
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _fernet() -> Fernet:
    return Fernet(_fernet_key_from_secret(settings.APP_SECRET_KEY))


def encrypt_api_key(plain: str) -> bytes:
    """Encrypt a raw API key for persistence in BYTEA. Caller must enforce non-empty input."""
    return _fernet().encrypt(plain.encode("utf-8"))


def decrypt_api_key(blob: bytes | None) -> str | None:
    """
    Decrypt stored key bytes to a string.

    Returns None if blob is None, empty, or ciphertext is invalid (wrong secret or corrupt data).
    Never raises to callers — use None to signal fallback to environment keys.
    """
    if not blob:
        return None
    try:
        return _fernet().decrypt(blob).decode("utf-8")
    except (InvalidToken, ValueError, UnicodeDecodeError):
        return None
