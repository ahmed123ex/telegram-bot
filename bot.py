import os
import time
import subprocess
import threading
import urllib.request
import json
import urllib.parse
from flask import Flask

# إعداد خادم الويب الخفيف (Flask) لإبقاء البوت مستيقظاً عبر UptimeRobot
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive and running!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# إعدادات بوت تيليجرام
TELEGRAM_TOKEN = "8989308901:AAFrYSE6PAu1SKBKbyFUlH4s5JfhWZEOJsk"
telegram_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

print("--- Media Downloader Bot with Keep-Alive Server is starting ---")

last_update_id = 0

def download_media(url):
    """دالة لتحميل الفيديوهات باستخدام yt-dlp"""
    output_template = "downloads/%(id)s.%(ext)s"
    os.makedirs("downloads", exist_ok=True)
    
    command = [
        "yt-dlp",
        "-f", "best[filesize<50M]/best",
        "-o", output_template,
        url
    ]
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=90)
        if result.returncode == 0:
            files = os.listdir("downloads")
            if files:
                latest_file = max([os.path.join("downloads", f) for f in files], key=os.path.getctime)
                return latest_file
    except Exception as e:
        print(f"Download Error: {e}")
    return None

def telegram_bot_loop():
    global last_update_id
    while True:
        try:
            updates_url = f"{telegram_url}/getUpdates?offset={last_update_id + 1}&timeout=30"
            response = urllib.request.urlopen(updates_url)
            data = json.loads(response.read().decode())

            if data.get("ok") and data.get("result"):
                for update in data["result"]:
                    last_update_id = update["update_id"]
                    
                    if "message" in update and "text" in update["message"]:
                        chat_id = update["message"]["chat"]["id"]
                        user_message = update["message"]["text"].strip()
                        user_name = update["message"].get("from", {}).get("first_name", "صديقي")

                        print(f"[رابط مستلم من {user_name}]: {user_message}")

                        if user_message.startswith("http://") or user_message.startswith("https://"):
                            notif_url = f"{telegram_url}/sendMessage?chat_id={chat_id}&text={urllib.parse.quote('⏳ جاري جلب وتحميل الملف، انتظر قليلاً...')}"
                            urllib.request.urlopen(notif_url)

                            media_file = download_media(user_message)

                            if media_file and os.path.exists(media_file):
                                if media_file.endswith(('.mp4', '.mkv', '.webm', '.mov')):
                                    send_cmd = f"curl -s -F chat_id={chat_id} -F video=@\"{media_file}\" {telegram_url}/sendVideo"
                                else:
                                    send_cmd = f"curl -s -F chat_id={chat_id} -F photo=@\"{media_file}\" {telegram_url}/sendPhoto"
                                
                                subprocess.run(send_cmd, shell=True)
                                
                                try:
                                    os.remove(media_file)
                                except:
                                    pass
                            else:
                                err_url = f"{telegram_url}/sendMessage?chat_id={chat_id}&text={urllib.parse.quote('❌ عذراً، لم أتمكن من تحميل الملف. تأكد أن الرابط صحيح.')}"
                                urllib.request.urlopen(err_url)
                        else:
                            reply_text = "أهلاً بك! أرسل لي رابطاً فقط وسأقوم بتحميله لك فوراً."
                            send_url = f"{telegram_url}/sendMessage?chat_id={chat_id}&text={urllib.parse.quote(reply_text)}"
                            urllib.request.urlopen(send_url)

            time.sleep(2)

        except Exception as e:
            print(f"Telegram Bot Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    # تشغيل خادم الويب في خلفية الكود لكي تستجيب المنصة لرابط الـ Ping
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()

    # تشغيل حلقة استقبال رسائل البوت الأساسية
    telegram_bot_loop()
