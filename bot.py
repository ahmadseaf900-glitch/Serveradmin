import os
import re
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
    ""
).strip()

# موجود في Render للتوافق مع إعداداتك.
# لا يُستخدم لتحديد الأوامر المسموحة.
CONSOLE_WHITELIST = os.getenv(
    "CONSOLE_WHITELIST",
    "say,whitelist,list,online,save-all"
).strip()

PORT = int(
    os.getenv("PORT", "10000")
)

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN غير موجود في Environment Variables"
    )

if not DISCORD_TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN غير موجود في Environment Variables"
    )

if not DISCORD_CHANNEL_ID:
    raise RuntimeError(
        "DISCORD_CHANNEL_ID غير موجود في Environment Variables"
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
# DISCORD API
# ============================================================

DISCORD_API = "https://discord.com/api/v10"


def discord_headers():
    return {
        "Authorization": f"Bot {DISCORD_TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "MinecraftTelegramManager/1.0"
    }


def send_discord_message(content):
    """
    إرسال رسالة حقيقية إلى قناة Discord.
    """

    if not content:
        raise ValueError(
            "رسالة Discord فارغة"
        )

    url = (
        f"{DISCORD_API}/channels/"
        f"{DISCORD_CHANNEL_ID}/messages"
    )

    response = requests.post(
        url,
        headers=discord_headers(),
        json={
            "content": content
        },
        timeout=15
    )

    if response.status_code not in (200, 201):
        raise RuntimeError(
            f"Discord API Error "
            f"{response.status_code}: "
            f"{response.text[:1000]}"
        )

    return response.json()


def send_console_command(command):
    """
    إرسال أمر Console إلى بوت Discord.

    مهم:
    بوت Discord الموجود عندك يجب أن يكون مبرمجًا
    على اعتبار الرسائل التي تصل بهذه الصيغة أو
    تنفيذها عبر DiscordSRV/Bridge.
    """

    command = str(
        command or ""
    ).strip()

    if not command:
        raise ValueError(
            "الأمر فارغ"
        )

    # صيغة موحدة يستطيع بوت Discord عندك
    # التقاطها وتحويلها إلى Minecraft Console.
    content = f"!console {command}"

    return send_discord_message(
        content
    )


def send_discord_bridge(command):
    """
    إرسال أمر للـ Discord Bridge.
    """

    command = str(
        command or ""
    ).strip()

    if not command:
        raise ValueError(
            "الأمر فارغ"
        )

    return send_discord_message(
        command
    )


# ============================================================
# TELEGRAM KEYBOARD
# ============================================================

def main_keyboard():

    markup = types.InlineKeyboardMarkup(
        row_width=2
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
        ),

        types.InlineKeyboardButton(
            "📊 Status",
            callback_data="status"
        )
    )

    markup.add(

        types.InlineKeyboardButton(
            "📢 Broadcast",
            callback_data="broadcast"
        ),

        types.InlineKeyboardButton(
            "💬 Say",
            callback_data="say"
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

    bot.send_message(

        message.chat.id,

        "🤖 <b>بوت إدارة Minecraft عبر DiscordSRV</b>\n\n"
        "اختر العملية:",

        reply_markup=main_keyboard()
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

        "📚 <b>الأوامر</b>\n\n"
        "/start — لوحة التحكم\n"
        "/console — Console\n"
        "/players — اللاعبين\n"
        "/status — Status\n"
        "/whitelist — Whitelist\n"
        "/say — إرسال رسالة\n"
        "/broadcast — Broadcast"
    )


# ============================================================
# /CONSOLE
# ============================================================

@bot.message_handler(
    commands=["console"]
)
def console_command_start(message):

    msg = bot.send_message(

        message.chat.id,

        "🖥️ <b>Console</b>\n\n"
        "أرسل أي أمر Minecraft تريد إرساله.\n\n"
        "مثال:\n"
        "<code>say Hello</code>\n"
        "<code>gamemode creative Player</code>\n"
        "<code>time set day</code>"
    )

    bot.register_next_step_handler(
        msg,
        console_command
    )


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

        send_console_command(
            command
        )

        bot.send_message(

            message.chat.id,

            "🖥️ <b>Console</b>\n\n"
            f"📤 <code>{command}</code>\n\n"
            "✅ تم إرسال الأمر إلى Discord."
        )

    except Exception as exc:

        bot.send_message(

            message.chat.id,

            "❌ <b>فشل إرسال الأمر</b>\n\n"
            f"<code>{str(exc)[:1000]}</code>"
        )


# ============================================================
# /PLAYERS
# ============================================================

@bot.message_handler(
    commands=["players"]
)
def players_command(message):

    try:

        send_console_command(
            "list"
        )

        bot.send_message(

            message.chat.id,

            "👥 <b>Players</b>\n\n"
            "📤 تم إرسال <code>list</code> "
            "إلى Discord Bridge.\n\n"
            "سيقوم بوت Discord/DiscordSRV بإرسال نتيجة اللاعبين."
        )

    except Exception as exc:

        bot.send_message(

            message.chat.id,

            "❌ فشل الطلب:\n"
            f"<code>{str(exc)[:1000]}</code>"
        )


# ============================================================
# /STATUS
# ============================================================

@bot.message_handler(
    commands=["status"]
)
def status_command(message):

    try:

        send_console_command(
            "list"
        )

        bot.send_message(

            message.chat.id,

            "📊 <b>Status</b>\n\n"
            "📤 تم إرسال طلب الحالة إلى Discord Bridge."
        )

    except Exception as exc:

        bot.send_message(

            message.chat.id,

            "❌ فشل طلب Status:\n"
            f"<code>{str(exc)[:1000]}</code>"
        )


# ============================================================
# /WHITELIST
# ============================================================

@bot.message_handler(
    commands=["whitelist"]
)
def whitelist_command(message):

    markup = types.InlineKeyboardMarkup(
        row_width=2
    )

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

        message.chat.id,

        "🔐 <b>Whitelist</b>\n\n"
        "اختر العملية:",

        reply_markup=markup
    )


# ============================================================
# WHITELIST ADD
# ============================================================

def whitelist_add_start(chat_id):

    msg = bot.send_message(

        chat_id,

        "➕ أرسل اسم اللاعب لإضافته إلى Whitelist:"
    )

    bot.register_next_step_handler(
        msg,
        whitelist_add
    )


def whitelist_add(message):

    player = (
        message.text or ""
    ).strip()

    if not re.fullmatch(
        r"[A-Za-z0-9_]{1,16}",
        player
    ):

        bot.send_message(
            message.chat.id,
            "❌ اسم Minecraft غير صالح."
        )

        return

    try:

        send_console_command(
            f"whitelist add {player}"
        )

        bot.send_message(

            message.chat.id,

            "🔐 <b>Whitelist Add</b>\n\n"
            f"👤 اللاعب: <code>{player}</code>\n"
            "✅ تم إرسال الأمر إلى Discord."
        )

    except Exception as exc:

        bot.send_message(

            message.chat.id,

            "❌ فشل:\n"
            f"<code>{str(exc)[:1000]}</code>"
        )


# ============================================================
# WHITELIST REMOVE
# ============================================================

def whitelist_remove_start(chat_id):

    msg = bot.send_message(

        chat_id,

        "➖ أرسل اسم اللاعب لحذفه من Whitelist:"
    )

    bot.register_next_step_handler(
        msg,
        whitelist_remove
    )


def whitelist_remove(message):

    player = (
        message.text or ""
    ).strip()

    if not re.fullmatch(
        r"[A-Za-z0-9_]{1,16}",
        player
    ):

        bot.send_message(
            message.chat.id,
            "❌ اسم Minecraft غير صالح."
        )

        return

    try:

        send_console_command(
            f"whitelist remove {player}"
        )

        bot.send_message(

            message.chat.id,

            "🔐 <b>Whitelist Remove</b>\n\n"
            f"👤 اللاعب: <code>{player}</code>\n"
            "✅ تم إرسال الأمر إلى Discord."
        )

    except Exception as exc:

        bot.send_message(

            message.chat.id,

            "❌ فشل:\n"
            f"<code>{str(exc)[:1000]}</code>"
        )


# ============================================================
# SAY
# ============================================================

def say_start(chat_id):

    msg = bot.send_message(

        chat_id,

        "💬 أرسل الرسالة التي تريد إرسالها إلى Minecraft:"
    )

    bot.register_next_step_handler(
        msg,
        say_message
    )


def say_message(message):

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

            "💬 <b>Say</b>\n\n"
            f"📤 <code>{text}</code>\n\n"
            "✅ تم الإرسال إلى Discord."
        )

    except Exception as exc:

        bot.send_message(

            message.chat.id,

            "❌ فشل:\n"
            f"<code>{str(exc)[:1000]}</code>"
        )


# ============================================================
# BROADCAST
# ============================================================

def broadcast_start(chat_id):

    msg = bot.send_message(

        chat_id,

        "📢 أرسل رسالة الـBroadcast:"
    )

    bot.register_next_step_handler(
        msg,
        broadcast_message
    )


def broadcast_message(message):

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

            "📢 <b>Broadcast</b>\n\n"
            "✅ تم إرسال الرسالة إلى Discord Bridge."
        )

    except Exception as exc:

        bot.send_message(

            message.chat.id,

            "❌ فشل:\n"
            f"<code>{str(exc)[:1000]}</code>"
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


    if call.data == "console":

        console_command_start(
            call.message
        )

        return


    if call.data == "players":

        players_command(
            call.message
        )

        return


    if call.data == "status":

        status_command(
            call.message
        )

        return


    if call.data == "whitelist":

        whitelist_command(
            call.message
        )

        return


    if call.data == "wl_add":

        whitelist_add_start(
            chat_id
        )

        return


    if call.data == "wl_remove":

        whitelist_remove_start(
            chat_id
        )

        return


    if call.data == "wl_list":

        send_console_command(
            "whitelist list"
        )

        bot.send_message(

            chat_id,

            "📋 <b>
