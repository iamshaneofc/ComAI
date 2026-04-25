#!/usr/bin/env python3
"""
Standalone Shopify Admin API check — no ComAI app imports (only httpx).

Loads SHOPIFY_* from ComAI/.env if present. Run:
  cd Z:\\ComAI\\ComAI && .\\.venv312\\Scripts\\python.exe scripts\\shopify_plain_http_test.py
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import httpx

API_VERSION = "2024-04"


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if " #" in v:
            v = v.split(" #", 1)[0].rstrip()
        if k and k not in os.environ:
            os.environ[k] = v


async def main() -> int:
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    _load_dotenv(root / ".env")

    domain = (
        os.environ.get("SHOPIFY_SMOKE_DOMAIN", "")
        or os.environ.get("SHOPIFY_DOMAIN", "")
    ).strip().lower()
    raw_smoke = (os.environ.get("SHOPIFY_SMOKE_ACCESS_TOKEN", "") or "").strip()
    client_id = (os.environ.get("SHOPIFY_APP_CLIENT_ID", "") or "").strip()
    client_secret = (os.environ.get("SHOPIFY_APP_CLIENT_SECRET", "") or "").strip()

    admin_token = raw_smoke
    if raw_smoke.startswith("shpss_"):
        admin_token = ""
        if not client_secret:
            client_secret = raw_smoke

    if not domain:
        print("ERROR: set SHOPIFY_SMOKE_DOMAIN (or SHOPIFY_DOMAIN) in .env")
        return 1

    shop = domain.replace("https://", "").split("/")[0].rstrip("/")
    print("shop:", shop)
    print("api_version:", API_VERSION)

    async with httpx.AsyncClient(timeout=45.0) as http:
        access = admin_token

        if not access and client_id and client_secret:
            oauth_url = f"https://{shop}/admin/oauth/access_token"
            print("oauth: POST", oauth_url)
            resp = await http.post(
                oauth_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            print("oauth_http_status:", resp.status_code)
            if not resp.is_success:
                print("oauth_response:", (resp.text or "")[:600])
                return 1
            body = resp.json()
            access = body.get("access_token") if isinstance(body, dict) else None
            if not isinstance(access, str) or not access:
                print("oauth: missing access_token in JSON")
                return 1
            print("oauth: OK, token_prefix:", access[:8] + "...")

        if not access:
            probe = client_secret or raw_smoke
            if probe.startswith("shpss_"):
                url = f"https://{shop}/admin/api/{API_VERSION}/products.json?limit=1"
                print(
                    "probe: GET products using shpss_ as X-Shopify-Access-Token "
                    "(Shopify should reject: shpss_ is a client secret, not an Admin token)."
                )
                resp = await http.get(
                    url,
                    headers={
                        "X-Shopify-Access-Token": probe,
                        "Content-Type": "application/json",
                    },
                )
                print("probe_http_status:", resp.status_code)
                print("probe_body_snippet:", (resp.text or "")[:500])
            print(
                "\nNo usable Admin token. Fix one of:\n"
                "  • Set SHOPIFY_APP_CLIENT_ID (with your shpss_ secret) for OAuth, or\n"
                "  • Set SHOPIFY_SMOKE_ACCESS_TOKEN to Admin API token (shpat_ or shpca_)."
            )
            return 1

        url = f"https://{shop}/admin/api/{API_VERSION}/products.json?limit=10"
        print("GET", url)
        resp = await http.get(
            url,
            headers={
                "X-Shopify-Access-Token": access,
                "Content-Type": "application/json",
            },
        )
        print("products_http_status:", resp.status_code)
        if not resp.is_success:
            print("products_body:", (resp.text or "")[:600])
            return 1

        data = resp.json()
        products = data.get("products") if isinstance(data, dict) else None
        if not isinstance(products, list):
            print("unexpected JSON shape:", type(data))
            return 1

        print("products_count_this_page:", len(products))
        for p in products[:10]:
            if isinstance(p, dict):
                print(" ", p.get("id"), "-", (p.get("title") or "")[:80])

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
