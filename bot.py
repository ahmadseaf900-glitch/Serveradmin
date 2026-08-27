import os
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests
import telebot
from telebot import types

=========================================================

Aternos library

=========================================================

try:
from python_aternos import Client as AternosClient
ATERNOS_LIBRARY_OK = True
ATERNOS_IMPORT_ERROR = ""
except Exception as e:
AternosClient = None
ATERNOS_LIBRARY_OK = False
ATERNOS_IMPORT_ERROR = str(e)

=========================================================

Environment Variables

=========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID", "").strip()

ATERNOS_USERNAME = os.getenv("ATERNOS_USERNAME", "").strip()
ATERNOS_PASSWORD = os.getenv("ATERNOS_PASSWORD", "").strip()
ATERNOS_SERVER = os.getenv(
"ATERNOS_SERVER",
"MACESMP37.aternos.me"
).strip()

if not BOT_TOKEN:
raise RuntimeError(
"BOT_TOKEN غير موجود في Render Environment Variables"
)

if not DISCORD_TOKEN:
print("⚠️ DISCORD_TOKEN غير موجود.")

if not DISCORD_CHANNEL_ID:
print("⚠️ DISCORD_CHANNEL_ID غير موجود.")

=========================================================

Telegram Bot

=========================================================

bot = telebot.TeleBot(
BOT_TOKEN,
parse_mode="HTML"
)

=========================================================

Aternos session

=========================================================

_aternos_client = None
_aternos_account = None
_aternos_server = None

_aternos_lock = threading.Lock()

=========================================================

Minecraft commands

=========================================================

DIRECT_COMMANDS = {
"op",
"deop",
"kick",
"ban",
"pardon",
"tp",
"teleport",
"give",
"gamemode",
"effect",
"time",
"weather",
"difficulty",
"gamerule",
"save-all",
"save-on",
"save-off",
"stop",
"reload",
"plugins",
"version",
"seed",
"locate",
"kill",
"list",
"online",
"whitelist",
}

CONSOLE_WHITELIST = {
x.strip().lower().lstrip("/")
for x in os.getenv(
"CONSOLE_WHITELIST",
"say,whitelist,list,online,save-all,op,deop,kick,ban,pardon,tp,give,gamemode"
).split(",")
if x.strip()
}

=========================================================

Discord

=========================================================

if DISCORD_CHANNEL_ID:
DISCORD_URL = (
f"https://discord.com/api/v10/channels/"
f"{DISCORD_CHANNEL_ID}/messages"
)
else:
DISCORD_URL = ""

DISCORD_HEADERS = {
"Authorization": f"Bot {DISCORD_TOKEN}",
"Content-Type": "application/json",
}

=========================================================

Discord functions

=========================================================

def send_to_discord(content):
if not DISCORD_TOKEN or not DISCORD_CHANNEL_ID:
return False, "Discord TOKEN أو CHANNEL ID غير مضبوط."

try:
    response = requests.post(
        DISCORD_URL,
        headers=DISCORD_HEADERS,
        json={"content": content},
        timeout=15,
    )

    if response.status_code not in (200, 201, 204):
        print(
            "Discord API:",
            response.status_code,
            response.text[:500],
            flush=True
        )

        return False, response.text

    return True, "OK"

except requests.RequestException as exc:
    print(
        "Discord connection error:",
        exc,
        flush=True
    )

    return False, str(exc)

def send_console(command):
command = command.strip().lstrip("/")

if not command:
    return False, "الأمر فارغ."

return send_to_discord(command)

def command_allowed(command):
command = command.strip().lstrip("/")

if not command:
    return False

first = command.split()[0].lower()

return (
    first in CONSOLE_WHITELIST
    or first in DIRECT_COMMANDS
)

=========================================================

Aternos

=========================================================

def reset_aternos_session():
global _aternos_client
global _aternos_account
global _aternos_server

_aternos_client = None
_aternos_account = None
_aternos_server = None

def get_aternos_server():
global _aternos_client
global _aternos_account
global _aternos_server

if not ATERNOS_LIBRARY_OK:
    return (
        None,
        "❌ مكتبة Aternos غير متاحة.\n"
        f"تفاصيل الاستيراد: {ATERNOS_IMPORT_ERROR}"
    )

if not ATERNOS_USERNAME:
    return None, "❌ ATERNOS_USERNAME غير موجود في Render."

if not ATERNOS_PASSWORD:
    return None, "❌ ATERNOS_PASSWORD غير موجود في Render."

with _aternos_lock:

    try:

        if _aternos_server is not None:
            return _aternos_server, None

        print(
            "🔐 تسجيل الدخول إلى Aternos...",
            flush=True
        )

        client = AternosClient()

        client.login(
            ATERNOS_USERNAME,
            ATERNOS_PASSWORD
        )

        account = client.account

        servers = account.list_servers()

        wanted = ATERNOS_SERVER.lower().strip()

        for server in servers:

            address = str(
                getattr(
                    server,
                    "address",
                    ""
                )
            ).lower().strip()

            name = str(
                getattr(
                    server,
                    "name",
                    ""
                )
            ).lower().strip()

            if (
                wanted == address
                or wanted == name
                or wanted in address
            ):

                _aternos_client = client
                _aternos_account = account
                _aternos_server = server

                print(
                    f"✅ تم العثور على السيرفر: {address}",
                    flush=True
                )

                return server, None

        return (
            None,
            f"❌ لم أجد السيرفر:\n{ATERNOS_SERVER}"
        )

    except Exception as exc:

        reset_aternos_session()

        print(
            "❌ Aternos login/error:",
            repr(exc),
            flush=True
        )

        return (
            None,
            f"{type(exc).__name__}: {exc}"
        )

def aternos_action(action):

server, error = get_aternos_server()

if error:
    return False, error

try:

    if action == "start":

        result = server.start()

        return (
            True,
            str(result)
            if result is not None
            else "تم إرسال طلب التشغيل."
        )

    if action == "stop":

        result = server.stop()

        return (
            True,
            str(result)
            if result is not None
            else "تم إرسال طلب الإيقاف."
        )

    if action == "restart":

        result = server.restart()

        return (
            True,
            str(result)
            if result is not None
            else "تم إرسال طلب إعادة التشغيل."
        )

    if action == "status":

        result = getattr(
            server,
            "status",
            None
        )

        if callable(result):
            result = result()

        return (
            True,
            str(result)
            if result is not None
            else "الحالة غير متاحة."
        )

    return False, "عملية Aternos غير معروفة."

except Exception as exc:

    reset_aternos_session()

    print(
        "❌ Aternos action error:",
        repr(exc),
        flush=True
    )

    return (
        False,
        f"{type(exc).__name__}: {exc}"
    )

=========================================================

Render Health Server

=========================================================

class HealthHandler(BaseHTTPRequestHandler):

def do_GET(self):

    self.send_response(200)

    self.send_header(
        "Content-type",
        "text/plain"
    )

    self.end_headers()

    self.wfile.write(
        b"Telegram Minecraft Server Bot is running!"
    )

def log_message(self, format, *args):
    return

def start_web_server():

port = int(
    os.environ.get(
        "PORT",
        "10000"
    )
)

server = HTTPServer(
    ("0.0.0.0", port),
    HealthHandler
)

print(
    f"🌐 Web server running on port {port}",
    flush=True
)

server.serve_forever()

threading.Thread(
target=start_web_server,
daemon=True
).start()

=========================================================

Main Menu

=========================================================

def main_menu():

markup = types.InlineKeyboardMarkup(
    row_width=2
)

markup.add(
    types.InlineKeyboardButton(
        "🟢 Status",
        callback_data="status"
    ),
    types.InlineKeyboardButton(
        "▶️ Start",
        callback_data="aternos_start"
    )
)

markup.add(
    types.InlineKeyboardButton(
        "⏹ Stop",
        callback_data="server_stop"
    ),
    types.InlineKeyboardButton(
        "🔄 Restart",
        callback_data="server_restart"
    )
)

markup.add(
    types.InlineKeyboardButton(
        "👥 Players",
        callback_data="players"
    ),
    types.InlineKeyboardButton(
        "🖥 Console",
        callback_data="console"
    )
)

markup.add(
    types.InlineKeyboardButton(
        "🔌 Plugins",
        callback_data="plugins"
    ),
    types.InlineKeyboardButton(
        "📜 Skripts",
        callback_data="skripts"
    )
)

markup.add(
    types.InlineKeyboardButton(
        "🟢 Whitelist",
        callback_data="whitelist"
    ),
    types.InlineKeyboardButton(
        "👑 Admin",
        callback_data="admin"
    )
)

markup.add(
    types.InlineKeyboardButton(
        "📢 Say",
        callback_data="say"
    )
)

return markup

=========================================================

/start

=========================================================

@bot.message_handler(commands=["start"])
def start_command(message):

telegram_id = message.from_user.id

username = (
    message.from_user.username
    or "بدون username"
)

print(
    f"[START] Telegram ID: {telegram_id} | "
    f"Username: @{username}",
    flush=True
)

bot.send_message(
    message.chat.id,

    "🤖 <b>Telegram → Discord → DiscordSRV</b>\n\n"
    "🟢 <b>البوت يعمل.</b>\n\n"
    f"🆔 <b>Telegram ID:</b> "
    f"<code>{telegram_id}</code>\n\n"
    "🎮 <b>اختر العملية:</b>",

    reply_markup=main_menu()
)

=========================================================

/console

=========================================================

@bot.message_handler(commands=["console"])
def console_command(message):

command = message.text.partition(" ")[2].strip()

if not command:

    bot.reply_to(
        message,
        "مثال:\n"
        "<code>/console list</code>"
    )

    return

if not command_allowed(command):

    bot.reply_to(
        message,
        "⛔ الأمر غير مسموح."
    )

    return

ok, detail = send_console(command)

if ok:

    bot.reply_to(
        message,
        "✅ <b>تم إرسال الأمر.</b>\n\n"
        f"🎮 <code>{command}</code>"
    )

else:

    bot.reply_to(
        message,
        f"❌ فشل:\n<code>{detail}</code>"
    )

=========================================================

/say

=========================================================

@bot.message_handler(commands=["say"])
def say_command(message):

text = message.text.partition(" ")[2].strip()

if not text:

    bot.reply_to(
        message,
        "مثال:\n"
        "<code>/say أهلاً باللاعبين!</code>"
    )

    return

ok, detail = send_console(
    "say " + text
)

if ok:

    bot.reply_to(
        message,
        "📢 تم إرسال الرسالة للسيرفر."
    )

else:

    bot.reply_to(
        message,
        f"❌ فشل:\n<code>{detail}</code>"
    )

=========================================================

/whitelist

=========================================================

@bot.message_handler(commands=["whitelist"])
def whitelist_command(message):

args = (
    message.text
    .partition(" ")[2]
    .strip()
    .split()
)

if (
    len(args) < 1
    or args[0].lower()
    not in {
        "add",
        "remove",
        "list"
    }
):

    bot.reply_to(
        message,

        "<code>/whitelist add Player</code>\n"
        "<code>/whitelist remove Player</code>\n"
        "<code>/whitelist list</code>"
    )

    return

action = args[0].lower()

if action == "list":

    command = "whitelist list"

elif (
    len(args) == 2
    and re.fullmatch(
        r"[A-Za-z0-9_]{1,16}",
        args[1]
    )
):

    command = (
        f"whitelist "
        f"{action} "
        f"{args[1]}"
    )

else:

    bot.reply_to(
        message,
        "❌ اسم اللاعب غير صالح أو ناقص."
    )

    return

ok, detail = send_console(command)

if ok:

    bot.reply_to(
        message,
        "✅ تم إرسال أمر Whitelist."
    )

else:

    bot.reply_to(
        message,
        f"❌ فشل:\n<code>{detail}</code>"
    )

=========================================================

Direct Minecraft commands

=========================================================

@bot.message_handler(
func=lambda message:
bool(message.text)
and message.text.startswith("/")
)
def direct_admin_command(message):

raw = message.text[1:].strip()

if not raw:
    return

command_name = (
    raw.split()[0]
    .lower()
)

# استثناء أوامر البوت الخاصة
if command_name in {
    "start",
    "console",
    "say",
    "whitelist"
}:
    return

if command_name not in DIRECT_COMMANDS:

    bot.reply_to(
        message,
        "❌ الأمر غير موجود.\n"
        "استخدم /start."
    )

    return

ok, detail = send_console(raw)

if ok:

    bot.reply_to(
        message,

        "✅ <b>تم إرسال الأمر إلى DiscordSRV.</b>\n\n"
        f"🎮 <code>{raw}</code>"
    )

else:

    bot.reply_to(
        message,
        f"❌ فشل:\n<code>{detail}</code>"
    )

=========================================================

Callback buttons

=========================================================

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

# -------------------------
# Status
# -------------------------

if call.data == "status":

    bot.send_message(
        chat_id,
        "⏳ جاري فحص حالة Aternos..."
    )

    ok, detail = aternos_action(
        "status"
    )

    if ok:

        bot.send_message(
            chat_id,
            "🟢 <b>Aternos Status</b>\n\n"
            f"<code>{detail}</code>"
        )

    else:

        bot.send_message(
            chat_id,
            f"❌ <b>فشل فحص الحالة</b>\n\n"
            f"<code>{detail}</code>"
        )

# -------------------------
# Start
# -------------------------

elif call.data == "aternos_start":

    bot.send_message(
        chat_id,
        "⏳ جاري إرسال طلب تشغيل Aternos..."
    )

    ok, detail = aternos_action(
        "start"
    )

    if ok:

        bot.send_message(
            chat_id,
            "▶️ <b>تم إرسال طلب تشغيل Aternos.</b>\n\n"
            f"<code>{detail}</code>"
        )

    else:

        bot.send_message(
            chat_id,
            "❌ <b>فشل التشغيل</b>\n\n"
            f"<code>{detail}</code>"
        )

# -------------------------
# Stop
# -------------------------

elif call.data == "server_stop":

    bot.send_message(
        chat_id,
        "⏳ جاري إيقاف السيرفر..."
    )

    ok, detail = aternos_action(
        "stop"
    )

    if ok:

        bot.send_message(
            chat_id,
            "⏹️ <b>تم إرسال طلب إيقاف Aternos.</b>\n\n"
            f"<code>{detail}</code>"
        )

    else:

        bot.send_message(
            chat_id,
            "❌ <b>فشل الإيقاف</b>\n\n"
            f"<code>{detail}</code>"
        )

# -------------------------
# Restart
# -------------------------

elif call.data == "server_restart":

    bot.send_message(
        chat_id,
        "⏳ جاري إعادة تشغيل السيرفر..."
    )

    ok, detail = aternos_action(
        "restart"
    )

    if ok:

        bot.send_message(
            chat_id,
            "🔄 <b>تم إرسال طلب Restart.</b>\n\n"
            f"<code>{detail}</code>"
        )

    else:

        bot.send_message(
            chat_id,
            "❌ <b>فشل Restart</b>\n\n"
            f"<code>{detail}</code>"
        )

# -------------------------
# Console
# -------------------------

elif call.data == "console":

    bot.send_message(
        chat_id,
        "🖥 <b>Console</b>\n\n"
        "أرسل الأمر بهذا الشكل:\n"
        "<code>/console list</code>"
    )

# -------------------------
# Say
# -------------------------

elif call.data == "say":

    bot.send_message(
        chat_id,
        "📢 أرسل:\n"
        "<code>/say رسالتك</code>"
    )

# -------------------------
# Players
# -------------------------

elif call.data == "players":

    ok, detail = send_console(
        "list"
    )

    if ok:

        bot.send_message(
            chat_id,
            "👥 تم طلب قائمة اللاعبين."
        )

    else:

        bot.send_message(
            chat_id,
            f"❌ فشل:\n<code>{detail}</code>"
        )

# -------------------------
# Plugins
# -------------------------

elif call.data == "plugins":

    ok, detail = send_console(
        "plugins"
    )

    if ok:

        bot.send_message(
            chat_id,
            "🔌 تم إرسال أمر Plugins."
        )

    else:

        bot.send_message(
            chat_id,
            f"❌ فشل:\n<code>{detail}</code>"
        )

# -------------------------
# Skripts
# -------------------------

elif call.data == "skripts":

    bot.send_message(
        chat_id,

        "📜 <b>Skripts</b>\n\n"
        "يمكنك إرسال أوامر Skript عبر Console.\n\n"
        "مثال:\n"
        "<code>/console skript reload all</code>"
    )

# -------------------------
# Whitelist
# -------------------------

elif call.data == "whitelist":

    bot.send_message(
        chat_id,

        "🟢 <b>Whitelist</b>\n\n"
        "<code>/whitelist add Player</code>\n"
        "<code>/whitelist remove Player</code>\n"
        "<code>/whitelist list</code>"
    )

# -------------------------
# Admin
# -------------------------

elif call.data == "admin":

    bot.send_message(
        chat_id,

        "👑 <b>أوامر الإدارة</b>\n\n"

        "<code>/op Player</code>\n"
        "<code>/deop Player</code>\n"
        "<code>/kick Player [سبب]</code>\n"
        "<code>/ban Player [سبب]</code>\n"
        "<code>/pardon Player</code>\n"
        "<code>/gamemode creative Player</code>\n"
        "<code>/tp Player Player2</code>\n"
        "<code>/give Player item 1</code>\n"
        "<code>/save-all</code>\n"
        "<code>/plugins</code>\n"
        "<code>/reload</code>"
    )

=========================================================

Unknown messages

=========================================================

@bot.message_handler(
func=lambda message: True
)
def unknown_message(message):

bot.send_message(
    message.chat.id,
    "استخدم /start لفتح لوحة التحكم.",
    reply_markup=main_menu()
)

=========================================================

Start

=========================================================

if name == "main":

print(
    "🤖 Telegram Bot Started",
    flush=True
)

print(
    f"🆔 Aternos Server: {ATERNOS_SERVER}",
    flush=True
)

if ATERNOS_LIBRARY_OK:

    print(
        "✅ python_aternos import OK",
        flush=True
    )

else:

    print(
        "❌ python_aternos import FAILED:",
        ATERNOS_IMPORT_ERROR,
        flush=True
    )

# إزالة Webhook
try:

    bot.remove_webhook()

    print(
        "✅ Webhook removed",
        flush=True
    )

except Exception as e:

    print(
        "⚠️ Webhook removal:",
        e,
        flush=True
    )

print(
    "🚀 Starting Telegram polling...",
    flush=True
)

while True:

    try:

        bot.infinity_polling(
            skip_pending=True,
            timeout=60,
            long_polling_timeout=60
        )

    except telebot.apihelper.ApiTelegramException as e:

        error_text = str(e)

        if (
            "409" in error_text
            or "Conflict" in error_text
        ):

            print(
                "⚠️ Telegram 409 Conflict — "
                "هناك نسخة أخرى من البوت تعمل. "
                "إعادة المحاولة بعد 10 ثوانٍ...",
                flush=True
            )

            time.sleep(10)

            continue

        if (
            "401" in error_text
            or "Unauthorized" in error_text
        ):

            print(
                "❌ Telegram 401 Unauthorized — "
                "BOT_TOKEN غير صحيح.",
                flush=True
            )

            time.sleep(30)

            continue

        print(
            f"❌ Telegram API error: {e}",
            flush=True
        )

        time.sleep(10)

    except Exception as e:

        print(
            f"❌ Polling error: {e}",
            flush=True
        )

        time.sleep(10)
