import requests
import logging

logger = logging.getLogger(__name__)

def handle_tohitam(bot, message):
    try:
        if not message.caption or not message.caption.lower().startswith("/tohitam"):
            return  # Skip jika caption tidak sesuai

        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        file_bytes = bot.download_file(file_info.file_path)

        # Upload ke qu.ax (buat dapat link)
        files = {"files[]": ("image.jpg", file_bytes)}
        resp = requests.post("https://qu.ax/upload.php", files=files)
        if resp.status_code != 200:
            bot.reply_to(message, "❌ Gagal upload foto.")
            return

        json_resp = resp.json()
        uploaded_url = json_resp['files'][0]['url']

        # Panggil API tohitam
        params = {"link": uploaded_url, "apikey": "key-Adhrian123"}
        resp2 = requests.get("https://api.ferdev.my.id/maker/tohitam", params=params, timeout=60)

        if resp2.headers.get("Content-Type", "").startswith("image/"):
            # Kalau langsung image
            bot.send_photo(message.chat.id, resp2.content, caption="🖤 Hasil foto hitam")
        else:
            try:
                data = resp2.json()
                if data.get("success"):
                    result_url = data["result"]
                    bot.send_photo(message.chat.id, result_url, caption="🖤 Hasil foto hitam")
                else:
                    bot.reply_to(message, f"❌ API error: {data.get('message','Unknown')}")
            except Exception:
                bot.reply_to(message, "⚠️ Respon API tidak valid.")

    except Exception as e:
        logger.error(f"Tohitam handler error: {e}")
        bot.reply_to(message, "⚠️ Terjadi kesalahan saat memproses gambar.")
