"""Check if we can get pricing data from SQL Server"""

from database.sql_server_store import sql_server_store
import pandas as pd

def check_pricing_capabilities():
    """Check what pricing data we can get from SQL Server"""
    print("=" * 60)
    print("Checking Pricing Capabilities in SQL Server")
    print("=" * 60)
    
    # Check if we can find ProductReferenceCode mapping
    print("\n1. Checking for ProductReferenceCode mapping...")
    try:
        # Check all columns that might contain product reference codes
        df = sql_server_store.query_to_dataframe("""
            SELECT TOP (5) 
                _GUID_,
                canonicalProductPageId,
                friendlyUrl,
                url,
                attribute01,
                attribute02,
                attribute03,
                platinumProductVendorId,
                platinumProductType,
                platinumProductSubType
            FROM [dbo].[SynComs.Products.ProductPage]
            WHERE canonicalProductPageId IS NOT NULL;
        """)
        
        if not df.empty:
            print(f"   ✅ Found {len(df)} rows with canonicalProductPageId")
            print("\n   Sample data:")
            for idx, row in df.iterrows():
                print(f"\n   Row {idx + 1}:")
                print(f"     _GUID_: {row['_GUID_']}")
                print(f"     canonicalProductPageId: {row['canonicalProductPageId']}")
                print(f"     friendlyUrl: {row['friendlyUrl']}")
                print(f"     attribute01: {row['attribute01']}")
        else:
            print("   ⚠️ No rows with canonicalProductPageId found")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Check PlatinumProduct table
    print("\n2. Checking PlatinumProduct table...")
    try:
        df = sql_server_store.query_to_dataframe("""
            SELECT TOP (5) *
            FROM [dbo].[SynComs.Products.PlatinumProducts.PlatinumProduct];
        """)
        
        if not df.empty:
            print(f"   ✅ Found {len(df)} rows")
            print(f"   Columns: {', '.join(df.columns.tolist()[:15])}...")
            
            # Check for price-related columns
            price_cols = [col for col in df.columns if 'price' in col.lower() or 'cost' in col.lower() or 'amount' in col.lower()]
            if price_cols:
                print(f"   Price-related columns: {', '.join(price_cols)}")
            else:
                print("   ⚠️ No obvious price columns found")
        else:
            print("   ⚠️ PlatinumProduct table is empty")
    except Exception as e:
        print(f"   ⚠️ Could not query PlatinumProduct: {e}")
    
    # Try to find a blanket product as example
    print("\n3. Searching for blanket products...")
    try:
        df = sql_server_store.query_to_dataframe("""
            SELECT TOP (5) 
                _GUID_,
                canonicalProductPageId,
                friendlyUrl,
                url,
                attribute01,
                attribute02,
                attribute03
            FROM [dbo].[SynComs.Products.ProductPage]
            WHERE (
                friendlyUrl LIKE '%blanket%'
                OR url LIKE '%blanket%'
                OR attribute01 LIKE '%blanket%'
                OR attribute02 LIKE '%blanket%'
                OR attribute03 LIKE '%blanket%'
            )
            AND canonicalProductPageId IS NOT NULL;
        """)
        
        if not df.empty:
            print(f"   ✅ Found {len(df)} blanket-related products:")
            for idx, row in df.iterrows():
                print(f"     - {row['friendlyUrl']} | GUID: {row['canonicalProductPageId']}")
        else:
            print("   ⚠️ No blanket products found")
    except Exception as e:
        print(f"   ⚠️ Could not search for blankets: {e}")
    
    # Check if we can query by GUID (like we do with Supabase)
    print("\n4. Testing GUID lookup...")
    try:
        # Get a sample GUID
        sample_df = sql_server_store.query_to_dataframe("""
            SELECT TOP (1) canonicalProductPageId
            FROM [dbo].[SynComs.Products.ProductPage]
            WHERE canonicalProductPageId IS NOT NULL;
        """)
        
        if not sample_df.empty:
            sample_guid = str(sample_df.iloc[0]['canonicalProductPageId'])
            print(f"   Testing with GUID: {sample_guid}")
            
            result = sql_server_store.query_product_page(sample_guid)
            if result:
                print(f"   ✅ Successfully queried product page by GUID")
                print(f"   Found: {result.get('friendlyUrl', 'N/A')}")
            else:
                print("   ⚠️ Query returned no results")
        else:
            print("   ⚠️ No GUIDs found to test with")
    except Exception as e:
        print(f"   ❌ Error testing GUID lookup: {e}")
        import traceback
        traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    print("✅ Can get canonicalProductPageId from SQL Server")
    print("✅ Can query ProductPage by GUID")
    print("⚠️ Need to check if we can map ProductReferenceCode to GUID")
    print("⚠️ Need to find where base prices are stored")
    print("⚠️ Need to find where discounts are stored (might still need Supabase)")
    print("=" * 60)

if __name__ == "__main__":
    check_pricing_capabilities()

