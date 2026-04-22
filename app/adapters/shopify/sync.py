import logging
from uuid import UUID
from typing import AsyncGenerator

from app.adapters.shopify.client import ShopifyClient
from app.adapters.shopify.normalizer import normalize_product
from app.schemas.product import ProductCreate

logger = logging.getLogger(__name__)


async def fetch_and_normalize_products(store_id: UUID, domain: str, access_token: str) -> AsyncGenerator[list[ProductCreate], None]:
    """Adapter logic: fetch products from Shopify and normalize them to domain schema."""
    client = ShopifyClient(domain=domain, access_token=access_token)
    
    # Fetch all products in chunks
    async for products_batch in client.get_products():
        normalized_products = []
        for sp in products_batch:
            try:
                # Normalize each raw JSON to ProductCreate schema
                p_create = normalize_product(sp)
                normalized_products.append(p_create)
            except Exception as e:
                logger.error(f"Failed to normalize product {sp.get('id')} for store {store_id}: {e}")
                continue
                
        if normalized_products:
            yield normalized_products
    
    logger.info(f"Finished fetching products for store {store_id} from Shopify.")
