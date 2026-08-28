import os
import re
import time
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import telebot
from telebot import types
from mcstatus import JavaServer, BedrockServer

# ============================================================
# ATERNOS
# ============================================================

try:
    from python_aternos import Client as AternosClient
    ATERNOS_LIBRARY_AVAILABLE = True
except ImportError:
    AternosClient = None
    ATERNOS_LIBRARY_AVAILABLE = False


# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

ATERNOS_USERNAME = os.getenv(
    "ATERNOS_USERNAME",
    ""
).strip()

ATERNOS_PASSWORD = os.getenv(
    "ATERNOS_PASSWORD",
    ""
).strip()

ATERNOS_URL = os.getenv(
    "ATERNOS_URL",
    "https://aternos.org/server/"
).strip()

DEFAULT_SERVER_HOST = os.getenv(
    "MC_SERVER_HOST",
    "MACESMP37.aternos.me"
).strip()

DEFAULT_SERVER_PORT = int(
    os.getenv(
        "MC_SERVER_PORT",
        "25565"
    )
)

PORT = int(
    os.getenv(
        "PORT",
        "10000"
    )
)

STATUS_TIMEOUT = float(
    os.getenv(
        "STATUS_TIMEOUT",
        "5"
    )
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
# STORAGE
# ============================================================

user_servers = {}

user_lock = threading.Lock()

aternos_lock = threading.Lock()

aternos_client = None
aternos_account = None


# ============================================================
# SERVER STORAGE
# ============================================================

def get_user_server(chat_id):
    with user_lock:
        server = user_servers.get(
            chat_id,
            {
                "host": DEFAULT_SERVER_HOST,
                "port": DEFAULT_SERVER_PORT
            }
        )

        return server.copy()


def save_user_server(
    chat_id,
    host,
    port
):
    with user_lock:
        user_servers[chat_id] = {
            "host": host,
            "port": int(port)
        }


# ============================================================
# ADDRESS
# ============================================================

def clean_host(host):
    host = str(
        host or ""
    ).strip()

    host = re.sub(
        r"^https?://",
        "",
        host,
        flags=re.IGNORECASE
    )

    host = host.split("/")[0].strip()

    return host


def parse_server_address(address):

    address = clean_host(address)

    if not address:
        raise ValueError(
            "عنوان السيرفر فارغ"
        )

    # IPv6
    if address.startswith("["):

        match = re.match(
            r"^\[([^\]]+)\](?::(\d+))?$",
            address
        )

        if match:

            host = match.group(1)

            port = int(
                match.group(2) or 25565
            )

            return host, port

    parts = address.rsplit(
        ":",
        1
    )

    if (
        len(parts) == 2
        and parts[1].isdigit()
    ):

        port = int(
            parts[1]
        )

        if not 1 <= port <= 65535:
            raise ValueError(
                "المنفذ يجب أن يكون بين 1 و 65535"
            )

        return parts[0], port

    return address, 25565


# ============================================================
# ATERNOS LOGIN
# ============================================================

def get_aternos_account():

    global aternos_client
    global aternos_account

    if not ATERNOS_LIBRARY_AVAILABLE:
        raise RuntimeError(
            "python-aternos غير مثبت."
        )

    if not ATERNOS_USERNAME:
        raise RuntimeError(
            "ATERNOS_USERNAME غير موجود."
        )

    if not ATERNOS_PASSWORD:
        raise RuntimeError(
            "ATERNOS_PASSWORD غير موجود."
        )

    with aternos_lock:

        if aternos_account is not None:
            return aternos_account

        print(
            "Logging into Aternos..."
        )

        client = AternosClient()

        client.login(
            ATERNOS_USERNAME,
            ATERNOS_PASSWORD
        )

        aternos_client = client
        aternos_account = client.account

        print(
            "Aternos login successful."
        )

        return aternos_account


# ============================================================
# FIND ATERNOS SERVER
# ============================================================

def get_aternos_server(
    target_host=None
):

    account = get_aternos_account()

    servers = account.list_servers()

    if not servers:
        raise RuntimeError(
            "لم يتم العثور على أي سيرفر في حساب Aternos."
        )

    if not target_host:
        target_host = DEFAULT_SERVER_HOST

    target_host = clean_host(
        target_host
    ).lower()

    # البحث بالعنوان
    for server in servers:

        try:
            address = clean_host(
                getattr(
                    server,
                    "address",
                    ""
                )
            ).lower()

            if address == target_host:
                return server

        except Exception:
            pass

    # محاولة البحث بالاسم/العنوان بشكل أوسع
    for server in servers:

        try:

            address = str(
                getattr(
                    server,
                    "address",
                    ""
                )
            ).lower()

            name = str(
                getattr(
                    server,
                    "name",
                    ""
                )
            ).lower()

            if (
                target_host in address
                or target_host in name
            ):
                return server

        except Exception:
            pass

    raise RuntimeError(
        "لم أجد السيرفر "
        f"{target_host} داخل حساب Aternos."
    )


# ============================================================
# ATERNOS START
# ============================================================

def aternos_start(
    target_host=None
):

    server = get_aternos_server(
        target_host
    )

    print(
        f"Starting Aternos server: "
        f"{getattr(server, 'address', 'unknown')}"
    )

    result = server.start()

    return {
        "success": True,
        "message": "تم إرسال أمر تشغيل السيرفر إلى Aternos.",
        "result": result
    }


# ============================================================
# ATERNOS STOP
# ============================================================

def aternos_stop(
    target_host=None
):

    server = get_aternos_server(
        target_host
    )

    print(
        f"Stopping Aternos server: "
        f"{getattr(server, 'address', 'unknown')}"
    )

    result = server.stop()

    return {
        "success": True,
        "message": "تم إرسال أمر إيقاف السيرفر إلى Aternos.",
        "result": result
    }


# ============================================================
# ATERNOS RESTART
# ============================================================

def aternos_restart(
    target_host=None
):

    server = get_aternos_server(
        target_host
    )

    print(
        f"Restarting Aternos server: "
        f"{getattr(server, 'address', 'unknown')}"
    )

    # بعض إصدارات المكتبة توفر restart()
    restart_method = getattr(
        server,
        "restart",
        None
    )

    if callable(restart_method):

        result = restart_method()

        return {
            "success": True,
            "message": "تم إرسال أمر Restart إلى Aternos.",
            "result": result
        }

    # fallback:
    # Stop ثم انتظار قصير ثم Start
    stop_method = getattr(
        server,
        "stop",
        None
    )

    start_method = getattr(
        server,
        "start",
        None
    )

    if not callable(stop_method):
        raise RuntimeError(
            "دالة Stop غير متوفرة في مكتبة Aternos."
        )

    if not callable(start_method):
        raise RuntimeError(
            "دالة Start غير متوفرة في مكتبة Aternos."
        )

    stop_method()

    time.sleep(3)

    start_method()

    return {
        "success": True,
        "message": (
            "تم تنفيذ Restart "
            "عن طريق Stop ثم Start."
        )
    }


# ============================================================
# MINECRAFT JAVA STATUS
# ============================================================

def get_java_status(
    host,
    port
):

    server = JavaServer(
        host,
        port,
        timeout=STATUS_TIMEOUT
    )

    result = server.status(
        tries=2
    )

    players_online = 0
    players_max = 0
    version = "غير معروف"

    try:
        players_online = int(
            result.players.online
        )
    except Exception:
        pass

    try:
        players_max = int(
            result.players.max
        )
    except Exception:
        pass

    try:
        version = str(
            result.version.name
            or "غير معروف"
        )
    except Exception:
        pass

    try:
        latency = round(
            float(result.latency)
        )
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
# MINECRAFT BEDROCK STATUS
# ============================================================

def get_bedrock_status(
    host,
    port
):

    server = BedrockServer(
        host,
        port,
        timeout=STATUS_TIMEOUT
    )

    result = server.status(
        tries=2
    )

    players_online = 0
    players_max = 0
    version = "غير معروف"

    try:
        players_online = int(
            result.players.online
        )
    except Exception:
        pass

    try:
        players_max = int(
            result.players.max
        )
    except Exception:
        pass

    try:
        version = str(
            result.version.name
            or "غير معروف"
        )
    except Exception:
        pass

    try:
        latency = round(
            float(result.latency)
        )
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
# REAL SERVER STATUS
# ============================================================

def get_real_server_status(
    host,
    port=25565
):

    host = clean_host(
        host
    )

    java_error = None

    # Java
    try:
        return get_java_status(
            host,
            port
        )

    except Exception as exc:
        java_error = exc

    # Bedrock على نفس المنفذ
    try:
        return get_bedrock_status(
            host,
            port
        )

    except Exception:
        pass

    # Bedrock default
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
        "error": str(
            java_error or
            "Server offline"
        )
    }


# ============================================================
# FORMAT STATUS
# ============================================================

def format_status(data):

    if not data["online"]:

        return (
            "🔴 <b>السيرفر Offline</b>\n\n"
            "🌐 العنوان:\n"
            f"<code>{data['host']}:{data['port']}</code>\n\n"
            "📡 لم يستجب السيرفر."
        )

    latency = data.get(
        "latency"
    )

    if latency is None:
        ping = "غير معروف"
    else:
        ping = f"{latency}ms"

    version = (
        data.get("version")
        or "غير معروف"
    )

    return (
        "🟢 <b>السيرفر Online</b>\n\n"
        f"👥 اللاعبين: "
        f"<b>{data['players']}/"
        f"{data['max_players']}</b>\n"
        f"📶 Ping: <b>{ping}</b>\n"
        f"🎮 الإصدار: "
        f"<b>{version}</b>\n"
        f"🧩 النوع: "
        f"<b>{data['edition']}</b>\n"
        "🌐 العنوان:\n"
        f"<code>{data['host']}:"
        f"{data['port']}</code>"
    )


# ============================================================
# KEYBOARD
# ============================================================

def main_keyboard():

    markup = types.InlineKeyboardMarkup(
        row_width=2
    )

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

@bot.message_handler(
    commands=["start"]
)
def start_command(message):

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

    text = (
        "🤖 <b>بوت إدارة سيرفر Minecraft</b>\n\n"
        f"{format_status(status)}\n\n"
        "اختر العملية:"
    )

    try:

        bot.edit_message_text(
            text,
            message.chat.id,
            msg.message_id,
            reply_markup=main_keyboard()
        )

    except Exception:

        bot.send_message(
            message.chat.id,
            text,
            reply_markup=main_keyboard()
        )


# ============================================================
# /STATUS
# ============================================================

@bot.message_handler(
    commands=[
        "status",
        "serverstatus"
    ]
)
def status_command(message):

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

@bot.message_handler(
    commands=["server"]
)
def server_command(message):

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

    try:

        if not message.text:
            raise ValueError(
                "لم يتم إرسال عنوان."
            )

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
            "🔎 جاري التحقق..."
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
# CALLBACK HANDLER
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

    server = get_user_server(
        chat_id
    )

    host = server["host"]

    # ========================================================
    # STATUS
    # ========================================================

    if call.data == "server_status":

        status = get_real_server_status(
            host,
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

    # ========================================================
    # START
    # ========================================================

    if call.data == "aternos_start":

        status_msg = bot.send_message(
            chat_id,
            "▶️ <b>جاري تشغيل السيرفر...</b>\n\n"
            "⏳ يتم الاتصال بحساب Aternos..."
        )

        try:

            result = aternos_start(
                host
            )

            bot.edit_message_text(
                "✅ <b>تم إرسال أمر التشغيل.</b>\n\n"
                "⏳ Aternos يحتاج بعض الوقت حتى يبدأ السيرفر.\n"
                "اضغط 📊 حالة السيرفر بعد قليل للتحقق من الحالة الحقيقية.",
                chat_id,
                status_msg.message_id,
                reply_markup=main_keyboard()
            )

        except Exception as exc:

            bot.edit_message_text(
                "❌ <b>فشل تشغيل السيرفر</b>\n\n"
                f"<code>{str(exc)[:1000]}</code>",
                chat_id,
                status_msg.message_id,
                reply_markup=main_keyboard()
            )

        return

    # ========================================================
    # STOP
    # ========================================================

    if call.data == "server_stop":

        status_msg = bot.send_message(
            chat_id,
            "⏹️ <b>جاري إيقاف السيرفر...</b>\n\n"
            "⏳ يتم الاتصال بحساب Aternos..."
        )

        try:

            result = aternos_stop(
                host
            )

            bot.edit_message_text(
                "✅ <b>تم إرسال أمر الإيقاف.</b>\n\n"
                "اضغط 📊 حالة السيرفر للتأكد من أنه أصبح Offline.",
                chat_id,
                status_msg.message_id,
                reply_markup=main_keyboard()
            )

        except Exception as exc:

            bot.edit_message_text(
                "❌ <b>فشل إيقاف السيرفر</b>\n\n"
                f"<code>{str(exc)[:1000]}</code>",
                chat_id,
                status_msg.message_id,
                reply_markup=main_keyboard()
            )

        return

    # ========================================================
    # RESTART
    # ========================================================

    if call.data == "server_restart":

        status_msg = bot.send_message(
            chat_id,
            "🔄 <b>جاري Restart للسيرفر...</b>\n\n"
            "⏳ يتم الاتصال بحساب Aternos..."
        )

        try:

            result = aternos_restart(
                host
            )

            bot.edit_message_text(
                "✅ <b>تم إرسال أمر Restart.</b>\n\n"
                "⏳ انتظر حتى يبدأ السيرفر من جديد.\n"
                "ثم اضغط 📊 حالة السيرفر للتحقق.",
                chat_id,
                status_msg.message_id,
                reply_markup=main_keyboard()
            )

        except Exception as exc:

            bot.edit_message_text(
                "❌ <b>فشل Restart</b>\n\n"
                f"<code>{str(exc)[:1000]}</code>",
                chat_id,
                status_msg.message_id,
                reply_markup=main_keyboard()
            )

        return


# ============================================================
# /IP
# ============================================================

@bot.message_handler(
    commands=["ip"]
)
def ip_command(message):

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

@bot.message_handler(
    commands=["help"]
)
def help_command(message):

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

    text = (
        message.text or ""
    ).strip().lower()

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
# RENDER HEALTH CHECK
# ============================================================

class HealthHandler(
    BaseHTTPRequestHandler
):

    def do_GET(self):

        self.send_response(
            200
        )

        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8"
        )

        self.end_headers()

        self.wfile.write(
            b"Telegram Minecraft Bot is running."
        )

    def log_message(
        self,
        format,
        *args
    ):
        return


def run_health_server():

    server = ThreadingHTTPServer(
        (
            "0.0.0.0",
            PORT
        ),
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

    while True:

        try:

            print(
                "Telegram bot started."
            )

            bot.infinity_polling(
                timeout=30,
                long_polling_timeout=30,
                skip_pending=True
            )

        except Exception as exc:

            print(
                "Telegram polling error:",
                exc
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
        f"{DEFAULT_SERVER_HOST}:"
        f"{DEFAULT_SERVER_PORT}"
    )

    print(
        "Aternos account control: ENABLED"
    )

    print(
        "Real Minecraft status: ENABLED"
    )

    print(
        "========================================"
    )

    health_thread = threading.Thread(
        target=run_health_server,
        daemon=True
    )

    health_thread.start()

    run_bot()
