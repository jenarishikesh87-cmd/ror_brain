import os
import requests
import re
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template
from supabase import create_client

app = Flask(__name__)

# ---------------- ENV ----------------
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------- ROR ----------------
def ror_brain(text):
    try:
        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openai/gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are a professional trading assistant."},
                    {"role": "user", "content": text}
                ]
            }
        ).json()

        return res["choices"][0]["message"]["content"]
    except:
        return "Analysis unavailable."

# ---------------- TRADE MEMORY ----------------
def save_trade(asset, decision, entry, tp, sl):
    supabase.table("trades").insert({
        "user_id":"rishi",
        "asset":asset,
        "decision":decision,
        "entry":entry,
        "tp":tp,
        "sl":sl
    }).execute()

# ---------------- REMINDER ----------------
def handle_reminder(text):
    if "remind me" in text.lower():
        return "Reminder system active."
    return None

# ---------------- ROUTES ----------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    msg = request.json.get("message","").strip()

    r = handle_reminder(msg)
    if r:
        return jsonify({"reply":r})

    return jsonify({"reply":ror_brain(msg)})

# ---------------- MAIN TRADING ENGINE ----------------
@app.route("/ror-trade/<asset>")
def ror_trade(asset):
    try:
        asset = asset.lower()

        # -------- FETCH DATA --------
        if asset in ["bitcoin","ethereum","solana"]:
            url = f"https://api.coingecko.com/api/v3/coins/{asset}/market_chart"
            data = requests.get(url, params={"vs_currency":"usd","days":1}).json()
            prices = [p[1] for p in data["prices"]]

        else:
            # STOCK (TwelveData)
            stock = asset.upper()
            res = requests.get(f"https://api.twelvedata.com/time_series?symbol={stock}&interval=5min&apikey=demo").json()
            prices = [float(x["close"]) for x in res["values"]][::-1]

        current = prices[-1]

        # -------- EMA --------
        def ema(data, period):
            k = 2/(period+1)
            val = data[0]
            for p in data[1:]:
                val = p*k + val*(1-k)
            return val

        ema_fast = ema(prices[-30:], 9)
        ema_mid = ema(prices[-60:], 21)

        # -------- RSI --------
        def rsi(data):
            gains, losses = [], []
            for i in range(1,15):
                d = data[-i] - data[-i-1]
                if d>0: gains.append(d)
                else: losses.append(abs(d))
            g = sum(gains)/14 if gains else 0.001
            l = sum(losses)/14 if losses else 0.001
            return 100-(100/(1+(g/l)))

        rsi_val = rsi(prices)

        # -------- MOMENTUM --------
        momentum = (prices[-1] - prices[-5]) / prices[-5] * 100

        # -------- VOLUME (PROXY) --------
        volume_strength = abs(momentum)

        # -------- ORDERBOOK (BINANCE) --------
        liquidity = 0
        try:
            symbol = asset.upper() + "USDT"
            ob = requests.get(f"https://api.binance.com/api/v3/depth?symbol={symbol}&limit=5").json()
            bids = sum([float(b[1]) for b in ob["bids"]])
            asks = sum([float(a[1]) for a in ob["asks"]])
            liquidity = bids - asks
        except:
            pass

        # -------- MULTI TIMEFRAME --------
        fast_trend = ema_fast > ema_mid
        mid_trend = ema(prices[-80:], 21) > ema(prices[-120:], 50)

        # -------- SESSION --------
        hour = datetime.utcnow().hour
        session = "ASIA"
        if 7 <= hour <= 15:
            session = "LONDON"
        elif 13 <= hour <= 22:
            session = "NEW YORK"

        # -------- STRUCTURE --------
        support = min(prices[-50:])
        resistance = max(prices[-50:])

        # -------- SCORING --------
        score = 0
        signals = []

        if rsi_val < 30:
            score += 2; signals.append("Oversold")
        elif rsi_val > 70:
            score -= 2; signals.append("Overbought")

        if fast_trend and mid_trend:
            score += 2; signals.append("Trend aligned")
        else:
            score -= 1

        if momentum > 0.5:
            score += 1; signals.append("Momentum Up")
        elif momentum < -0.5:
            score -= 1; signals.append("Momentum Down")

        if liquidity > 0:
            score += 1; signals.append("Buy pressure")
        elif liquidity < 0:
            score -= 1; signals.append("Sell pressure")

        if session == "NEW YORK":
            score += 1; signals.append("High volume session")

        # -------- DECISION --------
        if score >= 4:
            decision = "BUY"
        elif score <= -4:
            decision = "SELL"
        else:
            decision = "HOLD"

        confidence = min(95, abs(score)*15 + 40)

        # -------- RISK --------
        entry = current
        tp = resistance if decision=="BUY" else support
        sl = support if decision=="BUY" else resistance

        # SAVE TRADE
        if decision != "HOLD":
            save_trade(asset, decision, entry, tp, sl)

        # -------- AI EXPLANATION --------
        explanation = ror_brain(f"""
Asset {asset}
RSI {rsi_val:.2f}
Momentum {momentum:.2f}
Liquidity {liquidity}
Session {session}
Signals {signals}
Decision {decision}

Explain briefly.
""")

        return jsonify({
            "price": round(entry,2),
            "analysis":{
                "decision":decision,
                "confidence":int(confidence),
                "reason":explanation,
                "entry":round(entry,2),
                "tp":round(tp,2),
                "sl":round(sl,2),
                "signals":signals,
                "session":session
            }
        })

    except Exception as e:
        return jsonify({"error":str(e)})

# ---------------- START ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0", port=port)
