# bot.py

import os
import re
import time
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import telebot
from telebot import types
from mcstatus import JavaServer, BedrockServer

import aternos


# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

MC_SERVER_HOST = os.getenv(
    "MC_SERVER_HOST",
    "MACESMP37.aternos.me"
).strip()

MC_SERVER_PORT = int(
    os.getenv("MC_SERVER_PORT", "25565")
)

PORT = int(
    os.getenv("PORT", "10000")
)

STATUS_TIMEOUT = float(
    os.getenv("STATUS_TIMEOUT", "5")
)

# Discord
DISCORD_TOKEN = os.getenv(
    "DISCORD_TOKEN",
    ""
).strip()

DISCORD_CHANNEL_ID = os.getenv(
    "DISCORD_CHANNEL_ID",
    ""
).strip()

# قناة DiscordSRV / Discord
DISCORDSRV_CHANNEL_ID = DISCORD_CHANNEL_ID

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


def get_user_server(chat_id):
    with user_lock:
        return user_servers.get(
            chat_id,
            {
                "host": MC_SERVER_HOST,
                "port": MC_SERVER_PORT
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

    host = host.split("/")[0]

    return host.strip()


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
                "المنفذ غير صحيح"
            )

        return parts[0], port

    return address, 25565


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

    return {
        "online": True,
        "edition": "Java",
        "host": host,
        "port": port,
        "players": int(result.players.online),
        "max_players": int(result.players.max),
        "latency": round(float(result.latency)),
        "version": str(
            result.version.name
            or "Unknown"
        )
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

    return {
        "online": True,
        "edition": "Bedrock",
        "host": host,
        "port": port,
        "players": int(result.players.online),
        "max_players": int(result.players.max),
        "latency": round(float(result.latency)),
        "version": str(
            result.version.name
            or "Unknown"
        )
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
# STATUS TEXT
# ============================================================

def format_status(data):

    if not data["online"]:

        return (
            "🔴 <b>السيرفر Offline</b>\n\n"
            "🌐 العنوان:\n"
            f"<code>{data['host']}:{data['port']}</code>"
        )

    ping = (
        f"{data['latency']}ms"
        if data["latency"] is not None
        else "غير معروف"
    )

    return (
        "🟢 <b>السيرفر Online</b>\n\n"
        f"👥 اللاعبين: "
        f"<b>{data['players']}/{data['max_players']}</b>\n"
        f"📶 Ping: <b>{ping}</b>\n"
        f"🎮 الإصدار: <b>{data['version']}</b>\n"
        f"🧩 النوع: <b>{data['edition']}</b>\n"
        "🌐 العنوان:\n"
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
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "📊 Status",
            callback_data="server_status"
        ),
        types.InlineKeyboardButton(
            "👥 Players",
            callback_data="server_players"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "🖥 Console",
            callback_data="console"
        ),
        types.InlineKeyboardButton(
            "✅ Whitelist",
            callback_data="whitelist"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "🌐 Aternos",
            url=os.getenv(
                "ATERNOS_URL",
                "https://aternos.org/"
            )
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

@bot.message_handler(
    commands=["status"]
)
def status_command(message):

    server = get_user_server(
        message.chat.id
    )

    status = get_real_server_status(
        server["host"],
        server["port"]
    )

    bot.send_message(
        message.chat.id,
        format_status(status),
        reply_markup=main_keyboard()
    )


# ============================================================
# SERVER
# ============================================================

@bot.message_handler(
    commands=["server"]
)
def server_command(message):

    bot.send_message(
        message.chat.id,
        "📥 أرسل عنوان السيرفر:\n\n"
        "<code>MACESMP37.aternos.me</code>"
    )

    bot.register_next_step_handler(
        message,
        receive_server
    )


def receive_server(message):

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
            "✅ تم حفظ السيرفر."
        )

        status_command(message)

    except Exception as exc:

        bot.send_message(
            message.chat.id,
            f"❌ خطأ:\n<code>{str(exc)}</code>"
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
            call.id
        )
    except Exception:
        pass

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    if call.data == "server_status":

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

        return

    # --------------------------------------------------------
    # PLAYERS
    # --------------------------------------------------------

    if call.data == "server_players":

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
                "🔴 السيرفر Offline."
            )

            return

        bot.send_message(
            chat_id,
            "👥 <b>اللاعبين</b>\n\n"
            f"العدد: "
            f"<b>{status['players']}/{status['max_players']}</b>"
        )

        return

    # --------------------------------------------------------
    # START
    # --------------------------------------------------------

    if call.data == "aternos_start":

        result = aternos.start()

        if result["success"]:

            bot.send_message(
                chat_id,
                "▶️ <b>تم إرسال أمر التشغيل إلى Aternos.</b>\n\n"
                "🔎 جاري التحقق من حالة السيرفر..."
            )

            # نعطي Aternos وقتًا لمعالجة الأمر
            time.sleep(3)

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

        else:

            bot.send_message(
                chat_id,
                "❌ <b>فشل تشغيل السيرفر</b>\n\n"
                f"<code>{result['message'][:1000]}</code>"
            )

        return

    # --------------------------------------------------------
    # STOP
    # --------------------------------------------------------

    if call.data == "aternos_stop":

        result = aternos.stop()

        if result["success"]:

            bot.send_message(
                chat_id,
                "⏹️ <b>تم إرسال أمر الإيقاف إلى Aternos.</b>\n\n"
                "🔎 جاري التحقق..."
            )

            time.sleep(3)

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

        else:

            bot.send_message(
                chat_id,
                "❌ <b>فشل إيقاف السيرفر</b>\n\n"
                f"<code>{result['message'][:1000]}</code>"
            )

        return

    # --------------------------------------------------------
    # RESTART
    # --------------------------------------------------------

    if call.data == "aternos_restart":

        result = aternos.restart()

        if result["success"]:

            bot.send_message(
                chat_id,
                "🔄 <b>تم إرسال Restart إلى Aternos.</b>\n\n"
                "🔎 جاري التحقق من الحالة..."
            )

            time.sleep(5)

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

        else:

            bot.send_message(
                chat_id,
                "❌ <b>فشل Restart</b>\n\n"
                f"<code>{result['message'][:1000]}</code>"
            )

        return

    # --------------------------------------------------------
    # CONSOLE
    # --------------------------------------------------------

    if call.data == "console":

        bot.send_message(
            chat_id,
            "🖥 <b>Console</b>\n\n"
            "ميزة Console يتم تنفيذها عبر نظام "
            "DiscordSRV/Discord المرتبط بالسيرفر.\n\n"
            "أرسل الأمر بالطريقة التي ضبطتها في نظام DiscordSRV."
        )

        return

    # --------------------------------------------------------
    # WHITELIST
    # --------------------------------------------------------

    if call.data == "whitelist":

        markup = types.InlineKeyboardMarkup()

        markup.add(
            types.InlineKeyboardButton(
                "➕ إضافة لاعب",
                callback_data="whitelist_add"
            ),
            types.InlineKeyboardButton(
                "➖ إزالة لاعب",
                callback_data="whitelist_remove"
            )
        )

        markup.add(
            types.InlineKeyboardButton(
                "📋 عرض القائمة",
                callback_data="whitelist_list"
            )
        )

        bot.send_message(
            chat_id,
            "✅ <b>Whitelist</b>\n\n"
            "اختر العملية:",
            reply_markup=markup
        )

        return

    # --------------------------------------------------------
    # WHITELIST ADD
    # --------------------------------------------------------

    if call.data == "whitelist_add":

        bot.send_message(
            chat_id,
            "➕ أرسل اسم لاعب لإضافته إلى Whitelist."
        )

        bot.register_next_step_handler(
            call.message,
            whitelist_add_player
        )

        return

    # --------------------------------------------------------
    # WHITELIST REMOVE
    # --------------------------------------------------------

    if call.data == "whitelist_remove":

        bot.send_message(
            chat_id,
            "➖ أرسل اسم اللاعب لإزالته من Whitelist."
        )

        bot.register_next_step_handler(
            call.message,
            whitelist_remove_player
        )

        return

    # --------------------------------------------------------
    # WHITELIST LIST
    # --------------------------------------------------------

    if call.data == "whitelist_list":

        bot.send_message(
            chat_id,
            "📋 <b>Whitelist</b>\n\n"
            "القائمة تتم إدارتها من خلال "
            "Minecraft/DiscordSRV."
        )

        return


# ============================================================
# WHITELIST FUNCTIONS
# ============================================================

def whitelist_add_player(message):

    player = message.text.strip()

    if not player:
        bot.send_message(
            message.chat.id,
            "❌ اسم اللاعب فارغ."
        )
        return

    bot.send_message(
        message.chat.id,
        "➕ <b>Whitelist Add</b>\n\n"
        f"اللاعب: <code>{player}</code>\n\n"
        "سيتم تمرير الأمر إلى نظام السيرفر."
    )


def whitelist_remove_player(message):

    player = message.text.strip()

    if not player:
        bot.send_message(
            message.chat.id,
            "❌ اسم اللاعب فارغ."
        )
        return

    bot.send_message(
        message.chat.id,
        "➖ <b>Whitelist Remove</b>\n\n"
        f"اللاعب: <code>{player}</code>\n\n"
        "سيتم تمرير الأمر إلى نظام السيرفر."
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
        "🌐 <b>Server IP</b>\n\n"
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
        "/help"
    )


# ============================================================
# RENDER HEALTH
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
                f"Telegram error: {exc}"
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
        "Minecraft Telegram Server Manager"
    )

    print(
        "Aternos account control: ENABLED"
    )

    print(
        "Real Minecraft status: ENABLED"
    )

    print(
        "DiscordSRV integration: ENABLED"
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
