import os
import time
import requests
import yfinance as yf
from google import genai

print("🚀 Starting Market Sentiment AI...")

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = str(os.environ.get("TELEGRAM_CHAT_ID", ""))
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

print(f"DEBUG: TOKEN={TOKEN[:10] if TOKEN else 'EMPTY'}...")
print(f"DEBUG: CHAT_ID={CHAT_ID}")
print(f"DEBUG: GEMINI_KEY={GEMINI_KEY[:10] if GEMINI_KEY else 'EMPTY'}...")

BASE = f"https://api.telegram.org/bot{TOKEN}"

def send_msg(text):
    print(f"SENDING: {text[:100]}...")
    if not text or not TOKEN or not CHAT_ID:
        print("❌ FAILED: No text/TOKEN/CHAT_ID")
        return
    for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
        try:
            requests.post(
                f"{BASE}/sendMessage",
                json={"chat_id": CHAT_ID, "text": chunk, "parse_mode": "Markdown"},
                timeout=10,
            )
            print("✅ Telegram message sent!")
        except Exception as e:
            print(f"❌ Telegram error: {e}")
        time.sleep(0.5)

def get_ai_report(custom_prompt=None):
    print("📡 Fetching SPY/VIX news...")
    news = ""
    for t in ["^GSPC", "^VIX"]:
        try:
            for n in yf.Ticker(t).news[:2]:
                title = n.get("title") or n.get("content", {}).get("title")
                if title:
                    news += f"- {title}\n"
        except Exception as e:
            print(f"News error {t}: {e}")
            continue
    print(f"📰 News: {news[:200]}...")
    
    prompt = custom_prompt if custom_prompt else (
        f"ענה בעברית כמחלקת מחקר גולדמן סאקס. נתח: {news}\n"
        f"מבנה: ## דוח אסטרטגי\n### 🏛️ 1. הכסף הגדול\n"
        f"### 💣 2. מוקשים ומאקרו\n### 🌡️ 3. סנטימנט"
    )
    
    if not GEMINI_KEY:
        print("❌ No GEMINI_KEY - returning fallback")
        return "⚠️ AI Summary Unavailable - No API Key"
        
    try:
        print("🤖 Calling Gemini...")
        client = genai.Client(api_key=GEMINI_KEY)
        target = next((m.name for m in client.models.list() if "flash" in m.name), "gemini-1.5-flash")
        response = client.models.generate_content(model=target, contents=prompt).text
        print("✅ Gemini response received!")
        return response
    except Exception as e:
        print(f"❌ Gemini error: {e}")
        return "⚠️ AI Summary Unavailable"

def main():
    print("🎯 Generating AI report...")
    ai_report = get_ai_report()
    print(f"📄 Report length: {len(ai_report)} chars")
    send_msg(f"🤖 *Market Sentiment AI Report*\n\n{ai_report}")
    print("🏁 Bot completed!")

if __name__ == "__main__":
    main()
