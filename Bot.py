import telebot
import logging
import os
import requests
from datetime import datetime
from flask import Flask, request

# ===== Konfigurasi Bot =====
BOT_TOKEN = os.getenv('BOT_TOKEN', '7566896092:AAES1sc_K3RdeA-4vAVOxXhWSbO_Fby8Ges')
bot = telebot.TeleBot(BOT_TOKEN)

# ===== Anonymous Chat Feature =====
waiting_users = []  # antrean user yang menunggu pasangan
active_chats = {}   # pasangan chat {user_id: partner_id}

# ===== AI Mode Flag =====
ai_mode_enabled = False   # default: mati

# ===== Logging =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===== Groq AI Integration =====
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "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")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


# === Command untuk AI Mode ON ===
@bot.message_handler(commands=['aiOn'])
def ai_on(message):
    global ai_mode_enabled
    ai_mode_enabled = True
    bot.reply_to(message, "✅ *AI Mode aktif!*\nSemua pesanmu sekarang dijawab AI.", parse_mode="Markdown")


# === Command untuk AI Mode OFF ===
@bot.message_handler(commands=['aiOff'])
def ai_off(message):
    global ai_mode_enabled
    ai_mode_enabled = False
    bot.reply_to(message, "❌ *AI Mode dimatikan.*\nBot kembali ke mode normal.", parse_mode="Markdown")


# === Manual AI command (/ai <query>) ===
@bot.message_handler(commands=['ai'])
def ai_chat(message):
    try:
        command_parts = message.text.split(' ', 1)
        if len(command_parts) <= 1:
            bot.reply_to(message, "❌ Harap masukkan pertanyaan. Contoh:\n`/ai apa itu python?`", parse_mode="Markdown")
            return
        
        user_query = command_parts[1].strip()
        bot.send_chat_action(message.chat.id, 'typing')

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
            bot.reply_to(message, f"🤖 *AI Response:*\n{answer}", parse_mode="Markdown")
        else:
            bot.reply_to(message, f"❌ API Error: {response.status_code}\n{response.text}")
    
    except Exception as e:
        logger.error(f"Error in /ai command: {e}")
        bot.reply_to(message, "❌ Terjadi kesalahan saat menghubungi AI. Coba lagi nanti.")


# === Anonymous Chat ===
@bot.message_handler(commands=['anonymous'])
def anonymous_start(message):
    user_id = message.from_user.id

    if user_id in active_chats:
        bot.reply_to(message, "❌ Kamu sudah berada dalam obrolan anonim.\nGunakan /stop untuk keluar.")
        return

    if user_id in waiting_users:
        bot.reply_to(message, "⏳ Kamu sudah menunggu pasangan. Mohon tunggu ya...")
        return

    if waiting_users:
        partner_id = waiting_users.pop(0)
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id

        bot.send_message(user_id, "✅ Kamu terhubung dengan pasangan anonim!\nGunakan /stop untuk keluar.")
        bot.send_message(partner_id, "✅ Kamu terhubung dengan pasangan anonim!\nGunakan /stop untuk keluar.")
        logger.info(f"Anonymous chat started between {user_id} and {partner_id}")
    else:
        waiting_users.append(user_id)
        bot.reply_to(message, "⏳ Menunggu pasangan anonim... Mohon tunggu.")


@bot.message_handler(commands=['stop'])
def stop_anonymous(message):
    user_id = message.from_user.id

    if user_id in active_chats:
        partner_id = active_chats.pop(user_id, None)
        if partner_id:
            active_chats.pop(partner_id, None)
            bot.send_message(partner_id, "⚠️ Pasangan anonimmu keluar dari obrolan.")
        bot.send_message(user_id, "❌ Kamu keluar dari obrolan anonim.")
    elif user_id in waiting_users:
        waiting_users.remove(user_id)
        bot.reply_to(message, "❌ Kamu batal menunggu pasangan anonim.")
    else:
        bot.reply_to(message, "ℹ️ Kamu tidak sedang berada di obrolan anonim.")


@bot.message_handler(func=lambda m: m.from_user.id in active_chats, content_types=['text'])
def relay_anonymous_message(message):
    user_id = message.from_user.id
    partner_id = active_chats.get(user_id)
    if partner_id:
        try:
            bot.send_message(partner_id, f"💬 {message.text}")
        except Exception as e:
            logger.error(f"Error relaying message: {e}")
            bot.reply_to(message, "❌ Gagal mengirim pesan ke pasanganmu.")


# === Welcome & Help ===
@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        welcome_text = f"""
🤖 *Welcome to the Bot!*

Hello {message.from_user.first_name}! 👋

Saya bot serbaguna. Berikut yang bisa saya lakukan:
/help - Lihat semua perintah
/ai - Tanya AI asisten
/aiOn - Aktifkan mode AI otomatis
/aiOff - Matikan mode AI otomatis
/anonymous - Obrolan anonim
/facebook <url> - Download video Facebook
        """
        bot.reply_to(message, welcome_text, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in start command: {e}")


@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = """
📚 *Available Commands:*
/start - Welcome message
/help - Show this help
/info - Bot info
/time - Server time
/echo <text> - Echo message
/facebook <link> - Download FB video
/ai <query> - Tanya AI sekali
/aiOn - Aktifkan AI mode otomatis
/aiOff - Matikan AI mode otomatis
/anonymous - Chat anonim
/stop - Keluar dari chat anonim
    """
    bot.reply_to(message, help_text, parse_mode='Markdown')


# === Info Commands ===
@bot.message_handler(commands=['info'])
def send_info(message):
    info_text = f"""
ℹ️ *Bot Info:*
🤖 Name: PyTelegramBot
⚡ Status: Online
📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
👤 Your ID: {message.from_user.id}
💬 Chat ID: {message.chat.id}
    """
    bot.reply_to(message, info_text, parse_mode='Markdown')


@bot.message_handler(commands=['time'])
def send_time(message):
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
    bot.reply_to(message, f"🕐 *Server Time:*\n`{current_time}`", parse_mode='Markdown')


# === Facebook Downloader ===
@bot.message_handler(commands=['facebook'])
def facebook_download(message):
    try:
        command_parts = message.text.split(' ', 1)
        if len(command_parts) <= 1:
            bot.reply_to(message, "Usage: `/facebook <link>`", parse_mode="Markdown")
            return
        
        fb_url = command_parts[1].strip()
        if 'facebook.com' not in fb_url and 'fb.com' not in fb_url:
            bot.reply_to(message, "❌ Invalid Facebook link!")
            return

        processing_msg = bot.reply_to(message, "⏳ Processing link...")

        api_url = "https://api.ferdev.my.id/downloader/facebook"
        api_key = "key-Adhrian123"
        params = {'link': fb_url, 'apikey': api_key}
        response = requests.get(api_url, params=params, timeout=30)

        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('status') == 200:
                result = data.get('data', {})
                hd_url = result.get('hd', '')
                sd_url = result.get('sd', '')
                title = result.get('title', 'Facebook Video')
                original_url = result.get('url', fb_url)

                success_text = f"✅ *Download Success!*\n📹 {title}\n🔗 [Link]({original_url})"
                if hd_url:
                    success_text += f"\n• [HD]({hd_url})"
                if sd_url:
                    success_text += f"\n• [SD]({sd_url})"

                bot.edit_message_text(success_text, chat_id=processing_msg.chat.id, message_id=processing_msg.message_id,
                                      parse_mode='Markdown', disable_web_page_preview=True)
            else:
                bot.edit_message_text("❌ Failed to fetch video.", chat_id=processing_msg.chat.id,
                                      message_id=processing_msg.message_id)
        else:
            bot.edit_message_text("❌ API request failed.", chat_id=processing_msg.chat.id,
                                  message_id=processing_msg.message_id)
    except Exception as e:
        logger.error(f"FB error: {e}")
        bot.reply_to(message, "❌ Error processing link.")


# === Echo ===
@bot.message_handler(commands=['echo'])
def echo_message(message):
    command_parts = message.text.split(' ', 1)
    if len(command_parts) > 1:
        bot.reply_to(message, f"🔄 *Echo:* {command_parts[1]}", parse_mode='Markdown')
    else:
        bot.reply_to(message, "Usage: `/echo Hello!`", parse_mode='Markdown')


# === Unknown Commands ===
@bot.message_handler(func=lambda message: message.text.startswith('/'))
def unknown_command(message):
    bot.reply_to(message, f"❓ Unknown command: `{message.text}`", parse_mode='Markdown')


# === Text Messages (AI Mode check) ===
@bot.message_handler(content_types=['text'])
def handle_text_messages(message):
    global ai_mode_enabled
    try:
        if ai_mode_enabled:
            # AI Mode aktif
            bot.send_chat_action(message.chat.id, 'typing')
            headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
            payload = {
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": message.text}
                ]
            }
            response = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                data = response.json()
                answer = data["choices"][0]["message"]["content"]
                bot.reply_to(message, f"🤖 *AI:*\n{answer}", parse_mode="Markdown")
            else:
                bot.reply_to(message, "❌ AI API error.")
        else:
            # Mode biasa
            user_text = message.text.lower()
            user_name = message.from_user.first_name or "Friend"
            if any(g in user_text for g in ['hello', 'hi', 'hey', 'halo']):
                response = f"Hello {user_name}! 👋"
            elif "how" in user_text and "you" in user_text:
                response = "I'm doing great! How are you?"
            elif "thank" in user_text or "terima kasih" in user_text:
                response = "You're welcome! 😊"
            elif "bye" in user_text:
                response = "Goodbye! 👋"
            else:
                response = f"Thanks for your message, {user_name}!"
            bot.reply_to(message, response)
    except Exception as e:
        logger.error(f"Error handling text: {e}")
        bot.reply_to(message, "❌ Error processing message.")


# === Media Messages ===
@bot.message_handler(content_types=['photo', 'document', 'audio', 'video', 'voice', 'sticker'])
def handle_media_messages(message):
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


# === Flask Webhook ===
app = Flask(__name__)

@app.route('/')
def index():
    return "🤖 Bot is running with webhook!", 200

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200


if __name__ == '__main__':
    # Set webhook otomatis ke URL Render
    RENDER_URL = os.getenv("RENDER_URL", "https://bot-lwq9.onrender.com")
    full_webhook_url = f"{RENDER_URL}/{BOT_TOKEN}"

    try:
        setwebhook_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={full_webhook_url}"
        resp = requests.get(setwebhook_url)
        logger.info(f"SetWebhook response: {resp.text}")
    except Exception as e:
        logger.error(f"Gagal setWebhook: {e}")

    # Jalanin Flask server
    port = int(os.getenv('PORT', 5000))
    app.run(host="0.0.0.0", port=port)
