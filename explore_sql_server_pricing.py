"""Explore SQL Server to find pricing-related tables and data"""

from database.sql_server_store import sql_server_store
import pandas as pd

def explore_tables():
    """Explore what tables exist in the database"""
    print("=" * 60)
    print("Exploring SQL Server Tables")
    print("=" * 60)
    
    # Get all tables
    print("\n1. Listing all tables in the database...")
    try:
        df = sql_server_store.query_to_dataframe("""
            SELECT 
                TABLE_SCHEMA,
                TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_SCHEMA, TABLE_NAME;
        """)
        
        if not df.empty:
            print(f"   ✅ Found {len(df)} tables:")
            for idx, row in df.iterrows():
                print(f"     - [{row['TABLE_SCHEMA']}].[{row['TABLE_NAME']}]")
        else:
            print("   ⚠️ No tables found")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    # Look for pricing-related tables
    print("\n2. Searching for pricing-related tables...")
    try:
        df = sql_server_store.query_to_dataframe("""
            SELECT 
                TABLE_SCHEMA,
                TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE = 'BASE TABLE'
            AND (
                TABLE_NAME LIKE '%price%' 
                OR TABLE_NAME LIKE '%Price%'
                OR TABLE_NAME LIKE '%PRICE%'
                OR TABLE_NAME LIKE '%pricing%'
                OR TABLE_NAME LIKE '%Pricing%'
                OR TABLE_NAME LIKE '%discount%'
                OR TABLE_NAME LIKE '%Discount%'
            )
            ORDER BY TABLE_SCHEMA, TABLE_NAME;
        """)
        
        if not df.empty:
            print(f"   ✅ Found {len(df)} pricing-related tables:")
            for idx, row in df.iterrows():
                print(f"     - [{row['TABLE_SCHEMA']}].[{row['TABLE_NAME']}]")
        else:
            print("   ⚠️ No pricing-related tables found")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Check ProductPage table structure
    print("\n3. Checking ProductPage table structure...")
    try:
        df = sql_server_store.query_to_dataframe("""
            SELECT 
                COLUMN_NAME,
                DATA_TYPE,
                IS_NULLABLE,
                CHARACTER_MAXIMUM_LENGTH
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'dbo'
            AND TABLE_NAME = 'SynComs.Products.ProductPage'
            ORDER BY ORDINAL_POSITION;
        """)
        
        if not df.empty:
            print(f"   ✅ Found {len(df)} columns in ProductPage table:")
            for idx, row in df.iterrows():
                col_type = row['DATA_TYPE']
                if row['CHARACTER_MAXIMUM_LENGTH']:
                    col_type += f"({row['CHARACTER_MAXIMUM_LENGTH']})"
                nullable = "NULL" if row['IS_NULLABLE'] == 'YES' else "NOT NULL"
                print(f"     - {row['COLUMN_NAME']:40} | {col_type:20} | {nullable}")
        else:
            print("   ⚠️ Table structure not found")
    except Exception as e:
        print(f"   ⚠️ Could not get table structure: {e}")
    
    # Sample ProductPage data
    print("\n4. Sample ProductPage data...")
    try:
        df = sql_server_store.query_to_dataframe("""
            SELECT TOP (3) *
            FROM [dbo].[SynComs.Products.ProductPage];
        """)
        
        if not df.empty:
            print(f"   ✅ Sample data ({len(df)} rows):")
            print(f"   Columns: {', '.join(df.columns.tolist()[:10])}...")
            print("\n   First row sample:")
            for col in df.columns[:10]:
                val = df.iloc[0][col]
                if isinstance(val, str) and len(str(val)) > 50:
                    val = str(val)[:50] + "..."
                print(f"     {col}: {val}")
        else:
            print("   ⚠️ No data found")
    except Exception as e:
        print(f"   ⚠️ Could not get sample data: {e}")
    
    # Look for canonicalProductPageId
    print("\n5. Checking for canonicalProductPageId column...")
    try:
        df = sql_server_store.query_to_dataframe("""
            SELECT TOP (1) canonicalProductPageId
            FROM [dbo].[SynComs.Products.ProductPage]
            WHERE canonicalProductPageId IS NOT NULL;
        """)
        
        if not df.empty:
            print(f"   ✅ Found canonicalProductPageId:")
            print(f"     Sample GUID: {df.iloc[0]['canonicalProductPageId']}")
        else:
            print("   ⚠️ No canonicalProductPageId found")
    except Exception as e:
        print(f"   ⚠️ Could not check canonicalProductPageId: {e}")
    
    # Look for price-related columns in ProductPage
    print("\n6. Searching for price-related columns in ProductPage...")
    try:
        df = sql_server_store.query_to_dataframe("""
            SELECT 
                COLUMN_NAME,
                DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'dbo'
            AND TABLE_NAME = 'SynComs.Products.ProductPage'
            AND (
                COLUMN_NAME LIKE '%price%' 
                OR COLUMN_NAME LIKE '%Price%'
                OR COLUMN_NAME LIKE '%cost%'
                OR COLUMN_NAME LIKE '%Cost%'
                OR COLUMN_NAME LIKE '%amount%'
                OR COLUMN_NAME LIKE '%Amount%'
            )
            ORDER BY COLUMN_NAME;
        """)
        
        if not df.empty:
            print(f"   ✅ Found {len(df)} price-related columns:")
            for idx, row in df.iterrows():
                print(f"     - {row['COLUMN_NAME']} ({row['DATA_TYPE']})")
        else:
            print("   ⚠️ No price-related columns found in ProductPage table")
    except Exception as e:
        print(f"   ⚠️ Could not search for price columns: {e}")
    
    print("\n" + "=" * 60)
    print("Exploration complete!")
    print("=" * 60)

if __name__ == "__main__":
    explore_tables()

