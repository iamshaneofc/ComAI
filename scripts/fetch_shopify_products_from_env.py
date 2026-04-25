"""
Fetch products for the shop in .env (SHOPIFY_SMOKE_DOMAIN).

1) If SHOPIFY_SMOKE_ACCESS_TOKEN is shpat_/shpca_, or SHOPIFY_APP_CLIENT_ID+SECRET allow OAuth,
   uses Admin API (same as ShopifyClient).
2) Otherwise uses public storefront GET /products.json (published products only; no secrets).

Run from ComAI root:
  python scripts/fetch_shopify_products_from_env.py
  python scripts/fetch_shopify_products_from_env.py --json   # trailing JSON array for scripts
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


async def _admin_fetch(domain: str, token: str) -> list[dict]:
    os.chdir(_ROOT)
    from app.adapters.shopify.client import ShopifyClient

    out: list[dict] = []
    client = ShopifyClient(domain=domain, access_token=token)
    async for batch in client.get_products():
        out.extend(batch)
    return out


async def _public_fetch(hostname: str) -> list[dict]:
    from app.adapters.shopify.storefront_catalog import iter_storefront_product_batches

    out: list[dict] = []
    async for batch in iter_storefront_product_batches(hostname):
        out.extend(batch)
    return out


async def _resolve_admin_token() -> tuple[str, str] | None:
    os.chdir(_ROOT)
    from app.adapters.shopify.client import fetch_access_token_client_credentials
    from app.adapters.shopify.domain_utils import normalize_shopify_shop_hostname
    from app.core.config import get_settings

    cfg = get_settings()
    domain = (
        (os.environ.get("SHOPIFY_SMOKE_DOMAIN") or "").strip()
        or (cfg.SHOPIFY_SMOKE_DOMAIN or "").strip()
    )
    if not domain:
        return None
    host = normalize_shopify_shop_hostname(domain)

    token = (os.environ.get("SHOPIFY_SMOKE_ACCESS_TOKEN") or "").strip() or (
        cfg.SHOPIFY_SMOKE_ACCESS_TOKEN or ""
    ).strip()
    client_id = (os.environ.get("SHOPIFY_APP_CLIENT_ID") or cfg.SHOPIFY_APP_CLIENT_ID or "").strip()
    client_secret = (
        (os.environ.get("SHOPIFY_APP_CLIENT_SECRET") or cfg.SHOPIFY_APP_CLIENT_SECRET or "").strip()
    )

    if token.startswith("shpss_"):
        if not client_secret:
            client_secret = token
        token = ""

    if token.startswith(("shpat_", "shpca_")):
        return host, token

    if client_id and client_secret:
        t, _ = await fetch_access_token_client_credentials(host, client_id, client_secret)
        return host, t

    return None


async def main() -> int:
    os.chdir(_ROOT)
    from app.adapters.shopify.domain_utils import normalize_shopify_shop_hostname
    from app.core.config import get_settings

    cfg = get_settings()
    raw_domain = (
        (os.environ.get("SHOPIFY_SMOKE_DOMAIN") or "").strip()
        or (cfg.SHOPIFY_SMOKE_DOMAIN or "").strip()
    )
    if not raw_domain:
        print("Set SHOPIFY_SMOKE_DOMAIN in .env (e.g. shuddha-mix.myshopify.com).")
        return 1

    host = normalize_shopify_shop_hostname(raw_domain)
    admin = await _resolve_admin_token()

    if admin:
        d, tok = admin
        print("mode: admin_api", "domain:", d)
        products = await _admin_fetch(d, tok)
    else:
        print(
            "mode: public_storefront (no shpat_/shpca_ and no SHOPIFY_APP_CLIENT_ID+SECRET in .env)",
            "domain:",
            host,
        )
        products = await _public_fetch(host)

    print("product_count:", len(products))
    for p in products:
        title = p.get("title", "?")
        pid = p.get("id", "?")
        print(f"  - [{pid}] {title}")

    if "--json" in sys.argv:
        summary = [{"id": p.get("id"), "title": p.get("title"), "handle": p.get("handle")} for p in products]
        print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
