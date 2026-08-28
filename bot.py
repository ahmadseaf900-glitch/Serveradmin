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
except ImportError:
    AternosClient = None


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
    "https://aternos.org/"
).strip()

DEFAULT_SERVER_HOST = os.getenv(
    "MC_SERVER_HOST",
    "MACESMP37.aternos.me"
).strip()

DEFAULT_SERVER_PORT = int(
    os.getenv("MC_SERVER_PORT", "25565")
)

STATUS_TIMEOUT = float(
    os.getenv("STATUS_TIMEOUT", "5")
)

PORT = int(
    os.getenv("PORT", "10000")
)


if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN غير موجود في Environment Variables"
    )


# ============================================================
# TELEGRAM
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
aternos_server = None


# ============================================================
# SERVER STORAGE
# ============================================================

def get_user_server(chat_id):

    with user_lock:

        return user_servers.get(
            chat_id,
            {
                "host": DEFAULT_SERVER_HOST,
                "port": DEFAULT_SERVER_PORT
            }
        ).copy()


def save_user_server(chat_id, host, port):

    with user_lock:

        user_servers[chat_id] = {
            "host": host,
            "port": int(port)
        }


# ============================================================
# ADDRESS
# ============================================================

def clean_host(host):

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

    address = clean_host(address)

    if not address:
        raise ValueError(
            "عنوان السيرفر فارغ"
        )

    if address.startswith("["):

        match = re.match(
            r"^\[([^\]]+)\](?::(\d+))?$",
            address
        )

        if match:

            return (
                match.group(1),
                int(match.group(2) or 25565)
            )

    parts = address.rsplit(":", 1)

    if len(parts) == 2 and parts[1].isdigit():

        port = int(parts[1])

        if not 1 <= port <= 65535:
            raise ValueError(
                "المنفذ يجب أن يكون بين 1 و 65535"
            )

        return parts[0], port

    return address, 25565


# ============================================================
# ATERNOS LOGIN
# ============================================================

def get_aternos_server():

    global aternos_client
    global aternos_account
    global aternos_server

    if not ATERNOS_USERNAME:
        raise RuntimeError(
            "ATERNOS_USERNAME غير موجود"
        )

    if not ATERNOS_PASSWORD:
        raise RuntimeError(
            "ATERNOS_PASSWORD غير موجود"
        )

    if AternosClient is None:
        raise RuntimeError(
            "python-aternos غير مثبت. "
            "أضفه إلى requirements.txt"
        )

    with aternos_lock:

        # إذا كان لدينا اتصال سابق
        if aternos_server is not None:
            return aternos_server

        print(
            "Logging into Aternos..."
        )

        client = AternosClient()

        client.login(
            ATERNOS_USERNAME,
            ATERNOS_PASSWORD
        )

        account = client.account

        servers = account.list_servers()

        if not servers:
            raise RuntimeError(
                "لم يتم العثور على أي سيرفر في حساب Aternos"
            )

        wanted_host = clean_host(
            DEFAULT_SERVER_HOST
        ).lower()

        selected = None

        # البحث حسب العنوان
        for server in servers:

            try:

                address = clean_host(
                    getattr(
                        server,
                        "address",
                        ""
                    )
                ).lower()

                if address == wanted_host:

                    selected = server
                    break

            except Exception:
                pass

        # إذا لم نجد العنوان، نستخدم أول سيرفر
        if selected is None:

            selected = servers[0]

            print(
                "WARNING: MC_SERVER_HOST "
                "لم يطابق سيرفر Aternos. "
                "تم استخدام أول سيرفر."
            )

        aternos_client = client
        aternos_account = account
        aternos_server = selected

        print(
            "Aternos login successful."
        )

        print(
            "Selected Aternos server:",
            getattr(
                selected,
                "address",
                "unknown"
            )
        )

        return aternos_server


# ============================================================
# ATERNOS SERVER INFO
# ============================================================

def aternos_status():

    server = get_aternos_server()

    try:
        return str(
            server.status
        ).lower()
    except Exception:
        return "unknown"


# ============================================================
# ATERNOS START
# ============================================================

def aternos_start():

    server = get_aternos_server()

    status = aternos_status()

    print(
        "Aternos status before start:",
        status
    )

    if status in [
        "online",
        "loading",
        "preparing",
        "starting"
    ]:
        return {
            "success": True,
            "message": (
                "السيرفر يعمل بالفعل أو قيد التشغيل."
            )
        }

    print(
        "Sending Aternos START..."
    )

    result = server.start(
        headstart=False,
        accepteula=True
    )

    return {
        "success": True,
        "message": (
            "تم إرسال أمر تشغيل السيرفر إلى Aternos."
        ),
        "result": str(result)
    }


# ============================================================
# ATERNOS STOP
# ============================================================

def aternos_stop():

    server = get_aternos_server()

    status = aternos_status()

    print(
        "Aternos status before stop:",
        status
    )

    if status == "offline":
        return {
            "success": True,
            "message": (
                "السيرفر متوقف بالفعل."
            )
        }

    print(
        "Sending Aternos STOP..."
    )

    result = server.stop()

    return {
        "success": True,
        "message": (
            "تم إرسال أمر إيقاف السيرفر إلى Aternos."
        ),
        "result": str(result)
    }


# ============================================================
# ATERNOS RESTART
# ============================================================

def aternos_restart():

    server = get_aternos_server()

    print(
        "Sending Aternos RESTART..."
    )

    result = server.restart()

    return {
        "success": True,
        "message": (
            "تم إرسال أمر Restart إلى Aternos."
        ),
        "result": str(result)
    }


# ============================================================
# REAL MINECRAFT STATUS
# ============================================================

def get_java_status(host, port):

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
            result.version.name or "غير معروف"
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


def get_bedrock_status(host, port):

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
            result.version.name or "غير معروف"
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


def get_real_server_status(host, port):

    host = clean_host(host)

    try:

        return get_java_status(
            host,
            port
        )

    except Exception:
        pass

    try:

        return get_bedrock_status(
            host,
            port
        )

    except Exception:
        pass

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
        "version": None
    }


# ============================================================
# FORMAT STATUS
# ============================================================

def format_status(data):

    if not data["online"]:

        return (
            "🔴 <b>السيرفر Offline</b>\n\n"
            f"🌐 العنوان:\n"
            f"<code>{data['host']}:{data['port']}</code>\n\n"
            "📡 السيرفر لا يستجيب حاليًا."
        )

    latency = data.get("latency")

    ping = (
        "غير معروف"
        if latency is None
        else f"{latency}ms"
    )

    version = (
        data.get("version")
        or "غير معروف"
    )

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

    markup = types.InlineKeyboardMarkup(
        row_width=2
    )

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
            "🔐 Whitelist",
            callback_data="whitelist"
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

    status = get_real_server_status(
        server["host"],
        server["port"]
    )

    bot.send_message(

        message.chat.id,

        "🤖 <b>بوت إدارة سيرفر Minecraft</b>\n\n"
        f"{format_status(status)}\n\n"
        "اختر العملية:",

        reply_markup=main_keyboard()
    )


# ============================================================
# STATUS
# ============================================================

def send_status(chat_id):

    server = get_user_server(
        chat_id
    )

    status = get_real_server_status(
        server["host"],
        server["port"]
    )

    bot.send_message(
        chat_id,
        format_status(status),
        reply_markup=main_keyboard()
    )


@bot.message_handler(
    commands=["status", "serverstatus"]
)
def status_command(message):

    send_status(
        message.chat.id
    )


# ============================================================
# CALLBACKS
# ============================================================

@bot.callback_query_handler(
    func=lambda call: True
)
def callback_handler(call):

    chat_id = call.message.chat.id

    try:

        bot.answer_callback_query(
            call.id,
            "جاري التنفيذ..."
        )

    except Exception:
        pass


    # ========================================================
    # STATUS
    # ========================================================

    if call.data == "server_status":

        try:

            send_status(
                chat_id
            )

        except Exception as exc:

            bot.send_message(
                chat_id,
                "❌ فشل فحص الحالة:\n"
                f"<code>{str(exc)[:500]}</code>"
            )

        return


    # ========================================================
    # START
    # ========================================================

    if call.data == "aternos_start":

        bot.send_message(
            chat_id,
            "▶️ <b>جاري تشغيل السيرفر...</b>"
        )

        try:

            result = aternos_start()

            bot.send_message(
                chat_id,
                "✅ <b>تم إرسال أمر Start إلى Aternos.</b>\n\n"
                f"{result['message']}\n\n"
                "⏳ انتظر قليلًا ثم اضغط Status "
                "لمعرفة الحالة الحقيقية.",
                reply_markup=main_keyboard()
            )

        except Exception as exc:

            bot.send_message(
                chat_id,
                "❌ <b>فشل تشغيل السيرفر</b>\n\n"
                f"<code>{str(exc)[:1000]}</code>",
                reply_markup=main_keyboard()
            )

        return


    # ========================================================
    # STOP
    # ========================================================

    if call.data == "aternos_stop":

        bot.send_message(
            chat_id,
            "⏹️ <b>جاري إيقاف السيرفر...</b>"
        )

        try:

            result = aternos_stop()

            bot.send_message(
                chat_id,
                "✅ <b>تم إرسال أمر Stop إلى Aternos.</b>\n\n"
                f"{result['message']}\n\n"
                "اضغط Status للتأكد من الحالة.",
                reply_markup=main_keyboard()
            )

        except Exception as exc:

            bot.send_message(
                chat_id,
                "❌ <b>فشل إيقاف السيرفر</b>\n\n"
                f"<code>{str(exc)[:1000]}</code>",
                reply_markup=main_keyboard()
            )

        return


    # ========================================================
    # RESTART
    # ========================================================

    if call.data == "aternos_restart":

        bot.send_message(
            chat_id,
            "🔄 <b>جاري إعادة تشغيل السيرفر...</b>"
        )

        try:

            result = aternos_restart()

            bot.send_message(
                chat_id,
                "✅ <b>تم إرسال أمر Restart إلى Aternos.</b>\n\n"
                f"{result['message']}\n\n"
                "اضغط Status بعد قليل للتأكد.",
                reply_markup=main_keyboard()
            )

        except Exception as exc:

            bot.send_message(
                chat_id,
                "❌ <b>فشل Restart</b>\n\n"
                f"<code>{str(exc)[:1000]}</code>",
                reply_markup=main_keyboard()
            )

        return


    # ========================================================
    # CONSOLE
    # ========================================================

    if call.data == "console":

        bot.send_message(
            chat_id,
            "🖥️ <b>Console</b>\n\n"
            "ميزة Console تبقى مرتبطة بنظام DiscordSRV "
            "الذي ربطناه مع البوت.\n\n"
            "إذا كان Discord Bot متصلًا، "
            "سيتم تمرير أوامر Console من خلاله."
        )

        return


    # ========================================================
    # PLAYERS
    # ========================================================

    if call.data == "players":

        server = get_user_server(
            chat_id
        )

        status = get_real_server_status(
            server["host"],
            server["port"]
        )

        if not status["online"]:

            bot.send_message(
                chat_id,
                "👥 <b>Players</b>\n\n"
                "🔴 السيرفر Offline."
            )

            return

        bot.send_message(
            chat_id,
            "👥 <b>Players</b>\n\n"
            f"عدد اللاعبين: "
            f"<b>{status['players']}/{status['max_players']}</b>\n\n"
            "لعرض أسماء اللاعبين، يجب ربط "
            "مصدر بيانات اللاعبين من DiscordSRV/Console."
        )

        return


    # ========================================================
    # WHITELIST
    # ========================================================

    if call.data == "whitelist":

        bot.send_message(
            chat_id,
            "🔐 <b>Whitelist</b>\n\n"
            "ميزة Whitelist مرتبطة بنظام DiscordSRV "
            "والـ Console.\n\n"
            "يمكنك من هنا تجهيز أوامر الإضافة والحذف "
            "ليتم إرسالها إلى السيرفر عبر نظام الربط."
        )

        return


# ============================================================
# SERVER COMMAND
# ============================================================

@bot.message_handler(
    commands=["server"]
)
def server_command(message):

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

    try:

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
            f"<code>{host}:{port}</code>"
        )

        send_status(
            message.chat.id
        )

    except Exception as exc:

        bot.send_message(
            message.chat.id,
            "❌ فشل حفظ السيرفر:\n"
            f"<code>{str(exc)[:500]}</code>"
        )


# ============================================================
# IP
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
        "🌐 <b>Server Address</b>\n\n"
        f"<code>{server['host']}:{server['port']}</code>"
    )


# ============================================================
# HELP
# ============================================================

@bot.message_handler(
    commands=["help"]
)
def help_command(message):

    bot.send_message(
        message.chat.id,
        "📚 <b>أوامر البوت</b>\n\n"
        "/start\n"
        "/status\n"
        "/server\n"
        "/ip\n"
        "/help\n\n"
        "الأزرار:\n"
        "▶️ Start\n"
        "⏹️ Stop\n"
        "🔄 Restart\n"
        "📊 Status\n"
        "🖥️ Console\n"
        "👥 Players\n"
        "🔐 Whitelist"
    )


# ============================================================
# HEALTH SERVER
# ============================================================

class HealthHandler(
    BaseHTTPRequestHandler
):

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

    def log_message(
        self,
        format,
        *args
    ):
        return


def run_health_server():

    server = ThreadingHTTPServer(
        ("0.0.0.0", PORT),
        HealthHandler
    )

    print(
        f"Health server running on {PORT}"
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
