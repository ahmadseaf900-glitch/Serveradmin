import os
import time
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import telebot
from telebot import types

import aternos


# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

PORT = int(os.getenv("PORT", "10000"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN غير موجود")


# ============================================================
# TELEGRAM
# ============================================================

bot = telebot.TeleBot(
    BOT_TOKEN,
    parse_mode="HTML",
    threaded=True
)


# ============================================================
# HELPERS
# ============================================================

def get_server_object():
    return aternos.get_server()


def get_server_name(server):
    for attr in ("name", "server_name"):
        try:
            value = getattr(server, attr)
            if value:
                return str(value)
        except Exception:
            pass

    return "Aternos Server"


def get_server_address(server):
    for attr in ("address", "ip", "host"):
        try:
            value = getattr(server, attr)
            if value:
                return str(value)
        except Exception:
            pass

    return os.getenv(
        "MC_SERVER_HOST",
        "MACESMP37.aternos.me"
    )


def get_server_status_text(server):
    try:
        value = getattr(server, "status", None)

        if callable(value):
            value = value()

        return str(value)

    except Exception:
        return "غير معروف"


def keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)

    markup.add(
        types.InlineKeyboardButton(
            "▶️ Start",
            callback_data="aternos_start"
        ),
        types.InlineKeyboardButton(
            "⏹️ Stop",
            callback_data="aternos_stop"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "🔄 Restart",
            callback_data="aternos_restart"
        ),
        types.InlineKeyboardButton(
            "📊 Status",
            callback_data="server_status"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "🖥️ Console",
            callback_data="console"
        ),
        types.InlineKeyboardButton(
            "👥 Players",
            callback_data="players"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "📝 Whitelist",
            callback_data="whitelist"
        )
    )

    return markup


# ============================================================
# START
# ============================================================

@bot.message_handler(commands=["start"])
def start_command(message):

    try:
        server = get_server_object()

        name = get_server_name(server)
        address = get_server_address(server)
        status = get_server_status_text(server)

        text = (
            "🤖 <b>بوت إدارة سيرفر Minecraft</b>\n\n"
            f"🖥️ السيرفر: <b>{name}</b>\n"
            f"🌐 العنوان: <code>{address}</code>\n"
            f"📊 الحالة: <b>{status}</b>\n\n"
            "اختر العملية:"
        )

        bot.send_message(
            message.chat.id,
            text,
            reply_markup=keyboard()
        )

    except Exception as exc:
        bot.send_message(
            message.chat.id,
            "❌ فشل الاتصال بحساب Aternos:\n\n"
            f"<code>{str(exc)[:1000]}</code>"
        )


# ============================================================
# STATUS
# ============================================================

def send_status(chat_id):

    try:
        server = get_server_object()

        name = get_server_name(server)
        address = get_server_address(server)
        status = get_server_status_text(server)

        bot.send_message(
            chat_id,
            "📊 <b>حالة السيرفر</b>\n\n"
            f"🖥️ {name}\n"
            f"🌐 <code>{address}</code>\n"
            f"📡 الحالة: <b>{status}</b>",
            reply_markup=keyboard()
        )

    except Exception as exc:
        bot.send_message(
            chat_id,
            "❌ فشل جلب الحالة:\n"
            f"<code>{str(exc)[:1000]}</code>"
        )


# ============================================================
# CALLBACK
# ============================================================

@bot.callback_query_handler(
    func=lambda call: True
)
def callback_handler(call):

    chat_id = call.message.chat.id

    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    if call.data == "server_status":

        send_status(chat_id)
        return

    # --------------------------------------------------------
    # START
    # --------------------------------------------------------

    if call.data == "aternos_start":

        try:
            bot.send_message(
                chat_id,
                "▶️ <b>جاري تشغيل السيرفر...</b>"
            )

            aternos.start()

            bot.send_message(
                chat_id,
                "✅ <b>تم إرسال أمر Start إلى Aternos.</b>\n\n"
                "🔎 اضغط Status للتحقق من الحالة.",
                reply_markup=keyboard()
            )

        except Exception as exc:

            bot.send_message(
                chat_id,
                "❌ <b>فشل تشغيل السيرفر</b>\n\n"
                f"<code>{str(exc)[:1000]}</code>",
                reply_markup=keyboard()
            )

        return

    # --------------------------------------------------------
    # STOP
    # --------------------------------------------------------

    if call.data == "aternos_stop":

        try:
            bot.send_message(
                chat_id,
                "⏹️ <b>جاري إيقاف السيرفر...</b>"
            )

            aternos.stop()

            bot.send_message(
                chat_id,
                "✅ <b>تم إرسال أمر Stop إلى Aternos.</b>\n\n"
                "🔎 اضغط Status للتحقق.",
                reply_markup=keyboard()
            )

        except Exception as exc:

            bot.send_message(
                chat_id,
                "❌ <b>فشل إيقاف السيرفر</b>\n\n"
                f"<code>{str(exc)[:1000]}</code>",
                reply_markup=keyboard()
            )

        return

    # --------------------------------------------------------
    # RESTART
    # --------------------------------------------------------

    if call.data == "aternos_restart":

        try:
            bot.send_message(
                chat_id,
                "🔄 <b>جاري إعادة تشغيل السيرفر...</b>"
            )

            aternos.restart()

            bot.send_message(
                chat_id,
                "✅ <b>تم إرسال أمر Restart إلى Aternos.</b>\n\n"
                "🔎 اضغط Status للتحقق.",
                reply_markup=keyboard()
            )

        except Exception as exc:

            bot.send_message(
                chat_id,
                "❌ <b>فشل Restart</b>\n\n"
                f"<code>{str(exc)[:1000]}</code>",
                reply_markup=keyboard()
            )

        return

    # --------------------------------------------------------
    # CONSOLE
    # --------------------------------------------------------

    if call.data == "console":

        bot.send_message(
            chat_id,
            "🖥️ <b>Console</b>\n\n"
            "نظام الـ Console مربوط من خلال DiscordSRV/بوت Discord.\n"
            "أرسل الأمر عبر نظام Discord المرتبط بالسيرفر."
        )

        return

    # --------------------------------------------------------
    # PLAYERS
    # --------------------------------------------------------

    if call.data == "players":

        try:
            server = get_server_object()

            players = getattr(
                server,
                "players",
                None
            )

            if callable(players):
                players = players()

            if players:
                bot.send_message(
                    chat_id,
                    "👥 <b>اللاعبون</b>\n\n"
                    f"<code>{str(players)[:3000]}</code>",
                    reply_markup=keyboard()
                )
            else:
                bot.send_message(
                    chat_id,
                    "👥 لا توجد بيانات لاعبين متاحة حاليًا.",
                    reply_markup=keyboard()
                )

        except Exception as exc:

            bot.send_message(
                chat_id,
                "❌ فشل جلب اللاعبين:\n"
                f"<code>{str(exc)[:1000]}</code>"
            )

        return

    # --------------------------------------------------------
    # WHITELIST
    # --------------------------------------------------------

    if call.data == "whitelist":

        bot.send_message(
            chat_id,
            "📝 <b>Whitelist</b>\n\n"
            "أرسل أمر whitelist عبر نظام DiscordSRV المرتبط بالسيرفر.\n\n"
            "مثال:\n"
            "<code>/whitelist add PlayerName</code>"
        )

        return


# ============================================================
# COMMANDS
# ============================================================

@bot.message_handler(commands=["status"])
def status_command(message):

    send_status(message.chat.id)


@bot.message_handler(commands=["start_server"])
def start_server_command(message):

    try:
        aternos.start()

        bot.send_message(
            message.chat.id,
            "✅ تم إرسال Start إلى Aternos.",
            reply_markup=keyboard()
        )

    except Exception as exc:

        bot.send_message(
            message.chat.id,
            "❌ فشل Start:\n"
            f"<code>{str(exc)[:1000]}</code>"
        )


@bot.message_handler(commands=["stop_server"])
def stop_server_command(message):

    try:
        aternos.stop()

        bot.send_message(
            message.chat.id,
            "✅ تم إرسال Stop إلى Aternos.",
            reply_markup=keyboard()
        )

    except Exception as exc:

        bot.send_message(
            message.chat.id,
            "❌ فشل Stop:\n"
            f"<code>{str(exc)[:1000]}</code>"
        )


@bot.message_handler(commands=["restart"])
def restart_command(message):

    try:
        aternos.restart()

        bot.send_message(
            message.chat.id,
            "✅ تم إرسال Restart إلى Aternos.",
            reply_markup=keyboard()
        )

    except Exception as exc:

        bot.send_message(
            message.chat.id,
            "❌ فشل Restart:\n"
            f"<code>{str(exc)[:1000]}</code>"
        )


# ============================================================
# HELP
# ============================================================

@bot.message_handler(commands=["help"])
def help_command(message):

    bot.send_message(
        message.chat.id,
        "📚 <b>أوامر البوت</b>\n\n"
        "/start — لوحة التحكم\n"
        "/status — حالة السيرفر\n"
        "/start_server — تشغيل\n"
        "/stop_server — إيقاف\n"
        "/restart — إعادة تشغيل\n\n"
        "الأزرار تشمل:\n"
        "▶️ Start\n"
        "⏹️ Stop\n"
        "🔄 Restart\n"
        "📊 Status\n"
        "🖥️ Console\n"
        "👥 Players\n"
        "📝 Whitelist"
    )


# ============================================================
# RENDER HEALTH
# ============================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        self.send_response(200)

        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8"
        )

        self.end_headers()

        self.wfile.write(
            b"Telegram Minecraft Bot is running."
        )

    def log_message(self, format, *args):
        return


def run_health_server():

    server = ThreadingHTTPServer(
        ("0.0.0.0", PORT),
        HealthHandler
    )

    print(
        f"Health server listening on {PORT}"
    )

    server.serve_forever()


# ============================================================
# TELEGRAM POLLING
# ============================================================

def run_bot():

    while True:

        try:

            print("Telegram bot started.")

            bot.infinity_polling(
                timeout=30,
                long_polling_timeout=30,
                skip_pending=True
            )

        except Exception as exc:

            print(
                f"Telegram error: {exc}"
            )

            time.sleep(5)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    health_thread = threading.Thread(
        target=run_health_server,
        daemon=True
    )

    health_thread.start()

    run_bot()
