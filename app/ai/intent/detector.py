"""
Intent Detector — simple rule-based intent classification for Phase 1.

Phase 1 design: keyword matching (fast, zero cost, no API calls needed).
Phase 2 will add ML-based classification when needed.

Returns:
    intent: str  — one of the defined intents
    keywords: list[str]  — extracted searchable terms
    price_limit: float | None  — extracted price constraint if any
    categories: list[str]  — detected product categories
"""
import re
from dataclasses import dataclass, field


# ----------------------------------------------------------------
# Intent labels
# ----------------------------------------------------------------
INTENT_PRODUCT_SEARCH = "product_search"
INTENT_PRICE_FILTER   = "price_filter"
INTENT_GENERAL        = "general"
INTENT_GREETING       = "greeting"
INTENT_SUPPORT        = "support"
INTENT_ORDER_STATUS   = "order_status"


# ----------------------------------------------------------------
# Keyword maps for category detection
# ----------------------------------------------------------------
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "shoes":       ["shoe", "shoes", "footwear", "sneaker", "sandal", "boot", "heels"],
    "clothing":    ["shirt", "tshirt", "t-shirt", "jeans", "dress", "kurta", "top", "jacket"],
    "electronics": ["phone", "laptop", "tablet", "earphone", "headphone", "charger", "watch"],
    "bags":        ["bag", "handbag", "backpack", "purse", "wallet"],
    "beauty":      ["cream", "serum", "lipstick", "perfume", "makeup"],
}

GREETING_KEYWORDS = {"hi", "hello", "hey", "namaste", "good morning", "good afternoon"}
SUPPORT_KEYWORDS  = {"help", "support", "track", "order", "return", "refund", "cancel"}
ORDER_STATUS_PATTERNS = (
    r"\bwhere\s+is\s+my\s+order\b",
    r"\btrack\s+my\s+order\b",
    r"\border\s+status\b",
    r"\bmy\s+order\b",
)


@dataclass
class IntentResult:
    intent: str
    keywords: list[str] = field(default_factory=list)
    price_limit: float | None = None
    categories: list[str] = field(default_factory=list)
    confidence: float = 1.0


def detect_intent(query: str) -> IntentResult:
    """
    Analyse a user query and return structured intent.

    Examples:
        "shoes under 3000"  → product_search, keywords=["shoes"], price_limit=3000.0
        "hi there"          → greeting
        "track my order"    → support
        "I need a red bag"  → product_search, keywords=["red", "bag"]
    """
    q = query.lower().strip()
    tokens = set(re.findall(r"\b\w+\b", q))

    # --- Greeting ---
    if tokens & GREETING_KEYWORDS:
        return IntentResult(intent=INTENT_GREETING, confidence=0.95)

    # --- Support ---
    if any(re.search(p, q) for p in ORDER_STATUS_PATTERNS):
        return IntentResult(intent=INTENT_ORDER_STATUS, confidence=0.95)

    # --- Support ---
    if tokens & SUPPORT_KEYWORDS:
        return IntentResult(intent=INTENT_SUPPORT, confidence=0.9)

    # --- Price extraction ---
    # Handles: "under 3000", "below 500", "less than 1000", "upto 2000", "max 5000"
    price_patterns = [
        r"(?:under|below|less\s+than|upto|up\s+to|max(?:imum)?)\s+(?:rs\.?|inr|₹)?\s*(\d[\d,]*)",
        r"(?:rs\.?|inr|₹)\s*(\d[\d,]*)\s+(?:or\s+less|max)",
        r"budget\s+(?:of\s+)?(?:rs\.?|inr|₹)?\s*(\d[\d,]*)",
    ]
    price_limit: float | None = None
    for pattern in price_patterns:
        match = re.search(pattern, q)
        if match:
            price_limit = float(match.group(1).replace(",", ""))
            break

    # --- Category detection ---
    detected_categories: list[str] = []
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            detected_categories.append(category)

    # --- Keyword extraction ---
    # Remove stop words and price-related tokens, keep meaningful terms
    stop_words = {
        "i", "me", "my", "the", "a", "an", "are", "is", "in", "on", "for",
        "of", "to", "and", "or", "but", "looking", "want", "need", "find",
        "show", "get", "give", "can", "you", "please", "some", "any",
        "under", "below", "above", "less", "than", "upto", "up", "max",
        "budget", "rs", "inr", "rupees",
    }
    keywords = [t for t in tokens if t not in stop_words and len(t) > 2 and not t.isdigit()]

    # --- Determine intent ---
    if price_limit is not None or detected_categories or keywords:
        intent = INTENT_PRODUCT_SEARCH
    else:
        intent = INTENT_GENERAL

    return IntentResult(
        intent=intent,
        keywords=keywords,
        price_limit=price_limit,
        categories=detected_categories,
        confidence=0.85,
    )
