"""
Image Creation Service
Handles image processing and product preview generation
"""

import logging
import pandas as pd
import httpx
import re
import time
import asyncio
from typing import Dict, List, Optional
from pathlib import Path
from database.redis_store import redis_store
from bot.whatsapp_api import WhatsAppAPI

logger = logging.getLogger(__name__)


class ImageCreationService:
    """Service for handling image creation flow"""
    
    # API endpoint
    API_BASE_URL = "http://10.20.24.80:9201"
    
    def __init__(self, whatsapp_api: WhatsAppAPI):
        self.whatsapp_api = whatsapp_api
        self.redis_store = redis_store
        self.dimensions_df = None
        self.target_products = None
        self._load_dimensions()
    
    def _load_dimensions(self):
        """Load and filter dimensions.csv to target products"""
        try:
            csv_path = Path("dimensions.csv")
            if not csv_path.exists():
                logger.error("dimensions.csv not found")
                return
            
            self.dimensions_df = pd.read_csv(csv_path)
            logger.info(f"Loaded {len(self.dimensions_df)} products from dimensions.csv")
            
            # Filter to 5 target product types
            # Canvas prints (exclude bundles/clusters)
            canvas = self.dimensions_df[
                (self.dimensions_df['platinumProductType'] == 4) & 
                (self.dimensions_df['refcode'].str.startswith('Canvas_', na=False)) &
                (~self.dimensions_df['refcode'].str.contains('Bundle|Cluster', na=False))
            ]
            
            # Photo cushion
            cushion = self.dimensions_df[
                (self.dimensions_df['platinumProductType'] == 373) | 
                (self.dimensions_df['refcode'].str.startswith('Cushion', na=False))
            ]
            
            # Metal print
            metal = self.dimensions_df[
                (self.dimensions_df['platinumProductType'] == 366) | 
                (self.dimensions_df['refcode'].str.startswith('MetalPrint', na=False))
            ]
            
            # Photo poster
            poster = self.dimensions_df[
                (self.dimensions_df['platinumProductType'] == 7) | 
                (self.dimensions_df['refcode'].str.startswith('Poster_', na=False))
            ]
            
            # Framed canvas
            framed_canvas = self.dimensions_df[
                (self.dimensions_df['platinumProductType'] == 4) & 
                (self.dimensions_df['refcode'].str.contains('FloatFrame', na=False))
            ]
            
            # Combine all target products and remove duplicates
            self.target_products = pd.concat([
                canvas, cushion, metal, poster, framed_canvas
            ]).drop_duplicates(subset=['refcode'])
            
            logger.info(f"Filtered to {len(self.target_products)} target products")
            
        except Exception as e:
            logger.error(f"Error loading dimensions.csv: {e}", exc_info=True)
            self.dimensions_df = None
            self.target_products = None
    
    def get_region_from_phone_number(self, phone_number: str) -> str:
        """Detect region from phone number"""
        # Remove + and spaces
        clean_number = phone_number.replace('+', '').replace(' ', '').replace('-', '')
        
        # Country code mappings
        if clean_number.startswith('44'):
            return "UK"
        elif clean_number.startswith('1'):
            return "US"
        elif clean_number.startswith('33'):
            return "FR"
        elif clean_number.startswith('34'):
            return "ES"
        elif clean_number.startswith('39'):
            return "IT"
        elif clean_number.startswith('31'):
            return "NL"
        elif clean_number.startswith('49'):
            return "DE"
        elif clean_number.startswith('971'):
            return "AE"
        elif clean_number.startswith('91'):
            return "IN"
        else:
            # Default to UK
            return "UK"
    
    def _extract_s3key_from_url(self, url: str) -> str:
        """Extract s3key from URL if possible, otherwise use placeholder"""
        # Try to extract from ucarecdn.com URLs
        # Pattern: https://ucarecdn.com/{s3key}/
        match = re.search(r'ucarecdn\.com/([^/]+)/', url)
        if match:
            return match.group(1)
        
        # If no match, use a placeholder based on URL hash
        # This is a fallback - API might accept it or might need actual s3key
        return url.split('/')[-1] if '/' in url else "placeholder_key"
    
    def _get_product_type_from_refcode(self, refcode: str) -> str:
        """Determine product type from refcode"""
        refcode_lower = refcode.lower()
        
        if 'floatframe' in refcode_lower:
            return "canvas"  # Framed canvas
        elif refcode_lower.startswith('canvas'):
            return "canvas"
        elif refcode_lower.startswith('cushion'):
            return "cushion"
        elif refcode_lower.startswith('metalprint'):
            return "metal"
        elif refcode_lower.startswith('poster'):
            return "poster"
        else:
            return "canvas"  # Default fallback
    
    async def start_image_creation(self, user_id: str) -> None:
        """Start the image creation flow - prompt user to send image"""
        # Clear any existing state
        self.redis_store.clear_image_creation_state(user_id)
        
        # Set state to waiting for image
        self.redis_store.set_image_creation_state(
            user_id,
            "waiting_for_image",
            {}
        )
        
        # Send prompt message
        await self.whatsapp_api.send_message(
            user_id,
            "🎨 Great! Please send me the image you'd like to use.\n\nI'll show you how it looks on:\n• Canvas Prints\n• Photo Cushions\n• Metal Prints\n• Photo Posters\n• Framed Canvas\n\n📸 Send your image now!"
        )
        logger.info(f"Started image creation flow for user {user_id}")
    
    async def handle_image(self, user_id: str, media_id: str) -> None:
        """Handle incoming image - download and process"""
        try:
            # Update state to processing
            self.redis_store.set_image_creation_state(
                user_id,
                "processing",
                {"media_id": media_id}
            )
            
            # Send processing message
            await self.whatsapp_api.send_message(
                user_id,
                "⏳ Processing your image... This may take a moment."
            )
            
            # Get media URL from WhatsApp
            media_url = await self.whatsapp_api.get_media_url(media_id)
            if not media_url:
                raise Exception("Failed to get media URL from WhatsApp")
            
            # Extract s3key (try to extract from URL, fallback to placeholder)
            s3key = self._extract_s3key_from_url(media_url)
            
            # Get region from user's phone number
            region = self.get_region_from_phone_number(user_id)
            logger.info(f"Detected region: {region} for user {user_id}")
            
            # Process all target products
            await self._process_all_products(user_id, media_url, s3key, region)
            
        except Exception as e:
            logger.error(f"Error handling image for user {user_id}: {e}", exc_info=True)
            await self.whatsapp_api.send_message(
                user_id,
                "❌ Sorry, I encountered an error processing your image. Please try again or contact support."
            )
            self.redis_store.clear_image_creation_state(user_id)
    
    async def _process_all_products(self, user_id: str, image_url: str, s3key: str, region: str) -> None:
        """Process image through all target products"""
        if self.target_products is None or len(self.target_products) == 0:
            await self.whatsapp_api.send_message(
                user_id,
                "❌ No products available. Please contact support."
            )
            return
        
        results = {
            "canvas": [],
            "cushion": [],
            "metal": [],
            "poster": [],
            "framed_canvas": []
        }
        
        total_products = len(self.target_products)
        logger.info(f"Processing {total_products} products for user {user_id}")
        
        # Limit to first 20 products for initial testing (can be increased later)
        max_products = 20
        if total_products > max_products:
            logger.info(f"Limiting to first {max_products} products for testing")
            product_list = self.target_products.head(max_products).to_dict('records')
            total_products = max_products
        else:
            product_list = self.target_products.to_dict('records')
        
        # Send initial progress
        await self.whatsapp_api.send_message(
            user_id,
            f"📊 Found {total_products} products. Processing now..."
        )
        
        processed = 0
        errors = 0
        
        # Process products in batches to avoid overwhelming the API
        batch_size = 5
        
        for batch_start in range(0, len(product_list), batch_size):
            batch = product_list[batch_start:batch_start + batch_size]
            batch_tasks = []
            
            for row in batch:
                try:
                    product_type = self._get_product_type_from_refcode(row['refcode'])
                    
                    # Prepare API payload
                    payload = {
                        "productType": product_type,
                        "refcode": row['refcode'],
                        "width": int(row['width']),
                        "height": int(row['height']),
                        "thickness": int(row['thickness']),
                        "images": [
                            {
                                "url": image_url,
                                "s3key": s3key
                            }
                        ],
                        "region": region
                    }
                    
                    # Create task for this product
                    task = self._process_single_product(payload, row)
                    batch_tasks.append(task)
                    
                except Exception as e:
                    logger.error(f"Error preparing product {row.get('refcode', 'unknown')}: {e}")
                    errors += 1
            
            # Process batch in parallel
            try:
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                for i, result in enumerate(batch_results):
                    if isinstance(result, Exception):
                        logger.error(f"Error in batch processing: {result}")
                        errors += 1
                    elif result:
                        row = batch[i]
                        refcode = row.get('refcode', 'unknown')
                        product_type = result.get('product_type')
                        
                        if 'FloatFrame' in refcode:
                            results["framed_canvas"].append({
                                "refcode": refcode,
                                "response": result.get('response')
                            })
                        elif product_type in results:
                            results[product_type].append({
                                "refcode": refcode,
                                "response": result.get('response')
                            })
                
                processed += len(batch)
                
                # Progress update after each batch
                await self.whatsapp_api.send_message(
                    user_id,
                    f"⏳ Processing... {processed}/{total_products} products done"
                )
                logger.info(f"Processed batch: {processed}/{total_products} products")
                
            except Exception as e:
                logger.error(f"Error processing batch: {e}", exc_info=True)
                errors += len(batch)
        
        # Format and send results
        await self._send_results(user_id, results, processed, errors)
        
        # Clear state
        self.redis_store.set_image_creation_state(
            user_id,
            "completed",
            {"processed": processed, "errors": errors}
        )
    
    async def _process_single_product(self, payload: dict, row: dict) -> Optional[dict]:
        """Process a single product and return result"""
        try:
            response = await self._call_product_api(payload)
            if response and response.get("success", False):
                product_type = self._get_product_type_from_refcode(payload['refcode'])
                return {
                    "product_type": product_type,
                    "response": response
                }
            return None
        except Exception as e:
            logger.error(f"Error processing product {payload.get('refcode', 'unknown')}: {e}")
            return None
    
    async def _call_product_api(self, payload: dict) -> Optional[dict]:
        """Call the product API"""
        url = f"{self.API_BASE_URL}/api/v1/product/wa/detail"
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:  # Reduced timeout to 10s
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return {"success": True, "data": data}
        except httpx.TimeoutException:
            logger.error(f"API timeout for {payload.get('refcode', 'unknown')}")
            return {"success": False, "error": "timeout"}
        except httpx.HTTPStatusError as e:
            logger.error(f"API error for {payload.get('refcode', 'unknown')}: {e.response.status_code}")
            return {"success": False, "error": f"http_{e.response.status_code}"}
        except Exception as e:
            logger.error(f"API exception for {payload.get('refcode', 'unknown')}: {e}")
            return {"success": False, "error": str(e)}
    
    async def _send_results(self, user_id: str, results: dict, processed: int, errors: int) -> None:
        """Format and send results to user"""
        message_parts = ["🎨 Here are your products with your photo:\n"]
        
        # Canvas Prints
        if results["canvas"]:
            message_parts.append(f"📸 Canvas Prints ({len(results['canvas'])}):")
            for item in results["canvas"][:5]:  # Show first 5
                message_parts.append(f"• {item['refcode']}")
            if len(results["canvas"]) > 5:
                message_parts.append(f"... and {len(results['canvas']) - 5} more")
            message_parts.append("")
        
        # Photo Cushions
        if results["cushion"]:
            message_parts.append(f"🛋️ Photo Cushions ({len(results['cushion'])}):")
            for item in results["cushion"][:5]:
                message_parts.append(f"• {item['refcode']}")
            if len(results["cushion"]) > 5:
                message_parts.append(f"... and {len(results['cushion']) - 5} more")
            message_parts.append("")
        
        # Metal Prints
        if results["metal"]:
            message_parts.append(f"🔩 Metal Prints ({len(results['metal'])}):")
            for item in results["metal"][:5]:
                message_parts.append(f"• {item['refcode']}")
            if len(results["metal"]) > 5:
                message_parts.append(f"... and {len(results['metal']) - 5} more")
            message_parts.append("")
        
        # Photo Posters
        if results["poster"]:
            message_parts.append(f"📰 Photo Posters ({len(results['poster'])}):")
            for item in results["poster"][:5]:
                message_parts.append(f"• {item['refcode']}")
            if len(results["poster"]) > 5:
                message_parts.append(f"... and {len(results['poster']) - 5} more")
            message_parts.append("")
        
        # Framed Canvas
        if results["framed_canvas"]:
            message_parts.append(f"🖼️ Framed Canvas ({len(results['framed_canvas'])}):")
            for item in results["framed_canvas"][:5]:
                message_parts.append(f"• {item['refcode']}")
            if len(results["framed_canvas"]) > 5:
                message_parts.append(f"... and {len(results['framed_canvas']) - 5} more")
            message_parts.append("")
        
        # Summary
        message_parts.append(f"✅ Processed {processed} products")
        if errors > 0:
            message_parts.append(f"⚠️ {errors} errors occurred")
        
        message = "\n".join(message_parts)
        
        # Send message (split if too long)
        if len(message) > 4000:  # WhatsApp limit
            # Send in chunks
            chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
            for chunk in chunks:
                await self.whatsapp_api.send_message(user_id, chunk)
        else:
            await self.whatsapp_api.send_message(user_id, message)


# Singleton pattern
_image_creation_service = None

def get_image_creation_service(whatsapp_api: WhatsAppAPI) -> ImageCreationService:
    """Get or create image creation service instance"""
    global _image_creation_service
    if _image_creation_service is None:
        _image_creation_service = ImageCreationService(whatsapp_api)
    return _image_creation_service

