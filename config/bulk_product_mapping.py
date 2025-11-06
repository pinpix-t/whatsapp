"""
Product selection to ProductReferenceCode mapping table
Maps user selections (product + fabric/type + size) to ProductReferenceCode format
used in Supabase lookup table (e.g., "BlanketSherpafleece_25x20")
"""

# Mapping structure: product -> fabric/type -> size -> ProductReferenceCode
PRODUCT_REFERENCE_MAPPING = {
    "blankets": {
        "fabric_fleece": {
            "size_baby_20x25": "BlanketFlannelfleece_25x20",
            "size_med_30x40": "BlanketFlannelfleece_30x40",
            "size_throw_50x60": "BlanketFlannelfleece_50x60",
            "size_queen_60x80": "BlanketFlannelfleece_60x80",
        },
        "fabric_mink_touch": {
            # Using Polar fleece as closest match (Mink Touch may not exist in CSV)
            "size_baby_20x25": "BlanketPolarfleece_25x20",
            "size_med_30x40": "BlanketPolarfleece_30x40",
            "size_throw_50x60": "BlanketPolarfleece_50x60",
            "size_queen_60x80": "BlanketPolarfleece_60x80",
        },
        "fabric_sherpa": {
            "size_baby_20x25": "BlanketSherpafleece_25x20",
            "size_med_30x40": "BlanketSherpafleece_30x40",
            "size_throw_50x60": "BlanketSherpafleece_50x60",
            "size_queen_60x80": "BlanketSherpafleece_60x80",
        },
        "fabric_double_sided": {
            # Using DoubleSideBlanketFlannel (could also use DoubleSideBlanketPolar)
            "size_baby_20x25": "DoubleSideBlanketFlannel_25x20",
            "size_med_30x40": "DoubleSideBlanketFlannel_30x40",
            "size_throw_50x60": "DoubleSideBlanketFlannel_50x60",
            "size_queen_60x80": "DoubleSideBlanketFlannel_60x80",
        },
    },
    "canvas": {
        "default": {
            "size_6x6": "Canvas_F18_10x10",  # Using closest match (6x6 not in CSV)
            "size_10x10": "Canvas_F18_10x10",
            "size_12x12": "Canvas_F18_12x12",
            "size_11x14": "Canvas_F18_12x8",  # Using closest match (11x14 not in CSV)
            "size_16x20": "Canvas_F18_16x20",
            "size_36x24": "Canvas_F18_24x24",  # Using closest match (36x24 not in CSV)
            "size_30x40": "Canvas_F18_30x40",
        }
    },
    "photobooks": {
        "cover_hard_cover": {
            # Using CailuxCover as hard cover match
            "size_8x6": "PB_CailuxCover_8x6_Black_20pp",
            "size_8x8": "PB_CailuxCover_8x8_Black_20pp",
            "size_11x8_5": "PB_PhotoHardCover_12x8_50pp",  # Using closest match (11x8.5 not in CSV)
            "size_11x11": "PB_CailuxCover_11x11_Black_20pp",
        },
        "cover_leather_cover": {
            "size_8x6": "PB_LeatherCover_8x6_60pp",
            "size_8x8": "PB_LeatherCover_8x8_100pp",
            "size_11x8_5": "PB_LeatherCover_12x8_50pp",  # Using closest match (11x8.5 not in CSV)
            "size_11x11": "PB_LeatherCover_11x11_100pp",
        },
    },
    "mugs": {
        "default": {
            "type_classic_mug": "Mug_Basic_White_PackOf2",
            "type_magic_mug": "Mug_Basic_White_PackOf2",  # Using same as classic
            "type_latte_mug": "Mug_Basic20oz_White_PackOf2",
            "type_magic_latte_mug": "Mug_Basic20oz_White_PackOf2",  # Using same as latte
        }
    },
    # Other products (simpler mapping)
    "wall_calendar": {
        "default": {
            "default": "Cal_WallSS_12x17"
        }
    },
    "photo_frame": {
        "default": {
            "default": "Frame_Wooden_12x8_Oak_PackOf3"
        }
    },
    "jigsaw": {
        "default": {
            "default": "BoxedPuzzle_Board_15x11"
        }
    },
    "photo_slate": {
        "default": {
            "default": "Slate_Rect_12x12"
        }
    },
    "mouse_mat": {
        "default": {
            "default": "MouseMat"
        }
    },
    "photo_cushion": {
        "default": {
            "default": "CushionPolyester_18x12"
        }
    },
    "metal_photo": {
        "default": {
            "default": "MetalPrint_12x12"
        }
    },
}


def get_product_reference_code(selections: dict) -> str:
    """
    Get ProductReferenceCode from user selections
    
    Args:
        selections: Dictionary with product selections (product, fabric/type, size, etc.)
        
    Returns:
        ProductReferenceCode string or None if not found
    """
    product = selections.get("product")
    if not product or product not in PRODUCT_REFERENCE_MAPPING:
        return None
    
    product_mapping = PRODUCT_REFERENCE_MAPPING[product]
    
    # Handle products with fabric/type selection (blankets, photobooks)
    fabric_or_type = selections.get("fabric") or selections.get("cover") or selections.get("type")
    
    if fabric_or_type and fabric_or_type in product_mapping:
        # Product has fabric/type selection
        size_mapping = product_mapping[fabric_or_type]
        size = selections.get("size") or selections.get("type")
        if size and size in size_mapping:
            return size_mapping[size]
    elif "default" in product_mapping:
        # Product uses default mapping (canvas, mugs, other products)
        default_mapping = product_mapping["default"]
        size = selections.get("size") or selections.get("type")
        if size and size in default_mapping:
            return default_mapping[size]
        elif "default" in default_mapping:
            # Product has no size variations
            return default_mapping["default"]
    
    return None

