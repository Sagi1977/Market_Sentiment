#!/usr/bin/env python3
import json
import math
import os
from datetime import datetime, timezone

import requests
import yfinance as yf

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
ANALYSTS_FILE = os.getenv("ANALYSTS_FILE", "analysts.json")

MARKETS = {
    "SPY": "S&P 500",
    "QQQ": "Nasdaq 100",
    "IWM": "Russell 2000",
    "DIA": "Dow Jones",
    "BTC-USD": "Bitcoin",
    "ETH-USD": "Ethereum",
    "^VIX": "VIX",
    "DX-Y.NYB": "DXY",
    "^TNX": "US 10Y",
}

STANCE_MAP = {
    "bullish": 1.0,
    "positive": 0.5,
    "neutral": 0.0,
    "negative": -0.5,
    "bearish": -1.0,
}


def pct(a, b):
    if a in (None, 0) or b in (None, 0):
        return None
    return ((a / b) - 1) * 100


def safe_num(v):
    try:
        if v is None:
            return None
        x = float(v)
        if math.isnan(x):
            return None
        return x
    except Exception:
        return None


def load_analysts(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    analysts = data.get("analysts", [])
    compass, flow = [], []
    for a in analysts:
        stance = STANCE_MAP.get(str(a.get("stance", "neutral")).lower(), 0.0)
        weight = safe_num(a.get("weight")) or 1.0
        group = str(a.get("group", "flow")).lower()
        item = {
            "name": a.get("name", "Unknown"),
            "stance": stance,
            "weight": weight,
            "comment": a.get("comment", ""),
            "label": a.get("stance", "neutral"),
        }
        if group == "compass":
            compass.append(item)
        else:
            flow.append(item)
    return compass, flow


def weighted_group_score(items):
    if not items:
        return 0.0
    total_w = sum(i["weight"] for i in items)
    if total_w == 0:
        return 0.0
    return sum(i["stance"] * i["weight"] for i in items) / total_w


def fetch_market_data():
    tickers = list(MARKETS.keys())
    raw = yf.download(tickers=tickers, period="10d", interval="1d", auto_adjust=False, progress=False, group_by="ticker", threads=True)
    results = {}
    for t in tickers:
        try:
            frame = raw[t].dropna(how="all")
        except Exception:
            frame = None
        if frame is None or frame.empty:
            results[t] = None
            continue
        closes = frame["Close"].dropna().tolist()
        if len(closes) < 2:
            results[t] = None
            continue
        last_close = safe_num(closes[-1])
        prev_close = safe_num(closes[-2])
        week_base = safe_num(closes[-6]) if len(closes) >= 6 else safe_num(closes[0])
        results[t] = {
            "name": MARKETS[t],
            "price": last_close,
            "day_pct": pct(last_close, prev_close),
            "week_pct": pct(last_close, week_base),
        }
    return results


def score_from_market(data):
    score = 0.0
    details = {}

    def val(t, k):
        item = data.get(t) or {}
        return item.get(k)

    equities = []
    for t in ["SPY", "QQQ", "IWM", "DIA"]:
        d = val(t, "day_pct") or 0.0
        w = val(t, "week_pct") or 0.0
        s = (d * 0.35 + w * 0.65) / 5.0
        equities.append(s)
    equities_score = sum(equities) / len(equities)
    score += equities_score * 0.40
    details["equities"] = equities_score

    crypto = []
    for t in ["BTC-USD", "ETH-USD"]:
        d = val(t, "day_pct") or 0.0
        w = val(t, "week_pct") or 0.0
        s = (d * 0.3 + w * 0.7) / 6.0
        crypto.append(s)
    crypto_score = sum(crypto) / len(crypto)
    score += crypto_score * 0.20
    details["crypto"] = crypto_score

    vix = val("^VIX", "day_pct") or 0.0
    dxy = val("DX-Y.NYB", "week_pct") or 0.0
    tnx = val("^TNX", "week_pct") or 0.0
    risk_pressure = -((vix / 8.0) + (dxy / 4.0) + (tnx / 4.0)) / 3.0
    score += risk_pressure * 0.20
    details["risk_pressure"] = risk_pressure

    breadth_hint = 0.0
    if (val("SPY", "week_pct") or 0) > 0 and (val("IWM", "week_pct") or 0) > 0:
        breadth_hint += 0.4
    if (val("QQQ", "week_pct") or 0) > 0 and (val("DIA", "week_pct") or 0) > 0:
        breadth_hint += 0.3
    if (val("BTC-USD", "week_pct") or 0) > 0:
        breadth_hint += 0.3
    score += breadth_hint * 0.20
    details["breadth"] = breadth_hint

    return max(-2.0, min(2.0, score)), details


def regime_label(score):
    if score >= 0.75:
        return "RISK-ON"
    if score >= 0.25:
        return "CONSTRUCTIVE"
    if score > -0.25:
        return "NEUTRAL"
    if score > -0.75:
        return "CAUTIOUS"
    return "RISK-OFF"


def bucket_label(x):
    if x >= 0.6:
        return "חיובי"
    if x >= 0.2:
        return "נוטה לחיובי"
    if x > -0.2:
        return "מעורב"
    if x > -0.6:
        return "נוטה לשלילי"
    return "שלילי"


def analyst_line(items):
    if not items:
        return "ללא נתונים"
    parts = [f"{i['name']}: {i['label']}" for i in items]
    return ", ".join(parts)


def bottom_line(total_score, market_details, compass_score, flow_score):
    eq = market_details.get("equities", 0.0)
    cr = market_details.get("crypto", 0.0)
    rp = market_details.get("risk_pressure", 0.0)
    if total_score >= 0.75:
        return "התמונה הכללית חיובית. אפשר להחזיק הטיה שורית, אבל להעדיף חוזק מוכח ולא לרדוף אחרי מהלכים חדים מדי."
    if total_score >= 0.25:
        return "יש יתרון לשוורים, אך עדיין עדיף לפעול בצורה סלקטיבית ולתת עדיפות לנכסים שממשיכים להראות הובלה."
    if total_score > -0.25:
        return "השוק כרגע מעורב. עדיף לשמור על גישה מאוזנת, להקטין אגרסיביות, ולהמתין לאישור ברור יותר."
    if rp < -0.4:
        return "לחץ הסיכון בשוק עולה. עדיף להיות זהיר, להקטין חשיפה, ולא להתאהב בנרטיב חיובי בלי אישור מהמחיר."
    if cr > eq:
        return "הסנטימנט נחלש, אך הקריפטו מחזיק טוב יותר מהמניות. אם פועלים, עדיף לבחור חוזק יחסי ברור מאוד."
    return "התמונה הכללית זהירה עד שלילית. עדיף להתמקד בהגנה, סבלנות, ומעקב אחרי שיפור אמיתי בנתוני השוק."


def fmt_pct(x):
    return "N/A" if x is None else f"{x:+.1f}%"


def build_message(data, market_score, details, compass_items, flow_items, compass_score, flow_score):
    total_score = market_score * 0.5 + compass_score * 0.25 + flow_score * 0.25
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = []
    lines.append("🧭 *Market Sentiment MVP*")
    lines.append(f"זמן הרצה: {now}")
    lines.append("")
    lines.append(f"*Regime:* {regime_label(total_score)}")
    lines.append(f"*מניות:* {bucket_label(details.get('equities', 0.0))}")
    lines.append(f"*קריפטו:* {bucket_label(details.get('crypto', 0.0))}")
    lines.append(f"*לחץ סיכון:* {bucket_label(details.get('risk_pressure', 0.0))}")
    lines.append(f"*Breadth:* {bucket_label(details.get('breadth', 0.0))}")
    lines.append(f"*Compass:* {bucket_label(compass_score)}")
    lines.append(f"*Flow:* {bucket_label(flow_score)}")
    lines.append("")
    lines.append("*שינויי שוק מרכזיים:*" )
    for t in ["SPY", "QQQ", "IWM", "BTC-USD", "ETH-USD", "^VIX"]:
        item = data.get(t)
        if not item:
            continue
        lines.append(f"- {item['name']}: יום {fmt_pct(item['day_pct'])} | שבוע {fmt_pct(item['week_pct'])}")
    lines.append("")
    lines.append(f"*Compass Analysts:* {analyst_line(compass_items)}")
    lines.append(f"*Flow Analysts:* {analyst_line(flow_items)}")
    lines.append("")
    lines.append(f"*שורה תחתונה:* {bottom_line(total_score, details, compass_score, flow_score)}")
    return "\n".join(lines)


def send_telegram(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        raise RuntimeError("Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID")
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    r = requests.post(url, json=payload, timeout=20)
    r.raise_for_status()
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram API error: {data}")


def main():
    compass_items, flow_items = load_analysts(ANALYSTS_FILE)
    market_data = fetch_market_data()
    market_score, details = score_from_market(market_data)
    compass_score = weighted_group_score(compass_items)
    flow_score = weighted_group_score(flow_items)
    message = build_message(market_data, market_score, details, compass_items, flow_items, compass_score, flow_score)
    send_telegram(message)
    print("Market sentiment report sent successfully.")


if __name__ == "__main__":
    main()
