import structlog
from uuid import UUID

from app.channels.whatsapp.service import WhatsAppService
from app.modules.automation.dedup import release_trigger_slot, try_acquire_trigger_slot
from app.modules.automation.decision_engine import DecisionEngine
from app.modules.automation.trigger_engine import TriggerEngine
from app.modules.products.service import ProductService
from app.schemas.product import ProductSearchFilters
from app.services.memory_service import MemoryService
from app.services.user_service import UserService

logger = structlog.get_logger(__name__)


class AutomationService:
    def __init__(self, db):
        self.db = db
        self.memory_service = MemoryService(db)
        self.product_service = ProductService(db)
        self.user_service = UserService(db)
        self.trigger_engine = TriggerEngine()
        self.decision_engine = DecisionEngine()
        self.whatsapp_service = WhatsAppService()

    async def evaluate_user(self, store_id: UUID, user_id: UUID):
        """
        Main pipeline: Event -> ranked triggers -> dedupe -> Decision -> Action.

        Intended for Celery / isolated session (not request-scoped DB).
        """
        path: list[str] = ["start_evaluate_user"]

        def trace(step: str, **fields) -> None:
            nonlocal path
            path = [*path, step]
            logger.info("automation_decision_path", step=step, path=list(path), **fields)

        try:
            structlog.contextvars.bind_contextvars(
                flow="automation", store_id=str(store_id), user_id=str(user_id)
            )

            trace("context_bound", store_id=str(store_id), user_id=str(user_id))

            if await self.user_service.repo.get_by_id_for_store(store_id, user_id) is None:
                trace("exit_user_not_in_tenant")
                logger.warning("Automation skipped: user not in tenant", store_id=str(store_id))
                return

            trace("user_validated")

            events = await self.memory_service.repo.get_recent_events(store_id, user_id, limit=20)
            if not events:
                trace("exit_no_events")
                return

            trace("events_loaded", event_count=len(events))

            ranked = self.trigger_engine.collect_ranked_triggers(events)
            if not ranked:
                trace("exit_no_triggers")
                logger.debug("No triggers fired")
                return

            trace(
                "triggers_ranked",
                candidate_count=len(ranked),
                ordering=[t["trigger_type"] for t in ranked],
                top_scores=[t.get("metadata", {}).get("intent_score") for t in ranked[:3]],
            )

            for idx, trigger in enumerate(ranked):
                trigger_for_decision = {
                    "trigger_type": trigger["trigger_type"],
                    "metadata": dict(trigger["metadata"]),
                }
                meta = trigger_for_decision["metadata"]
                trace(
                    "consider_trigger",
                    rank_index=idx,
                    trigger_type=trigger_for_decision["trigger_type"],
                    intent_score=meta.get("intent_score"),
                    frequency_component=meta.get("frequency_component"),
                    recency_component=meta.get("recency_component"),
                )

                acquired, dedupe_fp = await try_acquire_trigger_slot(store_id, user_id, trigger_for_decision)
                if not acquired:
                    trace(
                        "dedupe_skip_repeat_trigger",
                        rank_index=idx,
                        fingerprint=dedupe_fp,
                        trigger_type=trigger_for_decision["trigger_type"],
                    )
                    continue

                trace("dedupe_acquired", rank_index=idx, fingerprint=dedupe_fp)

                products = []
                try:
                    if trigger_for_decision["trigger_type"] == "repeated_interest":
                        category = trigger_for_decision["metadata"]["category"]
                        filters = ProductSearchFilters(category=category, limit=10)
                        products_resp, _ = await self.product_service.repo.search_products(
                            store_id, filters
                        )
                        products = products_resp
                        trace(
                            "products_resolved",
                            rank_index=idx,
                            trigger_type="repeated_interest",
                            product_count=len(products),
                        )

                    elif trigger_for_decision["trigger_type"] == "high_intent":
                        product_id = trigger_for_decision["metadata"]["product_id"]
                        try:
                            product_uuid = UUID(str(product_id))
                            p = await self.product_service.repo.get_by_id(product_uuid, store_id)
                            if p:
                                products = [p]
                        except ValueError:
                            products = []
                        trace(
                            "products_resolved",
                            rank_index=idx,
                            trigger_type="high_intent",
                            product_count=len(products),
                        )

                    user_prefs = await self.memory_service.get_user_preferences(store_id, user_id)
                    trace("preferences_loaded", rank_index=idx)

                    decision = self.decision_engine.decide_action(
                        trigger_for_decision, user_prefs, products
                    )

                    trace(
                        "decision_emitted",
                        rank_index=idx,
                        action=decision["action"],
                        engine_trace=decision.get("decision_trace", []),
                    )

                    if decision["action"] == "no_action":
                        trace("release_dedupe_no_action", rank_index=idx)
                        await release_trigger_slot(store_id, user_id, dedupe_fp)
                        continue

                    outbound_ok = await self.execute_action(
                        store_id, decision, user_id, path=list(path)
                    )
                    if not outbound_ok:
                        trace(
                            "release_dedupe_no_outbound_effect",
                            rank_index=idx,
                            reason="execute_action_no_side_effect",
                        )
                        await release_trigger_slot(store_id, user_id, dedupe_fp)
                        continue

                    trace("exit_after_successful_action", rank_index=idx)
                    return

                except Exception:
                    trace("release_dedupe_on_error", rank_index=idx)
                    await release_trigger_slot(store_id, user_id, dedupe_fp)
                    raise

            trace("exit_all_candidates_exhausted")

        except Exception as e:
            logger.exception("Automation evaluation failed", error=str(e), path=list(path))

    async def execute_action(
        self, store_id: UUID, action: dict, user_id: UUID, path: list | None = None
    ) -> bool:
        """
        Runs the chosen automation. Returns True if a durable outbound side effect was queued.

        WhatsApp path returns False when the message was not enqueued (missing user/phone/products).
        """
        pipeline_path = list(path or [])
        pipeline_path.append("execute_action")
        logger.info(
            "Automation Action Executed",
            user_id=str(user_id),
            action_type=action["action"],
            products=action["products"],
            store_id=str(store_id),
            decision_trace=action.get("decision_trace", []),
            automation_path=pipeline_path,
        )

        if action["action"] == "recommend_products":
            if action.get("channel") == "whatsapp":
                user = await self.user_service.repo.get_by_id_for_store(store_id, user_id)
                if not user:
                    logger.warning("Automation: user not found for store", user_id=str(user_id))
                    return False

                product_ids = [UUID(pid) for pid in action["products"]]
                full_products = []
                for pid in product_ids:
                    p = await self.product_service.repo.get_by_id(pid, store_id)
                    if p:
                        full_products.append(p)

                phone = getattr(user, "phone", None)
                if phone and full_products:
                    message = self.whatsapp_service.generate_recommendation_message(full_products)
                    from app.tasks.message_tasks import send_whatsapp_message
                    from app.tasks.task_idempotency import stable_idempotency_key

                    send_idem = stable_idempotency_key(
                        str(store_id),
                        str(user_id),
                        ",".join(str(p.id) for p in full_products),
                    )
                    send_whatsapp_message.delay(phone, message, idempotency_key=send_idem)
                    return True

                logger.warning(
                    "Cannot send WhatsApp: missing phone or products",
                    user_id=str(user_id),
                    has_phone=bool(phone),
                    product_count=len(full_products),
                )
                return False

            # Non-WhatsApp channels: treat as completed for dedupe (no worker integration yet).
            return True

        return False
