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
    payload = {
        "key": key,
        "value": value
    }
    requests.post(url, headers=headers, json=payload)

# ---------------- LOAD PERSISTENT STATE ----------------

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
Rishi Identity Core:
- Strategic thinker.
- Building something serious long-term.
- Prefers stabilization before direction.
- Wants correction + better option.
- Dislikes generic tone.
- Values emotional intelligence + clarity.
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

def get_goal_context():
    if not active_goals:
        return "No active goals stored."
    return "Active goals:\n" + "\n".join(active_goals)

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

def get_emotional_pattern():
    if emotional_history.count("low") >= 3:
        return "Low energy repeating."
    if emotional_history.count("confused") >= 3:
        return "Confusion repeating."
    if emotional_history.count("frustrated") >= 3:
        return "Frustration increasing."
    return "Pattern stable."

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

def get_focus_status():
    if drift_score >= 5:
        return "Strategic drift increasing."
    if focus_score >= 5:
        return "Strong strategic alignment."
    return "Strategic state balanced."

# ---------------- ROR BRAIN ----------------

def ror_brain(user_text):

    if detect_goal(user_text):
        store_goal(user_text)

    state = detect_state(user_text)
    update_emotional_history(state)
    update_focus_and_drift(user_text)

    emotional_pattern = get_emotional_pattern()
    focus_status = get_focus_status()
    goal_context = get_goal_context()

    system_prompt = f"""
You are ROR (Reality of Rishi).

Core Identity:
{IDENTITY_ANCHOR}

Active Goals:
{goal_context}

Detected emotional state: {state}
Recent emotional pattern: {emotional_pattern}
Strategic alignment: {focus_status}

Behavior Rule:
1. Stabilize emotion.
2. Clarify reality.
3. Align response with active goals.
4. Suggest strongest next move.

Tone:
Natural Hinglish. Calm. Sharp.

Format strictly:
CATEGORY: <personal/goals/music/career/business/emotional>
REPLY: <response>
"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "openai/gpt-4o-mini",
        "temperature": 0.7,
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

    output = result["choices"][0]["message"]["content"]

    try:
        reply = output.split("REPLY:")[1].strip()
    except:
        reply = output

    return reply

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

# ---------------- START SERVER ----------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
