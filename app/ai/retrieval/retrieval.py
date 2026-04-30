"""
Retrieval Engine — translates chat queries into product search calls.

Phase 1: keyword-based retrieval via ProductService.
Phase 2: add vector similarity search (pgvector embeddings).

Architecture rule: AI layer receives DB data via service layer — NEVER queries DB directly.
"""
from uuid import UUID

import structlog

from app.ai.intent.detector import (
    INTENT_PRICE_FILTER,
    INTENT_PRODUCT_SEARCH,
    IntentResult,
)
from app.schemas.product import ProductSummary

logger = structlog.get_logger(__name__)

# Product-search chat: always surface up to this many DB-backed items in context.
PRODUCT_SEARCH_CONTEXT_LIMIT = 5


class RetrievalEngine:
    """
    Bridges the AI intent result to the product service.

    Receives:
        product_service: injected ProductService instance
    Input:
        query: str, intent: IntentResult, store_id: UUID
    Output:
        list[ProductSummary] — ready for prompt builder and chat response
    """

    def __init__(self, product_service, store_context_service=None) -> None:
        # product_service is passed in by ChatService — NOT imported here
        # This keeps the AI layer decoupled from FastAPI's DI system
        self.product_service = product_service
        self.store_context_service = store_context_service

    @staticmethod
    def _rank_products(
        products: list[ProductSummary],
        *,
        keyword: str | None,
        max_price: float | None,
    ) -> list[ProductSummary]:
        if not products:
            return []
        terms = [t for t in (keyword or "").lower().split() if t]

        def score(p: ProductSummary) -> tuple[int, float]:
            title = (p.title or "").lower()
            tags = " ".join((p.tags or [])).lower()
            text = f"{title} {tags}"
            keyword_hits = sum(1 for t in terms if t in text)
            if max_price is None:
                price_penalty = 0.0
            else:
                price_penalty = abs(float(p.price) - float(max_price))
            return (keyword_hits, -price_penalty)

        return sorted(products, key=score, reverse=True)

    async def get_products_for_query(
        self,
        query: str,
        intent: IntentResult,
        store_id: UUID,
        limit: int = 5,
        user_preferences: dict | None = None,
    ) -> list[ProductSummary]:
        """
        Retrieves relevant products based on the parsed intent.

        Strategy:
            1. Use extracted keywords as search term (joined for product_search)
            2. Apply price_limit if detected
            3. Scope to detected categories if any
            4. For product_search / price_filter: always aim for up to PRODUCT_SEARCH_CONTEXT_LIMIT
               rows from the DB, broadening the query if the first pass returns fewer.
        """
        is_product_intent = intent.intent in (INTENT_PRODUCT_SEARCH, INTENT_PRICE_FILTER)
        effective_limit = PRODUCT_SEARCH_CONTEXT_LIMIT if is_product_intent else limit

        no_signals = (
            not intent.keywords and not intent.categories and intent.price_limit is None
        )
        if no_signals and not is_product_intent:
            logger.debug("No retrieval signals in intent, skipping product fetch")
            return []

        # Product search: phrase-style keyword improves recall vs single token.
        if intent.keywords:
            if is_product_intent:
                joined = " ".join(intent.keywords).strip()
                keyword = (joined[:120] or None) if joined else None
            else:
                keyword = max(intent.keywords, key=len)
        else:
            keyword = None

        categories = list(intent.categories) if intent.categories else []
        max_price = intent.price_limit

        # Apply Personalization Layer
        if user_preferences:
            pref_categories = user_preferences.get("top_categories", [])

            if not categories and pref_categories:
                categories = [pref_categories[0]]
            elif categories and pref_categories and pref_categories[0] not in categories:
                categories.append(pref_categories[0])

            pref_price = user_preferences.get("avg_price_limit")
            if max_price is None and pref_price:
                max_price = pref_price

        products = await self.product_service.get_products_for_chat(
            store_id=store_id,
            keyword=keyword,
            max_price=max_price,
            categories=categories if categories else None,
            limit=effective_limit,
        )

        if is_product_intent and len(products) < effective_limit:
            need = effective_limit - len(products)
            exclude = [p.id for p in products]
            extra = await self.product_service.get_products_for_chat(
                store_id=store_id,
                keyword=None,
                max_price=max_price,
                categories=categories if categories else None,
                limit=need,
                exclude_product_ids=exclude or None,
            )
            seen = {p.id for p in products}
            for p in extra:
                if p.id not in seen:
                    products.append(p)
                    seen.add(p.id)
                if len(products) >= effective_limit:
                    break

        products = self._rank_products(products, keyword=keyword, max_price=max_price)[:effective_limit]

        logger.info(
            "Products retrieved",
            count=len(products),
            keyword=keyword,
            max_price=intent.price_limit,
            store_id=str(store_id),
            intent=intent.intent,
        )
        return products

    async def get_store_context_for_query(self, store_id: UUID) -> list[str]:
        if self.store_context_service is None:
            return []
        return await self.store_context_service.get_retrieval_context(store_id)
