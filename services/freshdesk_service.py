"""
Freshdesk Service (now using n8n webhook)
Handles ticket creation via n8n webhook for bulk order escalations
"""

import logging
import requests
from typing import Dict, Optional, Any
from config.settings import N8N_WEBHOOK_URL

logger = logging.getLogger(__name__)


class FreshdeskService:
    """Service for creating tickets via n8n webhook (legacy name kept for compatibility)"""
    
    def __init__(self):
        """Initialize service for n8n webhook"""
        # Use n8n webhook URL from environment or default
        self.api_url = N8N_WEBHOOK_URL
        
        # n8n webhook accepts requests without authentication
        self.headers = {
            "Content-Type": "application/json"
        }
    
    def create_ticket(
        self,
        email: str,
        subject: str,
        description: str,
        product_id: Optional[int] = None,
        group_id: Optional[int] = None,
        source: int = 10,  # Changed from 13 to 10 (Outbound Email) - valid values: 1,2,3,5,6,7,9,11,100,10
        tags: Optional[list] = None,
        status: int = 5,
        priority: int = 3,
        responder_id: int = 103141023779,
        # Individual data fields for database storage
        customer_name: Optional[str] = None,
        customer_email: Optional[str] = None,
        product_name: Optional[str] = None,
        quantity: Optional[int] = None,
        postcode: Optional[str] = None,
        region: Optional[str] = None,
        fabric: Optional[str] = None,
        cover: Optional[str] = None,
        type: Optional[str] = None,
        size: Optional[str] = None,
        pages: Optional[str] = None,
        discount_percent: Optional[float] = None,
        unit_price: Optional[str] = None,
        total_price: Optional[str] = None,
        offers_shown: Optional[str] = None,
        quote_level: Optional[str] = None,
        quote_state: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a ticket via n8n webhook with individual data fields for database storage
        
        Args:
            email: Customer email address
            subject: Ticket subject
            description: Ticket description (HTML format, no Unix/Windows newlines)
            product_id: Product ID (integer, from Region IDs table)
            group_id: Group ID (integer, from Region IDs table)
            source: Source ID (default: 10)
            tags: List of tags (default: ["WhatsAppBulk"])
            status: Status ID (default: 5)
            priority: Priority ID (default: 3)
            responder_id: Responder ID (default: 103141023779)
            customer_name: Customer name (optional)
            customer_email: Customer email address (optional)
            product_name: Product name (optional)
            quantity: Order quantity (optional)
            postcode: Customer postcode (optional)
            region: Region (optional)
            fabric: Fabric selection (optional)
            cover: Cover selection (optional)
            type: Type selection (optional)
            size: Size selection (optional)
            pages: Pages selection (optional)
            discount_percent: Discount percentage offered (optional)
            unit_price: Unit price formatted string (optional)
            total_price: Total price formatted string (optional)
            offers_shown: Comma-separated list of offers shown (optional)
            quote_level: Quote level when declined (optional)
            quote_state: Quote state (optional)
            
        Returns:
            Dictionary with success status and response data
        """
        # Build ticket data with description for backward compatibility and individual fields for database storage
        ticket_data = {
            "description": description
        }
        
        # Add individual fields if provided (only include non-None values)
        if customer_name is not None:
            ticket_data["customer_name"] = customer_name
        if customer_email is not None:
            ticket_data["customer_email"] = customer_email
        if product_name is not None:
            ticket_data["product_name"] = product_name
        if quantity is not None:
            ticket_data["quantity"] = quantity
        if postcode is not None:
            ticket_data["postcode"] = postcode
        if region is not None:
            ticket_data["region"] = region
        if fabric is not None:
            ticket_data["fabric"] = fabric
        if cover is not None:
            ticket_data["cover"] = cover
        if type is not None:
            ticket_data["type"] = type
        if size is not None:
            ticket_data["size"] = size
        if pages is not None:
            ticket_data["pages"] = pages
        if discount_percent is not None:
            ticket_data["discount_percent"] = discount_percent
        if unit_price is not None:
            ticket_data["unit_price"] = unit_price
        if total_price is not None:
            ticket_data["total_price"] = total_price
        if offers_shown is not None:
            ticket_data["offers_shown"] = offers_shown
        if quote_level is not None:
            ticket_data["quote_level"] = quote_level
        if quote_state is not None:
            ticket_data["quote_state"] = quote_state
        if product_id is not None:
            ticket_data["product_id"] = product_id
        if group_id is not None:
            ticket_data["group_id"] = group_id
        
        try:
            logger.info(f"Sending support ticket request to n8n webhook")
            logger.debug(f"Ticket data: {ticket_data}")
            
            response = requests.post(
                self.api_url,
                json=ticket_data,
                headers=self.headers,
                timeout=10
            )
            
            response.raise_for_status()
            
            # n8n webhook may return different response format
            try:
                response_data = response.json()
            except:
                response_data = {"status": "success", "message": response.text}
            
            logger.info(f"✅ Support ticket request sent successfully to n8n webhook")
            return {
                "success": True,
                "response": response_data
            }
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"n8n webhook returned {e.response.status_code}"
            if e.response.content:
                try:
                    error_data = e.response.json()
                    error_msg += f": {error_data}"
                except:
                    error_msg += f": {e.response.text[:200]}"
            
            logger.error(f"❌ Failed to send request to n8n webhook: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "status_code": e.response.status_code if e.response else None
            }
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Error calling n8n webhook: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
            
        except Exception as e:
            error_msg = f"Unexpected error sending request to n8n webhook: {str(e)}"
            logger.error(f"❌ {error_msg}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": error_msg
            }

