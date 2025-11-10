"""Test Freshdesk with real API call"""

import os
import logging

# Simulate no API key set (use fallback)
if 'FRESHDESK_API_KEY' in os.environ:
    del os.environ['FRESHDESK_API_KEY']

logging.basicConfig(level=logging.INFO)

print("=" * 60)
print("Testing Freshdesk with Real API Call")
print("=" * 60)

from services.freshdesk_service import FreshdeskService

freshdesk = FreshdeskService()

print(f"\n1. API URL: {freshdesk.api_url}")
print(f"2. Using fallback credential: {freshdesk.auth_header[:30]}...")

# Test with a real API call (but don't actually create a ticket)
print("\n3. Testing API connection...")
print("   ⚠️  This will make a REAL API call to Freshdesk!")
print("   Press Ctrl+C to cancel, or wait 3 seconds...")

import time
time.sleep(3)

try:
    # Try to create a test ticket (use a test email)
    print("\n4. Attempting to create test ticket...")
    result = freshdesk.create_ticket(
        email="test@example.com",
        subject="Test Ticket from WhatsApp Bot - Please Ignore",
        description="<p>This is a test ticket to verify the Freshdesk integration is working.</p><p>Please ignore or delete this ticket.</p>",
        product_id=None,
        group_id=None
    )
    
    if result.get("success"):
        ticket_id = result.get("ticket_id")
        print(f"\n   ✅ SUCCESS! Freshdesk API call worked!")
        print(f"   Ticket ID: {ticket_id}")
        print(f"   Check Freshdesk dashboard to verify the ticket was created")
        print(f"\n   ⚠️  Note: A test ticket was created in Freshdesk")
        print(f"   You may want to delete it from the Freshdesk dashboard")
    else:
        error = result.get("error", "Unknown error")
        status_code = result.get("status_code", "N/A")
        print(f"\n   ❌ FAILED: {error}")
        print(f"   Status Code: {status_code}")
        
        if status_code == 401:
            print(f"   ⚠️  Authentication failed - the credential might be invalid")
        elif status_code == 403:
            print(f"   ⚠️  Forbidden - check permissions")
        else:
            print(f"   ⚠️  Check the error message above")
            
except KeyboardInterrupt:
    print("\n   ⚠️  Test cancelled by user")
except Exception as e:
    print(f"\n   ❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Summary:")
print("=" * 60)
if result.get("success"):
    print("✅ Freshdesk integration is WORKING!")
    print("✅ The hardcoded credential is valid")
    print("✅ No need to set FRESHDESK_API_KEY")
else:
    print("❌ Freshdesk integration FAILED")
    print("⚠️  Check the error message above")
    print("⚠️  You may need to verify the credential")
print("=" * 60)

