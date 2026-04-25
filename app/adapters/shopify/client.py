import asyncio
import logging
from typing import AsyncGenerator

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


async def fetch_access_token_client_credentials(
    domain: str, client_id: str, client_secret: str
) -> tuple[str, int | None]:
    """
    Exchange app client ID + secret for an Admin API token (OAuth client_credentials).

    Returns ``(access_token, expires_in_seconds)`` where ``expires_in_seconds`` may be ``None``
    if Shopify omits it (caller may apply a default cache TTL).

    Use when the Dev Dashboard app does not expose a static ``shpat_`` / ``shpca_`` token in Admin.
    """
    shop = domain.strip().lower().replace("https://", "").split("/")[0]
    url = f"https://{shop}/admin/oauth/access_token"
    async with httpx.AsyncClient() as http:
        response = await http.post(
            url,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id.strip(),
                "client_secret": client_secret.strip(),
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30.0,
        )
        if not response.is_success:
            body = (response.text or "")[:800]
            raise httpx.HTTPError(
                f"Shopify OAuth {response.status_code} {response.reason_phrase}: {body}"
            )
        data = response.json()
        token = data.get("access_token")
        if not isinstance(token, str) or not token:
            raise ValueError("Shopify token response missing access_token")
        raw_exp = data.get("expires_in")
        expires_in: int | None = int(raw_exp) if isinstance(raw_exp, int) else None
        return token, expires_in


class ShopifyClient:
    def __init__(self, domain: str, access_token: str):
        self.domain = domain.strip("/") if domain else ""
        self.access_token = access_token
        api_version = settings.SHOPIFY_API_VERSION.strip()
        self.base_url = f"https://{self.domain}/admin/api/{api_version}"
        self.headers = {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json",
        }

    async def _request_json(self, url: str) -> tuple[dict, str | None]:
        async with httpx.AsyncClient() as client:
            while True:
                response = await client.get(url, headers=self.headers, timeout=30.0)
                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", "2.0"))
                    logger.warning(f"Rate limited by Shopify. Retrying after {retry_after}s")
                    await asyncio.sleep(retry_after)
                    continue
                response.raise_for_status()
                next_url = None
                link_header = response.headers.get("link", "")
                if link_header:
                    links = link_header.split(",")
                    for link in links:
                        if 'rel="next"' in link:
                            next_url = link[link.find("<") + 1:link.find(">")]
                            break
                return response.json(), next_url

    async def _paginate(self, start_url: str, key: str) -> AsyncGenerator[list[dict], None]:
        url: str | None = start_url
        while url:
            data, url = await self._request_json(url)
            yield data.get(key, [])

    async def get_products(self) -> AsyncGenerator[list[dict], None]:
        url = f"{self.base_url}/products.json?limit=250"
        try:
            async for batch in self._paginate(url, "products"):
                yield batch
        except httpx.HTTPError as e:
            logger.error(f"HTTP error occurred while fetching from Shopify: {e}")
            raise

    async def get_product_listings(self) -> AsyncGenerator[list[dict], None]:
        url = f"{self.base_url}/product_listings.json?limit=250"
        try:
            async for batch in self._paginate(url, "product_listings"):
                yield batch
        except httpx.HTTPStatusError as e:
            if e.response.status_code in {403, 404}:
                logger.info("Shopify product_listings unavailable", status=e.response.status_code)
                return
            raise

    async def get_product_feeds(self) -> AsyncGenerator[list[dict], None]:
        url = f"{self.base_url}/product_feeds.json?limit=250"
        try:
            async for batch in self._paginate(url, "product_feeds"):
                yield batch
        except httpx.HTTPStatusError as e:
            if e.response.status_code in {403, 404}:
                logger.info("Shopify product_feeds unavailable", status=e.response.status_code)
                return
            raise

    async def get_pages(self) -> AsyncGenerator[list[dict], None]:
        url = f"{self.base_url}/pages.json?limit=250"
        async for batch in self._paginate(url, "pages"):
            yield batch

    async def get_policies(self) -> list[dict]:
        url = f"{self.base_url}/policies.json"
        data, _ = await self._request_json(url)
        return data.get("policies", [])

    async def get_metaobjects(self) -> AsyncGenerator[list[dict], None]:
        url = f"{self.base_url}/metaobjects.json?limit=250"
        try:
            async for batch in self._paginate(url, "metaobjects"):
                yield batch
        except httpx.HTTPStatusError as e:
            if e.response.status_code in {403, 404}:
                logger.info("Shopify metaobjects unavailable", status=e.response.status_code)
                return
            raise

    async def get_orders(self, *, status: str = "any") -> AsyncGenerator[list[dict], None]:
        url = f"{self.base_url}/orders.json?limit=250&status={status}"
        try:
            async for batch in self._paginate(url, "orders"):
                yield batch
        except httpx.HTTPStatusError as e:
            if e.response.status_code in {403, 404}:
                logger.info("Shopify orders unavailable", status=e.response.status_code)
                return
            raise

    async def get_reports(self) -> list[dict]:
        url = f"{self.base_url}/reports.json?limit=250"
        try:
            data, _ = await self._request_json(url)
            return data.get("reports", [])
        except httpx.HTTPStatusError as e:
            if e.response.status_code in {403, 404}:
                logger.info("Shopify reports unavailable", status=e.response.status_code)
                return []
            raise

    async def get_shop(self) -> dict:
        url = f"{self.base_url}/shop.json"
        data, _ = await self._request_json(url)
        return data.get("shop", {})

    async def fetch_orders_page(self, *, limit: int = 5, status: str = "any") -> list[dict]:
        """First page of orders (Admin API). Same auth path as product sync."""
        url = f"{self.base_url}/orders.json?limit={limit}&status={status}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, timeout=30.0)
            response.raise_for_status()
            data = response.json()
            return data.get("orders", [])
