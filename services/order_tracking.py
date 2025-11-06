"""
Order tracking service for PrinterPix orders
Integrates with the official PrinterPix tracking API
"""

import requests
import logging
from typing import Dict, List, Optional, Tuple
from utils.retry import retry_api_call
from utils.error_handler import OrderTrackingError

logger = logging.getLogger(__name__)


class OrderTrackingService:
    """Service for tracking PrinterPix orders"""
    
    # Website codes mapping
    WEBSITE_CODES = {
        'UK': 4,
        'US': 6, 
        'FR': 10,
        'ES': 12,
        'IT': 13,
        'NL': 14,
        'DE': 16,
        'AE': 17,
        'IN': 18
    }
    
    # Reverse mapping for display
    CODE_TO_COUNTRY = {v: k for k, v in WEBSITE_CODES.items()}
    
    def __init__(self):
        self.base_url = "https://ediapi.printerpix.com/track-my-order/website"
    
    def extract_website_code(self, order_number: str) -> Optional[int]:
        """
        Extract website code from order number
        
        Args:
            order_number: Order number (8-10 digits)
            
        Returns:
            Website code or None if not found
        """
        # Remove any non-digit characters
        clean_order = ''.join(filter(str.isdigit, order_number))
        
        if len(clean_order) < 8:
            return None
            
        # Check first digit
        first_digit = int(clean_order[0])
        if first_digit in self.CODE_TO_COUNTRY:
            return first_digit
            
        # Check first two digits
        if len(clean_order) >= 2:
            first_two_digits = int(clean_order[:2])
            if first_two_digits in self.CODE_TO_COUNTRY:
                return first_two_digits
        
        # Default fallback: try website code 1 (US) if no match found
        # This handles cases where country code isn't clearly identifiable
        logger.warning(f"Could not identify website code for {clean_order}, defaulting to 1 (US)")
        return 1
    
    def validate_order_number(self, order_number: str) -> Tuple[bool, str]:
        """
        Validate order number format
        
        Args:
            order_number: Order number to validate
            
        Returns:
            (is_valid, error_message)
        """
        # Remove any non-digit characters
        clean_order = ''.join(filter(str.isdigit, order_number))
        
        if len(clean_order) < 8:
            return False, "Order number must be at least 8 digits"
            
        if len(clean_order) > 10:
            return False, "Order number must be 10 digits or less"
            
        # Check if we can extract a valid website code
        website_code = self.extract_website_code(clean_order)
        if not website_code:
            return False, f"Order number must start with a valid country code: {list(self.WEBSITE_CODES.keys())}"
            
        return True, ""
    
    @retry_api_call(max_attempts=3)
    def track_order(self, order_number: str) -> Dict:
        """
        Track an order using the PrinterPix API
        
        Args:
            order_number: Order number to track
            
        Returns:
            Tracking information dictionary
        """
        try:
            # Validate order number
            is_valid, error_msg = self.validate_order_number(order_number)
            if not is_valid:
                raise OrderTrackingError(f"Invalid order number: {error_msg}")
            
            # Extract website code
            website_code = self.extract_website_code(order_number)
            clean_order = ''.join(filter(str.isdigit, order_number))
            
            # Make API request
            params = {
                'webSiteCode': website_code,
                'orderNo': clean_order
            }
            
            logger.info(f"Tracking order {clean_order} for website code {website_code}")
            logger.info(f"API URL: {self.base_url} with params: {params}")
            
            try:
                response = requests.get(
                    self.base_url,
                    params=params,
                    timeout=10
                )
                logger.info(f"API Response status: {response.status_code}")
                
                # Handle 500 errors from the API
                if response.status_code == 500:
                    logger.error(f"Tracking API returned 500 error for order {order_number}")
                    # Try alternative website codes if first attempt fails
                    if website_code == 1:
                        # Try UK (4) as fallback
                        logger.info(f"Retrying with website code 4 (UK)")
                        params_retry = {'webSiteCode': 4, 'orderNo': clean_order}
                        response_retry = requests.get(self.base_url, params=params_retry, timeout=10)
                        if response_retry.status_code == 200:
                            response = response_retry
                            website_code = 4
                        else:
                            raise OrderTrackingError("The tracking system is currently unavailable. Please try again later or contact support.")
                    else:
                        raise OrderTrackingError("The tracking system is currently unavailable. Please try again later or contact support.")
                
                response.raise_for_status()
                
                data = response.json()
                logger.info(f"API Response data keys: {list(data.keys())}")
                
                # Check if tracking data exists
                if 'Tracking' not in data or not data['Tracking']:
                    logger.warning(f"No tracking data in response: {data}")
                    raise OrderTrackingError("No tracking information found for this order number")
            except requests.exceptions.Timeout:
                logger.error(f"Timeout connecting to tracking API for order {order_number}")
                raise OrderTrackingError("Failed to retrieve tracking information: Request timeout. Please try again.")
            except requests.exceptions.ConnectionError as e:
                logger.error(f"Connection error to tracking API: {e}")
                raise OrderTrackingError(f"Failed to retrieve tracking information: Cannot connect to tracking service.")
            
            # Add metadata
            data['order_number'] = clean_order
            data['website_code'] = website_code
            data['country'] = self.CODE_TO_COUNTRY.get(website_code, 'Unknown')
            
            logger.info(f"Successfully retrieved tracking for order {clean_order}")
            return data
            
        except OrderTrackingError:
            # Re-raise our custom errors (timeout, connection, etc.) as-is
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for order {order_number}: {e}")
            raise OrderTrackingError(f"Failed to retrieve tracking information: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error tracking order {order_number}: {e}")
            raise OrderTrackingError(f"Error tracking order: {str(e)}")
    
    def format_tracking_response(self, tracking_data: Dict) -> str:
        """
        Format tracking data into a user-friendly message
        
        Args:
            tracking_data: Raw tracking data from API
            
        Returns:
            Formatted message string
        """
        try:
            tracking_array = tracking_data.get('Tracking', [])
            order_number = tracking_data.get('order_number', 'Unknown')
            country = tracking_data.get('country', 'Unknown')
            
            if not tracking_array:
                return f"📦 I looked for order #{order_number}, but I don't have any tracking information for it yet. It might still be processing - try checking back in a bit, or contact support if you think there's an issue!"
            
            # Handle the actual API response format
            return self._format_actual_tracking_response(order_number, country, tracking_array)
            
        except Exception as e:
            logger.error(f"Error formatting tracking response: {e}")
            return f"📦 I found your order #{order_number}, but I'm having trouble getting the tracking details right now. Could you try again in a moment? If it keeps happening, feel free to contact support!"
    
    def _format_actual_tracking_response(self, order_number: str, country: str, tracking_array: List[Dict]) -> str:
        """Format tracking in a natural, conversational way"""
        # Parse according to exact rules
        parsed_data = self._parse_tracking_data(tracking_array)
        
        if not parsed_data['orders']:
            return f"📦 I found your order #{order_number} ({country}), but there's no tracking information available yet. It might still be processing - check back in a bit!"
        
        order_data = parsed_data['orders'][0]
        packages = order_data.get('packages', [])
        
        # Start with a friendly greeting
        response = f"Great news! I found your order #{order_number} ({country}). "
        
        # Handle order-level updates (most recent first)
        order_updates = [item for item in tracking_array 
                       if item.get('CONumber', '') == '' and 
                       item.get('Updates', {}).get('TrackingNumber', '') == '']
        
        if order_updates:
            # Get the latest update
            latest_update = order_updates[-1]
            updates_data = latest_update.get('Updates', {})
            status = updates_data.get('StatusDesc', 'Unknown')
            message_title = updates_data.get('MessageTitle', '')
            message_body = updates_data.get('MessageBody', '')
            date = updates_data.get('ShipmentDate', '')
            time = updates_data.get('ShipmentTime', '')
            
            status_emoji = self._get_status_emoji(status)
            
            # Natural status message
            if status.lower() in ['delivered', 'completed']:
                response += f"{status_emoji} It looks like your order has been delivered! "
            elif 'shipped' in status.lower() or 'courier' in status.lower():
                response += f"{status_emoji} Your order has shipped and is on the way! "
            elif 'processing' in status.lower() or 'working' in status.lower():
                response += f"{status_emoji} Your order is currently being processed. "
            else:
                response += f"{status_emoji} Current status: {status}. "
            
            # Add message details naturally
            if message_title or message_body:
                response += "\n\n"
                if message_title:
                    response += f"{message_title}"
                    if message_body:
                        response += f" {message_body}"
                elif message_body:
                    response += message_body
            
            # Add date/time naturally
            if date:
                formatted_date = self._format_date_natural(date)
                if time:
                    formatted_time = time[:5] if len(time) >= 5 else time[:8]
                    response += f"\n\nLast updated: {formatted_date} at {formatted_time}"
                else:
                    response += f"\n\nLast updated: {formatted_date}"
        
        # Handle packages naturally
        if packages:
            if len(packages) == 1:
                package = packages[0]
                status_emoji = self._get_status_emoji(package['latestStatus'])
                
                response += f"\n\n🚚 Tracking number: {package['trackingNumber']}"
                
                if package.get('coNumber'):
                    response += f"\nCO Number: {package['coNumber']}"
                
                # Natural status message for package
                if package['latestStatus'].lower() in ['delivered', 'completed']:
                    response += f"\n{status_emoji} This package has been delivered!"
                elif 'shipped' in package['latestStatus'].lower():
                    response += f"\n{status_emoji} This package is in transit."
                else:
                    response += f"\n{status_emoji} Status: {package['latestStatus']}"
            else:
                response += f"\n\nYour order has {len(packages)} packages:\n"
                for i, package in enumerate(packages, 1):
                    status_emoji = self._get_status_emoji(package['latestStatus'])
                    response += f"\n📦 Package {i}:"
                    if package.get('coNumber'):
                        response += f" CO {package['coNumber']}"
                    response += f"\n🚚 Tracking: {package['trackingNumber']}"
                    response += f"\n{status_emoji} {package['latestStatus']}"
        
        # Friendly closing
        response += "\n\nNeed more details? Just ask or visit our website!"
        
        return response
    
    def _format_date_natural(self, date_str: str) -> str:
        """Format date in a more natural way"""
        try:
            # Try to parse date if it's in YYYY-MM-DD format
            if '-' in date_str and len(date_str) >= 10:
                year, month, day = date_str[:10].split('-')
                months = ['January', 'February', 'March', 'April', 'May', 'June',
                         'July', 'August', 'September', 'October', 'November', 'December']
                try:
                    month_name = months[int(month) - 1]
                    # Remove leading zero from day
                    day = str(int(day))
                    return f"{month_name} {day}, {year}"
                except (ValueError, IndexError):
                    return date_str
            return date_str
        except:
            return date_str

    def _parse_tracking_data(self, tracking_array: List[Dict]) -> Dict:
        """Parse tracking data according to exact rules"""
        # Group by InvoiceNumber
        orders = {}
        
        for item in tracking_array:
            invoice_number = item.get('InvoiceNumber')
            if not invoice_number:
                continue
                
            if invoice_number not in orders:
                orders[invoice_number] = {
                    'invoiceNumber': str(invoice_number),
                    'customerOrderNumbers': set(),
                    'totalUpdates': 0,
                    'packages': {},
                    'orderLevelUpdates': 0,
                    'packageUpdates': 0
                }
            
            orders[invoice_number]['totalUpdates'] += 1
            
            updates_data = item.get('Updates', {})
            tracking_number = updates_data.get('TrackingNumber', '')
            conumber = item.get('CONumber', '')
            
            # Count order-level updates (both CONumber and TrackingNumber empty)
            if conumber == '' and tracking_number == '':
                orders[invoice_number]['orderLevelUpdates'] += 1
            else:
                # Track customer order numbers
                if conumber:
                    orders[invoice_number]['customerOrderNumbers'].add(conumber)
                
                # Count as package only if TrackingNumber is non-empty
                if tracking_number:
                    orders[invoice_number]['packageUpdates'] += 1
                    
                    # Group packages by TrackingNumber
                    if tracking_number not in orders[invoice_number]['packages']:
                        orders[invoice_number]['packages'][tracking_number] = {
                            'trackingNumber': tracking_number,
                            'coNumber': None,
                            'carrierId': updates_data.get('ShippingCarrierID', 0),
                            'latestStatus': updates_data.get('StatusDesc', 'Unknown'),
                            'latestTimestamp': f"{updates_data.get('ShipmentDate', '')}T{updates_data.get('ShipmentTime', '')[:8]}"
                        }
                    
                    # Update with latest info
                    current_timestamp = f"{updates_data.get('ShipmentDate', '')}T{updates_data.get('ShipmentTime', '')[:8]}"
                    if current_timestamp > orders[invoice_number]['packages'][tracking_number]['latestTimestamp']:
                        orders[invoice_number]['packages'][tracking_number].update({
                            'latestStatus': updates_data.get('StatusDesc', 'Unknown'),
                            'latestTimestamp': current_timestamp,
                            'carrierId': updates_data.get('ShippingCarrierID', 0)
                        })
                    
                    # Update CO number if present
                    if conumber:
                        orders[invoice_number]['packages'][tracking_number]['coNumber'] = conumber
        
        # Convert to final format
        result = {
            'orders': [],
            'totals': {
                'orders': 0,
                'packages': 0,
                'updates': len(tracking_array)
            }
        }
        
        for order_data in orders.values():
            order_data['customerOrderNumbers'] = list(order_data['customerOrderNumbers'])
            order_data['packages'] = list(order_data['packages'].values())
            order_data['counts'] = {
                'orderLevelUpdates': order_data['orderLevelUpdates'],
                'packageUpdates': order_data['packageUpdates']
            }
            del order_data['orderLevelUpdates']
            del order_data['packageUpdates']
            
            result['orders'].append(order_data)
            result['totals']['orders'] += 1
            result['totals']['packages'] += len(order_data['packages'])
        
        return result

    def _get_status_emoji(self, status: str) -> str:
        """Get emoji for status"""
        status_lower = status.lower()
        
        if 'working on it' in status_lower or 'processing' in status_lower:
            return '⚙️'
        elif 'good news' in status_lower or 'magic' in status_lower:
            return '✨'
        elif 'courier' in status_lower or 'shipped' in status_lower:
            return '🚚'
        elif 'delivered' in status_lower:
            return '✅'
        elif 'out for delivery' in status_lower:
            return '🚛'
        else:
            return '📦'

    def _format_single_package_tracking(self, order_number: str, country: str, tracking_info: Dict) -> str:
        """Format tracking for single package"""
        status = tracking_info.get('Status', 'Unknown')
        location = tracking_info.get('Location', 'Unknown')
        date = tracking_info.get('Date', 'Unknown')
        time = tracking_info.get('Time', 'Unknown')
        
        # Map status to emoji
        status_emoji = {
            'delivered': '✅',
            'in_transit': '🚚',
            'processing': '⚙️',
            'shipped': '📦',
            'out_for_delivery': '🚛'
        }.get(status.lower().replace(' ', '_'), '📦')
        
        return f"""📦 **Order #{order_number}** ({country})
        
{status_emoji} **Status:** {status}
📍 **Location:** {location}
📅 **Date:** {date}
🕐 **Time:** {time}

For more detailed tracking, visit our website or contact support."""
    
    def _format_multi_package_tracking(self, order_number: str, country: str, tracking_array: List[Dict]) -> str:
        """Format tracking for multiple packages"""
        response = f"📦 *Order #{order_number}* ({country})\n\n"
        response += f"This order has **{len(tracking_array)} packages**:\n\n"
        
        for i, package in enumerate(tracking_array, 1):
            co_ref = package.get('CO', f'Package {i}')
            status = package.get('Status', 'Unknown')
            
            status_emoji = {
                'delivered': '✅',
                'in_transit': '🚚', 
                'processing': '⚙️',
                'shipped': '📦',
                'out_for_delivery': '🚛'
            }.get(status.lower().replace(' ', '_'), '📦')
            
            response += f"**Package {i}:** {co_ref}\n"
            response += f"{status_emoji} Status: {status}\n\n"
        
        response += "To get detailed tracking for a specific package, please provide the CO reference."
        
        return response
    
    def get_supported_countries(self) -> str:
        """Get list of supported countries for display"""
        countries = list(self.WEBSITE_CODES.keys())
        return ", ".join(countries)


# Global instance
order_tracking_service = OrderTrackingService()
