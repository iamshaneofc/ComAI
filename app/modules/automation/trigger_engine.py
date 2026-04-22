from __future__ import annotations

import math
from collections import Counter
from datetime import UTC, datetime

from app.models.event import Event

# How strongly frequency vs recency drives ranking (must sum to 1 for interpretability).
WEIGHT_FREQUENCY = 0.55
WEIGHT_RECENCY = 0.45

# Normalize frequency: occurrences / cap (plateau).
FREQUENCY_CAP = 8.0

# Recency decay: exp(-RECENCY_DECAY_PER_HOUR * age_hours)
RECENCY_DECAY_PER_HOUR = 0.35


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _hours_since(when: datetime, now: datetime) -> float:
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return max(0.0, (now - when).total_seconds() / 3600.0)


def _frequency_component(count: int) -> float:
    return min(1.0, float(count) / FREQUENCY_CAP)


def _recency_component(latest_at: datetime | None, now: datetime) -> float:
    if latest_at is None:
        return 0.0
    age_h = _hours_since(latest_at, now)
    return math.exp(-RECENCY_DECAY_PER_HOUR * age_h)


def _intent_score(freq_component: float, rec_component: float) -> float:
    return WEIGHT_FREQUENCY * freq_component + WEIGHT_RECENCY * rec_component


class TriggerEngine:
    @staticmethod
    def detect_repeated_interest(events: list[Event]) -> dict | None:
        """Backward-compatible: first category meeting threshold."""
        ranked = TriggerEngine.collect_ranked_triggers(events)
        for t in ranked:
            if t["trigger_type"] == "repeated_interest":
                return {k: v for k, v in t.items() if k != "intent_score_breakdown"}
        return None

    @staticmethod
    def detect_high_intent(events: list[Event]) -> dict | None:
        """Backward-compatible: first product meeting threshold."""
        ranked = TriggerEngine.collect_ranked_triggers(events)
        for t in ranked:
            if t["trigger_type"] == "high_intent":
                return {k: v for k, v in t.items() if k != "intent_score_breakdown"}
        return None

    @staticmethod
    def collect_ranked_triggers(events: list[Event]) -> list[dict]:
        """
        Build all qualifying triggers, score user intent from frequency + recency, highest first.

        Each item includes trigger_type, metadata (category/product_id/occurrences), and scoring fields.
        """
        now = _utc_now()
        candidates: list[dict] = []

        search_events = [e for e in events if e.event_type == "search"][:10]
        category_latest: dict[str, datetime] = {}
        category_counts: Counter[str] = Counter()

        for e in search_events:
            cats = e.payload.get("categories", [])
            if isinstance(cats, str):
                cats = [cats]
            elif not isinstance(cats, list):
                cats = []
            ts = e.created_at
            for cat in cats:
                if not cat:
                    continue
                category_counts[cat] += 1
                prev = category_latest.get(cat)
                if prev is None or ts > prev:
                    category_latest[cat] = ts

        for cat, count in category_counts.most_common():
            if count < 3:
                continue
            f_comp = _frequency_component(count)
            r_comp = _recency_component(category_latest.get(cat), now)
            score = _intent_score(f_comp, r_comp)
            candidates.append(
                {
                    "trigger_type": "repeated_interest",
                    "metadata": {
                        "category": cat,
                        "occurrences": count,
                        "intent_score": round(score, 4),
                        "frequency_component": round(f_comp, 4),
                        "recency_component": round(r_comp, 4),
                    },
                    "intent_score_breakdown": {
                        "frequency_count": count,
                        "frequency_component": f_comp,
                        "recency_component": r_comp,
                        "intent_score": score,
                    },
                }
            )

        view_events = [e for e in events if e.event_type == "product_view"]
        product_latest: dict[str, datetime] = {}
        product_counts: Counter[str] = Counter()

        for e in view_events:
            pid = e.payload.get("product_id")
            if not pid:
                continue
            pid_s = str(pid)
            product_counts[pid_s] += 1
            ts = e.created_at
            prev = product_latest.get(pid_s)
            if prev is None or ts > prev:
                product_latest[pid_s] = ts

        for pid, count in product_counts.most_common():
            if count < 3:
                continue
            f_comp = _frequency_component(count)
            r_comp = _recency_component(product_latest.get(pid), now)
            score = _intent_score(f_comp, r_comp)
            candidates.append(
                {
                    "trigger_type": "high_intent",
                    "metadata": {
                        "product_id": pid,
                        "occurrences": count,
                        "intent_score": round(score, 4),
                        "frequency_component": round(f_comp, 4),
                        "recency_component": round(r_comp, 4),
                    },
                    "intent_score_breakdown": {
                        "frequency_count": count,
                        "frequency_component": f_comp,
                        "recency_component": r_comp,
                        "intent_score": score,
                    },
                }
            )

        candidates.sort(
            key=lambda c: c["metadata"].get("intent_score", 0.0),
            reverse=True,
        )
        return candidates
