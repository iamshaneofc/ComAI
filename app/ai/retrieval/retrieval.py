"""
Retrieval Engine — translates chat queries into product search calls.

Phase 1: keyword-based retrieval via ProductService.
Phase 2: add vector similarity search (pgvector embeddings).

Architecture rule: AI layer receives DB data via service layer — NEVER queries DB directly.
"""
from uuid import UUID

import structlog

from app.ai.intent.detector import IntentResult
from app.schemas.product import ProductSummary

logger = structlog.get_logger(__name__)


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

    def __init__(self, product_service) -> None:
        # product_service is passed in by ChatService — NOT imported here
        # This keeps the AI layer decoupled from FastAPI's DI system
        self.product_service = product_service

    async def get_products_for_query(
        self,
        query: str,
        intent: IntentResult,
        store_id: UUID,
        limit: int = 5,
        user_preferences: dict | None = None
    ) -> list[ProductSummary]:
        """
        Retrieves relevant products based on the parsed intent.

        Strategy:
            1. Use extracted keywords as search term
            2. Apply price_limit if detected
            3. Scope to detected categories if any
        """
        if not intent.keywords and not intent.categories and intent.price_limit is None:
            logger.debug("No retrieval signals in intent, skipping product fetch")
            return []

        # Use the most meaningful keyword (longest word — likely the product type)
        keyword = max(intent.keywords, key=len) if intent.keywords else None
        
        categories = intent.categories
        max_price = intent.price_limit
        
        # Apply Personalization Layer
        if user_preferences:
            pref_categories = user_preferences.get("top_categories", [])
            
            # If user has no explicit category in query but has strong historical preferences, inject it
            if not categories and pref_categories:
                categories = [pref_categories[0]]
            # If user has explicit categories, append preferenced category to expand search appropriately
            elif categories and pref_categories and pref_categories[0] not in categories:
                categories.append(pref_categories[0])
                
            # If explicit max_price not set, fall back to historical average limit if established
            pref_price = user_preferences.get("avg_price_limit")
            if max_price is None and pref_price:
                max_price = pref_price

        products = await self.product_service.get_products_for_chat(
            store_id=store_id,
            keyword=keyword,
            max_price=max_price,
            categories=categories if categories else None,
            limit=limit,
        )

        logger.info(
            "Products retrieved",
            count=len(products),
            keyword=keyword,
            max_price=intent.price_limit,
            store_id=str(store_id),
        )
        return products
