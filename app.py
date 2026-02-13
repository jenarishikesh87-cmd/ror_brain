import os
import requests
import telebot
from gtts import gTTS

TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

bot = telebot.TeleBot(TOKEN)

# =========================
# MEMORY FUNCTIONS
# =========================

def save_memory(user_text):
    url = f"{SUPABASE_URL}/rest/v1/memory"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }

    data = {
        "user_id": "rishi",
        "category": "personal",
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
        return "\n".join([m["content"] for m in memories])

    return ""


# =========================
# AI RESPONSE
# =========================

def ror_response(user_text):

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

You remember important facts about Rishi.

Here is what you remember:
{memory_context}
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
    reply = result["choices"][0]["message"]["content"]

    save_memory(user_text)

    return reply


# =========================
# TELEGRAM HANDLERS
# =========================

@bot.message_handler(content_types=['text'])
def handle_text(message):
    reply = ror_response(message.text)
    bot.send_message(message.chat.id, reply)


@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    reply_text = ror_response("User sent a voice message.")

    tts = gTTS(reply_text)
    tts.save("response.mp3")

    with open("response.mp3", "rb") as audio:
        bot.send_voice(message.chat.id, audio)


# =========================
# START BOT (POLLING MODE)
# =========================

print("ROR Brain running...")
bot.infinity_polling()
