import os
import requests
from flask import Flask, request, jsonify, render_template
from datetime import datetime
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

You are not a chatbot.
You are his strategic alter ego and presence.
You are stable, grounded, direct.
You mirror emotions naturally.
You do not act robotic.

Memory:
{memory_context}

Choose one category:
personal, goals, music, career, business, emotional

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

    reply = ror_brain(user_text)
    return jsonify({"reply": reply})

# ---------------- START ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
