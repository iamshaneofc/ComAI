"""
End-to-End Smoke Test — Core Backend & Chat Engine.

Requires:
    APP_SECRET_KEY in env (same as backend) for store provisioning
    OPENAI_API_KEY optional for real LLM calls
"""
import asyncio
import os
from uuid import uuid4

import httpx
from rich.console import Console

console = Console()
API_URL = "http://localhost:8000/api/v1"
PROVISION_SECRET = os.environ.get("APP_SECRET_KEY", "")


async def main():
    console.print("[bold yellow]Starting E2E Smoke Test...[/bold yellow]")

    if not PROVISION_SECRET:
        console.print("[bold red]Set APP_SECRET_KEY in the environment (must match backend).[/bold red]")
        return

    async with httpx.AsyncClient(base_url=API_URL, timeout=120.0) as client:
        console.print("\n[bold cyan]1. Provisioning Store...[/bold cyan]")
        store_res = await client.post(
            "/stores",
            json={
                "name": f"Smoke Test Store {uuid4().hex[:6]}",
                "platform": "shopify",
                "domain": "smoketest.myshopify.com",
            },
            headers={"X-Provision-Secret": PROVISION_SECRET},
        )

        if store_res.status_code != 201:
            console.print(f"[bold red]Failed to create store: {store_res.text}[/bold red]")
            return

        store = store_res.json()
        store_id = store["id"]
        api_key = store.get("api_key")
        if not api_key:
            console.print("[bold red]Response missing api_key[/bold red]")
            return

        console.print(f"[green]✓ Store created:[/green] {store_id} ({store['slug']})")

        auth_headers = {"X-API-KEY": api_key}

        console.print("\n[bold cyan]2. Seeding Products...[/bold cyan]")
        products_payload = [
            {
                "title": "Nike Air Max",
                "description": "Premium running shoes",
                "price": 4500.0,
                "currency": "INR",
                "tags": ["shoes", "nike", "running"],
                "categories": ["shoes", "sports"],
            },
            {
                "title": "Puma Sport Sneakers",
                "description": "Comfortable everyday sneakers",
                "price": 2500.0,
                "currency": "INR",
                "tags": ["shoes", "puma", "sneakers"],
                "categories": ["shoes", "casual"],
            },
            {
                "title": "Levi's Denim Jacket",
                "description": "Classic blue denim jacket",
                "price": 3500.0,
                "currency": "INR",
                "tags": ["clothing", "jacket", "denim"],
                "categories": ["clothing", "outerwear"],
            },
        ]

        prod_res = await client.post("/products/bulk", json=products_payload, headers=auth_headers)
        if prod_res.status_code != 201:
            console.print(f"[bold red]Failed to seed products: {prod_res.text}[/bold red]")
            return

        console.print(f"[green]✓ {len(prod_res.json())} products seeded.[/green]")

        console.print("\n[bold cyan]3. Testing DB Search (shoes under 3000)...[/bold cyan]")
        search_res = await client.get(
            "/products/search",
            params={"keyword": "shoes", "max_price": 3000},
            headers=auth_headers,
        )

        search_data = search_res.json()
        console.print(f"Found {search_data['total']} products matching criteria:")
        for item in search_data["items"]:
            console.print(f"  - {item['title']} (₹{item['price']})")

        console.print("\n[bold cyan]4. Testing AI Chat Engine...[/bold cyan]")
        queries = [
            "Hi there!",
            "Can you show me some shoes under 3000 rs?",
            "Do you have any jackets?",
        ]

        for q in queries:
            console.print(f"\n[bold magenta]User:[/bold magenta] {q}")
            chat_res = await client.post(
                "/chat",
                json={"message": q, "session_id": "smoke-session"},
                headers=auth_headers,
            )

            if chat_res.status_code != 200:
                console.print(f"[bold red]Chat error: {chat_res.text}[/bold red]")
                continue

            reply = chat_res.json()
            console.print(f"[bold green]AI (Intent: {reply['intent']}):[/bold green]\n{reply['message']}")

            if reply["products"]:
                console.print("[dim]Products attached:[/dim]")
                for p in reply["products"]:
                    console.print(f"[dim]  - {p['title']} (₹{p['price']})[/dim]")

    console.print("\n[bold yellow]Smoke test completed![/bold yellow]")


if __name__ == "__main__":
    asyncio.run(main())
