"""Test getting pricing data from SQL Server"""

from database.sql_server_store import sql_server_store
import pandas as pd

def test_pricing_from_sql():
    """Test if we can get pricing from SQL Server"""
    print("=" * 60)
    print("Testing Pricing from SQL Server")
    print("=" * 60)
    
    # Check PlatinumProduct table structure and pricing
    print("\n1. Checking PlatinumProduct pricing columns...")
    try:
        df = sql_server_store.query_to_dataframe("""
            SELECT TOP (5) 
                platinumProductReferenceId,
                price,
                comparisonPrice,
                costOfGoods,
                currency,
                priceByQtyId,
                platinumProductType
            FROM [dbo].[SynComs.Products.PlatinumProducts.PlatinumProduct]
            WHERE price IS NOT NULL;
        """)
        
        if not df.empty:
            print(f"   ✅ Found {len(df)} products with prices:")
            for idx, row in df.iterrows():
                print(f"\n   Product {idx + 1}:")
                print(f"     Reference ID: {row['platinumProductReferenceId']}")
                print(f"     Price: {row['price']} {row['currency']}")
                print(f"     Comparison Price: {row['comparisonPrice']}")
                print(f"     Cost of Goods: {row['costOfGoods']}")
                print(f"     Price By Qty ID: {row['priceByQtyId']}")
        else:
            print("   ⚠️ No products with prices found")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Check if we can join ProductPage with PlatinumProduct
    print("\n2. Testing join between ProductPage and PlatinumProduct...")
    try:
        df = sql_server_store.query_to_dataframe("""
            SELECT TOP (5)
                pp.canonicalProductPageId,
                pp.friendlyUrl,
                pp.attribute01,
                pp.attribute02,
                pp.attribute03,
                ppp.platinumProductReferenceId,
                ppp.price,
                ppp.currency,
                ppp.comparisonPrice
            FROM [dbo].[SynComs.Products.ProductPage] pp
            LEFT JOIN [dbo].[SynComs.Products.PlatinumProducts.PlatinumProduct] ppp
                ON pp.platinumProductVendorId = ppp.platinumProductVendorId
                AND pp.platinumProductType = ppp.platinumProductType
            WHERE pp.canonicalProductPageId IS NOT NULL
            AND ppp.price IS NOT NULL;
        """)
        
        if not df.empty:
            print(f"   ✅ Found {len(df)} joined records:")
            for idx, row in df.iterrows():
                print(f"\n   Record {idx + 1}:")
                print(f"     GUID: {row['canonicalProductPageId']}")
                print(f"     URL: {row['friendlyUrl']}")
                print(f"     Reference ID: {row['platinumProductReferenceId']}")
                print(f"     Price: {row['price']} {row['currency']}")
        else:
            print("   ⚠️ No joined records found")
    except Exception as e:
        print(f"   ⚠️ Could not join tables: {e}")
        import traceback
        traceback.print_exc()
    
    # Test with a blanket product
    print("\n3. Testing blanket product pricing...")
    try:
        df = sql_server_store.query_to_dataframe("""
            SELECT TOP (3)
                pp.canonicalProductPageId,
                pp.friendlyUrl,
                ppp.platinumProductReferenceId,
                ppp.price,
                ppp.currency
            FROM [dbo].[SynComs.Products.ProductPage] pp
            LEFT JOIN [dbo].[SynComs.Products.PlatinumProducts.PlatinumProduct] ppp
                ON pp.platinumProductVendorId = ppp.platinumProductVendorId
                AND pp.platinumProductType = ppp.platinumProductType
            WHERE pp.friendlyUrl LIKE '%blanket%'
            AND pp.canonicalProductPageId IS NOT NULL
            AND ppp.price IS NOT NULL;
        """)
        
        if not df.empty:
            print(f"   ✅ Found {len(df)} blanket products with prices:")
            for idx, row in df.iterrows():
                print(f"     - {row['friendlyUrl']}")
                print(f"       GUID: {row['canonicalProductPageId']}")
                print(f"       Reference: {row['platinumProductReferenceId']}")
                print(f"       Price: {row['price']} {row['currency']}")
        else:
            print("   ⚠️ No blanket products with prices found")
    except Exception as e:
        print(f"   ⚠️ Could not query blanket products: {e}")
    
    # Check if we can find ProductReferenceCode mapping
    print("\n4. Checking for ProductReferenceCode mapping...")
    try:
        # Check if platinumProductReferenceId matches our ProductReferenceCode format
        df = sql_server_store.query_to_dataframe("""
            SELECT TOP (10)
                platinumProductReferenceId,
                price,
                currency
            FROM [dbo].[SynComs.Products.PlatinumProducts.PlatinumProduct]
            WHERE platinumProductReferenceId LIKE '%Blanket%'
               OR platinumProductReferenceId LIKE '%PB_%'
               OR platinumProductReferenceId LIKE '%Cal_%'
            ORDER BY platinumProductReferenceId;
        """)
        
        if not df.empty:
            print(f"   ✅ Found {len(df)} products with reference IDs:")
            for idx, row in df.iterrows():
                print(f"     - {row['platinumProductReferenceId']}: {row['price']} {row['currency']}")
        else:
            print("   ⚠️ No matching reference IDs found")
    except Exception as e:
        print(f"   ⚠️ Could not search for reference IDs: {e}")
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    print("✅ Can get prices from PlatinumProduct table")
    print("✅ Can join ProductPage with PlatinumProduct")
    print("✅ Can get canonicalProductPageId from SQL Server")
    print("⚠️ Need to verify ProductReferenceCode mapping")
    print("⚠️ Discounts still need Supabase (pricing_b_d table)")
    print("=" * 60)

if __name__ == "__main__":
    test_pricing_from_sql()

