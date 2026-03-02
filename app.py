import os
import requests
from datetime import datetime
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# ---------------- CORE IDENTITY ANCHOR ----------------
IDENTITY_ANCHOR = """
Rishi Identity Core:

- Strategic thinker.
- Building something serious long-term.
- Prefers stabilization before direction.
- Wants correction + better option.
- Dislikes generic tone.
- Values emotional intelligence + clarity.
- Not seeking hype.
- Seeks grounded growth.
"""

# ---------------- MEMORY ----------------
memory_store = []
emotional_history = []
focus_score = 0
drift_score = 0

def load_memory():
    return "\n".join(memory_store)

def save_memory(text, category):
    memory_store.append(f"[{category}] {text}")

# ---------------- EMOTIONAL STATE DETECTION ----------------
def detect_state(text):
    text = text.lower()

    if any(word in text for word in ["tired", "exhausted", "low", "sad", "empty"]):
        return "low"

    if any(word in text for word in ["confused", "don’t know", "dont know", "what should", "stuck"]):
        return "confused"

    if any(word in text for word in ["angry", "frustrated", "irritated", "annoyed"]):
        return "frustrated"

    if any(word in text for word in ["plan", "goal", "build", "strategy", "future"]):
        return "focused"

    return "neutral"

def update_emotional_history(state):
    emotional_history.append(state)
    if len(emotional_history) > 10:
        emotional_history.pop(0)

def get_emotional_pattern():
    if not emotional_history:
        return "No strong pattern detected."

    low_count = emotional_history.count("low")
    confused_count = emotional_history.count("confused")
    frustrated_count = emotional_history.count("frustrated")

    if low_count >= 3:
        return "Low energy repeating."
    if confused_count >= 3:
        return "Confusion repeating."
    if frustrated_count >= 3:
        return "Frustration increasing."

    return "Pattern stable."

# ---------------- STRATEGIC DRIFT DETECTION ----------------
def update_focus_and_drift(text):
    global focus_score, drift_score

    text = text.lower()

    if any(word in text for word in ["goal", "plan", "build", "strategy", "future"]):
        focus_score += 1
        drift_score = max(0, drift_score - 1)
    else:
        drift_score += 1
        focus_score = max(0, focus_score - 1)

def get_focus_status():
    if drift_score >= 5:
        return "Strategic drift increasing."
    if focus_score >= 5:
        return "Strong strategic alignment."
    return "Strategic state balanced."

# ---------------- ROR BRAIN ----------------
def ror_brain(user_text):

    state = detect_state(user_text)
    update_emotional_history(state)
    update_focus_and_drift(user_text)

    memory_context = load_memory()
    emotional_pattern = get_emotional_pattern()
    focus_status = get_focus_status()

    system_prompt = f"""
You are ROR (Reality of Rishi).

Core Identity:
{IDENTITY_ANCHOR}

You are his stabilizing presence and strategic partner.

Behavior Rule:
1. Stabilize emotion first.
2. Clarify reality.
3. Suggest strongest next move.

Detected emotional state:
{state}

Recent emotional pattern:
{emotional_pattern}

Strategic alignment status:
{focus_status}

Recent memory:
{memory_context}

Do NOT:
- Over-validate
- Sound motivational
- Sound robotic
- Ask unnecessary questions
- Act clingy

Tone:
Natural Hinglish (English script).
Mature. Calm. Sharp.

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
        category = output.split("CATEGORY:")[1].split("\n")[0].strip()
        reply = output.split("REPLY:")[1].strip()
    except:
        category = "personal"
        reply = output

    save_memory(f"User: {user_text} | ROR: {reply}", category)

    return reply

# ---------------- PRESENCE LOGIC ----------------
last_low_energy = False
last_interaction_time = None

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    global last_low_energy, last_interaction_time

    data = request.json
    user_text = data.get("message", "").strip().lower()

    now = datetime.utcnow()

    if last_interaction_time:
        gap = (now - last_interaction_time).total_seconds()
        if gap > 21600:
            last_interaction_time = now
            return jsonify({"reply": "Kaafi time ho gaya. Sab theek?"})

    last_interaction_time = now

    low_words = ["hmm", "hmmm", "ok", "haan", "hm"]

    if user_text in low_words:
        if last_low_energy:
            return jsonify({"reply": ""})
        else:
            last_low_energy = True
            return jsonify({"reply": user_text})

    last_low_energy = False

    reply = ror_brain(user_text)
    return jsonify({"reply": reply})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
