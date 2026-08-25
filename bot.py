import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import telebot


TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN is not set")

bot = telebot.TeleBot(TOKEN)


# صفحة بسيطة حتى Render يعتبر الخدمة شغالة
class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is running!")

    def log_message(self, format, *args):
        pass


def run_web_server():
    port = int(os.getenv("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)

    print(f"🌐 Web server running on port {port}")

    server.serve_forever()


# تشغيل Web Server في Thread منفصل
threading.Thread(
    target=run_web_server,
    daemon=True
).start()


# أمر /start
@bot.message_handler(commands=["start"])
def start(message):

    bot.send_message(
        message.chat.id,
        "🤖 البوت يعمل بنجاح!\n\n"
        "أهلاً بك 👋"
    )


# أمر /help
@bot.message_handler(commands=["help"])
def help_command(message):

    bot.send_message(
        message.chat.id,
        "📚 الأوامر:\n\n"
        "/start - تشغيل البوت\n"
        "/help - المساعدة"
    )


print("🤖 Telegram Bot Started")

bot.infinity_polling(
    skip_pending=True,
    timeout=60,
    long_polling_timeout=60
)
