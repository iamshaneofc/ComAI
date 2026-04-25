"""
Store Service — business logic for store (tenant) management.

Rules:
    - All store business logic lives here
    - Calls StoreRepository for DB access (never raw SQL)
    - Raises HTTPException for user-facing errors
    - Does NOT format HTTP responses (that's the API layer)
"""
import structlog
from fastapi import Depends, HTTPException, status
from slugify import slugify
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from uuid import UUID

from app.adapters.custom.json_feed import fetch_custom_feed_products
from app.adapters.shopify.content_normalizer import (
    normalize_metaobjects,
    normalize_pages,
    normalize_policies,
    normalize_product_listing_context,
)
from app.adapters.shopify.order_normalizer import normalize_orders
from app.adapters.shopify.oauth_token_cache import get_cached_shopify_oauth_admin_token
from app.adapters.shopify.domain_utils import normalize_shopify_shop_hostname
from app.adapters.shopify.client import ShopifyClient
from app.adapters.shopify.sync import fetch_and_normalize_products
from app.core.config import get_settings
from app.core.database import get_db
from app.core.field_crypto import decrypt_secret_text
from app.core.onboarding import (
    ALLOWED_ONBOARDING_STATUSES,
    ONBOARDING_CREATED,
)
from app.models.order import Order
from app.models.store_content import StoreContent
from app.models.store import Store
from app.modules.products.service import ProductService
from app.repositories.agent_repo import AgentRepository
from app.repositories.metaobject_repo import MetaObjectRepository
from app.repositories.order_repo import OrderRepository
from app.repositories.product_repo import ProductRepository
from app.repositories.store_analytics_metric_repo import StoreAnalyticsMetricRepository
from app.repositories.store_repo import StoreRepository
from app.repositories.store_content_repo import StoreContentRepository
from app.schemas.store import StoreCreate, StoreMeStatusResponse, StoreUpdate
from app.schemas.product import ProductCreate

logger = structlog.get_logger(__name__)


def _initial_credentials(data: StoreCreate) -> dict | None:
    """Platform-specific secrets live under credentials (e.g. credentials.shopify.domain)."""
    if not data.domain:
        return None
    domain_norm = data.domain.strip().lower()
    creds: dict = {}
    if data.platform == "shopify":
        creds["shopify"] = {"domain": domain_norm}
    else:
        creds[data.platform] = {"domain": domain_norm}
    return creds


class StoreService:
    """Orchestrates all store operations."""

    def __init__(self, db: AsyncSession = Depends(get_db)) -> None:
        self.db = db
        self.repo = StoreRepository(db)

    # ----------------------------------------------------------------
    # Create
    # ----------------------------------------------------------------

    async def create_store(self, data: StoreCreate) -> Store:
        """
        Creates a new store (tenant).

        Business rules:
            - Slug is auto-generated from name (unique)
            - Duplicate slugs get a numeric suffix
            - Shopify/custom domain is stored only under credentials
        """
        base_slug = slugify(data.name)

        slug = base_slug
        counter = 1
        while await self.repo.get_by_slug(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1

        credentials = _initial_credentials(data)

        store = Store(
            name=data.name,
            slug=slug,
            platform=data.platform,
            whatsapp_phone_number=data.whatsapp_phone_number,
            credentials=credentials,
            onboarding_status=ONBOARDING_CREATED,
        )

        created = await self.repo.create_store(store)
        logger.info("Store created", store_id=str(created.id), slug=slug)
        return created

    # ----------------------------------------------------------------
    # Read
    # ----------------------------------------------------------------

    async def get_store(self, store_id) -> Store:
        """Fetch a store by UUID. Raises 404 if not found."""
        store = await self.repo.get_by_id(store_id)
        if store is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Store {store_id} not found",
            )
        return store

    async def list_stores(
        self,
        offset: int = 0,
        limit: int = 20,
        active_only: bool = True,
    ) -> tuple[list[Store], int]:
        """Returns paginated stores with total count."""
        return await self.repo.list_stores(
            offset=offset, limit=limit, active_only=active_only
        )

    # ----------------------------------------------------------------
    # Update
    # ----------------------------------------------------------------

    async def update_store(self, store_id, data: StoreUpdate) -> Store:
        """Partial update — only provided fields are changed."""
        store = await self.get_store(store_id)
        raw = data.model_dump(exclude_none=True)
        updates: dict = {}

        if "domain" in raw:
            domain = raw.pop("domain")
            creds = dict(store.credentials or {})
            if store.platform == "shopify":
                shop = dict(creds.get("shopify") or {})
                if domain is not None:
                    shop["domain"] = str(domain).strip().lower()
                creds["shopify"] = shop
            else:
                plat = dict(creds.get(store.platform) or {})
                if domain is not None:
                    plat["domain"] = str(domain).strip().lower()
                creds[store.platform] = plat
            updates["credentials"] = creds

        for column in ("name", "whatsapp_phone_number", "is_active"):
            if column in raw:
                updates[column] = raw[column]

        if not updates:
            return store
        updated = await self.repo.update_store(store, updates)
        logger.info("Store updated", store_id=str(store_id), fields=list(updates.keys()))
        return updated

    # ----------------------------------------------------------------
    # Deactivate (soft delete)
    # ----------------------------------------------------------------

    async def deactivate_store(self, store_id) -> Store:
        """Soft-deletes a store by marking is_active=False."""
        store = await self.get_store(store_id)
        deactivated = await self.repo.deactivate_store(store)
        logger.info("Store deactivated", store_id=str(store_id))
        return deactivated

    # ----------------------------------------------------------------
    # Sync Orchestration
    # ----------------------------------------------------------------

    async def sync_store_products(self, store_id) -> int:
        """Full synchronization pipeline. Orchestrated via the service layer."""
        structlog.contextvars.bind_contextvars(flow="sync", store_id=str(store_id))
        store = await self.get_store(store_id)
        product_service = ProductService(self.db)

        if get_settings().SHOPIFY_SYNC_MODE == "mock":
            mock_products = [
                ProductCreate(
                    title=f"{store.name} Starter Product",
                    description="Mock-synced product for staging validation",
                    price=999.0,
                    currency="INR",
                    is_available=True,
                    categories=["mock"],
                    source_platform="shopify",
                    external_id="mock-shopify-1",
                    source={"platform": "shopify", "mode": "mock"},
                    raw_data={"mock": True},
                )
            ]
            await product_service.bulk_upsert_products(store_id, mock_products)
            await self.db.commit()
            return len(mock_products)

        if store.platform == "custom":
            custom_cfg = (store.credentials or {}).get("custom", {})
            products_url = str(custom_cfg.get("products_url") or "").strip()
            items_path = str(custom_cfg.get("items_path") or "").strip()
            field_map = custom_cfg.get("field_map")
            if not products_url:
                logger.error(
                    "Custom products_url missing for store",
                    store_id=str(store_id),
                )
                return 0
            normalized_products = await fetch_custom_feed_products(
                store_id=store_id,
                products_url=products_url,
                items_path=items_path,
                field_map=field_map if isinstance(field_map, dict) else None,
            )
            if not normalized_products:
                return 0
            await product_service.bulk_upsert_products(store_id, normalized_products)
            await self.db.commit()
            return len(normalized_products)

        domain_raw, _, _ = self.get_decrypted_shopify_credentials(store)
        domain = normalize_shopify_shop_hostname(domain_raw) if domain_raw else None

        if not domain:
            logger.error(
                "Shopify shop hostname missing for store (set credentials.shopify.domain)",
                store_id=str(store_id),
            )
            return 0

        total_synced = 0
        async for normalized_products in fetch_and_normalize_products(store_id, domain):
            await product_service.bulk_upsert_products(store_id, normalized_products)
            await self.db.commit()
            total_synced += len(normalized_products)

        await self._sync_shopify_content_and_metaobjects(store_id, store, domain)
        await self._sync_shopify_orders(store_id, store, domain)
        await self._sync_shopify_analytics(store_id, store, domain)
        return total_synced

    async def _sync_shopify_content_and_metaobjects(self, store_id: UUID, store: Store, domain: str) -> None:
        token = await self._resolve_shopify_admin_token(store_id, store, domain)
        if not token:
            logger.info(
                "Skipping Shopify content/metaobjects sync: no admin token available",
                store_id=str(store_id),
            )
            return

        client = ShopifyClient(domain=domain, access_token=token)
        content_repo = StoreContentRepository(self.db)
        meta_repo = MetaObjectRepository(self.db)

        pages_raw: list[dict] = []
        async for batch in client.get_pages():
            pages_raw.extend(batch)
        policies_raw = await client.get_policies()
        page_rows = normalize_pages(store_id, pages_raw)
        policy_rows = normalize_policies(store_id, policies_raw)
        if page_rows or policy_rows:
            await content_repo.upsert_bulk(page_rows + policy_rows)

        meta_raw: list[dict] = []
        async for batch in client.get_metaobjects():
            meta_raw.extend(batch)
        meta_rows = normalize_metaobjects(store_id, meta_raw)
        if meta_rows:
            await meta_repo.upsert_bulk(meta_rows)

        listings_raw: list[dict] = []
        async for batch in client.get_product_listings():
            listings_raw.extend(batch)
        feeds_raw: list[dict] = []
        async for batch in client.get_product_feeds():
            feeds_raw.extend(batch)
        listing_context = normalize_product_listing_context(listings_raw, feeds_raw)
        if listing_context:
            await content_repo.upsert_bulk(
                [
                    StoreContent(
                        store_id=store_id,
                        type="catalog_context",
                        title="Shopify catalog context",
                        body=None,
                        metadata=listing_context[0],
                        external_id="catalog:shopify_context",
                    )
                ]
            )
        await self.db.commit()

    async def _resolve_shopify_admin_token(self, store_id: UUID, store: Store, domain: str) -> str | None:
        _, access_token, _ = self.get_decrypted_shopify_credentials(store)
        if access_token:
            return access_token
        client_id, client_secret = self.get_decrypted_shopify_oauth_credentials(store)
        if not client_id or not client_secret:
            return None
        return await get_cached_shopify_oauth_admin_token(
            store_id=str(store_id),
            domain=domain,
            client_id=client_id,
            client_secret=client_secret,
        )

    async def _sync_shopify_orders(self, store_id: UUID, store: Store, domain: str) -> None:
        token = await self._resolve_shopify_admin_token(store_id, store, domain)
        if not token:
            logger.info("Skipping Shopify orders sync: no admin token available", store_id=str(store_id))
            return
        client = ShopifyClient(domain=domain, access_token=token)
        repo = OrderRepository(self.db)
        total = 0
        async for batch in client.get_orders(status="any"):
            normalized = normalize_orders(store_id, batch)
            if not normalized:
                continue
            await repo.upsert_bulk(normalized)
            await self.db.commit()
            total += len(normalized)
        logger.info("Shopify orders sync completed", store_id=str(store_id), orders_synced=total)

    async def _sync_shopify_analytics(self, store_id: UUID, store: Store, domain: str) -> None:
        token = await self._resolve_shopify_admin_token(store_id, store, domain)
        if not token:
            logger.info("Skipping Shopify analytics sync: no admin token available", store_id=str(store_id))
            return
        client = ShopifyClient(domain=domain, access_token=token)
        repo = StoreAnalyticsMetricRepository(self.db)
        reports = await client.get_reports()
        shop = await client.get_shop()

        metrics: dict[str, dict] = {
            "shop_summary": {
                "name": shop.get("name"),
                "plan_name": shop.get("plan_name"),
                "currency": shop.get("currency"),
                "timezone": shop.get("iana_timezone"),
            },
            "reports_summary": {
                "reports_count": len(reports),
                "sample": [r.get("name") for r in reports[:10]],
            },
        }

        # Lightweight aggregate derived from synced minimal orders.
        # We avoid exposing raw orders and keep only aggregate counts.
        result = await self.db.execute(
            select(
                func.count(Order.id).label("total"),
                func.sum(case((Order.fulfillment_status == "fulfilled", 1), else_=0)).label("fulfilled"),
            ).where(Order.store_id == store_id)
        )
        row = result.one()
        metrics["orders_snapshot"] = {
            "orders_total": int(row.total or 0),
            "orders_fulfilled": int(row.fulfilled or 0),
        }

        await repo.upsert_many(store_id, metrics)
        await self.db.commit()

    async def get_store_by_shop_domain(self, domain: str) -> Store | None:
        return await self.repo.get_by_domain(domain)

    async def get_store_by_whatsapp_phone_number(self, phone_number: str) -> Store | None:
        return await self.repo.get_by_whatsapp_phone_number(phone_number)

    @staticmethod
    def get_decrypted_shopify_credentials(store: Store) -> tuple[str | None, str | None, str | None]:
        creds = store.credentials.get("shopify", {}) if store.credentials else {}
        domain = creds.get("domain")
        raw_access_token = creds.get("access_token")
        raw_webhook_secret = creds.get("webhook_secret")
        access_token = decrypt_secret_text(raw_access_token) or (raw_access_token if isinstance(raw_access_token, str) else None)
        webhook_secret = decrypt_secret_text(raw_webhook_secret) or (
            raw_webhook_secret if isinstance(raw_webhook_secret, str) else None
        )
        return domain, access_token, webhook_secret

    @staticmethod
    def get_decrypted_shopify_oauth_credentials(store: Store) -> tuple[str | None, str | None]:
        """Returns (client_id, client_secret) for OAuth client_credentials when no static Admin token."""
        creds = store.credentials.get("shopify", {}) if store.credentials else {}
        raw_cid = creds.get("client_id")
        client_id = raw_cid.strip() if isinstance(raw_cid, str) else None
        raw_cs = creds.get("client_secret")
        client_secret = None
        if isinstance(raw_cs, str) and raw_cs:
            client_secret = decrypt_secret_text(raw_cs) or raw_cs
        return (client_id or None), (client_secret or None)

    # ----------------------------------------------------------------
    # Onboarding status
    # ----------------------------------------------------------------

    async def update_onboarding_status(self, store_id: UUID, status: str) -> None:
        """Persist onboarding lifecycle state (no HTTP semantics)."""
        if status not in ALLOWED_ONBOARDING_STATUSES:
            raise ValueError(f"Invalid onboarding_status: {status}")
        store = await self.repo.get_by_id(store_id)
        if store is None:
            logger.warning("update_onboarding_status: store not found", store_id=str(store_id))
            return
        await self.repo.update_store(store, {"onboarding_status": status})

    async def get_me_onboarding_status(self, store_id: UUID) -> StoreMeStatusResponse:
        """Aggregate progress for GET /stores/me/status."""
        store = await self.get_store(store_id)
        products = ProductRepository(self.db)
        agents = AgentRepository(self.db)
        products_count = await products.count_for_store(store_id)
        chat_agent = await agents.get_by_type(store_id, "chat")
        return StoreMeStatusResponse(
            onboarding_status=store.onboarding_status,  # type: ignore[arg-type]
            products_count=products_count,
            agent_ready=chat_agent is not None,
        )
