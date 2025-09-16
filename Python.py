import os
import logging
import requests
import json
import re
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from ToHitam import handle_tohitam
import chord  # pastikan modul chord tersedia

# ===== Config =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
RENDER_URL = os.getenv("RENDER_URL")  # contoh: https://namabot.onrender.com
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

if not BOT_TOKEN or not GROQ_API_KEY or not RENDER_URL:
    raise ValueError("❌ Pastikan BOT_TOKEN, GROQ_API_KEY, dan RENDER_URL sudah diset!")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# ===== Logging =====
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ===== State Chord per User =====
user_chords = {}
user_transpose = {}
user_chunks = {}

NOTES = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
NORMAL_MAP = {"Db":"C#","Eb":"D#","Gb":"F#","Ab":"G#","Bb":"A#"}

def normalize_root(root):
    return NORMAL_MAP.get(root, root)

def transpose_chord(chord_token: str, steps: int) -> str:
    if "/" in chord_token:
        left, right = chord_token.split("/",1)
        return transpose_chord(left, steps) + "/" + transpose_chord(right, steps)
    m = re.match(r"^([A-G][#b]?)(.*)$", chord_token)
    if not m: return chord_token
    root_base, suffix = m.group(1), m.group(2)
    root_norm = normalize_root(root_base)
    if root_norm not in NOTES: return chord_token
    idx = NOTES.index(root_norm)
    new_root = NOTES[(idx + steps) % 12]
    return new_root + suffix

def transpose_text(text:str, steps:int) -> str:
    chord_pattern = re.compile(r'\b([A-G][#b]?'
                               r'(?:maj7|maj|min|m7|m|dim|aug|sus2|sus4|sus|add9|add11|add13|add2|add)?\d*'
                               r'(?:/[A-G][#b]?)?)\b')
    return chord_pattern.sub(lambda m: transpose_chord(m.group(1), steps), text)

def send_chord_chunks(chat_id, teks, slug, label="Asli", reply_markup=None):
    MAX_LEN = 4000
    chunks = [teks[i:i+MAX_LEN] for i in range(0, len(teks), MAX_LEN)]
    sent_ids = []
    first = bot.send_message(chat_id,
        f"🎸 *Chord {slug}* ({label}):\n\n```\n{chunks[0]}\n```",
        parse_mode="Markdown", reply_markup=reply_markup)
    sent_ids.append(first.message_id)
    for c in chunks[1:]:
        m = bot.send_message(chat_id, f"```\n{c}\n```", parse_mode="Markdown")
        sent_ids.append(m.message_id)
    return sent_ids

# ===== Internal Commands =====
def chord_cmd(message, slug):
    try:
        result = chord.getChord(slug)
        if not result:
            bot.reply_to(message, f"❌ Chord `{slug}` tidak ditemukan.", parse_mode="Markdown")
            return
        user_chords[message.chat.id] = result
        user_transpose[message.chat.id] = 0
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("➖1", callback_data="transpose_-1"),
            InlineKeyboardButton("🔄 Reset", callback_data="transpose_0"),
            InlineKeyboardButton("➕1", callback_data="transpose_1")
        )
        sent_ids = send_chord_chunks(message.chat.id, result, slug, "Asli", markup)
        user_chunks[message.chat.id] = sent_ids
    except Exception as e:
        logger.error(f"Chord error: {e}")
        bot.reply_to(message, "❌ Terjadi kesalahan saat mencari chord.")

def youtube_cmd(message, url):
    try:
        msg = bot.reply_to(message,"⏳ Processing Youtube...")
        api_url = "https://api.ferdev.my.id/downloader/ytmp4"
        params = {"link":url,"apikey":"key-Adhrian123"}
        resp = requests.get(api_url, params=params, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success"):
                d = data.get("data", {})
                title = d.get("title","Video Youtube")
                link = d.get("dlink")
                teks = f"✅ *{title}*\n"
                if link: teks += f"[Download]({link})"
                bot.edit_message_text(teks, chat_id=msg.chat.id, message_id=msg.message_id,
                                      parse_mode="Markdown", disable_web_page_preview=True)
            else:
                bot.edit_message_text(f"❌ API error: {data.get('message')}",
                                      chat_id=msg.chat.id, message_id=msg.message_id)
        else:
            bot.edit_message_text(f"❌ Request failed: {resp.status_code}",
                                  chat_id=msg.chat.id, message_id=msg.message_id)
    except Exception as e:
        logger.error(f"Youtube error: {e}")
        bot.reply_to(message,"❌ Terjadi kesalahan saat download Youtube.")

def facebook_cmd(message, url):
    try:
        msg = bot.reply_to(message,"⏳ Processing Facebook...")
        api_url = "https://api.ferdev.my.id/downloader/facebook"
        params = {"link":url,"apikey":"key-Adhrian123"}
        resp = requests.get(api_url, params=params, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success"):
                d = data.get("data", {})
                title = d.get("title","Video Facebook")
                hd = d.get("hd"); sd = d.get("sd")
                teks = f"✅ *{title}*\n"
                if hd: teks += f"• [HD]({hd})\n"
                if sd: teks += f"• [SD]({sd})"
                bot.edit_message_text(teks, chat_id=msg.chat.id, message_id=msg.message_id,
                                      parse_mode="Markdown", disable_web_page_preview=True)
            else:
                bot.edit_message_text(f"❌ API error: {data.get('message')}",
                                      chat_id=msg.chat.id, message_id=msg.message_id)
        else:
            bot.edit_message_text(f"❌ Request failed: {resp.status_code}",
                                  chat_id=msg.chat.id, message_id=msg.message_id)
    except Exception as e:
        logger.error(f"Facebook error: {e}")
        bot.reply_to(message,"❌ Terjadi kesalahan saat download Facebook.")

# ===== AI Dispatcher =====
@bot.message_handler(func=lambda m: True, content_types=["text","photo"])
def ai_dispatch_handler(message):
    user_input = message.text or message.caption or ""
    context = """
Kamu adalah dispatcher bot Telegram.
Fitur bot:
1. Download Youtube → {"action":"yt","params":{"url":"<link>"}}
2. Download Facebook → {"action":"fb","params":{"url":"<link>"}}
3. Cari chord → {"action":"chord","params":{"slug":"<judul>"}}
4. Edit foto jadi hitam putih → {"action":"edit_photo","params":{}}
5. Chat biasa → {"action":"reply","params":{"text":"jawaban"}}

⚠️ Penting: jika user meminta mengktifkan command dari fitur bot, kamu harus mengeksekusinya, dan untuk fitur tohitam lansung kirim kan link gambar yang sudah jadi ke user,atau lansung send hasil gambarnya yang sudah jadi
"""

    payload = {
        "model":"llama-3.1-8b-instant",
        "messages":[{"role":"system","content":context},
                    {"role":"user","content":user_input}]
    }
    headers = {"Authorization":f"Bearer {GROQ_API_KEY}", "Content-Type":"application/json"}

    try:
        resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
        if resp.status_code != 200:
            bot.reply_to(message, f"❌ AI Error {resp.status_code}")
            return
        ai_content = resp.json()["choices"][0]["message"]["content"].strip()
        try:
            ai_json = json.loads(ai_content)
        except Exception:
            logger.warning(f"AI output bukan JSON: {ai_content}")
            ai_json = {"action":"reply","params":{"text":ai_content}}

        action = ai_json.get("action")
        params = ai_json.get("params",{})

        # 👇 Eksekusi fitur sesuai action, user tidak akan lihat JSON
        if action == "chord":
            slug = params.get("slug")
            if slug: chord_cmd(message, slug)
        elif action == "yt":
            url = params.get("url")
            if url: youtube_cmd(message, url)
        elif action == "fb":
            url = params.get("url")
            if url: facebook_cmd(message, url)
        elif action == "edit_photo":
            handle_tohitam(bot, message)
        else:
            bot.reply_to(message, params.get("text","🤖 AI Response"))

    except Exception as e:
        logger.error(f"AI dispatch error: {e}")
        bot.reply_to(message,"❌ Terjadi kesalahan AI.")

# ===== Webhook Flask =====
@app.route("/")
def home(): return "Bot Online!"

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    try:
        update = telebot.types.Update.de_json(request.get_json(force=True, silent=True))
        if update: bot.process_new_updates([update])
    except Exception as e:
        logger.error(f"Webhook error: {e}")
    return "OK", 200

@app.route("/ping")
def ping(): return "OK"

def setup_webhook():
    try:
        bot.remove_webhook()
        bot.set_webhook(url=f"{RENDER_URL}/{BOT_TOKEN}")
        logger.info(f"✅ Webhook set at {RENDER_URL}/{BOT_TOKEN}")
    except Exception as e:
        logger.error(f"❌ Failed to set webhook: {e}")

setup_webhook()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🤖 Bot Running on port {port} ...")
    app.run(host="0.0.0.0", port=port)
