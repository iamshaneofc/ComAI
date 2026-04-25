"""
ChatService — Phase 1 MVP (Product search + AI response).

Flow:
    query → intent detection → product retrieval → AgentService → prompt build → LLM → response

What's NOT here yet (Phase 2):
    - Memory / conversation history
    - Events emission
    - Channel formatters (web/whatsapp/voice)
    - Session persistence

Rules:
    - ALL chat business logic lives here
    - Calls AI layer functions (no direct LLM API)
    - Calls ProductService for products (no direct DB)
    - Returns clean ChatResponse
"""
import structlog
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.intent.detector import (
    INTENT_GENERAL,
    INTENT_GREETING,
    INTENT_ORDER_STATUS,
    INTENT_PRICE_FILTER,
    INTENT_PRODUCT_SEARCH,
    INTENT_SUPPORT,
    detect_intent,
)
from app.ai.prompt.builder import build_prompt, format_memory_context_for_prompt
from app.ai.providers.factory import get_llm_provider
from app.ai.retrieval.retrieval import RetrievalEngine
from app.core.database import get_db
from app.modules.products.service import ProductService
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.agent_service import AgentService, AgentType
from app.services.memory_service import MemoryService
from app.services.order_service import OrderService
from app.services.store_context_service import StoreContextService
from app.services.user_service import UserService

logger = structlog.get_logger(__name__)

# Canned responses that avoid LLM calls for simple intents (cost optimisation)
GREETING_RESPONSE = (
    "Hello! Welcome to our store 👋 "
    "I'm your AI shopping assistant. "
    "Tell me what you're looking for — product type, budget, or anything else — "
    "and I'll find the best matches for you!"
)

SUPPORT_RESPONSE = (
    "I understand you need some help. "
    "For order tracking, returns, or refunds, "
    "please contact our support team or check your email for order details. "
    "Is there anything else I can help you with?"
)

FALLBACK_RESPONSE = (
    "I'm here to help you find great products! "
    "Try asking something like: "
    "'Show me shoes under ₹2000' or 'I need a red bag'. "
    "What are you looking for today?"
)


class ChatService:

    def __init__(self, db: AsyncSession = Depends(get_db)) -> None:
        self.db = db
        self.product_service = ProductService(db)
        self.store_context_service = StoreContextService(db)
        self.retrieval = RetrievalEngine(self.product_service, self.store_context_service)
        self._agent_service = AgentService(db)
        self.user_service = UserService(db)
        self.memory_service = MemoryService(db)
        self.order_service = OrderService(db)

    async def handle_chat(
        self,
        store_id,
        payload: ChatRequest,
        agent_type: AgentType = "chat",
    ) -> ChatResponse:
        """
        End-to-end chat handler.

        Step 1: Detect intent (keywords, price, categories)
        Step 2: Retrieve products (if product intent)
        Step 3: Build prompt (with product context)
        Step 4: Call LLM (or use canned response for greeting/support)
        Step 5: Return ChatResponse
        """
        log = logger.bind(store_id=str(store_id), query=payload.message[:50])

        structlog.contextvars.bind_contextvars(flow="chat")
        # ── Step 0: Resolve User & Memory ──────────────────────────────
        user = None
        user_preferences = None
        if payload.session_id:
            user = await self.user_service.get_or_create_user(store_id, payload.session_id)
            structlog.contextvars.bind_contextvars(user_id=str(user.id))
            user_preferences = await self.memory_service.get_user_preferences(store_id, user.id)
            log.info("Loaded user preferences", pref_categories=user_preferences.get("top_categories"))

        # ── Step 1: Detect intent ──────────────────────────────────
        intent = detect_intent(payload.message)
        log.info("Intent detected", intent=intent.intent, price_limit=intent.price_limit)

        # ── Step 2: Retrieve products ──────────────────────────────
        products = []
        if intent.intent in (INTENT_PRODUCT_SEARCH, INTENT_PRICE_FILTER):
            # Retrieval returns up to 3 DB-backed products for product_search (see RetrievalEngine).
            products = await self.retrieval.get_products_for_query(
                query=payload.message,
                intent=intent,
                store_id=store_id,
                user_preferences=user_preferences,
            )
            # Track event
            if user:
                event_payload = {
                    "keywords": intent.keywords,
                    "categories": intent.categories,
                    "price_limit": intent.price_limit
                }
                await self.memory_service.track_event(store_id, user.id, "search", event_payload)

                from app.tasks.automation_tasks import evaluate_user_automation

                try:
                    evaluate_user_automation.apply_async(
                        args=(str(store_id), str(user.id)),
                        retry=False,
                    )
                except Exception as exc:
                    log.error("Failed to enqueue automation task", error=str(exc))

        # ── Step 3 + 4: Build prompt + call LLM (or canned) ───────
        if intent.intent == INTENT_GREETING:
            reply = GREETING_RESPONSE

        elif intent.intent == INTENT_SUPPORT:
            reply = SUPPORT_RESPONSE

        elif intent.intent == INTENT_ORDER_STATUS:
            if user is None:
                reply = (
                    "I can check your order status after we identify your account. "
                    "Please continue from your signed-in session or share the phone/email linked to your order."
                )
            else:
                order = await self.order_service.find_latest_order_for_user(store_id, user)
                if order is None:
                    reply = (
                        "I could not find a recent order linked to your profile yet. "
                        "Please verify the same phone/email used at checkout."
                    )
                else:
                    reply = (
                        f"Your latest order ({order['order_number']}) is currently "
                        f"**{order['status']}** with fulfillment status **{order['fulfillment_status']}**."
                    )

        elif intent.intent == INTENT_GENERAL and not products:
            reply = FALLBACK_RESPONSE

        else:
            resolved = await self._agent_service.resolve_agent(store_id, agent_type)
            log.info(
                "LLM request",
                agent_id=str(resolved.agent_id) if resolved.agent_id else None,
                agent_type=agent_type,
                model=resolved.model,
            )
            memory_context = format_memory_context_for_prompt(user_preferences)
            store_context_chunks = await self.retrieval.get_store_context_for_query(store_id)
            prompt = build_prompt(
                query=payload.message,
                intent=intent,
                products=products,
                system_prompt=resolved.system_prompt,
                memory_context=memory_context,
                store_context_chunks=store_context_chunks,
            )
            llm = get_llm_provider(
                provider=resolved.provider,
                api_key=resolved.api_key,
                model=resolved.model,
            )
            llm_result = await llm.generate(
                prompt,
                temperature=resolved.temperature,
                system_prompt=resolved.system_prompt,
            )
            reply = llm_result.text

        log.info("Chat response built", intent=intent.intent, products_count=len(products))

        # ── Step 5: Return structured response ────────────────────
        return ChatResponse(
            message=reply,
            intent=intent.intent,
            products=[p.model_dump() for p in products],
        )
