import os
import requests
import re
import threading
import time
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from supabase import create_client

app = Flask(__name__)

# ---------------- ENV ----------------
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------- MEMORY ----------------
def load_memory():
    response = supabase.table("memory") \
        .select("content") \
        .eq("user_id", "rishi") \
        .order("id") \
        .execute()

    if response.data:
        return "\n".join([row["content"] for row in response.data])
    return ""

def save_memory(text, category):
    supabase.table("memory").insert({
        "user_id": "rishi",
        "category": category,
        "content": text
    }).execute()

# ---------------- REMINDER SYSTEM ----------------
reminders = []

def reminder_checker():
    while True:
        now = datetime.now().strftime("%H:%M")
        for r in reminders:
            if not r["triggered"] and r["time"] == now:
                r["triggered"] = True
        time.sleep(20)

threading.Thread(target=reminder_checker, daemon=True).start()

# ---------------- ROR BRAIN ----------------
def ror_brain(user_text):

    memory_context = load_memory()

    system_prompt = f"""
You are ROR (Reality of Rishi).
You are his grounded alter ego.
Be natural. No robotic tone.

Memory:
{memory_context}

Format strictly:
CATEGORY: <category>
REPLY: <actual reply>
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

    combined = f"User: {user_text}\nROR: {reply}"
    save_memory(combined, category)

    return reply

# ---------------- ROUTES ----------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_text = data.get("message", "").strip()

    if not user_text:
        return jsonify({"reply": "Say something."})

    # --------- REMINDER DETECTION ---------
    reminder_pattern = r"remind me at (\d{1,2})(?::(\d{2}))?\s?(am|pm) to (.+)"
    match = re.search(reminder_pattern, user_text.lower())

    if match:
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        ampm = match.group(3)
        task = match.group(4)

        if ampm == "pm" and hour != 12:
            hour += 12
        if ampm == "am" and hour == 12:
            hour = 0

        reminder_time = f"{hour:02d}:{minute:02d}"

        reminders.append({
            "time": reminder_time,
            "text": task,
            "triggered": False
        })

        return jsonify({
            "reply": f"Reminder set at {match.group(1)}:{minute:02d} {ampm.upper()} to {task}"
        })

    # -------- NORMAL BRAIN --------
    reply = ror_brain(user_text)
    return jsonify({"reply": reply})


@app.route("/check-reminder")
def check_reminder():
    for r in reminders:
        if r["triggered"]:
            r["triggered"] = False
            return jsonify({"reminder": r["text"]})
    return jsonify({"reminder": None})

# ---------------- START ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
