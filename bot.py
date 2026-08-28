import os
import time
import threading
import requests
import telebot
from telebot import types

# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()

DISCORD_CHANNEL_ID = os.getenv(
    "DISCORD_CHANNEL_ID",
    ""
).strip()

MC_SERVER_HOST = os.getenv(
    "MC_SERVER_HOST",
    "MACESMP37.aternos.me"
).strip()

MC_SERVER_PORT = int(
    os.getenv("MC_SERVER_PORT", "25565")
)

# =========================================================
# CHECK TOKEN
# =========================================================

if not BOT_TOKEN:
    raise RuntimeError(
        "❌ BOT_TOKEN غير موجود في Environment Variables"
    )

# =========================================================
# BOT
# =========================================================

bot = telebot.TeleBot(
    BOT_TOKEN,
    parse_mode="HTML",
    threaded=True
)

# =========================================================
# START
# =========================================================

@bot.message_handler(commands=["start"])
def start(message):

    keyboard = types.InlineKeyboardMarkup(row_width=2)

    keyboard.add(
        types.InlineKeyboardButton(
            "🎮 حالة السيرفر",
            callback_data="server_status"
        ),
        types.InlineKeyboardButton(
            "🌐 IP السيرفر",
            callback_data="server_ip"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "📋 المساعدة",
            callback_data="help"
        ),
        types.InlineKeyboardButton(
            "🧪 Discord Test",
            callback_data="discord_test"
        )
    )

    text = (
        "🤖 <b>أهلاً بك في Server Admin</b>\n\n"
        "🎮 إدارة سيرفر Minecraft\n"
        "📡 فحص حالة السيرفر\n"
        "💬 ربط Discord\n\n"
        "اختر من الأزرار بالأسفل:"
    )

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=keyboard
    )


# =========================================================
# HELP
# =========================================================

@bot.message_handler(commands=["help"])
def help_command(message):

    text = (
        "📋 <b>أوامر البوت</b>\n\n"
        "/start - القائمة الرئيسية\n"
        "/server - حالة السيرفر\n"
        "/ip - عنوان السيرفر\n"
        "/help - المساعدة\n"
        "/discord_test - اختبار Discord\n"
    )

    bot.send_message(
        message.chat.id,
        text
    )


# =========================================================
# SERVER STATUS
# =========================================================

def get_server_status():

    try:

        from mcstatus import JavaServer

        server = JavaServer.lookup(
            f"{MC_SERVER_HOST}:{MC_SERVER_PORT}"
        )

        status = server.status()

        players_online = status.players.online
        players_max = status.players.max

        return (
            True,
            players_online,
            players_max
        )

    except Exception:

        return (
            False,
            0,
            0
        )


# =========================================================
# /server
# =========================================================

@bot.message_handler(commands=["server"])
def server_command(message):

    msg = bot.send_message(
        message.chat.id,
        "🔄 <b>جاري فحص السيرفر...</b>"
    )

    online, players, maximum = get_server_status()

    if online:

        text = (
            "🟢 <b>السيرفر أونلاين</b>\n\n"
            f"🌐 <b>IP:</b> <code>{MC_SERVER_HOST}</code>\n"
            f"👥 اللاعبين: <b>{players}/{maximum}</b>\n"
        )

    else:

        text = (
            "🔴 <b>السيرفر أوفلاين</b>\n\n"
            f"🌐 <b>IP:</b> <code>{MC_SERVER_HOST}</code>"
        )

    try:

        bot.edit_message_text(
            text,
            message.chat.id,
            msg.message_id
        )

    except Exception:

        bot.send_message(
            message.chat.id,
            text
        )


# =========================================================
# /ip
# =========================================================

@bot.message_handler(commands=["ip"])
def ip_command(message):

    bot.send_message(
        message.chat.id,
        (
            "🌐 <b>IP السيرفر</b>\n\n"
            f"<code>{MC_SERVER_HOST}</code>\n\n"
            "📌 انسخه وأضفه داخل Minecraft."
        )
    )


# =========================================================
# DISCORD TEST
# =========================================================

def discord_test():

    if not DISCORD_TOKEN:

        return (
            False,
            "❌ DISCORD_TOKEN غير موجود."
        )

    headers = {
        "Authorization": f"Bot {DISCORD_TOKEN}"
    }

    try:

        response = requests.get(
            "https://discord.com/api/v10/users/@me",
            headers=headers,
            timeout=15
        )

        if response.status_code == 200:

            data = response.json()

            username = data.get(
                "username",
                "Unknown"
            )

            return (
                True,
                f"✅ Discord يعمل\n\n"
                f"🤖 Bot: <b>{username}</b>\n"
                f"🌐 HTTP: <code>200</code>"
            )

        return (
            False,
            f"❌ Discord Error\n\n"
            f"HTTP: {response.status_code}\n"
            f"{response.text[:500]}"
        )

    except Exception as e:

        return (
            False,
            f"❌ خطأ Discord:\n<code>{e}</code>"
        )


# =========================================================
# /discord_test
# =========================================================

@bot.message_handler(commands=["discord_test"])
def discord_test_command(message):

    bot.send_message(
        message.chat.id,
        "🧪 <b>جاري اختبار Discord...</b>"
    )

    success, text = discord_test()

    bot.send_message(
        message.chat.id,
        text
    )


# =========================================================
# CALLBACKS
# =========================================================

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):

    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass

    chat_id = call.message.chat.id

    # -------------------------
    # SERVER STATUS
    # -------------------------

    if call.data == "server_status":

        online, players, maximum = get_server_status()

        if online:

            text = (
                "🟢 <b>السيرفر أونلاين</b>\n\n"
                f"🌐 <code>{MC_SERVER_HOST}</code>\n"
                f"👥 اللاعبين: <b>{players}/{maximum}</b>"
            )

        else:

            text = (
                "🔴 <b>السيرفر أوفلاين</b>\n\n"
                f"🌐 <code>{MC_SERVER_HOST}</code>"
            )

        bot.send_message(
            chat_id,
            text
        )

    # -------------------------
    # IP
    # -------------------------

    elif call.data == "server_ip":

        bot.send_message(
            chat_id,
            (
                "🌐 <b>IP السيرفر:</b>\n\n"
                f"<code>{MC_SERVER_HOST}</code>"
            )
        )

    # -------------------------
    # HELP
    # -------------------------

    elif call.data == "help":

        help_text = (
            "📋 <b>المساعدة</b>\n\n"
            "/start\n"
            "/server\n"
            "/ip\n"
            "/help\n"
            "/discord_test"
        )

        bot.send_message(
            chat_id,
            help_text
        )

    # -------------------------
    # DISCORD
    # -------------------------

    elif call.data == "discord_test":

        bot.send_message(
            chat_id,
            "🧪 <b>جاري اختبار Discord...</b>"
        )

        success, text = discord_test()

        bot.send_message(
            chat_id,
            text
        )


# =========================================================
# UNKNOWN TEXT
# =========================================================

@bot.message_handler(
    func=lambda message: True,
    content_types=["text"]
)
def text_handler(message):

    text = message.text.strip().lower()

    if text in ["سيرفر", "السيرفر", "حالة السيرفر"]:

        server_command(message)

    elif text in ["اي بي", "ip", "الاى بي"]:

        ip_command(message)

    else:

        bot.send_message(
            message.chat.id,
            (
                "🤖 ما فهمت الأمر.\n\n"
                "استخدم /start لعرض القائمة."
            )
        )


# =========================================================
# WEB SERVER FOR RENDER
# =========================================================

from http.server import BaseHTTPRequestHandler, HTTPServer


class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8"
        )
        self.end_headers()

        self.wfile.write(
            b"Server Admin Bot is running."
        )

    def log_message(self, format, *args):
        pass


def run_web_server():

    port = int(
        os.getenv("PORT", "10000")
    )

    server = HTTPServer(
        ("0.0.0.0", port),
        HealthHandler
    )

    print(
        f"🌐 Web server running on port {port}"
    )

    server.serve_forever()


# =========================================================
# MAIN
# =========================================================

def main():

    print("===============================")
    print("SERVER ADMIN BOT")
    print("===============================")

    print(
        "BOT_TOKEN exists:",
        bool(BOT_TOKEN)
    )

    print(
        "DISCORD_TOKEN exists:",
        bool(DISCORD_TOKEN)
    )

    print(
        "DISCORD_CHANNEL_ID:",
        DISCORD_CHANNEL_ID
    )

    print(
        "Minecraft:",
        f"{MC_SERVER_HOST}:{MC_SERVER_PORT}"
    )

    # تشغيل Web Server
    web_thread = threading.Thread(
        target=run_web_server,
        daemon=True
    )

    web_thread.start()

    # حذف Webhook القديم
    try:

        bot.remove_webhook()

        time.sleep(1)

    except Exception as e:

        print(
            "Webhook cleanup error:",
            e
        )

    print("Telegram bot started.")

    # Polling
    while True:

        try:

            bot.infinity_polling(
                skip_pending=True,
                timeout=30,
                long_polling_timeout=30
            )

        except Exception as e:

            print(
                "Telegram polling error:",
                e
            )

            time.sleep(5)


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    main()
