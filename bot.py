import os
import telebot
from telebot import types

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN is not set")

bot = telebot.TeleBot(TOKEN)


@bot.message_handler(commands=["start"])
def start(message):
    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "🖥️ السيرفرات",
            callback_data="servers"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "ℹ️ المساعدة",
            callback_data="help"
        )
    )

    bot.send_message(
        message.chat.id,
        "👋 أهلاً بك في بوت إدارة السيرفرات!\n\n"
        "اختر من القائمة:",
        reply_markup=markup
    )


@bot.message_handler(commands=["help"])
def help_command(message):
    bot.send_message(
        message.chat.id,
        "📚 الأوامر:\n\n"
        "/start - القائمة الرئيسية\n"
        "/server - إدارة السيرفر\n"
        "/help - المساعدة"
    )


@bot.message_handler(commands=["server"])
def server_command(message):
    bot.send_message(
        message.chat.id,
        "🖥️ إدارة السيرفرات\n\n"
        "لا توجد سيرفرات مضافة حاليًا."
    )


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):

    if call.data == "servers":
        bot.answer_callback_query(call.id)

        bot.edit_message_text(
            "🖥️ إدارة السيرفرات\n\n"
            "لا توجد سيرفرات مضافة حاليًا.",
            call.message.chat.id,
            call.message.message_id
        )

    elif call.data == "help":
        bot.answer_callback_query(call.id)

        bot.edit_message_text(
            "ℹ️ المساعدة\n\n"
            "/start - القائمة الرئيسية\n"
            "/server - إدارة السيرفر\n"
            "/help - المساعدة",
            call.message.chat.id,
            call.message.message_id
        )


@bot.message_handler(func=lambda message: True)
def other_messages(message):

    if message.text.startswith("/"):
        return

    bot.reply_to(
        message,
        "🤖 استلمت رسالتك!"
    )


print("🤖 Bot is starting...")

bot.infinity_polling(
    skip_pending=True,
    timeout=60,
    long_polling_timeout=60
        )
