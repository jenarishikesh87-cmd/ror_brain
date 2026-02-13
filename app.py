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

# ==============================
# DATABASE SETUP
# ==============================

conn = sqlite3.connect("memory.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT
)
""")
conn.commit()


# ==============================
# MEMORY FUNCTIONS
# ==============================

def save_memory(text):
    cursor.execute("INSERT INTO memories (content) VALUES (?)", (text,))
    conn.commit()

def get_memories():
    cursor.execute("SELECT content FROM memories")
    rows = cursor.fetchall()
    return [row[0] for row in rows]


# ==============================
# IMPORTANCE DETECTION
# ==============================

def is_important(text):
    keywords = [
        "i am", "i'm", "i like", "i love", "i hate",
        "i want", "my goal", "i feel", "i think",
        "i prefer", "i get", "i struggle"
    ]
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in keywords)


# ==============================
# AI CORE FUNCTION
# ==============================

def ror_personality(user_text):

    # Save important memories automatically
    if is_important(user_text):
        save_memory(user_text)

    memory_list = get_memories()
    memory_text = "\n".join(memory_list)

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
You are strategic, intelligent, calm, slightly confident with attitude.
You guide Rishi toward growth and clarity.

Here is what you remember about Rishi:
{memory_text}

Use this knowledge naturally in conversation.
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
    return result["choices"][0]["message"]["content"]


# ==============================
# TELEGRAM HANDLERS
# ==============================

@bot.message_handler(content_types=['text'])
def handle_text(message):
    reply = ror_personality(message.text)
    bot.send_message(message.chat.id, reply)

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    reply_text = ror_personality("User sent a voice message. Respond wisely.")

    tts = gTTS(reply_text)
    tts.save("response.mp3")

    with open("response.mp3", "rb") as audio:
        bot.send_voice(message.chat.id, audio)


# ==============================
# WEBHOOK + FLASK
# ==============================

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_string = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def index():
    return "ROR Brain Online"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
