#!/usr/bin/env python3
import os
import sys
print("=== FULL DEBUG ===")
print(f"Python: {sys.version}")
print(f"Args: {sys.argv}")

# Check env
for key in ['TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID', 'GEMINI_API_KEY']:
    val = os.environ.get(key, 'MISSING')
    print(f"{key}: {'OK' if val and len(val)>10 else 'EMPTY'} ({len(val) if val else 0} chars)")

# Test imports
try:
    import requests
    print("✅ requests OK")
except:
    print("❌ requests FAILED")
    sys.exit(1)

try:
    import yfinance as yf
    print("✅ yfinance OK")
except:
    print("❌ yfinance FAILED")
    sys.exit(1)

try:
    from google import genai
    print("✅ genai OK")
except:
    print("❌ genai FAILED")
    sys.exit(1)

print("=== ALL IMPORTS OK ===")

# Test Telegram
TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
if TOKEN and CHAT_ID:
    BASE = f"https://api.telegram.org/bot{TOKEN}"
    try:
        resp = requests.get(f"{BASE}/getMe", timeout=5)
        print(f"Telegram bot info: {resp.status_code} {resp.json().get('ok', False)}")
    except Exception as e:
        print(f"Telegram test failed: {e}")
else:
    print("❌ Skipping Telegram test - missing TOKEN/CHAT_ID")

print("=== DEBUG END ===")
