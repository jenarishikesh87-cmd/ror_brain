import os
import json
import requests
from datetime import datetime
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# ---------------- SUPABASE HELPERS ----------------

def supabase_get(key):
    url = f"{SUPABASE_URL}/rest/v1/ror_state?key=eq.{key}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    r = requests.get(url, headers=headers)
    data = r.json()
    if data:
        return data[0]["value"]
    return None

def supabase_set(key, value):
    url = f"{SUPABASE_URL}/rest/v1/ror_state"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }
    payload = {"key": key, "value": value}
    requests.post(url, headers=headers, json=payload)

# ---------------- LOAD STATE ----------------

def load_state():
    global active_goals, emotional_history, focus_score, drift_score

    goals = supabase_get("active_goals")
    history = supabase_get("emotional_history")
    focus = supabase_get("focus_score")
    drift = supabase_get("drift_score")

    active_goals = json.loads(goals) if goals else []
    emotional_history = json.loads(history) if history else []
    focus_score = int(focus) if focus else 0
    drift_score = int(drift) if drift else 0

load_state()

# ---------------- CORE IDENTITY ----------------

IDENTITY_ANCHOR = """
Rishi:
- Strategic thinker
- Long-term builder
- Wants correction over comfort
- Stabilize first, then guide
"""

# ---------------- GOALS ----------------

def detect_goal(text):
    text = text.lower()
    if "i want to" in text or "my goal is" in text or "i will build" in text:
        return True
    return False

def store_goal(text):
    active_goals.append(text)
    supabase_set("active_goals", json.dumps(active_goals))

def clear_goals():
    active_goals.clear()
    supabase_set("active_goals", json.dumps(active_goals))

# ---------------- EMOTIONAL STATE ----------------

def detect_state(text):
    text = text.lower()

    if any(w in text for w in ["tired", "low", "sad", "empty"]):
        return "low"
    if any(w in text for w in ["confused", "stuck", "dont know"]):
        return "confused"
    if any(w in text for w in ["angry", "frustrated"]):
        return "frustrated"
    if any(w in text for w in ["plan", "goal", "build", "strategy"]):
        return "focused"

    return "neutral"

def update_emotional_history(state):
    emotional_history.append(state)
    if len(emotional_history) > 10:
        emotional_history.pop(0)
    supabase_set("emotional_history", json.dumps(emotional_history))

# ---------------- STRATEGIC DRIFT ----------------

def update_focus_and_drift(text):
    global focus_score, drift_score

    if any(w in text.lower() for w in ["goal", "plan", "build", "future"]):
        focus_score += 1
        drift_score = max(0, drift_score - 1)
    else:
        drift_score += 1
        focus_score = max(0, focus_score - 1)

    supabase_set("focus_score", str(focus_score))
    supabase_set("drift_score", str(drift_score))

# ---------------- COMMAND SYSTEM ----------------

def handle_command(user_text):

    if user_text == "/goals":
        if not active_goals:
            return "No active goals."
        return "\n".join(active_goals)

    if user_text == "/clear_goals":
        clear_goals()
        return "Goals cleared."

    if user_text == "/state":
        return f"Focus: {focus_score}\nDrift: {drift_score}\nEmotions: {emotional_history}"

    if user_text == "/reset_focus":
        global focus_score, drift_score
        focus_score = 0
        drift_score = 0
        supabase_set("focus_score", "0")
        supabase_set("drift_score", "0")
        return "Focus and drift reset."

    return None

# ---------------- ROR BRAIN ----------------

def ror_brain(user_text):

    command_response = handle_command(user_text)
    if command_response:
        return command_response

    if detect_goal(user_text):
        store_goal(user_text)

    state = detect_state(user_text)
    update_emotional_history(state)
    update_focus_and_drift(user_text)

    system_prompt = f"""
You are ROR.

Identity:
{IDENTITY_ANCHOR}

Active Goals:
{active_goals}

Detected state: {state}
Focus score: {focus_score}
Drift score: {drift_score}

Behavior:
- Stabilize emotion.
- Clarify reality.
- Align with goals.
- Suggest strongest move.
- Speak naturally.
"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "openai/gpt-4o-mini",
        "temperature": 0.75,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ]
    }

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=data
    )

    result = response.json()

    if "choices" not in result:
        return "Network issue."

    return result["choices"][0]["message"]["content"]

# ---------------- ROUTES ----------------

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_text = data.get("message", "").strip()
    reply = ror_brain(user_text)
    return jsonify({"reply": reply})

# ---------------- START ----------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
