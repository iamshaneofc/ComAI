"""
Prompt Builder — assembles structured prompts for the LLM.

Phase 1: template string assembly (no Jinja2 yet).
Phase 2: Jinja2 templates per intent, add memory context.

Rules:
    - Pure function — no side effects, no IO
    - Never calls LLM directly
    - Returns a plain string ready for any provider
"""
from app.ai.intent.detector import IntentResult, INTENT_GREETING, INTENT_SUPPORT
from app.schemas.product import ProductSummary


SYSTEM_PROMPT = """You are a helpful AI shopping assistant for an online store. 
Your job is to help customers find products, answer product questions, and provide 
friendly recommendations. Keep responses concise, warm, and helpful.
Always respond in the same language the customer used."""


def build_prompt(
    query: str,
    intent: IntentResult,
    products: list[ProductSummary],
) -> str:
    """
    Build a complete LLM prompt.

    Structure:
        [System] → role definition
        [Context] → products if any
        [User] → original query
    """
    # ----------------------------------------------------------------
    # System role
    # ----------------------------------------------------------------
    prompt_parts = [f"System: {SYSTEM_PROMPT}\n"]

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

    elif products:
        # Build a compact product catalogue for the LLM
        product_lines = []
        for i, p in enumerate(products, 1):
            currency = p.currency or "INR"
            line = f"  {i}. {p.title} — ₹{p.price:,.0f} {currency}"
            if p.tags:
                line += f" | Tags: {', '.join(p.tags[:3])}"
            product_lines.append(line)

        product_block = "\n".join(product_lines)
        prompt_parts.append(
            f"Context: Here are matching products from the store:\n"
            f"{product_block}\n\n"
            f"Use these products to answer the customer's question. "
            f"Mention specific products with their prices. "
            f"If none match perfectly, suggest browsing related items.\n"
        )

    else:
        # Product intent but no results found
        prompt_parts.append(
            "Context: No specific products were found matching the query. "
            "Apologise briefly and ask the customer to refine their search "
            "(different keywords, adjust price range, etc.).\n"
        )

    # ----------------------------------------------------------------
    # Price constraint hint
    # ----------------------------------------------------------------
    if intent.price_limit is not None:
        prompt_parts.append(
            f"Note: Customer's budget is ₹{intent.price_limit:,.0f}. "
            f"Only recommend products within this price range.\n"
        )

    # ----------------------------------------------------------------
    # User message
    # ----------------------------------------------------------------
    prompt_parts.append(f"Customer: {query}\nAssistant:")

    return "\n".join(prompt_parts)
