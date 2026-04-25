"""
In-process cache for Shopify OAuth client_credentials Admin tokens.

Sync and workers may call frequently; tokens are short-lived when Shopify returns expires_in.
Invalidate on credential changes via invalidate_shopify_oauth_cache.
"""
from __future__ import annotations

import asyncio
import time
from typing import Final

from app.adapters.shopify.client import fetch_access_token_client_credentials

_DEFAULT_TTL_SEC: Final[int] = 3600
_CACHE: dict[str, tuple[str, float]] = {}
_LOCKS: dict[str, asyncio.Lock] = {}


def invalidate_shopify_oauth_cache(store_id: str) -> None:
    """Drop cached OAuth token after onboarding or credential rotation."""
    _CACHE.pop(store_id, None)
    _LOCKS.pop(store_id, None)


async def get_cached_shopify_oauth_admin_token(
    store_id: str,
    domain: str,
    client_id: str,
    client_secret: str,
) -> str:
    lock = _LOCKS.setdefault(store_id, asyncio.Lock())
    async with lock:
        now = time.monotonic()
        hit = _CACHE.get(store_id)
        if hit:
            token, mono_until = hit
            if now < mono_until:
                return token
        token, expires_in = await fetch_access_token_client_credentials(domain, client_id, client_secret)
        if isinstance(expires_in, int) and expires_in > 0:
            ttl = max(120, int(expires_in * 0.85))
        else:
            ttl = _DEFAULT_TTL_SEC
        _CACHE[store_id] = (token, now + ttl)
        return token
