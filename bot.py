import os
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests
import telebot
from telebot import types


# =========================================================
# الإعدادات
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN غير موجود")

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN غير موجود")

if not DISCORD_CHANNEL_ID:
    raise RuntimeError("DISCORD_CHANNEL_ID غير موجود")


bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")


# =========================================================
# الأدمن
# =========================================================

ADMIN_IDS = {
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}


# =========================================================
# أوامر مسموحة
# =========================================================

CONSOLE_WHITELIST = {
    x.strip().lower().lstrip("/")
    for x in os.getenv(
        "CONSOLE_WHITELIST",
        "say,whitelist,list,online,save-all"
    ).split(",")
    if x.strip()
}


# =========================================================
# Discord
# =========================================================

DISCORD_URL = (
    f"https://discord.com/api/v10/channels/"
    f"{DISCORD_CHANNEL_ID}/messages"
)

DISCORD_HEADERS = {
    "Authorization": f"Bot {DISCORD_TOKEN}",
    "Content-Type": "application/json",
}


def is_admin(message):
    return message.from_user.id in ADMIN_IDS


def admin_only(message):
    if not is_admin(message):
        bot.reply_to(
            message,
            "⛔ <b>ليس لديك صلاحية Admin.</b>"
        )
        return False

    return True


def send_to_discord(text):
    try:

        response = requests.post(
            DISCORD_URL,
            headers=DISCORD_HEADERS,
            json={
                "content": text
            },
            timeout=15
        )

        if response.status_code not in (200, 201):

            print(
                "Discord Error:",
                response.status_code,
                response.text[:500]
            )

            return False

        return True

    except Exception as e:

        print("Discord connection error:", e)

        return False


# =========================================================
# إرسال أمر إلى DiscordSRV
# =========================================================

def send_console(command):

    command = command.strip().lstrip("/")

    return send_to_discord(
        "!c " + command
    )


# =========================================================
# التحقق من Whitelist
# =========================================================

def command_allowed(command):

    command = command.strip().lstrip("/")

    if not command:
        return False

    first = command.split()[0].lower()

    return first in CONSOLE_WHITELIST


# =========================================================
# Web Server لـ Render
# =========================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        self.send_response(200)

        self.send_header(
            "Content-type",
            "text/plain"
        )

        self.end_headers()

        self.wfile.write(
            b"Telegram Discord Bridge is running!"
        )

    def log_message(self, format, *args):
        return


def start_web_server():

    port = int(
        os.environ.get(
            "PORT",
            "10000"
        )
    )

    server = HTTPServer(
        ("0.0.0.0", port),
        HealthHandler
    )

    print(
        f"🌐 Web server running on port {port}"
    )

    server.serve_forever()


threading.Thread(
    target=start_web_server,
    daemon=True
).start()


# =========================================================
# القائمة الرئيسية
# =========================================================

def main_menu():

    markup = types.InlineKeyboardMarkup(
        row_width=2
    )

    markup.add(

        types.InlineKeyboardButton(
            "🖥 Console",
            callback_data="console"
        ),

        types.InlineKeyboardButton(
            "📢 Say",
            callback_data="say"
        )

    )

    markup.add(

        types.InlineKeyboardButton(
            "🟢 Whitelist",
            callback_data="whitelist"
        )

    )

    return markup


# =========================================================
# /start
# =========================================================

@bot.message_handler(
    commands=["start"]
)
def start_command(message):

    if not is_admin(message):

        bot.send_message(
            message.chat.id,
            "⛔ غير مصرح لك باستخدام البوت."
        )

        return

    bot.send_message(

        message.chat.id,

        "🤖 <b>Telegram → Discord → DiscordSRV</b>\n\n"
        "🟢 <b>البوت يعمل بنجاح!</b>\n\n"
        "🎮 اختر العملية:",

        reply_markup=main_menu()

    )


# =========================================================
# /console
# =========================================================

@bot.message_handler(
    commands=["console"]
)
def console_command(message):

    if not admin_only(message):
        return

    command = message.text.partition(" ")[2].strip()

    if not command:

        bot.reply_to(
            message,
            "مثال:\n"
            "<code>/console list</code>"
        )

        return

    if not command_allowed(command):

        bot.reply_to(
            message,
            "⛔ هذا الأمر غير موجود في Console Whitelist."
        )

        return

    if send_console(command):

        bot.reply_to(
            message,
            "✅ <b>تم إرسال الأمر إلى Discord.</b>\n\n"
            f"🎮 <code>{command}</code>"
        )

    else:

        bot.reply_to(
            message,
            "❌ فشل إرسال الأمر إلى Discord."
        )


# =========================================================
# /say
# =========================================================

@bot.message_handler(
    commands=["say"]
)
def say_command(message):

    if not admin_only(message):
        return

    text = message.text.partition(" ")[2].strip()

    if not text:

        bot.reply_to(
            message,
            "مثال:\n"
            "<code>/say أهلاً باللاعبين!</code>"
        )

        return

    if "say" not in CONSOLE_WHITELIST:

        bot.reply_to(
            message,
            "⛔ أمر say غير مسموح."
        )

        return

    if send_console(
        "say " + text
    ):

        bot.reply_to(
            message,
            "📢 <b>تم إرسال الرسالة إلى DiscordSRV.</b>"
        )

    else:

        bot.reply_to(
            message,
            "❌ فشل إرسال الرسالة."
        )


# =========================================================
# /whitelist
# =========================================================

@bot.message_handler(
    commands=["whitelist"]
)
def whitelist_command(message):

    if not admin_only(message):
        return

    args = (
        message.text
        .partition(" ")[2]
        .strip()
        .split()
    )

    if not args:

        bot.reply_to(
            message,
            "<code>/whitelist add Player</code>\n"
            "<code>/whitelist remove Player</code>\n"
            "<code>/whitelist list</code>"
        )

        return

    action = args[0].lower()

    if action not in {
        "add",
        "remove",
        "list"
    }:

        bot.reply_to(
            message,
            "❌ استخدم add أو remove أو list."
        )

        return

    if action == "list":

        command = "whitelist list"

    else:

        if len(args) != 2:

            bot.reply_to(
                message,
                "مثال:\n"
                "<code>/whitelist add Player</code>"
            )

            return

        player = args[1]

        if not re.fullmatch(
            r"[A-Za-z0-9_]{1,16}",
            player
        ):

            bot.reply_to(
                message,
                "❌ اسم اللاعب غير صالح."
            )

            return

        command = (
            f"whitelist {action} {player}"
        )

    if not command_allowed(command):

        bot.reply_to(
            message,
            "⛔ أمر whitelist غير مسموح."
        )

        return

    if send_console(command):

        bot.reply_to(
            message,
            "✅ <b>تم إرسال أمر Whitelist إلى Discord.</b>"
        )

    else:

        bot.reply_to(
            message,
            "❌ فشل إرسال الأمر."
        )


# =========================================================
# الأزرار
# =========================================================

@bot.callback_query_handler(
    func=lambda call: True
)
def callback_handler(call):

    if call.from_user.id not in ADMIN_IDS:

        bot.answer_callback_query(
            call.id,
            "⛔ غير مصرح",
            show_alert=True
        )

        return

    bot.answer_callback_query(
        call.id
    )

    chat_id = call.message.chat.id

    if call.data == "console":

        bot.send_message(
            chat_id,
            "🖥 <b>Console</b>\n\n"
            "أرسل:\n"
            "<code>/console list</code>"
        )

    elif call.data == "say":

        bot.send_message(
            chat_id,
            "📢 أرسل:\n"
            "<code>/say رسالتك</code>"
        )

    elif call.data == "whitelist":

        bot.send_message(
            chat_id,
            "🟢 <b>Whitelist</b>\n\n"
            "<code>/whitelist add Player</code>\n"
            "<code>/whitelist remove Player</code>\n"
            "<code>/whitelist list</code>"
        )


# =========================================================
# الرسائل غير المعروفة
# =========================================================

@bot.message_handler(
    func=lambda message: True
)
def unknown_message(message):

    if is_admin(message):

        bot.send_message(
            message.chat.id,
            "استخدم /start لعرض القائمة.",
            reply_markup=main_menu()
        )

    else:

        bot.reply_to(
            message,
            "⛔ غير مصرح لك باستخدام هذا البوت."
        )


# =========================================================
# تشغيل البوت
# =========================================================

if __name__ == "__main__":

    print(
        "🤖 Telegram Bot Started"
    )

    try:

        bot.remove_webhook()

        print(
            "✅ Webhook removed"
        )

    except Exception as e:

        print(
            "⚠️ Webhook removal:",
            e
        )

    print(
        "🚀 Starting Telegram polling..."
    )

    while True:

        try:

            bot.infinity_polling(
                skip_pending=True,
                timeout=60,
                long_polling_timeout=60
            )

        except Exception as e:

            print(
                "❌ Polling error:",
                e
            )

            time.sleep(10)
