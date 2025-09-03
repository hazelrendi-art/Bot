import os
import logging
import requests
from datetime import datetime
from flask import Flask, request
import telebot

# ===== Bot Config =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
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
waiting_users = []
active_chats = {}
ai_mode_enabled = False

# ===== Groq AI Config =====
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# ===== Helper Function =====
def ask_ai(query):
    try:
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": query}
            ]
        }
        resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        else:
            return f"❌ AI API error: {resp.status_code}"
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return "❌ Terjadi kesalahan AI."

# ===== Commands =====

# --- AI On/Off ---
@bot.message_handler(commands=['aiOn'])
def ai_on(message):
    global ai_mode_enabled
    ai_mode_enabled = True
    bot.reply_to(message, "✅ *AI Mode aktif!*", parse_mode="Markdown")

@bot.message_handler(commands=['aiOff'])
def ai_off(message):
    global ai_mode_enabled
    ai_mode_enabled = False
    bot.reply_to(message, "❌ *AI Mode dimatikan.*", parse_mode="Markdown")

@bot.message_handler(commands=['ai'])
def ai_chat(message):
    parts = message.text.split(' ', 1)
    if len(parts) <= 1:
        bot.reply_to(message, "❌ Contoh: `/ai apa itu python?`", parse_mode="Markdown")
        return
    answer = ask_ai(parts[1])
    bot.reply_to(message, f"🤖 *AI Response:*\n{answer}", parse_mode="Markdown")

# --- Anonymous Chat ---
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

# --- Welcome & Help ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, f"""
🤖 *Welcome to the Bot!*

Hello {message.from_user.first_name}! 👋

Perintah:
/help - Lihat semua perintah
/ai - Tanya AI
/aiOn - Aktifkan AI otomatis
/aiOff - Matikan AI
/anonymous - Chat anonim
/stop - Stop chat anonim
/facebook <url> - Download video FB
/echo <text> - Echo message
    """, parse_mode='Markdown')

@bot.message_handler(commands=['help'])
def send_help(message):
    bot.reply_to(message, """
📚 *Commands:*
/start - Welcome
/help - Bantuan
/info - Info bot
/time - Waktu server
/echo <text> - Echo
/facebook <link> - Download FB video
/ai <query> - Tanya AI
/aiOn - Aktifkan AI mode
/aiOff - Matikan AI mode
/anonymous - Chat anonim
/stop - Keluar chat anonim
    """, parse_mode='Markdown')

# --- Info / Time ---
@bot.message_handler(commands=['info'])
def send_info(message):
    bot.reply_to(message, f"""
ℹ️ *Bot Info:*
🤖 Name: PyTelegramBot
⚡ Status: Online
📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
👤 Your ID: {message.from_user.id}
💬 Chat ID: {message.chat.id}
    """, parse_mode='Markdown')

@bot.message_handler(commands=['time'])
def send_time(message):
    bot.reply_to(message, f"🕐 Server Time:\n`{datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}`", parse_mode='Markdown')

# --- Echo ---
@bot.message_handler(commands=['echo'])
def echo_message(message):
    parts = message.text.split(' ', 1)
    if len(parts) > 1:
        bot.reply_to(message, f"🔄 *Echo:* {parts[1]}", parse_mode='Markdown')
    else:
        bot.reply_to(message, "Usage: `/echo Hello!`", parse_mode='Markdown')

# --- Facebook Downloader ---
@bot.message_handler(commands=['facebook'])
def facebook_download(message):
    parts = message.text.split(' ', 1)
    if len(parts) <= 1:
        bot.reply_to(message, "Usage: `/facebook <link>`", parse_mode='Markdown')
        return
    fb_url = parts[1].strip()
    if 'facebook.com' not in fb_url and 'fb.com' not in fb_url:
        bot.reply_to(message, "❌ Invalid Facebook link!")
        return
    processing_msg = bot.reply_to(message, "⏳ Processing...")
    try:
        api_url = "https://api.ferdev.my.id/downloader/facebook"
        params = {'link': fb_url, 'apikey': "key-Adhrian123"}
        resp = requests.get(api_url, params=params, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('success') and data.get('status') == 200:
                result = data.get('data', {})
                hd_url = result.get('hd', '')
                sd_url = result.get('sd', '')
                title = result.get('title', 'Facebook Video')
                original_url = result.get('url', fb_url)
                text = f"✅ *Download Success!*\n📹 {title}\n🔗 [Link]({original_url})"
                if hd_url: text += f"\n• [HD]({hd_url})"
                if sd_url: text += f"\n• [SD]({sd_url})"
                bot.edit_message_text(text, chat_id=processing_msg.chat.id, message_id=processing_msg.message_id, parse_mode='Markdown', disable_web_page_preview=True)
            else:
                bot.edit_message_text("❌ Failed to fetch video.", chat_id=processing_msg.chat.id, message_id=processing_msg.message_id)
        else:
            bot.edit_message_text("❌ API request failed.", chat_id=processing_msg.chat.id, message_id=processing_msg.message_id)
    except Exception as e:
        logger.error(f"FB Error: {e}")
        bot.reply_to(message, "❌ Error processing link.")

# --- Unknown Commands ---
@bot.message_handler(func=lambda m: m.text.startswith('/'))
def unknown_command(message):
    bot.reply_to(message, f"❓ Unknown command: `{message.text}`", parse_mode='Markdown')

# --- Text Messages (AI Mode) ---
@bot.message_handler(content_types=['text'])
def handle_text_messages(message):
    global ai_mode_enabled
    if ai_mode_enabled:
        answer = ask_ai(message.text)
        bot.reply_to(message, f"🤖 *AI:*\n{answer}", parse_mode='Markdown')
    else:
        user_text = message.text.lower()
        user_name = message.from_user.first_name or "Friend"
        if any(g in user_text for g in ['hello','hi','hey','halo']):
            bot.reply_to(message, f"Hello {user_name}! 👋")
        elif "how" in user_text and "you" in user_text:
            bot.reply_to(message, "I'm doing great! How are you?")
        elif "thank" in user_text or "terima kasih" in user_text:
            bot.reply_to(message, "You're welcome! 😊")
        elif "bye" in user_text:
            bot.reply_to(message, "Goodbye! 👋")
        else:
            bot.reply_to(message, f"Thanks for your message, {user_name}!")

# --- Media Messages ---
@bot.message_handler(content_types=['photo','document','audio','video','voice','sticker'])
def handle_media(message):
    user_name = message.from_user.first_name or "Friend"
    responses = {
        'photo': f"Nice photo, {user_name}! 📸",
        'document': f"Got your document, {user_name}! 📄",
        'audio': f"Cool audio, {user_name}! 🎵",
        'video': f"Thanks for the video, {user_name}! 🎥",
        'voice': f"Got your voice note, {user_name}! 🎤",
        'sticker': f"Nice sticker, {user_name}! 😄"
    }
    bot.reply_to(message, responses.get(message.content_type, f"Got your {message.content_type}, {user_name}!"))

# ===== Flask Routes for Webhook =====
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

# ===== Main =====
if __name__ == "__main__":
    render_url = os.getenv("RENDER_URL")
    if render_url:
        bot.remove_webhook()
        bot.set_webhook(url=f"{render_url}/{BOT_TOKEN}")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0.0", port=port)

