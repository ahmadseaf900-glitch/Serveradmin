import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import telebot
from telebot import types
from mcstatus import JavaServer


# =========================
# إعدادات البوت
# =========================

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN is not set")

bot = telebot.TeleBot(TOKEN)

SERVER_HOST = "MACESMP37.aternos.me"
SERVER_PORT = 44114

WEB_PORT = int(os.getenv("PORT", "10000"))


# =========================
# Web Server لـ Render
# =========================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Telegram Bot is running!")

    def log_message(self, format, *args):
        return


def start_web_server():
    server = HTTPServer(("0.0.0.0", WEB_PORT), HealthHandler)
    print(f"🌐 Web server running on port {WEB_PORT}")
    server.serve_forever()


# =========================
# لوحة التحكم
# =========================

def main_keyboard():

    keyboard = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    keyboard.row(
        "🟢 Start",
        "🔴 Stop"
    )

    keyboard.row(
        "🔄 Restart",
        "📊 Status"
    )

    keyboard.row(
        "👥 Players"
    )

    return keyboard


# =========================
# فحص السيرفر
# =========================

def get_server_status():

    try:

        server = JavaServer.lookup(
            f"{SERVER_HOST}:{SERVER_PORT}"
        )

        status = server.status()

        online = status.players.online
        maximum = status.players.max

        return (
            True,
            online,
            maximum,
            status.version.name
        )

    except Exception as e:

        print("Status error:", e)

        return False, 0, 0, None


# =========================
# /start
# =========================

@bot.message_handler(commands=["start"])
def start(message):

    text = (
        "🤖 البوت يعمل بنجاح!\n\n"
        "أهلاً بك 👋\n\n"
        "🎮 لوحة تحكم سيرفر MACE SMP"
    )

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=main_keyboard()
    )


# =========================
# Status
# =========================

@bot.message_handler(
    func=lambda message: message.text == "📊 Status"
)
def status(message):

    bot.send_message(
        message.chat.id,
        "🔎 جاري فحص السيرفر..."
    )

    online, players, maximum, version = get_server_status()

    if online:

        text = (
            "🟢 السيرفر Online\n\n"
            f"🌐 {SERVER_HOST}:{SERVER_PORT}\n"
            f"👥 اللاعبين: {players}/{maximum}\n"
            f"🎮 الإصدار: {version}"
        )

    else:

        text = (
            "🔴 السيرفر Offline\n\n"
            f"🌐 {SERVER_HOST}:{SERVER_PORT}"
        )

    bot.send_message(
        message.chat.id,
        text
    )


# =========================
# Players
# =========================

@bot.message_handler(
    func=lambda message: message.text == "👥 Players"
)
def players(message):

    try:

        server = JavaServer.lookup(
            f"{SERVER_HOST}:{SERVER_PORT}"
        )

        status = server.status()

        online = status.players.online
        maximum = status.players.max

        text = (
            "👥 اللاعبين\n\n"
            f"🟢 المتصلون: {online}/{maximum}"
        )

        bot.send_message(
            message.chat.id,
            text
        )

    except Exception:

        bot.send_message(
            message.chat.id,
            "🔴 السيرفر Offline أو لا يمكن الوصول إليه."
        )


# =========================
# Start / Stop / Restart
# =========================

@bot.message_handler(
    func=lambda message: message.text in [
        "🟢 Start",
        "🔴 Stop",
        "🔄 Restart"
    ]
)
def server_controls(message):

    if message.text == "🟢 Start":

        bot.send_message(
            message.chat.id,
            "⚠️ تشغيل السيرفر من Aternos يحتاج ربطًا مع لوحة Aternos.\n\n"
            "حالياً زر Start غير منفذ."
        )

    elif message.text == "🔴 Stop":

        bot.send_message(
            message.chat.id,
            "⚠️ إيقاف السيرفر من Aternos يحتاج ربطًا مع لوحة Aternos.\n\n"
            "حالياً زر Stop غير منفذ."
        )

    elif message.text == "🔄 Restart":

        bot.send_message(
            message.chat.id,
            "⚠️ إعادة التشغيل من Aternos تحتاج ربطًا مع لوحة Aternos.\n\n"
            "حالياً زر Restart غير منفذ."
        )


# =========================
# تشغيل البوت
# =========================

if __name__ == "__main__":

    web_thread = threading.Thread(
        target=start_web_server,
        daemon=True
    )

    web_thread.start()

    print("🤖 Telegram Bot Started")

    bot.infinity_polling(
        skip_pending=True,
        timeout=60,
        long_polling_timeout=60
    )
