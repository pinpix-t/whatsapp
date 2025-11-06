"""
Base price mapping for bulk products
Maps ProductReferenceCode to base price in GBP

This is used as a fallback when base prices aren't in Supabase.
To update: Add or modify ProductReferenceCode -> base_price mappings below.
"""

from typing import Optional

# Base price mapping: ProductReferenceCode -> base price in GBP
# Prices should be the regular retail price before any bulk discounts
BASE_PRICE_MAPPING = {
    # Blankets - Prices from Excel files
    # Blankets - Fleece
    "BlanketFlannelfleece_25x20": 39.90,
    "BlanketFlannelfleece_30x40": 79.90,
    "BlanketFlannelfleece_50x60": 89.90,
    "BlanketFlannelfleece_60x80": 109.90,
    # Blankets - Polar/Mink Touch
    "BlanketPolarfleece_25x20": 34.90,
    "BlanketPolarfleece_30x40": 74.90,
    "BlanketPolarfleece_50x60": 84.90,
    "BlanketPolarfleece_60x80": 104.90,
    # Blankets - Sherpa
    "BlanketSherpafleece_25x20": 79.90,
    "BlanketSherpafleece_30x40": 119.90,
    "BlanketSherpafleece_50x60": 129.90,
    "BlanketSherpafleece_60x80": 159.90,
    # Photo Books - Hard Cover (Photo Hardcover)
    "PB_CailuxCover_8x6_Black_20pp": 29.95,  # A5 21x15cm
    "PB_CailuxCover_8x8_Black_20pp": 69.95,  # Square 27x27
    "PB_CailuxCover_11x11_Black_20pp": 69.95,  # Square 27x27
    "PB_PhotoHardCover_12x8_50pp": 44.95,  # A4
    # Photo Books - Soft Cover
    "PB_SoftCover_12x8_20pp": 35.95,
    "PB_SoftCover_8x12_20pp": 35.95,
    "PB_SoftCover_8x6_20pp": 19.95,
    "PB_SoftCover_8x8_20pp": 29.95,
    # Photo Books - Leather Cover (Luxury layflat)
    "PB_LeatherCover_8x6_60pp": 269.95,  # Luxury layflat square
    "PB_LeatherCover_8x8_100pp": 269.95,  # Luxury layflat square
    "PB_LeatherCover_12x8_50pp": 319.95,  # Luxury layflat A4
    "PB_LeatherCover_11x11_100pp": 369.95,  # Luxury layflat bigger square
    # Calendars
    "Cal_Double_12x8": 34.26,
    "Cal_Double_17x12": 51.40,
    "Cal_Double_8x6": 28.54,
    "Cal_Kitchen_5x12": 19.97,
    "Cal_Kitchen_5x17": 31.40,
    "Cal_WallSS_12x17": 49.95,
    "Cal_WallSS_6x8": 19.95,
    "Cal_WallSS_8x12": 29.95,
    "Cal_Wall_12x17": 39.97,
    "Cal_Wall_6x8": 15.95,
    "Cal_Wall_9x12": 23.30,
}


def get_base_price(product_reference_code: str) -> Optional[float]:
    """
    Get base price for a ProductReferenceCode
    
    Args:
        product_reference_code: ProductReferenceCode string
        
    Returns:
        Base price in GBP or None if not found
    """
    return BASE_PRICE_MAPPING.get(product_reference_code)

