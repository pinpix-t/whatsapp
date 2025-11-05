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
    # Blankets - Fleece
    "BlanketFlannelfleece_25x20": 19.99,  # Baby size
    "BlanketFlannelfleece_30x40": 29.99,  # Medium size
    "BlanketFlannelfleece_50x60": 39.99,  # Throw size
    "BlanketFlannelfleece_60x80": 49.99,  # Queen size
    
    # Blankets - Polar/Mink Touch
    "BlanketPolarfleece_25x20": 24.99,
    "BlanketPolarfleece_30x40": 34.99,
    "BlanketPolarfleece_50x60": 44.99,
    "BlanketPolarfleece_60x80": 54.99,
    
    # Blankets - Sherpa
    "BlanketSherpafleece_25x20": 24.99,
    "BlanketSherpafleece_30x40": 34.99,
    "BlanketSherpafleece_50x60": 44.99,
    "BlanketSherpafleece_60x80": 54.99,
    
    # Blankets - Double Sided
    "DoubleSideBlanketFlannel_25x20": 29.99,
    "DoubleSideBlanketFlannel_30x40": 39.99,
    "DoubleSideBlanketFlannel_50x60": 49.99,
    "DoubleSideBlanketFlannel_60x80": 59.99,
    
    # Canvas
    "Canvas_F18_10x10": 19.99,
    "Canvas_F18_12x12": 24.99,
    "Canvas_F18_16x20": 34.99,
    "Canvas_F18_30x40": 69.99,
    
    # Photo Books - Hard Cover
    "PB_CailuxCover_8x6_Black_20pp": 19.99,
    "PB_CailuxCover_8x8_Black_20pp": 24.99,
    "PB_CailuxCover_11x11_Black_20pp": 34.99,
    "PB_PhotoHardCover_12x8_50pp": 49.99,
    
    # Photo Books - Leather Cover
    "PB_LeatherCover_8x6_60pp": 39.99,
    "PB_LeatherCover_8x8_100pp": 59.99,
    "PB_LeatherCover_12x8_50pp": 54.99,
    "PB_LeatherCover_11x11_100pp": 69.99,
    
    # Mugs
    "Mug_Basic_White_PackOf2": 24.99,
    "Mug_Basic20oz_White_PackOf2": 29.99,
    
    # Other Products
    "Cal_WallSS_12x17": 14.99,
    "Frame_Wooden_12x8_Oak_PackOf3": 39.99,
    "BoxedPuzzle_Board_15x11": 19.99,
    "Slate_Rect_12x12": 29.99,
    "MouseMat": 12.99,
    "CushionPolyester_18x12": 24.99,
    "MetalPrint_12x12": 49.99,
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

