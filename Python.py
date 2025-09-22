#libr&& package    
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
from telebot import types
import re
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from client import JavtifulScraper

scraper = JavtifulScraper()

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
/help - Daftar perintah Bot
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
/chord - mencari chord + lirik lagu
/echo <text> - Echo message
/fb <link> - Download Facebook video
/yt <link> - Download Youtube
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
😎 Owner : Rhyo
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
    

# --- /jav ---
@bot.message_handler(commands=['jav'])
def jav_cmd(message):
    try:
        parts = message.text.split(' ', 1)
        if len(parts) <= 1:
            bot.reply_to(message, "❌ Gunakan: `/jav <link>`", parse_mode="Markdown")
            return

        jav_url = parts[1].strip()
        msg = bot.reply_to(message, "⏳ Processing...")

        try:
            video_url = scraper.get_video_url(jav_url)
            teks = f"✅ Video link ditemukan:\n{video_url}"
            bot.edit_message_text(teks, chat_id=msg.chat.id, message_id=msg.message_id,
                                  disable_web_page_preview=True)
        except Exception as e:
            bot.edit_message_text(f"❌ Error: {str(e)}", chat_id=msg.chat.id, message_id=msg.message_id)

    except Exception as e:
        logger.error(f"JAV error: {e}")
        bot.reply_to(message, "❌ Terjadi kesalahan saat ambil video JAV.")




# ===== SIMPAN DATA CHORD PER USER =====
user_chords = {}
user_transpose = {}
user_chunks = {}   # simpan list message_id chunk tambahan

# GANTIKAN fungsi transpose_chord & transpose_text lama dengan ini

CHORD_ROOTS = ["C", "C#", "Db", "D", "D#", "Eb", "E", "F", "F#", "Gb",
               "G", "G#", "Ab", "A", "A#", "Bb", "B"]
# Normalisasi roots ke bentuk '#' untuk indexing
NORMAL_MAP = {
    "Db": "C#", "D#": "D#", "Eb": "D#", "F#": "F#", "Gb": "F#",
    "G#": "G#", "Ab": "G#", "A#": "A#", "Bb": "A#", 
    # keep naturals
}

# canonical order using sharps (12-tone)
NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

def normalize_root(root):
    """Normalize root (Db -> C#, Eb -> D#, etc.) and keep uppercase."""
    if root in NORMAL_MAP:
        return NORMAL_MAP[root]
    return root

def transpose_chord(chord_token: str, steps: int) -> str:
    """
    Transpose a single chord token.
    Supported token examples:
      C, C#, Db, Am, A#m7, F#sus4, G/B, Em7/G, Dm9, Asus2
    """
    # split possible slash chord
    if "/" in chord_token:
        left, right = chord_token.split("/", 1)
        return transpose_chord(left, steps) + "/" + transpose_chord(right, steps)

    # match root + accidental + suffix (everything after root)
    m = re.match(r"^([A-G])([#b]?)(.*)$", chord_token)
    if not m:
        return chord_token  # not a chord
    root_base = m.group(1) + (m.group(2) or "")
    suffix = m.group(3) or ""

    root_norm = normalize_root(root_base)
    # if normalization didn't map and root_norm not in NOTES, return unchanged
    if root_norm not in NOTES:
        return chord_token

    idx = NOTES.index(root_norm)
    new_root = NOTES[(idx + steps) % len(NOTES)]
    # preserve original accidental style? we'll return with sharps (consistent)
    return new_root + suffix

def transpose_text(text: str, steps: int) -> str:
    """
    Transpose only chord tokens in the given text.
    Uses a regex that matches chord tokens as whole words so normal lyrics are safe.
    """
    # Pattern explanation:
    # \b - word boundary so not inside words
    # ([A-G])([#b]?) - root letter + optional accidental
    # (?:maj|min|m|dim|aug|sus|add|sus2|sus4|maj7|m7|7|9|11|13|add9|sus4|sus2|add2|add11|add13)? - optional modifiers (non-capturing)
    # (?:\d+)? - optional number (for m7, 9, 11, etc)
    # (?:/[A-G][#b]?)? - optional slash chord
    # \b - end boundary
    chord_pattern = re.compile(
        r'\b([A-G][#b]?'
        r'(?:maj7|maj|min|m7|m|dim|aug|sus2|sus4|sus|add9|add11|add13|add2|add)?\d*'
        r'(?:/[A-G][#b]?)?)\b'
    )

    def _repl(m):
        token = m.group(1)
        return transpose_chord(token, steps)

    # Only replace when token matches the chord pattern as a standalone token
    return chord_pattern.sub(_repl, text)



# ===== Fungsi helper untuk kirim chord panjang =====
def send_chord_chunks(chat_id, teks, slug, label="Asli", reply_markup=None):
    MAX_LEN = 4000
    chunks = [teks[i:i+MAX_LEN] for i in range(0, len(teks), MAX_LEN)]
    sent_ids = []

    # kirim bagian pertama dengan tombol transpose
    first_msg = bot.send_message(
        chat_id,
        f"🎸 *Chord {slug}* ({label}):\n\n```\n{chunks[0]}\n```",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    sent_ids.append(first_msg.message_id)

    # kirim sisa chunk tanpa tombol
    for c in chunks[1:]:
        m = bot.send_message(
            chat_id,
            f"```\n{c}\n```",
            parse_mode="Markdown"
        )
        sent_ids.append(m.message_id)

    return sent_ids





# ===== Command /chord =====
@bot.message_handler(commands=["chord"])
def chord_cmd(message):
    try:
        parts = message.text.split(" ", 1)
        if len(parts) <= 1:
            bot.reply_to(
                message,
                "❌ Gunakan: `/chord <slug>`\n\nContoh: `/chord wali-bocah-ngapa-yang-enak`",
                parse_mode="Markdown"
            )
            return

        slug = parts[1].strip()
        bot.send_chat_action(message.chat.id, "typing")

        result = chord.getChord(slug)
        if not result:
            bot.reply_to(message, f"❌ Chord `{slug}` tidak ditemukan.", parse_mode="Markdown")
            return

        # simpan chord + reset transpose
        user_chords[message.chat.id] = result
        user_transpose[message.chat.id] = 0

        # buat tombol inline
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("➖1", callback_data="transpose_-1"),
            InlineKeyboardButton("🔄 Reset", callback_data="transpose_0"),
            InlineKeyboardButton("➕1", callback_data="transpose_1")
        )

        # kirim chord dalam bentuk chunk
        sent_ids = send_chord_chunks(message.chat.id, result, slug, "Asli", markup)
        user_chunks[message.chat.id] = sent_ids

    except Exception as e:
        logger.error(f"Chord error: {e}")
        bot.reply_to(message, "❌ Terjadi kesalahan saat mencari chord.")


# ===== Callback Transpose =====
@bot.callback_query_handler(func=lambda call: call.data.startswith("transpose_"))
def callback_transpose(call):
    try:
        action = call.data.split("_")[1]
        chat_id = call.message.chat.id

        if chat_id not in user_chords:
            bot.answer_callback_query(call.id, "⚠️ Ambil chord dulu dengan /chord")
            return

        teks = user_chords[chat_id]

        if action == "0":  # reset
            user_transpose[chat_id] = 0
            hasil = teks
            label = "Asli"
        else:
            steps = int(action)
            user_transpose[chat_id] += steps
            total_steps = user_transpose[chat_id]
            hasil = transpose_text(teks, total_steps)
            label = f"Transpose {total_steps}"

        # tombol inline
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("➖1", callback_data="transpose_-1"),
            InlineKeyboardButton("🔄 Reset", callback_data="transpose_0"),
            InlineKeyboardButton("➕1", callback_data="transpose_1")
        )

        # hapus semua chunk lama
        if chat_id in user_chunks:
            for mid in user_chunks[chat_id]:
                try:
                    bot.delete_message(chat_id, mid)
                except:
                    pass

        # kirim ulang hasil transpose dalam chunk baru
        sent_ids = send_chord_chunks(chat_id, hasil, "Lagu", label, markup)
        user_chunks[chat_id] = sent_ids

    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Error: {e}")







#  --- Fallback text handler ---
@bot.message_handler(content_types=['text'])
def text_handler(message):
    OWNER_ID = 6488874900  # ganti dengan user ID kamu
    
    # Kalau chat grup DAN pengirim adalah kamu
    if message.chat.type in ["group", "supergroup"]:
        if message.from_user.id == OWNER_ID:
            name = message.from_user.first_name or message.from_user.username or "Ketua"
            bot.reply_to(message, f"🚨 Perhatian semua! Ketua {name} telah tiba! 👑")
        return  # biar tidak lanjut ke logika private chat

    # Kalau chat private
    if message.chat.type == "private":
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

@app.route("/ping")
def ping():
    return "OK"


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
