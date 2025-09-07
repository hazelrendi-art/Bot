import os
import logging
import cloudscraper
import requests
import chord
from bs4 import BeautifulSoup
from datetime import datetime
from flask import Flask, request
import telebot

# ===== Config =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
RENDER_URL = os.getenv("RENDER_URL")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN environment variable not set!")
if not GROQ_API_KEY:
    raise ValueError("❌ GROQ_API_KEY environment variable not set!")
if not RENDER_URL:
    raise ValueError("❌ RENDER_URL environment variable not set!")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# ===== Logging =====
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ===== Anonymous chat =====
waiting_users = []
active_chats = {}

# ===== Groq AI =====
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# ===== Handlers =====

def safe_reply(message, text):
    """Helper reply dengan logging"""
    try:
        bot.reply_to(message, text, parse_mode="MarkdownV2", disable_web_page_preview=True)
        logger.info(f"✅ Reply terkirim: {text[:30]}...")
    except Exception as e:
        logger.error(f"❌ Gagal kirim pesan: {e}")

# --- /start ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    text = (
        "🤖 *Welcome!*\n\n"
        f"Halo {message.from_user.first_name} 👋\n\n"
        "Perintah:\n"
        "/help - Daftar perintah\n"
        "/ai <pertanyaan> - Tanya AI\n"
        "/anonymous - Chat anonim\n"
        "/stop - Stop chat anonim"
    )
    safe_reply(message, text)

# --- /help ---
@bot.message_handler(commands=['help'])
def help_cmd(message):
    text = (
        "📚 *Perintah:*\n"
        "/start - Welcome\n"
        "/help - Bantuan\n"
        "/info - Info bot\n"
        "/time - Waktu server\n"
        "/echo <text> - Echo message\n"
        "/facebook <link> - Download Facebook video\n"
        "/yt <link> - Download YouTube video\n"
        "/ai <pertanyaan> - Tanya AI\n"
        "/anonymous - Chat anonim\n"
        "/stop - Keluar chat anonim\n"
        "/chord <lagu> - Cari chord gitar"
    )
    safe_reply(message, text)

# --- /info ---
@bot.message_handler(commands=['info'])
def info_cmd(message):
    text = (
        "ℹ️ *Bot Info*\n"
        "🤖 Bot: PyTelegramBot\n"
        "⚡ Status: Online\n"
        f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"👤 Your ID: {message.from_user.id}"
    )
    safe_reply(message, text)

# --- /time ---
@bot.message_handler(commands=['time'])
def time_cmd(message):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    safe_reply(message, f"🕐 Waktu server: `{now}`")

# --- /echo ---
@bot.message_handler(commands=['echo'])
def echo_cmd(message):
    parts = message.text.split(' ', 1)
    if len(parts) > 1:
        safe_reply(message, f"🔄 *Echo:* {parts[1]}")
    else:
        safe_reply(message, "Gunakan: `/echo <text>`")

# --- /ai ---
@bot.message_handler(commands=['ai'])
def ai_cmd(message):
    try:
        parts = message.text.split(' ', 1)
        if len(parts) <= 1:
            safe_reply(message, "❌ Gunakan: `/ai <pertanyaan>`")
            return

        user_query = parts[1].strip()
        bot.send_chat_action(message.chat.id, 'typing')

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": user_query}
            ]
        }
        resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            answer = data["choices"][0]["message"]["content"]
            safe_reply(message, f"🤖 *AI Response:*\n{answer}")
        else:
            safe_reply(message, f"❌ AI Error: {resp.status_code}")
    except Exception as e:
        logger.error(f"AI command error: {e}")
        safe_reply(message, "❌ Terjadi kesalahan AI.")

# --- /anonymous ---
@bot.message_handler(commands=['anonymous'])
def anon_start(message):
    user_id = message.from_user.id
    if user_id in active_chats:
        safe_reply(message, "❌ Sudah dalam obrolan.")
        return
    if user_id in waiting_users:
        safe_reply(message, "⏳ Menunggu pasangan...")
        return
    if waiting_users:
        partner_id = waiting_users.pop(0)
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id
        bot.send_message(user_id, "✅ Terhubung! /stop untuk keluar.")
        bot.send_message(partner_id, "✅ Terhubung! /stop untuk keluar.")
    else:
        waiting_users.append(user_id)
        safe_reply(message, "⏳ Menunggu pasangan anonim...")

# --- /stop ---
@bot.message_handler(commands=['stop'])
def anon_stop(message):
    user_id = message.from_user.id
    if user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        active_chats.pop(partner_id, None)
        bot.send_message(partner_id, "⚠️ Pasangan keluar.")
        bot.send_message(user_id, "❌ Kamu keluar dari obrolan.")
    elif user_id in waiting_users:
        waiting_users.remove(user_id)
        safe_reply(message, "❌ Batal menunggu.")
    else:
        safe_reply(message, "ℹ️ Tidak dalam chat.")

# --- Relay messages for anonymous chat ---
@bot.message_handler(func=lambda m: m.from_user.id in active_chats, content_types=['text'])
def relay_message(message):
    partner_id = active_chats.get(message.from_user.id)
    if partner_id:
        bot.send_message(partner_id, f"💬 {message.text}")

# --- /chord ---
@bot.message_handler(commands=["chord"])
def chord_cmd(message):
    try:
        parts = message.text.split(" ", 1)
        if len(parts) <= 1:
            safe_reply(message, "❌ Gunakan: `/chord <keyword>`\n\nContoh: `/chord wali-bocah-ngapa-yang-enak`")
            return

        keyword = parts[1].strip()
        bot.send_chat_action(message.chat.id, "typing")

        result = chord.getChord(keyword)
        if result:
            limit = 4000
            if len(result) > limit:
                safe_reply(message, f"🎸 *Chord {keyword}:*")
                for i in range(0, len(result), limit):
                    chunk = result[i:i+limit]
                    bot.send_message(message.chat.id, chunk, parse_mode="MarkdownV2")
            else:
                safe_reply(message, f"🎸 *Chord {keyword}:*\n\n{result}")
        else:
            safe_reply(message, f"❌ Chord `{keyword}` tidak ditemukan.")
    except Exception as e:
        logger.error(f"Chord error: {e}")
        safe_reply(message, "❌ Terjadi kesalahan saat mencari chord.")

# --- Text fallback ---
@bot.message_handler(content_types=['text'])
def text_handler(message):
    if message.chat.type != "private":
        return
    text = message.text.lower()
    name = message.from_user.first_name or "Friend"
    if any(g in text for g in ['hello', 'hi', 'halo', 'hey']):
        safe_reply(message, f"Hello {name}! 👋")
    elif 'bot' in text:
        safe_reply(message, "Yes, saya bot 🤖")
    else:
        safe_reply(message, f"Pesan diterima: {message.text}")

# --- Media messages ---
@bot.message_handler(content_types=['photo','video','audio','document','voice','sticker'])
def media_handler(message):
    safe_reply(message, "Terima kasih! Pesan media diterima ✅")

# ===== Flask webhook =====
@app.route("/")
def home():
    return "Halo Rio Bot sudah Online, Bot is running!"

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    try:
        json_data = request.get_json(force=True, silent=True)
        logger.info(f"📩 Update masuk: {json_data}")
        if not json_data:
            return "no data", 400
        update = telebot.types.Update.de_json(json_data)
        bot.process_new_updates([update])
    except Exception as e:
        logger.exception(f"Webhook error: {e}")
    return "OK", 200

# ===== Setup webhook on start =====
def setup_webhook():
    try:
        bot.remove_webhook()
        bot.set_webhook(url=f"{RENDER_URL}/{BOT_TOKEN}")
        logger.info(f"✅ Webhook set at {RENDER_URL}/{BOT_TOKEN}")
    except Exception as e:
        logger.error(f"❌ Failed to set webhook: {e}")

# ===== Main =====
if __name__ == "__main__":
    print("🤖 Telegram Bot Starting with Webhook...")
    setup_webhook()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
