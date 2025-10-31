import requests
import logging
from config.settings import WHATSAPP_TOKEN, PHONE_NUMBER_ID
from utils.retry import retry_api_call
from utils.error_handler import WhatsAppAPIError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WhatsAppAPI:
    """Official WhatsApp Business Cloud API client"""

    BASE_URL = "https://graph.facebook.com/v18.0"

    def __init__(self):
        self.token = WHATSAPP_TOKEN
        self.phone_number_id = PHONE_NUMBER_ID
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    @retry_api_call(max_attempts=3)
    def send_message(self, to: str, message: str):
        """
        Send a text message to a WhatsApp user

        Args:
            to: Phone number in international format (e.g., "1234567890")
            message: Text message to send

        Returns:
            dict: API response
        """
        url = f"{self.BASE_URL}/{self.phone_number_id}/messages"

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message
            }
        }

        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=10)
            response.raise_for_status()

            data = response.json()
            logger.info(f"✓ Message sent to {to}: {data}")
            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error sending message to {to}: {e}")
            error_details = {}
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
                error_details = {"response": e.response.text}

            raise WhatsAppAPIError(
                message=f"Failed to send message to {to}",
                status_code=getattr(e.response, 'status_code', 500) if hasattr(e, 'response') else 500,
                details=error_details
            )

    def send_template_message(self, to: str, template_name: str, language_code: str = "en"):
        """
        Send a template message (useful for starting conversations)

        Args:
            to: Phone number in international format
            template_name: Name of the approved template
            language_code: Language code (default: "en")
        """
        url = f"{self.BASE_URL}/{self.phone_number_id}/messages"

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": language_code
                }
            }
        }

        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()

            data = response.json()
            logger.info(f"✓ Template message sent to {to}: {data}")
            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error sending template to {to}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise

    def mark_message_as_read(self, message_id: str):
        """Mark a message as read"""
        url = f"{self.BASE_URL}/{self.phone_number_id}/messages"

        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }

        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            logger.info(f"✓ Marked message {message_id} as read")
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error marking message as read: {e}")
            return None

    def get_media_url(self, media_id: str):
        """Get the download URL for a media file"""
        url = f"{self.BASE_URL}/{media_id}"

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()

            data = response.json()
            return data.get("url")

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error getting media URL: {e}")
            return None

    def download_media(self, media_url: str):
        """Download media file from WhatsApp"""
        try:
            response = requests.get(media_url, headers=self.headers)
            response.raise_for_status()
            return response.content

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error downloading media: {e}")
            return None

    @retry_api_call(max_attempts=3)
    def send_interactive_buttons(self, to: str, body_text: str, buttons: list):
        """
        Send an interactive button message (up to 3 buttons)
        
        Args:
            to: Phone number in international format
            body_text: Main message text
            buttons: List of button dicts with 'id' and 'title'
                    Example: [{"id": "btn_faq", "title": "General FAQ"}]
        
        Returns:
            dict: API response
        """
        url = f"{self.BASE_URL}/{self.phone_number_id}/messages"
        
        # Format buttons for WhatsApp API (max 3 buttons)
        formatted_buttons = []
        for btn in buttons[:3]:  # Limit to 3 buttons
            formatted_buttons.append({
                "type": "reply",
                "reply": {
                    "id": btn["id"],
                    "title": btn["title"]
                }
            })
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {
                    "text": body_text
                },
                "action": {
                    "buttons": formatted_buttons
                }
            }
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"✓ Interactive button message sent to {to}")
            return data
            
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            error_details = {}
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_details = e.response.json()
                    error_msg = error_details.get('error', {}).get('message', error_msg)
                    logger.error(f"❌ Error sending interactive buttons to {to}: {error_msg}")
                    logger.error(f"Full error: {error_details}")
                except:
                    logger.error(f"❌ Error sending interactive buttons to {to}: {error_msg}")
                    logger.error(f"Response text: {e.response.text}")
                    error_details = {"response": e.response.text}
            else:
                logger.error(f"❌ Error sending interactive buttons to {to}: {error_msg}")
            
            raise WhatsAppAPIError(
                message=f"Failed to send interactive buttons to {to}: {error_msg}",
                status_code=getattr(e.response, 'status_code', 500) if hasattr(e, 'response') else 500,
                details=error_details
            )

    @retry_api_call(max_attempts=3)
    def send_list_message(self, to: str, body_text: str, button_text: str, sections: list):
        """
        Send an interactive list message (dropdown menu)
        
        Args:
            to: Phone number in international format
            body_text: Main message text
            button_text: Text for the button that opens the list (e.g., "Choose Product")
            sections: List of sections, each containing 'rows' with 'id' and 'title'
                    Example: [{
                        "title": "Products",
                        "rows": [
                            {"id": "product_blankets", "title": "Blankets"},
                            {"id": "product_canvas", "title": "Canvas"}
                        ]
                    }]
        
        Returns:
            dict: API response
        """
        url = f"{self.BASE_URL}/{self.phone_number_id}/messages"
        
        # Format sections for WhatsApp API
        formatted_sections = []
        for section in sections:
            formatted_section = {
                "rows": section.get("rows", [])
            }
            if "title" in section:
                formatted_section["title"] = section["title"]
            formatted_sections.append(formatted_section)
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {
                    "text": body_text
                },
                "action": {
                    "button": button_text,
                    "sections": formatted_sections
                }
            }
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"✓ List message sent to {to}")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error sending list message to {to}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise WhatsAppAPIError(
                message=f"Failed to send list message to {to}",
                status_code=getattr(e.response, 'status_code', 500) if hasattr(e, 'response') else 500,
                details={"response": e.response.text} if hasattr(e, 'response') and e.response is not None else {}
            )
