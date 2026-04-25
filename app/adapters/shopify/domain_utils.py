"""Normalize Shopify shop hostnames for Admin API and storefront JSON URLs."""
from __future__ import annotations

from urllib.parse import urlparse


def normalize_shopify_shop_hostname(domain: str) -> str:
    """
    Return hostname only, lowercase, no scheme or path (e.g. ``shuddha-mix.myshopify.com``).

    Accepts values like ``https://shop.myshopify.com/`` stored from onboarding UIs.
    """
    if not domain or not str(domain).strip():
        return ""
    s = domain.strip().lower()
    if "://" in s:
        parsed = urlparse(s if s.startswith(("http://", "https://")) else f"https://{s}")
        host = (parsed.hostname or "").strip().lower()
        if host:
            return host.rstrip(".")
        path_first = (parsed.path or "").strip("/").split("/")[0]
        return path_first.rstrip(".").lower() if path_first else ""
    host = s.split("/")[0].strip().lower()
    return host.rstrip(".")
