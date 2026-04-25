"""
Published catalog via legacy storefront ``GET /products.json`` (no Admin token).

Same approach as ``scripts/fetch_shopify_products_from_env.py`` public mode: paginate with
``page=``. Only products visible on the Online Store are returned.
"""
from __future__ import annotations

import logging
from typing import AsyncGenerator

import httpx

logger = logging.getLogger(__name__)


async def iter_storefront_product_batches(
    shop_hostname: str,
    *,
    limit: int = 250,
    client_timeout: float = 30.0,
) -> AsyncGenerator[list[dict], None]:
    """
    Yield product dict batches from ``https://{shop_hostname}/products.json``.

    ``shop_hostname`` must be a bare host (e.g. ``name.myshopify.com``), no scheme.
    """
    host = shop_hostname.strip().lower().split("/")[0]
    base = f"https://{host}"
    page = 1
    max_pages = 500

    async with httpx.AsyncClient(timeout=client_timeout) as http:
        while page <= max_pages:
            url = f"{base}/products.json?limit={limit}&page={page}"
            try:
                response = await http.get(url)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                logger.error("storefront_products_fetch_failed", url=url, error=str(exc))
                raise

            data = response.json()
            batch = data.get("products") or []
            yield batch
            if len(batch) < limit:
                return
            page += 1
