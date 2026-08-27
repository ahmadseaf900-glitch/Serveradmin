import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests
import telebot
from telebot import types

# =========================================================
# إعدادات
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")

ATERNOS_USERNAME = os.getenv("ATERNOS_USERNAME")
ATERNOS_PASSWORD = os.getenv("ATERNOS_PASSWORD")
ATERNOS_SERVER = os.getenv(
    "ATERNOS_SERVER",
    "MACESMP37.aternos.me"
)

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN غير موجود")

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN غير موجود")

if not DISCORD_CHANNEL_ID:
    raise RuntimeError("DISCORD_CHANNEL_ID غير موجود")

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


def send_to_discord(content):
    try:
        response = requests.post(
            DISCORD_URL,
            headers=DISCORD_HEADERS,
            json={"content": content},
            timeout=15
        )

        if response.status_code not in (200, 201):
            print(
                "Discord Error:",
                response.status_code,
                response.text[:500],
                flush=True
            )
            return False

        return True

    except Exception as exc:
        print(
            "Discord Connection Error:",
            exc,
            flush=True
        )
        return False


def send_console(command):
    command = command.strip().lstrip("/")

    if not command:
        return False

    return send_to_discord(command)


# =========================================================
# Aternos
# =========================================================

try:
    from python_aternos import Client as AternosClient
    ATERNOS_AVAILABLE = True
    print("✅ py-aternos loaded", flush=True)

except ImportError as exc:
    ATERNOS_AVAILABLE = False
    AternosClient = None
    print(
        f"⚠️ Aternos library unavailable: {exc}",
        flush=True
    )


_aternos_client = None
_aternos_server = None
_aternos_lock = threading.Lock()


def get_aternos_server():

    global _aternos_client
    global _aternos_server

    if not ATERNOS_AVAILABLE:
        return None, (
            "❌ مكتبة Aternos غير متوفرة في البيئة."
        )

    if not ATERNOS_USERNAME:
        return None, (
            "❌ ATERNOS_USERNAME غير موجود."
        )

    if not ATERNOS_PASSWORD:
        return None, (
            "❌ ATERNOS_PASSWORD غير موجود."
        )

    with _aternos_lock:

        try:

            if _aternos_server is not None:
                return _aternos_server, None

            print(
                "🔐 تسجيل الدخول إلى Aternos...",
                flush=True
            )

            client = AternosClient()

            client.login(
                ATERNOS_USERNAME,
                ATERNOS_PASSWORD
            )

            account = client.account

            servers = account.list_servers()

            wanted = (
                ATERNOS_SERVER
                .strip()
                .lower()
            )

            for server in servers:

                address = str(
                    getattr(
                        server,
                        "address",
                        ""
                    )
                ).strip().lower()

                name = str(
                    getattr(
                        server,
                        "name",
                        ""
                    )
                ).strip().lower()

                if (
                    wanted == address
                    or wanted == name
                    or wanted in address
                ):

                    _aternos_client = client
                    _aternos_server = server

                    print(
                        f"✅ Aternos server found: {address}",
                        flush=True
                    )

                    return server, None

            return None, (
                f"❌ لم يتم العثور على السيرفر: "
                f"{ATERNOS_SERVER}"
            )

        except Exception as exc:

            _aternos_client = None
            _aternos_server = None

            print(
                "❌ Aternos Error:",
                repr(exc),
                flush=True
            )

            return None, str(exc)


def aternos_action(action):

    server, error = get_aternos_server()

    if error:
        return False, error

    try:

        if action == "start":

            result = server.start()

            return True, (
                "▶️ تم إرسال طلب تشغيل السيرفر."
                if result is None
                else str(result)
            )

        if action == "stop":

            result = server.stop()

            return True, (
                "⏹️ تم إرسال طلب إيقاف السيرفر."
                if result is None
                else str(result)
            )

        if action == "restart":

            result = server.restart()

            return True, (
                "🔄 تم إرسال طلب Restart."
                if result is None
                else str(result)
            )

        if action == "status":

            status = getattr(
                server,
                "status",
                None
            )

            if callable(status):
                status = status()

            return True, str(status)

        return False, "عملية Aternos غير معروفة."

    except Exception as exc:

        print(
            "❌ Aternos action error:",
            repr(exc),
            flush=True
        )

        global _aternos_client
        global _aternos_server

        _aternos_client = None
        _aternos_server = None

        return False, str(exc)


# =========================================================
# القائمة
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
            "▶️ تشغيل",
            callback_data="start"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "⏹️ إيقاف",
            callback_data="stop"
        ),
        types.InlineKeyboardButton(
            "🔄 Restart",
            callback_data="restart"
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
        f"🎮 السيرفر:\n"
        f"<code>{ATERNOS_SERVER}</code>\n\n"
        "اختر العملية:",
        reply_markup=main_menu()
    )


# =========================================================
# /console
# =========================================================

@bot.message_handler(commands=["console"])
def console_command(message):

    command = (
        message.text
        .partition(" ")[2]
        .strip()
    )

    if not command:
        bot.reply_to(
            message,
            "مثال:\n"
            "<code>/console list</code>"
        )
        return

    if send_console(command):

        bot.reply_to(
            message,
            "✅ تم إرسال الأمر إلى Discord Console.\n\n"
            f"<code>{command}</code>"
        )

    else:

        bot.reply_to(
            message,
            "❌ فشل إرسال الأمر إلى Discord."
        )


# =========================================================
# /say
# =========================================================

@bot.message_handler(commands=["say"])
def say_command(message):

    text = (
        message.text
        .partition(" ")[2]
        .strip()
    )

    if not text:

        bot.reply_to(
            message,
            "مثال:\n"
            "<code>/say أهلاً بالجميع!</code>"
        )

        return

    if send_console("say " + text):

        bot.reply_to(
            message,
            "📢 تم إرسال الرسالة."
        )

    else:

        bot.reply_to(
            message,
            "❌ فشل إرسال الرسالة."
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

    elif action in ("add", "remove"):

        if len(args) != 2:

            bot.reply_to(
                message,
                "❌ اكتب اسم اللاعب."
            )

            return

        player = args[1]

        command = (
            f"whitelist {action} {player}"
        )

    else:

        bot.reply_to(
            message,
            "❌ الأمر غير صحيح."
        )

        return

    if send_console(command):

        bot.reply_to(
            message,
            "✅ تم إرسال الأمر."
        )

    else:

        bot.reply_to(
            message,
            "❌ فشل إرسال الأمر."
        )


# =========================================================
# أوامر Minecraft
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
    "whitelist"
}


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

    if command_name not in DIRECT_COMMANDS:

        bot.reply_to(
            message,
            "❌ الأمر غير موجود."
        )

        return

    if send_console(raw):

        bot.reply_to(
            message,
            "✅ <b>تم إرسال الأمر.</b>\n\n"
            f"<code>/{raw}</code>"
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

    chat_id = call.message.chat.id

    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass

    # -------------------------
    # Console
    # -------------------------

    if call.data == "console":

        bot.send_message(
            chat_id,
            "🖥 Console\n\n"
            "استخدم:\n"
            "<code>/console list</code>\n\n"
            "أو أي أمر Minecraft مسموح."
        )

    # -------------------------
    # Say
    # -------------------------

    elif call.data == "say":

        bot.send_message(
            chat_id,
            "📢 استخدم:\n"
            "<code>/say رسالتك</code>"
        )

    # -------------------------
    # Whitelist
    # -------------------------

    elif call.data == "whitelist":

        bot.send_message(
            chat_id,
            "🟢 Whitelist\n\n"
            "<code>/whitelist add Player</code>\n"
            "<code>/whitelist remove Player</code>\n"
            "<code>/whitelist list</code>"
        )

    # -------------------------
    # Admin
    # -------------------------

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

    # -------------------------
    # Aternos Status
    # -------------------------

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
                "❌ <b>فشل جلب الحالة</b>\n\n"
                f"<code>{detail}</code>"
            )

    # -------------------------
    # Start
    # -------------------------

    elif call.data == "start":

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
                "❌ <b>فشل التشغيل</b>\n\n"
                f"<code>{detail}</code>"
            )

    # -------------------------
    # Stop
    # -------------------------

    elif call.data == "stop":

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
                "❌ <b>فشل الإيقاف</b>\n\n"
                f"<code>{detail}</code>"
            )

    # -------------------------
    # Restart
    # -------------------------

    elif call.data == "restart":

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
                "❌ <b>فشل Restart</b>\n\n"
                f"<code>{detail}</code>"
            )


# =========================================================
# رسائل أخرى
# =========================================================

@bot.message_handler(
    func=lambda message: True
)
def unknown_message(message):

    bot.send_message(
        message.chat.id,
        "استخدم /start لفتح لوحة التحكم.",
        reply_markup=main_menu()
    )


# =========================================================
# Web Server
# =========================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        self.send_response(200)

        self.send_header(
            "Content-Type",
            "text/plain"
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

    port = int(
        os.getenv(
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
