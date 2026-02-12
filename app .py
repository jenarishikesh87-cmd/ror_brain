import os
import requests
from flask import Flask, request
import telebot
from gtts import gTTS

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

def ror_personality(user_text):
    return f"Analyzing your input: {user_text}. Stay strategic. Stay aware."

@bot.message_handler(content_types=['text'])
def handle_text(message):
    response = ror_personality(message.text)
    bot.send_message(message.chat.id, response)

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    file_info = bot.get_file(message.voice.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    with open("voice.ogg", "wb") as f:
        f.write(downloaded_file)

    response_text = "Voice received. Processing your thoughts."
    tts = gTTS(response_text)
    tts.save("response.mp3")

    with open("response.mp3", "rb") as audio:
        bot.send_voice(message.chat.id, audio)

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
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
