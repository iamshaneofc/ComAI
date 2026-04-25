"""
Smoke test: same Shopify adapter as product sync (ShopifyClient).

Run from repo root (ComAI) with venv active:

  cd Z:\\ComAI\\ComAI
  .\\.venv312\\Scripts\\Activate.ps1
  $env:SHOPIFY_SMOKE_DOMAIN="your-store.myshopify.com"
  $env:SHOPIFY_SMOKE_ACCESS_TOKEN="shpat_..."   # Admin API access token (not client secret)
  python scripts/shopify_backend_smoke.py

Or copy env.shopify.smoke.example to .env.shopify.smoke in the repo root (gitignored) and fill values.

Do not commit tokens. Rotate if leaked.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Allow `python scripts/shopify_backend_smoke.py` from repo root
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _load_shopify_smoke_file() -> None:
    """Optional local file (gitignored): .env.shopify.smoke — KEY=value lines."""
    path = _ROOT / ".env.shopify.smoke"
    if not path.is_file():
        return
    keys = frozenset(
        {"SHOPIFY_SMOKE_DOMAIN", "SHOPIFY_SMOKE_ACCESS_TOKEN", "SHOPIFY_SMOKE_WEBHOOK_SECRET"}
    )
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if " #" in v:
            v = v.split(" #", 1)[0].rstrip()
        if k in keys and k not in os.environ:
            os.environ[k] = v


async def main() -> int:
    # So pydantic-settings ``env_file=".env"`` resolves to ``ComAI/.env`` even when cwd is elsewhere.
    os.chdir(_ROOT)
    _load_shopify_smoke_file()
    from app.core.config import get_settings

    cfg = get_settings()
    domain = (
        (os.environ.get("SHOPIFY_SMOKE_DOMAIN") or "").strip().lower()
        or (cfg.SHOPIFY_SMOKE_DOMAIN or "").strip().lower()
    )
    token = (os.environ.get("SHOPIFY_SMOKE_ACCESS_TOKEN") or "").strip() or (
        cfg.SHOPIFY_SMOKE_ACCESS_TOKEN or ""
    ).strip()
    webhook = (os.environ.get("SHOPIFY_SMOKE_WEBHOOK_SECRET") or "").strip() or (
        cfg.SHOPIFY_SMOKE_WEBHOOK_SECRET or ""
    ).strip()
    client_id = (cfg.SHOPIFY_APP_CLIENT_ID or "").strip()
    client_secret = (cfg.SHOPIFY_APP_CLIENT_SECRET or "").strip()

    if token.startswith("shpss_"):
        if not client_secret:
            client_secret = token.strip()
        print(
            "Note: SHOPIFY_SMOKE_ACCESS_TOKEN contained shpss_ (client secret), not an Admin token. "
            "Using it as SHOPIFY_APP_CLIENT_SECRET and attempting OAuth client_credentials if "
            "SHOPIFY_APP_CLIENT_ID is set."
        )
        token = ""

    if not domain:
        print("Missing SHOPIFY_SMOKE_DOMAIN in .env (or env / .env.shopify.smoke).")
        return 1

    from app.adapters.shopify.client import ShopifyClient, fetch_access_token_client_credentials

    if not token:
        if client_id and client_secret:
            print(
                "SHOPIFY_SMOKE_ACCESS_TOKEN empty; exchanging SHOPIFY_APP_CLIENT_ID + "
                "SHOPIFY_APP_CLIENT_SECRET (OAuth client_credentials)..."
            )
            try:
                token, _expires_in = await fetch_access_token_client_credentials(
                    domain, client_id, client_secret
                )
                print("token_source: client_credentials (short-lived; use SHOPIFY_SMOKE_ACCESS_TOKEN for a static admin token if you prefer)")
            except Exception as e:
                print("client_credentials_exchange_failed:", e)
                return 1
        else:
            if client_secret and not client_id:
                print(
                    "SHOPIFY_APP_CLIENT_SECRET is set but SHOPIFY_APP_CLIENT_ID is empty.\n"
                    "In Shopify Admin: Settings > Apps and sales channels > Develop apps > [your app] > "
                    "API credentials - copy the Client ID (API key) into SHOPIFY_APP_CLIENT_ID, "
                    "or paste the Admin API access token (shpat_/shpca_) into SHOPIFY_SMOKE_ACCESS_TOKEN."
                )
            else:
                print(
                    "Missing Admin API token: set SHOPIFY_SMOKE_ACCESS_TOKEN (shpat_/shpca_ from a custom app),\n"
                    "or set SHOPIFY_APP_CLIENT_ID + SHOPIFY_APP_CLIENT_SECRET for automatic client_credentials exchange.\n"
                    "Note: shpss_... is the app client secret, not the access token header value by itself.\n"
                    "Webhook HMAC verification uses the same client secret (shpss_), not the client ID hex."
                )
            return 1

    from app.adapters.shopify.normalizer import normalize_product
    print("shop_domain:", domain)
    print("webhook_secret_configured:", bool(webhook), "(not used for Admin product GET; for ComAI webhook HMAC only)")

    client = ShopifyClient(domain=domain, access_token=token)

    product_count = 0
    sample_titles: list[str] = []
    first_product: dict | None = None
    async for batch in client.get_products():
        product_count += len(batch)
        for p in batch[:3]:
            t = p.get("title")
            if isinstance(t, str):
                sample_titles.append(t)
        if batch:
            first_product = batch[0]
        break

    print(f"products_first_page: {product_count} items")
    if sample_titles:
        print("sample_titles:", sample_titles)

    if first_product:
        try:
            normalized = normalize_product(first_product)
            print(
                "normalize_ok:",
                normalized.title,
                f"price={normalized.price}",
                f"external_id={normalized.external_id}",
            )
        except Exception as e:
            print("normalize_failed:", e)
            return 1

    orders = await client.fetch_orders_page(limit=3, status="any")
    print(f"orders_sample: {len(orders)} rows (first page, status=any)")
    if orders:
        o0 = orders[0]
        print("first_order:", o0.get("id"), o0.get("name"), o0.get("financial_status"))

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
