import os
import time
import requests
import yfinance as yf
from google import genai

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = str(os.environ.get("TELEGRAM_CHAT_ID", ""))
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
BASE = f"https://api.telegram.org/bot{TOKEN}"

def send_msg(text):
    if not text:
        return
    for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
        try:
            requests.post(
                f"{BASE}/sendMessage",
                json={"chat_id": CHAT_ID, "text": chunk, "parse_mode": "Markdown"},
                timeout=10,
            )
        except Exception:
            pass
        time.sleep(0.5)

def get_ai_report(custom_prompt=None):
    news = ""
    for t in ["^GSPC", "^VIX"]:
        try:
            for n in yf.Ticker(t).news[:2]:
                title = n.get("title") or n.get("content", {}).get("title")
                if title:
                    news += f"- {title}\\n"
        except Exception:
            continue
    prompt = custom_prompt if custom_prompt else (
        f"ענה בעברית כמחלקת מחקר גולדמן סאקס. נתח: {news}\\n"
        f"מבנה: ## דוח אסטרטגי\\n### 🏛️ 1. הכסף הגדול\\n"
        f"### 💣 2. מוקשים ומאקרו\\n### 🌡️ 3. סנטימנט"
    )
    try:
        client = genai.Client(api_key=GEMINI_KEY)
        target = next((m.name for m in client.models.list() if "flash" in m.name), "gemini-1.5-flash")
        return client.models.generate_content(model=target, contents=prompt).text
    except Exception:
        return "⚠️ AI Summary Unavailable"

def main():
    ai_report = get_ai_report()
    send_msg(f"🤖 *Market Sentiment AI Report*\\n\\n{ai_report}")

if __name__ == "__main__":
    main()
