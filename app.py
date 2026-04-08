import os, requests, json
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# ---------- CHAT ----------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    msg = data.get("message","")
    return jsonify({"reply": "ROR: " + msg})

# ---------- TRADING ----------
@app.route("/ror-trade")
def trade():
    symbol = request.args.get("symbol","BTCUSDT")

    try:
        if "USDT" in symbol:
            url=f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=5m&limit=50"
            data=requests.get(url).json()
            prices=[float(x[4]) for x in data]

        else:
            url="https://query1.finance.yahoo.com/v8/finance/chart/"+symbol
            res=requests.get(url).json()
            prices=res["chart"]["result"][0]["indicators"]["quote"][0]["close"]

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
            "price":round(price,2),
            "analysis":{
                "decision":decision,
                "confidence":70,
                "entry":entry,
                "tp":tp,
                "sl":sl,
                "reason":"Momentum based trade"
            }
        })

    except Exception as e:
        return jsonify({"error":str(e)})

if __name__=="__main__":
    app.run()
