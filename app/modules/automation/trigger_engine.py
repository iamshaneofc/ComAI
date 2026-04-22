from collections import Counter
from app.models.event import Event

class TriggerEngine:
    @staticmethod
    def detect_repeated_interest(events: list[Event]) -> dict | None:
        """
        Groups last 10 search events.
        If same category appears >= 3 times, return trigger "repeated_interest".
        """
        search_events = [e for e in events if e.event_type == "search"][:10]
        
        all_categories = []
        for e in search_events:
            cats = e.payload.get("categories", [])
            if isinstance(cats, list):
                all_categories.extend(cats)
            elif isinstance(cats, str):
                all_categories.append(cats)
            
        counter = Counter(all_categories)
        for cat, count in counter.most_common():
            if count >= 3:
                return {
                    "trigger_type": "repeated_interest",
                    "metadata": {
                        "category": cat,
                        "occurrences": count
                    }
                }
        return None

    @staticmethod
    def detect_high_intent(events: list[Event]) -> dict | None:
        """
        Multiple product_view events for same product -> trigger "high_intent".
        """
        view_events = [e for e in events if e.event_type == "product_view"]
        
        all_product_ids = []
        for e in view_events:
            pid = e.payload.get("product_id")
            if pid:
                all_product_ids.append(pid)
                
        counter = Counter(all_product_ids)
        for pid, count in counter.most_common():
            if count >= 3:
                return {
                    "trigger_type": "high_intent",
                    "metadata": {
                        "product_id": pid,
                        "occurrences": count
                    }
                }
        return None
