"""
Script to update config/bulk_base_prices.py with prices from Excel files
Maps Excel MPN format to our ProductReferenceCode format
"""

import sys
from parse_pricing_files import (
    parse_blanket_file,
    parse_calendar_file,
    parse_photobooks_file,
    parse_canvas_file,
    parse_other_products_file
)

# Map Excel MPN format to our ProductReferenceCode format
# Excel has 20x25, we use 25x20 (dimensions swapped for baby size)
MPN_MAPPING = {
    # Blankets - Excel format -> Our format
    "BlanketFlannelfleece_20x25": "BlanketFlannelfleece_25x20",
    "BlanketPolarfleece_20x25": "BlanketPolarfleece_25x20",
    "BlanketSherpafleece_20x25": "BlanketSherpafleece_25x20",
    # Other sizes match
    "BlanketFlannelfleece_30x40": "BlanketFlannelfleece_30x40",
    "BlanketFlannelfleece_50x60": "BlanketFlannelfleece_50x60",
    "BlanketFlannelfleece_60x80": "BlanketFlannelfleece_60x80",
    "BlanketPolarfleece_30x40": "BlanketPolarfleece_30x40",
    "BlanketPolarfleece_50x60": "BlanketPolarfleece_50x60",
    "BlanketPolarfleece_60x80": "BlanketPolarfleece_60x80",
    "BlanketSherpafleece_30x40": "BlanketSherpafleece_30x40",
    "BlanketSherpafleece_50x60": "BlanketSherpafleece_50x60",
    "BlanketSherpafleece_60x80": "BlanketSherpafleece_60x80",
}

def main():
    """Parse all files and update base_prices.py"""
    print("=== Extracting Prices from Excel Files ===\n")
    
    all_prices = {}
    
    # Parse each file
    files = [
        ('Blanket_UK.xlsx', parse_blanket_file, 'Blankets'),
        ('Calendar_UK.xlsx', parse_calendar_file, 'Calendars'),
        ('Photobooks-Multiple_UK.xlsx', parse_photobooks_file, 'Photobooks'),
        ('Canvas_UK.xlsx', parse_canvas_file, 'Canvas'),
        ('UK_OtherProducts.xlsx', parse_other_products_file, 'Other Products'),
    ]
    
    for filename, parser_func, product_type in files:
        try:
            print(f"📄 Parsing {filename} ({product_type})...")
            prices = parser_func(filename)
            
            # Map Excel MPNs to our format
            for excel_mpn, price in prices.items():
                # Check if we need to map it
                our_mpn = MPN_MAPPING.get(excel_mpn, excel_mpn)
                all_prices[our_mpn] = price
            
            print(f"  ✅ Found {len(prices)} base prices")
        except Exception as e:
            print(f"  ❌ Error parsing {filename}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n=== Total Base Prices: {len(all_prices)} ===\n")
    
    # Read current base_prices.py
    with open('config/bulk_base_prices.py', 'r') as f:
        content = f.read()
    
    # Generate new BASE_PRICE_MAPPING
    print("=== Generating Updated BASE_PRICE_MAPPING ===\n")
    
    # Group prices by product type
    blankets = {k: v for k, v in all_prices.items() if 'Blanket' in k}
    calendars = {k: v for k, v in all_prices.items() if k.startswith('Cal_')}
    photobooks = {k: v for k, v in all_prices.items() if k.startswith('PB_')}
    canvas = {k: v for k, v in all_prices.items() if k.startswith('Canvas_')}
    other = {k: v for k, v in all_prices.items() if k not in blankets and k not in calendars and k not in photobooks and k not in canvas}
    
    # Build new mapping
    new_mapping = []
    new_mapping.append("BASE_PRICE_MAPPING = {")
    
    # Blankets
    if blankets:
        new_mapping.append("    # Blankets - Prices from Excel files")
        fleece = {k: v for k, v in blankets.items() if 'Flannelfleece' in k}
        polar = {k: v for k, v in blankets.items() if 'Polarfleece' in k}
        sherpa = {k: v for k, v in blankets.items() if 'Sherpafleece' in k}
        double = {k: v for k, v in blankets.items() if 'DoubleSide' in k}
        
        if fleece:
            new_mapping.append("    # Blankets - Fleece")
            for mpn, price in sorted(fleece.items()):
                new_mapping.append(f'    "{mpn}": {price:.2f},')
        
        if polar:
            new_mapping.append("    # Blankets - Polar/Mink Touch")
            for mpn, price in sorted(polar.items()):
                new_mapping.append(f'    "{mpn}": {price:.2f},')
        
        if sherpa:
            new_mapping.append("    # Blankets - Sherpa")
            for mpn, price in sorted(sherpa.items()):
                new_mapping.append(f'    "{mpn}": {price:.2f},')
        
        if double:
            new_mapping.append("    # Blankets - Double Sided")
            for mpn, price in sorted(double.items()):
                new_mapping.append(f'    "{mpn}": {price:.2f},')
    
    # Canvas
    if canvas:
        new_mapping.append("    # Canvas")
        for mpn, price in sorted(canvas.items()):
            new_mapping.append(f'    "{mpn}": {price:.2f},')
    
    # Photo Books
    if photobooks:
        new_mapping.append("    # Photo Books")
        for mpn, price in sorted(photobooks.items()):
            new_mapping.append(f'    "{mpn}": {price:.2f},')
    
    # Calendars
    if calendars:
        new_mapping.append("    # Calendars")
        for mpn, price in sorted(calendars.items()):
            new_mapping.append(f'    "{mpn}": {price:.2f},')
    
    # Other Products
    if other:
        new_mapping.append("    # Other Products")
        for mpn, price in sorted(other.items()):
            new_mapping.append(f'    "{mpn}": {price:.2f},')
    
    new_mapping.append("}")
    
    # Replace BASE_PRICE_MAPPING in content
    import re
    pattern = r'BASE_PRICE_MAPPING = \{.*?\}'
    replacement = '\n'.join(new_mapping)
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # Write updated file
    with open('config/bulk_base_prices.py', 'w') as f:
        f.write(new_content)
    
    print("✅ Updated config/bulk_base_prices.py with prices from Excel files!")
    print(f"\nTotal prices updated: {len(all_prices)}")
    print("\nSample prices:")
    for mpn, price in list(all_prices.items())[:10]:
        print(f"  {mpn}: £{price:.2f}")

if __name__ == "__main__":
    main()

