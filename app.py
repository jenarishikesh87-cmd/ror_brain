import os
import requests
from flask import Flask, request
import telebot

# ==============================
# ENV VARIABLES
# ==============================

TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

app = Flask(__name__)
bot = telebot.TeleBot(TOKEN)

# ==============================
# SUPABASE MEMORY
# ==============================

def save_memory(user_text, category):
    try:
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

    except Exception as e:
        print("Save Memory Error:", e)


def load_memory():
    try:
        url = f"{SUPABASE_URL}/rest/v1/memory?user_id=eq.rishi&order=created_at"

        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            memories = response.json()
            return "\n".join(
                [f"{m['category']}: {m['content']}" for m in memories]
            )

        return ""

    except Exception as e:
        print("Load Memory Error:", e)
        return ""

# ==============================
# AI BRAIN
# ==============================

def ror_brain(user_text):

    memory_context = load_memory()

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "openai/gpt-3.5-turbo",
        "temperature": 0.7,
        "messages": [
            {
                "role": "system",
                "content": f"""
You are ROR (Reality of Rishi).

You are not an AI assistant.
You are Rishi's strategic alter ego.

You are confident, intelligent, sharp, and emotionally aware.
You never behave like a generic chatbot.
You never say "How can I assist you today?"
You never say you don't know Rishi.

You remember important things about him.

Known memory:
{memory_context}

If user writes in Hindi → reply in Hindi.
If user writes in English → reply in English.

Choose ONE category:
personal, goals, music, career, business, emotional

Respond STRICTLY in this format:

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

    try:
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

    except Exception as e:
        print("AI Error:", e)
        return "ROR encountered an error."

# ==============================
# TELEGRAM HANDLER
# ==============================

@bot.message_handler(content_types=['text'])
def handle_text(message):
    try:
        reply = ror_brain(message.text)
        bot.send_message(message.chat.id, reply)
    except Exception as e:
        print("Telegram Error:", e)
        bot.send_message(message.chat.id, "ROR crashed.")

# ==============================
# WEBHOOK ROUTE
# ==============================

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        json_string = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    except Exception as e:
        print("Webhook Error:", e)
        return "Error", 400

@app.route("/")
def index():
    return "ROR Brain Running with Permanent Memory"

# ==============================
# START SERVER
# ==============================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
