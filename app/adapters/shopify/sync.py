import logging
from uuid import UUID
from typing import AsyncGenerator

from app.adapters.shopify.normalizer import normalize_product
from app.adapters.shopify.storefront_catalog import iter_storefront_product_batches
from app.schemas.product import ProductCreate

logger = logging.getLogger(__name__)


async def fetch_and_normalize_products(
    store_id: UUID, shop_hostname: str
) -> AsyncGenerator[list[ProductCreate], None]:
    """
    Fetch published products from Shopify's legacy storefront JSON (same as
    ``GET https://{shop}/products.json`` — no Admin API token).

    ``shop_hostname`` must be a bare host (e.g. ``name.myshopify.com``).
    """
    async for products_batch in iter_storefront_product_batches(shop_hostname):
        normalized_products = []
        for sp in products_batch:
            try:
                p_create = normalize_product(sp, catalog_source="storefront")
                normalized_products.append(p_create)
            except Exception as e:
                logger.error(
                    "Failed to normalize storefront product %s for store %s: %s",
                    sp.get("id"),
                    store_id,
                    e,
                )
                continue

        if normalized_products:
            yield normalized_products

    logger.info("Finished storefront catalog fetch for store %s", store_id)
