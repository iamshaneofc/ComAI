"""
Product Service — business logic for product management.

Rules:
    - All product logic lives here
    - Calls ProductRepository for all DB access
    - Builds searchable_text before persisting (AI retrieval depends on it)
    - NO direct SQL, NO AI calls
"""
import structlog
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.tenant import ensure_products_single_tenant, ensure_row_store_id
from app.models.product import Product
from app.repositories.product_repo import ProductRepository
from app.schemas.product import (
    PaginatedProducts,
    ProductCreate,
    ProductResponse,
    ProductSearchFilters,
    ProductSummary,
)

logger = structlog.get_logger(__name__)


def _build_searchable_text(data: ProductCreate) -> str:
    """
    Build a single flat document for substring fallback search and for search_vector.
    Combines: title + description + tags + categories
    """
    parts = [data.title]
    if data.description:
        parts.append(data.description)
    if data.tags:
        parts.extend(data.tags)
    if data.categories:
        parts.extend(data.categories)
    return " ".join(parts).lower()


class ProductService:

    def __init__(self, db: AsyncSession = Depends(get_db)) -> None:
        self.repo = ProductRepository(db)

    # ----------------------------------------------------------------
    # Create
    # ----------------------------------------------------------------

    async def create_product(
        self, store_id, data: ProductCreate
    ) -> ProductResponse:
        product = Product(
            store_id=store_id,
            title=data.title,
            description=data.description,
            price=float(data.price),
            compare_price=float(data.compare_price) if data.compare_price else None,
            currency=data.currency,
            sku=data.sku,
            is_available=data.is_available,
            inventory_quantity=data.inventory_quantity,
            images=data.images,
            variants=data.variants,
            attributes=data.attributes,
            tags=data.tags,
            categories=data.categories,
            source_platform=data.source_platform,
            external_id=data.external_id,
            raw_data=data.raw_data,
            searchable_text=_build_searchable_text(data),
        )
        created = await self.repo.create_product(product)
        ensure_row_store_id(row_store_id=created.store_id, store_id=store_id, label="product")
        logger.info("Product created", product_id=str(created.id), store_id=str(store_id))
        return ProductResponse.model_validate(created)

    async def bulk_create_products(
        self, store_id, items: list[ProductCreate]
    ) -> list[ProductResponse]:
        """Create multiple products efficiently (sync / seed use case)."""
        products = [
            Product(
                store_id=store_id,
                title=d.title,
                description=d.description,
                price=float(d.price),
                compare_price=float(d.compare_price) if d.compare_price else None,
                currency=d.currency,
                sku=d.sku,
                is_available=d.is_available,
                inventory_quantity=d.inventory_quantity,
                images=d.images,
                variants=d.variants,
                attributes=d.attributes,
                tags=d.tags,
                categories=d.categories,
                source_platform=d.source_platform,
                external_id=d.external_id,
                raw_data=d.raw_data,
                searchable_text=_build_searchable_text(d),
            )
            for d in items
        ]
        ensure_products_single_tenant(products, store_id)
        created = await self.repo.bulk_insert_products(products)
        logger.info(
            "Bulk products created",
            count=len(created),
            store_id=str(store_id),
        )
        return [ProductResponse.model_validate(p) for p in created]

    async def bulk_upsert_products(self, store_id, items: list[ProductCreate]) -> None:
        """Upsert multiple products utilizing the repository."""
        products = [
            Product(
                store_id=store_id,
                title=d.title,
                description=d.description,
                price=float(d.price),
                compare_price=float(d.compare_price) if d.compare_price else None,
                currency=d.currency,
                sku=d.sku,
                is_available=d.is_available,
                inventory_quantity=d.inventory_quantity,
                images=d.images,
                variants=d.variants,
                attributes=d.attributes,
                tags=d.tags,
                categories=d.categories,
                source_platform=d.source_platform,
                external_id=d.external_id,
                source=d.source,
                raw_data=d.raw_data,
                searchable_text=_build_searchable_text(d),
            )
            for d in items
        ]
        ensure_products_single_tenant(products, store_id)
        await self.repo.upsert_products_bulk(products)
        logger.info(
            "Bulk products upserted",
            count=len(products),
            store_id=str(store_id),
        )

    async def upsert_product(self, store_id, d: ProductCreate) -> None:
        """Upsert a single product utilizing the repository."""
        product = Product(
            store_id=store_id,
            title=d.title,
            description=d.description,
            price=float(d.price),
            compare_price=float(d.compare_price) if d.compare_price else None,
            currency=d.currency,
            sku=d.sku,
            is_available=d.is_available,
            inventory_quantity=d.inventory_quantity,
            images=d.images,
            variants=d.variants,
            attributes=d.attributes,
            tags=d.tags,
            categories=d.categories,
            source=d.source,
            source_platform=d.source_platform,
            external_id=d.external_id,
            raw_data=d.raw_data,
            searchable_text=_build_searchable_text(d),
        )
        ensure_row_store_id(row_store_id=product.store_id, store_id=store_id, label="product")
        await self.repo.upsert_product(product)
        logger.info("Product upserted", product_external_id=d.external_id, store_id=str(store_id))

    # ----------------------------------------------------------------
    # Search
    # ----------------------------------------------------------------

    async def search_products(
        self, store_id, filters: ProductSearchFilters
    ) -> PaginatedProducts:
        products, total = await self.repo.search_products(store_id, filters)
        for p in products:
            ensure_row_store_id(row_store_id=p.store_id, store_id=store_id, label="product")
        return PaginatedProducts(
            items=[ProductResponse.model_validate(p) for p in products],
            total=total,
            offset=filters.offset,
            limit=filters.limit,
        )

    async def get_products_for_chat(
        self,
        store_id,
        keyword: str | None = None,
        max_price: float | None = None,
        categories: list[str] | None = None,
        limit: int = 5,
    ) -> list[ProductSummary]:
        """
        Focused search for the chat engine.
        Returns lightweight ProductSummary cards, not full ProductResponse.
        """
        filters = ProductSearchFilters(
            keyword=keyword,
            max_price=max_price,
            category=categories[0] if categories else None,
            limit=limit,
        )
        products, _ = await self.repo.search_products(store_id, filters)
        for p in products:
            ensure_row_store_id(row_store_id=p.store_id, store_id=store_id, label="product")
        return [ProductSummary.model_validate(p) for p in products]
