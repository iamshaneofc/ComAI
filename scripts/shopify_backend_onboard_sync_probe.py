"""
Run Shopify onboard + product sync using backend services (same logic as API + worker sync).

No HTTP server or Celery required: uses AsyncSessionLocal, StoreOnboardingService, StoreService.sync_store_products.

Usage (from ComAI repo root, venv active):
  cd Z:\\ComAI\\ComAI
  .\\.venv312\\Scripts\\python.exe scripts\\shopify_backend_onboard_sync_probe.py
  .\\.venv312\\Scripts\\python.exe scripts\\shopify_backend_onboard_sync_probe.py --mock-sync

Requires in .env:
  - DATABASE_URL (Postgres up)
  - SHOPIFY_SMOKE_DOMAIN (shop hostname, e.g. shuddha-mix.myshopify.com)

Live sync uses the storefront ``/products.json`` feed (published products only); no Admin token.

--mock-sync: sets SHOPIFY_SYNC_MODE=mock for this process only (verifies DB pipeline without calling Shopify).
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


async def main() -> int:
    parser = argparse.ArgumentParser(description="Backend Shopify onboard + sync probe")
    parser.add_argument(
        "--mock-sync",
        action="store_true",
        help="Use SHOPIFY_SYNC_MODE=mock (no live Shopify HTTP)",
    )
    args = parser.parse_args()
    if args.mock_sync:
        os.environ["SHOPIFY_SYNC_MODE"] = "mock"

    os.chdir(_ROOT)
    from app.core.config import get_settings
    from app.core.database import AsyncSessionLocal
    from app.modules.stores.onboarding_service import StoreOnboardingService
    from app.modules.stores.service import StoreService
    from app.repositories.product_repo import ProductRepository
    from app.schemas.product import ProductSearchFilters
    from app.schemas.store import StoreOnboardRequest

    get_settings.cache_clear()
    cfg = get_settings()
    domain = (cfg.SHOPIFY_SMOKE_DOMAIN or "").strip().lower()
    if not domain:
        print("ERROR: set SHOPIFY_SMOKE_DOMAIN in .env")
        return 1

    payload = StoreOnboardRequest(
        platform="shopify",
        domain=domain,
    )

    print("domain:", domain)
    print("sync: storefront /products.json (unless --mock-sync)")

    async with AsyncSessionLocal() as session:
        onboard = StoreOnboardingService(db=session)
        try:
            resp = await onboard.onboard_shopify(payload)
        except Exception as exc:
            print("onboard_failed:", exc)
            return 1
        await session.commit()
        store_id = resp.id
        print("onboard_ok store_id:", store_id, "api_key_suffix:", (resp.api_key or "")[-6:])

        store_svc = StoreService(db=session)
        try:
            synced = await store_svc.sync_store_products(store_id)
        except Exception as exc:
            print("sync_failed:", exc)
            return 1
        await session.commit()
        print("sync_rows_upserted:", synced)

        products = ProductRepository(session)
        total = await products.count_for_store(store_id)
        print("products_in_db_for_store:", total)
        if total:
            items, _ = await products.search_products(
                store_id,
                ProductSearchFilters(offset=0, limit=min(5, total), is_available=True),
            )
            for p in items[:5]:
                print(" sample:", p.title[:70], "price=", p.price)

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
