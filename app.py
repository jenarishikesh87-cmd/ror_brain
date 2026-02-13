import os
import requests
import sqlite3
from flask import Flask, request
import telebot
from gtts import gTTS

TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

app = Flask(__name__)
bot = telebot.TeleBot(TOKEN)

# ---------------- DATABASE SETUP ----------------

conn = sqlite3.connect("ror_memory.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT,
    content TEXT
)
""")
conn.commit()

# ---------------- MEMORY FUNCTIONS ----------------

def save_memory(category, content):
    cursor.execute(
        "INSERT INTO memory (category, content) VALUES (?, ?)",
        (category, content)
    )
    conn.commit()

def get_relevant_memory(limit=10):
    cursor.execute(
        "SELECT category, content FROM memory ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    rows = cursor.fetchall()
    rows.reverse()
    return "\n".join([f"{r[0]}: {r[1]}" for r in rows])

# ---------------- AI MEMORY CLASSIFIER ----------------

def classify_memory(user_text):

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [
            {
                "role": "system",
                "content": """
You are a memory classifier for ROR.
Decide if the user's message contains important personal information.
If yes, categorize it strictly as one of:
Identity, Ambition, Emotion, Preference, Project.
If not important, respond: Ignore.
Only return the category name or Ignore.
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
    category = result["choices"][0]["message"]["content"].strip()

    return category

# ---------------- ROR PERSONALITY ENGINE ----------------

def ror_personality(user_text):

    # Step 1: Classify memory
    category = classify_memory(user_text)

    if category != "Ignore":
        save_memory(category, user_text)

    # Step 2: Retrieve past memory
    memory_context = get_relevant_memory()

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
You are strategic, intelligent, emotionally balanced, and slightly confident.

Here is what you know about Rishi:
{memory_context}

Use this memory naturally in your response.
Guide him wisely.
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
    reply_text = result["choices"][0]["message"]["content"]

    return reply_text

# ---------------- HANDLERS ----------------

@bot.message_handler(content_types=['text'])
def handle_text(message):
    reply = ror_personality(message.text)
    bot.send_message(message.chat.id, reply)

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    reply_text = ror_personality("User sent a voice message. Respond intelligently.")

    tts = gTTS(reply_text)
    tts.save("response.mp3")

    with open("response.mp3", "rb") as audio:
        bot.send_voice(message.chat.id, audio)

# ---------------- WEBHOOK ----------------

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_string = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "OK", 200

@app.route("/")
def index():
    return "ROR Brain Online - Intelligent Memory Active"

# ---------------- RUN ----------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
