from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from uuid import UUID

import httpx

from app.schemas.product import ProductCreate

DEFAULT_FIELD_MAP: dict[str, str] = {
    "title": "title",
    "description": "description",
    "price": "price",
    "compare_price": "compare_price",
    "currency": "currency",
    "sku": "sku",
    "is_available": "is_available",
    "inventory_quantity": "inventory_quantity",
    "images": "images",
    "variants": "variants",
    "attributes": "attributes",
    "tags": "tags",
    "categories": "categories",
    "external_id": "id",
}


def _nested_get(obj: Any, path: str) -> Any:
    if not path:
        return None
    current = obj
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list):
            try:
                idx = int(part)
            except (TypeError, ValueError):
                return None
            if idx < 0 or idx >= len(current):
                return None
            current = current[idx]
        else:
            return None
    return current


def _to_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_bool(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"1", "true", "yes", "y", "in_stock", "available"}:
            return True
        if v in {"0", "false", "no", "n", "out_of_stock", "unavailable"}:
            return False
    return default


def _to_str_list(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, list):
        out = [str(v).strip() for v in value if str(v).strip()]
        return out or None
    if isinstance(value, str):
        parts = [p.strip() for p in value.split(",") if p.strip()]
        return parts or None
    return None


def _to_images(value: Any) -> list[dict] | None:
    if value is None:
        return None
    if isinstance(value, list):
        out: list[dict] = []
        for item in value:
            if isinstance(item, dict):
                url = item.get("url") or item.get("src")
                if url:
                    out.append({"url": str(url), "alt": item.get("alt")})
            elif isinstance(item, str) and item.strip():
                out.append({"url": item.strip(), "alt": None})
        return out or None
    if isinstance(value, str) and value.strip():
        return [{"url": value.strip(), "alt": None}]
    return None


def _as_items(payload: Any, items_path: str) -> Iterable[dict]:
    root = _nested_get(payload, items_path.strip()) if items_path.strip() else payload
    if isinstance(root, list):
        return [x for x in root if isinstance(x, dict)]
    if isinstance(root, dict):
        return [root]
    return []


def _normalize_item(item: dict[str, Any], field_map: dict[str, str]) -> ProductCreate | None:
    title = _nested_get(item, field_map.get("title", "title"))
    if not title:
        return None

    price = _to_float(_nested_get(item, field_map.get("price", "price")))
    if price <= 0:
        return None

    return ProductCreate(
        title=str(title).strip(),
        description=_nested_get(item, field_map.get("description", "description")),
        price=price,
        compare_price=_to_float(_nested_get(item, field_map.get("compare_price", "compare_price")), default=0.0)
        or None,
        currency=str(_nested_get(item, field_map.get("currency", "currency")) or "INR"),
        sku=_nested_get(item, field_map.get("sku", "sku")),
        is_available=_to_bool(_nested_get(item, field_map.get("is_available", "is_available")), default=True),
        inventory_quantity=_to_int(
            _nested_get(item, field_map.get("inventory_quantity", "inventory_quantity")),
            default=0,
        ),
        images=_to_images(_nested_get(item, field_map.get("images", "images"))),
        variants=_nested_get(item, field_map.get("variants", "variants")),
        attributes=_nested_get(item, field_map.get("attributes", "attributes")),
        tags=_to_str_list(_nested_get(item, field_map.get("tags", "tags"))),
        categories=_to_str_list(_nested_get(item, field_map.get("categories", "categories"))),
        source_platform="custom",
        external_id=str(
            _nested_get(item, field_map.get("external_id", "id"))
            or _nested_get(item, "slug")
            or _nested_get(item, "sku")
            or title
        ),
        source={"platform": "custom", "type": "json_feed"},
        raw_data=item,
    )


async def fetch_custom_feed_products(
    store_id: UUID,
    products_url: str,
    items_path: str = "",
    field_map: dict[str, str] | None = None,
) -> list[ProductCreate]:
    merged_map = {**DEFAULT_FIELD_MAP, **(field_map or {})}

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        response = await client.get(products_url)
        response.raise_for_status()
        payload = response.json()

    products: list[ProductCreate] = []
    for item in _as_items(payload, items_path):
        normalized = _normalize_item(item, merged_map)
        if normalized is not None:
            products.append(normalized)

    return products
