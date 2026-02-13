import os
import requests
from flask import Flask, request
import telebot

# ===============================
# ENV VARIABLES
# ===============================

TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

app = Flask(__name__)
bot = telebot.TeleBot(TOKEN)

# ===============================
# SUPABASE MEMORY
# ===============================

def save_memory(user_text, category):
    url = f"{SUPABASE_URL}/rest/v1/memory"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }

    data = {
        "user_id": "rishi",
        "category": category,
        "content": user_text
    }

    requests.post(url, headers=headers, json=data)


def load_memory():
    url = f"{SUPABASE_URL}/rest/v1/memory?user_id=eq.rishi&order=created_at"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        memories = response.json()
        return "\n".join([f"{m['category']}: {m['content']}" for m in memories])

    return ""


# ===============================
# AI ENGINE
# ===============================

def ror_brain(user_text):

    memory_context = load_memory()

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [
            {
                "role": "system",
                "content": f"""
You are ROR (Reality of Rishi).
You are strategic, intelligent, slightly confident.

Here is what you know about Rishi:
{memory_context}

When responding:
1. Choose a category for this message from:
personal, goals, music, career, business, emotional
2. Respond normally.

Format:
CATEGORY: <category>
REPLY: <actual reply>
"""
            },
            {
                "role": "user",
                "content": user_text
            }
        ]
    }

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=data
    )

    result = response.json()
    output = result["choices"][0]["message"]["content"]

    try:
        category = output.split("CATEGORY:")[1].split("\n")[0].strip()
        reply = output.split("REPLY:")[1].strip()
    except:
        category = "personal"
        reply = output

    save_memory(user_text, category)

    return reply


# ===============================
# TELEGRAM HANDLER
# ===============================

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    reply = ror_brain(message.text)
    bot.reply_to(message, reply)


# ===============================
# WEBHOOK ROUTE
# ===============================

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_string = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "OK", 200


@app.route("/")
def index():
    return "ROR Brain Running with Permanent Memory"


# ===============================
# START SERVER
# ===============================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
