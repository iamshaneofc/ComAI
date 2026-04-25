"""
Try GET /api/v1/products/search; if HTTP fails, read products from DB for the Shopify domain store.

  cd Z:\\ComAI\\ComAI && .\\.venv312\\Scripts\\python.exe scripts\\fetch_store_products_test.py
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import httpx

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


async def _db_fallback() -> int:
    os.chdir(_ROOT)
    from app.core.config import get_settings
    from app.core.database import AsyncSessionLocal
    from app.repositories.product_repo import ProductRepository
    from app.repositories.store_repo import StoreRepository
    from app.schemas.product import ProductSearchFilters

    get_settings.cache_clear()
    cfg = get_settings()
    domain = (cfg.SHOPIFY_SMOKE_DOMAIN or "").strip().lower()

    async with AsyncSessionLocal() as session:
        stores = StoreRepository(session)
        store = await stores.get_by_domain(domain) if domain else None
        if store is None and domain:
            print("DB: no store for domain", domain)
            return 1
        if store is None:
            print("DB: set SHOPIFY_SMOKE_DOMAIN in .env")
            return 1

        print("DB: store_id=", store.id, "api_key_suffix=", (store.api_key or "")[-8:])
        pr = ProductRepository(session)
        total = await pr.count_for_store(store.id)
        print("DB: products_count=", total)
        if total:
            items, _ = await pr.search_products(
                store.id,
                ProductSearchFilters(offset=0, limit=min(10, total), is_available=True),
            )
            for p in items:
                print(" ", p.id, p.title[:60], "price=", p.price)
    return 0


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv(_ROOT / ".env")
    base = os.environ.get("APP_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    key = (os.environ.get("DEV_TENANT_API_KEY") or "").strip()
    url = f"{base}/api/v1/products/search"
    params = {"offset": 0, "limit": 50}

    if not key:
        print("DEV_TENANT_API_KEY empty in .env — trying DB fallback.")
        return asyncio.run(_db_fallback())

    try:
        r = httpx.get(url, params=params, headers={"X-API-KEY": key}, timeout=15.0)
    except httpx.ConnectError as e:
        print("HTTP: backend not reachable at", base, "-", e)
        print("Trying DB fallback…")
        return asyncio.run(_db_fallback())

    print("HTTP status:", r.status_code, "URL:", r.request.url)
    if r.status_code == 401:
        print("HTTP: invalid X-API-KEY - use the api_key returned from POST /stores or /stores/onboard.")
        print("Trying DB fallback for SHOPIFY_SMOKE_DOMAIN store…")
        return asyncio.run(_db_fallback())

    if not r.is_success:
        print(r.text[:500])
        return 1

    data = r.json()
    items = data.get("items") or []
    print("total=", data.get("total"), "returned=", len(items))
    for row in items[:15]:
        print(" ", row.get("id"), (row.get("title") or "")[:60], "price=", row.get("price"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
