import os
import re
import time
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import telebot
from telebot import types
from mcstatus import JavaServer, BedrockServer


# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

DEFAULT_SERVER_HOST = os.getenv(
    "MC_SERVER_HOST",
    "MACESMP37.aternos.me"
).strip()

DEFAULT_SERVER_PORT = int(
    os.getenv("MC_SERVER_PORT", "25565")
)

ATERNOS_URL = os.getenv(
    "ATERNOS_URL",
    "https://aternos.org/server/"
).strip()

PORT = int(os.getenv("PORT", "10000"))

STATUS_TIMEOUT = float(
    os.getenv("STATUS_TIMEOUT", "5")
)

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN غير موجود في Environment Variables"
    )


# ============================================================
# TELEGRAM BOT
# ============================================================

bot = telebot.TeleBot(
    BOT_TOKEN,
    parse_mode="HTML",
    threaded=True
)


# ============================================================
# SIMPLE MEMORY STORAGE
# ============================================================

user_servers = {}
user_lock = threading.Lock()


# ============================================================
# SERVER STORAGE
# ============================================================

def get_user_server(chat_id):
    """إرجاع السيرفر المحفوظ للمستخدم."""
    with user_lock:
        return user_servers.get(
            chat_id,
            {
                "host": DEFAULT_SERVER_HOST,
                "port": DEFAULT_SERVER_PORT
            }
        ).copy()


def save_user_server(chat_id, host, port):
    """حفظ سيرفر للمستخدم."""
    with user_lock:
        user_servers[chat_id] = {
            "host": host,
            "port": int(port)
        }


# ============================================================
# ADDRESS PARSER
# ============================================================

def clean_host(host):
    """تنظيف عنوان السيرفر."""
    host = str(host or "").strip()

    host = re.sub(
        r"^https?://",
        "",
        host,
        flags=re.IGNORECASE
    )

    host = host.split("/")[0].strip()

    return host


def parse_server_address(address):
    """
    تحليل:
    example.com
    example.com:25565
    [IPv6]:25565
    """

    address = clean_host(address)

    if not address:
        raise ValueError("عنوان السيرفر فارغ")

    # IPv6
    if address.startswith("["):
        match = re.match(
            r"^\[([^\]]+)\](?::(\d+))?$",
            address
        )

        if match:
            host = match.group(1)
            port = int(match.group(2) or 25565)
            return host, port

    # hostname:port
    parts = address.rsplit(":", 1)

    if len(parts) == 2 and parts[1].isdigit():
        port = int(parts[1])

        if not 1 <= port <= 65535:
            raise ValueError("المنفذ يجب أن يكون بين 1 و 65535")

        return parts[0], port

    return address, 25565


# ============================================================
# JAVA STATUS
# ============================================================

def get_java_status(host, port):
    """فحص Java Edition."""

    server = JavaServer(
        host,
        port,
        timeout=STATUS_TIMEOUT
    )

    result = server.status(tries=2)

    players_online = 0
    players_max = 0
    version = "غير معروف"

    try:
        players_online = int(result.players.online)
    except Exception:
        pass

    try:
        players_max = int(result.players.max)
    except Exception:
        pass

    try:
        version = str(result.version.name or "غير معروف")
    except Exception:
        pass

    try:
        latency = round(float(result.latency))
    except Exception:
        latency = None

    return {
        "online": True,
        "edition": "Java",
        "host": host,
        "port": port,
        "players": players_online,
        "max_players": players_max,
        "latency": latency,
        "version": version
    }


# ============================================================
# BEDROCK STATUS
# ============================================================

def get_bedrock_status(host, port):
    """فحص Bedrock Edition."""

    server = BedrockServer(
        host,
        port,
        timeout=STATUS_TIMEOUT
    )

    result = server.status(tries=2)

    players_online = 0
    players_max = 0
    version = "غير معروف"

    try:
        players_online = int(result.players.online)
    except Exception:
        pass

    try:
        players_max = int(result.players.max)
    except Exception:
        pass

    try:
        version = str(result.version.name or "غير معروف")
    except Exception:
        pass

    try:
        latency = round(float(result.latency))
    except Exception:
        latency = None

    return {
        "online": True,
        "edition": "Bedrock",
        "host": host,
        "port": port,
        "players": players_online,
        "max_players": players_max,
        "latency": latency,
        "version": version
    }


# ============================================================
# REAL STATUS
# ============================================================

def get_real_server_status(host, port=25565):
    """
    فحص حقيقي للسيرفر.

    يجرب Java ثم Bedrock.
    إذا لم يستجب أي منهما يعتبر السيرفر Offline.
    """

    host = clean_host(host)

    java_error = None

    try:
        return get_java_status(
            host,
            port
        )

    except Exception as exc:
        java_error = exc

    # Bedrock يستخدم غالبًا 19132.
    # لكننا نجرب المنفذ المحدد أولًا.
    try:
        return get_bedrock_status(
            host,
            port
        )

    except Exception:
        pass

    # إذا كان المنفذ الافتراضي 25565،
    # نجرب منفذ Bedrock الشائع.
    if port == 25565:
        try:
            return get_bedrock_status(
                host,
                19132
            )

        except Exception:
            pass

    return {
        "online": False,
        "edition": "Unknown",
        "host": host,
        "port": port,
        "players": 0,
        "max_players": 0,
        "latency": None,
        "version": None,
        "error": str(java_error or "Server offline")
    }


# ============================================================
# FORMAT STATUS
# ============================================================

def format_status(data):
    """تحويل نتيجة الفحص إلى رسالة Telegram."""

    if not data["online"]:
        return (
            "🔴 <b>السيرفر Offline</b>\n\n"
            f"🌐 العنوان:\n"
            f"<code>{data['host']}:{data['port']}</code>\n\n"
            "📡 لم يستجب السيرفر لطلب Minecraft Server List Ping."
        )

    latency = data.get("latency")

    if latency is None:
        ping = "غير معروف"
    else:
        ping = f"{latency}ms"

    version = data.get("version") or "غير معروف"

    return (
        "🟢 <b>السيرفر Online</b>\n\n"
        f"👥 اللاعبين: "
        f"<b>{data['players']}/{data['max_players']}</b>\n"
        f"📶 Ping: <b>{ping}</b>\n"
        f"🎮 الإصدار: <b>{version}</b>\n"
        f"🧩 النوع: <b>{data['edition']}</b>\n"
        f"🌐 العنوان:\n"
        f"<code>{data['host']}:{data['port']}</code>"
    )


# ============================================================
# KEYBOARD
# ============================================================

def main_keyboard():
    """لوحة التحكم."""

    markup = types.InlineKeyboardMarkup(row_width=2)

    markup.add(
        types.InlineKeyboardButton(
            "📊 حالة السيرفر",
            callback_data="server_status"
        ),
        types.InlineKeyboardButton(
            "👥 اللاعبين",
            callback_data="server_status"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "▶️ تشغيل",
            callback_data="aternos_start"
        ),
        types.InlineKeyboardButton(
            "⏹️ إيقاف",
            callback_data="server_stop"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "🔄 Restart",
            callback_data="server_restart"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "🌐 فتح Aternos",
            url=ATERNOS_URL
        )
    )

    return markup


# ============================================================
# /START
# ============================================================

@bot.message_handler(commands=["start"])
def start_command(message):
    """لوحة البداية."""

    server = get_user_server(
        message.chat.id
    )

    status = get_real_server_status(
        server["host"],
        server["port"]
    )

    text = (
        "🤖 <b>بوت إدارة سيرفر Minecraft</b>\n\n"
        f"🌐 السيرفر:\n"
        f"<code>{server['host']}:{server['port']}</code>\n\n"
        f"{format_status(status)}\n\n"
        "اختر العملية:"
    )

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=main_keyboard()
    )


# ============================================================
# /STATUS
# ============================================================

@bot.message_handler(
    commands=["status", "serverstatus"]
)
def status_command(message):
    """عرض الحالة الحقيقية."""

    server = get_user_server(
        message.chat.id
    )

    msg = bot.send_message(
        message.chat.id,
        "🔎 <b>جاري فحص السيرفر...</b>"
    )

    status = get_real_server_status(
        server["host"],
        server["port"]
    )

    try:
        bot.edit_message_text(
            format_status(status),
            message.chat.id,
            msg.message_id,
            reply_markup=main_keyboard()
        )

    except Exception:
        bot.send_message(
            message.chat.id,
            format_status(status),
            reply_markup=main_keyboard()
        )


# ============================================================
# /SERVER
# ============================================================

@bot.message_handler(commands=["server"])
def server_command(message):
    """طلب عنوان سيرفر جديد."""

    bot.send_message(
        message.chat.id,
        "📥 <b>أرسل عنوان السيرفر:</b>\n\n"
        "مثال:\n"
        "<code>MACESMP37.aternos.me</code>\n\n"
        "أو:\n"
        "<code>example.com:25565</code>"
    )

    bot.register_next_step_handler(
        message,
        receive_server_address
    )


def receive_server_address(message):
    """استقبال عنوان السيرفر."""

    try:
        if not message.text:
            raise ValueError("لم يتم إرسال عنوان")

        host, port = parse_server_address(
            message.text
        )

        save_user_server(
            message.chat.id,
            host,
            port
        )

        bot.send_message(
            message.chat.id,
            "✅ <b>تم حفظ السيرفر</b>\n\n"
            f"🌐 <code>{host}:{port}</code>\n\n"
            "🔎 جاري فحص الحالة..."
        )

        status = get_real_server_status(
            host,
            port
        )

        bot.send_message(
            message.chat.id,
            format_status(status),
            reply_markup=main_keyboard()
        )

    except Exception as exc:
        bot.send_message(
            message.chat.id,
            "❌ <b>فشل حفظ السيرفر</b>\n\n"
            f"<code>{str(exc)[:500]}</code>"
        )


# ============================================================
# CALLBACKS
# ============================================================

@bot.callback_query_handler(
    func=lambda call: True
)
def callback_handler(call):
    """معالجة أزرار البوت."""

    chat_id = call.message.chat.id

    try:
        bot.answer_callback_query(
            call.id
        )
    except Exception:
        pass

    server = get_user_server(
        chat_id
    )

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    if call.data == "server_status":

        status = get_real_server_status(
            server["host"],
            server["port"]
        )

        try:
            bot.edit_message_text(
                format_status(status),
                chat_id,
                call.message.message_id,
                reply_markup=main_keyboard()
            )
        except Exception:
            bot.send_message(
                chat_id,
                format_status(status),
                reply_markup=main_keyboard()
            )

        return

    # --------------------------------------------------------
    # START
    # --------------------------------------------------------

    if call.data == "aternos_start":

        markup = types.InlineKeyboardMarkup()

        markup.add(
            types.InlineKeyboardButton(
                "🌐 فتح Aternos",
                url=ATERNOS_URL
            )
        )

        bot.send_message(
            chat_id,
            "▶️ <b>تشغيل السيرفر</b>\n\n"
            "هذه النسخة لا تستخدم python-aternos "
            "ولا تدّعي تنفيذ Start بدون API موثوق.\n\n"
            "يمكنك فتح لوحة Aternos من الزر.",
            reply_markup=markup
        )

        return

    # --------------------------------------------------------
    # STOP
    # --------------------------------------------------------

    if call.data == "server_stop":

        markup = types.InlineKeyboardMarkup()

        markup.add(
            types.InlineKeyboardButton(
                "🌐 فتح Aternos",
                url=ATERNOS_URL
            )
        )

        bot.send_message(
            chat_id,
            "⏹️ <b>إيقاف السيرفر</b>\n\n"
            "هذه النسخة لا تنفذ Stop بشكل وهمي.\n"
            "افتح لوحة Aternos إذا أردت إيقاف السيرفر.",
            reply_markup=markup
        )

        return

    # --------------------------------------------------------
    # RESTART
    # --------------------------------------------------------

    if call.data == "server_restart":

        markup = types.InlineKeyboardMarkup()

        markup.add(
            types.InlineKeyboardButton(
                "🌐 فتح Aternos",
                url=ATERNOS_URL
            )
        )

        bot.send_message(
            chat_id,
            "🔄 <b>Restart</b>\n\n"
            "هذه النسخة لا تدّعي تنفيذ Restart "
            "بدون API موثوق.",
            reply_markup=markup
        )

        return


# ============================================================
# /IP
# ============================================================

@bot.message_handler(commands=["ip"])
def ip_command(message):
    """عرض IP السيرفر."""

    server = get_user_server(
        message.chat.id
    )

    bot.send_message(
        message.chat.id,
        "🌐 <b>عنوان السيرفر</b>\n\n"
        f"<code>{server['host']}:{server['port']}</code>"
    )


# ============================================================
# /HELP
# ============================================================

@bot.message_handler(commands=["help"])
def help_command(message):
    """عرض الأوامر."""

    bot.send_message(
        message.chat.id,
        "📚 <b>أوامر البوت</b>\n\n"
        "/start — لوحة التحكم\n"
        "/status — الحالة الحقيقية\n"
        "/server — تغيير السيرفر\n"
        "/ip — عنوان السيرفر\n"
        "/help — المساعدة"
    )


# ============================================================
# TEXT HANDLER
# ============================================================

@bot.message_handler(
    func=lambda message: True,
    content_types=["text"]
)
def text_handler(message):
    """معالجة الرسائل النصية."""

    text = message.text.strip().lower()

    if text in [
        "status",
        "الحالة",
        "حالة السيرفر"
    ]:
        status_command(message)
        return

    if text in [
        "ip",
        "الاي بي",
        "الاى بي",
        "الآي بي"
    ]:
        ip_command(message)
        return

    bot.send_message(
        message.chat.id,
        "استخدم /start لفتح لوحة التحكم."
    )


# ============================================================
# RENDER HEALTH SERVER
# ============================================================

class HealthHandler(BaseHTTPRequestHandler):
    """HTTP Health Check لـRender."""

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
    """تشغيل HTTP server."""

    server = ThreadingHTTPServer(
        ("0.0.0.0", PORT),
        HealthHandler
    )

    print(
        f"Health server listening on port {PORT}"
    )

    server.serve_forever()


# ============================================================
# TELEGRAM POLLING
# ============================================================

def run_bot():
    """تشغيل Telegram polling."""

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
                f"Telegram polling error: {exc}"
            )

            time.sleep(5)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print("========================================")
    print("Minecraft Telegram Bot")
    print(
        f"Default server: "
        f"{DEFAULT_SERVER_HOST}:{DEFAULT_SERVER_PORT}"
    )
    print("python-aternos: DISABLED")
    print("Real Minecraft status: ENABLED")
    print("========================================")

    health_thread = threading.Thread(
        target=run_health_server,
        daemon=True
    )

    health_thread.start()

    run_bot()
