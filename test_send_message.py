"""
Script to send a test message via WhatsApp API
This opens the 24-hour conversation window
"""
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

# Get credentials from environment
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
RECIPIENT_NUMBER = os.getenv("TEST_PHONE_NUMBER")  # Your phone number

if not all([WHATSAPP_TOKEN, PHONE_NUMBER_ID, RECIPIENT_NUMBER]):
    print("❌ Missing environment variables!")
    print(f"WHATSAPP_TOKEN: {'✅' if WHATSAPP_TOKEN else '❌'}")
    print(f"PHONE_NUMBER_ID: {'✅' if PHONE_NUMBER_ID else '❌'}")
    print(f"TEST_PHONE_NUMBER: {'✅' if RECIPIENT_NUMBER else '❌'}")
    print("\nSet TEST_PHONE_NUMBER=+447822035766 (your number) in .env")
    sys.exit(1)

BASE_URL = "https://graph.facebook.com/v18.0"

# Send text message
url = f"{BASE_URL}/{PHONE_NUMBER_ID}/messages"

headers = {
    "Authorization": f"Bearer {WHATSAPP_TOKEN}",
    "Content-Type": "application/json"
}

# For test - try text message first (might work in test mode)
payload = {
    "messaging_product": "whatsapp",
    "recipient_type": "individual",
    "to": RECIPIENT_NUMBER.replace("+", ""),  # Remove + from phone number
    "type": "text",
    "text": {
        "preview_url": False,
        "body": "Hello! This is your PrinterPix WhatsApp bot. You can now send me messages and I'll reply! 📱"
    }
}

try:
    print(f"📤 Sending test message to {RECIPIENT_NUMBER}...")
    response = requests.post(url, headers=headers, json=payload, timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Message sent successfully!")
        print(f"Message ID: {data.get('messages', [{}])[0].get('id', 'N/A')}")
        print("\n📱 Check your WhatsApp - you should receive the message!")
        print("🔓 After receiving it, you can send messages and the bot will reply.")
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"Response: {response.text}")
        print("\n💡 If you see error about template, try adding your number to test list in Meta.")
        
except Exception as e:
    print(f"❌ Error sending message: {e}")

