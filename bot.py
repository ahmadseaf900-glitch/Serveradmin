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
except ImportError:
    AternosClient = None

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

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN غير موجود في Render")

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN غير موجود في Render")

if not DISCORD_CHANNEL_ID:
    raise RuntimeError("DISCORD_CHANNEL_ID غير موجود في Render")

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
# Minecraft Commands
# =========================================================

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

CONSOLE_WHITELIST = {
    x.strip().lower().lstrip("/")
    for x in os.getenv(
        "CONSOLE_WHITELIST",
        "say,whitelist,list,online,save-all"
    ).split(",")
    if x.strip()
}

# =========================================================
# Discord إرسال
# =========================================================

def send_to_discord(content):
    try:
        response = requests.post(
            DISCORD_URL,
            headers=DISCORD_HEADERS,
            json={"content": content},
            timeout=15,
        )

        if response.status_code not in (200, 201):
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

    if not command:
        return False, "الأمر فارغ."

    return send_to_discord(command)


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
        return None, (
            "python-aternos غير مثبت. "
            "تحقق من requirements.txt."
        )

    if not ATERNOS_USERNAME or not ATERNOS_PASSWORD:
        return None, (
            "ضع ATERNOS_USERNAME و "
            "ATERNOS_PASSWORD في Render."
        )

    with _aternos_lock:

        try:

            if _aternos_server is not None:
                return _aternos_server, None

            client = AternosClient()

            client.login(
                ATERNOS_USERNAME,
                ATERNOS_PASSWORD
            )

            account = client.account

            servers = account.list_servers()

            wanted = ATERNOS_SERVER.lower().strip()

            for server in servers:

                address = str(
                    getattr(
                        server,
                        "address",
                        ""
                    )
                ).lower().strip()

                name = str(
                    getattr(
                        server,
                        "name",
                        ""
                    )
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
                        f"✅ Aternos server found: "
                        f"{address}",
                        flush=True
                    )

                    return server, None

            return None, (
                f"لم أجد السيرفر "
                f"{ATERNOS_SERVER} "
                f"في حساب Aternos."
            )

        except Exception as exc:

            _aternos_client = None
            _aternos_account = None
            _aternos_server = None

            print(
                "Aternos error:",
                exc,
                flush=True
            )

            return None, str(exc)


def aternos_action(action):

    global _aternos_client
    global _aternos_account
    global _aternos_server

    server, error = get_aternos_server()

    if error:
        return False, error

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

        return True, (
            str(result)
            if result is not None
            else "OK"
        )

    except Exception as exc:

        _aternos_client = None
        _aternos_account = None
        _aternos_server = None

        return False, str(exc)


# =========================================================
# Web Server - Render
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

    telegram_id = message.from_user.id

    username = (
        message.from_user.username
        or "بدون username"
    )

    print(
        f"[START] Telegram ID: "
        f"{telegram_id} | "
        f"Username: @{username}",
        flush=True
    )

    text = (
        "🤖 <b>بوت إدارة سيرفرات ماينكرافت</b>\n\n"
        "🟢 البوت يعمل.\n\n"
        f"🆔 <b>Telegram ID:</b> "
        f"<code>{telegram_id}</code>\n\n"
        "🎮 اختر العملية:"
    )

    bot.send_message(
        message.chat.id,
        text,
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

    first = command.split()[0].lower()

    if (
        first not in CONSOLE_WHITELIST
        and first not in DIRECT_COMMANDS
    ):

        bot.reply_to(
            message,
            "⛔ هذا الأمر غير مسموح."
        )

        return

    ok, detail = send_console(command)

    if ok:

        bot.reply_to(
            message,
            "✅ <b>تم إرسال الأمر إلى DiscordSRV.</b>\n\n"
            f"🎮 <code>{command}</code>"
        )

    else:

        bot.reply_to(
            message,
            f"❌ فشل:\n"
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
            f"❌ فشل:\n"
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
            f"whitelist "
            f"{action} "
            f"{args[1]}"
        )

    else:

        bot.reply_to(
            message,
            "❌ الأمر غير صحيح."
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
            f"❌ فشل:\n"
            f"<code>{detail}</code>"
        )


# =========================================================
# Direct Minecraft Commands
# =========================================================

@bot.message_handler(
    func=lambda message:
    bool(message.text)
    and message.text.startswith("/")
)
def direct_command(message):

    raw = message.text[1:].strip()

    if not raw:
        return

    command_name = (
        raw.split()[0]
        .lower()
    )

    # الأوامر التي لها Handler خاص
    if command_name in {
        "start",
        "console",
        "say",
        "whitelist"
    }:
        return

    if command_name not in DIRECT_COMMANDS:

        bot.reply_to(
            message,
            "❌ الأمر غير موجود."
        )

        return

    ok, detail = send_console(raw)

    if ok:

        bot.reply_to(
            message,
            "✅ <b>تم إرسال الأمر.</b>\n\n"
            f"🎮 <code>{raw}</code>"
        )

    else:

        bot.reply_to(
            message,
            f"❌ فشل:\n"
            f"<code>{detail}</code>"
        )


# =========================================================
# Buttons
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

    # -----------------------------------------------------
    # Console
    # -----------------------------------------------------

    if call.data == "console":

        bot.send_message(
            chat_id,
            "🖥 Console\n\n"
            "أرسل مثلاً:\n"
            "<code>/console list</code>\n"
            "<code>/console say Hello</code>"
        )

    # -----------------------------------------------------
    # Status
    # -----------------------------------------------------

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
                "❌ فشل الحصول على الحالة:\n\n"
                f"<code>{detail}</code>"
            )

    # -----------------------------------------------------
    # Say
    # -----------------------------------------------------

    elif call.data == "say":

        bot.send_message(
            chat_id,
            "📢 أرسل:\n"
            "<code>/say رسالتك</code>"
        )

    # -----------------------------------------------------
    # Whitelist
    # -----------------------------------------------------

    elif call.data == "whitelist":

        bot.send_message(
            chat_id,
            "🟢 Whitelist\n\n"
            "<code>/whitelist add Player</code>\n"
            "<code>/whitelist remove Player</code>\n"
            "<code>/whitelist list</code>"
        )

    # -----------------------------------------------------
    # Admin
    # -----------------------------------------------------

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
            "<code>/reload</code>\n"
            "<code>/list</code>"
        )

    # -----------------------------------------------------
    # Aternos Start
    # -----------------------------------------------------

    elif call.data == "aternos_start":

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
                "❌ فشل التشغيل:\n\n"
                f"<code>{detail}</code>"
            )

    # -----------------------------------------------------
    # Aternos Stop
    # -----------------------------------------------------

    elif call.data == "server_stop":

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
                "❌ فشل الإيقاف:\n\n"
                f"<code>{detail}</code>"
            )

    # -----------------------------------------------------
    # Aternos Restart
    # -----------------------------------------------------

    elif call.data == "server_restart":

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
                "❌ فشل Restart:\n\n"
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
        "استخدم /start لعرض القائمة.",
        reply_markup=main_menu()
    )


# =========================================================
# Start
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

            error_text = str(exc)

            if (
                "409" in error_text
                or "Conflict" in error_text
            ):

                print(
                    "⚠️ Telegram 409 Conflict. "
                    "يوجد Bot instance آخر بنفس التوكن.",
                    flush=True
                )

                time.sleep(15)
                continue

            if (
                "401" in error_text
                or "Unauthorized" in error_text
            ):

                print(
                    "❌ Telegram 401 Unauthorized. "
                    "تحقق من BOT_TOKEN.",
                    flush=True
                )

                time.sleep(30)
                continue

            print(
                "❌ Telegram API error:",
                exc,
                flush=True
            )

            time.sleep(10)

        except Exception as exc:

            print(
                "❌ Polling error:",
                exc,
                flush=True
            )

            time.sleep(10)
