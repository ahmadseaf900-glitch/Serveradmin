import os
import re
import time
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import telebot
from telebot import types
from mcstatus import JavaServer, BedrockServer

import aternos


# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

SERVER_HOST = os.getenv(
    "MC_SERVER_HOST",
    "MACESMP37.aternos.me"
).strip()

SERVER_PORT = int(
    os.getenv(
        "MC_SERVER_PORT",
        "25565"
    )
)

ATERNOS_URL = os.getenv(
    "ATERNOS_URL",
    "https://aternos.org/server/"
).strip()

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
        "BOT_TOKEN غير موجود في Environment Variables."
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
# USER SERVERS
# ============================================================

user_servers = {}
user_lock = threading.Lock()


def get_user_server(chat_id):
    """إرجاع السيرفر الخاص بالمستخدم."""
    with user_lock:
        return user_servers.get(
            chat_id,
            {
                "host": SERVER_HOST,
                "port": SERVER_PORT
            }
        )


def save_user_server(chat_id, host, port):
    """حفظ عنوان السيرفر للمستخدم."""
    with user_lock:
        user_servers[chat_id] = {
            "host": host,
            "port": int(port)
        }


# ============================================================
# ADDRESS
# ============================================================

def clean_host(host):
    """تنظيف عنوان السيرفر."""
    host = str(host).strip()

    host = re.sub(
        r"^https?://",
        "",
        host,
        flags=re.IGNORECASE
    )

    host = host.split("/")[0]

    return host.strip()


def parse_server_address(address):
    """تحليل host:port."""
    address = clean_host(address)

    if (
        ":" in address
        and address.rsplit(":", 1)[1].isdigit()
    ):
        host, port = address.rsplit(":", 1)
        return host, int(port)

    return address, 25565


# ============================================================
# REAL MINECRAFT STATUS
# ============================================================

def get_java_status(host, port):
    """فحص Minecraft Java."""
    server = JavaServer(
        host,
        port,
        timeout=STATUS_TIMEOUT
    )

    result = server.status(tries=2)

    return {
        "online": True,
        "edition": "Java",
        "host": host,
        "port": port,
        "players": result.players.online,
        "max_players": result.players.max,
        "latency": round(float(result.latency)),
        "version": str(result.version.name)
    }


def get_bedrock_status(host, port):
    """فحص Minecraft Bedrock."""
    server = BedrockServer(
        host,
        port,
        timeout=STATUS_TIMEOUT
    )

    result = server.status(tries=2)

    return {
        "online": True,
        "edition": "Bedrock",
        "host": host,
        "port": port,
        "players": result.players.online,
        "max_players": result.players.max,
        "latency": round(float(result.latency)),
        "version": str(result.version.name)
    }


def get_real_server_status(host, port):
    """
    فحص Java ثم Bedrock.

    Online لا تُعتبر صحيحة إلا إذا نجح اتصال Minecraft فعلياً.
    """
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
    except Exception as exc:
        return {
            "online": False,
            "edition": "Unknown",
            "host": host,
            "port": port,
            "players": 0,
            "max_players": 0,
            "latency": None,
            "version": None,
            "error": str(exc)
        }


# ============================================================
# FORMAT STATUS
# ============================================================

def format_status(data):
    """تحويل نتيجة الفحص إلى رسالة Telegram."""
    if not data["online"]:
        return (
            "🔴 <b>السيرفر Offline</b>\n\n"
            f"🌐 العنوان:\n"
            f"<code>{data['host']}:{data['port']}</code>\n\n"
            "📡 لم يستجب Minecraft."
        )

    latency = data.get("latency")

    ping = (
        f"{latency}ms"
        if latency is not None
        else "غير معروف"
    )

    version = data.get("version") or "غير معروف"

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
    """إنشاء لوحة التحكم."""
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
            "🌐 Aternos",
            url=ATERNOS_URL
        )
    )

    return markup


# ============================================================
# WAIT FOR MINECRAFT STATE
# ============================================================

def wait_for_state(
    host,
    port,
    desired_online,
    timeout=120
):
    """
    انتظار الحالة الحقيقية للسيرفر.

    لا نخبر المستخدم أن Start/Stop نجح
    إلا بعد التحقق من Minecraft.
    """
    started = time.time()

    while time.time() - started < timeout:

        status = get_real_server_status(
            host,
            port
        )

        if status["online"] == desired_online:
            return status

        time.sleep(5)

    return get_real_server_status(
        host,
        port
    )


# ============================================================
# START
# ============================================================

@bot.message_handler(commands=["start"])
def start_command(message):
    """عرض لوحة التحكم."""
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
        + format_status(status)
        + "\n\nاختر العملية:",
        reply_markup=main_keyboard()
    )


# ============================================================
# STATUS
# ============================================================

@bot.message_handler(
    commands=["status", "serverstatus"]
)
def status_command(message):
    """عرض الحالة الحقيقية."""
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
# SERVER
# ============================================================

@bot.message_handler(commands=["server"])
def server_command(message):
    """طلب عنوان سيرفر جديد."""
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
    """حفظ عنوان السيرفر."""
    try:
        host, port = parse_server_address(
            message.text
        )

        if not host:
            raise ValueError(
                "عنوان السيرفر فارغ."
            )

        save_user_server(
            message.chat.id,
            host,
            port
        )

        status = get_real_server_status(
            host,
            port
        )

        bot.send_message(
            message.chat.id,
            "✅ <b>تم حفظ السيرفر</b>\n\n"
            + format_status(status),
            reply_markup=main_keyboard()
        )

    except Exception as exc:
        bot.send_message(
            message.chat.id,
            "❌ فشل حفظ السيرفر:\n"
            f"<code>{str(exc)[:500]}</code>"
        )


# ============================================================
# CALLBACKS
# ============================================================

@bot.callback_query_handler(
    func=lambda call: True
)
def callback_handler(call):
    """معالجة أزرار البوت."""
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
    port = server["port"]

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    if call.data == "server_status":

        status = get_real_server_status(
            host,
            port
        )

        bot.send_message(
            chat_id,
            format_status(status),
            reply_markup=main_keyboard()
        )

        return

    # --------------------------------------------------------
    # START
    # --------------------------------------------------------

    if call.data == "aternos_start":

        bot.send_message(
            chat_id,
            "⏳ <b>جاري تشغيل السيرفر...</b>\n\n"
            "🔐 تسجيل الدخول إلى حساب Aternos..."
        )

        try:
            aternos.start()

            bot.send_message(
                chat_id,
                "▶️ تم إرسال أمر Start إلى Aternos.\n"
                "⏳ أنتظر تأكيد Minecraft..."
            )

            status = wait_for_state(
                host,
                port,
                True,
                180
            )

            if status["online"]:

                bot.send_message(
                    chat_id,
                    "🟢 <b>تم تشغيل السيرفر بنجاح!</b>\n\n"
                    + format_status(status),
                    reply_markup=main_keyboard()
                )

            else:

                bot.send_message(
                    chat_id,
                    "⚠️ تم إرسال أمر Start، "
                    "لكن لم أستطع تأكيد Online عبر Minecraft.\n\n"
                    + format_status(status),
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

    # --------------------------------------------------------
    # STOP
    # --------------------------------------------------------

    if call.data == "server_stop":

        bot.send_message(
            chat_id,
            "⏳ <b>جاري إيقاف السيرفر...</b>"
        )

        try:
            aternos.stop()

            bot.send_message(
                chat_id,
                "⏹️ تم إرسال أمر Stop.\n"
                "⏳ أنتظر تأكيد Minecraft..."
            )

            status = wait_for_state(
                host,
                port,
                False,
                120
            )

            if not status["online"]:

                bot.send_message(
                    chat_id,
                    "🔴 <b>تم إيقاف السيرفر بنجاح.</b>\n\n"
                    + format_status(status),
                    reply_markup=main_keyboard()
                )

            else:

                bot.send_message(
                    chat_id,
                    "⚠️ تم إرسال أمر Stop، "
                    "لكن السيرفر ما زال Online.",
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

    # --------------------------------------------------------
    # RESTART
    # --------------------------------------------------------

    if call.data == "server_restart":

        bot.send_message(
            chat_id,
            "🔄 <b>جاري إعادة تشغيل السيرفر...</b>"
        )

        try:
            aternos.restart()

            bot.send_message(
                chat_id,
                "🔄 تم إرسال أمر Restart.\n"
                "⏳ أنتظر عودة السيرفر..."
            )

            status = wait_for_state(
                host,
                port,
                True,
                180
            )

            if status["online"]:

                bot.send_message(
                    chat_id,
                    "🟢 <b>تمت إعادة التشغيل بنجاح!</b>\n\n"
                    + format_status(status),
                    reply_markup=main_keyboard()
                )

            else:

                bot.send_message(
                    chat_id,
                    "⚠️ تم إرسال Restart، "
                    "لكن لم أستطع تأكيد عودة السيرفر Online.",
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


# ============================================================
# IP
# ============================================================

@bot.message_handler(commands=["ip"])
def ip_command(message):
    """عرض IP."""
    server = get_user_server(
        message.chat.id
    )

    bot.send_message(
        message.chat.id,
        "🌐 <b>عنوان السيرفر</b>\n\n"
        f"<code>{server['host']}:{server['port']}</code>"
    )


# ============================================================
# HELP
# ============================================================

@bot.message_handler(commands=["help"])
def help_command(message):
    """عرض المساعدة."""
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
# UNKNOWN TEXT
# ============================================================

@bot.message_handler(
    func=lambda message: True,
    content_types=["text"]
)
def text_handler(message):
    """معالجة الرسائل النصية."""
    text = message.text.strip().lower()

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
        "الاى بي"
    ]:
        ip_command(message)
        return

    bot.send_message(
        message.chat.id,
        "استخدم /start لفتح لوحة التحكم."
    )


# ============================================================
# RENDER HEALTH SERVER
# ============================================================

class HealthHandler(BaseHTTPRequestHandler):
    """HTTP health endpoint لـ Render."""

    def do_GET(self):
        """الرد على HTTP GET."""
        self.send_response(200)

        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8"
        )

        self.end_headers()

        self.wfile.write(
            b"Telegram Minecraft Bot is running."
        )

    def log_message(self, format, *args):
        """منع سجلات HTTP المزعجة."""
        return


def run_health_server():
    """تشغيل Health Server."""
    server = HTTPServer(
        ("0.0.0.0", PORT),
        HealthHandler
    )

    print(
        f"Health server listening on {PORT}"
    )

    server.serve_forever()


# ============================================================
# TELEGRAM
# ============================================================

def run_bot():
    """تشغيل Telegram polling."""
    while True:

        try:

            print(
                "Telegram Minecraft Bot started."
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
        "========================================"
    )

    print(
        "Minecraft Telegram Server Manager"
    )

    print(
        f"Server: "
        f"{SERVER_HOST}:{SERVER_PORT}"
    )

    print(
        "Aternos control: ENABLED"
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
