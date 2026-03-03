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

# ---------------- REMINDER HANDLER ----------------
def handle_reminder(user_text):

    text = user_text.lower()

    # IN X MINUTES
    match = re.search(r"remind me to (.+) in (\d+) minutes?", text)
    if match:
        task = match.group(1)
        minutes = int(match.group(2))
        remind_time = datetime.now() + timedelta(minutes=minutes)

        supabase.table("reminders").insert({
            "user_id": "rishi",
            "text": task,
            "remind_at": remind_time.isoformat(),
            "recurring": None,
            "triggered": False
        }).execute()

        return f"Okay. I’ll remind you in {minutes} minutes."

    # SPECIFIC DATE
    match = re.search(r"remind me on (\d{1,2})[./](\d{1,2})[./](\d{2,4}) at (\d{1,2}):?(\d{2})?\s?(am|pm)", text)
    if match:
        day = int(match.group(1))
        month = int(match.group(2))
        year = int(match.group(3))
        hour = int(match.group(4))
        minute = int(match.group(5) or 0)
        ampm = match.group(6)

        if year < 100:
            year += 2000

        if ampm == "pm" and hour != 12:
            hour += 12
        if ampm == "am" and hour == 12:
            hour = 0

        remind_time = datetime(year, month, day, hour, minute)

        supabase.table("reminders").insert({
            "user_id": "rishi",
            "text": "Reminder",
            "remind_at": remind_time.isoformat(),
            "recurring": None,
            "triggered": False
        }).execute()

        return "Reminder scheduled."

    # DAILY
    match = re.search(r"remind me everyday at (\d{1,2}):?(\d{2})?\s?(am|pm)", text)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        ampm = match.group(3)

        if ampm == "pm" and hour != 12:
            hour += 12
        if ampm == "am" and hour == 12:
            hour = 0

        now = datetime.now()
        remind_time = now.replace(hour=hour, minute=minute, second=0)

        if remind_time < now:
            remind_time += timedelta(days=1)

        supabase.table("reminders").insert({
            "user_id": "rishi",
            "text": "Daily reminder",
            "remind_at": remind_time.isoformat(),
            "recurring": "daily",
            "triggered": False
        }).execute()

        return "Daily reminder set."

    return None

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

    reminder_reply = handle_reminder(user_text)
    if reminder_reply:
        return jsonify({"reply": reminder_reply})

    reply = ror_brain(user_text)
    return jsonify({"reply": reply})

@app.route("/check-reminder")
def check_reminder():

    now = datetime.now().isoformat()

    response = supabase.table("reminders") \
        .select("*") \
        .eq("user_id", "rishi") \
        .lte("remind_at", now) \
        .eq("triggered", False) \
        .execute()

    if response.data:
        reminder = response.data[0]

        if reminder["recurring"] == "daily":
            next_time = datetime.fromisoformat(reminder["remind_at"]) + timedelta(days=1)
            supabase.table("reminders").update({
                "remind_at": next_time.isoformat()
            }).eq("id", reminder["id"]).execute()
        else:
            supabase.table("reminders").update({
                "triggered": True
            }).eq("id", reminder["id"]).execute()

        return jsonify({"reminder": reminder["text"]})

    return jsonify({"reminder": None})

# ---------------- START ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
