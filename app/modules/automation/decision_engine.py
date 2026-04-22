class DecisionEngine:
    @staticmethod
    def decide_action(trigger: dict, user_preferences: dict, products: list) -> dict:
        """
        Deterministic decision tree processing active triggers.
        Returns explicit action payload format.
        """
        if trigger["trigger_type"] == "repeated_interest":
            category = trigger["metadata"]["category"]
            
            # Simple match of top products by category logic
            # Engine assumes `products` contains category-matched products
            matching_products = [
                str(p.id) for p in products 
                if (p.categories and category in p.categories) or (p.tags and category in p.tags)
            ]
            
            # Fallback if categories are loosely defined
            if not matching_products and products:
                matching_products = [str(p.id) for p in products[:3]]
                
            return {
                "action": "recommend_products",
                "products": matching_products[:3],
                "channel": "whatsapp"
            }
            
        elif trigger["trigger_type"] == "high_intent":
            product_id = trigger["metadata"]["product_id"]
            
            return {
                "action": "recommend_products",
                "products": [str(product_id)],
                "channel": "web"
            }
            
        return {
            "action": "no_action",
            "products": [],
            "channel": "web"
        }
