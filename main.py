import os
import time
import requests
import yfinance as yf
from google import genai

print("=== DEBUG START ===")

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = str(os.environ.get("TELEGRAM_CHAT_ID", ""))
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

print(f"TOKEN len: {len(TOKEN) if TOKEN else 0}")
print(f"CHAT_ID: '{CHAT_ID}'")
print(f"GEMINI_KEY len: {len(GEMINI_KEY) if GEMINI_KEY else 0}")

if not TOKEN or not CHAT_ID:
    print("❌ CRITICAL: Missing TELEGRAM_TOKEN or CHAT_ID")
    exit(1)

if not GEMINI_KEY:
    print("⚠️ WARNING: No GEMINI_KEY - using fallback")
    ai_report = "TEST: No Gemini key, but Telegram should work"
else:
    print("🤖 Calling Gemini...")
    try:
        client = genai.Client(api_key=GEMINI_KEY)
        response = client.models.generate_content("test").text
        ai_report = f"🤖 Gemini OK: {response[:100]}"
    except Exception as e:
        print(f"Gemini error: {e}")
        ai_report = "⚠️ Gemini failed"

print(f"Report: {ai_report[:100]}")

# Test Telegram
BASE = f"https://api.telegram.org/bot{TOKEN}"
try:
    resp = requests.post(
        f"{BASE}/sendMessage",
        json={"chat_id": CHAT_ID, "text": f"🤖 *TEST* {ai_report}", "parse_mode": "Markdown"},
        timeout=10
    )
    print(f"Telegram response: {resp.status_code} {resp.text}")
except Exception as e:
    print(f"Telegram error: {e}")

print("=== DEBUG END ===")
