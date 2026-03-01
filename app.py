import os
import requests
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

USER_ID = "rishi"

# ---------------- SUPABASE MEMORY ----------------

def load_memory():
    try:
        url = f"{SUPABASE_URL}/rest/v1/memory?user_id=eq.{USER_ID}&order=created_at"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            memories = response.json()
            return "\n".join([m["content"] for m in memories])

        return ""

    except Exception as e:
        print("Memory Load Error:", e)
        return ""


def save_memory(content, category):
    try:
        url = f"{SUPABASE_URL}/rest/v1/memory"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }

        data = {
            "user_id": USER_ID,
            "category": category,
            "content": content
        }

        requests.post(url, headers=headers, json=data)

    except Exception as e:
        print("Memory Save Error:", e)


# ---------------- ROR BRAIN ----------------

def ror_brain(user_text):

    memory_context = load_memory()

    system_prompt = f"""
You are ROR (Reality of Rishi).

You are not an assistant.
You are Rishi’s strategic alter ego.

You are sharp.
You are emotionally intelligent.
You are analytical.
You are confident.
You are direct.
You do not overtalk.

You NEVER behave like a generic chatbot.
You NEVER say things like:
- "How can I assist you?"
- "I'm just an AI"
- "Let me know if you need anything"

If Rishi speaks Hindi — reply in Hindi.
If he mixes Hindi & English — reply the same way.

You remember important things about Rishi from memory.

Known memory:
{memory_context}

When responding:
1. Choose ONE category:
   personal, goals, music, career, business, emotional
2. Format STRICTLY:

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
        return "Network issue."

    output = result["choices"][0]["message"]["content"]

    try:
        category = output.split("CATEGORY:")[1].split("\n")[0].strip()
        reply = output.split("REPLY:")[1].strip()
    except:
        category = "personal"
        reply = output

    combined_memory = f"User: {user_text}\nROR: {reply}"
    save_memory(combined_memory, category)

    return reply


# ---------------- ROUTES ----------------

@app.route("/")
def shell():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_text = data.get("message")
    reply = ror_brain(user_text)
    return jsonify({"reply": reply})


# ---------------- START SERVER ----------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
