import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


# ---------------- MEMORY (temporary in RAM for now) ----------------
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

You are Rishi's strategic alter ego.
You are sharp, confident, minimal, direct.

Never act like a generic assistant.
Never ask unnecessary follow-up questions.

Known memory:
{memory_context}

Choose one category:
personal, goals, music, career, business, emotional

Format:
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

    save_memory(f"User: {user_text} | ROR: {reply}", category)

    return reply


# ---------------- API ROUTE ----------------
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_text = data.get("message")

    reply = ror_brain(user_text)

    return jsonify({"reply": reply})


@app.route("/")
def home():
    return "ROR is running."


# ---------------- START SERVER ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
