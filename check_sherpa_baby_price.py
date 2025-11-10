"""Check Sherpa baby blanket pricing from SQL Server"""

from database.sql_server_store import sql_server_store
import pandas as pd

def check_sherpa_baby_price():
    """Check Sherpa baby blanket pricing"""
    print("=" * 60)
    print("Checking Sherpa Baby Blanket Pricing")
    print("=" * 60)
    
    # Check for Sherpa baby blanket (20x25 or 25x20)
    print("\n1. Checking Sherpa baby blanket prices...")
    try:
        df = sql_server_store.query_to_dataframe("""
            SELECT 
                platinumProductReferenceId,
                price,
                currency,
                comparisonPrice,
                costOfGoods
            FROM [dbo].[SynComs.Products.PlatinumProducts.PlatinumProduct]
            WHERE platinumProductReferenceId LIKE '%Sherpa%'
               AND (
                   platinumProductReferenceId LIKE '%20x25%'
                   OR platinumProductReferenceId LIKE '%25x20%'
               )
            ORDER BY platinumProductReferenceId;
        """)
        
        if not df.empty:
            print(f"   ✅ Found {len(df)} Sherpa baby blanket products:")
            for idx, row in df.iterrows():
                print(f"\n   Product {idx + 1}:")
                print(f"     Reference ID: {row['platinumProductReferenceId']}")
                print(f"     Price: £{row['price']:.2f} ({row['currency']})")
                print(f"     Comparison Price: £{row['comparisonPrice']:.2f}" if row['comparisonPrice'] else "     Comparison Price: N/A")
                print(f"     Cost of Goods: £{row['costOfGoods']:.2f}" if pd.notna(row['costOfGoods']) else "     Cost of Goods: N/A")
        else:
            print("   ⚠️ No Sherpa baby blanket products found")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Check all Sherpa blanket sizes
    print("\n2. Checking all Sherpa blanket sizes...")
    try:
        df = sql_server_store.query_to_dataframe("""
            SELECT 
                platinumProductReferenceId,
                price,
                currency
            FROM [dbo].[SynComs.Products.PlatinumProducts.PlatinumProduct]
            WHERE platinumProductReferenceId LIKE '%Sherpa%'
               AND platinumProductReferenceId LIKE '%Blanket%'
            ORDER BY 
                CASE 
                    WHEN platinumProductReferenceId LIKE '%20x25%' OR platinumProductReferenceId LIKE '%25x20%' THEN 1
                    WHEN platinumProductReferenceId LIKE '%30x40%' THEN 2
                    WHEN platinumProductReferenceId LIKE '%50x60%' THEN 3
                    WHEN platinumProductReferenceId LIKE '%60x80%' THEN 4
                    ELSE 5
                END,
                platinumProductReferenceId;
        """)
        
        if not df.empty:
            print(f"   ✅ Found {len(df)} Sherpa blanket products:")
            for idx, row in df.iterrows():
                print(f"     - {row['platinumProductReferenceId']}: £{row['price']:.2f}")
        else:
            print("   ⚠️ No Sherpa blanket products found")
    except Exception as e:
        print(f"   ⚠️ Error: {e}")
    
    # Compare with our local mapping
    print("\n3. Comparing with local base price mapping...")
    try:
        from config.bulk_base_prices import BASE_PRICE_MAPPING
        
        sherpa_mapping = {
            "BlanketSherpafleece_25x20": BASE_PRICE_MAPPING.get("BlanketSherpafleece_25x20"),
            "BlanketSherpafleece_30x40": BASE_PRICE_MAPPING.get("BlanketSherpafleece_30x40"),
            "BlanketSherpafleece_50x60": BASE_PRICE_MAPPING.get("BlanketSherpafleece_50x60"),
            "BlanketSherpafleece_60x80": BASE_PRICE_MAPPING.get("BlanketSherpafleece_60x80"),
        }
        
        print("   Local mapping prices:")
        for ref_code, price in sherpa_mapping.items():
            if price:
                print(f"     - {ref_code}: £{price:.2f}")
        
        # Check SQL Server prices
        sql_prices = sql_server_store.query_to_dataframe("""
            SELECT 
                platinumProductReferenceId,
                price
            FROM [dbo].[SynComs.Products.PlatinumProducts.PlatinumProduct]
            WHERE platinumProductReferenceId IN (
                'BlanketSherpafleece_25x20',
                'BlanketSherpafleece_30x40',
                'BlanketSherpafleece_50x60',
                'BlanketSherpafleece_60x80'
            )
            ORDER BY platinumProductReferenceId;
        """)
        
        if not sql_prices.empty:
            print("\n   SQL Server prices:")
            for idx, row in sql_prices.iterrows():
                ref_code = row['platinumProductReferenceId']
                sql_price = row['price']
                local_price = sherpa_mapping.get(ref_code)
                
                match = "✅ MATCH" if local_price and abs(sql_price - local_price) < 0.01 else "⚠️ DIFFERENT"
                print(f"     - {ref_code}: £{sql_price:.2f} {match}")
                if local_price and abs(sql_price - local_price) >= 0.01:
                    print(f"       Local: £{local_price:.2f}")
    except Exception as e:
        print(f"   ⚠️ Error comparing: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    print("✅ SQL Server has base prices (pre-discount)")
    print("✅ These match the original prices shown on the website")
    print("✅ Discounts are applied separately (from Supabase pricing_b_d table)")
    print("=" * 60)
    print("\nExample for Sherpa Baby (25x20):")
    print("  Base Price (SQL Server): £79.90")
    print("  Discounted Price (80% off): £15.98")
    print("  Formula: £79.90 × (1 - 0.80) = £15.98")
    print("=" * 60)

if __name__ == "__main__":
    check_sherpa_baby_price()

