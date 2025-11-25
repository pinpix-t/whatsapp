"""
Script to get prices for all photobooks, blankets, and canvas products
Run this to generate a complete price list
"""

import sys
import os

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import directly to avoid __init__.py circular imports
import importlib.util
spec = importlib.util.spec_from_file_location("bulk_pricing", os.path.join(os.path.dirname(os.path.dirname(__file__)), "services", "bulk_pricing.py"))
bulk_pricing_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bulk_pricing_module)
BulkPricingService = bulk_pricing_module.BulkPricingService

bulk_pricing_service = BulkPricingService()

# Standard quantity for pricing (you can change this)
STANDARD_QUANTITY = 50

def get_all_product_combinations():
    """Generate all product combinations"""
    combinations = []
    
    # Photo Books
    for cover in ["cover_hard_cover", "cover_leather_cover"]:
        for size in ["size_8x6", "size_8x8", "size_11x8_5", "size_8_5x11", "size_11x11"]:
            for pages in ["pages_20", "pages_40", "pages_60"]:
                combinations.append({
                    "product": "photobooks",
                    "cover": cover,
                    "size": size,
                    "pages": pages
                })
    
    # Blankets
    for fabric in ["fabric_fleece", "fabric_cosy_fleece", "fabric_sherpa"]:
        for size in ["size_baby_20x25", "size_med_30x40", "size_throw_50x60", "size_queen_60x80"]:
            combinations.append({
                "product": "blankets",
                "fabric": fabric,
                "size": size
            })
    
    # Canvas
    for size in ["size_6x6", "size_10x10", "size_12x12", "size_11x14", "size_16x20", "size_36x24", "size_30x40"]:
        combinations.append({
            "product": "canvas",
            "size": size
        })
    
    return combinations

def format_product_name(selections):
    """Format product name from selections"""
    product = selections.get("product", "")
    
    if product == "photobooks":
        cover = selections.get("cover", "").replace("cover_", "").replace("_", " ").title()
        size = selections.get("size", "").replace("size_", "").replace("_", "x")
        pages = selections.get("pages", "").replace("pages_", "")
        return f"Photo Book - {cover} - {size} - {pages} pages"
    elif product == "blankets":
        fabric = selections.get("fabric", "").replace("fabric_", "").replace("_", " ").title()
        size = selections.get("size", "").replace("size_", "").replace("_", "x").replace("baby", "Baby").replace("med", "Medium").replace("throw", "Throw").replace("queen", "Queen")
        return f"Blanket - {fabric} - {size}"
    elif product == "canvas":
        size = selections.get("size", "").replace("size_", "").replace("_", "x")
        return f"Canvas - {size}"
    
    return str(selections)

def get_prices():
    """Get prices for all combinations"""
    combinations = get_all_product_combinations()
    results = []
    
    print(f"Getting prices for {len(combinations)} product combinations...\n")
    
    for i, selections in enumerate(combinations, 1):
        try:
            print(f"Processing {i}/{len(combinations)}: {format_product_name(selections)}...", end=" ")
            
            # Get prices for both offer types (try second_offer first as it's more commonly used)
            price_info = bulk_pricing_service.get_bulk_price_info(
                selections=selections,
                quantity=STANDARD_QUANTITY,
                offer_type="second_offer"
            )
            
            if price_info.get("success"):
                results.append({
                    "product": format_product_name(selections),
                    "product_reference_code": price_info.get("product_reference_code"),
                    "base_price": price_info.get("base_price"),
                    "discount_percent": price_info.get("discount_percent"),
                    "unit_price": price_info.get("unit_price"),
                    "total_price": price_info.get("total_price"),
                    "formatted_unit_price": price_info.get("formatted_unit_price"),
                    "formatted_total_price": price_info.get("formatted_total_price"),
                })
                print("✓")
            else:
                error = price_info.get("error_message", "Unknown error")
                results.append({
                    "product": format_product_name(selections),
                    "error": error
                })
                print(f"✗ ({error[:50]})")
        except Exception as e:
            results.append({
                "product": format_product_name(selections),
                "error": str(e)
            })
            print(f"✗ ({str(e)[:50]})")
    
    return results

def print_price_list(results):
    """Print formatted price list"""
    print("\n" + "=" * 120)
    print(f"PRICE LIST - All Products (Quantity: {STANDARD_QUANTITY} units)")
    print("=" * 120)
    print()
    
    # Group by product type
    photobooks = [r for r in results if "Photo Book" in r.get("product", "")]
    blankets = [r for r in results if "Blanket" in r.get("product", "")]
    canvas = [r for r in results if "Canvas" in r.get("product", "")]
    
    # Print Photo Books
    print("📚 PHOTO BOOKS")
    print("-" * 120)
    print(f"{'Product':<70} | {'Base Price':>12} | {'Discount':>10} | {'Unit Price':>12} | {'Total Price':>15}")
    print("-" * 120)
    for r in photobooks:
        if "error" not in r:
            base = f"£{r.get('base_price', 0):.2f}" if r.get('base_price') else "N/A"
            discount = f"{r.get('discount_percent', 0):.1f}%" if r.get('discount_percent') else "N/A"
            unit = r.get('formatted_unit_price', 'N/A')
            total = r.get('formatted_total_price', 'N/A')
            print(f"{r['product']:<70} | {base:>12} | {discount:>10} | {unit:>12} | {total:>15}")
        else:
            print(f"{r['product']:<70} | ERROR: {r['error'][:40]}")
    print()
    
    # Print Blankets
    print("🛏️  BLANKETS")
    print("-" * 120)
    print(f"{'Product':<70} | {'Base Price':>12} | {'Discount':>10} | {'Unit Price':>12} | {'Total Price':>15}")
    print("-" * 120)
    for r in blankets:
        if "error" not in r:
            base = f"£{r.get('base_price', 0):.2f}" if r.get('base_price') else "N/A"
            discount = f"{r.get('discount_percent', 0):.1f}%" if r.get('discount_percent') else "N/A"
            unit = r.get('formatted_unit_price', 'N/A')
            total = r.get('formatted_total_price', 'N/A')
            print(f"{r['product']:<70} | {base:>12} | {discount:>10} | {unit:>12} | {total:>15}")
        else:
            print(f"{r['product']:<70} | ERROR: {r['error'][:40]}")
    print()
    
    # Print Canvas
    print("🖼️  CANVAS")
    print("-" * 120)
    print(f"{'Product':<70} | {'Base Price':>12} | {'Discount':>10} | {'Unit Price':>12} | {'Total Price':>15}")
    print("-" * 120)
    for r in canvas:
        if "error" not in r:
            base = f"£{r.get('base_price', 0):.2f}" if r.get('base_price') else "N/A"
            discount = f"{r.get('discount_percent', 0):.1f}%" if r.get('discount_percent') else "N/A"
            unit = r.get('formatted_unit_price', 'N/A')
            total = r.get('formatted_total_price', 'N/A')
            print(f"{r['product']:<70} | {base:>12} | {discount:>10} | {unit:>12} | {total:>15}")
        else:
            print(f"{r['product']:<70} | ERROR: {r['error'][:40]}")
    print()
    
    # Summary
    successful = len([r for r in results if "error" not in r])
    failed = len([r for r in results if "error" in r])
    print("=" * 120)
    print(f"Summary: {successful} successful, {failed} failed out of {len(results)} total")
    print("=" * 120)

if __name__ == "__main__":
    results = get_prices()
    print_price_list(results)

