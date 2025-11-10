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
            # Using PhotoHardCover (actual API product name)
            "size_8x6": "PB_PhotoHardCover_8x6_20pp",
            "size_8x8": "PB_PhotoHardCover_8x8_20pp",
            "size_11x8_5": "PB_PhotoHardCover_12x8_20pp",  # Using closest match (11x8.5 not in CSV)
            "size_11x11": "PB_PhotoHardCover_11x11_20pp",
        },
        "cover_leather_cover": {
            "size_8x6": "PB_LeatherCover_8x6_60pp",
            "size_8x8": "PB_LeatherCover_8x8_100pp",
            "size_11x8_5": "PB_LeatherCover_12x8_50pp",  # Using closest match (11x8.5 not in CSV)
            "size_11x11": "PB_LeatherCover_11x11_100pp",
        },
        "cover_layflat": {
            # Luxury layflat photobooks
            "size_8x6": "PBLayFlat_PhotoHardCover_8x6_20pp",  # If exists, otherwise use 8x8
            "size_8x8": "PBLayFlat_PhotoHardCover_8x8_20pp",
            "size_11x8_5": "PBLayFlat_PhotoHardCover_12x8_20pp",  # Using closest match
            "size_11x11": "PBLayFlat_PhotoHardCover_11x11_20pp",  # If exists, otherwise use 8x8
        },
        "cover_luxury_layflat": {
            # Alias for layflat
            "size_8x6": "PBLayFlat_PhotoHardCover_8x6_20pp",
            "size_8x8": "PBLayFlat_PhotoHardCover_8x8_20pp",
            "size_11x8_5": "PBLayFlat_PhotoHardCover_12x8_20pp",
            "size_11x11": "PBLayFlat_PhotoHardCover_11x11_20pp",
        },
        "cover_soft_cover": {
            # Softcover photobooks
            "size_8x6": "PB_SoftCover_8x6_20pp",
            "size_8x8": "PB_SoftCover_8x8_20pp",
            "size_11x8_5": "PB_SoftCover_12x8_20pp",  # 30x21cm ≈ 12x8 inches
            "size_11x11": "PB_SoftCover_11x11_20pp",
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
        
        # Handle cm sizes for photobooks - convert to inches dynamically
        if size and product == "photobooks" and "cm" in str(size).lower():
            # Normalize size string (remove spaces, lowercase)
            size_normalized = str(size).lower().replace(" ", "").replace("_", "")
            # Extract dimensions from cm string (e.g., "30x21cm" -> 30, 21)
            import re
            cm_match = re.search(r'(\d+)x(\d+)', size_normalized)
            if cm_match:
                width_cm = float(cm_match.group(1))
                height_cm = float(cm_match.group(2))
                # Convert cm to inches
                width_inches = width_cm / 2.54
                height_inches = height_cm / 2.54
                # Round to nearest standard size
                # Standard sizes: 8x6, 8x8, 11x8.5, 11x11, 12x8
                standard_sizes = [
                    (8, 6, "size_8x6"),
                    (8, 8, "size_8x8"),
                    (11, 8.5, "size_11x8_5"),
                    (11, 11, "size_11x11"),
                    (12, 8, "size_11x8_5"),  # 12x8 maps to 11x8.5
                ]
                # Find closest match
                min_distance = float('inf')
                closest_size = None
                for std_w, std_h, size_key in standard_sizes:
                    distance = abs(width_inches - std_w) + abs(height_inches - std_h)
                    if distance < min_distance:
                        min_distance = distance
                        closest_size = size_key
                if closest_size:
                    size = closest_size
        
        if size and size in size_mapping:
            return size_mapping[size]
        # Try alternative formats
        if size:
            # Try with "size_" prefix
            size_with_prefix = f"size_{size}" if not size.startswith("size_") else size
            if size_with_prefix in size_mapping:
                return size_mapping[size_with_prefix]
            # Try without prefix
            size_without_prefix = size.replace("size_", "")
            if size_without_prefix in size_mapping:
                return size_mapping[size_without_prefix]
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

