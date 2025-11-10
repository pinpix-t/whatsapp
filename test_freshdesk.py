"""Test Freshdesk integration"""

from services.freshdesk_service import FreshdeskService
import logging

logging.basicConfig(level=logging.INFO)

def test_freshdesk():
    """Test Freshdesk ticket creation"""
    print("=" * 60)
    print("Testing Freshdesk Integration")
    print("=" * 60)
    
    freshdesk = FreshdeskService()
    
    print("\n1. Testing Freshdesk connection...")
    print(f"   API URL: {freshdesk.api_url}")
    print(f"   Auth Header: {freshdesk.auth_header[:20]}...")
    
    # Test ticket creation (use a test email)
    print("\n2. Testing ticket creation...")
    print("   ⚠️  This will create a REAL ticket in Freshdesk!")
    print("   Press Ctrl+C to cancel, or wait 5 seconds...")
    
    import time
    time.sleep(5)
    
    try:
        result = freshdesk.create_ticket(
            email="test@example.com",
            subject="Test Ticket from WhatsApp Bot",
            description="<p>This is a test ticket created by the WhatsApp bot integration.</p><p>If you see this, the integration is working!</p>",
            product_id=None,
            group_id=None
        )
        
        if result.get("success"):
            ticket_id = result.get("ticket_id")
            print(f"\n   ✅ SUCCESS! Ticket created: ID {ticket_id}")
            print(f"   Check Freshdesk dashboard to verify")
        else:
            error = result.get("error", "Unknown error")
            print(f"\n   ❌ FAILED: {error}")
            print(f"   Status Code: {result.get('status_code', 'N/A')}")
            
    except KeyboardInterrupt:
        print("\n   ⚠️  Test cancelled by user")
    except Exception as e:
        print(f"\n   ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    print("✅ Freshdesk service exists")
    print("✅ Used in bulk ordering when users say 'too expensive'")
    print("⚠️  Credentials are hardcoded (should be in env vars)")
    print("=" * 60)

if __name__ == "__main__":
    test_freshdesk()

