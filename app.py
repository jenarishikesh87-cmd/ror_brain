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

# ---------- DATABASE SETUP ----------

conn = sqlite3.connect("memory.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT,
    content TEXT
)
""")
conn.commit()

# ---------- MEMORY FUNCTIONS ----------

def save_memory(role, content):
    cursor.execute("INSERT INTO memory (role, content) VALUES (?, ?)", (role, content))
    conn.commit()

def load_memory():
    cursor.execute("SELECT role, content FROM memory ORDER BY id DESC LIMIT 20")
    rows = cursor.fetchall()
    rows.reverse()
    return [{"role": r[0], "content": r[1]} for r in rows]

# ---------- AI PERSONALITY ----------

def ror_personality(user_text):

    save_memory("user", user_text)

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    memory_messages = load_memory()

    data = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [
            {
                "role": "system",
                "content": "You are ROR (Reality of Rishi). You are strategic, intelligent, emotionally balanced, and slightly confident in tone. You guide Rishi but respect his final decision."
            }
        ] + memory_messages
    }

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=data
    )

    result = response.json()
    reply_text = result["choices"][0]["message"]["content"]

    save_memory("assistant", reply_text)

    return reply_text

# ---------- HANDLERS ----------

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

# ---------- WEBHOOK ----------

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_string = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def index():
    return "ROR Brain Online - Memory Active"

# ---------- RUN ----------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
