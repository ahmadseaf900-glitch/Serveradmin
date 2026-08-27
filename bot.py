from aternos import start as aternos_start_action
from aternos import stop as aternos_stop_action
from aternos import restart as aternos_restart_action
from aternos import get_status as aternos_get_status

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):

chat_id = call.message.chat.id

try:
    bot.answer_callback_query(call.id)
except Exception:
    pass

# -------------------------
# Aternos Start
# -------------------------

if call.data == "aternos_start":

    result = aternos_start_action()

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            "🌐 فتح Aternos",
            url=result["url"]
        )
    )

    bot.send_message(
        chat_id,
        "▶️ <b>تشغيل السيرفر</b>\n\n"
        "Aternos لا يسمح للبوتات الخارجية بتشغيل السيرفر عبر API.\n"
        "افتح لوحة Aternos واضغط <b>Start</b>.",
        reply_markup=markup
    )

# -------------------------
# Aternos Stop
# -------------------------

elif call.data == "server_stop":

    result = aternos_stop_action()

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            "🌐 فتح Aternos",
            url=result["url"]
        )
    )

    bot.send_message(
        chat_id,
        "⏹️ <b>إيقاف السيرفر</b>\n\n"
        "افتح لوحة Aternos واضغط <b>Stop</b>.",
        reply_markup=markup
    )

# -------------------------
# Aternos Restart
# -------------------------

elif call.data == "server_restart":

    result = aternos_restart_action()

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            "🌐 فتح Aternos",
            url=result["url"]
        )
    )

    bot.send_message(
        chat_id,
        "🔄 <b>Restart</b>\n\n"
        "افتح لوحة Aternos ونفّذ إعادة التشغيل من هناك.",
        reply_markup=markup
    )
