"""
Region Lookup Service
Queries Supabase Region IDs table to get product_id and group_id for Freshdesk tickets
"""

import logging
from typing import Dict, Optional, Tuple
from supabase import create_client, Client
from config.settings import SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger(__name__)


class RegionLookupService:
    """Service for looking up region-specific IDs from Supabase"""
    
    def __init__(self):
        """Initialize Supabase client"""
        self.supabase: Optional[Client] = None
        if SUPABASE_URL and SUPABASE_KEY:
            try:
                self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
                logger.info("✓ Region Lookup Service: Supabase client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client for region lookup: {e}")
                self.supabase = None
        else:
            logger.warning("Region Lookup Service: Supabase credentials not configured")
    
    def get_region_ids(self, region: str) -> Tuple[Optional[int], Optional[int]]:
        """
        Get product_id and group_id for a region from Supabase Region IDs table
        
        Args:
            region: Region name (e.g., "UK", "US", "FR", etc.)
            
        Returns:
            Tuple of (product_id, group_id) as integers, or (None, None) if not found
        """
        if not self.supabase:
            logger.warning("Supabase not available, cannot lookup region IDs")
            return None, None
        
        if not region:
            logger.warning("Region not provided for lookup")
            return None, None
        
        try:
            # Query Supabase Region IDs table
            # Note: Table name might be "Region IDs" or "region_ids" - adjust as needed
            response = self.supabase.table("Region IDs").select("product_id, group_id").eq(
                "region", region.upper()
            ).execute()
            
            if response.data and len(response.data) > 0:
                row = response.data[0]
                product_id = row.get("product_id")
                group_id = row.get("group_id")
                
                # Convert to integers if they're not already
                if product_id is not None:
                    product_id = int(product_id)
                if group_id is not None:
                    group_id = int(group_id)
                
                logger.info(f"Found region IDs for {region}: product_id={product_id}, group_id={group_id}")
                return product_id, group_id
            
            logger.warning(f"No region IDs found for region: {region}")
            return None, None
            
        except Exception as e:
            logger.error(f"Error querying Supabase for region IDs: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None, None
    
    def get_region_from_postcode(self, postcode: str) -> str:
        """
        Determine region from UK postcode
        
        Args:
            postcode: UK postcode (e.g., "SW1A 1AA", "M1 1AA")
            
        Returns:
            Region string (default: "UK" for UK postcodes)
        """
        if not postcode:
            return "UK"  # Default to UK
        
        postcode_upper = postcode.upper().strip()
        
        # Basic UK postcode detection
        # UK postcodes typically start with 1-2 letters, followed by numbers
        # This is a simple heuristic - can be improved
        if len(postcode_upper) >= 5 and postcode_upper[0].isalpha():
            # Looks like a UK postcode
            return "UK"
        
        # For now, default to UK
        # Can be extended to detect other regions based on postcode patterns
        return "UK"

