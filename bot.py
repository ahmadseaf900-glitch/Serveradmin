import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import telebot
from telebot import types
from mcstatus import JavaServer


# =========================================================
# إعدادات البوت
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN غير موجود في Render Environment Variables")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")


# =========================================================
# إعدادات سيرفر Minecraft
# =========================================================

SERVER_HOST = "MACESMP37.aternos.me"
SERVER_PORT = 44114


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
# فحص السيرفر
# =========================================================

def get_server_status():

    try:

        server = JavaServer(
            SERVER_HOST,
            SERVER_PORT
        )

        status = server.status()

        return {
            "online": True,
            "players": status.players.online,
            "max_players": status.players.max,
            "version": status.version.name,
            "latency": round(status.latency)
        }

    except Exception as e:

        print("Server status error:", e)

        return {
            "online": False,
            "players": 0,
            "max_players": 0,
            "version": "Unknown",
            "latency": 0
        }


# =========================================================
# القائمة الرئيسية
# =========================================================

def main_menu():

    markup = types.InlineKeyboardMarkup(row_width=2)

    start_button = types.InlineKeyboardButton(
        "🟢 Start",
        callback_data="start_server"
    )

    stop_button = types.InlineKeyboardButton(
        "🔴 Stop",
        callback_data="stop_server"
    )

    restart_button = types.InlineKeyboardButton(
        "🔄 Restart",
        callback_data="restart_server"
    )

    status_button = types.InlineKeyboardButton(
        "📊 Status",
        callback_data="status_server"
    )

    players_button = types.InlineKeyboardButton(
        "👥 Players",
        callback_data="players_server"
    )

    markup.add(
        start_button,
        stop_button
    )

    markup.add(
        restart_button,
        status_button
    )

    markup.add(
        players_button
    )

    return markup


# =========================================================
# /start
# =========================================================

@bot.message_handler(commands=["start"])
def start_command(message):

    text = (
        "🤖 <b>البوت يعمل بنجاح!</b>\n\n"
        "أهلاً بك 👋\n\n"
        "🎮 <b>بوت إدارة سيرفر ماينكرافت</b>\n\n"
        f"🌐 السيرفر:\n"
        f"<code>{SERVER_HOST}:{SERVER_PORT}</code>\n\n"
        "اختر العملية:"
    )

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=main_menu()
    )


# =========================================================
# أي رسالة نصية
# =========================================================

@bot.message_handler(func=lambda message: True)
def text_handler(message):

    if message.text == "Start":
        bot.send_message(
            message.chat.id,
            "🟢 <b>Start</b>\n\n"
            "⚠️ تشغيل Aternos مباشرة يحتاج ربط API/طريقة تشغيل خاصة.\n"
            "حاليًا أستطيع فحص حالة السيرفر."
        )

    elif message.text == "Stop":

        bot.send_message(
            message.chat.id,
            "🔴 <b>Stop</b>\n\n"
            "⚠️ إيقاف Aternos يحتاج ربط API."
        )

    elif message.text == "Restart":

        bot.send_message(
            message.chat.id,
            "🔄 <b>Restart</b>\n\n"
            "⚠️ إعادة التشغيل تحتاج ربط Aternos API."
        )

    elif message.text == "Status":

        send_status(message.chat.id)

    elif message.text == "Players":

        send_players(message.chat.id)

    else:

        bot.send_message(
            message.chat.id,
            "اختر أحد الأزرار الموجودة في القائمة 👇",
            reply_markup=main_menu()
        )


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

    if call.data == "status_server":

        send_status(chat_id)


    # -------------------------
    # Players
    # -------------------------

    elif call.data == "players_server":

        send_players(chat_id)


    # -------------------------
    # Start
    # -------------------------

    elif call.data == "start_server":

        bot.send_message(
            chat_id,
            "🟢 <b>Start</b>\n\n"
            "⚠️ تشغيل سيرفر Aternos يحتاج ربط API.\n\n"
            "📌 السيرفر الحالي:\n"
            f"<code>{SERVER_HOST}:{SERVER_PORT}</code>"
        )


    # -------------------------
    # Stop
    # -------------------------

    elif call.data == "stop_server":

        bot.send_message(
            chat_id,
            "🔴 <b>Stop</b>\n\n"
            "⚠️ إيقاف السيرفر يحتاج ربط Aternos API."
        )


    # -------------------------
    # Restart
    # -------------------------

    elif call.data == "restart_server":

        bot.send_message(
            chat_id,
            "🔄 <b>Restart</b>\n\n"
            "⚠️ إعادة تشغيل السيرفر تحتاج ربط Aternos API."
        )


# =========================================================
# إرسال حالة السيرفر
# =========================================================

def send_status(chat_id):

    bot.send_message(
        chat_id,
        "⏳ جاري فحص السيرفر..."
    )

    status = get_server_status()

    if status["online"]:

        text = (
            "🟢 <b>السيرفر Online</b>\n\n"
            f"🌐 <b>IP:</b>\n"
            f"<code>{SERVER_HOST}:{SERVER_PORT}</code>\n\n"
            f"👥 اللاعبين: "
            f"<b>{status['players']}/{status['max_players']}</b>\n\n"
            f"🎮 الإصدار: <code>{status['version']}</code>\n"
            f"📡 Ping: <b>{status['latency']}ms</b>"
        )

    else:

        text = (
            "🔴 <b>السيرفر Offline</b>\n\n"
            f"🌐 <code>{SERVER_HOST}:{SERVER_PORT}</code>\n\n"
            "قد يكون السيرفر متوقفًا أو أن Aternos نائم."
        )

    bot.send_message(
        chat_id,
        text,
        reply_markup=main_menu()
    )


# =========================================================
# اللاعبين
# =========================================================

def send_players(chat_id):

    try:

        server = JavaServer(
            SERVER_HOST,
            SERVER_PORT
        )

        status = server.status()

        if status.players.online == 0:

            bot.send_message(
                chat_id,
                "👥 <b>اللاعبون</b>\n\n"
                "لا يوجد لاعبين حاليًا.",
                reply_markup=main_menu()
            )

            return


        players = []

        if status.players.sample:

            for player in status.players.sample:

                players.append(
                    f"👤 {player.name}"
                )


        if players:

            text = (
                "👥 <b>اللاعبون المتصلون</b>\n\n"
                + "\n".join(players)
            )

        else:

            text = (
                "👥 <b>اللاعبون</b>\n\n"
                f"عدد اللاعبين: {status.players.online}\n\n"
                "⚠️ السيرفر لم يعطِ أسماء اللاعبين."
            )


        bot.send_message(
            chat_id,
            text,
            reply_markup=main_menu()
        )


    except Exception:

        bot.send_message(
            chat_id,
            "🔴 السيرفر Offline أو لا يمكن الوصول إليه.",
            reply_markup=main_menu()
        )


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


    bot.infinity_polling(
        skip_pending=True,
        timeout=60,
        long_polling_timeout=60
        )
