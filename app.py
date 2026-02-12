import os
import requests
from flask import Flask, request
import telebot
from gtts import gTTS

TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

app = Flask(__name__)
bot = telebot.TeleBot(TOKEN)

# Memory storage
conversation_memory = []


def ror_personality(user_text):
    global conversation_memory

    # Add user message to memory
    conversation_memory.append({
        "role": "user",
        "content": user_text
    })

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [
            {
                "role": "system",
                "content": "You are ROR (Reality of Rishi). You are strategic, sharp, emotionally intelligent, slightly bold, and guide Rishi to make powerful decisions."
            }
        ] + conversation_memory
    }

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=data
    )

    result = response.json()
    reply_text = result["choices"][0]["message"]["content"]

    # Add assistant reply to memory
    conversation_memory.append({
        "role": "assistant",
        "content": reply_text
    })

    return reply_text


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


@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_string = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "OK", 200


@app.route("/")
def index():
    return "ROR Brain Online"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
