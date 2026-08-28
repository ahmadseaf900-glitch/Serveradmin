import os
import time
import threading
import requests
import telebot
from telebot import types
from mcstatus import JavaServer

# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID", "").strip()

MC_SERVER_HOST = os.getenv(
    "MC_SERVER_HOST",
    "MACESMP37.aternos.me"
).strip()

MC_SERVER_PORT = int(
    os.getenv("MC_SERVER_PORT", "25565")
)

# ============================================================
# CHECK BOT TOKEN
# ============================================================

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN غير موجود في Environment Variables"
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
# DISCORD
# ============================================================

def discord_test():
    if not DISCORD_TOKEN:
        print("DISCORD_TOKEN غير موجود")
        return False

    try:
        response = requests.get(
            "https://discord.com/api/v10/users/@me",
            headers={
                "Authorization": f"Bot {DISCORD_TOKEN}"
            },
            timeout=15
        )

        print("===============================")
        print("========== DISCORD ==========")
        print("HTTP:", response.status_code)
        print("Response:", response.text)
        print("===============================")

        return response.status_code == 200

    except Exception as e:
        print("Discord error:", e)
        return False


def send_discord_message(text):
    if not DISCORD_TOKEN:
        return False

    if not DISCORD_CHANNEL_ID:
        return False

    # إذا وضعت رابط القناة بدل ID، نستخرج الـ ID الأخير
    channel_id = DISCORD_CHANNEL_ID.strip().rstrip("/").split("/")[-1]

    if not channel_id.isdigit():
        print("DISCORD_CHANNEL_ID غير صحيح:", DISCORD_CHANNEL_ID)
        return False

    url = (
        f"https://discord.com/api/v10/channels/"
        f"{channel_id}/messages"
    )

    try:
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bot {DISCORD_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "content": text
            },
            timeout=15
        )

        print(
            "Discord message:",
            response.status_code,
            response.text
        )

        return response.status_code in (200, 201)

    except Exception as e:
        print("Discord send error:", e)
        return False


# ============================================================
# MINECRAFT STATUS
# ============================================================

def get_minecraft_status():
    try:
        server = JavaServer.lookup(
            f"{MC_SERVER_HOST}:{MC_SERVER_PORT}"
        )

        status = server.status()

        players_online = status.players.online
        players_max = status.players.max

        version = "Unknown"

        try:
            version = status.version.name
        except Exception:
            pass

        return {
            "online": True,
            "players": players_online,
            "max_players": players_max,
            "version": version,
            "latency": round(status.latency)
        }

    except Exception as e:
        print("Minecraft status error:", e)

        return {
            "online": False,
            "players": 0,
            "max_players": 0,
            "version": "Unknown",
            "latency": 0
        }


# ============================================================
# /START
# ============================================================

@bot.message_handler(commands=["start"])
def start_command(message):

    text = (
        "🤖 <b>Server Admin</b>\n\n"
        "أهلاً بك في بوت إدارة السيرفر.\n\n"
        "📋 الأوامر:\n"
        "/server - حالة السيرفر\n"
        "/ip - معلومات الاتصال\n"
        "/players - اللاعبين\n"
        "/discord - اختبار Discord\n"
        "/help - المساعدة\n"
    )

    bot.send_message(
        message.chat.id,
        text
    )


# ============================================================
# /HELP
# ============================================================

@bot.message_handler(commands=["help"])
def help_command(message):

    text = (
        "📚 <b>مساعدة Server Admin</b>\n\n"
        "🟢 /server\n"
        "عرض حالة سيرفر Minecraft.\n\n"
        "🌐 /ip\n"
        "عرض عنوان السيرفر.\n\n"
        "👥 /players\n"
        "عرض عدد اللاعبين.\n\n"
        "💬 /discord\n"
        "اختبار اتصال Discord.\n"
    )

    bot.send_message(
        message.chat.id,
        text
    )


# ============================================================
# /IP
# ============================================================

@bot.message_handler(commands=["ip"])
def ip_command(message):

    bot.send_message(
        message.chat.id,
        (
            "🌐 <b>معلومات السيرفر</b>\n\n"
            f"Host: <code>{MC_SERVER_HOST}</code>\n"
            f"Port: <code>{MC_SERVER_PORT}</code>"
        )
    )


# ============================================================
# /SERVER
# ============================================================

@bot.message_handler(commands=["server"])
def server_command(message):

    msg = bot.send_message(
        message.chat.id,
        "🔎 جاري فحص سيرفر Minecraft..."
    )

    status = get_minecraft_status()

    if status["online"]:

        text = (
            "🟢 <b>السيرفر ONLINE</b>\n\n"
            f"👥 اللاعبين: "
            f"<b>{status['players']}/{status['max_players']}</b>\n"
            f"🎮 الإصدار: "
            f"<code>{status['version']}</code>\n"
            f"📡 Ping: "
            f"<b>{status['latency']} ms</b>\n\n"
            f"🌐 <code>{MC_SERVER_HOST}:{MC_SERVER_PORT}</code>"
        )

    else:

        text = (
            "🔴 <b>السيرفر OFFLINE</b>\n\n"
            f"🌐 <code>{MC_SERVER_HOST}:{MC_SERVER_PORT}</code>\n\n"
            "⚠️ لم أستطع الحصول على حالة السيرفر."
        )

    try:
        bot.edit_message_text(
            text,
            chat_id=message.chat.id,
            message_id=msg.message_id
        )
    except Exception:
        bot.send_message(
            message.chat.id,
            text
        )


# ============================================================
# /PLAYERS
# ============================================================

@bot.message_handler(commands=["players"])
def players_command(message):

    status = get_minecraft_status()

    if not status["online"]:
        bot.send_message(
            message.chat.id,
            "🔴 السيرفر Offline."
        )
        return

    try:
        server = JavaServer.lookup(
            f"{MC_SERVER_HOST}:{MC_SERVER_PORT}"
        )

        query = server.query()

        players = query.players.names or []

        if players:

            players_text = "\n".join(
                f"• {name}"
                for name in players
            )

            text = (
                "👥 <b>اللاعبون المتصلون:</b>\n\n"
                f"{players_text}\n\n"
                f"📊 العدد: "
                f"{len(players)}/{status['max_players']}"
            )

        else:

            text = (
                "👥 لا يوجد لاعبون حالياً.\n\n"
                f"📊 0/{status['max_players']}"
            )

        bot.send_message(
            message.chat.id,
            text
        )

    except Exception as e:

        print("Players error:", e)

        bot.send_message(
            message.chat.id,
            (
                "🟢 السيرفر Online\n"
                f"👥 اللاعبين: "
                f"{status['players']}/{status['max_players']}\n\n"
                "⚠️ تعذر الحصول على أسماء اللاعبين."
            )
        )


# ============================================================
# /DISCORD
# ============================================================

@bot.message_handler(commands=["discord"])
def discord_command(message):

    bot.send_message(
        message.chat.id,
        "🧪 جاري اختبار Discord..."
    )

    result = discord_test()

    if result:

        bot.send_message(
            message.chat.id,
            "🟢 Discord متصل بنجاح."
        )

    else:

        bot.send_message(
            message.chat.id,
            "🔴 فشل اتصال Discord."
        )


# ============================================================
# /DISCORD_SEND
# ============================================================

@bot.message_handler(commands=["discord_send"])
def discord_send_command(message):

    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:

        bot.send_message(
            message.chat.id,
            "استخدم:\n"
            "<code>/discord_send الرسالة</code>"
        )

        return

    text = parts[1].strip()

    if send_discord_message(text):

        bot.send_message(
            message.chat.id,
            "✅ تم إرسال الرسالة إلى Discord."
        )

    else:

        bot.send_message(
            message.chat.id,
            "❌ فشل إرسال الرسالة إلى Discord."
        )


# ============================================================
# BUTTON MENU
# ============================================================

@bot.message_handler(commands=["menu"])
def menu_command(message):

    markup = types.InlineKeyboardMarkup(
        row_width=2
    )

    markup.add(
        types.InlineKeyboardButton(
            "🖥 حالة السيرفر",
            callback_data="server_status"
        ),
        types.InlineKeyboardButton(
            "👥 اللاعبين",
            callback_data="players"
        ),
        types.InlineKeyboardButton(
            "🌐 IP",
            callback_data="server_ip"
        ),
        types.InlineKeyboardButton(
            "💬 Discord",
            callback_data="discord_test"
        )
    )

    bot.send_message(
        message.chat.id,
        "🎛 <b>لوحة Server Admin</b>",
        reply_markup=markup
    )


# ============================================================
# CALLBACK BUTTONS
# ============================================================

@bot.callback_query_handler(
    func=lambda call: True
)
def callback_handler(call):

    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass

    chat_id = call.message.chat.id

    if call.data == "server_status":

        status = get_minecraft_status()

        if status["online"]:

            text = (
                "🟢 <b>السيرفر ONLINE</b>\n\n"
                f"👥 {status['players']}/"
                f"{status['max_players']}\n"
                f"🎮 {status['version']}\n"
                f"📡 {status['latency']} ms"
            )

        else:

            text = (
                "🔴 <b>السيرفر OFFLINE</b>"
            )

        bot.edit_message_text(
            text,
            chat_id=chat_id,
            message_id=call.message.message_id
        )

    elif call.data == "players":

        status = get_minecraft_status()

        if not status["online"]:

            text = "🔴 السيرفر Offline."

        else:

            try:

                server = JavaServer.lookup(
                    f"{MC_SERVER_HOST}:{MC_SERVER_PORT}"
                )

                query = server.query()

                players = query.players.names or []

                if players:

                    text = (
                        "👥 <b>اللاعبون:</b>\n\n"
                        + "\n".join(
                            f"• {p}"
                            for p in players
                        )
                    )

                else:

                    text = "👥 لا يوجد لاعبون حالياً."

            except Exception:

                text = (
                    f"👥 المتصلون: "
                    f"{status['players']}/"
                    f"{status['max_players']}"
                )

        bot.edit_message_text(
            text,
            chat_id=chat_id,
            message_id=call.message.message_id
        )

    elif call.data == "server_ip":

        bot.edit_message_text(
            (
                "🌐 <b>IP السيرفر</b>\n\n"
                f"<code>{MC_SERVER_HOST}:"
                f"{MC_SERVER_PORT}</code>"
            ),
            chat_id=chat_id,
            message_id=call.message.message_id
        )

    elif call.data == "discord_test":

        result = discord_test()

        text = (
            "🟢 Discord متصل."
            if result
            else
            "🔴 Discord غير متصل."
        )

        bot.edit_message_text(
            text,
            chat_id=chat_id,
            message_id=call.message.message_id
        )


# ============================================================
# UNKNOWN COMMANDS
# ============================================================

@bot.message_handler(
    func=lambda message:
        message.text is not None
        and message.text.startswith("/")
)
def unknown_command(message):

    bot.send_message(
        message.chat.id,
        "❓ الأمر غير معروف.\n"
        "استخدم /help"
    )


# ============================================================
# HEALTH SERVER
# ============================================================

def run_health_server():

    from http.server import (
        BaseHTTPRequestHandler,
        HTTPServer
    )

    class Handler(BaseHTTPRequestHandler):

        def do_GET(self):

            self.send_response(200)
            self.send_header(
                "Content-Type",
                "text/plain; charset=utf-8"
            )
            self.end_headers()

            self.wfile.write(
                b"Server Admin Bot is running."
            )

        def log_message(
            self,
            format,
            *args
        ):
            return

    port = int(
        os.getenv("PORT", "10000")
    )

    server = HTTPServer(
        ("0.0.0.0", port),
        Handler
    )

    print(
        f"Health server running on port {port}"
    )

    server.serve_forever()


# ============================================================
# START
# ============================================================

def start_bot():

    print("===============================")
    print("ENV TEST")
    print(
        "BOT_TOKEN exists:",
        bool(BOT_TOKEN)
    )
    print(
        "DISCORD_TOKEN exists:",
        bool(DISCORD_TOKEN)
    )
    print(
        "DISCORD_TOKEN length:",
        len(DISCORD_TOKEN)
    )
    print(
        "DISCORD_CHANNEL_ID exists:",
        bool(DISCORD_CHANNEL_ID)
    )
    print(
        "DISCORD_CHANNEL_ID:",
        DISCORD_CHANNEL_ID
    )
    print(
        "Minecraft:",
        f"{MC_SERVER_HOST}:{MC_SERVER_PORT}"
    )
    print("===============================")

    discord_test()

    print("Telegram bot started.")

    # حذف أي Webhook قديم
    try:
        bot.remove_webhook()
        time.sleep(1)
    except Exception as e:
        print("Webhook removal:", e)

    # مهم: لا تشغل نسخة ثانية من البوت
    bot.infinity_polling(
        skip_pending=True,
        timeout=30,
        long_polling_timeout=30
    )


if __name__ == "__main__":

    # Health server في Thread
    health_thread = threading.Thread(
        target=run_health_server,
        daemon=True
    )

    health_thread.start()

    start_bot()
