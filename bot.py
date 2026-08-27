import os
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests
import telebot
from telebot import types

try:
    from python_aternos import Client as AternosClient
except ImportError:
    AternosClient = None


# ============================================================
# Environment Variables
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID", "").strip()

ATERNOS_USERNAME = os.getenv("ATERNOS_USERNAME", "").strip()
ATERNOS_PASSWORD = os.getenv("ATERNOS_PASSWORD", "").strip()

# مثال:
# MACESMP37.aternos.me
ATERNOS_SERVER = os.getenv(
    "ATERNOS_SERVER",
    "MACESMP37.aternos.me"
).strip()


# ============================================================
# Validation
# ============================================================

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN غير موجود في Render Environment Variables")

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN غير موجود في Render Environment Variables")

if not DISCORD_CHANNEL_ID:
    raise RuntimeError(
        "DISCORD_CHANNEL_ID غير موجود في Render Environment Variables"
    )

if not ATERNOS_USERNAME:
    raise RuntimeError(
        "ATERNOS_USERNAME غير موجود في Render Environment Variables"
    )

if not ATERNOS_PASSWORD:
    raise RuntimeError(
        "ATERNOS_PASSWORD غير موجود في Render Environment Variables"
    )


# ============================================================
# Telegram
# ============================================================

bot = telebot.TeleBot(
    BOT_TOKEN,
    parse_mode="HTML"
)


# ============================================================
# Discord
# ============================================================

DISCORD_URL = (
    f"https://discord.com/api/v10/channels/"
    f"{DISCORD_CHANNEL_ID}/messages"
)

DISCORD_HEADERS = {
    "Authorization": f"Bot {DISCORD_TOKEN}",
    "Content-Type": "application/json",
}


# ============================================================
# Aternos state
# ============================================================

_aternos_client = None
_aternos_account = None
_aternos_server = None

_aternos_lock = threading.Lock()


# ============================================================
# Minecraft command whitelist
# ============================================================

DIRECT_COMMANDS = {
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


# ============================================================
# Discord command sender
# ============================================================

def send_to_discord(content: str):
    """
    إرسال رسالة إلى قناة Discord المحددة.
    DiscordSRV يمكنه التقاط الرسالة وتنفيذها حسب إعداد السيرفر.
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

        if response.status_code not in (200, 201, 204):
            print(
                "Discord API Error:",
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


def send_console(command: str):
    """
    إرسال أمر Minecraft إلى Discord.
    """

    command = command.strip().lstrip("/")

    if not command:
        return False, "الأمر فارغ."

    return send_to_discord(command)


# ============================================================
# Aternos
# ============================================================

def reset_aternos():
    """
    مسح جلسة Aternos الحالية لإعادة تسجيل الدخول لاحقًا.
    """

    global _aternos_client
    global _aternos_account
    global _aternos_server

    _aternos_client = None
    _aternos_account = None
    _aternos_server = None


def get_aternos_server():
    """
    تسجيل الدخول إلى Aternos والعثور على السيرفر المطلوب.
    """

    global _aternos_client
    global _aternos_account
    global _aternos_server

    if AternosClient is None:
        return (
            None,
            "مكتبة python-aternos غير مثبتة. "
            "تحقق من requirements.txt ثم أعد Deploy."
        )

    with _aternos_lock:

        try:

            # إذا كان السيرفر موجودًا مسبقًا نستخدم الجلسة الحالية.
            if _aternos_server is not None:
                return _aternos_server, None

            print(
                "🔐 تسجيل الدخول إلى Aternos...",
                flush=True,
            )

            client = AternosClient()

            client.login(
                ATERNOS_USERNAME,
                ATERNOS_PASSWORD
            )

            account = client.account

            print(
                "✅ تم تسجيل الدخول إلى Aternos",
                flush=True,
            )

            servers = account.list_servers()

            if not servers:
                return (
                    None,
                    "لم يتم العثور على أي سيرفر في حساب Aternos."
                )

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
                        f"✅ تم العثور على السيرفر: {address}",
                        flush=True,
                    )

                    return server, None

            available = []

            for server in servers:

                address = str(
                    getattr(server, "address", "")
                )

                name = str(
                    getattr(server, "name", "")
                )

                available.append(
                    f"{name} ({address})"
                )

            return (
                None,
                "لم أجد السيرفر المطلوب.\n"
                "السيرفرات الموجودة:\n"
                + "\n".join(available)
            )

        except Exception as exc:

            print(
                "Aternos error:",
                repr(exc),
                flush=True,
            )

            reset_aternos()

            return None, str(exc)


def aternos_action(action: str):
    """
    تنفيذ start / stop / restart / status على سيرفر Aternos.
    """

    server, error = get_aternos_server()

    if error:
        return False, error

    try:

        if action == "start":

            result = server.start()

            return (
                True,
                str(result)
                if result is not None
                else "تم إرسال طلب التشغيل."
            )

        if action == "stop":

            result = server.stop()

            return (
                True,
                str(result)
                if result is not None
                else "تم إرسال طلب الإيقاف."
            )

        if action == "restart":

            # بعض إصدارات المكتبة توفر restart.
            restart = getattr(
                server,
                "restart",
                None
            )

            if callable(restart):

                result = restart()

                return (
                    True,
                    str(result)
                    if result is not None
                    else "تم إرسال طلب Restart."
                )

            # fallback:
            # stop ثم start
            server.stop()

            time.sleep(3)

            server.start()

            return True, "تم تنفيذ Restart."

        if action == "status":

            status = getattr(
                server,
                "status",
                None
            )

            if callable(status):
                status = status()

            return (
                True,
                str(status)
                if status is not None
                else "غير معروف"
            )

        return False, "عملية Aternos غير معروفة."

    except Exception as exc:

        print(
            f"Aternos {action} error:",
            repr(exc),
            flush=True,
        )

        reset_aternos()

        return False, str(exc)


# ============================================================
# Render Web Server
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
            b"Telegram Minecraft Admin Bot is running!"
        )

    def log_message(self, format, *args):
        return


def start_web_server():
    """
    تشغيل HTTP server حتى يستطيع Render معرفة أن الخدمة تعمل.
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
        f"🌐 HTTP server running on port {port}",
        flush=True,
    )

    server.serve_forever()


threading.Thread(
    target=start_web_server,
    daemon=True
).start()


# ============================================================
# Telegram menu
# ============================================================

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
            "⏹ إيقاف Aternos",
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
        ),

        types.InlineKeyboardButton(
            "👑 Admin",
            callback_data="admin"
        ),

    )

    return markup


# ============================================================
# /start
# ============================================================

@bot.message_handler(commands=["start"])
def start_command(message):

    bot.send_message(
        message.chat.id,
        "🤖 <b>بوت إدارة سيرفر Minecraft</b>\n\n"
        "🟢 البوت يعمل بنجاح.\n\n"
        "اختر العملية:",
        reply_markup=main_menu(),
    )


# ============================================================
# /console
# ============================================================

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

    command_name = (
        command
        .lstrip("/")
        .split()[0]
        .lower()
    )

    if command_name not in DIRECT_COMMANDS:

        bot.reply_to(
            message,
            "⛔ هذا الأمر غير مسموح."
        )

        return

    ok, detail = send_console(command)

    if ok:

        bot.reply_to(
            message,
            "✅ تم إرسال الأمر:\n"
            f"<code>{command}</code>"
        )

    else:

        bot.reply_to(
            message,
            "❌ فشل الإرسال:\n"
            f"<code>{detail}</code>"
        )


# ============================================================
# /say
# ============================================================

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


# ============================================================
# /whitelist
# ============================================================

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
            f"❌ فشل:\n<code>{detail}</code>"
        )


# ============================================================
# Direct Minecraft commands
# ============================================================

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

    if command_name in {
        "start",
        "console",
        "say",
        "whitelist",
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
            "✅ <b>تم إرسال الأمر</b>\n\n"
            f"<code>{raw}</code>"
        )

    else:

        bot.reply_to(
            message,
            f"❌ فشل:\n<code>{detail}</code>"
        )


# ============================================================
# Callback buttons
# ============================================================

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

    # --------------------------------------------------------
    # Console
    # --------------------------------------------------------

    if call.data == "console":

        bot.send_message(
            chat_id,
            "🖥 Console\n\n"
            "أرسل مثلًا:\n"
            "<code>/console list</code>\n"
            "<code>/console say Hello</code>"
        )

        return

    # --------------------------------------------------------
    # Say
    # --------------------------------------------------------

    if call.data == "say":

        bot.send_message(
            chat_id,
            "📢 أرسل:\n"
            "<code>/say رسالتك</code>"
        )

        return

    # --------------------------------------------------------
    # Whitelist
    # --------------------------------------------------------

    if call.data == "whitelist":

        bot.send_message(
            chat_id,
            "🟢 Whitelist\n\n"
            "<code>/whitelist add Player</code>\n"
            "<code>/whitelist remove Player</code>\n"
            "<code>/whitelist list</code>"
        )

        return

    # --------------------------------------------------------
    # Admin
    # --------------------------------------------------------

    if call.data == "admin":

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

        return

    # --------------------------------------------------------
    # Aternos status
    # --------------------------------------------------------

    if call.data == "status":

        bot.send_message(
            chat_id,
            "⏳ جاري فحص Aternos..."
        )

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
                "❌ فشل فحص Aternos:\n"
                f"<code>{detail}</code>"
            )

        return

    # --------------------------------------------------------
    # Aternos start
    # --------------------------------------------------------

    if call.data == "aternos_start":

        bot.send_message(
            chat_id,
            "⏳ جاري إرسال طلب التشغيل..."
        )

        ok, detail = aternos_action(
            "start"
        )

        if ok:

            bot.send_message(
                chat_id,
                "▶️ <b>تم إرسال طلب تشغيل Aternos.</b>\n\n"
                f"<code>{detail}</code>"
            )

        else:

            bot.send_message(
                chat_id,
                "❌ فشل التشغيل:\n"
                f"<code>{detail}</code>"
            )

        return

    # --------------------------------------------------------
    # Aternos stop
    # --------------------------------------------------------

    if call.data == "server_stop":

        bot.send_message(
            chat_id,
            "⏳ جاري إرسال طلب الإيقاف..."
        )

        ok, detail = aternos_action(
            "stop"
        )

        if ok:

            bot.send_message(
                chat_id,
                "⏹️ <b>تم إرسال طلب إيقاف Aternos.</b>\n\n"
                f"<code>{detail}</code>"
            )

        else:

            bot.send_message(
                chat_id,
                "❌ فشل الإيقاف:\n"
                f"<code>{detail}</code>"
            )

        return

    # --------------------------------------------------------
    # Aternos restart
    # --------------------------------------------------------

    if call.data == "server_restart":

        bot.send_message(
            chat_id,
            "⏳ جاري تنفيذ Restart..."
        )

        ok, detail = aternos_action(
            "restart"
        )

        if ok:

            bot.send_message(
                chat_id,
                "🔄 <b>تم إرسال Restart إلى Aternos.</b>\n\n"
                f"<code>{detail}</code>"
            )

        else:

            bot.send_message(
                chat_id,
                "❌ فشل Restart:\n"
                f"<code>{detail}</code>"
            )

        return


# ============================================================
# Unknown messages
# ============================================================

@bot.message_handler(
    func=lambda message: True
)
def unknown_message(message):

    bot.send_message(
        message.chat.id,
        "استخدم /start لفتح لوحة التحكم.",
        reply_markup=main_menu(),
    )


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    print(
        "🤖 Telegram Minecraft Admin Bot Started",
        flush=True,
    )

    try:

        bot.remove_webhook()

        print(
            "✅ Webhook removed",
            flush=True,
        )

    except Exception as exc:

        print(
            "⚠️ Webhook removal:",
            exc,
            flush=True,
        )

    print(
        "🚀 Starting Telegram polling...",
        flush=True,
    )

    while True:

        try:

            bot.infinity_polling(
                skip_pending=True,
                timeout=60,
                long_polling_timeout=60,
            )

        except Exception as exc:

            print(
                "❌ Polling error:",
                repr(exc),
                flush=True,
            )

            time.sleep(10)
