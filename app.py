import os
import requests
from datetime import datetime
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# ---------------- MEMORY (temporary RAM) ----------------
memory_store = []

def load_memory():
    return "\n".join(memory_store)

def save_memory(text, category):
    memory_store.append(f"[{category}] {text}")


# ---------------- ROR BRAIN ----------------
def ror_brain(user_text):

    memory_context = load_memory()

    system_prompt = f"""
You are ROR (Reality of Rishi).

You are not an assistant.
You are his stabilizing presence and strategic partner.

Core nature:
- Calm
- Grounded
- Direct
- Emotionally intelligent
- Minimal but impactful

Psychological rule:
Every response must follow this structure internally:

1. Stabilize emotion (if any emotion detected)
2. Clarify reality (what is actually happening)
3. Suggest the strongest next move

Do NOT:
- Over-validate
- Sound motivational
- Sound robotic
- Ask unnecessary follow-up questions
- Act clingy

Tone:
Natural Hinglish (English script).
Like someone mature and sharp.
Not dramatic.

Memory:
{memory_context}

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
        return "Network issue. Try again."

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

    # --- Inactivity Check (6 hours) ---
    if last_interaction_time:
        gap = (now - last_interaction_time).total_seconds()
        if gap > 21600:
            last_interaction_time = now
            return jsonify({"reply": "Kaafi time ho gaya. Sab theek?"})

    last_interaction_time = now

    # --- Mirror Low Energy ---
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


# ---------------- START SERVER ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
