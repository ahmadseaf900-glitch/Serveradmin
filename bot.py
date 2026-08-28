import os
import time
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import requests
import telebot
from telebot import types


# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
DISCORD_CHANNEL_ID = os.getenv(
    "DISCORD_CHANNEL_ID",
    os.getenv("DISCORD_CHANNELID", "")
).strip()

PORT = int(os.getenv("PORT", "10000"))

DISCORD_API = "https://discord.com/api/v10"


if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN غير موجود في Render")

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN غير موجود في Render")

if not DISCORD_CHANNEL_ID:
    raise RuntimeError("DISCORD_CHANNEL_ID غير موجود في Render")


# ============================================================
# TELEGRAM
# ============================================================

bot = telebot.TeleBot(
    BOT_TOKEN,
    parse_mode="HTML",
    threaded=True
)


# ============================================================
# DISCORD
# ============================================================

def discord_headers():
    return {
        "Authorization": f"Bot {DISCORD_TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "Minecraft-Telegram-Bridge/1.0"
    }


def test_discord():
    """اختبار توكن Discord."""

    try:
        response = requests.get(
            f"{DISCORD_API}/users/@me",
            headers=discord_headers(),
            timeout=15
        )

        print(
            f"Discord authentication status: "
            f"{response.status_code}"
        )

        if response.status_code == 200:
            data = response.json()

            print(
                "Discord bot authenticated as: "
                f"{data.get('username')} "
                f"(ID: {data.get('id')})"
            )

            return True

        print(
            "Discord authentication failed:"
        )
        print(
            response.text[:1000]
        )

        return False

    except Exception as exc:

        print(
            f"Discord connection error: {exc}"
        )

        return False


def send_discord_message(text):
    """إرسال رسالة إلى قناة Discord."""

    text = str(text or "").strip()

    if not text:
        raise ValueError("النص فارغ")

    response = requests.post(
        f"{DISCORD_API}/channels/"
        f"{DISCORD_CHANNEL_ID}/messages",

        headers=discord_headers(),

        json={
            "content": text
        },

        timeout=15
    )

    if response.status_code not in (200, 201):

        raise RuntimeError(
            f"Discord HTTP {response.status_code}: "
            f"{response.text[:1000]}"
        )

    return response.json()


# ============================================================
# MINECRAFT COMMAND BRIDGE
# ============================================================

def send_console_command(command):

    command = str(command or "").strip()

    if not command:
        raise ValueError("الأمر فارغ")

    # هذا هو الأمر الذي يستقبله بوت Discord
    # ويرسله إلى DiscordSRV / Minecraft
    return send_discord_message(
        f"!console {command}"
    )


# ============================================================
# MAIN KEYBOARD
# ============================================================

def main_keyboard():

    markup = types.InlineKeyboardMarkup(
        row_width=2
    )

    markup.add(

        types.InlineKeyboardButton(
            "📊 Status",
            callback_data="status"
        ),

        types.InlineKeyboardButton(
            "👥 Players",
            callback_data="players"
        )
    )

    markup.add(

        types.InlineKeyboardButton(
            "🖥️ Console",
            callback_data="console"
        ),

        types.InlineKeyboardButton(
            "🔐 Whitelist",
            callback_data="whitelist"
        )
    )

    markup.add(

        types.InlineKeyboardButton(
            "💬 Say",
            callback_data="say"
        ),

        types.InlineKeyboardButton(
            "📢 Broadcast",
            callback_data="broadcast"
        )
    )

    markup.add(

        types.InlineKeyboardButton(
            "🔄 Refresh",
            callback_data="refresh"
        )
    )

    return markup


# ============================================================
# START
# ============================================================

@bot.message_handler(commands=["start"])
def start_command(message):

    bot.send_message(
        message.chat.id,

        "🤖 <b>Minecraft Management Bot</b>\n\n"
        "🔗 Telegram → Discord → Minecraft\n\n"
        "اختر العملية:",

        reply_markup=main_keyboard()
    )


# ============================================================
# HELP
# ============================================================

@bot.message_handler(commands=["help"])
def help_command(message):

    bot.send_message(
        message.chat.id,

        "📚 <b>الأوامر</b>\n\n"
        "/start — لوحة التحكم\n"
        "/status — حالة السيرفر\n"
        "/players — اللاعبين\n"
        "/console — الكونسول\n"
        "/whitelist — الوايت ليست\n"
        "/say — إرسال رسالة\n"
        "/broadcast — Broadcast"
    )


# ============================================================
# STATUS
# ============================================================

def do_status(chat_id):

    try:

        send_console_command("list")

        bot.send_message(
            chat_id,

            "📊 <b>Status</b>\n\n"
            "📤 تم إرسال أمر الحالة إلى Discord Bot."
        )

    except Exception as exc:

        bot.send_message(
            chat_id,

            "❌ <b>فشل إرسال الطلب</b>\n\n"
            f"<code>{str(exc)[:1000]}</code>"
        )


@bot.message_handler(commands=["status"])
def status_command(message):
    do_status(message.chat.id)


# ============================================================
# PLAYERS
# ============================================================

def do_players(chat_id):

    try:

        send_console_command("list")

        bot.send_message(
            chat_id,

            "👥 <b>Players</b>\n\n"
            "📤 تم إرسال أمر <code>list</code> إلى Discord."
        )

    except Exception as exc:

        bot.send_message(
            chat_id,

            "❌ <b>فشل</b>\n\n"
            f"<code>{str(exc)[:1000]}</code>"
        )


@bot.message_handler(commands=["players"])
def players_command(message):
    do_players(message.chat.id)


# ============================================================
# CONSOLE
# ============================================================

def do_console(chat_id):

    msg = bot.send_message(
        chat_id,

        "🖥️ <b>Console</b>\n\n"
        "أرسل أمر Minecraft:\n\n"
        "<code>say Hello</code>\n"
        "<code>list</code>\n"
        "<code>time set day</code>"
    )

    bot.register_next_step_handler(
        msg,
        console_execute
    )


def console_execute(message):

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

        send_console_command(command)

        bot.send_message(
            message.chat.id,

            "🖥️ <b>Console</b>\n\n"
            f"📤 <code>{command}</code>\n\n"
            "✅ تم إرسال الأمر إلى Discord Bot."
        )

    except Exception as exc:

        bot.send_message(
            message.chat.id,

            "❌ <b>فشل</b>\n\n"
            f"<code>{str(exc)[:1000]}</code>"
        )


@bot.message_handler(commands=["console"])
def console_command(message):
    do_console(message.chat.id)


# ============================================================
# WHITELIST MENU
# ============================================================

def whitelist_menu(chat_id):

    markup = types.InlineKeyboardMarkup(
        row_width=2
    )

    markup.add(

        types.InlineKeyboardButton(
            "➕ إضافة",
            callback_data="wl_add"
        ),

        types.InlineKeyboardButton(
            "➖ حذف",
            callback_data="wl_remove"
        )
    )

    markup.add(

        types.InlineKeyboardButton(
            "📋 القائمة",
            callback_data="wl_list"
        )
    )

    bot.send_message(
        chat_id,

        "🔐 <b>Whitelist</b>\n\n"
        "اختر العملية:",

        reply_markup=markup
    )


@bot.message_handler(commands=["whitelist"])
def whitelist_command(message):
    whitelist_menu(message.chat.id)


# ============================================================
# WHITELIST ADD
# ============================================================

def whitelist_add_start(chat_id):

    msg = bot.send_message(
        chat_id,
        "➕ أرسل اسم اللاعب:"
    )

    bot.register_next_step_handler(
        msg,
        whitelist_add_execute
    )


def whitelist_add_execute(message):

    player = (
        message.text or ""
    ).strip()

    if not player:
        return

    try:

        send_console_command(
            f"whitelist add {player}"
        )

        bot.send_message(
            message.chat.id,

            "🔐 <b>Whitelist Add</b>\n\n"
            f"👤 <code>{player}</code>\n"
            "✅ تم إرسال الأمر."
        )

    except Exception as exc:

        bot.send_message(
            message.chat.id,

            "❌ <b>فشل</b>\n\n"
            f"<code>{str(exc)[:1000]}</code>"
        )


# ============================================================
# WHITELIST REMOVE
# ============================================================

def whitelist_remove_start(chat_id):

    msg = bot.send_message(
        chat_id,
        "➖ أرسل اسم اللاعب:"
    )

    bot.register_next_step_handler(
        msg,
        whitelist_remove_execute
    )


def whitelist_remove_execute(message):

    player = (
        message.text or ""
    ).strip()

    if not player:
        return

    try:

        send_console_command(
            f"whitelist remove {player}"
        )

        bot.send_message(
            message.chat.id,

            "🔐 <b>Whitelist Remove</b>\n\n"
            f"👤 <code>{player}</code>\n"
            "✅ تم إرسال الأمر."
        )

    except Exception as exc:

        bot.send_message(
            message.chat.id,

            "❌ <b>فشل</b>\n\n"
            f"<code>{str(exc)[:1000]}</code>"
        )


# ============================================================
# WHITELIST LIST
# ============================================================

def whitelist_list(chat_id):

    try:

        send_console_command(
            "whitelist list"
        )

        bot.send_message(
            chat_id,

            "📋 <b>Whitelist</b>\n\n"
            "📤 تم إرسال <code>whitelist list</code>."
        )

    except Exception as exc:

        bot.send_message(
            chat_id,

            "❌ <b>فشل</b>\n\n"
            f"<code>{str(exc)[:1000]}</code>"
        )


# ============================================================
# SAY
# ============================================================

def do_say(chat_id):

    msg = bot.send_message(
        chat_id,
        "💬 أرسل الرسالة:"
    )

    bot.register_next_step_handler(
        msg,
        say_execute
    )


def say_execute(message):

    text = (
        message.text or ""
    ).strip()

    if not text:
        return

    try:

        send_console_command(
            f"say {text}"
        )

        bot.send_message(
            message.chat.id,
            "💬 ✅ تم إرسال الرسالة إلى Discord Bot."
        )

    except Exception as exc:

        bot.send_message(
            message.chat.id,

            "❌ <b>فشل</b>\n\n"
            f"<code>{str(exc)[:1000]}</code>"
        )


@bot.message_handler(commands=["say"])
def say_command(message):
    do_say(message.chat.id)


# ============================================================
# BROADCAST
# ============================================================

def do_broadcast(chat_id):

    msg = bot.send_message(
        chat_id,
        "📢 أرسل رسالة Broadcast:"
    )

    bot.register_next_step_handler(
        msg,
        broadcast_execute
    )


def broadcast_execute(message):

    text = (
        message.text or ""
    ).strip()

    if not text:
        return

    try:

        send_console_command(
            f"say {text}"
        )

        bot.send_message(
            message.chat.id,
            "📢 ✅ تم إرسال Broadcast."
        )

    except Exception as exc:

        bot.send_message(
            message.chat.id,

            "❌ <b>فشل</b>\n\n"
            f"<code>{str(exc)[:1000]}</code>"
        )


@bot.message_handler(commands=["broadcast"])
def broadcast_command(message):
    do_broadcast(message.chat.id)


# ============================================================
# CALLBACKS
# ============================================================

@bot.callback_query_handler(
    func=lambda call: True
)
def callback_handler(call):

    chat_id = call.message.chat.id

    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass

    if call.data == "status":
        do_status(chat_id)
        return

    if call.data == "players":
        do_players(chat_id)
        return

    if call.data == "console":
        do_console(chat_id)
        return

    if call.data == "whitelist":
        whitelist_menu(chat_id)
        return

    if call.data == "wl_add":
        whitelist_add_start(chat_id)
        return

    if call.data == "wl_remove":
        whitelist_remove_start(chat_id)
        return

    if call.data == "wl_list":
        whitelist_list(chat_id)
        return

    if call.data == "say":
        do_say(chat_id)
        return

    if call.data == "broadcast":
        do_broadcast(chat_id)
        return

    if call.data == "refresh":

        try:
            bot.edit_message_reply_markup(
                chat_id,
                call.message.message_id,
                reply_markup=main_keyboard()
            )
        except Exception:
            pass

        return


# ============================================================
# HEALTH SERVER
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
            b"Telegram Discord Bridge is running."
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
        f"Health server listening on port {PORT}"
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
                f"Telegram polling error: {exc}"
            )

            time.sleep(5)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print(
        "=========================================="
    )

    print(
        "Telegram → Discord → Minecraft Bridge"
    )

    print(
        "Aternos: DISABLED"
    )

    print(
        "Start: DISABLED"
    )

    print(
        "Stop: DISABLED"
    )

    print(
        "Restart: DISABLED"
    )

    print(
        "Console: ENABLED"
    )

    print(
        "Whitelist: ENABLED"
    )

    print(
        "Players: ENABLED"
    )

    print(
        "Discord API: ENABLED"
    )

    print(
        "=========================================="
    )

    # اختبار Discord عند بدء التشغيل
    test_discord()

    threading.Thread(
        target=run_health_server,
        daemon=True
    ).start()

    run_bot()
