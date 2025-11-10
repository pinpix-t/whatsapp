"""Test the complete bulk pricing flow"""

from services.bulk_pricing import bulk_pricing_service
import logging

logging.basicConfig(level=logging.INFO)

def test_bulk_pricing_flow():
    """Test the complete bulk pricing flow"""
    print("=" * 60)
    print("Testing Bulk Pricing Flow")
    print("=" * 60)
    
    # Test with Sherpa Baby blanket
    print("\n1. Testing Sherpa Baby Blanket (25x20)...")
    selections = {
        "product": "blankets",
        "fabric": "fabric_sherpa",
        "size": "size_baby_20x25"
    }
    quantity = 50
    
    result = bulk_pricing_service.get_bulk_price_info(
        selections=selections,
        quantity=quantity,
        offer_type="second_offer"  # Worse discount first
    )
    
    print(f"\n   Product Reference Code: {result.get('product_reference_code')}")
    print(f"   Base Price: £{result.get('base_price', 0):.2f}")
    print(f"   Discount: {result.get('discount_percent', 0):.1f}%")
    print(f"   Unit Price (after discount): {result.get('formatted_unit_price', 'N/A')}")
    print(f"   Total Price ({quantity} units): {result.get('formatted_total_price', 'N/A')}")
    print(f"   Success: {result.get('success')}")
    
    if result.get('error_message'):
        print(f"   Error: {result.get('error_message')}")
    
    # Verify calculation
    if result.get('base_price') and result.get('discount_percent'):
        base_price = result.get('base_price')
        discount = result.get('discount_percent')
        unit_price = result.get('unit_price')
        total_price = result.get('total_price')
        
        expected_unit_price = base_price * (1 - discount / 100)
        expected_total_price = expected_unit_price * quantity
        
        print(f"\n   Verification:")
        print(f"     Expected unit price: £{expected_unit_price:.2f}")
        print(f"     Actual unit price: £{unit_price:.2f}")
        print(f"     Match: {'✅' if abs(unit_price - expected_unit_price) < 0.01 else '❌'}")
        print(f"     Expected total price: £{expected_total_price:.2f}")
        print(f"     Actual total price: £{total_price:.2f}")
        print(f"     Match: {'✅' if abs(total_price - expected_total_price) < 0.01 else '❌'}")
    
    # Test with better discount
    print("\n2. Testing with better discount (first_offer)...")
    result2 = bulk_pricing_service.get_bulk_price_info(
        selections=selections,
        quantity=quantity,
        offer_type="first_offer"  # Better discount
    )
    
    print(f"   Base Price: £{result2.get('base_price', 0):.2f}")
    print(f"   Discount: {result2.get('discount_percent', 0):.1f}%")
    print(f"   Unit Price (after discount): {result2.get('formatted_unit_price', 'N/A')}")
    print(f"   Total Price ({quantity} units): {result2.get('formatted_total_price', 'N/A')}")
    
    # Compare discounts
    if result.get('discount_percent') and result2.get('discount_percent'):
        print(f"\n   Discount Comparison:")
        print(f"     Second offer (worse): {result.get('discount_percent'):.1f}%")
        print(f"     First offer (better): {result2.get('discount_percent'):.1f}%")
        if result2.get('discount_percent') > result.get('discount_percent'):
            print(f"     ✅ Better discount is higher (as expected)")
        else:
            print(f"     ⚠️ Discounts may be reversed")
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    print("✅ Flow: SQL Server (base price) → Supabase (discount) → Calculate")
    print("✅ Base price from SQL Server: Pre-discount price")
    print("✅ Discount from Supabase: Percentage to apply")
    print("✅ Final price: Base price × (1 - discount/100) × quantity")
    print("=" * 60)

if __name__ == "__main__":
    test_bulk_pricing_flow()

