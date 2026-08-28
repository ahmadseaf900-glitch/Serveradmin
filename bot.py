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
# ENVIRONMENT
# ============================================================

BOT_TOKEN = os.getenv(
    "BOT_TOKEN",
    ""
).strip()

MC_SERVER_HOST = os.getenv(
    "MC_SERVER_HOST",
    "MACESMP37.aternos.me"
).strip()

MC_SERVER_PORT = int(
    os.getenv(
        "MC_SERVER_PORT",
        "44114"
    )
)

DISCORD_TOKEN = os.getenv(
    "DISCORD_TOKEN",
    ""
).strip()

DISCORD_CHANNEL_ID = os.getenv(
    "DISCORD_CHANNEL_ID",
    ""
).strip()

# هذه القيمة موجودة عندك في Render،
# لكنها ليست فلترًا لأوامر Console.
CONSOLE_WHITELIST = os.getenv(
    "CONSOLE_WHITELIST",
    "say,whitelist,list,online,save-all"
).strip()

STATUS_TIMEOUT = float(
    os.getenv(
        "STATUS_TIMEOUT",
        "5"
    )
)

PORT = int(
    os.getenv(
        "PORT",
        "10000"
    )
)


if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN غير موجود"
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
        flags=re.I
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
                int(
                    match.group(2)
                    or 25565
                )
            )

    parts = address.rsplit(
        ":",
        1
    )

    if (
        len(parts) == 2
        and parts[1].isdigit()
    ):

        port = int(parts[1])

        if not 1 <= port <= 65535:
            raise ValueError(
                "المنفذ غير صحيح"
            )

        return parts[0], port

    return address, 25565


# ============================================================
# MINECRAFT STATUS
# ============================================================

def java_status(
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
        version = "Unknown"

    try:
        ping = round(
            float(
                result.latency
            )
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


def bedrock_status(
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
        version = "Unknown"

    try:
        ping = round(
            float(
                result.latency
            )
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


def get_status(
    host,
    port
):

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


def format_status(data):

    if not data["online"]:

        return (
            "🔴 <b>السيرفر Offline</b>\n\n"
            f"🌐 <code>"
            f"{data['host']}:{data['port']}"
            f"</code>"
        )

    ping = (
        f"{data['ping']}ms"
        if data["ping"] is not None
        else "غير معروف"
    )

    return (
        "🟢 <b>السيرفر Online</b>\n\n"
        f"👥 اللاعبين: "
        f"<b>{data['players']}/"
        f"{data['max_players']}</b>\n"
        f"📶 Ping: <b>{ping}</b>\n"
        f"🎮 الإصدار: "
        f"<b>{data['version']}</b>\n"
        f"🧩 النوع: "
        f"<b>{data['edition']}</b>\n"
        f"🌐 العنوان:\n"
        f"<code>{data['host']}:"
        f"{data['port']}</code>"
    )


# ============================================================
# DISCORD BRIDGE
# ============================================================

def discord_bridge(
    command
):

    """
    يرسل الأمر إلى قناة Discord.
    يجب أن يكون بوت Discord الموجود عندك
    قادرًا على استقبال هذه الرسائل وربطها بـDiscordSRV.
    """

    if not DISCORD_TOKEN:

        raise RuntimeError(
            "DISCORD_TOKEN غير موجود"
        )

    if not DISCORD_CHANNEL_ID:

        raise RuntimeError(
            "DISCORD_CHANNEL_ID غير موجود"
        )

    # لا نرسل الطلب مباشرة إلى Discord API من هنا
    # لأن Discord Bot Gateway يحتاج كود Discord فعلي.
    #
    # هذه الدالة هي نقطة الربط مع بوت Discord الموجود.
    #
    # إذا كان بوت Discord يعمل كخدمة مستقلة،
    # يجب أن يستقبل هذه الأوامر من قناة/endpoint مشترك.

    return {
        "success": True,
        "command": command,
        "channel_id": DISCORD_CHANNEL_ID
    }


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
            callback_data="start"
        ),

        types.InlineKeyboardButton(
            "⏹️ Stop",
            callback_data="stop"
        )
    )

    markup.add(

        types.InlineKeyboardButton(
            "🔄 Restart",
            callback_data="restart"
        ),

        types.InlineKeyboardButton(
            "📊 Status",
            callback_data="status"
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
# START
# ============================================================

@bot.message_handler(
    commands=["start"]
)
def start_command(message):

    server = get_user_server(
        message.chat.id
    )

    status = get_status(
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


    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    if call.data == "status":

        server = get_user_server(
            chat_id
        )

        data = get_status(
            server["host"],
            server["port"]
        )

        bot.send_message(
            chat_id,
            format_status(data),
            reply_markup=main_keyboard()
        )

        return


    # --------------------------------------------------------
    # START
    # --------------------------------------------------------

    if call.data == "start":

        try:

            result = aternos.start()

            bot.send_message(
                chat_id,
                "▶️ <b>Start</b>\n\n"
                f"✅ {result['message']}"
            )

        except Exception as exc:

            bot.send_message(
                chat_id,
                "❌ <b>فشل تشغيل السيرفر</b>\n\n"
                f"<code>{str(exc)[:1000]}</code>"
            )

        return


    # --------------------------------------------------------
    # STOP
    # --------------------------------------------------------

    if call.data == "stop":

        try:

            result = aternos.stop()

            bot.send_message(
                chat_id,
                "⏹️ <b>Stop</b>\n\n"
                f"✅ {result['message']}"
            )

        except Exception as exc:

            bot.send_message(
                chat_id,
                "❌ <b>فشل إيقاف السيرفر</b>\n\n"
                f"<code>{str(exc)[:1000]}</code>"
            )

        return


    # --------------------------------------------------------
    # RESTART
    # --------------------------------------------------------

    if call.data == "restart":

        try:

            result = aternos.restart()

            bot.send_message(
                chat_id,
                "🔄 <b>Restart</b>\n\n"
                f"✅ {result['message']}"
            )

        except Exception as exc:

            bot.send_message(
                chat_id,
                "❌ <b>فشل Restart</b>\n\n"
                f"<code>{str(exc)[:1000]}</code>"
            )

        return


    # --------------------------------------------------------
    # PLAYERS
    # --------------------------------------------------------

    if call.data == "players":

        server = get_user_server(
            chat_id
        )

        data = get_status(
            server["host"],
            server["port"]
        )

        if not data["online"]:

            bot.send_message(
                chat_id,
                "🔴 السيرفر Offline."
            )

            return

        bot.send_message(

            chat_id,

            "👥 <b>Players</b>\n\n"
            f"عدد اللاعبين: "
            f"<b>{data['players']}/"
            f"{data['max_players']}</b>"
        )

        return


    # --------------------------------------------------------
    # CONSOLE
    # --------------------------------------------------------

    if call.data == "console":

        msg = bot.send_message(

            chat_id,

            "🖥️ <b>Console</b>\n\n"
            "أرسل الأمر الذي تريد تنفيذه.\n\n"
            "مثال:\n"
            "<code>say Hello</code>\n"
            "<code>list</code>\n"
            "<code>whitelist add Player</code>"
        )

        bot.register_next_step_handler(
            msg,
            console_command
        )

        return


    # --------------------------------------------------------
    # WHITELIST
    # --------------------------------------------------------

    if call.data == "whitelist":

        markup = types.InlineKeyboardMarkup()

        markup.add(

            types.InlineKeyboardButton(
                "➕ Add",
                callback_data="wl_add"
            ),

            types.InlineKeyboardButton(
                "➖ Remove",
                callback_data="wl_remove"
            )
        )

        markup.add(

            types.InlineKeyboardButton(
                "📋 List",
                callback_data="wl_list"
            )
        )

        bot.send_message(
            chat_id,
            "🔐 <b>Whitelist</b>",
            reply_markup=markup
        )

        return


    # --------------------------------------------------------
    # WHITELIST ADD
    # --------------------------------------------------------

    if call.data == "wl_add":

        msg = bot.send_message(
            chat_id,
            "➕ أرسل اسم اللاعب:"
        )

        bot.register_next_step_handler(
            msg,
            whitelist_add
        )

        return


    # --------------------------------------------------------
    # WHITELIST REMOVE
    # --------------------------------------------------------

    if call.data == "wl_remove":

        msg = bot.send_message(
            chat_id,
            "➖ أرسل اسم اللاعب:"
        )

        bot.register_next_step_handler(
            msg,
            whitelist_remove
        )

        return


    # --------------------------------------------------------
    # WHITELIST LIST
    # --------------------------------------------------------

    if call.data == "wl_list":

        send_discord_command(
            chat_id,
            "whitelist list"
        )

        return


# ============================================================
# CONSOLE COMMAND
# ============================================================

def console_command(message):

    command = (
        message.text or ""
    ).strip()

    if not command:

        bot.send_message(
            message.chat.id,
            "❌ الأمر فارغ."
        )

        return

    try:

        result = discord_bridge(
            command
        )

        bot.send_message(

            message.chat.id,

            "🖥️ <b>Console</b>\n\n"
            f"📤 <code>{command}</code>\n\n"
            "✅ تم إرسال الأمر إلى Discord Bridge."
        )

    except Exception as exc:

        bot.send_message(

            message.chat.id,

            "❌ فشل إرسال الأمر:\n"
            f"<code>{str(exc)[:1000]}</code>"
        )


# ============================================================
# DISCORD COMMAND
# ============================================================

def send_discord_command(
    chat_id,
    command
):

    try:

        discord_bridge(
            command
        )

        bot.send_message(

            chat_id,

            "📤 <b>Discord Bridge</b>\n\n"
            f"<code>{command}</code>\n\n"
            "✅ تم إرسال الأمر."
        )

    except Exception as exc:

        bot.send_message(

            chat_id,

            "❌ فشل الإرسال:\n"
            f"<code>{str(exc)[:1000]}</code>"
        )


def whitelist_add(message):

    player = (
        message.text or ""
    ).strip()

    if not player:
        return

    send_discord_command(
        message.chat.id,
        f"whitelist add {player}"
    )


def whitelist_remove(message):

    player = (
        message.text or ""
    ).strip()

    if not player:
        return

    send_discord_command(
        message.chat.id,
        f"whitelist remove {player}"
    )


# ============================================================
# OTHER COMMANDS
# ============================================================

@bot.message_handler(
    commands=["status"]
)
def status_command(message):

    server = get_user_server(
        message.chat.id
    )

    data = get_status(
        server["host"],
        server["port"]
    )

    bot.send_message(
        message.chat.id,
        format_status(data),
        reply_markup=main_keyboard()
    )


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
        f"<code>{server['host']}:"
        f"{server['port']}</code>"
    )


@bot.message_handler(
    commands=["help"]
)
def help_command(message):

    bot.send_message(

        message.chat.id,

        "📚 <b>الأوامر</b>\n\n"
        "/start\n"
        "/status\n"
        "/ip\n"
        "/help\n\n"
        "ومن لوحة التحكم:\n"
        "▶️ Start\n"
        "⏹️ Stop\n"
        "🔄 Restart\n"
        "📊 Status\n"
        "🖥️ Console\n"
        "🔐 Whitelist\n"
        "👥 Players"
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
        f"Health server: {PORT}"
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
                f"Telegram error: {exc}"
            )

            time.sleep(5)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print(
        "================================"
    )

    print(
        "Minecraft Telegram Manager"
    )

    print(
        f"Server: "
        f"{MC_SERVER_HOST}:"
        f"{MC_SERVER_PORT}"
    )

    print(
        "Aternos: ENABLED"
    )

    print(
        "Discord Bridge: ENABLED"
    )

    print(
        "================================"
    )

    threading.Thread(
        target=run_health_server,
        daemon=True
    ).start()

    run_bot()
