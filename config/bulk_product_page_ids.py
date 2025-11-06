"""
Product selection to productPageId mapping table
Maps user selections (product + fabric/type + size) to productPageId
used in pricing API (e.g., "bc3e9ee3-84b4-452e-9559-3283a6b1a20e")
"""

# Mapping structure: product -> fabric/type -> size -> productPageId
# TODO: Fill in actual productPageId values from pricing API
PRODUCT_PAGE_ID_MAPPING = {
    "blankets": {
        "fabric_fleece": {
            "size_baby_20x25": "de485800-93c6-4276-992b-def1ce74d487",  # BlanketFlannelfleece_25x20
            "size_med_30x40": "72af97ca-2ec4-41c3-bd7d-b8e97fdccd75",  # BlanketFlannelfleece_30x40
            "size_throw_50x60": "d593e4ee-0075-484d-b83b-e50c93821e0a",  # BlanketFlannelfleece_50x60
            "size_queen_60x80": "df4daec2-e14b-436e-8f81-4c6888576126",  # BlanketFlannelfleece_60x80
        },
        "fabric_mink_touch": {
            "size_baby_20x25": "818db4ff-7407-458c-957e-cfb7c15371f5",  # BlanketPolarfleece_25x20
            "size_med_30x40": "6fc2bf2d-47d6-49e7-a42e-66acfd72cc07",  # BlanketPolarfleece_30x40
            "size_throw_50x60": "bbeed95b-adb5-4394-8ddb-857ec8a86f42",  # BlanketPolarfleece_50x60
            "size_queen_60x80": "7749fd23-0c3e-4d7a-9af8-9e754a3c2c2c",  # BlanketPolarfleece_60x80
        },
        "fabric_sherpa": {
            "size_baby_20x25": "06b5ad20-1832-41c6-99ab-985c090dd4d3",  # BlanketSherpafleece_25x20
            "size_med_30x40": "0fd9e65c-de5e-48c4-a1a7-559991a3ad77",  # BlanketSherpafleece_30x40
            "size_throw_50x60": "6da0bca9-e178-4706-a8b4-fa13dba2b15e",  # BlanketSherpafleece_50x60
            "size_queen_60x80": "11c5bbfb-ca04-4d3d-884e-8c649c99cfa4",  # BlanketSherpafleece_60x80
        },
        "fabric_double_sided": {
            "size_baby_20x25": "de485800-93c6-4276-992b-def1ce74d487",  # DoubleSideBlanketFlannel_25x20 not in CSV
            "size_med_30x40": "2b526c4a-56d1-4b43-892c-477cd6188746",  # DoubleSideBlanketFlannel_30x40
            "size_throw_50x60": "4bddf7f7-8b6d-468a-85f5-0c69ffff218b",  # DoubleSideBlanketFlannel_50x60
            "size_queen_60x80": "2ed7ec8f-1c6a-42cd-a843-dbbf1499c137",  # DoubleSideBlanketFlannel_60x80
        },
    },
    "canvas": {
        "default": {
            "size_6x6": "6eca1e34-1a2f-4b2c-9768-52a6395923aa",
            "size_10x10": "6eca1e34-1a2f-4b2c-9768-52a6395923aa",  # Canvas_F18_10x10 (correct)
            "size_12x12": "c340938c-f5fe-4f77-8082-7b23e75d727c",
            "size_11x14": "f7822b38-be1c-4d54-be94-b6282d40a064",
            "size_16x20": "81979a7c-131d-47a6-9a22-74135296bb78",
            "size_36x24": "da359457-fc24-4894-9409-137b28d0f8e0",
            "size_30x40": "f54f9463-fb3d-4517-b83c-a25cf055bb66",
        }
    },
    "photobooks": {
        "cover_hard_cover": {
            "size_8x6": "d5baac75-ecae-40e7-b5c3-84538d73e671",
            "size_8x8": "c5f5e749-b8df-46b8-b816-4913cdc3ca21",
            "size_11x8_5": "f6692129-efb5-446c-921a-82701949b8ba",
            "size_11x11": "db99bfe6-e0f0-4563-8266-5f8e7182bbce",
        },
        "cover_leather_cover": {
            "size_8x6": "e8727d92-48fd-4f32-8119-bb1c39623a1a",
            "size_8x8": "fc45fc2c-bcc4-4060-aae3-087e8ac73b3a",
            "size_11x8_5": "4433f22b-375d-4c0f-8348-0da4868e019b",
            "size_11x11": "dd072355-e333-42cc-bc40-e2ed2e4a16ac",
        },
    },
    "mugs": {
        "default": {
            "type_classic_mug": "eb6dc4dd-4a29-4771-bc15-481ed4e44dd0",
            "type_magic_mug": "eb6dc4dd-4a29-4771-bc15-481ed4e44dd0",
            "type_latte_mug": "e8fecd98-c9a9-440a-8abf-2da2966a7b6b",
            "type_magic_latte_mug": "e8fecd98-c9a9-440a-8abf-2da2966a7b6b",
        }
    },
    # Other products (simpler mapping)
    "wall_calendar": {
        "default": {
            "default": "f6e28494-5a96-472e-aeca-04ab31ea5f7c"  # Cal_WallSS_12x17 (correct)
        }
    },
    "photo_frame": {
        "default": {
            "default": "fe3a44be-0948-4d11-9535-672764e8e9b6"  # Frame_Wooden_12x8_Oak_PackOf3
        }
    },
    "jigsaw": {
        "default": {
            "default": "ffecac6e-5cd5-47f2-8568-8b8246f54f70"  # BoxedPuzzle_Board_15x11
        }
    },
    "photo_slate": {
        "default": {
            "default": "d50fa27e-baea-470d-ac9b-aca58a67001d"  # Slate_Rect_12x12
        }
    },
    "mouse_mat": {
        "default": {
            "default": "38dc7a2f-adec-476d-96c1-b9699c5fbd2f"  # MouseMat
        }
    },
    "photo_cushion": {
        "default": {
            "default": "d469b117-d1b2-4424-9b2c-05800615495c"  # CushionPolyester_18x12
        }
    },
    "metal_photo": {
        "default": {
            "default": "d2f48311-10a9-480c-9426-511a2fd0f06d"  # MetalPrint_12x12
        }
    },
}


def get_product_page_id(selections: dict) -> str:
    """
    Get productPageId from user selections
    
    Args:
        selections: Dictionary with product selections (product, fabric/type, size, etc.)
        
    Returns:
        productPageId string or None if not found
    """
    product = selections.get("product")
    if not product or product not in PRODUCT_PAGE_ID_MAPPING:
        return None
    
    product_mapping = PRODUCT_PAGE_ID_MAPPING[product]
    
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

