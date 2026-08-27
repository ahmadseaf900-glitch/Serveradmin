import os
import re
import time
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import telebot
from telebot import types
from mcstatus import JavaServer, BedrockServer


# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# السيرفر الافتراضي
DEFAULT_SERVER_HOST = os.getenv(
    "MC_SERVER_HOST",
    "MACESMP37.aternos.me"
).strip()

DEFAULT_SERVER_PORT = int(
    os.getenv("MC_SERVER_PORT", "25565")
)

# رابط لوحة Aternos - يستخدم فقط للفتح اليدوي عند الحاجة
ATERNOS_URL = os.getenv(
    "ATERNOS_URL",
    "https://aternos.org/server/"
).strip()

# اختياري: Discord
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID", "").strip()

# Port الخاص بـ Render
PORT = int(os.getenv("PORT", "10000"))

# فحص الحالة
STATUS_TIMEOUT = float(os.getenv("STATUS_TIMEOUT", "5"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN غير موجود في Environment Variables")


# ============================================================
# BOT
# ============================================================

bot = telebot.TeleBot(
    BOT_TOKEN,
    parse_mode="HTML",
    threaded=True
)


# ============================================================
# SIMPLE STORAGE
# ============================================================

user_servers = {}
user_lock = threading.Lock()


# ============================================================
# SERVER MODEL
# ============================================================

def get_user_server(chat_id):
    """
    يرجع السيرفر المحفوظ للمستخدم.
    """
    with user_lock:
        return user_servers.get(
            chat_id,
            {
                "host": DEFAULT_SERVER_HOST,
                "port": DEFAULT_SERVER_PORT
            }
        )


def save_user_server(chat_id, host, port=25565):
    """
    يحفظ عنوان سيرفر للمستخدم.
    """
    with user_lock:
        user_servers[chat_id] = {
            "host": host,
            "port": int(port)
        }


# ============================================================
# SERVER ADDRESS PARSER
# ============================================================

def clean_host(host):
    """
    تنظيف عنوان السيرفر من البروتوكولات والمسارات.
    """
    host = host.strip()

    host = re.sub(
        r"^https?://",
        "",
        host,
        flags=re.IGNORECASE
    )

    host = host.split("/")[0]

    return host.strip()


def parse_server_address(address):
    """
    يحلل:
        example.aternos.me
        example.aternos.me:25565

    ويعيد host, port.
    """

    address = clean_host(address)

    if ":" in address:
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
            return parts[0], int(parts[1])

    return address, 25565


# ============================================================
# REAL MINECRAFT STATUS
# ============================================================

def get_java_status(host, port):
    """
    فحص Java Edition باستخدام Minecraft Server List Ping.
    """

    server = JavaServer(
        host,
        port,
        timeout=STATUS_TIMEOUT
    )

    status = server.status(
        tries=2
    )

    version_name = "غير معروف"

    try:
        version_name = status.version.name or "غير معروف"
    except Exception:
        pass

    online_players = 0
    max_players = 0

    try:
        online_players = status.players.online
    except Exception:
        pass

    try:
        max_players = status.players.max
    except Exception:
        pass

    latency = round(float(status.latency), 0)

    return {
        "online": True,
        "edition": "Java",
        "host": host,
        "port": port,
        "players": online_players,
        "max_players": max_players,
        "latency": latency,
        "version": version_name
    }


def get_bedrock_status(host, port):
    """
    فحص Bedrock Edition.
    """

    server = BedrockServer(
        host,
        port,
        timeout=STATUS_TIMEOUT
    )

    status = server.status(
        tries=2
    )

    version_name = "غير معروف"

    try:
        version_name = status.version.name or "غير معروف"
    except Exception:
        pass

    online_players = 0
    max_players = 0

    try:
        online_players = status.players.online
    except Exception:
        pass

    try:
        max_players = status.players.max
    except Exception:
        pass

    latency = round(float(status.latency), 0)

    return {
        "online": True,
        "edition": "Bedrock",
        "host": host,
        "port": port,
        "players": online_players,
        "max_players": max_players,
        "latency": latency,
        "version": version_name
    }


def get_real_server_status(host, port=25565):
    """
    يحاول Java أولًا ثم Bedrock.

    لا يعتمد على MOTD لمعرفة Online/Offline.
    إذا فشل الاتصال فعليًا يعيد Offline.
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

    # إذا كان المستخدم يستخدم Bedrock
    try:
        return get_bedrock_status(
            host,
            port
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
        "error": str(java_error) if java_error else "Server offline"
    }


# ============================================================
# FORMAT STATUS
# ============================================================

def format_status(data):
    """
    تحويل بيانات السيرفر إلى رسالة Telegram.
    """

    if not data["online"]:
        return (
            "🔴 <b>السيرفر Offline</b>\n\n"
            f"🌐 العنوان: <code>{data['host']}</code>\n"
            f"🔌 المنفذ: <code>{data['port']}</code>\n\n"
            "📡 لم يستجب السيرفر لـ Minecraft Server List Ping."
        )

    players = data["players"]
    max_players = data["max_players"]

    latency = data["latency"]

    if latency is None:
        ping_text = "غير معروف"
    else:
        ping_text = f"{latency}ms"

    version = data["version"] or "غير معروف"

    return (
        "🟢 <b>السيرفر Online</b>\n\n"
        f"👥 اللاعبين: <b>{players}/{max_players}</b>\n"
        f"📶 Ping: <b>{ping_text}</b>\n"
        f"🎮 الإصدار: <b>{version}</b>\n"
        f"🧩 النوع: <b>{data['edition']}</b>\n"
        f"🌐 العنوان: <code>{data['host']}:{data['port']}</code>"
    )


# ============================================================
# KEYBOARD
# ============================================================

def main_keyboard():
    """
    لوحة التحكم الرئيسية.
    """

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
            "🌐 Aternos",
            url=ATERNOS_URL
        )
    )

    return markup


# ============================================================
# /START
# ============================================================

@bot.message_handler(commands=["start"])
def start_command(message):
    """
    الأمر الرئيسي للبوت.
    """

    server = get_user_server(
        message.chat.id
    )

    status = get_real_server_status(
        server["host"],
        server["port"]
    )

    text = (
        "🤖 <b>بوت إدارة سيرفر Minecraft</b>\n\n"
        f"🌐 السيرفر: <code>{server['host']}</code>\n\n"
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
    """
    يعرض الحالة الحقيقية للسيرفر.
    """

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
    """
    يعرض السيرفر الحالي ويطلب عنوانًا جديدًا.
    """

    bot.send_message(
        message.chat.id,
        "📥 أرسل عنوان السيرفر.\n\n"
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
    """
    يستقبل عنوان السيرفر ويحفظه.
    """

    try:
        host, port = parse_server_address(
            message.text
        )

        if not host:
            raise ValueError("عنوان فارغ")

        save_user_server(
            message.chat.id,
            host,
            port
        )

        bot.send_message(
            message.chat.id,
            "✅ <b>تم حفظ السيرفر</b>\n\n"
            f"🌐 <code>{host}:{port}</code>\n\n"
            "🔎 جاري التحقق من الحالة..."
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
            "❌ فشل حفظ السيرفر.\n\n"
            f"<code>{str(exc)[:500]}</code>"
        )


# ============================================================
# CALLBACK HANDLER
# ============================================================

@bot.callback_query_handler(
    func=lambda call: True
)
def callback_handler(call):
    """
    معالجة أزرار Telegram.
    """

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
    # REAL STATUS
    # --------------------------------------------------------

    if call.data == "server_status":

        try:
            status = get_real_server_status(
                server["host"],
                server["port"]
            )

            bot.send_message(
                chat_id,
                format_status(status),
                reply_markup=main_keyboard()
            )

        except Exception as exc:

            bot.send_message(
                chat_id,
                "❌ فشل فحص الحالة:\n"
                f"<code>{str(exc)[:500]}</code>"
            )

        return

    # --------------------------------------------------------
    # START
    # --------------------------------------------------------

    if call.data == "aternos_start":

        # لا ندعي أن السيرفر اشتغل.
        # Aternos لا يوفر Public API رسميًا لهذا التحكم.

        markup = types.InlineKeyboardMarkup()

        markup.add(
            types.InlineKeyboardButton(
                "🌐 فتح لوحة Aternos",
                url=ATERNOS_URL
            )
        )

        bot.send_message(
            chat_id,
            "▶️ <b>تشغيل السيرفر</b>\n\n"
            "لا يوجد API رسمي من Aternos يسمح للبوت "
            "بتنفيذ Start مباشرة.\n\n"
            "لذلك لن أرسل لك رسالة كاذبة بأن السيرفر اشتغل.\n\n"
            "بعد تشغيله، اضغط <b>📊 حالة السيرفر</b> "
            "وسأتحقق منه مباشرة عبر Minecraft.",
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
                "🌐 فتح لوحة Aternos",
                url=ATERNOS_URL
            )
        )

        bot.send_message(
            chat_id,
            "⏹️ <b>إيقاف السيرفر</b>\n\n"
            "هذا الإصدار لا ينفذ Stop عبر API غير رسمي.\n\n"
            "بعد الإيقاف يمكنك الضغط على "
            "<b>📊 حالة السيرفر</b> للتأكد من أنه أصبح Offline.",
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
                "🌐 فتح لوحة Aternos",
                url=ATERNOS_URL
            )
        )

        bot.send_message(
            chat_id,
            "🔄 <b>Restart</b>\n\n"
            "لا يوجد API رسمي من Aternos لتنفيذ Restart "
            "من خارج اللوحة.\n\n"
            "لن أدعي أن العملية تمت وهي لم تتم.",
            reply_markup=markup
        )

        return


# ============================================================
# /IP
# ============================================================

@bot.message_handler(commands=["ip"])
def ip_command(message):
    """
    يعرض عنوان السيرفر.
    """

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
    """
    قائمة أوامر البوت.
    """

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
# UNKNOWN TEXT
# ============================================================

@bot.message_handler(
    func=lambda message: True,
    content_types=["text"]
)
def text_handler(message):
    """
    معالجة الرسائل النصية العامة.
    """

    text = message.text.strip().lower()

    if text in ["status", "الحالة", "حالة السيرفر"]:
        status_command(message)
        return

    if text in ["ip", "الاى بي", "الاي بي"]:
        ip_command(message)
        return

    bot.send_message(
        message.chat.id,
        "استخدم /start لفتح لوحة التحكم."
    )


# ============================================================
# HEALTH SERVER FOR RENDER
# ============================================================

class HealthHandler(BaseHTTPRequestHandler):
    """
    HTTP endpoint بسيط حتى يبقى Web Service صحيًا على Render.
    """

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
    """
    تشغيل HTTP server على PORT الخاص بـRender.
    """

    server = HTTPServer(
        ("0.0.0.0", PORT),
        HealthHandler
    )

    server.serve_forever()


# ============================================================
# TELEGRAM POLLING
# ============================================================

def run_bot():
    """
    تشغيل Telegram polling مع إعادة المحاولة عند انقطاع الاتصال.
    """

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

    print(
        "========================================"
    )

    print(
        "Minecraft Telegram Bot"
    )

    print(
        f"Default server: "
        f"{DEFAULT_SERVER_HOST}:{DEFAULT_SERVER_PORT}"
    )

    print(
        "python-aternos: DISABLED"
    )

    print(
        "Real Minecraft status: ENABLED"
    )

    print(
        "========================================"
    )

    # Web health server
    health_thread = threading.Thread(
        target=run_health_server,
        daemon=True
    )

    health_thread.start()

    # Telegram
    run_bot()
