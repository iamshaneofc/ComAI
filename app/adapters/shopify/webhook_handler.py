import hmac
import hashlib
import logging
import base64

from app.adapters.shopify.normalizer import normalize_product
from app.schemas.product import ProductCreate

logger = logging.getLogger(__name__)

def verify_and_normalize_webhook(raw_body: bytes, hmac_header: str, webhook_secret: str, payload: dict) -> ProductCreate:
    """Verifies the HMAC signature and extracts the normalized product data."""
    if not webhook_secret:
        logger.error("No webhook secret configured")
        raise ValueError("No webhook secret configured")
        
    if not hmac_header:
        logger.error("Missing HMAC header")
        raise ValueError("Missing HMAC header")
        
    computed_hmac = hmac.new(
        webhook_secret.encode('utf-8'),
        raw_body,
        hashlib.sha256
    ).digest()
    
    computed_hmac_b64 = base64.b64encode(computed_hmac).decode('utf-8')
    
    if not hmac.compare_digest(computed_hmac_b64, hmac_header):
        logger.error("Invalid HMAC signature")
        raise ValueError("Invalid signature")
        
    # Return business-domain data model inward
    return normalize_product(payload)
