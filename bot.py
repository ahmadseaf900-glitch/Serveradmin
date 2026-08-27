import os
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import telebot
from telebot import types
import requests

try:
    from python_aternos import Client as AternosClient
except ImportError:
    AternosClient = None


# =========================================================
# إعدادات البوت
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")
ATERNOS_USERNAME = os.getenv("ATERNOS_USERNAME")
ATERNOS_PASSWORD = os.getenv("ATERNOS_PASSWORD")
ATERNOS_SERVER = os.getenv("ATERNOS_SERVER", "MACESMP37.aternos.me")

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN غير موجود في Render Environment Variables")
if not DISCORD_TOKEN:
    raise RuntimeError("❌ DISCORD_TOKEN غير موجود في Render Environment Variables")
if not DISCORD_CHANNEL_ID:
    raise RuntimeError("❌ DISCORD_CHANNEL_ID غير موجود في Render Environment Variables")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

ADMIN_IDS = {
    int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}

CONSOLE_WHITELIST = {
    x.strip().lower().lstrip("/")
    for x in os.getenv(
        "CONSOLE_WHITELIST",
        "say,whitelist,list,online,save-all"
    ).split(",") if x.strip()
}

# أوامر الإدارة المتاحة من Telegram.
# أوامر تشغيل/إيقاف Aternos ليست ضمن هذه القائمة لأنها تحتاج API/تحكمًا
# خاصًا بالاستضافة، وليست أوامر Minecraft Console عادية.
ADMIN_COMMANDS = {
    "list", "online", "say", "whitelist", "op", "deop", "kick", "ban",
    "pardon", "tp", "gamemode", "give", "effect", "time", "weather",
    "difficulty", "gamerule", "save-all", "save-on", "save-off", "stop",
    "reload", "plugins", "version", "seed", "locate", "teleport", "kill"
}

# أوامر Telegram المباشرة التي تبدأ بـ / وتُرسل إلى Minecraft Console.
DIRECT_COMMANDS = {
    "op", "deop", "kick", "ban", "pardon", "tp", "teleport", "give",
    "gamemode", "effect", "time", "weather", "difficulty", "gamerule",
    "save-all", "save-on", "save-off", "stop", "reload", "plugins", "version",
    "seed", "locate", "kill", "list", "online", "whitelist"
}

DISCORD_URL = f"https://discord.com/api/v10/channels/{DISCORD_CHANNEL_ID}/messages"
DISCORD_HEADERS = {
    "Authorization": f"Bot {DISCORD_TOKEN}",
    "Content-Type": "application/json",
}

def is_admin(message):
    return message.from_user.id in ADMIN_IDS

def admin_only(message):
    if not is_admin(message):
        bot.reply_to(message, "⛔ <b>ليس لديك صلاحية Admin.</b>")
        return False
    return True

def send_to_discord(content):
    try:
        response = requests.post(
            DISCORD_URL,
            headers=DISCORD_HEADERS,
            json={"content": content},
            timeout=15,
        )
        if response.status_code not in (200, 201):
            print("Discord API:", response.status_code, response.text[:500])
            return False, response.text
        return True, "OK"
    except requests.RequestException as exc:
        print("Discord connection error:", exc)
        return False, str(exc)

def send_console(command):
    # قناة DiscordConsoleChannelId تنفذ الرسالة نفسها كأمر Console.
    # لا نضيف !c هنا؛ !c مخصص لأوامر Console القادمة من قناة الدردشة.
    return send_to_discord(command.strip().lstrip("/"))

def command_allowed(command):
    command = command.strip().lstrip("/").lower()
    first = command.split()[0] if command.split() else ""
    return first in CONSOLE_WHITELIST or first in ADMIN_COMMANDS


# =========================================================
# Aternos — تحكم بالحساب المخصص للبوت
# =========================================================

_aternos_client = None
_aternos_account = None
_aternos_server = None
_aternos_lock = threading.Lock()


def get_aternos_server():
    """تسجيل الدخول مرة واحدة ثم العثور على السيرفر بالعنوان."""
    global _aternos_client, _aternos_account, _aternos_server

    if AternosClient is None:
        return None, "python-aternos غير مثبت. أضفه إلى requirements.txt."

    if not ATERNOS_USERNAME or not ATERNOS_PASSWORD:
        return None, "ضع ATERNOS_USERNAME و ATERNOS_PASSWORD في Render."

    with _aternos_lock:
        try:
            if _aternos_server is not None:
                return _aternos_server, None

            client = AternosClient()
            client.login(ATERNOS_USERNAME, ATERNOS_PASSWORD)
            account = client.account
            servers = account.list_servers()

            wanted = ATERNOS_SERVER.lower().strip()
            for server in servers:
                address = str(getattr(server, "address", "")).lower().strip()
                name = str(getattr(server, "name", "")).lower().strip()
                if wanted in {address, name} or wanted in address:
                    _aternos_client = client
                    _aternos_account = account
                    _aternos_server = server
                    return server, None

            return None, f"لم أجد السيرفر {ATERNOS_SERVER} في حساب Aternos."
        except Exception as exc:
            _aternos_client = None
            _aternos_account = None
            _aternos_server = None
            return None, str(exc)


def aternos_action(action):
    server, error = get_aternos_server()
    if error:
        return False, error
    try:
        if action == "start":
            result = server.start()
        elif action == "stop":
            result = server.stop()
        elif action == "restart":
            result = server.restart()
        elif action == "status":
            result = getattr(server, "status", None)
            if callable(result):
                result = result()
        else:
            return False, "عملية Aternos غير معروفة."
        return True, str(result) if result is not None else "OK"
    except Exception as exc:
        # إذا انتهت الجلسة، أعد تسجيل الدخول في الطلب التالي.
        global _aternos_client, _aternos_account, _aternos_server
        _aternos_client = None
        _aternos_account = None
        _aternos_server = None
        return False, str(exc)


# =========================================================
# Web Server لـ Render
# =========================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Telegram Bot is running!")

    def log_message(self, format, *args):
        return


def start_web_server():
    port = int(os.environ.get("PORT", 10000))

    server = HTTPServer(("0.0.0.0", port), HealthHandler)

    print(f"🌐 Web server running on port {port}")

    server.serve_forever()


threading.Thread(
    target=start_web_server,
    daemon=True
).start()


# =========================================================
# القائمة الرئيسية
# =========================================================

def main_menu():

    markup = types.InlineKeyboardMarkup(row_width=2)

    markup.add(
        types.InlineKeyboardButton("🟢 حالة السيرفر", callback_data="status"),
        types.InlineKeyboardButton("▶️ تشغيل Aternos", callback_data="aternos_start"),
    )
    markup.add(
        types.InlineKeyboardButton("⏹ إيقاف السيرفر", callback_data="server_stop"),
        types.InlineKeyboardButton("🔄 Restart", callback_data="server_restart"),
    )
    markup.add(
        types.InlineKeyboardButton("🖥 Console", callback_data="console"),
        types.InlineKeyboardButton("📢 Say", callback_data="say"),
    )
    markup.add(types.InlineKeyboardButton("🟢 Whitelist", callback_data="whitelist"))
    markup.add(types.InlineKeyboardButton("👑 Admin", callback_data="admin"))

    return markup


# =========================================================
# /start
# =========================================================

@bot.message_handler(commands=["start"])
def start_command(message):

    text = (
        "🤖 <b>Telegram → Discord → DiscordSRV</b>\n\n"
        "🟢 البوت يعمل. اختر العملية:"
    )

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=main_menu()
    )


@bot.message_handler(commands=["console"])
def console_command(message):
    if not admin_only(message): return
    command = message.text.partition(" ")[2].strip()
    if not command:
        bot.reply_to(message, "مثال: <code>/console list</code>")
        return
    if not command_allowed(command):
        bot.reply_to(message, "⛔ الأمر غير موجود في Console Whitelist.")
        return
    ok, detail = send_console(command)
    bot.reply_to(message, "✅ تم إرسال الأمر إلى DiscordSRV." if ok else f"❌ فشل: <code>{detail}</code>")

@bot.message_handler(commands=["say"])
def say_command(message):
    if not admin_only(message): return
    text = message.text.partition(" ")[2].strip()
    if not text:
        bot.reply_to(message, "مثال: <code>/say أهلاً باللاعبين!</code>")
        return
    ok, detail = send_console("say " + text)
    bot.reply_to(message, "📢 تم إرسال الرسالة للسيرفر." if ok else f"❌ فشل: <code>{detail}</code>")

@bot.message_handler(commands=["whitelist"])
def whitelist_command(message):
    if not admin_only(message): return
    args = message.text.partition(" ")[2].strip().split()
    if len(args) < 1 or args[0].lower() not in {"add", "remove", "list"}:
        bot.reply_to(message, "<code>/whitelist add Player</code>\n<code>/whitelist remove Player</code>\n<code>/whitelist list</code>")
        return
    action = args[0].lower()
    if action == "list":
        command = "whitelist list"
    elif len(args) == 2 and re.fullmatch(r"[A-Za-z0-9_]{1,16}", args[1]):
        command = f"whitelist {action} {args[1]}"
    else:
        bot.reply_to(message, "❌ اسم اللاعب غير صالح أو ناقص.")
        return
    ok, detail = send_console(command)
    bot.reply_to(message, "✅ تم إرسال أمر الـWhitelist." if ok else f"❌ فشل: <code>{detail}</code>")


@bot.message_handler(func=lambda message: bool(message.text) and message.text.startswith("/"))
def direct_admin_command(message):
    """تنفيذ أوامر الإدارة المكتوبة مباشرة مثل /op aizenx."""
    if not admin_only(message):
        return

    raw = message.text[1:].strip()
    if not raw:
        return

    command_name = raw.split()[0].lower()

    if command_name not in DIRECT_COMMANDS:
        bot.reply_to(message, "❌ الأمر غير موجود. استخدم /start لعرض الأوامر المتاحة.")
        return

    ok, detail = send_console(raw)
    if ok:
        bot.reply_to(
            message,
            "✅ <b>تم إرسال الأمر إلى DiscordSRV.</b>\n\n"
            f"🎮 <code>{raw}</code>"
        )
    else:
        bot.reply_to(message, f"❌ فشل إرسال الأمر: <code>{detail}</code>")


# =========================================================
# الأزرار
# =========================================================

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):

    chat_id = call.message.chat.id

    try:

        bot.answer_callback_query(call.id)

    except Exception:
        pass


    # -------------------------
    # Status
    # -------------------------

    if call.data == "console":
        bot.send_message(chat_id, "🖥 أرسل <code>/console list</code> — الأوامر تمر عبر Whitelist.")
    elif call.data == "status":
        if not is_admin(call.message):
            bot.send_message(chat_id, "⛔ غير مصرح لك.")
            return
        ok, detail = aternos_action("status")
        bot.send_message(chat_id, f"🟢 <b>Aternos Status</b>\n\n<code>{detail}</code>" if ok else f"❌ <code>{detail}</code>")
    elif call.data == "say":
        bot.send_message(chat_id, "📢 أرسل <code>/say رسالتك</code>")
    elif call.data == "whitelist":
        bot.send_message(chat_id, "🟢 <code>/whitelist add Player</code>\n<code>/whitelist remove Player</code>\n<code>/whitelist list</code>")
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
    elif call.data == "aternos_start":
        if not is_admin(call.message):
            bot.send_message(chat_id, "⛔ غير مصرح لك.")
            return
        ok, detail = aternos_action("start")
        bot.send_message(chat_id, "▶️ <b>تم إرسال طلب تشغيل Aternos.</b>" if ok else f"❌ فشل التشغيل:\n<code>{detail}</code>")
    elif call.data == "server_stop":
        if not is_admin(call.message):
            bot.send_message(chat_id, "⛔ غير مصرح لك.")
            return
        ok, detail = aternos_action("stop")
        bot.send_message(
            chat_id,
            "⏹️ <b>تم إرسال طلب إيقاف Aternos.</b>" if ok
            else f"❌ فشل إيقاف Aternos: <code>{detail}</code>"
        )
    elif call.data == "server_restart":
        if not is_admin(call.message):
            bot.send_message(chat_id, "⛔ غير مصرح لك.")
            return
        ok, detail = aternos_action("restart")
        bot.send_message(chat_id, "🔄 <b>تم إرسال طلب Restart إلى Aternos.</b>" if ok else f"❌ فشل Restart: <code>{detail}</code>")

@bot.message_handler(func=lambda message: True)
def unknown_message(message):
    if is_admin(message):
        bot.send_message(message.chat.id, "استخدم /start أو الأوامر الموجودة في القائمة.", reply_markup=main_menu())
    else:
        bot.reply_to(message, "⛔ غير مصرح لك باستخدام هذا البوت.")


# =========================================================
# تشغيل البوت
# =========================================================

if __name__ == "__main__":

    print("🤖 Telegram Bot Started")

    # مهم جدًا:
    # إزالة Webhook حتى لا يتعارض مع polling
    try:
        bot.remove_webhook()
        print("✅ Webhook removed")
    except Exception as e:
        print("⚠️ Webhook removal:", e)


    print("🚀 Starting Telegram polling...")


    # إعادة المحاولة تلقائيًا عند حدوث 409 بدل توقف البوت.
    # 409 يعني أن Telegram يرى getUpdates آخر لنفس التوكن.
    while True:
        try:
            bot.infinity_polling(
                skip_pending=True,
                timeout=60,
                long_polling_timeout=60
            )
        except telebot.apihelper.ApiTelegramException as e:
            error_text = str(e)

            if "409" in error_text or "Conflict" in error_text:
                print("⚠️ Telegram 409 Conflict — إعادة المحاولة بعد 10 ثوانٍ...")
                time.sleep(10)
                continue

            if "401" in error_text or "Unauthorized" in error_text:
                print("❌ Telegram 401 Unauthorized — تحقق من BOT_TOKEN في Render.")
                time.sleep(30)
                continue

            print(f"❌ Telegram API error: {e}")
            time.sleep(10)

        except Exception as e:
            print(f"❌ Polling error: {e}")
            time.sleep(10)
