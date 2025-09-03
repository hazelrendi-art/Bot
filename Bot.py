import os
import logging
from datetime import datetime
from flask import Flask, request
import telebot

# ===== Logging =====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("MyBot")

# ===== Bot Config =====
BOT_TOKEN = os.getenv("BOT_TOKEN", "7566896092:AAEQIx0dynG7xM8vO0W5wj9X4bm5wqyRX7o")
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
        json_str = request.get_data().decode("UTF-8")   # ambil raw string JSON
        logger.info(f"📩 Incoming update: {json_str}")
        update = telebot.types.Update.de_json(json_str)  # kirim string, bukan dict
        bot.process_new_updates([update])
        logger.info("✅ Update diteruskan ke handlers")
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
    return "OK", 200

@app.route("/test", methods=["GET"])
def test_send():
    try:
        chat_id = os.getenv("TEST_CHAT_ID", "6488874900")  # ganti ID kamu
        bot.send_message(chat_id, "🚀 Test pesan langsung dari Flask berhasil!")
        return "Pesan test terkirim!", 200
    except Exception as e:
        logger.error(f"❌ Gagal kirim test: {e}")
        return f"Error: {e}", 500

# ===== Command Handlers =====
@bot.message_handler(commands=["start"])
def start_cmd(message):
    logger.info(f"👉 /start dari {message.from_user.id}")
    try:
        text = f"Halo {message.from_user.first_name}! 👋\nKetik /help untuk bantuan."
        bot.reply_to(message, text, parse_mode="MarkdownV2")
        logger.info("✅ Balasan /start terkirim")
    except Exception as e:
        logger.error(f"❌ Gagal kirim balasan: {e}")

@bot.message_handler(commands=["help"])
def help_cmd(message):
    logger.info(f"👉 /help dari {message.from_user.id}")
    text = (
        "📚 *Perintah Bot:*\n"
        "/start - Mulai bot\n"
        "/help - Lihat bantuan\n"
        "/time - Waktu server"
    )
    bot.reply_to(message, text, parse_mode="MarkdownV2")

@bot.message_handler(commands=["time"])
def time_cmd(message):
    logger.info(f"👉 /time dari {message.from_user.id}")
    current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    bot.reply_to(message, f"🕒 Sekarang: `{current_time}`", parse_mode="MarkdownV2")

# ===== Webhook Setup =====
def set_webhook():
    render_domain = os.getenv("RENDER_EXTERNAL_HOSTNAME", "localhost:10000")
    webhook_url = f"https://{render_domain}/{BOT_TOKEN}"

    try:
        bot.remove_webhook()
        bot.set_webhook(url=webhook_url)
        logger.info(f"✅ Webhook di-set: {webhook_url}")
    except Exception as e:
        logger.error(f"❌ Gagal set webhook: {e}")

set_webhook()

# ===== Run Local (optional) =====
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
