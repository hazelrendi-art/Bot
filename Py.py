import os
import logging
from datetime import datetime
from flask import Flask, request
import telebot
import requests

# ===== Logging =====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("Py")

# ===== Bot Config =====
BOT_TOKEN = os.getenv("BOT_TOKEN", "ISI_TOKEN_KAMU")
bot = telebot.TeleBot(BOT_TOKEN)

# ===== Flask App =====
app = Flask(__name__)

# === Health Check ===
@app.route("/", methods=["GET", "HEAD"])
def home():
    return "Bot is running 🚀", 200

# === Webhook Endpoint ===
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def process_webhook():
    try:
        json_str = request.get_data().decode("UTF-8")
        update = telebot.types.Update.de_json(json_str)
        logger.info(f"📩 Incoming update: {json_str}")
        bot.process_new_updates([update])
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
    return "OK", 200


# ===== Command Handlers =====
@bot.message_handler(commands=["start"])
def send_welcome(message):
    logger.info(f"👉 Handler /start dipanggil oleh {message.from_user.id}")
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
        bot.reply_to(message, welcome_text)
    except Exception as e:
        logger.error(f"❌ Error di handler /start: {e}")


@bot.message_handler(commands=["help"])
def send_help(message):
    logger.info(f"👉 Handler /help dipanggil oleh {message.from_user.id}")
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
    bot.reply_to(message, help_text, parse_mode="MarkdownV2")


@bot.message_handler(commands=["info"])
def send_info(message):
    logger.info(f"👉 Handler /info dipanggil oleh {message.from_user.id}")
    info_text = f"""
ℹ️ *Bot Info:*
🤖 Name: PyTelegramBot
⚡ Status: Online
📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
👤 Your ID: {message.from_user.id}
💬 Chat ID: {message.chat.id}
    """
    bot.reply_to(message, info_text, parse_mode="MarkdownV2")


@bot.message_handler(commands=["time"])
def send_time(message):
    logger.info(f"👉 Handler /time dipanggil oleh {message.from_user.id}")
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    bot.reply_to(message, f"🕐 *Server Time:*\n`{current_time}`", parse_mode="Markdown")


@bot.message_handler(commands=["echo"])
def echo_message(message):
    logger.info(f"👉 Handler /echo dipanggil oleh {message.from_user.id}")
    command_parts = message.text.split(" ", 1)
    if len(command_parts) > 1:
        bot.reply_to(message, f"🔄 *Echo:* {command_parts[1]}", parse_mode="Markdown")
    else:
        bot.reply_to(message, "Usage: `/echo Hello!`", parse_mode="Markdown")


# ===== Webhook Setup =====
def set_webhook():
    RENDER_DOMAIN = os.getenv("RENDER_EXTERNAL_HOSTNAME", "bot-lwq9.onrender.com")
    WEBHOOK_URL = f"https://{RENDER_DOMAIN}/{BOT_TOKEN}"

    try:
        bot.remove_webhook()
        bot.set_webhook(url=WEBHOOK_URL)
        logger.info(f"✅ Webhook set to {WEBHOOK_URL}")
    except Exception as e:
        logger.error(f"❌ Gagal set webhook: {e}")


set_webhook()

# ===== Run Local (optional) =====
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
