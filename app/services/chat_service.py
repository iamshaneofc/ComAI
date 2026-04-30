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
from app.ai.prompt.builder import (
    build_prompt,
    format_conversation_context_for_prompt,
    format_memory_context_for_prompt,
)
from app.ai.providers.factory import get_llm_provider
from app.ai.retrieval.retrieval import RetrievalEngine
from app.core.database import get_db
from app.modules.products.service import ProductService
from app.repositories.chat_message_repo import ChatMessageRepository
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
LLM_FAILURE_RESPONSE = (
    "I'm having trouble responding right now. "
    "Meanwhile, here are some products you can browse while I recover."
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
        self.chat_messages = ChatMessageRepository(db)

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
        recent_turns: list[dict] = []
        session_id = (payload.session_id or "").strip()
        if session_id:
            user = await self.user_service.get_or_create_user(store_id, session_id)
            structlog.contextvars.bind_contextvars(user_id=str(user.id))
            user_preferences = await self.memory_service.get_user_preferences(store_id, user.id)
            recent_rows = await self.chat_messages.get_recent_messages(
                store_id=store_id,
                session_id=session_id,
                limit=10,
            )
            recent_turns = []
            current_user = None
            for row in reversed(recent_rows):
                role = (row.role or "").strip().lower()
                text = (row.content or "").strip()
                if not text:
                    continue
                if role == "user":
                    if current_user:
                        recent_turns.append({"user_message": current_user, "bot_response": ""})
                    current_user = text
                elif role == "assistant":
                    if current_user is None:
                        recent_turns.append({"user_message": "", "bot_response": text})
                    else:
                        recent_turns.append({"user_message": current_user, "bot_response": text})
                        current_user = None
            if current_user:
                recent_turns.append({"user_message": current_user, "bot_response": ""})
            log.info("Loaded user preferences", pref_categories=user_preferences.get("top_categories"))

        if session_id:
            try:
                await self.chat_messages.add_message(
                    store_id=store_id,
                    session_id=session_id,
                    role="user",
                    content=payload.message[:4000],
                )
            except Exception as exc:
                log.error("Failed to persist user chat message", error=str(exc))

        # ── Step 1: Detect intent ──────────────────────────────────
        intent = detect_intent(payload.message)
        log.info("Intent detected", intent=intent.intent, price_limit=intent.price_limit)

        # ── Step 2: Retrieve products ──────────────────────────────
        products = []
        used_memory = bool(user_preferences)
        used_store_context = False
        llm_failed = False
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

            if not products:
                products = await self.product_service.get_products_for_chat(
                    store_id=store_id,
                    keyword=None,
                    max_price=None,
                    categories=intent.categories if intent.categories else None,
                    limit=5,
                )

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
            conversation_context = format_conversation_context_for_prompt(
                recent_turns,
                max_messages=8,
                max_chars=1800,
            )
            store_context_chunks = await self.retrieval.get_store_context_for_query(store_id)
            used_store_context = bool(store_context_chunks)
            prompt = build_prompt(
                query=payload.message,
                intent=intent,
                products=products,
                system_prompt=resolved.system_prompt,
                memory_context=memory_context,
                conversation_context=conversation_context,
                store_context_chunks=store_context_chunks,
            )
            llm = get_llm_provider(
                provider=resolved.provider,
                api_key=resolved.api_key,
                model=resolved.model,
            )
            try:
                llm_result = await llm.generate(
                    prompt,
                    temperature=resolved.temperature,
                    system_prompt=resolved.system_prompt,
                )
                reply = llm_result.text
            except Exception as exc:
                llm_failed = True
                log.exception("LLM generation failed", error=str(exc))
                if not products:
                    products = await self.product_service.get_products_for_chat(
                        store_id=store_id,
                        keyword=None,
                        max_price=None,
                        categories=intent.categories if intent.categories else None,
                        limit=5,
                    )
                if products:
                    reply = LLM_FAILURE_RESPONSE
                else:
                    reply = (
                        "I'm having trouble right now. Please try again in a moment, "
                        "or tell me your product type and budget so I can retry."
                    )

        log.info("Chat response built", intent=intent.intent, products_count=len(products))

        if session_id:
            try:
                await self.chat_messages.add_message(
                    store_id=store_id,
                    session_id=session_id,
                    role="assistant",
                    content=reply[:4000],
                )
            except Exception as exc:
                log.error("Failed to persist assistant chat message", error=str(exc))

        if user:
            try:
                await self.memory_service.track_chat_turn(
                    store_id=store_id,
                    user_id=user.id,
                    user_message=payload.message,
                    bot_response=reply,
                )
            except Exception as exc:
                log.error("Failed to persist chat turn", error=str(exc))

        # ── Step 5: Return structured response ────────────────────
        return ChatResponse(
            message=reply,
            intent=intent.intent,
            products=[p.model_dump() for p in products],
            metadata={
                "used_memory": used_memory,
                "used_context": used_store_context,
                "used_conversation": bool(recent_turns),
                "llm_failed": llm_failed,
            },
        )
