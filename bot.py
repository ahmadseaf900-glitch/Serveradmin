import os
import re
import time
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import telebot
from telebot import types
from mcstatus import JavaServer, BedrockServer

import aternos


BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

PORT = int(
    os.getenv("PORT", "10000")
)

STATUS_TIMEOUT = float(
    os.getenv("STATUS_TIMEOUT", "5")
)

ATERNOS_URL = os.getenv(
    "ATERNOS_URL",
    "https://aternos.org/server/"
).strip()

CONSOLE_WHITELIST = {
    x.strip()
    for x in os.getenv(
        "CONSOLE_WHITELIST",
        ""
    ).split(",")
    if x.strip()
}


if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN غير موجود."
    )


bot = telebot.TeleBot(
    BOT_TOKEN,
    parse_mode="HTML",
    threaded=True
)


def clean_host(host):
    host = str(host or "").strip()

    host = re.sub(
        r"^https?://",
        "",
        host,
        flags=re.IGNORECASE
    )

    return host.split("/")[0].strip()


def mc_status(host, port):
    host = clean_host(host)

    try:
        server = JavaServer(
            host,
            port,
            timeout=STATUS_TIMEOUT
        )

        data = server.status(tries=2)

        return {
            "online": True,
            "edition": "Java",
            "players": data.players.online,
            "max": data.players.max,
            "ping": round(data.latency),
            "version": str(data.version.name),
            "host": host,
            "port": port,
        }

    except Exception:
        pass

    try:
        server = BedrockServer(
            host,
            port,
            timeout=STATUS_TIMEOUT
        )

        data = server.status(tries=2)

        return {
            "online": True,
            "edition": "Bedrock",
            "players": data.players.online,
            "max": data.players.max,
            "ping": round(data.latency),
            "version": str(data.version.name),
            "host": host,
            "port": port,
        }

    except Exception:
        pass

    return {
        "online": False,
        "edition": "Unknown",
        "players": 0,
        "max": 0,
        "ping": None,
        "version": None,
        "host": host,
        "port": port,
    }


def get_mc_address():
    info = aternos.server_info()

    address = str(
        info.get(
            "address",
            os.getenv(
                "MC_SERVER_HOST",
                "MACESMP37.aternos.me"
            )
        )
    )

    if ":" in address:
        parts = address.rsplit(":", 1)

        if parts[1].isdigit():
            return parts[0], int(parts[1])

    return address, 25565


def status_text():
    host, port = get_mc_address()

    data = mc_status(
        host,
        port
    )

    if not data["online"]:
        return (
            "🔴 <b>السيرفر Offline</b>\n\n"
            f"🌐 العنوان:\n"
            f"<code>{host}:{port}</code>"
        )

    return (
        "🟢 <b>السيرفر Online</b>\n\n"
        f"👥 اللاعبين: "
        f"<b>{data['players']}/{data['max']}</b>\n"
        f"📶 Ping: <b>{data['ping']}ms</b>\n"
        f"🎮 الإصدار: <b>{data['version']}</b>\n"
        f"🧩 النوع: <b>{data['edition']}</b>\n"
        f"🌐 العنوان:\n"
        f"<code>{host}:{port}</code>"
    )


def keyboard():
    k = types.InlineKeyboardMarkup(row_width=2)

    k.add(
        types.InlineKeyboardButton(
            "▶️ Start",
            callback_data="start"
        ),
        types.InlineKeyboardButton(
            "⏹️ Stop",
            callback_data="stop"
        )
    )

    k.add(
        types.InlineKeyboardButton(
            "🔄 Restart",
            callback_data="restart"
        ),
        types.InlineKeyboardButton(
            "📊 Status",
            callback_data="status"
        )
    )

    k.add(
        types.InlineKeyboardButton(
            "🖥️ Console",
            callback_data="console"
        ),
        types.InlineKeyboardButton(
            "👥 Players",
            callback_data="players"
        )
    )

    k.add(
        types.InlineKeyboardButton(
            "✅ Whitelist",
            callback_data="whitelist"
        ),
        types.InlineKeyboardButton(
            "👑 OP",
            callback_data="op"
        )
    )

    k.add(
        types.InlineKeyboardButton(
            "🌐 Aternos",
            url=ATERNOS_URL
        )
    )

    return k


@bot.message_handler(commands=["start"])
def start_command(message):
    try:
        text = (
            "🤖 <b>بوت إدارة Minecraft</b>\n\n"
            f"{status_text()}\n\n"
            "اختر العملية:"
        )

    except Exception as exc:
        text = (
            "🤖 <b>بوت إدارة Minecraft</b>\n\n"
            "⚠️ تعذر قراءة حالة Aternos:\n"
            f"<code>{str(exc)[:500]}</code>"
        )

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=keyboard()
    )


@bot.message_handler(
    commands=["status"]
)
def status_command(message):
    try:
        bot.send_message(
            message.chat.id,
            status_text(),
            reply_markup=keyboard()
        )
    except Exception as exc:
        bot.send_message(
            message.chat.id,
            "❌ خطأ:\n"
            f"<code>{str(exc)[:500]}</code>"
        )


def execute_aternos(action):
    try:
        if action == "start":
            return aternos.start()

        if action == "stop":
            return aternos.stop()

        if action == "restart":
            return aternos.restart()

        raise ValueError("عملية غير معروفة.")

    except Exception as exc:
        return {
            "success": False,
            "message": str(exc)
        }


@bot.callback_query_handler(
    func=lambda call: True
)
def callback_handler(call):
    chat_id = call.message.chat.id
    action = call.data

    try:
        bot.answer_callback_query(
            call.id
        )
    except Exception:
        pass

    if action in (
        "start",
        "stop",
        "restart"
    ):
        msg = bot.send_message(
            chat_id,
            "⏳ <b>جاري تنفيذ العملية...</b>"
        )

        result = execute_aternos(action)

        if result.get("success"):
            if action == "start":
                title = "▶️ <b>Start</b>"

            elif action == "stop":
                title = "⏹️ <b>Stop</b>"

            else:
                title = "🔄 <b>Restart</b>"

            text = (
                f"{title}\n\n"
                f"✅ {result.get('message', 'تم التنفيذ.')}"
            )

        else:
            text = (
                "❌ <b>فشلت العملية</b>\n\n"
                f"<code>{result.get('message', 'خطأ غير معروف')[:1000]}</code>"
            )

        try:
            bot.edit_message_text(
                text,
                chat_id,
                msg.message_id,
                reply_markup=keyboard()
            )
        except Exception:
            bot.send_message(
                chat_id,
                text,
                reply_markup=keyboard()
            )

        return

    if action == "status":
        try:
            text = status_text()
        except Exception as exc:
            text = (
                "❌ فشل فحص الحالة:\n"
                f"<code>{str(exc)[:500]}</code>"
            )

        bot.send_message(
            chat_id,
            text,
            reply_markup=keyboard()
        )

        return

    if action == "players":
        try:
            players = aternos.get_players()

            if not players:
                text = "👥 <b>Players</b>\n\nلا يوجد لاعبون متصلون."

            else:
                lines = "\n".join(
                    f"• <code>{p}</code>"
                    for p in players
                )

                text = (
                    "👥 <b>اللاعبون المتصلون</b>\n\n"
                    f"{lines}"
                )

        except Exception as exc:
            text = (
                "❌ فشل جلب اللاعبين:\n"
                f"<code>{str(exc)[:500]}</code>"
            )

        bot.send_message(
            chat_id,
            text,
            reply_markup=keyboard()
        )

        return

    if action == "whitelist":
        text = (
            "✅ <b>Whitelist</b>\n\n"
            "اختر العملية:\n\n"
            "/whitelist — عرض القائمة\n"
            "/wladd Player — إضافة\n"
            "/wlremove Player — حذف"
        )

        bot.send_message(
            chat_id,
            text,
            reply_markup=keyboard()
        )

        return

    if action == "op":
        text = (
            "👑 <b>OP</b>\n\n"
            "/op Player — إعطاء OP\n"
            "/deop Player — إزالة OP"
        )

        bot.send_message(
            chat_id,
            text,
            reply_markup=keyboard()
        )

        return

    if action == "console":
        bot.send_message(
            chat_id,
            "🖥️ <b>Console</b>\n\n"
            "أرسل الأمر بهذا الشكل:\n"
            "<code>/console say Hello</code>\n\n"
            "يجب أن يكون حساب Telegram موجودًا في "
            "<code>CONSOLE_WHITELIST</code>."
        )

        return


@bot.message_handler(commands=["whitelist"])
def whitelist_command(message):
    try:
        players = aternos.whitelist_list()

        if not players:
            text = (
                "✅ <b>Whitelist</b>\n\n"
                "القائمة فارغة."
            )
        else:
            text = (
                "✅ <b>Whitelist</b>\n\n"
                + "\n".join(
                    f"• <code>{p}</code>"
                    for p in players
                )
            )

    except Exception as exc:
        text = (
            "❌ فشل قراءة Whitelist:\n"
            f"<code>{str(exc)[:1000]}</code>"
        )

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=keyboard()
    )


@bot.message_handler(commands=["wladd"])
def whitelist_add_command(message):
    parts = message.text.split(maxsplit=1)

    if len(parts) != 2:
        bot.reply_to(
            message,
            "استخدم:\n<code>/wladd Player</code>"
        )
        return

    player = parts[1].strip()

    try:
        aternos.whitelist_add(player)

        bot.reply_to(
            message,
            f"✅ تم إضافة <code>{player}</code> إلى Whitelist."
        )

    except Exception as exc:
        bot.reply_to(
            message,
            "❌ فشل الإضافة:\n"
            f"<code>{str(exc)[:1000]}</code>"
        )


@bot.message_handler(commands=["wlremove"])
def whitelist_remove_command(message):
    parts = message.text.split(maxsplit=1)

    if len(parts) != 2:
        bot.reply_to(
            message,
            "استخدم:\n<code>/wlremove Player</code>"
        )
        return

    player = parts[1].strip()

    try:
        aternos.whitelist_remove(player)

        bot.reply_to(
            message,
            f"✅ تم حذف <code>{player}</code> من Whitelist."
        )

    except Exception as exc:
        bot.reply_to(
            message,
            "❌ فشل الحذف:\n"
            f"<code>{str(exc)[:1000]}</code>"
        )


@bot.message_handler(commands=["op"])
def op_command(message):
    parts = message.text.split(maxsplit=1)

    if len(parts) != 2:
        bot.reply_to(
            message,
            "استخدم:\n<code>/op Player</code>"
        )
        return

    player = parts[1].strip()

    try:
        aternos.op_add(player)

        bot.reply_to(
            message,
            f"👑 تم إعطاء OP للاعب <code>{player}</code>."
        )

    except Exception as exc:
        bot.reply_to(
            message,
            "❌ فشل OP:\n"
            f"<code>{str(exc)[:1000]}</code>"
        )


@bot.message_handler(commands=["deop"])
def deop_command(message):
    parts = message.text.split(maxsplit=1)

    if len(parts) != 2:
        bot.reply_to(
            message,
            "استخدم:\n<code>/deop Player</code>"
        )
        return

    player = parts[1].strip()

    try:
        aternos.op_remove(player)

        bot.reply_to(
            message,
            f"🚫 تم إزالة OP من <code>{player}</code>."
        )

    except Exception as exc:
        bot.reply_to(
            message,
            "❌ فشل DeOP:\n"
            f"<code>{str(exc)[:1000]}</code>"
        )


@bot.message_handler(commands=["console"])
def console_command(message):
    user_id = str(message.from_user.id)

    if CONSOLE_WHITELIST and user_id not in CONSOLE_WHITELIST:
        bot.reply_to(
            message,
            "⛔ ليس لديك صلاحية استخدام Console."
        )
        return

    parts = message.text.split(maxsplit=1)

    if len(parts) != 2:
        bot.reply_to(
            message,
            "استخدم:\n"
            "<code>/console say Hello</code>"
        )
        return

    command = parts[1].strip()

    bot.reply_to(
        message,
        "🖥️ تم استلام الأمر:\n"
        f"<code>{command}</code>\n\n"
        "⚠️ تنفيذ أوامر Console داخل اللعبة يحتاج قناة تنفيذ "
        "مباشرة مثل RCON أو Discord bot/bridge موجود عندك."
    )


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

    def log_message(self, format, *args):
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


def run_bot():
    while True:
        try:
            print("Telegram bot started.")

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


if __name__ == "__main__":
    health = threading.Thread(
        target=run_health_server,
        daemon=True
    )

    health.start()

    run_bot()
