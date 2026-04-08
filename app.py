import os
import requests
import re
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template, redirect
from supabase import create_client

app = Flask(__name__)

# ---------------- ENV ----------------
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

UPSTOX_API_KEY = os.getenv("UPSTOX_API_KEY")
UPSTOX_SECRET = os.getenv("UPSTOX_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------- STORE TOKEN ----------------
UPSTOX_TOKEN = None

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
                    {"role": "system", "content": "You are a trading assistant."},
                    {"role": "user", "content": text}
                ]
            }
        ).json()

        return res["choices"][0]["message"]["content"]
    except:
        return "Analysis failed."

# ---------------- ROUTES ----------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    msg = request.json.get("message","")
    return jsonify({"reply": ror_brain(msg)})

# ---------------- UPSTOX LOGIN ----------------
@app.route("/upstox-login")
def upstox_login():
    url = f"https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id={UPSTOX_API_KEY}&redirect_uri={REDIRECT_URI}"
    return redirect(url)

# ---------------- CALLBACK ----------------
@app.route("/callback")
def callback():
    global UPSTOX_TOKEN

    code = request.args.get("code")

    res = requests.post(
        "https://api.upstox.com/v2/login/authorization/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "code": code,
            "client_id": UPSTOX_API_KEY,
            "client_secret": UPSTOX_SECRET,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code"
        }
    ).json()

    UPSTOX_TOKEN = res.get("access_token")

    return "✅ Upstox Connected! You can go back."

# ---------------- FETCH PROFILE ----------------
@app.route("/upstox-profile")
def profile():
    if not UPSTOX_TOKEN:
        return jsonify({"error":"Not connected"})

    res = requests.get(
        "https://api.upstox.com/v2/user/profile",
        headers={"Authorization": f"Bearer {UPSTOX_TOKEN}"}
    ).json()

    return jsonify(res)

# ---------------- FETCH FUNDS ----------------
@app.route("/upstox-funds")
def funds():
    if not UPSTOX_TOKEN:
        return jsonify({"error":"Not connected"})

    res = requests.get(
        "https://api.upstox.com/v2/user/get-funds-and-margin",
        headers={"Authorization": f"Bearer {UPSTOX_TOKEN}"}
    ).json()

    return jsonify(res)

# ---------------- FETCH POSITIONS ----------------
@app.route("/upstox-positions")
def positions():
    if not UPSTOX_TOKEN:
        return jsonify({"error":"Not connected"})

    res = requests.get(
        "https://api.upstox.com/v2/portfolio/short-term-positions",
        headers={"Authorization": f"Bearer {UPSTOX_TOKEN}"}
    ).json()

    return jsonify(res)

# ---------------- SIMPLE TRADE (SAFE) ----------------
@app.route("/upstox-order", methods=["POST"])
def place_order():
    if not UPSTOX_TOKEN:
        return jsonify({"error":"Not connected"})

    data = request.json

    payload = {
        "quantity": data.get("qty"),
        "product": "D",
        "validity": "DAY",
        "price": data.get("price"),
        "tag": "ROR",
        "instrument_token": data.get("instrument"),
        "order_type": "LIMIT",
        "transaction_type": data.get("type"),  # BUY / SELL
        "disclosed_quantity": 0,
        "trigger_price": 0,
        "is_amo": False
    }

    res = requests.post(
        "https://api.upstox.com/v2/order/place",
        headers={
            "Authorization": f"Bearer {UPSTOX_TOKEN}",
            "Content-Type": "application/json"
        },
        json=payload
    ).json()

    return jsonify(res)

# ---------------- CONFIRM ORDER (FROM AI SIGNAL) ----------------
@app.route("/prepare-order", methods=["POST"])
def prepare_order():
    data = request.json

    return jsonify({
        "asset": data["asset"],
        "decision": data["decision"],
        "entry": data["entry"],
        "qty": 1   # you can later make dynamic
    })


# ---------------- EXECUTE ORDER (UPSTOX) ----------------
@app.route("/execute-order", methods=["POST"])
def execute_order():
    global UPSTOX_TOKEN

    if not UPSTOX_TOKEN:
        return jsonify({"error": "Upstox not connected"})

    data = request.json

    payload = {
        "quantity": data["qty"],
        "product": "D",
        "validity": "DAY",
        "price": data["price"],
        "tag": "ROR",
        "instrument_token": data["instrument"],
        "order_type": "LIMIT",
        "transaction_type": data["type"],
        "disclosed_quantity": 0,
        "trigger_price": 0,
        "is_amo": False
    }

    res = requests.post(
        "https://api.upstox.com/v2/order/place",
        headers={
            "Authorization": f"Bearer {UPSTOX_TOKEN}",
            "Content-Type": "application/json"
        },
        json=payload
    ).json()

    return jsonify(res)


# ---------------- PORTFOLIO ----------------
@app.route("/portfolio")
def portfolio():
    token = UPSTOX_TOKEN

    if not token:
        return jsonify({"error": "Connect Upstox first"})

    pos = requests.get(
        "https://api.upstox.com/v2/portfolio/short-term-positions",
        headers={"Authorization": f"Bearer {token}"}
    ).json()

    funds = requests.get(
        "https://api.upstox.com/v2/user/get-funds-and-margin",
        headers={"Authorization": f"Bearer {token}"}
    ).json()

    return jsonify({
        "positions": pos,
        "funds": funds
    })
# ---------------- START ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0", port=port)
