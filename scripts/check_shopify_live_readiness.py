"""Print live Shopify readiness from .env (no secret values). Run: python scripts/check_shopify_live_readiness.py"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
os.chdir(_ROOT)
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def classify_token(tok: str) -> str:
    t = (tok or "").strip()
    if not t:
        return "empty"
    if t.startswith("shpat_") or t.startswith("shpca_"):
        return "admin_token_shape_ok"
    if t.startswith("shpss_"):
        return "shpss_client_secret_not_usable_as_admin_header"
    return "nonstandard_prefix"


def main() -> int:
    from app.core.config import get_settings

    s = get_settings()
    print("=== ComAI live Shopify readiness ===\n")
    print(f"SHOPIFY_SYNC_MODE: {s.SHOPIFY_SYNC_MODE!r}  (must be 'live' to call Shopify API)")
    print(f"SHOPIFY_API_VERSION: {s.SHOPIFY_API_VERSION!r}")
    print(f"APP_SECRET_KEY length: {len(s.APP_SECRET_KEY)} chars (Fernet derives from this for credential storage)")
    print(f"CELERY_BROKER_URL configured: {bool(s.CELERY_BROKER_URL.strip())}")
    print("\n--- Global smoke / dev vars (scripts only; NOT used by StoreService.sync) ---")
    print(f"SHOPIFY_SMOKE_DOMAIN: {(s.SHOPIFY_SMOKE_DOMAIN or '').strip() or '(empty)'}")
    print(f"SHOPIFY_SMOKE_ACCESS_TOKEN: {classify_token(s.SHOPIFY_SMOKE_ACCESS_TOKEN)}")
    print(f"SHOPIFY_APP_CLIENT_ID set: {bool(s.SHOPIFY_APP_CLIENT_ID.strip())}")
    print(f"SHOPIFY_APP_CLIENT_SECRET set: {bool(s.SHOPIFY_APP_CLIENT_SECRET.strip())}")

    ok_live = s.SHOPIFY_SYNC_MODE == "live"
    smoke_admin = classify_token(s.SHOPIFY_SMOKE_ACCESS_TOKEN) == "admin_token_shape_ok"
    smoke_oauth = bool(s.SHOPIFY_APP_CLIENT_ID.strip() and s.SHOPIFY_APP_CLIENT_SECRET.strip())
    print("\n--- Summary ---")
    print(f"1. Live sync enabled: {'YES' if ok_live else 'NO (set SHOPIFY_SYNC_MODE=live)'}")
    print(
        "2. scripts/shopify_backend_smoke.py (optional Admin API smoke): "
        + (
            "YES (admin token in SHOPIFY_SMOKE_ACCESS_TOKEN)"
            if smoke_admin
            else (
                "YES (OAuth if domain + client id + secret)"
                if smoke_oauth and (s.SHOPIFY_SMOKE_DOMAIN or "").strip()
                else (
                    "NO (optional) - not required for product sync; backend uses storefront /products.json"
                )
            )
        )
    )
    print(
        "3. Tenant product sync: uses store.credentials.shopify.domain only — "
        "POST /stores/onboard with domain (no Admin token). Published catalog via /products.json."
    )
    print(
        "4. Onboarding background job: Celery worker must be running with same env "
        "(same SHOPIFY_SYNC_MODE and Redis/DB connectivity)."
    )

    print("\n--- Database (active stores, credential keys only) ---")
    try:
        import asyncio
        from sqlalchemy import text

        from app.core.database import AsyncSessionLocal

        async def _stores() -> None:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    text(
                        "SELECT id::text, name, platform, onboarding_status, credentials "
                        "FROM stores WHERE is_active = true ORDER BY created_at DESC NULLS LAST LIMIT 8"
                    )
                )
                rows = result.fetchall()
                if not rows:
                    print("(no active stores)")
                    return
                for row in rows:
                    sid, name, plat, ob, creds = row
                    shop = (creds or {}).get("shopify") or {}
                    if not isinstance(shop, dict):
                        shop = {}
                    print(
                        f"  store {str(sid)[:8]}... {name!r} platform={plat} onboarding={ob} "
                        f"shopify_domain={shop.get('domain')!r} "
                        f"has_access_token={bool(shop.get('access_token'))} "
                        f"has_client_id={bool(shop.get('client_id'))} "
                        f"has_client_secret={bool(shop.get('client_secret'))}"
                    )

        asyncio.run(_stores())
    except Exception as exc:
        print(f"  (skipped: {exc})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
