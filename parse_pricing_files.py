"""
Script to parse Excel pricing files and extract base prices
Extracts MPN (ProductReferenceCode) → RRP (base price when QTY=1) mappings
"""

import pandas as pd
from typing import Dict, Optional
import sys

def parse_blanket_file(filepath: str) -> Dict[str, float]:
    """Parse Blanket_UK.xlsx file"""
    df = pd.read_excel(filepath, header=None)
    base_prices = {}
    current_mpn = None
    expecting_header = False
    expecting_data = False
    
    for idx, row in df.iterrows():
        mpn = row[0]  # First column is MPN
        
        # Check if this is a NEW MPN (different from current)
        if pd.notna(mpn) and isinstance(mpn, str) and mpn.startswith('Blanket'):
            if mpn != current_mpn:  # Only reset if it's a different MPN
                current_mpn = mpn
                expecting_header = True
                expecting_data = False
                continue
        
        # Skip if we already have this MPN's price
        if current_mpn and current_mpn in base_prices:
            continue
        
        # Check if this is the header row (after MPN)
        if expecting_header and pd.notna(row[1]) and isinstance(row[1], str):
            if 'QTY' in str(row[1]) or 'Quantity' in str(row[1]):
                expecting_header = False
                expecting_data = True
                continue
        
        # After header, check for QTY=1
        if expecting_data and current_mpn and pd.notna(row[1]):
            try:
                qty = float(row[1])
                if qty == 1.0:
                    # RRP is in column 3 (index 3)
                    rrp = row[3]
                    if pd.notna(rrp):
                        base_prices[current_mpn] = float(rrp)
                        expecting_data = False  # Found it, reset for next MPN
            except (ValueError, TypeError):
                pass
    
    return base_prices


def parse_calendar_file(filepath: str) -> Dict[str, float]:
    """Parse Calendar_UK.xlsx file"""
    df = pd.read_excel(filepath, header=None)
    base_prices = {}
    current_mpn = None
    expecting_header = False
    expecting_data = False
    
    for idx, row in df.iterrows():
        mpn = row[0]  # First column is MPN
        
        # Check if this is a NEW MPN (different from current)
        if pd.notna(mpn) and isinstance(mpn, str) and mpn.startswith('Cal_'):
            if mpn != current_mpn:  # Only reset if it's a different MPN
                current_mpn = mpn
                expecting_header = True
                expecting_data = False
                continue
        
        # Skip if we already have this MPN's price
        if current_mpn and current_mpn in base_prices:
            continue
        
        # Check if this is the header row (after MPN)
        if expecting_header and pd.notna(row[1]) and isinstance(row[1], str):
            if 'QTY' in str(row[1]) or 'Quantity' in str(row[1]):
                expecting_header = False
                expecting_data = True
                continue
        
        # After header, check for QTY=1
        if expecting_data and current_mpn and pd.notna(row[1]):
            try:
                qty = float(row[1])
                if qty == 1.0:
                    # RRP is in column 3 (index 3)
                    rrp = row[3]
                    if pd.notna(rrp):
                        base_prices[current_mpn] = float(rrp)
                        expecting_data = False  # Found it, reset for next MPN
            except (ValueError, TypeError):
                pass
    
    return base_prices


def parse_photobooks_file(filepath: str) -> Dict[str, float]:
    """Parse Photobooks-Multiple_UK.xlsx file"""
    df = pd.read_excel(filepath, header=None)
    base_prices = {}
    current_mpn = None
    expecting_header = False
    expecting_data = False
    
    for idx, row in df.iterrows():
        mpn = row[0]  # First column is MPN
        
        # Check if this is a NEW MPN (different from current)
        if pd.notna(mpn) and isinstance(mpn, str) and mpn.startswith('PB_'):
            if mpn != current_mpn:  # Only reset if it's a different MPN
                current_mpn = mpn
                expecting_header = True
                expecting_data = False
                continue
        
        # Skip if we already have this MPN's price
        if current_mpn and current_mpn in base_prices:
            continue
        
        # Check if this is the header row (after MPN)
        if expecting_header and pd.notna(row[1]) and isinstance(row[1], str):
            if 'QTY' in str(row[1]) or 'Quantity' in str(row[1]):
                expecting_header = False
                expecting_data = True
                continue
        
        # After header, check for QTY=1
        if expecting_data and current_mpn and pd.notna(row[1]):
            try:
                qty = float(row[1])
                if qty == 1.0:
                    # RRP is in column 2 (index 2)
                    rrp = row[2]
                    if pd.notna(rrp):
                        base_prices[current_mpn] = float(rrp)
                        expecting_data = False  # Found it, reset for next MPN
            except (ValueError, TypeError):
                pass
    
    return base_prices


def parse_canvas_file(filepath: str) -> Dict[str, float]:
    """Parse Canvas_UK.xlsx file - different structure"""
    df = pd.read_excel(filepath, header=None)
    base_prices = {}
    
    # Canvas file has different structure - need to find pattern
    # Looking for size descriptions and corresponding RRP
    current_size = None
    
    for idx, row in df.iterrows():
        # Check first column for size info
        first_col = row[0]
        
        if pd.notna(first_col) and isinstance(first_col, str):
            # Check if it's a size description (contains 'cm' or 'x')
            if 'cm' in str(first_col) or ('x' in str(first_col) and any(c.isdigit() for c in str(first_col))):
                current_size = str(first_col).strip()
        
        # Check if this is a header row
        if pd.notna(row[1]) and isinstance(row[1], str):
            if 'Quantity' in str(row[1]) or 'RRP' in str(row[1]):
                continue
        
        # Check if this is a data row with QTY=1
        if current_size and pd.notna(row[1]):
            try:
                qty = float(row[1])
                if qty == 1.0:
                    # RRP is usually in column 2 (index 2)
                    rrp = row[2]
                    if pd.notna(rrp):
                        # Map size to ProductReferenceCode format
                        # Need to match Canvas_F18_* format
                        # This is complex - may need manual mapping
                        pass
            except (ValueError, TypeError):
                pass
    
    # Canvas file structure is complex - may need manual review
    return base_prices


def parse_other_products_file(filepath: str) -> Dict[str, float]:
    """Parse UK_OtherProducts.xlsx file - different structure"""
    df = pd.read_excel(filepath, header=None)
    base_prices = {}
    
    # Other products file structure:
    # Row 2: Size (e.g., "8'' x 6''")
    # Row 3: Header row ('Quantity', 'RRP', 'Selling Price', 'Shipping')
    # Row 4+: Data rows with QTY=1, 2, 3...
    
    current_size = None
    expecting_header = False
    expecting_data = False
    
    # Map sizes to ProductReferenceCode (if applicable)
    # This file may contain various products - need to identify which ones
    
    for idx, row in df.iterrows():
        first_col = row[0]
        
        # Check if this is a size row (contains inches or dimensions)
        if pd.notna(first_col) and isinstance(first_col, str):
            if "''" in str(first_col) or 'x' in str(first_col):
                current_size = str(first_col).strip()
                expecting_header = True
                expecting_data = False
                continue
        
        # Check if this is the header row
        if expecting_header and pd.notna(row[1]) and isinstance(row[1], str):
            if 'Quantity' in str(row[1]) or 'QTY' in str(row[1]):
                expecting_header = False
                expecting_data = True
                continue
        
        # After header, check for QTY=1
        if expecting_data and current_size and pd.notna(row[1]):
            try:
                qty = float(row[1])
                if qty == 1.0:
                    # RRP is in column 2 (index 2)
                    rrp = row[2]
                    if pd.notna(rrp):
                        # For now, we'll skip other products as they may not have MPN format
                        # Can be added later if needed
                        pass
                        expecting_data = False
            except (ValueError, TypeError):
                pass
    
    return base_prices


def main():
    """Parse all pricing files and extract base prices"""
    print("=== Parsing Pricing Files ===\n")
    
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
            all_prices.update(prices)
            print(f"  ✅ Found {len(prices)} base prices")
        except Exception as e:
            print(f"  ❌ Error parsing {filename}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n=== Total Base Prices Extracted: {len(all_prices)} ===\n")
    
    # Show sample prices
    print("Sample prices (first 20):")
    for mpn, price in list(all_prices.items())[:20]:
        print(f"  {mpn}: £{price:.2f}")
    
    return all_prices


if __name__ == "__main__":
    prices = main()
    
    # Save to a temporary file for review
    with open('extracted_prices.txt', 'w') as f:
        f.write("# Extracted Base Prices from Excel Files\n\n")
        for mpn, price in sorted(prices.items()):
            f.write(f'"{mpn}": {price:.2f},\n')
    
    print(f"\n✅ Prices saved to extracted_prices.txt")

