"""
Product Repository — all DB queries for the Product entity.

Rules:
    - Every method receives store_id (multi-tenancy enforced at DB level)
    - No business logic — pure async SQLAlchemy queries
    - search_products: keyword via GIN-backed tsvector @@ to_tsquery, with ILIKE fallback
"""
import re
from uuid import UUID

from sqlalchemy import String, and_, cast, func, literal, or_, select
from sqlalchemy.dialects.postgresql import ARRAY, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.repositories.base import BaseRepository
from app.schemas.product import ProductSearchFilters


def _keyword_to_prefix_tsquery(keyword: str) -> str | None:
    """
    Build a safe `to_tsquery` pattern: AND-joined prefix lexemes (`token:*`).
    Returns None when there are no tokens suitable for FTS (use ILIKE only).
    """
    parts: list[str] = []
    for tok in re.findall(r"\S+", keyword.strip()):
        cleaned = re.sub(r"\W", "", tok, flags=re.UNICODE)
        if len(cleaned) < 2:
            continue
        parts.append(f"{cleaned}:*")
    if not parts:
        return None
    return " & ".join(parts)


class ProductRepository(BaseRepository[Product]):

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(model=Product, db=db)

    @staticmethod
    def _assert_single_tenant_batch(products: list[Product]) -> None:
        if not products:
            return
        sid = products[0].store_id
        if any(p.store_id != sid for p in products):
            raise ValueError("Product batch mixes multiple store_id values")

    # ----------------------------------------------------------------
    # Writes
    # ----------------------------------------------------------------

    async def create_product(self, product: Product) -> Product:
        return await self.create(product)

    async def upsert_products_bulk(self, products: list[Product]) -> None:
        """Upsert multiple products utilizing ON CONFLICT to update."""
        if not products:
            return
        self._assert_single_tenant_batch(products)

        values = []
        for p in products:
            vals = {
                "id": p.id,
                "store_id": p.store_id,
                "source_platform": p.source_platform,
                "external_id": p.external_id,
                "title": p.title,
                "description": p.description,
                "price": p.price,
                "compare_price": p.compare_price,
                "currency": p.currency,
                "sku": p.sku,
                "is_available": p.is_available,
                "inventory_quantity": p.inventory_quantity,
                "images": p.images,
                "variants": p.variants,
                "attributes": p.attributes,
                "tags": p.tags,
                "categories": p.categories,
                "searchable_text": p.searchable_text,
                "source": p.source,
                "raw_data": p.raw_data,
            }
            values.append(vals)

        stmt = insert(Product).values(values)
        
        # update fields except immutable ones
        update_dict = {
            c.name: c
            for c in stmt.excluded
            if c.name not in ("id", "store_id", "external_id", "created_at", "source_platform")
        }
        
        # Ensure we set updated_at explicitly or if the model triggers handle it, we can safely depend on standard behaviour.
        stmt = stmt.on_conflict_do_update(
            index_elements=["store_id", "external_id"],
            set_=update_dict
        )
        
        await self.db.execute(stmt)

    async def upsert_product(self, product: Product) -> Product:
        await self.upsert_products_bulk([product])
        return product

    async def bulk_insert_products(self, products: list[Product]) -> list[Product]:
        """Insert multiple products in a single flush — efficient for sync jobs."""
        self._assert_single_tenant_batch(products)
        for p in products:
            self.db.add(p)
        await self.db.flush()
        for p in products:
            await self.db.refresh(p)
        return products

    # ----------------------------------------------------------------
    # Reads
    # ----------------------------------------------------------------

    async def get_by_external_id(
        self, store_id: UUID, external_id: str
    ) -> Product | None:
        result = await self.db.execute(
            select(Product).where(
                Product.store_id == store_id,
                Product.external_id == external_id,
            )
        )
        return result.scalar_one_or_none()

    async def search_products(
        self, store_id: UUID, filters: ProductSearchFilters
    ) -> tuple[list[Product], int]:
        """
        Flexible product search with:
            - keyword: search_vector @@ to_tsquery (GIN), OR ILIKE on searchable_text
            - price range: min_price / max_price
            - category: ARRAY contains check
            - is_available: default True
        Returns (products, total_count)
        """
        conditions = [
            Product.store_id == store_id,
            Product.is_available == filters.is_available,
        ]

        if filters.keyword:
            kw = filters.keyword.strip()
            ilike = Product.searchable_text.ilike(f"%{kw}%")
            tsq_str = _keyword_to_prefix_tsquery(kw)
            if tsq_str is not None:
                tsq = func.to_tsquery("english", literal(tsq_str, type_=String()))
                conditions.append(or_(Product.search_vector.op("@@")(tsq), ilike))
            else:
                conditions.append(ilike)

        # Price range
        if filters.min_price is not None:
            conditions.append(Product.price >= filters.min_price)
        if filters.max_price is not None:
            conditions.append(Product.price <= filters.max_price)

        # Category filter (ARRAY contains)
        if filters.category:
            conditions.append(
                Product.categories.contains(
                    cast([filters.category], ARRAY(String))
                )
            )

        # Tags filter — any tag matches
        if filters.tags:
            tag_conditions = [
                Product.tags.contains(cast([t], ARRAY(String)))
                for t in filters.tags
            ]
            conditions.append(or_(*tag_conditions))

        if filters.exclude_product_ids:
            conditions.append(Product.id.notin_(filters.exclude_product_ids))

        where_clause = and_(*conditions)

        # Total count
        count_q = select(func.count()).select_from(Product).where(where_clause)
        total_result = await self.db.execute(count_q)
        total = total_result.scalar_one()

        # Paginated products — cheapest first (good for "under X" queries)
        products_q = (
            select(Product)
            .where(where_clause)
            .order_by(Product.price.asc())
            .offset(filters.offset)
            .limit(filters.limit)
        )
        result = await self.db.execute(products_q)
        products = list(result.scalars().all())

        return products, total

    async def sample_product_categories(self, store_id: UUID, row_limit: int = 60) -> list[str]:
        """Flatten distinct category labels from recent product rows (for prompt generation)."""
        result = await self.db.execute(
            select(Product.categories)
            .where(
                Product.store_id == store_id,
                Product.categories.isnot(None),
            )
            .limit(row_limit)
        )
        seen: set[str] = set()
        ordered: list[str] = []
        for cats in result.scalars().all():
            if not cats:
                continue
            for c in cats:
                if not c:
                    continue
                k = str(c).strip().lower()
                if k and k not in seen:
                    seen.add(k)
                    ordered.append(str(c).strip())
        return ordered[:20]

    async def count_for_store(self, store_id: UUID) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(Product).where(Product.store_id == store_id)
        )
        return int(result.scalar_one())
