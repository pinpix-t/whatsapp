"""
Bulk Pricing Service
Handles price calculation for bulk orders using Supabase lookup table and pricing API
"""

import logging
import requests
from typing import Dict, Optional, Tuple, Any
from supabase import create_client, Client
from config.settings import SUPABASE_URL, SUPABASE_KEY
from config.bulk_product_mapping import get_product_reference_code
from config.bulk_product_page_ids import get_product_page_id
from config.bulk_products import PRICE_POINT_MAPPING

logger = logging.getLogger(__name__)


class BulkPricingService:
    """Service for calculating bulk order prices"""
    
    def __init__(self):
        """Initialize Supabase client"""
        self.supabase: Optional[Client] = None
        if SUPABASE_URL and SUPABASE_KEY:
            try:
                self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
                logger.info("✓ Supabase client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
                self.supabase = None
        else:
            logger.warning("Supabase credentials not configured")
        
        # Pricing API base URL
        self.pricing_api_url = "https://qt-api.printerpix.co.uk/artwrap/GetProductsAndTierPricingV2/"
    
    def get_product_reference_code(self, selections: Dict) -> Optional[str]:
        """
        Get ProductReferenceCode from user selections
        
        Args:
            selections: Dictionary with product selections
            
        Returns:
            ProductReferenceCode string or None
        """
        return get_product_reference_code(selections)
    
    def get_discount_from_supabase(self, product_reference_code: str, price_point_id: str) -> Optional[float]:
        """
        Get discount percentage from Supabase lookup table
        
        Args:
            product_reference_code: ProductReferenceCode (e.g., "BlanketSherpafleece_25x20")
            price_point_id: PricePointId (e.g., "D" or "B")
            
        Returns:
            Discount percentage (0-100) or None if not found
        """
        if not self.supabase:
            logger.warning("Supabase not available, cannot get discount")
            return None
        
        if not product_reference_code or not price_point_id:
            logger.warning(f"Missing parameters: product_reference_code={product_reference_code}, price_point_id={price_point_id}")
            return None
        
        try:
            # Query Supabase table
            response = self.supabase.table("pricing_b_d").select("PercentDiscount").eq(
                "ProductReferenceCode", product_reference_code
            ).eq("PricePointId", price_point_id).execute()
            
            if response.data and len(response.data) > 0:
                discount = response.data[0].get("PercentDiscount")
                if discount is not None:
                    # PercentDiscount is stored as decimal (0.8549 = 85.49%)
                    # Convert to percentage for display/calculation
                    discount_percent = float(discount) * 100
                    logger.info(f"Found discount for {product_reference_code} (PricePoint {price_point_id}): {discount_percent}%")
                    return discount_percent
            
            logger.warning(f"No discount found for {product_reference_code} (PricePoint {price_point_id})")
            return None
            
        except Exception as e:
            logger.error(f"Error querying Supabase for discount: {e}")
            return None
    
    def get_base_price_from_api(self, product_selections: Dict, product_page_id: Optional[str] = None) -> Optional[float]:
        """
        Get base price from pricing API
        
        Args:
            product_selections: Product selections dictionary
            product_page_id: Optional productPageId (if not provided, will use placeholder)
            
        Returns:
            Base price in GBP or None if unavailable
        """
        # TODO: Need proper productPageId mapping
        # For now, use placeholder or skip if not provided
        if not product_page_id:
            logger.warning("productPageId not provided, cannot get base price from API")
            return None
        
        try:
            # Build JSON body (API expects productPageId in body, not params)
            body_data = {
                "productPageId": product_page_id,
                "photoW": 0,
                "photoH": 0,
                "defaultSorting": False
            }
            
            # Make POST request with JSON body
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            response = requests.post(
                self.pricing_api_url,
                json=body_data,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Extract price from response
            # API response structure may vary - check common patterns
            # Common fields: price, Price, unitPrice, basePrice, etc.
            price = None
            
            # Try various price field names
            price_fields = ["price", "Price", "unitPrice", "basePrice", "BasePrice", "UnitPrice", "productPrice"]
            for field in price_fields:
                if field in data:
                    price = float(data[field])
                    break
            
            # If price is in a nested structure, try common patterns
            if price is None:
                # Check if there's a products array or items array
                if isinstance(data, dict):
                    # Try nested structures
                    if "products" in data and isinstance(data["products"], list) and len(data["products"]) > 0:
                        first_product = data["products"][0]
                        for field in price_fields:
                            if field in first_product:
                                price = float(first_product[field])
                                break
                    elif "items" in data and isinstance(data["items"], list) and len(data["items"]) > 0:
                        first_item = data["items"][0]
                        for field in price_fields:
                            if field in first_item:
                                price = float(first_item[field])
                                break
            
            if price is not None:
                logger.info(f"Retrieved base price from API: £{price}")
                return price
            else:
                logger.warning(f"Price not found in API response. Available keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                # Log full response for debugging (first 1000 chars)
                logger.warning(f"API response preview: {str(data)[:1000]}")
                # Try to log more details about the response structure
                if isinstance(data, dict):
                    logger.warning(f"Response type: dict with {len(data)} keys")
                    if "products" in data:
                        logger.info(f"Found 'products' array with {len(data['products'])} items")
                        if len(data['products']) > 0:
                            logger.info(f"First product keys: {list(data['products'][0].keys()) if isinstance(data['products'][0], dict) else 'Not a dict'}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling pricing API: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing pricing API response: {e}")
            return None
    
    def calculate_bulk_price(self, base_price: float, discount_percent: float, quantity: int) -> float:
        """
        Calculate total bulk price
        
        Formula: base_price × (1 - discount_percent/100) × quantity
        
        Args:
            base_price: Base price per unit
            discount_percent: Discount percentage (0-100)
            quantity: Number of units
            
        Returns:
            Total price in GBP
        """
        discounted_price = base_price * (1 - discount_percent / 100)
        total_price = discounted_price * quantity
        return round(total_price, 2)
    
    def format_price_gbp(self, amount: float) -> str:
        """
        Format price as GBP currency string
        
        Args:
            amount: Price amount
            
        Returns:
            Formatted string like "£25.50"
        """
        return f"£{amount:.2f}"
    
    def get_bulk_price_info(
        self, 
        selections: Dict, 
        quantity: int, 
        offer_type: str = "first_offer",
        product_page_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get complete bulk pricing information
        
        Args:
            selections: Product selections dictionary
            quantity: Number of units
            offer_type: "first_offer" or "second_offer"
            product_page_id: Optional productPageId for pricing API (if not provided, will try to get from mapping)
            
        Returns:
            Dictionary with pricing info:
            {
                "success": bool,
                "product_reference_code": str,
                "discount_percent": float,
                "base_price": float,
                "unit_price": float,
                "total_price": float,
                "formatted_unit_price": str,
                "formatted_total_price": str,
                "error_message": str (if success=False)
            }
        """
        result = {
            "success": False,
            "product_reference_code": None,
            "discount_percent": None,
            "base_price": None,
            "unit_price": None,
            "total_price": None,
            "formatted_unit_price": None,
            "formatted_total_price": None,
            "error_message": None
        }
        
        # Get product reference code
        product_reference_code = self.get_product_reference_code(selections)
        result["product_reference_code"] = product_reference_code
        
        if not product_reference_code:
            logger.warning(f"Could not get ProductReferenceCode from selections: {selections}")
            logger.info(f"Missing fields - product: {selections.get('product')}, fabric: {selections.get('fabric')}, size: {selections.get('size')}")
            result["error_message"] = "Product reference code not found (missing fabric/size selections?)"
            return result
        
        logger.info(f"Found ProductReferenceCode: {product_reference_code} for selections: {selections}")
        
        # Get price point ID
        price_point_id = PRICE_POINT_MAPPING.get(offer_type)
        if not price_point_id:
            result["error_message"] = f"Price point not found for offer type: {offer_type}"
            return result
        
        # Get discount from Supabase
        discount_percent = self.get_discount_from_supabase(product_reference_code, price_point_id)
        result["discount_percent"] = discount_percent
        
        if discount_percent is None:
            result["error_message"] = "Discount not found in lookup table"
            return result
        
        # Get productPageId from mapping if not provided
        if not product_page_id:
            product_page_id = get_product_page_id(selections)
            if not product_page_id:
                logger.warning(f"Could not get productPageId from selections: {selections}")
                logger.info(f"Missing required fields - product: {selections.get('product')}, fabric: {selections.get('fabric')}, size: {selections.get('size')}")
        
        # Get base price from API (optional - can proceed without it)
        if product_page_id:
            logger.info(f"Attempting to get base price with productPageId: {product_page_id}")
            base_price = self.get_base_price_from_api(selections, product_page_id)
            result["base_price"] = base_price
        else:
            logger.warning("Cannot get base price - productPageId not available (missing fabric/size selections?)")
            base_price = None
            result["base_price"] = None
        
        # If we have both discount and base price, calculate totals
        if base_price is not None:
            unit_price = base_price * (1 - discount_percent / 100)
            total_price = self.calculate_bulk_price(base_price, discount_percent, quantity)
            
            result["unit_price"] = unit_price
            result["total_price"] = total_price
            result["formatted_unit_price"] = self.format_price_gbp(unit_price)
            result["formatted_total_price"] = self.format_price_gbp(total_price)
            result["success"] = True
        else:
            # We have discount but no base price - can still show discount percentage
            result["success"] = True  # Partial success - can show discount
            result["error_message"] = "Base price unavailable, showing discount only"
        
        return result


# Global instance
bulk_pricing_service = BulkPricingService()

