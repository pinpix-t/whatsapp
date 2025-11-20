"""
Bulk ordering product configuration
Maps products to their questions and options based on printerpix.co.uk/bulk-ordering/
"""

BULK_PRODUCTS = {
    "blankets": {
        "name": "Blankets",
        "questions": [
            {
                "step": "fabric",
                "question": "Select fabric type:",
                "component": "list",
                "options": [
                    {"id": "fabric_fleece", "title": "Fleece"},
                    {"id": "fabric_cosy_fleece", "title": "Cosy Fleece"},
                    {"id": "fabric_sherpa", "title": "Sherpa Fleece"}
                ]
            },
            {
                "step": "size",
                "question": "Select size:",
                "component": "list",
                "options": [
                    {"id": "size_baby_20x25", "title": "Baby (20x25 inches)"},
                    {"id": "size_med_30x40", "title": "Medium (30x40 inches)"},
                    {"id": "size_throw_50x60", "title": "Throw (50x60 inches)"},
                    {"id": "size_queen_60x80", "title": "Queen (60x80 inches)"}
                ]
            }
        ]
    },
    "canvas": {
        "name": "Canvas",
        "questions": [
            {
                "step": "size",
                "question": "Select canvas size:",
                "component": "list",
                "options": [
                    {"id": "size_6x6", "title": "6x6 inches"},
                    {"id": "size_10x10", "title": "10x10 inches"},
                    {"id": "size_12x12", "title": "12x12 inches"},
                    {"id": "size_11x14", "title": "11x14 inches"},
                    {"id": "size_16x20", "title": "16x20 inches"},
                    {"id": "size_36x24", "title": "36x24 inches"},
                    {"id": "size_30x40", "title": "30x40 inches"}
                ]
            }
        ]
    },
    "photobooks": {
        "name": "Photo Books",
        "questions": [
            {
                "step": "cover",
                "question": "Select cover type:",
                "component": "buttons",
                "options": [
                    {"id": "cover_hard_cover", "title": "Hard Cover"},
                    {"id": "cover_leather_cover", "title": "Leather Cover"}
                ]
            },
            {
                "step": "size",
                "question": "Select size:",
                "component": "list",
                "options": [
                    {"id": "size_8x6", "title": "8x6 inches"},
                    {"id": "size_8x8", "title": "8x8 inches"},
                    {"id": "size_11x8_5", "title": "11x8.5 inches"},
                    {"id": "size_8_5x11", "title": "8.5x11 inches"},
                    {"id": "size_11x11", "title": "11x11 inches"}
                ]
            },
            {
                "step": "pages",
                "question": "How many pages?",
                "component": "buttons",
                "options": [
                    {"id": "pages_20", "title": "20 pages"},
                    {"id": "pages_40", "title": "40 pages"},
                    {"id": "pages_60", "title": "60 pages"},
                    {"id": "pages_custom", "title": "Custom"}
                ]
            }
        ]
    },
    "mugs": {
        "name": "Mugs",
        "questions": [
            {
                "step": "type",
                "question": "Select mug type:",
                "component": "list",
                "options": [
                    {"id": "type_classic_mug", "title": "Classic Mug"},
                    {"id": "type_magic_mug", "title": "Magic Mug"},
                    {"id": "type_latte_mug", "title": "Latte Mug"},
                    {"id": "type_magic_latte_mug", "title": "Magic Latte Mug"}
                ]
            }
        ]
    },
}

# Discount codes
DISCOUNT_CODES = {
    "first_offer": "2BULK103025CSR",  # 5% discount
    "second_offer": "BULK103025CS"    # 10% discount
}

# Price point mapping: discount codes map to PricePointId UUID in Supabase
# 2BULK103025CSR is price point D, BULK103025CS is price point B
# Based on CSV: 563f6010... appears to be one price point, 5d21e679... appears to be another
PRICE_POINT_MAPPING = {
    "first_offer": "563f6010-fbf4-4474-bc7f-f35879f6b1ee",  # Price point for 2BULK103025CSR
    "second_offer": "5d21e679-f8b2-495e-ac26-86aefbffc190"  # Price point for BULK103025CS
}

# Other products (no detailed qualification questions)
OTHER_PRODUCTS = {
    "wall_calendar": {
        "name": "Wall Calendar",
        "url": "https://www.printerpix.co.uk/photo-calendars/personalised-wall-calendar/"
    },
    "photo_frame": {
        "name": "Photo Frame",
        "url": "https://www.printerpix.co.uk/photo-prints/photo-frame-prints/"
    },
    "jigsaw": {
        "name": "Jigsaw",
        "url": "https://www.printerpix.co.uk/photo-gifts/all/personalised-jigsaw-puzzle-card/"
    },
    "photo_slate": {
        "name": "Photo Slate",
        "url": "https://www.printerpix.co.uk/photo-gifts/all/photo-slate/"
    },
    "mouse_mat": {
        "name": "Mouse Mat",
        "url": "https://www.printerpix.co.uk/photo-gifts/all/personalised-mouse-mat/"
    },
    "photo_cushion": {
        "name": "Photo Cushion",
        "url": "https://www.printerpix.co.uk/photo-gifts/all/personalised-photo-cushion/"
    },
    "metal_photo": {
        "name": "Metal Photo",
        "url": "https://www.printerpix.co.uk/photo-prints/metal-photo-prints/"
    }
}

# Product selection list (for initial product selection)
PRODUCT_SELECTION_LIST = [
    {"id": "product_photobooks", "title": "Photo Books"},
    {"id": "product_blankets", "title": "Blankets"},
    {"id": "product_canvas", "title": "Canvas"},
    {"id": "product_mugs", "title": "Mugs"},
    {"id": "product_other", "title": "Other"}
]

# Other products selection list (shown when "Other" is selected)
OTHER_PRODUCTS_LIST = [
    {"id": "other_wall_calendar", "title": "Wall Calendar"},
    {"id": "other_photo_frame", "title": "Photo Frame"},
    {"id": "other_jigsaw", "title": "Jigsaw"},
    {"id": "other_photo_slate", "title": "Photo Slate"},
    {"id": "other_mouse_mat", "title": "Mouse Mat"},
    {"id": "other_photo_cushion", "title": "Photo Cushion"},
    {"id": "other_metal_photo", "title": "Metal Photo"}
]

# Product landing page URLs
PRODUCT_URLS = {
    "blankets": "https://www.printerpix.co.uk/photo-blankets/mink-personalised-blanket/",
    "canvas": "https://www.printerpix.co.uk/canvas-prints/v1/",
    "photobooks": "https://www.printerpix.co.uk/photo-books/hardcover-photobook/",
    "mugs": "https://www.printerpix.co.uk/photo-mugs/personalised-photo-mug/",
    # Other products
    "wall_calendar": "https://www.printerpix.co.uk/photo-calendars/personalised-wall-calendar/",
    "photo_frame": "https://www.printerpix.co.uk/photo-prints/photo-frame-prints/",
    "jigsaw": "https://www.printerpix.co.uk/photo-gifts/all/personalised-jigsaw-puzzle-card/",
    "photo_slate": "https://www.printerpix.co.uk/photo-gifts/all/photo-slate/",
    "mouse_mat": "https://www.printerpix.co.uk/photo-gifts/all/personalised-mouse-mat/",
    "photo_cushion": "https://www.printerpix.co.uk/photo-gifts/all/personalised-photo-cushion/",
    "metal_photo": "https://www.printerpix.co.uk/photo-prints/metal-photo-prints/"
}

# Homepage URL (for multiple products)
HOMEPAGE_URL = "https://www.printerpix.co.uk/"

