"""
Prompt Builder — assembles structured prompts for the LLM.

Phase 1: template string assembly (no Jinja2 yet).
Phase 2: Jinja2 templates per intent, add memory context.

Rules:
    - Pure function — no side effects, no IO
    - Never calls LLM directly
    - Returns a plain string ready for any provider
"""
from app.ai.intent.detector import (
    INTENT_GREETING,
    INTENT_PRODUCT_SEARCH,
    INTENT_SUPPORT,
    IntentResult,
)
from app.schemas.product import ProductSummary


SYSTEM_PROMPT = """You are a helpful AI shopping assistant for an online store.
Your job is to help customers find products, answer product questions, and provide
friendly recommendations. Sound like a skilled retail sales associate: natural,
personable, and focused on helping the shopper decide — never pushy or robotic.
Keep responses concise and clear. Always respond in the same language the customer used."""


def format_memory_context_for_prompt(user_preferences: dict | None) -> str | None:
    """
    Turn memory/user preference dict into a short line block for the user message body.

    Returns None when there is nothing useful to add.
    """
    if not user_preferences:
        return None
    lines: list[str] = []
    cats = user_preferences.get("top_categories") or []
    if cats:
        lines.append("Typical product categories of interest: " + ", ".join(str(c) for c in cats[:5]) + ".")
    avg_price = user_preferences.get("avg_price_limit")
    if avg_price is not None:
        try:
            lines.append(f"Historical average budget hint: ₹{float(avg_price):,.0f}.")
        except (TypeError, ValueError):
            pass
    if not lines:
        return None
    return " ".join(lines)


def _format_catalog_products_for_prompt(products: list[ProductSummary]) -> str:
    """Structured, DB-grounded lines: name, price, short benefit (description/tags only)."""
    lines: list[str] = []
    for i, p in enumerate(products, 1):
        cur = (p.currency or "INR").upper()
        if cur == "INR":
            price_line = f"₹{p.price:,.0f}"
        else:
            price_line = f"{cur} {p.price:,.2f}"
        benefit = (p.benefit_snippet or "").strip()
        if not benefit:
            if p.tags:
                benefit = "Highlights (from catalog): " + ", ".join(str(t) for t in p.tags[:5] if t)
            else:
                benefit = "No extra catalog notes — describe only from the product name."
        lines.append(
            f"  [{i}] Product name: {p.title}\n"
            f"      Price: {price_line}\n"
            f"      Short benefit / notes (from catalog only): {benefit}"
        )
    return "\n".join(lines)


def build_prompt(
    query: str,
    intent: IntentResult,
    products: list[ProductSummary],
    system_prompt: str | None = None,
    memory_context: str | None = None,
    store_context_chunks: list[str] | None = None,
) -> str:
    """
    Build a complete LLM prompt.

    Structure:
        [System] → role definition (embedded only when system_prompt is None)
        [Context] → products if any
        [User] → original query

    When ``system_prompt`` is set, the system role is omitted here so the caller
    can pass it as a native ``system`` message (e.g. OpenAI chat completions).
    When ``system_prompt`` is None, behaviour matches the original single-string prompt.

    Optional ``memory_context`` adds a compact preferences line before the customer turn.
    """
    # ----------------------------------------------------------------
    # System role
    # ----------------------------------------------------------------
    if system_prompt is None:
        prompt_parts = [f"System: {SYSTEM_PROMPT}\n"]
    else:
        prompt_parts = []

    # ----------------------------------------------------------------
    # Intent-specific context
    # ----------------------------------------------------------------
    if intent.intent == INTENT_GREETING:
        prompt_parts.append(
            "Context: The customer has just greeted you. "
            "Welcome them warmly and invite them to describe what they are looking for.\n"
        )

    elif intent.intent == INTENT_SUPPORT:
        prompt_parts.append(
            "Context: The customer needs support. "
            "Be empathetic, acknowledge their concern, and offer help.\n"
        )

    elif intent.intent == INTENT_PRODUCT_SEARCH:
        if products:
            product_block = _format_catalog_products_for_prompt(products)
            prompt_parts.append(
                "Context: PRODUCT SEARCH — the lines below are the ONLY in-stock catalog items "
                "you may mention. Up to three items from the database are shown.\n"
                f"{product_block}\n\n"
                "STRICT RULES:\n"
                "- Mention only products listed above, using their exact titles and prices.\n"
                "- Do not invent SKUs, discounts, delivery promises, or features not in the catalog lines.\n"
                "- If a detail is missing, say you do not have that information rather than guessing.\n"
                "- Reply like a helpful sales associate: warm, specific, 2–5 sentences; you may briefly "
                "walk through each numbered item if it helps the shopper compare.\n"
            )
        else:
            prompt_parts.append(
                "Context: PRODUCT SEARCH — no matching in-stock products were returned from the "
                "store catalog for this request.\n"
                "Act like an experienced sales associate: respond in one short paragraph. "
                "Acknowledge that nothing in the catalog matched yet. Do NOT invent product names, "
                "prices, or brands. Suggest 2–3 practical ways to refine the search (budget, category, "
                "colour, size, occasion, or product type) and invite the customer to share a bit more "
                "so you can search again.\n"
            )

    elif products:
        product_block = _format_catalog_products_for_prompt(products)
        prompt_parts.append(
            f"Context: Here are matching products from the store catalog:\n"
            f"{product_block}\n\n"
            "Use only these products; do not invent items or prices. "
            "Answer the customer's question in a friendly, sales-minded tone.\n"
        )

    else:
        prompt_parts.append(
            "Context: No catalog products are available for this turn. "
            "Keep the reply brief; do not invent inventory. "
            "Invite the customer to describe what they need or try different keywords.\n"
        )

    # ----------------------------------------------------------------
    # Price constraint hint
    # ----------------------------------------------------------------
    if intent.price_limit is not None:
        prompt_parts.append(
            f"Note: Customer's budget is ₹{intent.price_limit:,.0f}. "
            f"Only recommend products within this price range.\n"
        )

    if memory_context and memory_context.strip():
        prompt_parts.append(
            "Context: What we know about this customer's preferences from prior activity: "
            f"{memory_context.strip()}\n"
        )

    if store_context_chunks:
        compact = [c.strip() for c in store_context_chunks if c and c.strip()]
        if compact:
            prompt_parts.append(
                "Context: Store policy/content facts for grounded responses (internal):\n"
                + "\n".join(f"- {c}" for c in compact[:10])
                + "\n"
            )

    # ----------------------------------------------------------------
    # User message
    # ----------------------------------------------------------------
    prompt_parts.append(f"Customer: {query}\nAssistant:")

    return "\n".join(prompt_parts)
