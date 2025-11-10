"""
Bulk Pricing Service
Handles price calculation for bulk orders using CSV file for base prices and Supabase for discounts
"""

import logging
import os
import requests
import pandas as pd
from typing import Dict, Optional, Tuple, Any
from supabase import create_client, Client
from config.settings import SUPABASE_URL, SUPABASE_KEY, CSV_DATA_PATH
from config.bulk_product_mapping import get_product_reference_code
from config.bulk_product_page_ids import get_product_page_id
from config.bulk_products import PRICE_POINT_MAPPING

logger = logging.getLogger(__name__)

# Import base price mapping with fallback
try:
    from config.bulk_base_prices import get_base_price as get_base_price_from_mapping
except ImportError as e:
    logger.warning(f"⚠️ Cannot import bulk_base_prices module: {e}")
    logger.warning("Base prices will not be available from mapping file")
    get_base_price_from_mapping = None

# Import SQL Server store for base prices
try:
    from database.sql_server_store import sql_server_store
except ImportError as e:
    logger.warning(f"⚠️ Cannot import sql_server_store: {e}")
    logger.warning("SQL Server base prices will not be available")
    sql_server_store = None


class BulkPricingService:
    """Service for calculating bulk order prices"""
    
    def __init__(self):
        """Initialize Supabase client and load CSV data"""
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
        # NOTE: This API may require authentication or a different request format
        # Currently returns 400 Bad Request - base price lookup is disabled until API access is configured
        self.pricing_api_url = "https://qt-api.printerpix.co.uk/artwrap/GetProductsAndTierPricingV2/"
        
        # Load CSV data for base prices
        self.csv_price_lookup: Dict[str, float] = {}
        self._load_csv_data()
    
    def _load_csv_data(self) -> None:
        """
        Load CSV file and create price lookup dictionary
        
        Loads the CSV file containing product data and creates an in-memory
        lookup dictionary mapping platinumProductReferenceId to price.
        """
        try:
            csv_path = CSV_DATA_PATH
            if not os.path.exists(csv_path):
                logger.warning(f"CSV file not found at {csv_path}, CSV price lookup will be unavailable")
                return
            
            # Load CSV file
            df = pd.read_csv(csv_path)
            
            # Check required columns exist
            if 'platinumProductReferenceId' not in df.columns or 'price' not in df.columns:
                logger.error(f"CSV file missing required columns. Found: {list(df.columns)}")
                return
            
            # Filter out rows with null/empty prices
            df_filtered = df[df['price'].notna() & (df['price'] != '')]
            
            # Create lookup dictionary: {platinumProductReferenceId: price}
            for _, row in df_filtered.iterrows():
                ref_id = str(row['platinumProductReferenceId']).strip()
                price = row['price']
                
                # Skip if price is not numeric
                try:
                    price_float = float(price)
                    if price_float > 0:  # Only store positive prices
                        self.csv_price_lookup[ref_id] = price_float
                except (ValueError, TypeError):
                    continue
            
            logger.info(f"✓ Loaded {len(self.csv_price_lookup)} product prices from CSV file: {csv_path}")
            
        except Exception as e:
            logger.error(f"Error loading CSV data: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.csv_price_lookup = {}
    
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
    
    def get_product_page_id_from_supabase(self, product_reference_code: str) -> Optional[str]:
        """
        Get productPageId (Guid) from Supabase pricing_b_d table
        
        Args:
            product_reference_code: ProductReferenceCode (e.g., "BlanketSherpafleece_25x20")
            
        Returns:
            productPageId (Guid) string or None if not found
        """
        if not self.supabase:
            logger.warning("Supabase not available, cannot get productPageId")
            return None
        
        if not product_reference_code:
            logger.warning(f"Missing product_reference_code for productPageId lookup")
            return None
        
        try:
            # Query Supabase table to get Guid (productPageId)
            response = self.supabase.table("pricing_b_d").select("Guid").eq(
                "ProductReferenceCode", product_reference_code
            ).limit(1).execute()
            
            if response.data and len(response.data) > 0:
                guid = response.data[0].get("Guid")
                if guid:
                    logger.info(f"✅ Found productPageId (Guid) for {product_reference_code}: {guid}")
                    return guid
                else:
                    logger.warning(f"Guid column is null for {product_reference_code}")
            else:
                logger.warning(f"No data found for {product_reference_code} in pricing_b_d table")
            
            return None
            
        except Exception as e:
            logger.error(f"Error querying Supabase for productPageId: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def get_base_price_from_csv(self, product_reference_code: str) -> Optional[float]:
        """
        Get base price from CSV data (loaded from ProductPage table)
        
        Args:
            product_reference_code: ProductReferenceCode (e.g., "BlanketSherpafleece_25x20")
            
        Returns:
            Base price in GBP or None if not found
        """
        if not product_reference_code:
            logger.warning(f"Missing product_reference_code for CSV base price lookup")
            return None
        
        if not self.csv_price_lookup:
            logger.warning("CSV price lookup not available (CSV not loaded)")
            return None
        
        try:
            # Look up price by platinumProductReferenceId
            price = self.csv_price_lookup.get(product_reference_code)
            
            if price is not None:
                logger.info(f"✅ Found base price from CSV for {product_reference_code}: £{price}")
                return float(price)
            
            logger.warning(f"No base price found in CSV for {product_reference_code}")
            return None
            
        except Exception as e:
            logger.error(f"Error looking up price in CSV: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def get_base_price_from_sql_server(self, product_reference_code: str) -> Optional[float]:
        """
        Get base price from SQL Server PlatinumProduct table (DEPRECATED - use CSV instead)
        
        Args:
            product_reference_code: ProductReferenceCode (e.g., "BlanketSherpafleece_25x20")
            
        Returns:
            Base price in GBP or None if not found
        """
        if not sql_server_store or not sql_server_store.engine:
            logger.warning("SQL Server not available, cannot get base price")
            return None
        
        if not product_reference_code:
            logger.warning(f"Missing product_reference_code for SQL Server base price lookup")
            return None
        
        try:
            # Query SQL Server PlatinumProduct table
            sql = """
                SELECT TOP (1) price, currency
                FROM [dbo].[SynComs.Products.PlatinumProducts.PlatinumProduct]
                WHERE platinumProductReferenceId = :ref_code
                AND price IS NOT NULL;
            """
            
            df = sql_server_store.query_to_dataframe(sql, params={"ref_code": product_reference_code})
            
            if not df.empty and len(df) > 0:
                price = float(df.iloc[0]['price'])
                currency = df.iloc[0].get('currency', 1)  # 1 = GBP typically
                
                # Convert to GBP if needed (currency 1 = GBP)
                if currency != 1:
                    logger.warning(f"Price in currency {currency}, may need conversion")
                
                logger.info(f"✅ Found base price from SQL Server for {product_reference_code}: £{price}")
                return price
            
            logger.warning(f"No base price found in SQL Server for {product_reference_code}")
            return None
            
        except Exception as e:
            logger.error(f"Error querying SQL Server for base price: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def get_base_price_from_supabase(self, product_reference_code: str) -> Optional[float]:
        """
        Get base price from Supabase lookup table
        
        Args:
            product_reference_code: ProductReferenceCode (e.g., "BlanketSherpafleece_25x20")
            
        Returns:
            Base price in GBP or None if not found
        """
        if not self.supabase:
            logger.warning("Supabase not available, cannot get base price")
            return None
        
        if not product_reference_code:
            logger.warning(f"Missing product_reference_code for base price lookup")
            return None
        
        try:
            # Query Supabase table to check available columns
            # NOTE: pricing_b_d table currently only has PercentDiscount, not base prices
            response = self.supabase.table("pricing_b_d").select("*").eq(
                "ProductReferenceCode", product_reference_code
            ).limit(1).execute()
            
            if response.data and len(response.data) > 0:
                row = response.data[0]
                available_fields = list(row.keys())
                logger.debug(f"Available fields in pricing_b_d for {product_reference_code}: {available_fields}")
                
                # Try various price field names in case they add it later
                price_fields = ["BasePrice", "Price", "UnitPrice", "base_price", "price", "UnitPrice", "BasePricePerUnit"]
                for field in price_fields:
                    if field in row and row[field] is not None:
                        base_price = float(row[field])
                        logger.info(f"Found base price for {product_reference_code}: £{base_price}")
                        return base_price
                
                logger.warning(f"No base price field found. pricing_b_d table only has: {available_fields}")
                logger.warning(f"Base price needs to be added to pricing_b_d table or retrieved from another source")
            
            logger.warning(f"No data found for {product_reference_code} in pricing_b_d table")
            return None
            
        except Exception as e:
            logger.error(f"Error querying Supabase for base price: {e}")
            return None
    
    def get_base_price_from_api(self, product_selections: Dict, product_page_id: Optional[str] = None, product_reference_code: Optional[str] = None) -> Optional[float]:
        """
        Get base price from pricing API
        
        Args:
            product_selections: Product selections dictionary
            product_page_id: Optional productPageId (if not provided, will use placeholder)
            product_reference_code: Optional ProductReferenceCode to match in API response
            
        Returns:
            Base price in GBP or None if unavailable
        """
        if not product_page_id:
            logger.warning("productPageId not provided, cannot get base price from API")
            return None
        
        try:
            # Build query parameters (API expects parameters in query string)
            params = {
                "productPageId": product_page_id,
                "couponCode": "",
                "couponProductId": "",
                "vc": "",
                "affCoupon": "",
                "photoW": 0,
                "photoH": 0,
                "defaultSorting": "false",
                "preselectedRefId": ""
            }
            
            # Make POST request with empty JSON body and params in query string
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            # Send empty JSON body as required by API
            response = requests.post(
                self.pricing_api_url,
                params=params,
                json={},  # Empty JSON body as required
                headers=headers,
                timeout=10
            )
            
            # Check if response is successful
            if response.status_code != 200:
                logger.warning(f"API returned status {response.status_code} for productPageId {product_page_id}")
                return None
            
            data = response.json()
            
            # Check if API returned an error
            if isinstance(data, dict):
                status = data.get("Status", "").upper()
                if status == "ERROR":
                    error_msg = data.get("Message", "Unknown error")
                    error_code = data.get("ErrorCode", "")
                    logger.warning(f"API returned error for productPageId {product_page_id}: {error_code} - {error_msg}")
                    logger.warning(f"This is a server-side API bug. Falling back to local mapping file.")
                    return None
            
            # Parse the API response structure
            # Response has: data.tierPricings[] with platinumProductReferenceId and prices[]
            base_price = None
            
            if isinstance(data, dict) and "data" in data:
                tier_pricings = data.get("data", {}).get("tierPricings", [])
                
                if tier_pricings and isinstance(tier_pricings, list):
                    # If product_reference_code is provided, try to match it
                    if product_reference_code:
                        # Normalize our ProductReferenceCode for comparison (remove underscores, lowercase)
                        our_code_normalized = product_reference_code.lower().replace("_", "").replace("-", "")
                        
                        # Extract dimensions from our ProductReferenceCode for unit conversion
                        # Format: BlanketSherpafleece_30x40 -> extract 30x40
                        import re
                        dimension_match = re.search(r'(\d+)x(\d+)', product_reference_code)
                        our_dimensions_inches = None
                        our_dimensions_cm = None
                        if dimension_match:
                            width_inches = int(dimension_match.group(1))
                            height_inches = int(dimension_match.group(2))
                            our_dimensions_inches = f"{width_inches}x{height_inches}"
                            # Convert to cm (1 inch = 2.54 cm, round to nearest integer)
                            width_cm = round(width_inches * 2.54)
                            height_cm = round(height_inches * 2.54)
                            our_dimensions_cm = f"{width_cm}x{height_cm}"
                        
                        # Try to find matching tier pricing by platinumProductReferenceId
                        for tier in tier_pricings:
                            platinum_id = tier.get("platinumProductReferenceId", "")
                            if not platinum_id:
                                continue
                            
                            # Try exact case-insensitive match first
                            if platinum_id.lower() == product_reference_code.lower():
                                # Found exact match, get price for QTY=1
                                prices = tier.get("prices", [])
                                for price_entry in prices:
                                    if price_entry.get("quantity") == 1:
                                        base_price = float(price_entry.get("price", 0))
                                        logger.info(f"✅ Found exact match: API returned base price for {product_reference_code}: £{base_price}")
                                        return base_price
                            
                            # Try normalized comparison (ignore underscores/dashes)
                            api_code_normalized = platinum_id.lower().replace("_", "").replace("-", "")
                            if api_code_normalized == our_code_normalized:
                                # Found normalized match, get price for QTY=1
                                prices = tier.get("prices", [])
                                for price_entry in prices:
                                    if price_entry.get("quantity") == 1:
                                        base_price = float(price_entry.get("price", 0))
                                        logger.info(f"✅ Found normalized match: API returned base price for {product_reference_code} (matched {platinum_id}): £{base_price}")
                                        return base_price
                            
                            # Try unit conversion match (inches vs cm)
                            if our_dimensions_inches and our_dimensions_cm:
                                # Check if API code contains our dimensions in inches
                                if our_dimensions_inches in platinum_id or our_dimensions_inches.replace("x", "X") in platinum_id:
                                    prices = tier.get("prices", [])
                                    for price_entry in prices:
                                        if price_entry.get("quantity") == 1:
                                            base_price = float(price_entry.get("price", 0))
                                            logger.info(f"✅ Found dimension match (inches): API returned base price for {product_reference_code} (matched {platinum_id}): £{base_price}")
                                            return base_price
                                
                                # Check if API code contains our dimensions in cm
                                if our_dimensions_cm in platinum_id or our_dimensions_cm.replace("x", "X") in platinum_id:
                                    prices = tier.get("prices", [])
                                    for price_entry in prices:
                                        if price_entry.get("quantity") == 1:
                                            base_price = float(price_entry.get("price", 0))
                                            logger.info(f"✅ Found dimension match (cm): API returned base price for {product_reference_code} (matched {platinum_id}): £{base_price}")
                                            return base_price
                        
                        # No match found - log available options for debugging
                        available_ids = [tier.get("platinumProductReferenceId", "unknown") for tier in tier_pricings if tier.get("platinumProductReferenceId")]
                        logger.warning(f"⚠️ No match found for {product_reference_code} in API response")
                        logger.warning(f"Looking for: {product_reference_code} (normalized: {our_code_normalized})")
                        logger.warning(f"Available platinumProductReferenceIds: {available_ids}")
                        logger.warning("Will fall back to local mapping file instead of using wrong product's price")
                        # Don't use first tier's price if it doesn't match - return None to fall back to local mapping
                        return None
                    
                    # If no product_reference_code provided, we can't safely match - return None
                    logger.warning("No product_reference_code provided for API lookup - cannot safely match")
                    return None
            
            # Fallback: try to get price from products array
            if base_price is None and isinstance(data, dict) and "data" in data:
                products = data.get("data", {}).get("products", [])
                if products and isinstance(products, list) and len(products) > 0:
                    first_product = products[0]
                    # Try common price fields
                    price_fields = ["price", "Price", "unitPrice", "basePrice"]
                    for field in price_fields:
                        if field in first_product:
                            base_price = float(first_product[field])
                            logger.info(f"Found base price from products array: £{base_price}")
                            return base_price
            
            if base_price is None:
                logger.warning(f"Price not found in API response. Available keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                if isinstance(data, dict) and "data" in data:
                    logger.warning(f"Data keys: {list(data['data'].keys())}")
                    if "tierPricings" in data["data"]:
                        logger.warning(f"Found {len(data['data']['tierPricings'])} tier pricings")
                return None
            else:
                logger.info(f"Retrieved base price from API: £{base_price}")
                return base_price
                
        except requests.exceptions.HTTPError as e:
            if e.response:
                if e.response.status_code == 415:
                    logger.error(f"Pricing API returned 415 Unsupported Media Type")
                    logger.error("API requires Content-Type: application/json and empty JSON body")
                elif e.response.status_code == 400:
                    error_data = e.response.json() if e.response.content else {}
                    logger.error(f"Pricing API returned 400 Bad Request: {error_data}")
                else:
                    logger.error(f"Pricing API returned {e.response.status_code}: {e.response.text[:200]}")
            else:
                logger.error(f"HTTP error calling pricing API: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling pricing API: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing pricing API response: {e}")
            import traceback
            logger.error(traceback.format_exc())
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
    
    def _get_default_base_price_for_product(self, product: str) -> Optional[float]:
        """
        Get a default base price for a product type when specific selections aren't available
        
        Args:
            product: Product type (e.g., "blankets", "canvas")
            
        Returns:
            Default base price or None
        """
        # Use first available ProductReferenceCode for this product as fallback
        default_refs = {
            "blankets": "BlanketSherpafleece_25x20",
            "canvas": "Canvas_F18_10x10",
            "photobooks": "PB_CailuxCover_8x6_Black_20pp",
            "mugs": "Mug_Basic_White_PackOf2",
        }
        
        if product in default_refs:
            return get_base_price_from_mapping(default_refs[product])
        
        return None
    
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
        logger.info(f"🔍 get_bulk_price_info called: selections={selections}, quantity={quantity}, offer_type={offer_type}")
        logger.info(f"🔍 get_base_price_from_mapping available: {get_base_price_from_mapping is not None}")
        
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
        
        # If ProductReferenceCode not found, try to use a default base price for the product
        if not product_reference_code:
            logger.warning(f"Could not get ProductReferenceCode from selections: {selections}")
            logger.info(f"Missing fields - product: {selections.get('product')}, fabric: {selections.get('fabric')}, size: {selections.get('size')}")
            
            # Try to get a default base price for the product type
            product = selections.get("product")
            fabric_or_type = selections.get("fabric") or selections.get("cover") or selections.get("type")
            
            if product:
                # If fabric/type is selected but size is missing, use default size for that fabric/type
                if fabric_or_type and product == "blankets":
                    # Use medium size (30x40) as default for the selected fabric
                    default_size_for_fabric = {
                        "fabric_fleece": "size_med_30x40",  # BlanketFlannelfleece_30x40
                        "fabric_mink_touch": "size_med_30x40",  # BlanketPolarfleece_30x40
                        "fabric_sherpa": "size_med_30x40",  # BlanketSherpafleece_30x40
                        "fabric_double_sided": "size_med_30x40",  # DoubleSideBlanketFlannel_30x40
                    }
                    
                    if fabric_or_type in default_size_for_fabric:
                        # Try to get ProductReferenceCode with default size
                        selections_with_default_size = selections.copy()
                        selections_with_default_size["size"] = default_size_for_fabric[fabric_or_type]
                        product_reference_code = self.get_product_reference_code(selections_with_default_size)
                        
                        if product_reference_code:
                            logger.info(f"Using default size ({default_size_for_fabric[fabric_or_type]}) for fabric {fabric_or_type}")
                            logger.info(f"ProductReferenceCode with default size: {product_reference_code}")
                            result["product_reference_code"] = product_reference_code
                        else:
                            logger.warning(f"Could not get ProductReferenceCode even with default size for {fabric_or_type}")
                
                # If still no ProductReferenceCode, use generic product default
                if not product_reference_code:
                    # Use first available ProductReferenceCode for this product as fallback
                    # This allows us to show pricing even without specific fabric/size
                    default_base_price = self._get_default_base_price_for_product(product)
                    if default_base_price:
                        logger.info(f"Using default base price for product {product}: £{default_base_price}")
                        # Continue with discount lookup using a default ProductReferenceCode
                        # For blankets, use a common one like Sherpa Baby
                        if product == "blankets":
                            product_reference_code = "BlanketSherpafleece_25x20"
                        elif product == "canvas":
                            product_reference_code = "Canvas_F18_10x10"
                        elif product == "photobooks":
                            product_reference_code = "PB_CailuxCover_8x6_Black_20pp"
                        elif product == "mugs":
                            product_reference_code = "Mug_Basic_White_PackOf2"
                        
                        if product_reference_code:
                            result["product_reference_code"] = product_reference_code
                            logger.info(f"Using default ProductReferenceCode: {product_reference_code} for pricing estimate")
                    else:
                        result["error_message"] = "Product reference code not found (missing fabric/size selections?)"
                        return result
            else:
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
        
        # If Supabase is not configured or discount not found, use a default discount
        # This allows pricing to work even without Supabase configured
        if discount_percent is None:
            logger.warning(f"Discount not found in Supabase for {product_reference_code} (PricePoint {price_point_id})")
            logger.warning("Supabase may not be configured. Using default discount for pricing estimate.")
            # Use a default discount percentage (e.g., 15% as a reasonable bulk discount)
            # This allows us to show pricing even if Supabase is unavailable
            discount_percent = 15.0  # Default 15% bulk discount
            result["discount_percent"] = discount_percent
            logger.info(f"Using default discount: {discount_percent}% for pricing calculation")
        
        # Get base price - try multiple sources in order:
        # 1. CSV file (PRIMARY - loaded from ProductPage table, no network needed)
        # 2. External API (fallback - constantly updated)
        # 3. Local mapping file (fallback - static prices)
        # 4. Supabase (fallback - if column exists)
        base_price = None
        
        # PRIMARY: Try CSV first (most reliable source, no network connection needed)
        logger.info(f"🔄 Attempting to get base price from CSV (PRIMARY) for {product_reference_code}")
        base_price = self.get_base_price_from_csv(product_reference_code)
        if base_price is not None:
            logger.info(f"✅ Retrieved base price from CSV: £{base_price}")
        else:
            logger.warning("⚠️ CSV did not return base price, trying fallbacks...")
        
        # FALLBACK 1: External API if CSV didn't work
        if base_price is None:
            # First try to get productPageId from Supabase (using Guid column)
            if not product_page_id:
                product_page_id = self.get_product_page_id_from_supabase(product_reference_code)
            
            # Fallback to hardcoded mapping if Supabase doesn't have it
            if not product_page_id:
                product_page_id = get_product_page_id(selections)
                if not product_page_id:
                    logger.warning(f"Could not get productPageId from Supabase or hardcoded mapping for selections: {selections}")
                    logger.info(f"Missing required fields - product: {selections.get('product')}, fabric: {selections.get('fabric')}, size: {selections.get('size')}")
            
            if product_page_id:
                logger.info(f"🔄 Attempting to get base price from API (fallback) with productPageId: {product_page_id}")
                base_price = self.get_base_price_from_api(selections, product_page_id, product_reference_code)
                if base_price is not None:
                    logger.info(f"✅ Retrieved base price from API: £{base_price}")
                else:
                    logger.warning("⚠️ API did not return base price, trying more fallbacks...")
            else:
                logger.warning("⚠️ Cannot get base price from API - productPageId not available, trying more fallbacks...")
        
        # FALLBACK 2: Local mapping file if SQL Server and API didn't work
        if base_price is None:
            if get_base_price_from_mapping is None:
                logger.error("❌ bulk_base_prices module not imported - file may be missing on Railway")
            else:
                try:
                    base_price = get_base_price_from_mapping(product_reference_code)
                    if base_price is not None:
                        logger.info(f"✅ Found base price from local mapping (fallback) for {product_reference_code}: £{base_price}")
                    else:
                        logger.warning(f"❌ No base price found in mapping for {product_reference_code}")
                except Exception as e:
                    logger.error(f"❌ Error getting base price from mapping: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
        
        # FALLBACK 3: Supabase if SQL Server, API, and mapping didn't work
        if base_price is None:
            logger.info("🔄 Attempting to get base price from Supabase (fallback)")
            base_price = self.get_base_price_from_supabase(product_reference_code)
            if base_price is not None:
                logger.info(f"✅ Found base price from Supabase (fallback): £{base_price}")
        
        result["base_price"] = base_price
        
        # If we have both discount and base price, calculate totals
        if base_price is not None:
            unit_price = base_price * (1 - discount_percent / 100)
            total_price = self.calculate_bulk_price(base_price, discount_percent, quantity)
            
            result["unit_price"] = unit_price
            result["total_price"] = total_price
            result["formatted_unit_price"] = self.format_price_gbp(unit_price)
            result["formatted_total_price"] = self.format_price_gbp(total_price)
            result["success"] = True
            
            logger.info(f"✅ PRICING CALCULATED: base_price=£{base_price}, unit_price=£{unit_price}, total_price=£{total_price}")
        else:
            # We have discount but no base price - can still show discount percentage
            result["success"] = True  # Partial success - can show discount
            result["error_message"] = "Base price unavailable, showing discount only"
            logger.warning(f"❌ NO BASE PRICE: base_price=None, discount_percent={discount_percent}, product_reference_code={product_reference_code}")
        
        logger.info(f"🔍 FINAL RESULT: success={result['success']}, base_price={result['base_price']}, total_price={result['total_price']}")
        return result


# Global instance
bulk_pricing_service = BulkPricingService()

