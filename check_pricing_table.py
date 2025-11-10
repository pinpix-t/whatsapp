# check_pricing_table.py
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ SUPABASE_URL and SUPABASE_KEY must be set in .env file")
    exit(1)

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=" * 60)
print("Querying pricing_b_d table...")
print("=" * 60)

try:
    # Query all rows (limit to first 5 to see structure)
    response = supabase.table("pricing_b_d").select("*").limit(5).execute()
    
    if response.data and len(response.data) > 0:
        print(f"\n✅ Found {len(response.data)} row(s)")
        print("\n" + "=" * 60)
        print("COLUMNS IN pricing_b_d TABLE:")
        print("=" * 60)
        
        # Get all columns from first row
        first_row = response.data[0]
        columns = list(first_row.keys())
        
        for i, col in enumerate(columns, 1):
            value = first_row[col]
            value_type = type(value).__name__
            print(f"{i}. {col:30} | Type: {value_type:15} | Value: {value}")
        
        print("\n" + "=" * 60)
        print("SAMPLE ROWS:")
        print("=" * 60)
        
        for idx, row in enumerate(response.data, 1):
            print(f"\n--- Row {idx} ---")
            for col, val in row.items():
                print(f"  {col}: {val}")
    else:
        print("⚠️ Table is empty - no rows found")
        
except Exception as e:
    print(f"❌ Error querying table: {e}")
    import traceback
    traceback.print_exc()

