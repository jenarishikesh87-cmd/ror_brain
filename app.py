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

# ---------------- REMINDER ----------------
def handle_reminder(text):
    t = text.lower()

    if "show my reminders" in t:
        r = supabase.table("reminders").select("*").eq("user_id","rishi").eq("triggered",False).execute()
        return "\n".join([x["text"] for x in r.data]) if r.data else "No reminders."

    m = re.search(r"remind me in (\d+) minutes? to (.+)", t)
    if m:
        mins = int(m.group(1))
        task = m.group(2)

        supabase.table("reminders").insert({
            "user_id":"rishi",
            "text":task,
            "remind_at":(datetime.now()+timedelta(minutes=mins)).isoformat(),
            "triggered":False
        }).execute()

        return f"Reminder set for {task}"

    return None

# ---------------- ROUTES ----------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    msg = request.json.get("message","").strip()

    if not msg:
        return jsonify({"reply":"Say something."})

    r = handle_reminder(msg)
    if r:
        return jsonify({"reply":r})

    return jsonify({"reply":ror_brain(msg)})

@app.route("/check-reminder")
def check_reminder():
    now = datetime.now().isoformat()

    r = supabase.table("reminders") \
        .select("*") \
        .eq("user_id","rishi") \
        .lte("remind_at",now) \
        .eq("triggered",False) \
        .execute()

    if r.data:
        rem = r.data[0]
        supabase.table("reminders").update({"triggered":True}).eq("id",rem["id"]).execute()
        return jsonify({"reminder":rem["text"]})

    return jsonify({"reminder":None})

# ---------------- PRO TRADING ENGINE ----------------
@app.route("/ror-trade")
def ror_trade():
    try:
        # -------- DATA --------
        data = requests.get(
            "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart",
            params={"vs_currency":"usd","days":1}
        ).json()

        prices = [p[1] for p in data["prices"]]
        current = prices[-1]

        # -------- EMA --------
        def ema(data, period):
            k = 2/(period+1)
            val = data[0]
            for p in data[1:]:
                val = p*k + val*(1-k)
            return val

        ema_fast = ema(prices[-30:], 9)
        ema_slow = ema(prices[-60:], 21)

        trend = "UP" if ema_fast > ema_slow else "DOWN"

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

        # -------- STRUCTURE --------
        support = min(prices[-50:])
        resistance = max(prices[-50:])

        near_support = current <= support * 1.01
        near_resistance = current >= resistance * 0.99

        # -------- VOLATILITY --------
        volatility = (max(prices[-20:]) - min(prices[-20:])) / current * 100

        # -------- LIQUIDITY TRAP --------
        fake_breakout_up = current > resistance and momentum < 0.3
        fake_breakout_down = current < support and momentum > -0.3

        # -------- SCORING --------
        score = 0
        signals = []

        # RSI
        if rsi_val < 30:
            score += 2; signals.append("Oversold")
        elif rsi_val > 70:
            score -= 2; signals.append("Overbought")

        # Trend
        if trend == "UP":
            score += 2; signals.append("Uptrend")
        else:
            score -= 2; signals.append("Downtrend")

        # Momentum
        if momentum > 0.5:
            score += 1; signals.append("Momentum Up")
        elif momentum < -0.5:
            score -= 1; signals.append("Momentum Down")

        # Structure
        if near_support:
            score += 2; signals.append("Near Support")
        if near_resistance:
            score -= 2; signals.append("Near Resistance")

        # Liquidity trap penalty
        if fake_breakout_up or fake_breakout_down:
            score -= 2
            signals.append("Liquidity Trap")

        # -------- DECISION FILTER --------
        if abs(momentum) < 0.2:
            decision = "HOLD"
        elif score >= 3:
            decision = "BUY"
        elif score <= -3:
            decision = "SELL"
        else:
            decision = "HOLD"

        confidence = min(95, abs(score)*20 + 40)

        # -------- SMART RISK --------
        risk = volatility / 2

        if decision == "BUY":
            entry = current
            tp = min(resistance, current * (1 + risk/100))
            sl = current * (1 - risk/100)

        elif decision == "SELL":
            entry = current
            tp = max(support, current * (1 - risk/100))
            sl = current * (1 + risk/100)

        else:
            entry = tp = sl = current

        # -------- AI EXPLANATION --------
        explanation = ror_brain(f"""
BTC {current}
RSI {rsi_val:.2f}
Momentum {momentum:.2f}
Volatility {volatility:.2f}
Signals {signals}
Decision {decision}

Explain like a pro trader in 1 line.
""")

        return jsonify({
            "price": round(entry,2),
            "analysis":{
                "decision":decision,
                "confidence":int(confidence),
                "reason":explanation,
                "rsi":round(rsi_val,2),
                "entry":round(entry,2),
                "tp":round(tp,2),
                "sl":round(sl,2),
                "signals":signals
            }
        })

    except Exception as e:
        return jsonify({"error":str(e)})

# ---------------- START ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0", port=port)
