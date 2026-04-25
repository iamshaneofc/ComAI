from datetime import datetime, timezone
from typing import Literal

from app.schemas.product import ProductCreate

CatalogSource = Literal["admin", "storefront"]


def normalize_product(
    shopify_product: dict,
    *,
    catalog_source: CatalogSource = "admin",
) -> ProductCreate:
    """
    Normalizes raw Shopify JSON into ProductCreate.

    ``catalog_source="admin"`` expects Admin REST payloads (``status`` field).
    ``catalog_source="storefront"`` uses legacy ``/products.json`` payloads (no ``status``;
    availability is inferred from ``published_at``).
    """
    external_id = str(shopify_product.get("id"))
    title = shopify_product.get("title", "")
    description = shopify_product.get("body_html") or ""
    
    # Process variants
    variants = shopify_product.get("variants", [])
    
    # Get first variant price safely
    price_str = variants[0].get("price", "0") if variants else "0"
    try:
        price = float(price_str)
    except ValueError:
        price = 0.0

    # Process images
    images = shopify_product.get("images", [])
    # Keep only URL and alt to minimize payload size
    normalized_images = [{"url": img.get("src"), "alt": img.get("alt")} for img in images]
    
    # Process tags
    tags_str = shopify_product.get("tags", "")
    tags = [tag.strip() for tag in tags_str.split(",")] if tags_str else []
    
    # Process attributes
    attributes = {"options": shopify_product.get("options", [])}
    
    if catalog_source == "storefront":
        is_available = bool(shopify_product.get("published_at"))
    else:
        is_available = shopify_product.get("status") == "active"

    # Required Source Dictionary mapping
    source = {
        "platform": "shopify",
        "external_id": external_id,
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "catalog": catalog_source,
    }

    return ProductCreate(
        title=title,
        description=description,
        price=price,
        is_available=is_available,
        images=normalized_images,
        variants=variants,
        attributes=attributes,
        tags=tags,
        source_platform="shopify",
        external_id=external_id,
        source=source,
        raw_data=shopify_product
    )
