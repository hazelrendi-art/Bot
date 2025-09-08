import os
import logging
import cloudscraper
import requests
import chord
from bs4 import BeautifulSoup 
from datetime import datetime
from flask import Flask, request
import telebot
from ToHitam import handle_tohitam
import re
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


# ===== Config =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
RENDER_URL = os.getenv("RENDER_URL")  # URL Render, misal https://namabot.onrender.com

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

# --- /start ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    text = f"""
🤖 *Welcome!*

Halo {message.from_user.first_name} 👋

Perintah:
/help - Daftar perintah
/ai <pertanyaan> - Tanya AI
/anonymous - Chat anonim
/stop - Stop chat anonim
"""
    bot.reply_to(message, text, parse_mode="Markdown")

# --- /help ---
@bot.message_handler(commands=['help'])
def help_cmd(message):
    text = """
📚 *Perintah:*
/start - Welcome
/help - Bantuan
/info - Info bot
/time - Waktu server
/echo <text> - Echo message
/facebook <link> - Download Facebook video
/ai <pertanyaan> - Tanya AI
/anonymous - Chat anonim
/stop - Keluar chat anonim
"""
    bot.reply_to(message, text, parse_mode="Markdown")

# --- /info ---
@bot.message_handler(commands=['info'])
def info_cmd(message):
    text = f"""
ℹ️ *Bot Info*
🤖 Bot: PyTelegramBot
⚡ Status: Online
📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
👤 Your ID: {message.from_user.id}
"""
    bot.reply_to(message, text, parse_mode="Markdown")

# --- /time ---
@bot.message_handler(commands=['time'])
def time_cmd(message):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    bot.reply_to(message, f"🕐 Waktu server: `{now}`", parse_mode="Markdown")

# --- /echo ---
@bot.message_handler(commands=['echo'])
def echo_cmd(message):
    parts = message.text.split(' ', 1)
    if len(parts) > 1:
        bot.reply_to(message, f"🔄 *Echo:* {parts[1]}", parse_mode="Markdown")
    else:
        bot.reply_to(message, "Gunakan: `/echo <text>`", parse_mode="Markdown")

# --- /ai ---
@bot.message_handler(commands=['ai'])
def ai_cmd(message):
    try:
        parts = message.text.split(' ', 1)
        if len(parts) <= 1:
            bot.reply_to(message, "❌ Gunakan: `/ai <pertanyaan>`", parse_mode="Markdown")
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
            bot.reply_to(message, f"🤖 *AI Response:*\n{answer}", parse_mode="Markdown")
        else:
            bot.reply_to(message, f"❌ AI Error: {resp.status_code}")
    except Exception as e:
        logger.error(f"AI command error: {e}")
        bot.reply_to(message, "❌ Terjadi kesalahan AI.")

# --- /anonymous ---
@bot.message_handler(commands=['anonymous'])
def anon_start(message):
    user_id = message.from_user.id
    if user_id in active_chats:
        bot.reply_to(message, "❌ Sudah dalam obrolan.")
        return
    if user_id in waiting_users:
        bot.reply_to(message, "⏳ Menunggu pasangan...")
        return
    if waiting_users:
        partner_id = waiting_users.pop(0)
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id
        bot.send_message(user_id, "✅ Terhubung! /stop untuk keluar.")
        bot.send_message(partner_id, "✅ Terhubung! /stop untuk keluar.")
    else:
        waiting_users.append(user_id)
        bot.reply_to(message, "⏳ Menunggu pasangan anonim...")

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
        bot.reply_to(message, "❌ Batal menunggu.")
    else:
        bot.reply_to(message, "ℹ️ Tidak dalam chat.")

# --- Relay messages for anonymous chat ---
@bot.message_handler(func=lambda m: m.from_user.id in active_chats, content_types=['text'])
def relay_message(message):
    partner_id = active_chats.get(message.from_user.id)
    if partner_id:
        bot.send_message(partner_id, f"💬 {message.text}")




# --- /DOWNLOADER FUNCTION----TOOLS
# --- /youtube_Downloader ---
@bot.message_handler(commands =['yt'])
def youtube_cmd(message):
    try:
        parts = message.text.split(' ',1)
        if len(parts) <= 1:
            bot.reply_to(message, "❌ Contoh: `/yt <link youtube>`",parse_mode= 'Markdown' )
            return
        yt_url = parts[1].strip()
        if 'youtube.com' not in yt_url and 'youtu.be' not in yt_url:
            bot.reply_to(message,"❌ Url Tidak Valid !")
            return
        
        msg = bot.reply_to(message, "⏳ Processing...")
        api_url = "https://api.ferdev.my.id/downloader/ytmp4"
        params = {"link": yt_url, "apikey": "key-Adhrian123"}
        resp = requests.get(api_url, params=params, timeout=30)
        if resp.status_code == 200:
            data =resp.json()
            if data.get('success'):
                d = data.get('data',{})
                title= d.get('title','video youtube')
                dlinks = d.get('dlink')
                teks = f"✅ Sukses mendapatkan Link {title}\n"
                if dlinks: teks += f"[Download]({dlinks})"
                bot.edit_message_text(teks, chat_id=msg.chat.id, message_id=msg.message_id,
                                      parse_mode="Markdown", disable_web_page_preview=True)
            else:
                bot.edit_message_text(f"❌ API error: {data.get('message')}", chat_id=msg.chat.id,
                                      message_id=msg.message_id)
        else:
            bot.edit_message_text(f"❌ Request failed: {resp.status_code}", chat_id=msg.chat.id,
                                    message_id=msg.message_id)
    except Exception as e:
        logger.error(f"Facebook error: {e}")
        bot.reply_to(message, "❌ Terjadi kesalahan saat download Youtube.")



# --- /facebook_Downloader ---
@bot.message_handler(commands=['fb'])
def facebook_cmd(message):
    try:
        parts = message.text.split(' ', 1)
        if len(parts) <= 1:
            bot.reply_to(message, "❌ Gunakan: `/fb <link>`", parse_mode="Markdown")
            return
        fb_url = parts[1].strip()
        if 'facebook.com' not in fb_url and 'fb.com' not in fb_url:
            bot.reply_to(message, "❌ URL Facebook tidak valid!")
            return

        msg = bot.reply_to(message, "⏳ Processing...")
        api_url = "https://api.ferdev.my.id/downloader/facebook"
        params = {"link": fb_url, "apikey": "key-Adhrian123"}
        resp = requests.get(api_url, params=params, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('success'):
                d = data.get('data', {})
                hd_url = d.get('hd')
                sd_url = d.get('sd')
                title = d.get('title', 'Video Facebook')
                text = f"✅ *Download: {title}*\n"
                if hd_url: text += f"• [HD]({hd_url})\n"
                if sd_url: text += f"• [SD]({sd_url})"
                bot.edit_message_text(text, chat_id=msg.chat.id, message_id=msg.message_id,
                                      parse_mode="Markdown", disable_web_page_preview=True)
            else:
                bot.edit_message_text(f"❌ API error: {data.get('message')}", chat_id=msg.chat.id,
                                      message_id=msg.message_id)
        else:
            bot.edit_message_text(f"❌ Request failed: {resp.status_code}", chat_id=msg.chat.id,
                                  message_id=msg.message_id)
    except Exception as e:
        logger.error(f"Facebook error: {e}")
        bot.reply_to(message, "❌ Terjadi kesalahan saat download Facebook.")


# --- Fallback text handler ---

# ===== SIMPAN DATA CHORD PER USER =====
user_chords = {}
user_transpose = {}

# ===== TRANSPOSE =====
NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

def transpose_chord(chord, steps):
    match = re.match(r"([A-G][#b]?)(.*)", chord)
    if not match:
        return chord
    root, suffix = match.groups()
    if root not in NOTES:
        return chord
    idx = NOTES.index(root)
    new_root = NOTES[(idx + steps) % len(NOTES)]
    return new_root + suffix

def transpose_text(text, steps):
    def repl(match):
        return transpose_chord(match.group(0), steps)
    return re.sub(r"[A-G][#b]?(m|maj|min|dim|aug|sus|add)?\d*", repl, text)



# --- /chord ---
@bot.message_handler(commands=["chord"])
def chord_cmd(message):
    try:
        parts = message.text.split(" ", 2)
        if len(parts) <= 1:
            bot.reply_to(
                message,
                "❌ Gunakan:\n"
                "`/chord <keyword>`\n"
                "`/chord <keyword> <+/-step>` untuk transpose\n\n"
                "Contoh:\n`/chord wali-yank`\n`/chord wali-yank +2`",
                parse_mode="Markdown",
            )
            return

        keyword = parts[1].strip()
        step = 0
        if len(parts) == 3:
            try:
                step = int(parts[2])
            except ValueError:
                bot.reply_to(message, "❌ Step transpose harus angka.", parse_mode="Markdown")
                return

        bot.send_chat_action(message.chat.id, "typing")
        result = chord.getChord(keyword)

        if result:
            if step != 0:
                result = chord.transpose_text(result, step)

            limit = 4000
            header = f"🎸 *Chord {keyword}* (Transpose {step}):"
            bot.reply_to(message, header, parse_mode="Markdown")

            for i in range(0, len(result), limit):
                chunk = result[i:i+limit]
                bot.send_message(message.chat.id, chunk, parse_mode="Markdown")

            # === Inline Keyboard untuk transpose ===
            markup = types.InlineKeyboardMarkup()
            markup.row(
                types.InlineKeyboardButton("⬆️ Naik", callback_data=f"transpose:{keyword}:{step+1}"),
                types.InlineKeyboardButton("⬇️ Turun", callback_data=f"transpose:{keyword}:{step-1}")
            )
            bot.send_message(message.chat.id, "🔀 Transpose chord:", reply_markup=markup)

        else:
            bot.reply_to(message, f"❌ Chord `{keyword}` tidak ditemukan.", parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Chord error: {e}")
        bot.reply_to(message, "❌ Terjadi kesalahan saat mencari chord.")


# --- Handler callback Transpose ----
@bot.callback_query_handler(func=lambda call: call.data.startswith("transpose:"))
def transpose_callback(call):
    try:
        _, keyword, step_str = call.data.split(":")
        step = int(step_str)

        bot.send_chat_action(call.message.chat.id, "typing")
        result = chord.getChord(keyword)

        if result:
            result = chord.transpose_text(result, step)
            limit = 4000
            header = f"🎸 *Chord {keyword}* (Transpose {step}):"
            bot.send_message(call.message.chat.id, header, parse_mode="Markdown")

            for i in range(0, len(result), limit):
                chunk = result[i:i+limit]
                bot.send_message(call.message.chat.id, chunk, parse_mode="Markdown")

            # Update tombol dengan step terbaru
            markup = types.InlineKeyboardMarkup()
            markup.row(
                types.InlineKeyboardButton("⬆️ Naik", callback_data=f"transpose:{keyword}:{step+1}"),
                types.InlineKeyboardButton("⬇️ Turun", callback_data=f"transpose:{keyword}:{step-1}")
            )
            bot.send_message(call.message.chat.id, "🔀 Transpose chord:", reply_markup=markup)

        else:
            bot.send_message(call.message.chat.id, f"❌ Chord `{keyword}` tidak ditemukan.", parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Transpose callback error: {e}")
        bot.send_message(call.message.chat.id, "❌ Error saat transpose chord.")




#  --- Fallback text handler ---
@bot.message_handler(content_types=['text'])
def text_handler(message):
    # Fallback hanya aktif di private chat
    if message.chat.type != "private":
        return  

    text = message.text.lower()
    name = message.from_user.first_name or "Friend"

    if any(g in text for g in ['hello', 'hi', 'halo', 'hey']):
        bot.reply_to(message, f"Hello {name}! 👋")
    elif 'bot' in text:
        bot.reply_to(message, "Yes, saya bot 🤖")
    else:
        bot.reply_to(message, f"Pesan diterima: {message.text}")


@bot.message_handler(content_types=['photo'])
def photo_handler(message):
    # Cek dulu apakah ini command /tohitam
    if message.caption and message.caption.lower().startswith("/tohitam"):
        handle_tohitam(bot, message)
        return

    # Bisa tetap tangani media lain
    bot.reply_to(message, "Terima kasih! Pesan media diterima ✅")


# --- Media messages ---
@bot.message_handler(content_types=['photo','video','audio','document','voice','sticker'])
def media_handler(message):
    bot.reply_to(message, "Terima kasih! Pesan media diterima ✅")

# ===== Flask webhook =====
@app.route("/")
def home():
    return "Halo Rio Bot sudah Online, Bot is running!"

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    try:
        json_data = request.get_json(force=True, silent=True)
        logger.info(f"📩 Update masuk: {json_data}")   # Tambahin log biar kelihatan
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
        
setup_webhook()
# ===== Main =====
if __name__ == "__main__":
    print("🤖 Telegram Bot Starting with Webhook...")
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
