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

STATUS_TIMEOUT = float(
    os.getenv("STATUS_TIMEOUT", "5")
)

PORT = int(
    os.getenv("PORT", "10000")
)


if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN غير موجود في Render"
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
# SERVER STORAGE
# ============================================================

user_servers = {}

server_lock = threading.Lock()


def get_user_server(chat_id):

    with server_lock:
        return user_servers.get(
            chat_id,
            {
                "host": MC_SERVER_HOST,
                "port": MC_SERVER_PORT
            }
        ).copy()


def save_user_server(chat_id, host, port):

    with server_lock:
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


def parse_address(address):

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

            host = match.group(1)

            port = int(
                match.group(2) or 25565
            )

            return host, port

    parts = address.rsplit(":", 1)

    if len(parts) == 2:

        if parts[1].isdigit():

            port = int(parts[1])

            if not 1 <= port <= 65535:
                raise ValueError(
                    "Port غير صحيح"
                )

            return parts[0], port

    return address, 25565


# ============================================================
# JAVA STATUS
# ============================================================

def java_status(host, port):

    server = JavaServer(
        host,
        port,
        timeout=STATUS_TIMEOUT
    )

    result = server.status(
        tries=2
    )

    try:
        players = int(
            result.players.online
        )
    except Exception:
        players = 0

    try:
        maximum = int(
            result.players.max
        )
    except Exception:
        maximum = 0

    try:
        version = str(
            result.version.name
        )
    except Exception:
        version = "غير معروف"

    try:
        ping = round(
            float(result.latency)
        )
    except Exception:
        ping = None

    return {
        "online": True,
        "edition": "Java",
        "host": host,
        "port": port,
        "players": players,
        "max_players": maximum,
        "version": version,
        "ping": ping
    }


# ============================================================
# BEDROCK STATUS
# ============================================================

def bedrock_status(host, port):

    server = BedrockServer(
        host,
        port,
        timeout=STATUS_TIMEOUT
    )

    result = server.status(
        tries=2
    )

    try:
        players = int(
            result.players.online
        )
    except Exception:
        players = 0

    try:
        maximum = int(
            result.players.max
        )
    except Exception:
        maximum = 0

    try:
        version = str(
            result.version.name
        )
    except Exception:
        version = "غير معروف"

    try:
        ping = round(
            float(result.latency)
        )
    except Exception:
        ping = None

    return {
        "online": True,
        "edition": "Bedrock",
        "host": host,
        "port": port,
        "players": players,
        "max_players": maximum,
        "version": version,
        "ping": ping
    }


# ============================================================
# REAL STATUS
# ============================================================

def get_real_status(host, port):

    host = clean_host(host)

    try:
        return java_status(
            host,
            port
        )
    except Exception:
        pass

    try:
        return bedrock_status(
            host,
            port
        )
    except Exception:
        pass

    if port == 25565:

        try:
            return bedrock_status(
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
        "version": None,
        "ping": None
    }


# ============================================================
# STATUS FORMAT
# ============================================================

def format_status(data):

    if not data["online"]:

        return (
            "🔴 <b>السيرفر Offline</b>\n\n"
            f"🌐 العنوان:\n"
            f"<code>{data['host']}:{data['port']}</code>\n\n"
            "📡 السيرفر لا يستجيب حاليًا."
        )

    ping = data["ping"]

    if ping is None:
        ping_text = "غير معروف"
    else:
        ping_text = f"{ping}ms"

    return (
        "🟢 <b>السيرفر Online</b>\n\n"
        f"👥 اللاعبين: "
        f"<b>{data['players']}/{data['max_players']}</b>\n"
        f"📶 Ping: <b>{ping_text}</b>\n"
        f"🎮 الإصدار: <b>{data['version']}</b>\n"
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
            "📝 Whitelist",
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

    status = get_real_status(
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

    msg = bot.send_message(
        chat_id,
        "🔎 <b>جاري فحص السيرفر...</b>"
    )

    status = get_real_status(
        server["host"],
        server["port"]
    )

    try:

        bot.edit_message_text(

            format_status(status),

            chat_id,

            msg.message_id,

            reply_markup=main_keyboard()
        )

    except Exception:

        bot.send_message(

            chat_id,

            format_status(status),

            reply_markup=main_keyboard()
        )


@bot.message_handler(
    commands=["status"]
)
def status_command(message):

    send_status(
        message.chat.id
    )


# ============================================================
# CALLBACK
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


    # ========================================================
    # STATUS
    # ========================================================

    if call.data == "server_status":

        send_status(
            chat_id
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

            result = aternos.start()

            if result.get("success"):

                bot.send_message(
                    chat_id,
                    "✅ <b>تم إرسال أمر Start إلى Aternos.</b>\n\n"
                    "⏳ انتظر قليلًا ثم اضغط Status.",
                    reply_markup=main_keyboard()
                )

            else:

                raise RuntimeError(
                    str(result)
                )

        except Exception as exc:

            bot.send_message(
                chat_id,
                "❌ <b>فشل تشغيل السيرفر</b>\n\n"
                f"<code>{str(exc)[:2000]}</code>",
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

            result = aternos.stop()

            if result.get("success"):

                bot.send_message(
                    chat_id,
                    "✅ <b>تم إرسال أمر Stop إلى Aternos.</b>\n\n"
                    "اضغط Status للتحقق.",
                    reply_markup=main_keyboard()
                )

            else:

                raise RuntimeError(
                    str(result)
                )

        except Exception as exc:

            bot.send_message(
                chat_id,
                "❌ <b>فشل إيقاف السيرفر</b>\n\n"
                f"<code>{str(exc)[:2000]}</code>",
                reply_markup=main_keyboard()
            )

        return


    # ========================================================
    # RESTART
    # ========================================================

    if call.data == "aternos_restart":

        bot.send_message(
            chat_id,
            "🔄 <b>جاري Restart...</b>"
        )

        try:

            result = aternos.restart()

            if result.get("success"):

                bot.send_message(
                    chat_id,
                    "✅ <b>تم إرسال أمر Restart إلى Aternos.</b>\n\n"
                    "اضغط Status للتحقق.",
                    reply_markup=main_keyboard()
                )

            else:

                raise RuntimeError(
                    str(result)
                )

        except Exception as exc:

            bot.send_message(
                chat_id,
                "❌ <b>فشل Restart</b>\n\n"
                f"<code>{str(exc)[:2000]}</code>",
                reply_markup=main_keyboard()
            )

        return


    # ========================================================
    # PLAYERS
    # ========================================================

    if call.data == "players":

        server = get_user_server(
            chat_id
        )

        status = get_real_status(
            server["host"],
            server["port"]
        )

        if not status["online"]:

            bot.send_message(
                chat_id,
                "🔴 السيرفر Offline.\n"
                "لا يمكن جلب اللاعبين الآن.",
                reply_markup=main_keyboard()
            )

            return

        bot.send_message(
            chat_id,

            "👥 <b>اللاعبون</b>\n\n"
            f"عدد اللاعبين: "
            f"<b>{status['players']}/{status['max_players']}</b>\n\n"
            "ℹ️ أسماء اللاعبين تحتاج نظام Player List إضافي.",
            
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

            "الـ Console عندك مرتبط بنظام DiscordSRV "
            "وبوت Discord.\n\n"

            "يمكن إبقاء هذه الواجهة من Telegram "
            "مربوطة مع قناة Discord الخاصة بالكونسول.",

            reply_markup=main_keyboard()
        )

        return


    # ========================================================
    # WHITELIST
    # ========================================================

    if call.data == "whitelist":

        markup = types.InlineKeyboardMarkup(
            row_width=2
        )

        markup.add(

            types.InlineKeyboardButton(
                "➕ Add",
                callback_data="whitelist_add"
            ),

            types.InlineKeyboardButton(
                "➖ Remove",
                callback_data="whitelist_remove"
            )
        )

        markup.add(

            types.InlineKeyboardButton(
                "📋 List",
                callback_data="whitelist_list"
            )
        )

        markup.add(

            types.InlineKeyboardButton(
                "🔙 رجوع",
                callback_data="back_main"
            )
        )

        bot.send_message(
            chat_id,
            "📝 <b>Whitelist</b>\n\n"
            "اختر العملية:",
            reply_markup=markup
        )

        return


    # ========================================================
    # BACK
    # ========================================================

    if call.data == "back_main":

        bot.send_message(
            chat_id,
            "🎮 <b>لوحة التحكم</b>",
            reply_markup=main_keyboard()
        )

        return


    # ========================================================
    # WHITELIST ACTIONS
    # ========================================================

    if call.data == "whitelist_add":

        bot.send_message(
            chat_id,
            "➕ أرسل اسم اللاعب لإضافته إلى Whitelist.\n\n"
            "مثال:\n"
            "<code>/whitelist_add Steve</code>"
        )

        return


    if call.data == "whitelist_remove":

        bot.send_message(
            chat_id,
            "➖ أرسل اسم اللاعب لإزالته.\n\n"
            "مثال:\n"
            "<code>/whitelist_remove Steve</code>"
        )

        return


    if call.data == "whitelist_list":

        bot.send_message(
            chat_id,
            "📋 <b>Whitelist</b>\n\n"
            "سيتم جلب القائمة من نظام DiscordSRV/Console "
            "الموجود عندك.",
            reply_markup=main_keyboard()
        )

        return


# ============================================================
# WHITELIST COMMANDS
# ============================================================

@bot.message_handler(
    commands=["whitelist_add"]
)
def whitelist_add(message):

    parts = message.text.split(
        maxsplit=1
    )

    if len(parts) < 2:

        bot.send_message(
            message.chat.id,
            "❌ استخدم:\n"
            "<code>/whitelist_add PlayerName</code>"
        )

        return

    player = parts[1].strip()

    bot.send_message(
        message.chat.id,
        "📝 سيتم إرسال أمر Whitelist للاعب:\n"
        f"<code>{player}</code>\n\n"
        "اربط هذه العملية مع Console/DiscordSRV لديك."
    )


@bot.message_handler(
    commands=["whitelist_remove"]
)
def whitelist_remove(message):

    parts = message.text.split(
        maxsplit=1
    )

    if len(parts) < 2:

        bot.send_message(
            message.chat.id,
            "❌ استخدم:\n"
            "<code>/whitelist_remove PlayerName</code>"
        )

        return

    player = parts[1].strip()

    bot.send_message(
        message.chat.id,
        "📝 سيتم إرسال أمر إزالة Whitelist للاعب:\n"
        f"<code>{player}</code>\n\n"
        "اربط هذه العملية مع Console/DiscordSRV لديك."
    )


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

        "🌐 <b>Server Address</b>\n\n"

        f"<code>"
        f"{server['host']}:{server['port']}"
        f"</code>"
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
        "/ip\n"
        "/help\n"
        "/start_server\n"
        "/stop_server\n"
        "/restart\n"
        "/whitelist_add\n"
        "/whitelist_remove"
    )


# ============================================================
# RENDER HEALTH
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
# POLLING
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
                "Telegram error:",
                exc
            )

            time.sleep(5)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    health_thread = threading.Thread(

        target=run_health_server,

        daemon=True
    )

    health_thread.start()

    print(
        "Aternos account control: ENABLED"
    )

    print(
        "Minecraft status: ENABLED"
    )

    run_bot()
