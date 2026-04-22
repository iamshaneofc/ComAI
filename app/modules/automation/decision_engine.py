from __future__ import annotations

import structlog
from typing import Any

logger = structlog.get_logger(__name__)


class DecisionEngine:
    @staticmethod
    def decide_action(
        trigger: dict,
        user_preferences: dict,
        products: list[Any],
    ) -> dict:
        """
        Deterministic decision tree with an explicit trace for observability.

        Returns action payload including ``decision_trace`` (ordered decision path).
        """
        trace: list[str] = ["enter_decision_engine"]
        trigger_type = trigger.get("trigger_type")
        meta = trigger.get("metadata") or {}
        intent = meta.get("intent_score")

        logger.info(
            "automation_decision_path",
            step="decision_start",
            trigger_type=trigger_type,
            intent_score=intent,
            path=list(trace),
        )

        if trigger_type == "repeated_interest":
            trace.append("branch_repeated_interest")
            category = meta.get("category")
            trace.append(f"category={category}")

            matching_products = [
                str(p.id)
                for p in products
                if (p.categories and category in p.categories) or (p.tags and category in p.tags)
            ]
            trace.append(f"strict_match_count={len(matching_products)}")

            if not matching_products and products:
                trace.append("fallback_top_catalog_slice")
                matching_products = [str(p.id) for p in products[:3]]

            if matching_products:
                trace.append("action_recommend_products_whatsapp")
                out = {
                    "action": "recommend_products",
                    "products": matching_products[:3],
                    "channel": "whatsapp",
                    "decision_trace": trace,
                }
                logger.info(
                    "automation_decision_path",
                    step="decision_final",
                    action=out["action"],
                    channel=out["channel"],
                    product_count=len(out["products"]),
                    path=list(trace),
                )
                return out

            trace.append("no_products_for_category")
            out = DecisionEngine._no_action(trace, "repeated_interest_empty_products")
            logger.info(
                "automation_decision_path",
                step="decision_final",
                action=out["action"],
                path=list(trace),
            )
            return out

        if trigger_type == "high_intent":
            trace.append("branch_high_intent")
            product_id = meta.get("product_id")
            trace.append(f"product_id={product_id}")
            trace.append("action_recommend_products_web")
            out = {
                "action": "recommend_products",
                "products": [str(product_id)],
                "channel": "web",
                "decision_trace": trace,
            }
            logger.info(
                "automation_decision_path",
                step="decision_final",
                action=out["action"],
                channel=out["channel"],
                path=list(trace),
            )
            return out

        trace.append("branch_unknown_trigger")
        out = DecisionEngine._no_action(trace, "unknown_trigger_type")
        logger.info(
            "automation_decision_path",
            step="decision_final",
            action=out["action"],
            path=list(trace),
        )
        return out

    @staticmethod
    def _no_action(trace: list[str], reason: str) -> dict:
        trace.append(f"no_action:{reason}")
        return {
            "action": "no_action",
            "products": [],
            "channel": "web",
            "decision_trace": trace,
        }
