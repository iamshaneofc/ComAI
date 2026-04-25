from __future__ import annotations

from typing import Any
from uuid import UUID

from app.models.order import Order


def _normalize_customer_identifier(order: dict[str, Any]) -> str | None:
    customer = order.get("customer") or {}
    email = str(customer.get("email") or order.get("email") or "").strip().lower()
    phone = str(customer.get("phone") or order.get("phone") or "").strip().lower()
    if email:
        return f"email:{email}"
    if phone:
        digits = "".join(ch for ch in phone if ch.isdigit() or ch == "+")
        if digits:
            return f"phone:{digits}"
    return None


def normalize_orders(store_id: UUID, payloads: list[dict]) -> list[Order]:
    rows: list[Order] = []
    for order in payloads:
        external_id = order.get("id")
        if not external_id:
            continue
        cid = _normalize_customer_identifier(order)
        if not cid:
            continue
        rows.append(
            Order(
                store_id=store_id,
                external_id=str(external_id),
                order_number=str(order.get("order_number") or ""),
                customer_identifier=cid,
                status=str(order.get("financial_status") or "unknown"),
                fulfillment_status=str(order.get("fulfillment_status") or "unfulfilled"),
                metadata={
                    "name": order.get("name"),
                    "processed_at": order.get("processed_at"),
                },
            )
        )
    return rows
