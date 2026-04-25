import base64
import hashlib
import hmac
import json
from uuid import uuid4

import pytest
from celery.exceptions import Retry
from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.field_crypto import encrypt_secret_text
from app.models.product import Product
from app.modules.stores.service import StoreService
from app.schemas.product import ProductCreate


@pytest.mark.asyncio
async def test_store_creation(async_client):
    resp = await async_client.post(
        "/api/v1/stores",
        headers={"X-Provision-Secret": settings.APP_SECRET_KEY},
        json={
            "name": "Store Alpha",
            "platform": "shopify",
            "domain": "alpha.myshopify.com",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["api_key"]
    assert body["domain"] == "alpha.myshopify.com"
    assert "credentials" not in body


@pytest.mark.asyncio
async def test_tenant_isolation_products(async_client, make_store):
    store_a = await make_store(name="A", slug="a", api_key="key-a")
    store_b = await make_store(name="B", slug="b", api_key="key-b")

    create_resp = await async_client.post(
        "/api/v1/products",
        headers={"X-API-KEY": store_a.api_key},
        json={"title": "Tenant A Product", "price": 1999, "categories": ["shoes"]},
    )
    assert create_resp.status_code == 201

    search_resp = await async_client.get(
        "/api/v1/products/search?keyword=Tenant+A+Product",
        headers={"X-API-KEY": store_b.api_key},
    )
    assert search_resp.status_code == 200
    assert search_resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_product_sync_uses_encrypted_shopify_token(db_session, make_store, monkeypatch):
    encrypted_token = encrypt_secret_text("shpat_test_token")
    encrypted_webhook_secret = encrypt_secret_text("test_webhook_secret")
    store = await make_store(
        name="Sync Store",
        slug="sync-store",
        api_key="sync-key",
        credentials={
            "shopify": {
                "domain": "sync.myshopify.com",
                "access_token": encrypted_token,
                "webhook_secret": encrypted_webhook_secret,
            }
        },
    )

    async def fake_fetch_and_normalize_products(store_id, domain, access_token):
        assert domain == "sync.myshopify.com"
        assert access_token == "shpat_test_token"
        yield [
            ProductCreate(
                title="Synced Sneaker",
                price=999,
                source_platform="shopify",
                external_id="shopify-1",
            )
        ]

    monkeypatch.setattr(
        "app.modules.stores.service.fetch_and_normalize_products",
        fake_fetch_and_normalize_products,
    )

    synced = await StoreService(db_session).sync_store_products(store.id)
    assert synced == 1

    rows = await db_session.execute(select(Product).where(Product.store_id == store.id))
    assert len(list(rows.scalars().all())) == 1


@pytest.mark.asyncio
async def test_chat_flow(async_client, make_store, monkeypatch):
    store = await make_store(name="Chat Store", slug="chat-store", api_key="chat-key")

    class DummyLLM:
        async def generate(self, prompt, **kwargs):
            class R:
                text = "mocked response"

            return R()

    monkeypatch.setattr("app.services.chat_service.get_llm_provider", lambda **kwargs: DummyLLM())

    resp = await async_client.post(
        "/api/v1/chat",
        headers={"X-API-KEY": store.api_key},
        json={"session_id": "9199999999", "message": "show me shoes under 2000"},
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "mocked response"


@pytest.mark.asyncio
async def test_shopify_webhook_hmac_validation(async_client, make_store):
    webhook_secret = "super_webhook_secret"
    await make_store(
        name="Webhook Store",
        slug="webhook-store",
        api_key="webhook-key",
        credentials={
            "shopify": {
                "domain": "webhook.myshopify.com",
                "access_token": encrypt_secret_text("shpat_test_token"),
                "webhook_secret": encrypt_secret_text(webhook_secret),
            }
        },
    )

    payload = {
        "id": 123,
        "title": "Webhook Product",
        "body_html": "desc",
        "status": "active",
        "variants": [{"price": "1000"}],
        "images": [],
        "tags": "new",
    }
    raw = json.dumps(payload).encode("utf-8")
    valid_sig = base64.b64encode(
        hmac.new(webhook_secret.encode("utf-8"), raw, hashlib.sha256).digest()
    ).decode("utf-8")

    invalid = await async_client.post(
        "/api/v1/webhooks/shopify/products/create",
        headers={
            "X-Shopify-Shop-Domain": "webhook.myshopify.com",
            "X-Shopify-Hmac-Sha256": "invalid",
        },
        content=raw,
    )
    assert invalid.status_code == 401

    ok = await async_client.post(
        "/api/v1/webhooks/shopify/products/create",
        headers={
            "X-Shopify-Shop-Domain": "webhook.myshopify.com",
            "X-Shopify-Hmac-Sha256": valid_sig,
            "Content-Type": "application/json",
        },
        content=raw,
    )
    assert ok.status_code == 200


@pytest.mark.asyncio
async def test_automation_task_retries_on_failure(monkeypatch):
    from app.tasks import automation_tasks as at

    class DummyIdempotency:
        def __init__(self, namespace, idempotency_key):
            self.namespace = namespace
            self.idempotency_key = idempotency_key

        def check_or_acquire(self):
            return "proceed"

        def release_lease(self):
            return None

        def mark_completed(self):
            return None

    async def failing_eval(*args, **kwargs):
        raise RuntimeError("forced automation failure")

    monkeypatch.setattr(at, "TaskIdempotency", DummyIdempotency)
    monkeypatch.setattr(at, "_evaluate_user_async", failing_eval)

    old_eager = celery_app.conf.task_always_eager
    old_propagates = celery_app.conf.task_eager_propagates
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    try:
        with pytest.raises(Retry):
            at.evaluate_user_automation.apply(
                args=[str(uuid4()), str(uuid4())],
                throw=True,
            )
    finally:
        celery_app.conf.task_always_eager = old_eager
        celery_app.conf.task_eager_propagates = old_propagates
