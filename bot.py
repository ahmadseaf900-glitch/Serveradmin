import os
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests
import telebot
from telebot import types

from aternos import (
    start as aternos_start_action,
    stop as aternos_stop_action,
    restart as aternos_restart_action,
    status as aternos_get_status,
)


# =========================================================
# إعدادات البوت
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")

ATERNOS_SERVER = os.getenv(
    "ATERNOS_SERVER",
    "MACESMP37.aternos.me"
).strip()

ATERNOS_URL = os.getenv(
    "ATERNOS_URL",
    "https://aternos.org/"
)


# =========================================================
# التحقق من الإعدادات الأساسية
# =========================================================

if not BOT_TOKEN:
    raise RuntimeError(
        "❌ BOT_TOKEN غير موجود في Render Environment Variables"
    )

if not DISCORD_TOKEN:
    raise RuntimeError(
        "❌ DISCORD_TOKEN غير موجود في Render Environment Variables"
    )

if not DISCORD_CHANNEL_ID:
    raise RuntimeError(
        "❌ DISCORD_CHANNEL_ID غير موجود في Render Environment Variables"
    )


# =========================================================
# إنشاء البوت
# =========================================================

bot = telebot.TeleBot(
    BOT_TOKEN,
    parse_mode="HTML"
)


# =========================================================
# أوامر Console المسموحة
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
# أوامر الإدارة
# =========================================================

ADMIN_COMMANDS = {
    "list",
    "online",
    "say",
    "whitelist",
    "op",
    "deop",
    "kick",
    "ban",
    "pardon",
    "tp",
    "gamemode",
    "give",
    "effect",
    "time",
    "weather",
    "difficulty",
    "gamerule",
    "save-all",
    "save-on",
    "save-off",
    "stop",
    "reload",
    "plugins",
    "version",
    "seed",
    "locate",
    "teleport",
    "kill",
}


DIRECT_COMMANDS = {
    "op",
    "deop",
    "kick",
    "ban",
    "pardon",
    "tp",
    "teleport",
    "give",
    "gamemode",
    "effect",
    "time",
    "weather",
    "difficulty",
    "gamerule",
    "save-all",
    "save-on",
    "save-off",
    "stop",
    "reload",
    "plugins",
    "version",
    "seed",
    "locate",
    "kill",
    "list",
    "online",
    "whitelist",
}


# =========================================================
# Discord API
# =========================================================

DISCORD_URL = (
    f"https://discord.com/api/v10/channels/"
    f"{DISCORD_CHANNEL_ID}/messages"
)

DISCORD_HEADERS = {
    "Authorization": f"Bot {DISCORD_TOKEN}",
    "Content-Type": "application/json",
}


# =========================================================
# إرسال رسالة إلى Discord
# =========================================================

def send_to_discord(content):
    """
    إرسال نص إلى قناة Discord المحددة.
    DiscordSRV يمكنه استقبال الأمر من القناة
    وتنفيذه في Minecraft Console حسب إعداداته.
    """

    try:
        response = requests.post(
            DISCORD_URL,
            headers=DISCORD_HEADERS,
            json={
                "content": content
            },
            timeout=15,
        )

        if response.status_code not in (200, 201):
            print(
                "Discord API:",
                response.status_code,
                response.text[:500],
                flush=True,
            )

            return False, response.text

        return True, "OK"

    except requests.RequestException as exc:
        print(
            "Discord connection error:",
            exc,
            flush=True,
        )

        return False, str(exc)


# =========================================================
# إرسال أمر Minecraft Console
# =========================================================

def send_console(command):
    """
    إرسال أمر Minecraft إلى Discord.

    لا نضيف !c لأن إعداد DiscordSRV المستخدم
    هو المسؤول عن تنفيذ الرسالة كـConsole.
    """

    command = command.strip().lstrip("/")

    if not command:
        return False, "الأمر فارغ."

    return send_to_discord(command)


# =========================================================
# فحص صلاحية الأمر
# =========================================================

def command_allowed(command):
    """
    السماح فقط بالأوامر الموجودة في القائمة.
    """

    command = command.strip().lstrip("/")

    if not command:
        return False

    parts = command.split()

    if not parts:
        return False

    first = parts[0].lower()

    return (
        first in CONSOLE_WHITELIST
        or first in ADMIN_COMMANDS
    )


# =========================================================
# القائمة الرئيسية
# =========================================================

def main_menu():

    markup = types.InlineKeyboardMarkup(
        row_width=2
    )

    markup.add(
        types.InlineKeyboardButton(
            "🟢 حالة السيرفر",
            callback_data="status"
        ),
        types.InlineKeyboardButton(
            "▶️ تشغيل Aternos",
            callback_data="aternos_start"
        ),
    )

    markup.add(
        types.InlineKeyboardButton(
            "⏹ إيقاف السيرفر",
            callback_data="server_stop"
        ),
        types.InlineKeyboardButton(
            "🔄 Restart",
            callback_data="server_restart"
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
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "👑 Admin",
            callback_data="admin"
        )
    )

    return markup


# =========================================================
# /start
# =========================================================

@bot.message_handler(commands=["start"])
def start_command(message):

    bot.send_message(
        message.chat.id,
        "🤖 <b>بوت إدارة سيرفر Minecraft</b>\n\n"
        "🟢 <b>البوت يعمل بدون نظام حماية أو دعوات.</b>\n\n"
        "🎮 اختر العملية:",
        reply_markup=main_menu()
    )


# =========================================================
# /console
# =========================================================

@bot.message_handler(commands=["console"])
def console_command(message):

    command = message.text.partition(" ")[2].strip()

    if not command:

        bot.reply_to(
            message,
            "🖥 <b>استخدم:</b>\n\n"
            "<code>/console list</code>"
        )

        return

    if not command_allowed(command):

        bot.reply_to(
            message,
            "⛔ <b>هذا الأمر غير مسموح.</b>\n\n"
            "الأمر غير موجود في قائمة Console."
        )

        return

    ok, detail = send_console(command)

    if ok:

        bot.reply_to(
            message,
            "✅ <b>تم إرسال الأمر إلى Discord.</b>\n\n"
            f"🎮 <code>{command}</code>"
        )

    else:

        bot.reply_to(
            message,
            "❌ <b>فشل إرسال الأمر.</b>\n\n"
            f"<code>{detail}</code>"
        )


# =========================================================
# /say
# =========================================================

@bot.message_handler(commands=["say"])
def say_command(message):

    text = message.text.partition(" ")[2].strip()

    if not text:

        bot.reply_to(
            message,
            "📢 <b>مثال:</b>\n\n"
            "<code>/say أهلاً باللاعبين!</code>"
        )

        return

    command = "say " + text

    ok, detail = send_console(command)

    if ok:

        bot.reply_to(
            message,
            "📢 <b>تم إرسال الرسالة للسيرفر.</b>"
        )

    else:

        bot.reply_to(
            message,
            "❌ <b>فشل الإرسال:</b>\n"
            f"<code>{detail}</code>"
        )


# =========================================================
# /whitelist
# =========================================================

@bot.message_handler(commands=["whitelist"])
def whitelist_command(message):

    args = (
        message.text
        .partition(" ")[2]
        .strip()
        .split()
    )

    if not args:

        bot.reply_to(
            message,
            "🟢 <b>أوامر Whitelist:</b>\n\n"
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
            "❌ الأمر غير صحيح."
        )

        return

    if action == "list":

        command = "whitelist list"

    elif (
        len(args) == 2
        and re.fullmatch(
            r"[A-Za-z0-9_]{1,16}",
            args[1]
        )
    ):

        command = (
            f"whitelist {action} {args[1]}"
        )

    else:

        bot.reply_to(
            message,
            "❌ اسم اللاعب غير صالح أو ناقص."
        )

        return

    ok, detail = send_console(command)

    if ok:

        bot.reply_to(
            message,
            "✅ <b>تم إرسال أمر Whitelist.</b>\n\n"
            f"<code>{command}</code>"
        )

    else:

        bot.reply_to(
            message,
            "❌ <b>فشل:</b>\n"
            f"<code>{detail}</code>"
        )


# =========================================================
# أوامر Minecraft المباشرة
# =========================================================

@bot.message_handler(
    func=lambda message:
        bool(message.text)
        and message.text.startswith("/")
)
def direct_admin_command(message):

    raw = message.text[1:].strip()

    if not raw:
        return

    command_name = (
        raw.split()[0]
        .lower()
    )

    if command_name not in DIRECT_COMMANDS:

        bot.reply_to(
            message,
            "❌ <b>الأمر غير موجود.</b>\n\n"
            "استخدم /start لعرض القائمة."
        )

        return

    if not command_allowed(raw):

        bot.reply_to(
            message,
            "⛔ <b>هذا الأمر غير مسموح.</b>"
        )

        return

    ok, detail = send_console(raw)

    if ok:

        bot.reply_to(
            message,
            "✅ <b>تم إرسال الأمر إلى Discord.</b>\n\n"
            f"🎮 <code>{raw}</code>"
        )

    else:

        bot.reply_to(
            message,
            "❌ <b>فشل إرسال الأمر:</b>\n\n"
            f"<code>{detail}</code>"
        )


# =========================================================
# أزرار البوت
# =========================================================

@bot.callback_query_handler(
    func=lambda call: True
)
def callback_handler(call):

    chat_id = call.message.chat.id

    try:
        bot.answer_callback_query(
            call.id
        )
    except Exception:
        pass


    # =====================================================
    # حالة السيرفر
    # =====================================================

    if call.data == "status":

        result = aternos_get_status()

        if result.get("online"):

            players = result.get(
                "players",
                0
            )

            max_players = result.get(
                "max_players",
                0
            )

            latency = result.get(
                "latency"
            )

            version = result.get(
                "version"
            )

            ping_text = (
                f"{latency}ms"
                if latency is not None
                else "غير معروف"
            )

            version_text = (
                str(version)
                if version
                else "غير معروف"
            )

            bot.send_message(
                chat_id,
                "🟢 <b>السيرفر Online</b>\n\n"
                f"👥 اللاعبين: "
                f"<b>{players}/{max_players}</b>\n"
                f"📶 Ping: <b>{ping_text}</b>\n"
                f"🎮 الإصدار: "
                f"<code>{version_text}</code>\n"
                f"🌐 العنوان:\n"
                f"<code>{ATERNOS_SERVER}</code>"
            )

        else:

            bot.send_message(
                chat_id,
                "🔴 <b>السيرفر Offline</b>\n\n"
                f"🌐 العنوان:\n"
                f"<code>{ATERNOS_SERVER}</code>"
            )

        return


    # =====================================================
    # تشغيل Aternos
    # =====================================================

    if call.data == "aternos_start":

        result = aternos_start_action()

        markup = types.InlineKeyboardMarkup()

        markup.add(
            types.InlineKeyboardButton(
                "🌐 فتح Aternos",
                url=result["url"]
            )
        )

        bot.send_message(
            chat_id,
            "▶️ <b>تشغيل السيرفر</b>\n\n"
            "افتح لوحة Aternos واضغط "
            "<b>Start</b>.",
            reply_markup=markup
        )

        return


    # =====================================================
    # إيقاف Aternos
    # =====================================================

    if call.data == "server_stop":

        result = aternos_stop_action()

        markup = types.InlineKeyboardMarkup()

        markup.add(
            types.InlineKeyboardButton(
                "🌐 فتح Aternos",
                url=result["url"]
            )
        )

        bot.send_message(
            chat_id,
            "⏹️ <b>إيقاف السيرفر</b>\n\n"
            "افتح لوحة Aternos واضغط "
            "<b>Stop</b>.",
            reply_markup=markup
        )

        return


    # =====================================================
    # Restart Aternos
    # =====================================================

    if call.data == "server_restart":

        result = aternos_restart_action()

        markup = types.InlineKeyboardMarkup()

        markup.add(
            types.InlineKeyboardButton(
                "🌐 فتح Aternos",
                url=result["url"]
            )
        )

        bot.send_message(
            chat_id,
            "🔄 <b>Restart</b>\n\n"
            "افتح لوحة Aternos ونفّذ "
            "إعادة التشغيل من هناك.",
            reply_markup=markup
        )

        return


    # =====================================================
    # Console
    # =====================================================

    if call.data == "console":

        bot.send_message(
            chat_id,
            "🖥 <b>Console</b>\n\n"
            "أرسل الأمر بهذا الشكل:\n\n"
            "<code>/console list</code>\n\n"
            "أو استخدم أمرًا مباشرًا مثل:\n"
            "<code>/op Player</code>"
        )

        return


    # =====================================================
    # Say
    # =====================================================

    if call.data == "say":

        bot.send_message(
            chat_id,
            "📢 أرسل:\n\n"
            "<code>/say رسالتك</code>"
        )

        return


    # =====================================================
    # Whitelist
    # =====================================================

    if call.data == "whitelist":

        bot.send_message(
            chat_id,
            "🟢 <b>Whitelist</b>\n\n"
            "<code>/whitelist add Player</code>\n"
            "<code>/whitelist remove Player</code>\n"
            "<code>/whitelist list</code>"
        )

        return


    # =====================================================
    # Admin
    # =====================================================

    if call.data == "admin":

        bot.send_message(
            chat_id,
            "👑 <b>أوامر الإدارة</b>\n\n"

            "<code>/op Player</code>\n"
            "<code>/deop Player</code>\n"
            "<code>/kick Player [سبب]</code>\n"
            "<code>/ban Player [سبب]</code>\n"
            "<code>/pardon Player</code>\n"
            "<code>/gamemode creative Player</code>\n"
            "<code>/tp Player Player2</code>\n"
            "<code>/give Player item 1</code>\n"
            "<code>/effect Player effect</code>\n"
            "<code>/time set day</code>\n"
            "<code>/weather clear</code>\n"
            "<code>/save-all</code>\n"
            "<code>/plugins</code>\n"
            "<code>/version</code>\n"
            "<code>/list</code>\n"
            "<code>/reload</code>"
        )

        return


# =========================================================
# الرسائل غير المعروفة
# =========================================================

@bot.message_handler(
    func=lambda message: True
)
def unknown_message(message):

    bot.send_message(
        message.chat.id,
        "🤖 <b>بوت إدارة Minecraft</b>\n\n"
        "استخدم /start لفتح لوحة التحكم.",
        reply_markup=main_menu()
    )


# =========================================================
# Web Server لـRender
# =========================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        self.send_response(200)

        self.send_header(
            "Content-type",
            "text/plain; charset=utf-8"
        )

        self.end_headers()

        self.wfile.write(
            b"Telegram Minecraft Bot is running!"
        )

    def log_message(
        self,
        format,
        *args
    ):
        return


def start_web_server():
    """
    تشغيل HTTP server بسيط حتى يستطيع Render
    اكتشاف المنفذ وتشغيل الخدمة.
    """

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
        f"🌐 Web server running on port {port}",
        flush=True
    )

    server.serve_forever()


# =========================================================
# تشغيل Web Server في Thread
# =========================================================

threading.Thread(
    target=start_web_server,
    daemon=True
).start()


# =========================================================
# تشغيل البوت
# =========================================================

if __name__ == "__main__":

    print(
        "🤖 Telegram Minecraft Bot Started",
        flush=True
    )

    # إزالة Webhook القديم حتى لا يتعارض
    # مع نظام polling.
    try:

        bot.remove_webhook()

        print(
            "✅ Webhook removed",
            flush=True
        )

    except Exception as exc:

        print(
            "⚠️ Webhook removal:",
            exc,
            flush=True
        )


    print(
        "🚀 Starting Telegram polling...",
        flush=True
    )


    # إعادة المحاولة تلقائيًا عند أخطاء Telegram.
    while True:

        try:

            bot.infinity_polling(
                skip_pending=True,
                timeout=60,
                long_polling_timeout=60
            )

        except telebot.apihelper.ApiTelegramException as exc:

            error_text = str(exc)

            if (
                "409" in error_text
                or "Conflict" in error_text
            ):

                print(
                    "⚠️ Telegram 409 Conflict "
                    "— إعادة المحاولة بعد 10 ثوانٍ...",
                    flush=True
                )

                time.sleep(10)

                continue


            if (
                "401" in error_text
                or "Unauthorized" in error_text
            ):

                print(
                    "❌ Telegram 401 Unauthorized "
                    "— تحقق من BOT_TOKEN.",
                    flush=True
                )

                time.sleep(30)

                continue


            print(
                f"❌ Telegram API error: {exc}",
                flush=True
            )

            time.sleep(10)


        except Exception as exc:

            print(
                f"❌ Polling error: {exc}",
                flush=True
            )

            time.sleep(10)
