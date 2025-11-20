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
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from database.redis_store import redis_store
from bot.whatsapp_api import WhatsAppAPI

logger = logging.getLogger(__name__)


class ImageCreationService:
    """Service for handling image creation flow"""
    
    # Bearer token for API authentication
    BEARER_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXkiOiJwdWJsaWNBY2Nlc3NUb2tlbiIsInJvbGUiOiJwdWJsaWMiLCJnZW5lcmF0ZWRfYXQiOiIyMDI1LTA4LTI3VDEyOjM5OjEzLjk0OFoiLCJpYXQiOjE3NTYyOTgzNTMsImV4cCI6MjA3MTg3NDM1M30.h-DKZkhoBEgw1qZ4Gg2Lk20d9VP6JAbDUKX21xbMUVs"
    
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
    
    def _get_api_domain(self, region: str) -> str:
        """Map region to API domain"""
        domain_map = {
            "UK": "https://services.printerpix.co.uk",
            "US": "https://services.printerpix.com",
            "FR": "https://services.printerpix.fr",
            "ES": "https://services.printerpix.es",
            "IT": "https://services.printerpix.it",
            "NL": "https://services.printerpix.nl",
            "DE": "https://services.printerpix.de",
            "AE": "https://services.printerpix.ae",
            "IN": "https://services.printerpix.in"
        }
        return domain_map.get(region, "https://services.printerpix.co.uk")  # Default to UK
    
    def _extract_s3key_from_url(self, url: str) -> str:
        """Extract s3key from URL if possible, otherwise use placeholder"""
        # Try to extract from ucarecdn.com URLs
        # Pattern: https://ucarecdn.com/{s3key}/
        # s3key can be a path like "4/9bhd/25u2ij/7a855573-7cf3-435c-bc31-94aa85e01a7b"
        match = re.search(r'ucarecdn\.com/([^/]+(?:/[^/]+)*)/', url)
        if match:
            # Return the full path as s3key
            s3key = match.group(1)
            # Remove trailing slash if present
            s3key = s3key.rstrip('/')
            return s3key
        
        # Try simpler pattern if first one didn't match
        match = re.search(r'ucarecdn\.com/([^/]+)/', url)
        if match:
            return match.group(1)
        
        # If no match, try to extract from URL path
        # This is a fallback - API might accept it or might need actual s3key
        if 'ucarecdn.com' in url:
            # Extract everything after ucarecdn.com/
            parts = url.split('ucarecdn.com/')
            if len(parts) > 1:
                s3key = parts[1].split('/')[0]  # Get first part
                return s3key.rstrip('/')
        
        # Last resort: use filename or placeholder
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
    
    async def _upload_to_ucarecdn(self, image_bytes: bytes, filename: str = "image.jpg") -> Tuple[str, str]:
        """
        Upload image to Uploadcare CDN and get permanent URL
        
        Args:
            image_bytes: Image file bytes
            filename: Original filename (optional)
            
        Returns:
            Tuple of (public_url, s3key)
        """
        try:
            # Uploadcare public upload endpoint
            upload_url = "https://upload.uploadcare.com/base/"
            
            # Prepare multipart form data
            files = {
                'file': (filename, image_bytes, 'image/jpeg')
            }
            
            logger.info(f"📤 Uploading image to Uploadcare ({len(image_bytes)} bytes)...")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(upload_url, files=files)
                response.raise_for_status()
                
                # Uploadcare returns the file UUID
                file_uuid = response.text.strip()
                logger.info(f"✅ Uploaded to Uploadcare, UUID: {file_uuid}")
                
                # Construct public URL
                public_url = f"https://ucarecdn.com/{file_uuid}/"
                
                # Extract s3key (for Uploadcare, the UUID is typically the s3key)
                # But we might need to construct it based on Uploadcare's structure
                s3key = file_uuid
                
                logger.info(f"✅ Got public URL: {public_url}")
                logger.info(f"✅ Extracted s3key: {s3key}")
                
                return public_url, s3key
                
        except httpx.TimeoutException:
            logger.error("⏱️ Timeout uploading to Uploadcare")
            raise Exception("Image upload timed out. Please try again.")
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Uploadcare API error: {e.response.status_code} - {e.response.text[:200]}")
            raise Exception(f"Failed to upload image: {e.response.status_code}")
        except Exception as e:
            logger.error(f"❌ Error uploading to Uploadcare: {e}", exc_info=True)
            raise Exception(f"Failed to upload image: {str(e)}")
    
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
        logger.info(f"🖼️ handle_image called for user {user_id}, media_id: {media_id}")
        try:
            # Update state to processing
            self.redis_store.set_image_creation_state(
                user_id,
                "processing",
                {"media_id": media_id}
            )
            logger.info(f"✅ State set to processing for user {user_id}")
            
            # Send processing message
            await self.whatsapp_api.send_message(
                user_id,
                "⏳ Processing your image... This may take a moment."
            )
            logger.info(f"✅ Processing message sent to user {user_id}")
            
            # Get media URL from WhatsApp
            logger.info(f"📥 Getting media URL from WhatsApp for media_id: {media_id}")
            media_url = await self.whatsapp_api.get_media_url(media_id)
            logger.info(f"📥 Media URL received: {media_url[:100] if media_url else 'None'}...")
            
            if not media_url:
                raise Exception("Failed to get media URL from WhatsApp")
            
            # Download image from WhatsApp
            logger.info(f"📥 Downloading image from WhatsApp...")
            image_bytes = await self.whatsapp_api.download_media(media_url)
            
            if not image_bytes:
                raise Exception("Failed to download image from WhatsApp")
            
            logger.info(f"✅ Downloaded image ({len(image_bytes)} bytes)")
            
            # Upload image to Uploadcare CDN to get permanent URL
            logger.info(f"📤 Uploading image to CDN...")
            public_url, s3key = await self._upload_to_ucarecdn(image_bytes, "whatsapp_image.jpg")
            logger.info(f"✅ Image uploaded to CDN: {public_url}")
            logger.info(f"🔑 Extracted s3key: {s3key[:50]}...")
            
            # Get region from user's phone number
            region = self.get_region_from_phone_number(user_id)
            logger.info(f"🌍 Detected region: {region} for user {user_id}")
            
            # Process all target products
            logger.info(f"🚀 Starting to process all products for user {user_id}")
            await self._process_all_products(user_id, public_url, s3key, region)
            logger.info(f"✅ Finished processing all products for user {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Error handling image for user {user_id}: {e}", exc_info=True)
            error_message = str(e)[:200] if len(str(e)) > 200 else str(e)
            await self.whatsapp_api.send_message(
                user_id,
                f"❌ Sorry, I encountered an error processing your image: {error_message}. Please try again or contact support."
            )
            self.redis_store.clear_image_creation_state(user_id)
    
    async def _process_all_products(self, user_id: str, image_url: str, s3key: str, region: str) -> None:
        """Process image through all target products"""
        logger.info(f"🔥 _process_all_products CALLED for user {user_id}")
        logger.info(f"🔥 Image URL: {image_url[:100] if image_url else 'None'}...")
        logger.info(f"🔥 S3Key: {s3key[:50] if s3key else 'None'}...")
        logger.info(f"🔥 Region: {region}")
        logger.info(f"🔥 Target products: {self.target_products is not None}, Count: {len(self.target_products) if self.target_products is not None else 0}")
        
        if self.target_products is None or len(self.target_products) == 0:
            logger.error(f"❌ No target products available!")
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
        
        # Limit to first 10 products for initial testing to avoid long waits
        max_products = 10
        if total_products > max_products:
            logger.info(f"Limiting to first {max_products} products for testing")
            product_list = self.target_products.head(max_products).to_dict('records')
            total_products = max_products
        else:
            product_list = self.target_products.to_dict('records')
        
        # Send initial progress
        logger.info(f"Sending initial progress message to user {user_id}")
        await self.whatsapp_api.send_message(
            user_id,
            f"📊 Found {total_products} products. Processing now..."
        )
        logger.info(f"Initial progress message sent")
        
        processed = 0
        errors = 0
        
        # Process products one at a time with timeout to avoid hanging
        logger.info(f"Processing {len(product_list)} products (API calls may timeout)")
        
        # Process each product through the API
        for row in product_list:
            try:
                refcode = row.get('refcode', 'unknown')
                product_type = self._get_product_type_from_refcode(refcode)
                
                # Extract dimensions from CSV row
                width = int(row.get('width', 0)) if pd.notna(row.get('width')) else 0
                height = int(row.get('height', 0)) if pd.notna(row.get('height')) else 0
                thickness = int(row.get('thickness', 0)) if pd.notna(row.get('thickness')) else 0
                
                # Build payload in new API format
                payload = {
                    "productType": product_type,
                    "refcode": refcode,
                    "width": width,
                    "height": height,
                    "thickness": thickness,
                    "images": [
                        {
                            "url": image_url,
                            "s3key": s3key
                        }
                    ]
                }
                
                # Call API for this product
                result = await self._process_single_product(payload, row, region)
                
                if result:
                    # Categorize product by type
                    if 'FloatFrame' in refcode:
                        results["framed_canvas"].append(result)
                    elif product_type in results:
                        results[product_type].append(result)
                    processed += 1
                else:
                    errors += 1
                    logger.warning(f"Failed to process product {refcode}")
                
                # Progress update every 5 products
                if processed % 5 == 0:
                    await self.whatsapp_api.send_message(
                        user_id,
                        f"⏳ Processing... {processed}/{total_products} products"
                    )
                    logger.info(f"Progress: {processed}/{total_products}")
                    
            except Exception as e:
                logger.error(f"Error processing product {row.get('refcode', 'unknown')}: {e}", exc_info=True)
                errors += 1
            
        
        # Format and send results
        logger.info(f"Finished processing: {processed} products, {errors} errors")
        if processed > 0:
            await self._send_results(user_id, results, processed, errors)
        else:
            await self.whatsapp_api.send_message(
                user_id,
                "❌ Could not process any products. The API may be unavailable. Please try again later."
            )
        
        # Clear state
        self.redis_store.set_image_creation_state(
            user_id,
            "completed",
            {"processed": processed, "errors": errors}
        )
    
    async def _process_single_product(self, payload: dict, row: dict, region: str) -> Optional[dict]:
        """Process a single product and return result"""
        try:
            response = await self._call_product_api(payload, region)
            if response and response.get("success", False):
                product_type = self._get_product_type_from_refcode(payload['refcode'])
                return {
                    "product_type": product_type,
                    "refcode": payload['refcode'],
                    "response": response
                }
            return None
        except Exception as e:
            logger.error(f"Error processing product {payload.get('refcode', 'unknown')}: {e}")
            return None
    
    async def _call_product_api(self, payload: dict, region: str) -> Optional[dict]:
        """Call the product API with region-specific domain"""
        # Get the correct domain for the region
        api_domain = self._get_api_domain(region)
        url = f"{api_domain}/api/v1/product/wa/detail"
        refcode = payload.get('refcode', 'unknown')
        
        # Prepare headers with Bearer token
        headers = {
            "Authorization": f"Bearer {self.BEARER_TOKEN}",
            "Content-Type": "application/json"
        }
        
        try:
            logger.info(f"Calling API for {refcode} on {api_domain}")
            async with httpx.AsyncClient(timeout=8.0) as client:  # Reduced timeout to 8s
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                logger.info(f"✅ API success for {refcode}")
                return {"success": True, "data": data}
        except httpx.TimeoutException:
            logger.warning(f"⏱️ API timeout for {refcode} (8s)")
            return {"success": False, "error": "timeout"}
        except httpx.ConnectError as e:
            logger.error(f"🔌 Connection error for {refcode}: {e}")
            return {"success": False, "error": "connection_error"}
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ API HTTP error for {refcode}: {e.response.status_code} - {e.response.text[:200]}")
            return {"success": False, "error": f"http_{e.response.status_code}"}
        except Exception as e:
            logger.error(f"❌ API exception for {refcode}: {e}")
            return {"success": False, "error": str(e)}
    
    async def _send_results(self, user_id: str, results: dict, processed: int, errors: int) -> None:
        """Format and send results to user"""
        message_parts = ["🎨 Here are your products with your photo:\n"]
        
        # Helper function to extract preview URL from API response
        def get_preview_url(item):
            """Extract preview image URL from API response if available"""
            try:
                response_data = item.get('response', {})
                if isinstance(response_data, dict):
                    data = response_data.get('data', {})
                    # Check for common preview URL fields
                    if isinstance(data, dict):
                        # Look for preview, image, url, or previewUrl fields
                        for key in ['preview', 'previewUrl', 'image', 'url', 'preview_image']:
                            if key in data and data[key]:
                                return data[key]
                        # Check if data has nested structure
                        if 'preview' in data and isinstance(data['preview'], dict):
                            return data['preview'].get('url') or data['preview'].get('image')
            except Exception as e:
                logger.debug(f"Could not extract preview URL: {e}")
            return None
        
        # Canvas Prints
        if results["canvas"]:
            message_parts.append(f"📸 Canvas Prints ({len(results['canvas'])}):")
            for item in results["canvas"][:5]:  # Show first 5
                refcode = item.get('refcode', 'unknown')
                preview_url = get_preview_url(item)
                if preview_url:
                    message_parts.append(f"• {refcode} - Preview: {preview_url}")
                else:
                    message_parts.append(f"• {refcode}")
            if len(results["canvas"]) > 5:
                message_parts.append(f"... and {len(results['canvas']) - 5} more")
            message_parts.append("")
        
        # Photo Cushions
        if results["cushion"]:
            message_parts.append(f"🛋️ Photo Cushions ({len(results['cushion'])}):")
            for item in results["cushion"][:5]:
                refcode = item.get('refcode', 'unknown')
                preview_url = get_preview_url(item)
                if preview_url:
                    message_parts.append(f"• {refcode} - Preview: {preview_url}")
                else:
                    message_parts.append(f"• {refcode}")
            if len(results["cushion"]) > 5:
                message_parts.append(f"... and {len(results['cushion']) - 5} more")
            message_parts.append("")
        
        # Metal Prints
        if results["metal"]:
            message_parts.append(f"🔩 Metal Prints ({len(results['metal'])}):")
            for item in results["metal"][:5]:
                refcode = item.get('refcode', 'unknown')
                preview_url = get_preview_url(item)
                if preview_url:
                    message_parts.append(f"• {refcode} - Preview: {preview_url}")
                else:
                    message_parts.append(f"• {refcode}")
            if len(results["metal"]) > 5:
                message_parts.append(f"... and {len(results['metal']) - 5} more")
            message_parts.append("")
        
        # Photo Posters
        if results["poster"]:
            message_parts.append(f"📰 Photo Posters ({len(results['poster'])}):")
            for item in results["poster"][:5]:
                refcode = item.get('refcode', 'unknown')
                preview_url = get_preview_url(item)
                if preview_url:
                    message_parts.append(f"• {refcode} - Preview: {preview_url}")
                else:
                    message_parts.append(f"• {refcode}")
            if len(results["poster"]) > 5:
                message_parts.append(f"... and {len(results['poster']) - 5} more")
            message_parts.append("")
        
        # Framed Canvas
        if results["framed_canvas"]:
            message_parts.append(f"🖼️ Framed Canvas ({len(results['framed_canvas'])}):")
            for item in results["framed_canvas"][:5]:
                refcode = item.get('refcode', 'unknown')
                preview_url = get_preview_url(item)
                if preview_url:
                    message_parts.append(f"• {refcode} - Preview: {preview_url}")
                else:
                    message_parts.append(f"• {refcode}")
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

