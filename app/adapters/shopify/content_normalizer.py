from __future__ import annotations

from typing import Any
from uuid import UUID

from app.models.metaobject import MetaObject
from app.models.store_content import StoreContent


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalize_pages(store_id: UUID, pages: list[dict]) -> list[StoreContent]:
    rows: list[StoreContent] = []
    for page in pages:
        external_id = str(page.get("id") or page.get("handle") or "")
        title = _safe_text(page.get("title") or page.get("handle"))
        if not external_id or not title:
            continue
        rows.append(
            StoreContent(
                store_id=store_id,
                type="page",
                title=title,
                body=_safe_text(page.get("body_html")),
                metadata={
                    "handle": page.get("handle"),
                    "published_at": page.get("published_at"),
                    "author": page.get("author"),
                },
                external_id=f"page:{external_id}",
            )
        )
    return rows


def normalize_policies(store_id: UUID, policies: list[dict]) -> list[StoreContent]:
    rows: list[StoreContent] = []
    for policy in policies:
        handle = _safe_text(policy.get("handle"))
        if not handle:
            continue
        title = _safe_text(policy.get("title") or handle.replace("_", " ").title())
        rows.append(
            StoreContent(
                store_id=store_id,
                type="policy",
                title=title,
                body=_safe_text(policy.get("body")),
                metadata={
                    "url": policy.get("url"),
                    "updated_at": policy.get("updated_at"),
                },
                external_id=f"policy:{handle}",
            )
        )
    return rows


def normalize_metaobjects(store_id: UUID, items: list[dict]) -> list[MetaObject]:
    rows: list[MetaObject] = []
    for item in items:
        type_name = _safe_text(item.get("type") or "metaobject")
        handle = _safe_text(item.get("handle") or item.get("id"))
        if not handle:
            continue
        key = f"{type_name}:{handle}"
        rows.append(
            MetaObject(
                store_id=store_id,
                key=key,
                value={
                    "id": item.get("id"),
                    "type": type_name,
                    "handle": item.get("handle"),
                    "fields": item.get("fields") or {},
                    "updated_at": item.get("updated_at"),
                },
            )
        )
    return rows


def normalize_product_listing_context(listings: list[dict], feeds: list[dict]) -> list[dict]:
    return [
        {
            "listings_count": len(listings),
            "feeds_count": len(feeds),
            "listing_ids": [x.get("product_id") for x in listings[:30] if x.get("product_id")],
        }
    ]
