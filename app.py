import os, requests, math
from flask import Flask, request, jsonify, render_template, redirect
from datetime import datetime
from supabase import create_client

app = Flask(__name__)

# ---------------- ENV ----------------
UPSTOX_API_KEY = os.getenv("UPSTOX_API_KEY")
UPSTOX_SECRET = os.getenv("UPSTOX_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

UPSTOX_TOKEN = None

# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("index.html")

# ---------------- CHAT ----------------
@app.route("/chat", methods=["POST"])
def chat():
    msg = request.json.get("message","")
    return jsonify({"reply": "ROR: " + msg})

# ---------------- TRADING ENGINE ----------------
@app.route("/ror-trade")
def trade():
    symbol = request.args.get("symbol","BTCUSDT")

    url=f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=5m&limit=50"
    data=requests.get(url).json()
    prices=[float(x[4]) for x in data]

    price=prices[-1]

    change=((prices[-1]-prices[0])/prices[0])*100
    momentum=((prices[-1]-prices[-10])/prices[-10])*100

    decision="HOLD"
    if change>1 and momentum>0.5:
        decision="BUY"
    elif change<-1 and momentum<-0.5:
        decision="SELL"

    entry=round(price,2)
    tp=round(price*1.01,2)
    sl=round(price*0.99,2)

    return jsonify({
        "price":price,
        "analysis":{
            "decision":decision,
            "confidence":70,
            "entry":entry,
            "tp":tp,
            "sl":sl,
            "reason":"Momentum breakout"
        }
    })

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

    return "✅ Upstox Connected"

# ---------------- GET BALANCE ----------------
def get_balance():
    global UPSTOX_TOKEN

    if not UPSTOX_TOKEN:
        return 10000  # fallback demo

    res = requests.get(
        "https://api.upstox.com/v2/user/get-funds-and-margin",
        headers={"Authorization": f"Bearer {UPSTOX_TOKEN}"}
    ).json()

    try:
        return float(res["data"]["equity"]["available_margin"])
    except:
        return 10000

# ---------------- POSITION SIZE ----------------
def calculate_qty(balance, risk_percent, entry, sl):
    risk_amount = balance * (risk_percent / 100)
    per_unit_risk = abs(entry - sl)

    if per_unit_risk == 0:
        return 1

    qty = math.floor(risk_amount / per_unit_risk)
    return max(1, qty)

# ---------------- EXECUTE ORDER ----------------
@app.route("/execute-order", methods=["POST"])
def execute_order():
    global UPSTOX_TOKEN

    if not UPSTOX_TOKEN:
        return jsonify({"error":"Connect Upstox first"})

    data = request.json

    balance = get_balance()
    qty = calculate_qty(balance, 1, data["price"], data["price"]*0.99)

    payload = {
        "quantity": qty,
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

    # SAVE TRADE
    supabase.table("trades").insert({
        "user_id":"rishi",
        "symbol": data["instrument"],
        "decision": data["type"],
        "entry": data["price"],
        "tp": data["price"]*1.01,
        "sl": data["price"]*0.99,
        "qty": qty,
        "result": "open",
        "pnl": 0
    }).execute()

    return jsonify(res)

# ---------------- PNL UPDATE ----------------
@app.route("/update-pnl")
def update_pnl():

    trades = supabase.table("trades").select("*").eq("result","open").execute().data

    for t in trades:
        current_price = t["entry"] * 1.01  # simulate

        pnl = (current_price - t["entry"]) * t["qty"]

        supabase.table("trades").update({
            "pnl": pnl,
            "result": "closed"
        }).eq("id", t["id"]).execute()

    return jsonify({"status":"updated"})

# ---------------- ANALYTICS ----------------
@app.route("/analytics")
def analytics():

    trades = supabase.table("trades").select("*").execute().data

    total = len(trades)
    wins = sum(1 for t in trades if t["pnl"] > 0)

    winrate = (wins/total*100) if total else 0

    avg_pnl = sum(t["pnl"] for t in trades)/total if total else 0

    return jsonify({
        "total_trades": total,
        "winrate": round(winrate,2),
        "avg_pnl": round(avg_pnl,2)
    })

# ---------------- AI LEARNING ----------------
@app.route("/ai-insights")
def ai_insights():

    trades = supabase.table("trades").select("*").execute().data

    if not trades:
        return jsonify({"insight":"No trades yet"})

    losses = [t for t in trades if t["pnl"] < 0]

    if len(losses) > len(trades)/2:
        return jsonify({"insight":"You are overtrading. Reduce frequency."})

    return jsonify({"insight":"Strategy stable. Continue."})

# ---------------- PORTFOLIO ----------------
@app.route("/portfolio")
def portfolio():
    trades = supabase.table("trades").select("*").execute().data
    return jsonify(trades)

# ---------------- START ----------------
if __name__ == "__main__":
    app.run(port=10000)
