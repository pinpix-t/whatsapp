"""
Freshdesk Service
Handles ticket creation in Freshdesk for bulk order escalations
"""

import logging
import requests
import base64
from typing import Dict, Optional, Any
from config.settings import FRESHDESK_API_URL, FRESHDESK_API_KEY

logger = logging.getLogger(__name__)


class FreshdeskService:
    """Service for creating tickets in Freshdesk"""
    
    def __init__(self):
        """Initialize Freshdesk service"""
        # Use environment variables or fallback to hardcoded values
        self.api_url = FRESHDESK_API_URL or "https://printerpix-support.freshdesk.com/api/v2/tickets"
        
        # Build auth header from API key
        if FRESHDESK_API_KEY:
            # Freshdesk uses API key as username with password "X" (or empty)
            auth_string = f"{FRESHDESK_API_KEY}:X"
            auth_bytes = auth_string.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            self.auth_header = f"Basic {auth_b64}"
        else:
            # Fallback to hardcoded (for backward compatibility)
            logger.warning("⚠️ FRESHDESK_API_KEY not set, using fallback credentials")
            self.auth_header = "Basic RmZLSDR4Q0xMb1FTREtMZmFYenU6WA=="
        
        self.headers = {
            "Authorization": self.auth_header,
            "Content-Type": "application/json"
        }
    
    def create_ticket(
        self,
        email: str,
        subject: str,
        description: str,
        product_id: Optional[int] = None,
        group_id: Optional[int] = None,
        source: int = 13,
        tags: Optional[list] = None,
        status: int = 5,
        priority: int = 3,
        responder_id: int = 103141023779
    ) -> Dict[str, Any]:
        """
        Create a ticket in Freshdesk
        
        Args:
            email: Customer email address
            subject: Ticket subject
            description: Ticket description (HTML format, no Unix/Windows newlines)
            product_id: Product ID (integer, from Region IDs table)
            group_id: Group ID (integer, from Region IDs table)
            source: Source ID (default: 13)
            tags: List of tags (default: ["WhatsAppBulk"])
            status: Status ID (default: 5)
            priority: Priority ID (default: 3)
            responder_id: Responder ID (default: 103141023779)
            
        Returns:
            Dictionary with ticket_id if successful, or error information
        """
        if tags is None:
            tags = ["WhatsAppBulk"]
        
        # Build ticket payload
        ticket_data = {
            "email": email,
            "source": source,
            "tags": tags,
            "status": status,
            "priority": priority,
            "responder_id": responder_id,
            "custom_fields": {
                "cf_exclude_from_automations": True,
                "cf_noapi": True
            },
            "subject": subject,
            "description": description
        }
        
        # Add product_id and group_id if provided
        if product_id is not None:
            ticket_data["product_id"] = product_id
        if group_id is not None:
            ticket_data["group_id"] = group_id
        
        try:
            logger.info(f"Creating Freshdesk ticket for {email}")
            logger.debug(f"Ticket data: {ticket_data}")
            
            response = requests.post(
                self.api_url,
                json=ticket_data,
                headers=self.headers,
                timeout=10
            )
            
            response.raise_for_status()
            
            ticket = response.json()
            ticket_id = ticket.get("id")
            
            logger.info(f"✅ Freshdesk ticket created successfully: ID {ticket_id}")
            return {
                "success": True,
                "ticket_id": ticket_id,
                "ticket": ticket
            }
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"Freshdesk API returned {e.response.status_code}"
            if e.response.content:
                try:
                    error_data = e.response.json()
                    error_msg += f": {error_data}"
                except:
                    error_msg += f": {e.response.text[:200]}"
            
            logger.error(f"❌ Failed to create Freshdesk ticket: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "status_code": e.response.status_code if e.response else None
            }
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Error calling Freshdesk API: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
            
        except Exception as e:
            error_msg = f"Unexpected error creating Freshdesk ticket: {str(e)}"
            logger.error(f"❌ {error_msg}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": error_msg
            }

