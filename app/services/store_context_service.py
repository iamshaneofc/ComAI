from __future__ import annotations

from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.metaobject_repo import MetaObjectRepository
from app.repositories.store_content_repo import StoreContentRepository


class StoreContextService:
    """Builds safe, tenant-scoped context snippets from ingested content/metaobjects."""

    def __init__(self, db: AsyncSession = Depends(get_db)) -> None:
        self.content_repo = StoreContentRepository(db)
        self.meta_repo = MetaObjectRepository(db)

    async def get_prompt_context(self, store_id: UUID) -> dict:
        policies = await self.content_repo.list_by_types(store_id, ["policy"], limit=8)
        pages = await self.content_repo.list_by_types(store_id, ["page"], limit=20)
        metaobjects = await self.meta_repo.list_for_store(store_id, limit=30)

        policy_lines: list[str] = []
        for row in policies:
            text = (row.body or "").strip()
            if not text:
                continue
            compact = " ".join(text.split())
            policy_lines.append(f"{row.title}: {compact[:260]}")

        faq_lines: list[str] = []
        for row in metaobjects:
            fields = row.value.get("fields", {}) if isinstance(row.value, dict) else {}
            question = (fields.get("question") or fields.get("title") or "").strip()
            answer = (fields.get("answer") or fields.get("body") or "").strip()
            if question and answer:
                faq_lines.append(f"Q: {question} A: {' '.join(answer.split())[:220]}")
        if not faq_lines:
            for page in pages:
                t = page.title.lower()
                if "faq" in t and page.body:
                    faq_lines.append(f"FAQ page: {page.title}")
                    if len(faq_lines) >= 6:
                        break

        tone_hint = "friendly"
        if policy_lines:
            joined = " ".join(policy_lines).lower()
            if any(k in joined for k in ("premium", "luxury", "exclusive")):
                tone_hint = "premium"
            elif any(k in joined for k in ("fast", "deal", "offer", "discount")):
                tone_hint = "aggressive"

        return {
            "tone_hint": tone_hint,
            "policies": policy_lines[:8],
            "faqs": faq_lines[:8],
        }

    async def get_retrieval_context(self, store_id: UUID) -> list[str]:
        policies = await self.content_repo.list_by_types(store_id, ["policy"], limit=6)
        metaobjects = await self.meta_repo.list_for_store(store_id, limit=12)
        chunks: list[str] = []
        for row in policies:
            body = " ".join((row.body or "").split())
            if body:
                chunks.append(f"Policy::{row.title}::{body[:260]}")
        for row in metaobjects:
            value = row.value if isinstance(row.value, dict) else {"value": row.value}
            fields = value.get("fields") if isinstance(value, dict) else None
            if isinstance(fields, dict):
                parts = []
                for k, v in fields.items():
                    if isinstance(v, (str, int, float)) and str(v).strip():
                        parts.append(f"{k}={str(v).strip()}")
                if parts:
                    chunks.append(f"Meta::{row.key}::{' | '.join(parts[:6])}")
            if len(chunks) >= 12:
                break
        return chunks[:12]
