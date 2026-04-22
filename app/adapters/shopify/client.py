import asyncio
import logging
from typing import AsyncGenerator

import httpx

logger = logging.getLogger(__name__)

class ShopifyClient:
    def __init__(self, domain: str, access_token: str):
        self.domain = domain.strip("/") if domain else ""
        self.access_token = access_token
        self.base_url = f"https://{self.domain}/admin/api/2024-01"
        self.headers = {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json"
        }

    async def get_products(self) -> AsyncGenerator[list[dict], None]:
        url = f"{self.base_url}/products.json?limit=250"
        
        async with httpx.AsyncClient() as client:
            while url:
                try:
                    response = await client.get(url, headers=self.headers, timeout=30.0)
                    
                    if response.status_code == 429:
                        retry_after = float(response.headers.get("Retry-After", "2.0"))
                        logger.warning(f"Rate limited by Shopify. Retrying after {retry_after}s")
                        await asyncio.sleep(retry_after)
                        continue
                        
                    response.raise_for_status()
                    
                    data = response.json()
                    yield data.get("products", [])
                    
                    # Pagination via link header
                    link_header = response.headers.get("link", "")
                    url = None
                    if link_header:
                        links = link_header.split(",")
                        for link in links:
                            if 'rel="next"' in link:
                                url = link[link.find("<")+1:link.find(">")]
                                break
                except httpx.HTTPError as e:
                    logger.error(f"HTTP error occurred while fetching from Shopify: {e}")
                    # Avoid tight logging loops if the API is persistently failing. 
                    raise
