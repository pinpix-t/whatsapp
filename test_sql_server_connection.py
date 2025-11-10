"""Quick test script to verify SQL Server connection"""

import sys
from database.sql_server_store import sql_server_store

def test_connection():
    """Test SQL Server connection"""
    print("=" * 60)
    print("Testing SQL Server Connection")
    print("=" * 60)
    
    # Test 1: Check connection pool status
    print("\n1. Checking connection pool status...")
    stats = sql_server_store.get_pool_stats()
    print(f"   Status: {stats.get('status')}")
    
    if stats.get('status') != 'connected':
        print("   ❌ Connection failed!")
        print(f"   Error: {stats.get('error', 'Unknown error')}")
        return False
    
    print("   ✅ Connection pool established")
    print(f"   Pool size: {stats.get('pool_size', 'N/A')}")
    print(f"   Total connections: {stats.get('total_connections', 'N/A')}")
    
    # Test 2: Simple query - list databases
    print("\n2. Testing simple query (list databases)...")
    try:
        df = sql_server_store.query_to_dataframe(
            "SELECT TOP (5) name FROM sys.databases ORDER BY name;"
        )
        if not df.empty:
            print("   ✅ Query successful!")
            print(f"   Found {len(df)} databases:")
            for idx, row in df.iterrows():
                print(f"     - {row['name']}")
        else:
            print("   ⚠️ Query returned no results")
    except Exception as e:
        print(f"   ❌ Query failed: {e}")
        return False
    
    # Test 3: Query product page table (if it exists)
    print("\n3. Testing product page table query...")
    try:
        df = sql_server_store.query_to_dataframe(
            "SELECT TOP (5) * FROM [dbo].[SynComs.Products.ProductPage];"
        )
        if not df.empty:
            print("   ✅ Product page table accessible!")
            print(f"   Found {len(df)} rows")
            print(f"   Columns: {', '.join(df.columns[:5].tolist())}...")
        else:
            print("   ⚠️ Table exists but is empty")
    except Exception as e:
        print(f"   ⚠️ Could not query product page table: {e}")
        print("   (This is okay if the table doesn't exist or has different permissions)")
    
    print("\n" + "=" * 60)
    print("✅ Connection test completed successfully!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    try:
        success = test_connection()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

