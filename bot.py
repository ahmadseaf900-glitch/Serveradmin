import os
import requests
import telebot

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID", "").strip()

print("========== ENV TEST ==========")
print("BOT_TOKEN exists:", bool(BOT_TOKEN))
print("DISCORD_TOKEN exists:", bool(DISCORD_TOKEN))
print("DISCORD_TOKEN length:", len(DISCORD_TOKEN))
print("DISCORD_CHANNEL_ID exists:", bool(DISCORD_CHANNEL_ID))
print("DISCORD_CHANNEL_ID:", DISCORD_CHANNEL_ID)
print("===============================")


def test_discord():

    if not DISCORD_TOKEN:
        print("❌ DISCORD_TOKEN فارغ")
        return

    # لا نطبع التوكن أبدًا
    headers = {
        "Authorization": "Bot " + DISCORD_TOKEN,
        "User-Agent": "Discord-Test-Bot/1.0"
    }

    try:

        r = requests.get(
            "https://discord.com/api/v10/users/@me",
            headers=headers,
            timeout=15
        )

        print("========== DISCORD ==========")
        print("HTTP:", r.status_code)
        print("Response:", r.text[:500])
        print("=============================")

    except Exception as e:

        print("Discord connection error:")
        print(repr(e))


if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN غير موجود")

test_discord()

bot = telebot.TeleBot(
    BOT_TOKEN,
    parse_mode="HTML"
)


@bot.message_handler(commands=["start"])
def start(message):

    bot.send_message(
        message.chat.id,

        "🧪 <b>Discord Test</b>\n\n"
        "تم تشغيل اختبار Discord.\n"
        "راجع Render Logs."
    )


@bot.message_handler(commands=["test"])
def test(message):

    bot.send_message(
        message.chat.id,
        "🔎 تم اختبار Discord عند تشغيل البوت.\n\n"
        "راجع Render Logs."
    )


print("Telegram bot started.")

bot.infinity_polling(
    timeout=30,
    long_polling_timeout=30,
    skip_pending=True
)
