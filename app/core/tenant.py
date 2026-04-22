"""
Strict multi-tenant helpers — every caller must use the authenticated store.

Never trust store_id from headers, query params, or path; use `request.state.store`
after `verify_store_api_key`, or pass store_id only from that source into services.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, Request


def authenticated_store_id(request: Request) -> UUID:
    """Return the tenant id bound by API key auth (401 if missing)."""
    store = getattr(request.state, "store", None)
    if store is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return store.id


def ensure_row_store_id(*, row_store_id: UUID, store_id: UUID, label: str = "row") -> None:
    """
    Guardrail: ORM row must belong to the active tenant.
    Raises HTTPException 500 (misconfiguration / bug) if violated.
    """
    if row_store_id != store_id:
        raise HTTPException(
            status_code=500,
            detail=f"Tenant isolation violation: {label} store mismatch",
        )


def ensure_products_single_tenant(products: list, expected_store_id: UUID) -> None:
    """Reject bulk product payloads that mix tenants (defensive)."""
    for p in products:
        sid = getattr(p, "store_id", None)
        if sid is not None and sid != expected_store_id:
            raise HTTPException(
                status_code=500,
                detail="Tenant isolation violation: mixed store_id in product batch",
            )
