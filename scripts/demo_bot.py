import urllib.request
import urllib.error
import json
import re
import os

# ----------------------------------------------------------------
# EXACT REPLICA OF THE INTENT DETECTION LOGIC
# ----------------------------------------------------------------
INTENT_PRODUCT_SEARCH = "product_search"
INTENT_GENERAL        = "general"
INTENT_GREETING       = "greeting"
INTENT_SUPPORT        = "support"

CATEGORY_KEYWORDS = {
    "shoes":       ["shoe", "shoes", "footwear", "sneaker", "sandal", "boot", "heels"],
    "clothing":    ["shirt", "tshirt", "t-shirt", "jeans", "dress", "kurta", "top", "jacket"],
}
GREETING_KEYWORDS = {"hi", "hello", "hey", "namaste", "good morning", "good afternoon"}
SUPPORT_KEYWORDS  = {"help", "support", "track", "order", "return", "refund", "cancel"}

class IntentResult:
    def __init__(self, intent, keywords, price_limit, categories):
        self.intent = intent
        self.keywords = keywords
        self.price_limit = price_limit
        self.categories = categories

def detect_intent(query: str):
    q = query.lower().strip()
    tokens = set(re.findall(r"\b\w+\b", q))

    if tokens & GREETING_KEYWORDS:
        return IntentResult(INTENT_GREETING, [], None, [])
    if tokens & SUPPORT_KEYWORDS:
        return IntentResult(INTENT_SUPPORT, [], None, [])

    price_patterns = [
        r"(?:under|below|less\s+than|upto|up\s+to|max)\s*(?:rs\.?|inr|₹)?\s*(\d[\d,]*)",
        r"(?:rs\.?|inr|₹)\s*(\d[\d,]*)\s*(?:or\s+less|max)",
        r"budget\s+(?:of\s+)?(?:rs\.?|inr|₹)?\s*(\d[\d,]*)",
    ]
    price_limit = None
    for pattern in price_patterns:
        match = re.search(pattern, q)
        if match:
            price_limit = float(match.group(1).replace(",", ""))
            break

    cats = [c for c, kws in CATEGORY_KEYWORDS.items() if any(kw in q for kw in kws)]
    
    stop_words = {"i", "me", "my", "the", "a", "an", "looking", "want", "need", "show", "under", "rs", "inr"}
    keywords = [t for t in tokens if t not in stop_words and len(t) > 2 and not t.isdigit()]

    intent = INTENT_PRODUCT_SEARCH if (price_limit is not None or cats or keywords) else INTENT_GENERAL
    return IntentResult(intent, keywords, price_limit, cats)

# ----------------------------------------------------------------
# EXACT REPLICA OF THE PROMPT BUILDER
# ----------------------------------------------------------------
SYSTEM_PROMPT = """You are a helpful AI shopping assistant for an online store. 
Your job is to help customers find products, answer product questions, and provide 
friendly recommendations. Keep responses concise, warm, and helpful.
Always respond in the same language the customer used."""

def build_prompt(query, intent, products):
    prompt_parts = [f"System: {SYSTEM_PROMPT}\n"]

    if intent.intent == INTENT_GREETING:
        prompt_parts.append("Context: The customer has just greeted you. Welcome them warmly and invite them to describe what they are looking for.\n")
    elif intent.intent == INTENT_SUPPORT:
        prompt_parts.append("Context: The customer needs support. Be empathetic, acknowledge their concern, and offer help.\n")
    elif products:
        lines = [f"  {i+1}. {p['title']} — ₹{p['price']} | Tags: {','.join(p.get('tags', []))}" for i, p in enumerate(products)]
        prompt_parts.append("Context: Here are matching products from the store:\n" + "\n".join(lines) + "\n\nUse these products to answer the customer's question.\n")
    else:
        prompt_parts.append("Context: No specific products were found matching the query. Apologise briefly and ask the customer to refine their search.\n")

    if intent.price_limit is not None:
        prompt_parts.append(f"Note: Customer's budget is ₹{intent.price_limit}. Only recommend products within this price range.\n")

    prompt_parts.append(f"Customer: {query}\nAssistant:")
    return "\n".join(prompt_parts)

# ----------------------------------------------------------------
# MOCK DATABASE (PRODUCTS)
# ----------------------------------------------------------------
DB_PRODUCTS = [
    {"id": "1", "title": "Nike Air Max", "price": 4500.0, "tags": ["shoes", "nike"]},
    {"id": "2", "title": "Puma Sport Sneakers", "price": 2500.0, "tags": ["shoes", "puma"]},
    {"id": "3", "title": "Adidas Running Shoes", "price": 2800.0, "tags": ["shoes", "adidas"]}
]

def retrieval_engine(intent):
    if intent.intent != INTENT_PRODUCT_SEARCH:
        return []
    res = DB_PRODUCTS
    if intent.price_limit:
        res = [p for p in res if p["price"] <= intent.price_limit]
    if "shoes" in intent.categories or "shoes" in intent.keywords:
        res = [p for p in res if "shoes" in p["tags"]]
    return res

# ----------------------------------------------------------------
# OPENAI API CALL (USING URLLIB TO AVOID PIP DEPENDENCIES)
# ----------------------------------------------------------------
def call_llm(prompt, api_key):
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps({
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 150,
            "temperature": 0.7
        }).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    )
    try:
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode("utf-8")
            return json.loads(res_body)["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        return f"API ERROR: {e.read().decode()}"

# ----------------------------------------------------------------
# READ .ENV
# ----------------------------------------------------------------
api_key = None
with open(".env", "r", encoding="utf-8") as f:
    for line in f:
        if line.startswith("OPENAI_API_KEY="):
            api_key = line.split("=", 1)[1].strip()

# ----------------------------------------------------------------
# RUN USE CASES
# ----------------------------------------------------------------
use_cases = [
    "Hi there!",
    "Where is my order?",
    "Show me shoes under 3000 rs",
    "I want shoes below 1000 inr"
]

results = []
for q in use_cases:
    intent = detect_intent(q)
    products = retrieval_engine(intent)
    
    # Canned responses bypass LLM
    if intent.intent == INTENT_GREETING:
        reply = "Hello! Welcome to our store 👋 I'm your AI shopping assistant. Tell me what you're looking for..."
    elif intent.intent == INTENT_SUPPORT:
        reply = "I understand you need some help. For order tracking, please check your email for order details."
    else:
        prompt = build_prompt(q, intent, products)
        reply = call_llm(prompt, api_key)
        
    results.append({
        "query": q,
        "intent_detected": intent.intent,
        "price_limit_detected": intent.price_limit,
        "products_retrieved": len(products),
        "ai_response": reply
    })

print(json.dumps(results, indent=2))
