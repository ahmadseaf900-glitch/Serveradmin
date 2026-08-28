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

DISCORD_CHANNEL_ID = os.getenv(
    "DISCORD_CHANNEL_ID",
    ""
).strip()

DISCORD_TOKEN = os.getenv(
    "DISCORD_TOKEN",
    ""
).strip()

CONSOLE_WHITELIST = os.getenv(
    "CONSOLE_WHITELIST",
    ""
).strip()


if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN غير موجود."
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
# HELPERS
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

    host = host.split("/")[0]

    return host


def parse_address(address):
    address = clean_host(address)

    if ":" in address:

        parts = address.rsplit(
            ":",
            1
        )

        if (
            len(parts) == 2
            and parts[1].isdigit()
        ):
            return (
                parts[0],
                int(parts[1])
            )

    return (
        address,
        25565
    )


# ============================================================
# MC STATUS
# ============================================================

def minecraft_status():

    host = clean_host(
        MC_SERVER_HOST
    )

    port = MC_SERVER_PORT

    try:

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
            "players": result.players.online,
            "max": result.players.max,
            "ping": round(
                float(result.latency)
            ),
            "version": str(
                result.version.name
            ),
            "host": host,
            "port": port
        }

    except Exception:
        pass

    # Bedrock
    try:

        bedrock_port = (
            19132
            if port == 25565
            else port
        )

        server = BedrockServer(
            host,
            bedrock_port,
            timeout=STATUS_TIMEOUT
        )

        result = server.status(
            tries=2
        )

        return {
            "online": True,
            "edition": "Bedrock",
            "players": result.players.online,
            "max": result.players.max,
            "ping": round(
                float(result.latency)
            ),
            "version": str(
                result.version.name
            ),
            "host": host,
            "port": bedrock_port
        }

    except Exception as exc:

        return {
            "online": False,
            "edition": "Unknown",
            "players": 0,
            "max": 0,
            "ping": None,
            "version": None,
            "host": host,
            "port": port,
            "error": str(exc)
        }


# ============================================================
# STATUS TEXT
# ============================================================

def status_text():

    data = minecraft_status()

    if not data["online"]:

        return (
            "🔴 <b>السيرفر Offline</b>\n\n"
            f"🌐 <code>"
            f"{data['host']}:{data['port']}"
            f"</code>"
        )

    return (
        "🟢 <b>السيرفر Online</b>\n\n"
        f"👥 اللاعبين: "
        f"<b>{data['players']}/{data['max']}</b>\n"
        f"📶 Ping: "
        f"<b>{data['ping']}ms</b>\n"
        f"🎮 الإصدار: "
        f"<b>{data['version']}</b>\n"
        f"🧩 النوع: "
        f"<b>{data['edition']}</b>\n"
        f"🌐 العنوان:\n"
        f"<code>"
        f"{data['host']}:{data['port']}"
        f"</code>"
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
            callback_data="status"
        )
    )

    markup.add(

        types.InlineKeyboardButton(
            "👥 Players",
            callback_data="players"
        ),

        types.InlineKeyboardButton(
            "📝 Console",
            callback_data="console"
        )
    )

    markup.add(

        types.InlineKeyboardButton(
            "🟢 Whitelist",
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

    try:

        text = (
            "🤖 <b>بوت إدارة سيرفر Minecraft</b>\n\n"
            f"🌐 <code>"
            f"{MC_SERVER_HOST}:{MC_SERVER_PORT}"
            f"</code>\n\n"
            f"{status_text()}"
        )

        bot.send_message(
            message.chat.id,
            text,
            reply_markup=main_keyboard()
        )

    except Exception as exc:

        bot.send_message(
            message.chat.id,
            "❌ خطأ:\n"
            f"<code>{str(exc)[:1000]}</code>"
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

    if call.data == "status":

        try:

            bot.send_message(
                chat_id,
                status_text(),
                reply_markup=main_keyboard()
            )

        except Exception as exc:

            bot.send_message(
                chat_id,
                "❌ فشل فحص الحالة:\n"
                f"<code>{str(exc)[:1000]}</code>"
            )

        return


    # ========================================================
    # START
    # ========================================================

    if call.data == "aternos_start":

        try:

            result = aternos.start()

            bot.send_message(
                chat_id,
                "▶️ <b>تم إرسال أمر تشغيل السيرفر.</b>\n\n"
                f"📡 حالة Aternos: "
                f"<code>{result.get('status')}</code>\n\n"
                "⏳ انتظر قليلًا ثم اضغط Status.",
                reply_markup=main_keyboard()
            )

        except Exception as exc:

            bot.send_message(
                chat_id,
                "❌ <b>فشل تشغيل السيرفر</b>\n\n"
                f"<code>{str(exc)[:1500]}</code>"
            )

        return


    # ========================================================
    # STOP
    # ========================================================

    if call.data == "aternos_stop":

        try:

            result = aternos.stop()

            bot.send_message(
                chat_id,
                "⏹️ <b>تم إرسال أمر إيقاف السيرفر.</b>\n\n"
                f"📡 حالة Aternos: "
                f"<code>{result.get('status')}</code>",
                reply_markup=main_keyboard()
            )

        except Exception as exc:

            bot.send_message(
                chat_id,
                "❌ <b>فشل إيقاف السيرفر</b>\n\n"
                f"<code>{str(exc)[:1500]}</code>"
            )

        return


    # ========================================================
    # RESTART
    # ========================================================

    if call.data == "aternos_restart":

        try:

            result = aternos.restart()

            bot.send_message(
                chat_id,
                "🔄 <b>تم إرسال أمر Restart.</b>\n\n"
                f"📡 حالة Aternos: "
                f"<code>{result.get('status')}</code>",
                reply_markup=main_keyboard()
            )

        except Exception as exc:

            bot.send_message(
                chat_id,
                "❌ <b>فشل Restart</b>\n\n"
                f"<code>{str(exc)[:1500]}</code>"
            )

        return


    # ========================================================
    # PLAYERS
    # ========================================================

    if call.data == "players":

        try:

            data = aternos.players()

            if not data["players"]:

                text = (
                    "👥 <b>اللاعبون</b>\n\n"
                    "لا يوجد لاعب متصل حاليًا."
                )

            else:

                players = "\n".join(
                    f"• <code>{name}</code>"
                    for name in data["players"]
                )

                text = (
                    "👥 <b>اللاعبون المتصلون</b>\n\n"
                    f"{players}\n\n"
                    f"📊 {data['online']}/{data['max']}"
                )

            bot.send_message(
                chat_id,
                text,
                reply_markup=main_keyboard()
            )

        except Exception as exc:

            bot.send_message(
                chat_id,
                "❌ فشل جلب اللاعبين:\n"
                f"<code>{str(exc)[:1000]}</code>"
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
                "➕ إضافة",
                callback_data="whitelist_add"
            ),

            types.InlineKeyboardButton(
                "➖ إزالة",
                callback_data="whitelist_remove"
            )
        )

        markup.add(

            types.InlineKeyboardButton(
                "📋 القائمة",
                callback_data="whitelist_list"
            )
        )

        bot.send_message(
            chat_id,
            "🟢 <b>Whitelist</b>\n\n"
            "اختر العملية:",
            reply_markup=markup
        )

        return


    # ========================================================
    # WHITELIST LIST
    # ========================================================

    if call.data == "whitelist_list":

        try:

            players = aternos.whitelist_list()

            if not players:

                text = (
                    "📋 <b>Whitelist</b>\n\n"
                    "القائمة فارغة."
                )

            else:

                text = (
                    "📋 <b>Whitelist</b>\n\n"
                    + "\n".join(
                        f"• <code>{p}</code>"
                        for p in players
                    )
                )

            bot.send_message(
                chat_id,
                text,
                reply_markup=main_keyboard()
            )

        except Exception as exc:

            bot.send_message(
                chat_id,
                "❌ فشل قراءة Whitelist:\n"
                f"<code>{str(exc)[:1500]}</code>"
            )

        return


    # ========================================================
    # WHITELIST ADD
    # ========================================================

    if call.data == "whitelist_add":

        msg = bot.send_message(
            chat_id,
            "➕ أرسل اسم اللاعب لإضافته إلى Whitelist:"
        )

        bot.register_next_step_handler(
            msg,
            whitelist_add_handler
        )

        return


    # ========================================================
    # WHITELIST REMOVE
    # ========================================================

    if call.data == "whitelist_remove":

        msg = bot.send_message(
            chat_id,
            "➖ أرسل اسم اللاعب لإزالته من Whitelist:"
        )

        bot.register_next_step_handler(
            msg,
            whitelist_remove_handler
        )

        return


    # ========================================================
    # CONSOLE
    # ========================================================

    if call.data == "console":

        bot.send_message(
            chat_id,
            "📝 <b>Console</b>\n\n"
            "أرسل الأمر بهذا الشكل:\n"
            "<code>/console say Hello</code>\n\n"
            "أو:\n"
            "<code>/console list</code>\n\n"
            "سيتم تمريره إلى قناة DiscordSRV المحددة "
            "في DISCORD_CHANNEL_ID.",
            reply_markup=main_keyboard()
        )

        return


# ============================================================
# WHITELIST ADD HANDLER
# ============================================================

def whitelist_add_handler(message):

    player = (
        message.text or ""
    ).strip()

    try:

        aternos.whitelist_add(
            player
        )

        bot.send_message(
            message.chat.id,
            "✅ تم إضافة:\n"
            f"<code>{player}</code>",
            reply_markup=main_keyboard()
        )

    except Exception as exc:

        bot.send_message(
            message.chat.id,
            "❌ فشل إضافة اللاعب:\n"
            f"<code>{str(exc)[:1500]}</code>"
        )


# ============================================================
# WHITELIST REMOVE HANDLER
# ============================================================

def whitelist_remove_handler(message):

    player = (
        message.text or ""
    ).strip()

    try:

        aternos.whitelist_remove(
            player
        )

        bot.send_message(
            message.chat.id,
            "✅ تم إزالة:\n"
            f"<code>{player}</code>",
            reply_markup=main_keyboard()
        )

    except Exception as exc:

        bot.send_message(
            message.chat.id,
            "❌ فشل إزالة اللاعب:\n"
            f"<code>{str(exc)[:1500]}</code>"
        )


# ============================================================
# /STATUS
# ============================================================

@bot.message_handler(
    commands=["status"]
)
def status_command(message):

    bot.send_message(
        message.chat.id,
        status_text(),
        reply_markup=main_keyboard()
    )


# ============================================================
# /PLAYERS
# ============================================================

@bot.message_handler(
    commands=["players"]
)
def players_command(message):

    try:

        data = aternos.players()

        if not data["players"]:

            text = (
                "👥 لا يوجد لاعب متصل."
            )

        else:

            text = (
                "👥 <b>Players</b>\n\n"
                + "\n".join(
                    f"• <code>{p}</code>"
                    for p in data["players"]
                )
                + "\n\n"
                f"📊 {data['online']}/{data['max']}"
            )

        bot.send_message(
            message.chat.id,
            text,
            reply_markup=main_keyboard()
        )

    except Exception as exc:

        bot.send_message(
            message.chat.id,
            "❌ "
            f"<code>{str(exc)[:1000]}</code>"
        )


# ============================================================
# /CONSOLE
#
# يرسل الأمر إلى Discord عبر Discord REST.
#
# ملاحظة:
# DiscordSRV يجب أن يكون مضبوطًا بحيث تكون قناة
# DISCORD_CHANNEL_ID هي قناة Console التي يستقبل منها
# أوامر السيرفر.
# ============================================================

@bot.message_handler(
    commands=["console"]
)
def console_command(message):

    command = (
        message.text or ""
    )

    command = re.sub(
        r"^/console\s*",
        "",
        command,
        flags=re.IGNORECASE
    ).strip()

    if not command:

        bot.send_message(
            message.chat.id,
            "📝 الاستخدام:\n"
            "<code>/console list</code>"
        )

        return

    if not DISCORD_TOKEN:

        bot.send_message(
            message.chat.id,
            "❌ DISCORD_TOKEN غير موجود."
        )

        return

    if not DISCORD_CHANNEL_ID:

        bot.send_message(
            message.chat.id,
            "❌ DISCORD_CHANNEL_ID غير موجود."
        )

        return

    # هذه الوظيفة تعتمد على requests
    # لإرسال رسالة إلى قناة Discord.
    try:

        import requests

        url = (
            "https://discord.com/api/v10/"
            f"channels/{DISCORD_CHANNEL_ID}/messages"
        )

        headers = {
            "Authorization":
                f"Bot {DISCORD_TOKEN}",
            "Content-Type":
                "application/json"
        }

        payload = {
            "content": command
        }

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=10
        )

        if response.status_code >= 300:

            raise RuntimeError(
                f"Discord HTTP "
                f"{response.status_code}: "
                f"{response.text[:500]}"
            )

        bot.send_message(
            message.chat.id,
            "✅ تم إرسال الأمر إلى DiscordSRV:\n\n"
            f"<code>{command}</code>"
        )

    except Exception as exc:

        bot.send_message(
            message.chat.id,
            "❌ فشل إرسال الأمر إلى Discord:\n"
            f"<code>{str(exc)[:1500]}</code>"
        )


# ============================================================
# /WHITELIST
# ============================================================

@bot.message_handler(
    commands=["whitelist"]
)
def whitelist_command(message):

    parts = (
        message.text or ""
    ).split()

    if len(parts) == 1:

        try:

            players = aternos.whitelist_list()

            bot.send_message(
                message.chat.id,
                "📋 <b>Whitelist</b>\n\n"
                + (
                    "\n".join(
                        f"• <code>{p}</code>"
                        for p in players
                    )
                    if players
                    else "القائمة فارغة."
                )
            )

        except Exception as exc:

            bot.send_message(
                message.chat.id,
                "❌ "
                f"<code>{str(exc)[:1000]}</code>"
            )

        return

    action = parts[1].lower()

    if len(parts) < 3:

        bot.send_message(
            message.chat.id,
            "الاستخدام:\n\n"
            "<code>/whitelist add Player</code>\n"
            "<code>/whitelist remove Player</code>"
        )

        return

    player = parts[2]

    try:

        if action == "add":

            aternos.whitelist_add(
                player
            )

            text = (
                "✅ تمت إضافة "
                f"<code>{player}</code>"
                " إلى Whitelist."
            )

        elif action in (
            "remove",
            "del",
            "delete"
        ):

            aternos.whitelist_remove(
                player
            )

            text = (
                "✅ تمت إزالة "
                f"<code>{player}</code>"
                " من Whitelist."
            )

        else:

            text = (
                "❌ العملية غير معروفة."
            )

        bot.send_message(
            message.chat.id,
            text
        )

    except Exception as exc:

        bot.send_message(
            message.chat.id,
            "❌ "
            f"<code>{str(exc)[:1500]}</code>"
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
        "/players\n"
        "/console الأمر\n\n"

        "/whitelist\n"
        "/whitelist add Player\n"
        "/whitelist remove Player\n\n"

        "أو استخدم أزرار لوحة التحكم."
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
            b"Minecraft Telegram Bot is running."
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

    server.serve_forever()


# ============================================================
# TELEGRAM LOOP
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

    print(
        "Minecraft Telegram Control Bot"
    )

    threading.Thread(
        target=run_health_server,
        daemon=True
    ).start()

    run_bot()
