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
        responder_id: int = 103141023779
    ) -> Dict[str, Any]:
        """
        Create a ticket via n8n webhook (sends same JSON payload as before)
        
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
            
        Returns:
            Dictionary with success status and response data
        """
        # Only send description field to n8n (simplified payload)
        ticket_data = {
            "description": description
        }
        
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

