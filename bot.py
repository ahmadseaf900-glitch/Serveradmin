import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests
import telebot
from telebot import types

from aternos import AternosManager


# =========================================================
# إعدادات
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID", "").strip()

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN غير موجود في Environment Variables.")

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN غير موجود في Environment Variables.")

if not DISCORD_CHANNEL_ID:
    raise RuntimeError(
        "DISCORD_CHANNEL_ID غير موجود في Environment Variables."
    )


bot = telebot.TeleBot(
    BOT_TOKEN,
    parse_mode="HTML"
)

aternos = AternosManager()


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


def send_to_discord(content):
    """إرسال رسالة إلى قناة Discord."""
    try:
        response = requests.post(
            DISCORD_URL,
            headers=DISCORD_HEADERS,
            json={"content": content},
            timeout=15,
        )

        if response.status_code not in (200, 201):
            return False, response.text

        return True, "OK"

    except requests.RequestException as exc:
        return False, str(exc)


def send_console(command):
    """إرسال أمر Minecraft Console إلى Discord."""
    command = command.strip().lstrip("/")

    if not command:
        return False, "الأمر فارغ."

    return send_to_discord(command)


# =========================================================
# القائمة
# =========================================================

def main_menu():
    """إنشاء القائمة الرئيسية للبوت."""

    markup = types.InlineKeyboardMarkup(row_width=2)

    markup.add(
        types.InlineKeyboardButton(
            "🟢 الحالة",
            callback_data="status"
        ),
        types.InlineKeyboardButton(
            "▶️ تشغيل",
            callback_data="start"
        ),
    )

    markup.add(
        types.InlineKeyboardButton(
            "⏹ إيقاف",
            callback_data="stop"
        ),
        types.InlineKeyboardButton(
            "🔄 Restart",
            callback_data="restart"
        ),
    )

    markup.add(
        types.InlineKeyboardButton(
            "🖥 Console",
            callback_data="console"
        ),
        types.InlineKeyboardButton(
            "📢 Say",
            callback_data="say"
        ),
    )

    markup.add(
        types.InlineKeyboardButton(
            "🟢 Whitelist",
            callback_data="whitelist"
        ),
        types.InlineKeyboardButton(
            "👑 Admin",
            callback_data="admin"
        ),
    )

    return markup


# =========================================================
# /start
# =========================================================

@bot.message_handler(commands=["start"])
def start_command(message):
    """عرض لوحة التحكم."""

    bot.send_message(
        message.chat.id,
        "🤖 <b>بوت إدارة سيرفر Minecraft</b>\n\n"
        "اختر العملية:",
        reply_markup=main_menu()
    )


# =========================================================
# /status
# =========================================================

@bot.message_handler(commands=["status"])
def status_command(message):
    """عرض حالة Aternos."""

    try:
        status = aternos.status()

        bot.reply_to(
            message,
            f"🟢 <b>حالة السيرفر:</b>\n<code>{status}</code>"
        )

    except Exception as exc:
        bot.reply_to(
            message,
            f"❌ فشل قراءة الحالة:\n<code>{exc}</code>"
        )


# =========================================================
# /startserver
# =========================================================

@bot.message_handler(commands=["startserver"])
def start_server_command(message):
    """تشغيل سيرفر Aternos."""

    try:
        result = aternos.start()

        bot.reply_to(
            message,
            f"▶️ <b>تم إرسال طلب التشغيل.</b>\n"
            f"<code>{result}</code>"
        )

    except Exception as exc:
        bot.reply_to(
            message,
            f"❌ فشل التشغيل:\n<code>{exc}</code>"
        )


# =========================================================
# /stopserver
# =========================================================

@bot.message_handler(commands=["stopserver"])
def stop_server_command(message):
    """إيقاف سيرفر Aternos."""

    try:
        result = aternos.stop()

        bot.reply_to(
            message,
            f"⏹️ <b>تم إرسال طلب الإيقاف.</b>\n"
            f"<code>{result}</code>"
        )

    except Exception as exc:
        bot.reply_to(
            message,
            f"❌ فشل الإيقاف:\n<code>{exc}</code>"
        )


# =========================================================
# /restart
# =========================================================

@bot.message_handler(commands=["restart"])
def restart_command(message):
    """إعادة تشغيل السيرفر."""

    try:
        result = aternos.restart()

        bot.reply_to(
            message,
            f"🔄 <b>تم إرسال Restart.</b>\n"
            f"<code>{result}</code>"
        )

    except Exception as exc:
        bot.reply_to(
            message,
            f"❌ فشل Restart:\n<code>{exc}</code>"
        )


# =========================================================
# /console
# =========================================================

@bot.message_handler(commands=["console"])
def console_command(message):
    """إرسال أمر Minecraft إلى Discord."""

    command = message.text.partition(" ")[2].strip()

    if not command:
        bot.reply_to(
            message,
            "مثال:\n<code>/console list</code>"
        )
        return

    success, detail = send_console(command)

    if success:
        bot.reply_to(
            message,
            "✅ تم إرسال الأمر إلى Discord."
        )
    else:
        bot.reply_to(
            message,
            f"❌ فشل:\n<code>{detail}</code>"
        )


# =========================================================
# /say
# =========================================================

@bot.message_handler(commands=["say"])
def say_command(message):
    """إرسال رسالة إلى اللاعبين."""

    text = message.text.partition(" ")[2].strip()

    if not text:
        bot.reply_to(
            message,
            "مثال:\n<code>/say أهلاً بالجميع!</code>"
        )
        return

    success, detail = send_console(
        f"say {text}"
    )

    if success:
        bot.reply_to(
            message,
            "📢 تم إرسال الرسالة."
        )
    else:
        bot.reply_to(
            message,
            f"❌ فشل:\n<code>{detail}</code>"
        )


# =========================================================
# /whitelist
# =========================================================

@bot.message_handler(commands=["whitelist"])
def whitelist_command(message):
    """إدارة Whitelist."""

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

    if action == "list":
        command = "whitelist list"

    elif action in {"add", "remove"} and len(args) == 2:
        player = args[1]

        if not player.replace("_", "").isalnum():
            bot.reply_to(
                message,
                "❌ اسم اللاعب غير صالح."
            )
            return

        command = f"whitelist {action} {player}"

    else:
        bot.reply_to(
            message,
            "❌ الصيغة غير صحيحة."
        )
        return

    success, detail = send_console(command)

    if success:
        bot.reply_to(
            message,
            "✅ تم إرسال أمر Whitelist."
        )
    else:
        bot.reply_to(
            message,
            f"❌ فشل:\n<code>{detail}</code>"
        )


# =========================================================
# الأزرار
# =========================================================

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    """معالجة أزرار لوحة التحكم."""

    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass

    chat_id = call.message.chat.id

    if call.data == "status":
        try:
            status = aternos.status()

            bot.send_message(
                chat_id,
                f"🟢 <b>الحالة:</b>\n<code>{status}</code>"
            )

        except Exception as exc:
            bot.send_message(
                chat_id,
                f"❌ <code>{exc}</code>"
            )

    elif call.data == "start":
        try:
            result = aternos.start()

            bot.send_message(
                chat_id,
                f"▶️ <b>تم إرسال طلب التشغيل.</b>\n"
                f"<code>{result}</code>"
            )

        except Exception as exc:
            bot.send_message(
                chat_id,
                f"❌ فشل التشغيل:\n<code>{exc}</code>"
            )

    elif call.data == "stop":
        try:
            result = aternos.stop()

            bot.send_message(
                chat_id,
                f"⏹️ <b>تم إرسال طلب الإيقاف.</b>\n"
                f"<code>{result}</code>"
            )

        except Exception as exc:
            bot.send_message(
                chat_id,
                f"❌ فشل الإيقاف:\n<code>{exc}</code>"
            )

    elif call.data == "restart":
        try:
            result = aternos.restart()

            bot.send_message(
                chat_id,
                f"🔄 <b>تم إرسال Restart.</b>\n"
                f"<code>{result}</code>"
            )

        except Exception as exc:
            bot.send_message(
                chat_id,
                f"❌ فشل Restart:\n<code>{exc}</code>"
            )

    elif call.data == "console":
        bot.send_message(
            chat_id,
            "🖥 استخدم:\n"
            "<code>/console list</code>"
        )

    elif call.data == "say":
        bot.send_message(
            chat_id,
            "📢 استخدم:\n"
            "<code>/say رسالتك</code>"
        )

    elif call.data == "whitelist":
        bot.send_message(
            chat_id,
            "<code>/whitelist add Player</code>\n"
            "<code>/whitelist remove Player</code>\n"
            "<code>/whitelist list</code>"
        )

    elif call.data == "admin":
        bot.send_message(
            chat_id,
            "👑 <b>أوامر الإدارة</b>\n\n"
            "<code>/console list</code>\n"
            "<code>/console op Player</code>\n"
            "<code>/console deop Player</code>\n"
            "<code>/console kick Player</code>\n"
            "<code>/console ban Player</code>\n"
            "<code>/console tp Player Player2</code>\n"
            "<code>/console gamemode creative Player</code>\n"
            "<code>/console give Player item 1</code>\n"
            "<code>/console save-all</code>"
        )


# =========================================================
# رسائل غير معروفة
# =========================================================

@bot.message_handler(func=lambda message: True)
def unknown_message(message):
    """معالجة الرسائل غير المعروفة."""

    bot.send_message(
        message.chat.id,
        "استخدم /start لفتح لوحة التحكم.",
        reply_markup=main_menu()
    )


# =========================================================
# Web Server لـ Render
# =========================================================

class HealthHandler(BaseHTTPRequestHandler):
    """صفحة Health بسيطة حتى يظل Web Service صالحًا."""

    def do_GET(self):
        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8"
        )
        self.end_headers()

        self.wfile.write(
            b"Telegram Minecraft Server Bot is running."
        )

    def log_message(self, format, *args):
        return


def start_web_server():
    """تشغيل HTTP server على PORT الخاص بـ Render."""

    port = int(
        os.getenv("PORT", "10000")
    )

    server = HTTPServer(
        ("0.0.0.0", port),
        HealthHandler
    )

    print(
        f"🌐 Health server running on port {port}",
        flush=True
    )

    server.serve_forever()


# =========================================================
# تشغيل
# =========================================================

def main():
    """تشغيل Health Server وTelegram polling."""

    threading.Thread(
        target=start_web_server,
        daemon=True
    ).start()

    print(
        "🤖 Telegram bot starting...",
        flush=True
    )

    try:
        bot.remove_webhook()
    except Exception as exc:
        print(
            f"Webhook warning: {exc}",
            flush=True
        )

    bot.infinity_polling(
        skip_pending=True,
        timeout=60,
        long_polling_timeout=60
    )


if __name__ == "__main__":
    main()
