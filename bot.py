import os
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests
import telebot
from telebot import types

# =========================================================
# Aternos
# =========================================================

try:
    from python_aternos import Client as AternosClient
except Exception as exc:
    AternosClient = None
    ATERNOS_IMPORT_ERROR = str(exc)

# =========================================================
# Environment Variables
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID", "").strip()

ATERNOS_USERNAME = os.getenv("ATERNOS_USERNAME", "").strip()
ATERNOS_PASSWORD = os.getenv("ATERNOS_PASSWORD", "").strip()
ATERNOS_SERVER = os.getenv(
    "ATERNOS_SERVER",
    "MACESMP37.aternos.me"
).strip()

# =========================================================
# Validation
# =========================================================

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN غير موجود في Render Environment Variables")

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN غير موجود في Render Environment Variables")

if not DISCORD_CHANNEL_ID:
    raise RuntimeError("DISCORD_CHANNEL_ID غير موجود في Render Environment Variables")

# =========================================================
# Telegram Bot
# =========================================================

bot = telebot.TeleBot(
    BOT_TOKEN,
    parse_mode="HTML"
)

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

# =========================================================
# Console Commands
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
    "teleport",
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
    "kill",
}

DIRECT_COMMANDS = ADMIN_COMMANDS.copy()

CONSOLE_WHITELIST = {
    x.strip().lower().lstrip("/")
    for x in os.getenv(
        "CONSOLE_WHITELIST",
        "say,whitelist,list,online,save-all"
    ).split(",")
    if x.strip()
}

# =========================================================
# Discord Functions
# =========================================================

def send_to_discord(content):
    try:
        response = requests.post(
            DISCORD_URL,
            headers=DISCORD_HEADERS,
            json={"content": content},
            timeout=15,
        )

        if response.status_code not in (200, 201, 204):
            print(
                "Discord API:",
                response.status_code,
                response.text[:500],
                flush=True
            )
            return False, response.text

        return True, "OK"

    except requests.RequestException as exc:
        print(
            "Discord connection error:",
            exc,
            flush=True
        )
        return False, str(exc)


def send_console(command):
    command = command.strip().lstrip("/")
    return send_to_discord(command)


def command_allowed(command):
    command = command.strip().lstrip("/")

    if not command:
        return False

    first = command.split()[0].lower()

    return (
        first in CONSOLE_WHITELIST
        or first in ADMIN_COMMANDS
    )

# =========================================================
# Aternos
# =========================================================

_aternos_client = None
_aternos_account = None
_aternos_server = None
_aternos_lock = threading.Lock()


def get_aternos_server():
    global _aternos_client
    global _aternos_account
    global _aternos_server

    if AternosClient is None:
        return (
            None,
            "مكتبة Aternos لم يتم تحميلها.\n"
            f"سبب الاستيراد: {ATERNOS_IMPORT_ERROR}"
        )

    if not ATERNOS_USERNAME:
        return None, "ATERNOS_USERNAME غير موجود."

    if not ATERNOS_PASSWORD:
        return None, "ATERNOS_PASSWORD غير موجود."

    with _aternos_lock:

        try:

            if _aternos_server is not None:
                return _aternos_server, None

            print(
                "[ATERNOS] تسجيل الدخول...",
                flush=True
            )

            client = AternosClient()

            client.login(
                ATERNOS_USERNAME,
                ATERNOS_PASSWORD
            )

            account = client.account

            print(
                "[ATERNOS] البحث عن السيرفر...",
                flush=True
            )

            servers = account.list_servers()

            wanted = ATERNOS_SERVER.lower().strip()

            for server in servers:

                address = str(
                    getattr(server, "address", "")
                ).lower().strip()

                name = str(
                    getattr(server, "name", "")
                ).lower().strip()

                if (
                    wanted == address
                    or wanted == name
                    or wanted in address
                ):

                    _aternos_client = client
                    _aternos_account = account
                    _aternos_server = server

                    print(
                        f"[ATERNOS] تم العثور على: {address}",
                        flush=True
                    )

                    return server, None

            return (
                None,
                f"لم أجد السيرفر:\n{ATERNOS_SERVER}"
            )

        except Exception as exc:

            _aternos_client = None
            _aternos_account = None
            _aternos_server = None

            print(
                "[ATERNOS ERROR]",
                repr(exc),
                flush=True
            )

            return None, str(exc)


def aternos_action(action):

    server, error = get_aternos_server()

    if error:
        return False, error

    global _aternos_client
    global _aternos_account
    global _aternos_server

    try:

        if action == "start":
            result = server.start()

        elif action == "stop":
            result = server.stop()

        elif action == "restart":
            result = server.restart()

        elif action == "status":

            result = getattr(
                server,
                "status",
                None
            )

            if callable(result):
                result = result()

        else:
            return False, "عملية Aternos غير معروفة."

        return (
            True,
            str(result) if result is not None else "OK"
        )

    except Exception as exc:

        _aternos_client = None
        _aternos_account = None
        _aternos_server = None

        return False, str(exc)

# =========================================================
# Render Web Server
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
        f"🌐 Web server running on port {port}",
        flush=True
    )

    server.serve_forever()


threading.Thread(
    target=start_web_server,
    daemon=True
).start()

# =========================================================
# Main Menu
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
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "⏹ إيقاف السيرفر",
            callback_data="server_stop"
        ),
        types.InlineKeyboardButton(
            "🔄 Restart",
            callback_data="server_restart"
        )
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
        "🟢 البوت يعمل.\n\n"
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
            "مثال:\n"
            "<code>/console list</code>"
        )
        return

    if not command_allowed(command):
        bot.reply_to(
            message,
            "⛔ الأمر غير موجود في قائمة الأوامر."
        )
        return

    ok, detail = send_console(command)

    if ok:
        bot.reply_to(
            message,
            "✅ تم إرسال الأمر إلى DiscordSRV.\n\n"
            f"🎮 <code>{command}</code>"
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

    text = message.text.partition(" ")[2].strip()

    if not text:
        bot.reply_to(
            message,
            "مثال:\n"
            "<code>/say أهلاً باللاعبين!</code>"
        )
        return

    ok, detail = send_console(
        "say " + text
    )

    if ok:
        bot.reply_to(
            message,
            "📢 تم إرسال الرسالة للسيرفر."
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

    elif (
        action in {"add", "remove"}
        and len(args) == 2
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
            "❌ الاستخدام غير صحيح."
        )
        return

    ok, detail = send_console(command)

    if ok:
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
# Direct Minecraft Commands
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
        raw.split()[0].lower()
    )

    if command_name not in DIRECT_COMMANDS:

        bot.reply_to(
            message,
            "❌ الأمر غير موجود.\n"
            "استخدم /start."
        )
        return

    ok, detail = send_console(raw)

    if ok:

        bot.reply_to(
            message,
            "✅ <b>تم إرسال الأمر إلى DiscordSRV.</b>\n\n"
            f"🎮 <code>{raw}</code>"
        )

    else:

        bot.reply_to(
            message,
            f"❌ فشل:\n<code>{detail}</code>"
        )

# =========================================================
# Callback Buttons
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

    if call.data == "console":

        bot.send_message(
            chat_id,
            "🖥 Console\n\n"
            "مثال:\n"
            "<code>/console list</code>\n\n"
            "أو استخدم أوامر Minecraft المباشرة."
        )

    elif call.data == "say":

        bot.send_message(
            chat_id,
            "📢 مثال:\n"
            "<code>/say أهلاً باللاعبين!</code>"
        )

    elif call.data == "whitelist":

        bot.send_message(
            chat_id,
            "🟢 Whitelist:\n\n"
            "<code>/whitelist add Player</code>\n"
            "<code>/whitelist remove Player</code>\n"
            "<code>/whitelist list</code>"
        )

    elif call.data == "admin":

        bot.send_message(
            chat_id,
            "👑 <b>أوامر الإدارة</b>\n\n"
            "<code>/op Player</code>\n"
            "<code>/deop Player</code>\n"
            "<code>/kick Player</code>\n"
            "<code>/ban Player</code>\n"
            "<code>/pardon Player</code>\n"
            "<code>/gamemode creative Player</code>\n"
            "<code>/tp Player Player2</code>\n"
            "<code>/give Player item 1</code>\n"
            "<code>/save-all</code>\n"
            "<code>/plugins</code>\n"
            "<code>/reload</code>"
        )

    elif call.data == "status":

        ok, detail = aternos_action(
            "status"
        )

        if ok:

            bot.send_message(
                chat_id,
                "🟢 <b>Aternos Status</b>\n\n"
                f"<code>{detail}</code>"
            )

        else:

            bot.send_message(
                chat_id,
                "❌ <b>فشل الحصول على الحالة</b>\n\n"
                f"<code>{detail}</code>"
            )

    elif call.data == "aternos_start":

        bot.send_message(
            chat_id,
            "⏳ جاري طلب تشغيل Aternos..."
        )

        ok, detail = aternos_action(
            "start"
        )

        if ok:

            bot.send_message(
                chat_id,
                "▶️ <b>تم إرسال طلب تشغيل Aternos.</b>"
            )

        else:

            bot.send_message(
                chat_id,
                "❌ <b>فشل التشغيل:</b>\n\n"
                f"<code>{detail}</code>"
            )

    elif call.data == "server_stop":

        bot.send_message(
            chat_id,
            "⏳ جاري طلب إيقاف Aternos..."
        )

        ok, detail = aternos_action(
            "stop"
        )

        if ok:

            bot.send_message(
                chat_id,
                "⏹️ <b>تم إرسال طلب إيقاف Aternos.</b>"
            )

        else:

            bot.send_message(
                chat_id,
                "❌ <b>فشل الإيقاف:</b>\n\n"
                f"<code>{detail}</code>"
            )

    elif call.data == "server_restart":

        bot.send_message(
            chat_id,
            "⏳ جاري طلب Restart..."
        )

        ok, detail = aternos_action(
            "restart"
        )

        if ok:

            bot.send_message(
                chat_id,
                "🔄 <b>تم إرسال طلب Restart.</b>"
            )

        else:

            bot.send_message(
                chat_id,
                "❌ <b>فشل Restart:</b>\n\n"
                f"<code>{detail}</code>"
            )

# =========================================================
# Unknown Messages
# =========================================================

@bot.message_handler(
    func=lambda message: True
)
def unknown_message(message):

    bot.send_message(
        message.chat.id,
        "استخدم /start لعرض لوحة التحكم."
    )

# =========================================================
# Start Bot
# =========================================================

if __name__ == "__main__":

    print(
        "🤖 Telegram Bot Started",
        flush=True
    )

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

    while True:

        try:

            bot.infinity_polling(
                skip_pending=True,
                timeout=60,
                long_polling_timeout=60
            )

        except telebot.apihelper.ApiTelegramException as exc:

            text = str(exc)

            if (
                "409" in text
                or "Conflict" in text
            ):

                print(
                    "⚠️ Telegram 409 Conflict — "
                    "إعادة المحاولة بعد 10 ثوانٍ...",
                    flush=True
                )

                time.sleep(10)

            elif (
                "401" in text
                or "Unauthorized" in text
            ):

                print(
                    "❌ Telegram 401 — "
                    "تحقق من BOT_TOKEN.",
                    flush=True
                )

                time.sleep(30)

            else:

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
