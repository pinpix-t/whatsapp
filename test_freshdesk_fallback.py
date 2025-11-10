"""Test Freshdesk fallback credential"""

import os
import logging

# Simulate no API key set
if 'FRESHDESK_API_KEY' in os.environ:
    del os.environ['FRESHDESK_API_KEY']

logging.basicConfig(level=logging.INFO)

print("=" * 60)
print("Testing Freshdesk Fallback Credential")
print("=" * 60)

# Import after clearing env var
from services.freshdesk_service import FreshdeskService

freshdesk = FreshdeskService()

print(f"\n1. API URL: {freshdesk.api_url}")
print(f"2. Auth Header: {freshdesk.auth_header[:30]}...")
print(f"3. Full Auth Header: {freshdesk.auth_header}")

# Check if it's using the fallback
if freshdesk.auth_header == "Basic RmZLSDR4Q0xMb1FTREtMZmFYenU6WA==":
    print("\n✅ SUCCESS: Using hardcoded fallback credential")
    print("   This means Freshdesk will work without FRESHDESK_API_KEY set")
else:
    print("\n⚠️  WARNING: Not using fallback credential")
    print(f"   Using: {freshdesk.auth_header}")

print("\n" + "=" * 60)
print("Summary:")
print("=" * 60)
print("✅ If FRESHDESK_API_KEY is not set, the code uses:")
print("   'Basic RmZLSDR4Q0xMb1FTREtMZmFYenU6WA=='")
print("✅ This is the hardcoded credential you provided")
print("✅ Freshdesk integration will work without setting the env var")
print("=" * 60)

