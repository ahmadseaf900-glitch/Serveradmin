import os
import time
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import telebot
from telebot import types

from aternos import AternosManager


# ============================================================
# Configuration
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN غير موجود في Environment Variables")

bot = telebot.TeleBot(
    BOT_TOKEN,
    parse_mode="HTML",
    threaded=True,
)

aternos = AternosManager()


# ============================================================
# Simple health server for Render
# ============================================================

class HealthHandler(BaseHTTPRequestHandler):
    """HTTP endpoint used by Render to verify that the service is alive."""

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"ServerAdmin Telegram Bot is running!")

    def log_message(self, format, *args):
        return


def start_health_server():
    """Start the HTTP health server in a background thread."""

    port = int(os.getenv("PORT", "10000"))

    server = ThreadingHTTPServer(
        ("0.0.0.0", port),
        HealthHandler,
    )

    print(f"🌐 Health server listening on port {port}", flush=True)

    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )

    thread.start()


# ============================================================
# Main menu
# ============================================================

def main_menu():
    """Create the Telegram inline keyboard."""

    keyboard = types.InlineKeyboardMarkup(row_width=2)

    keyboard.add(
        types.InlineKeyboardButton(
            "🟢 الحالة",
            callback_data="status",
        ),
        types.InlineKeyboardButton(
            "▶️ تشغيل",
            callback_data="start",
        ),
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "⏹️ إيقاف",
            callback_data="stop",
        ),
        types.InlineKeyboardButton(
            "🔄 Restart",
            callback_data="restart",
        ),
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "👥 اللاعبين",
            callback_data="players",
        ),
        types.InlineKeyboardButton(
            "ℹ️ معلومات",
            callback_data="info",
        ),
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "🖥️ Console",
            callback_data="console",
        )
    )

    return keyboard


# ============================================================
# /start
# ============================================================

@bot.message_handler(commands=["start"])
def start_command(message):
    """Display the main control panel."""

    bot.send_message(
        message.chat.id,
        (
            "🤖 <b>بوت إدارة سيرفر Minecraft</b>\n\n"
            "اختر العملية التي تريد تنفيذها:"
        ),
        reply_markup=main_menu(),
    )


# ============================================================
# /status
# ============================================================

@bot.message_handler(commands=["status"])
def status_command(message):
    """Return the current Aternos server status."""

    ok, result = aternos.status()

    if ok:
        bot.reply_to(
            message,
            f"🟢 <b>حالة السيرفر</b>\n\n<code>{result}</code>",
        )
    else:
        bot.reply_to(
            message,
            f"❌ <b>فشل الحصول على الحالة</b>\n\n<code>{result}</code>",
        )


# ============================================================
# /startserver
# ============================================================

@bot.message_handler(commands=["startserver"])
def start_server_command(message):
    """Start the configured Aternos server."""

    bot.reply_to(message, "⏳ جاري إرسال طلب تشغيل السيرفر...")

    ok, result = aternos.start()

    if ok:
        bot.send_message(
            message.chat.id,
            f"▶️ <b>تم إرسال طلب تشغيل السيرفر.</b>\n\n<code>{result}</code>",
        )
    else:
        bot.send_message(
            message.chat.id,
            f"❌ <b>فشل التشغيل:</b>\n<code>{result}</code>",
        )


# ============================================================
# /stopserver
# ============================================================

@bot.message_handler(commands=["stopserver"])
def stop_server_command(message):
    """Stop the configured Aternos server."""

    bot.reply_to(message, "⏳ جاري إرسال طلب الإيقاف...")

    ok, result = aternos.stop()

    if ok:
        bot.send_message(
            message.chat.id,
            f"⏹️ <b>تم إرسال طلب إيقاف السيرفر.</b>\n\n<code>{result}</code>",
        )
    else:
        bot.send_message(
            message.chat.id,
            f"❌ <b>فشل الإيقاف:</b>\n<code>{result}</code>",
        )


# ============================================================
# /restart
# ============================================================

@bot.message_handler(commands=["restart"])
def restart_command(message):
    """Restart the configured Aternos server."""

    bot.reply_to(message, "⏳ جاري تنفيذ Restart...")

    ok, result = aternos.restart()

    if ok:
        bot.send_message(
            message.chat.id,
            f"🔄 <b>تم إرسال طلب Restart.</b>\n\n<code>{result}</code>",
        )
    else:
        bot.send_message(
            message.chat.id,
            f"❌ <b>فشل Restart:</b>\n<code>{result}</code>",
        )


# ============================================================
# /info
# ============================================================

@bot.message_handler(commands=["info"])
def info_command(message):
    """Display server information."""

    ok, result = aternos.info()

    if ok:
        bot.reply_to(
            message,
            f"ℹ️ <b>معلومات السيرفر</b>\n\n<code>{result}</code>",
        )
    else:
        bot.reply_to(
            message,
            f"❌ <b>فشل:</b>\n<code>{result}</code>",
        )


# ============================================================
# /players
# ============================================================

@bot.message_handler(commands=["players"])
def players_command(message):
    """Display currently connected players."""

    ok, result = aternos.players()

    if ok:
        bot.reply_to(
            message,
            f"👥 <b>اللاعبون</b>\n\n<code>{result}</code>",
        )
    else:
        bot.reply_to(
            message,
            f"❌ <b>فشل:</b>\n<code>{result}</code>",
        )


# ============================================================
# /console
# ============================================================

@bot.message_handler(commands=["console"])
def console_command(message):
    """
    Send a Minecraft console command.

    Example:
        /console list
        /console say Hello
        /console whitelist add Player
    """

    command = message.text.partition(" ")[2].strip()

    if not command:
        bot.reply_to(
            message,
            (
                "🖥️ <b>Console</b>\n\n"
                "استخدم:\n"
                "<code>/console list</code>\n"
                "<code>/console say Hello</code>"
            ),
        )
        return

    ok, result = aternos.console(command)

    if ok:
        bot.reply_to(
            message,
            (
                "✅ <b>تم إرسال الأمر</b>\n\n"
                f"🎮 <code>{command}</code>\n\n"
                f"{result}"
            ),
        )
    else:
        bot.reply_to(
            message,
            f"❌ <b>فشل:</b>\n<code>{result}</code>",
        )


# ============================================================
# Callback buttons
# ============================================================

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    """Handle all inline keyboard buttons."""

    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass

    chat_id = call.message.chat.id

    if call.data == "status":
        ok, result = aternos.status()

        if ok:
            bot.send_message(
                chat_id,
                f"🟢 <b>الحالة:</b>\n\n<code>{result}</code>",
            )
        else:
            bot.send_message(
                chat_id,
                f"❌ <code>{result}</code>",
            )

    elif call.data == "start":
        bot.send_message(
            chat_id,
            "⏳ جاري تشغيل السيرفر...",
        )

        ok, result = aternos.start()

        bot.send_message(
            chat_id,
            (
                f"▶️ <b>تم إرسال طلب التشغيل.</b>\n<code>{result}</code>"
                if ok
                else f"❌ <b>فشل التشغيل:</b>\n<code>{result}</code>"
            ),
        )

    elif call.data == "stop":
        bot.send_message(
            chat_id,
            "⏳ جاري إيقاف السيرفر...",
        )

        ok, result = aternos.stop()

        bot.send_message(
            chat_id,
            (
                f"⏹️ <b>تم إرسال طلب الإيقاف.</b>\n<code>{result}</code>"
                if ok
                else f"❌ <b>فشل الإيقاف:</b>\n<code>{result}</code>"
            ),
        )

    elif call.data == "restart":
        bot.send_message(
            chat_id,
            "⏳ جاري Restart...",
        )

        ok, result = aternos.restart()

        bot.send_message(
            chat_id,
            (
                f"🔄 <b>تم إرسال طلب Restart.</b>\n<code>{result}</code>"
                if ok
                else f"❌ <b>فشل Restart:</b>\n<code>{result}</code>"
            ),
        )

    elif call.data == "players":
        ok, result = aternos.players()

        bot.send_message(
            chat_id,
            (
                f"👥 <b>اللاعبون:</b>\n\n<code>{result}</code>"
                if ok
                else f"❌ <code>{result}</code>"
            ),
        )

    elif call.data == "info":
        ok, result = aternos.info()

        bot.send_message(
            chat_id,
            (
                f"ℹ️ <b>معلومات السيرفر:</b>\n\n<code>{result}</code>"
                if ok
                else f"❌ <code>{result}</code>"
            ),
        )

    elif call.data == "console":
        bot.send_message(
            chat_id,
            (
                "🖥️ <b>Console</b>\n\n"
                "أرسل الأمر بهذا الشكل:\n"
                "<code>/console list</code>\n\n"
                "أو:\n"
                "<code>/console say أهلاً</code>"
            ),
        )


# ============================================================
# Unknown commands/messages
# ============================================================

@bot.message_handler(func=lambda message: True)
def fallback_handler(message):
    """Show the control panel for unsupported text."""

    if message.text and message.text.startswith("/"):
        bot.reply_to(
            message,
            "❌ الأمر غير معروف.\n\nاستخدم /start",
        )
    else:
        bot.send_message(
            message.chat.id,
            "استخدم /start لفتح لوحة التحكم.",
            reply_markup=main_menu(),
        )


# ============================================================
# Polling
# ============================================================

def run_bot():
    """
    Start Telegram polling.

    Telegram error 409 means another polling process is using
    the same bot token. The bot waits and retries.
    """

    print("🤖 Telegram Bot Started", flush=True)

    try:
        bot.remove_webhook()
        print("✅ Webhook removed", flush=True)
    except Exception as exc:
        print(f"⚠️ Webhook removal failed: {exc}", flush=True)

    while True:
        try:
            print("🚀 Starting Telegram polling...", flush=True)

            bot.infinity_polling(
                skip_pending=True,
                timeout=60,
                long_polling_timeout=60,
                allowed_updates=[
                    "message",
                    "callback_query",
                ],
            )

        except Exception as exc:
            error = str(exc)

            print(
                f"❌ Telegram polling error: {error}",
                flush=True,
            )

            if "409" in error or "Conflict" in error:
                print(
                    "⚠️ Telegram 409 Conflict. "
                    "Waiting 15 seconds...",
                    flush=True,
                )
                time.sleep(15)
            else:
                time.sleep(10)


# ============================================================
# Application entry point
# ============================================================

if __name__ == "__main__":
    start_health_server()
    run_bot()
