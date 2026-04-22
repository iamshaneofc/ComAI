from datetime import datetime, timezone

from app.schemas.product import ProductCreate


def normalize_product(shopify_product: dict) -> ProductCreate:
    """Normalizes raw Shopify JSON payload into ProductCreate schema."""
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
    
    # Required Source Dictionary mapping
    source = {
        "platform": "shopify",
        "external_id": external_id,
        "synced_at": datetime.now(timezone.utc).isoformat()
    }
    
    return ProductCreate(
        title=title,
        description=description,
        price=price,
        is_available=shopify_product.get("status") == "active",
        images=normalized_images,
        variants=variants,
        attributes=attributes,
        tags=tags,
        source_platform="shopify",
        external_id=external_id,
        source=source,
        raw_data=shopify_product
    )
