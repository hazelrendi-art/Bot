import os
import logging
import requests
from datetime import datetime
from flask import Flask, request
import telebot

# ===== Konfigurasi Bot =====
BOT_TOKEN = os.getenv("BOT_TOKEN", )
bot = telebot.TeleBot(BOT_TOKEN)

# ===== Flask App =====
app = Flask(__name__)

# ===== Logging =====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ===== Feature Flags =====
waiting_users = []  # antrean user untuk anonymous chat
active_chats = {}   # pasangan chat {user_id: partner_id}
ai_mode_enabled = False  # default: AI off

# ===== Groq AI Config =====
GROQ_API_KEY = os.getenv("GROQ_API_KEY", )
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# === Command AI ===
@bot.message_handler(commands=['ai'])
def ai_chat(message):
    try:
        command_parts = message.text.split(' ', 1)
        if len(command_parts) <= 1:
            bot.reply_to(message, "❌ Contoh: `/ai apa itu python?`", parse_mode="Markdown")
            return

        user_query = command_parts[1].strip()
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": user_query}
            ]
        }

        response = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            answer = data["choices"][0]["message"]["content"]
            bot.reply_to(message, f"🤖 *AI:*\n{answer}", parse_mode="Markdown")
        else:
            bot.reply_to(message, "❌ Gagal hubungi AI.")
    except Exception as e:
        logger.error(f"AI Error: {e}")
        bot.reply_to(message, "❌ Error AI.")

# === Perintah dasar ===
@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.reply_to(message, f"""
🤖 *Bot Telegram Online via Render!*

Halo {message.from_user.first_name} 👋

Perintah:
/help - Daftar perintah
/ai <tanya> - Tanya ke AI
/anonymous - Chat anonim
/stop - Stop chat anonim
""", parse_mode="Markdown")

@bot.message_handler(commands=['help'])
def help_cmd(message):
    bot.reply_to(message, """
📚 *Perintah:*
/start - Welcome
/help - Bantuan
/ai <query> - Tanya AI
/anonymous - Chat anonim
/stop - Keluar chat anonim
""", parse_mode="Markdown")

# === Anonymous Chat ===
@bot.message_handler(commands=['anonymous'])
def anonymous_start(message):
    user_id = message.from_user.id
    if user_id in active_chats:
        bot.reply_to(message, "❌ Kamu sudah dalam obrolan.")
        return
    if user_id in waiting_users:
        bot.reply_to(message, "⏳ Kamu sudah menunggu.")
        return
    if waiting_users:
        partner_id = waiting_users.pop(0)
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id
        bot.send_message(user_id, "✅ Terhubung! /stop untuk keluar.")
        bot.send_message(partner_id, "✅ Terhubung! /stop untuk keluar.")
    else:
        waiting_users.append(user_id)
        bot.reply_to(message, "⏳ Menunggu pasangan...")

@bot.message_handler(commands=['stop'])
def stop_chat(message):
    user_id = message.from_user.id
    if user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        active_chats.pop(partner_id, None)
        bot.send_message(partner_id, "⚠️ Pasangan keluar.")
        bot.send_message(user_id, "❌ Kamu keluar dari obrolan.")
    elif user_id in waiting_users:
        waiting_users.remove(user_id)
        bot.reply_to(message, "❌ Batal menunggu.")
    else:
        bot.reply_to(message, "ℹ️ Kamu tidak dalam chat.")

@bot.message_handler(func=lambda m: m.from_user.id in active_chats, content_types=['text'])
def relay_message(message):
    partner_id = active_chats.get(message.from_user.id)
    if partner_id:
        bot.send_message(partner_id, f"💬 {message.text}")

# === Flask Routes untuk Render ===
@app.route("/")
def home():
    return "Bot is running!"

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    try:
        update = telebot.types.Update.de_json(request.data.decode("utf-8"))
        bot.process_new_updates([update])
    except Exception as e:
        logger.error(f"Webhook error: {e}")
    return "OK", 200

if __name__ == "__main__":
    # Set webhook saat startup
    render_url = os.getenv("RENDER_URL")
    if render_url:
        bot.remove_webhook()
        bot.set_webhook(url=f"{render_url}/{BOT_TOKEN}")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
