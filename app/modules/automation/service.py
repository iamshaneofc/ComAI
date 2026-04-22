import structlog
from uuid import UUID

from app.modules.products.service import ProductService
from app.modules.automation.trigger_engine import TriggerEngine
from app.modules.automation.decision_engine import DecisionEngine
from app.services.memory_service import MemoryService
from app.services.user_service import UserService
from app.schemas.product import ProductSearchFilters
from app.channels.whatsapp.service import WhatsAppService

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
        Main pipeline: Event -> Trigger -> Decision -> Action
        Run asynchronously so as not to block incoming API calls.
        """
        try:
            structlog.contextvars.bind_contextvars(flow="automation", store_id=str(store_id), user_id=str(user_id))
            
            # 1. Fetch events
            events = await self.memory_service.repo.get_recent_events(store_id, user_id, limit=20)
            if not events:
                return

            # 2. Trigger Generation
            trigger = self.trigger_engine.detect_repeated_interest(events)
            if not trigger:
                trigger = self.trigger_engine.detect_high_intent(events)
                
            if not trigger:
                logger.debug("No triggers fired")
                return

            # 3. Action Candidate Pool Generation
            products = []
            if trigger["trigger_type"] == "repeated_interest":
                category = trigger["metadata"]["category"]
                filters = ProductSearchFilters(category=category, limit=10)
                # Repo method returns (products, total_count)
                products_resp, _ = await self.product_service.repo.search_products(store_id, filters)
                products = products_resp
                
            elif trigger["trigger_type"] == "high_intent":
                product_id = trigger["metadata"]["product_id"]
                try:
                    product_uuid = UUID(product_id)
                    p = await self.product_service.repo.get(product_uuid)
                    if p:
                        products = [p]
                except ValueError:
                    pass

            # 4. Decision Processing
            user_prefs = await self.memory_service.get_user_preferences(store_id, user_id)
            decision = self.decision_engine.decide_action(trigger, user_prefs, products)
            
            # 5. Execution Execution Engine
            if decision["action"] != "no_action":
                await self.execute_action(decision, user_id)
                
        except Exception as e:
            logger.exception("Automation evaluation failed", error=str(e))
            
    async def execute_action(self, action: dict, user_id: UUID):
        """Executes and logs the system action definitively."""
        logger.info(
            "Automation Action Executed", 
            user_id=str(user_id), 
            action_type=action["action"], 
            products=action["products"]
        )
        
        if action["action"] == "recommend_products":
            if action.get("channel") == "whatsapp":
                user = await self.user_service.get_or_create_user(self.db, user_id) # Using repo internally or lookup by ID
                
                # Fetch full products
                product_ids = [UUID(pid) for pid in action["products"]]
                full_products = []
                for pid in product_ids:
                    p = await self.product_service.repo.get(pid)
                    if p:
                        full_products.append(p)
                        
                await self.whatsapp_service.send_product_recommendation(user, full_products)
