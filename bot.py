import os
import requests
import telebot

# =========================================================
# ENV
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID", "").strip()

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN غير موجود")

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN غير موجود")

if not DISCORD_CHANNEL_ID:
    raise RuntimeError("DISCORD_CHANNEL_ID غير موجود")


# =========================================================
# TELEGRAM
# =========================================================

bot = telebot.TeleBot(
    BOT_TOKEN,
    parse_mode="HTML"
)


# =========================================================
# DISCORD TEST
# =========================================================

def discord_test():

    headers = {
        "Authorization": f"Bot {DISCORD_TOKEN}",
        "Content-Type": "application/json"
    }

    print("========== DISCORD TEST ==========")
    print("Token موجود: YES")
    print("Token length:", len(DISCORD_TOKEN))
    print("Channel ID:", DISCORD_CHANNEL_ID)

    # -----------------------------------------------------
    # 1. اختبار التوكن
    # -----------------------------------------------------

    try:

        response = requests.get(
            "https://discord.com/api/v10/users/@me",
            headers=headers,
            timeout=15
        )

        print("Authentication status:",
              response.status_code)

        print("Authentication response:",
              response.text[:500])

        if response.status_code != 200:

            print("❌ Discord Token غير صالح")

            return (
                False,
                "Discord Token غير صالح"
            )

    except Exception as e:

        print("❌ Authentication error:", e)

        return (
            False,
            str(e)
        )

    # -----------------------------------------------------
    # 2. اختبار إرسال رسالة
    # -----------------------------------------------------

    try:

        response = requests.post(

            f"https://discord.com/api/v10/channels/"
            f"{DISCORD_CHANNEL_ID}/messages",

            headers=headers,

            json={
                "content":
                    "🧪 اختبار من Telegram Bot"
            },

            timeout=15
        )

        print("Send message status:",
              response.status_code)

        print("Send message response:",
              response.text[:500])

        if response.status_code in (200, 201):

            print("✅ Discord يعمل بشكل صحيح")

            return (
                True,
                "تم إرسال الرسالة بنجاح"
            )

        print("❌ فشل إرسال الرسالة")

        return (
            False,
            f"Discord HTTP {response.status_code}: "
            f"{response.text[:500]}"
        )

    except Exception as e:

        print("❌ Send error:", e)

        return (
            False,
            str(e)
        )


# =========================================================
# /START
# =========================================================

@bot.message_handler(commands=["start"])
def start(message):

    bot.send_message(
        message.chat.id,

        "🤖 <b>Discord Bridge Test</b>\n\n"
        "هذا بوت اختبار فقط.\n\n"
        "استخدم:\n"
        "/test\n\n"
        "لا يوجد Aternos ولا Console ولا DiscordSRV "
        "في هذه النسخة."
    )


# =========================================================
# /TEST
# =========================================================

@bot.message_handler(commands=["test"])
def test(message):

    bot.send_message(
        message.chat.id,
        "🔎 جاري اختبار Discord..."
    )

    success, result = discord_test()

    if success:

        bot.send_message(
            message.chat.id,

            "✅ <b>نجح الاختبار</b>\n\n"
            "تم إرسال رسالة إلى Discord."
        )

    else:

        bot.send_message(
            message.chat.id,

            "❌ <b>فشل الاختبار</b>\n\n"
            f"<code>{result}</code>"
        )


# =========================================================
# RUN
# =========================================================

print("================================")
print("Telegram → Discord TEST BOT")
print("================================")

print(
    "BOT_TOKEN:",
    "OK" if BOT_TOKEN else "MISSING"
)

print(
    "DISCORD_TOKEN:",
    "OK" if DISCORD_TOKEN else "MISSING"
)

print(
    "DISCORD_CHANNEL_ID:",
    DISCORD_CHANNEL_ID
)

print("================================")

# اختبار Discord عند تشغيل السيرفر
discord_test()

print("Telegram bot started.")

bot.infinity_polling(
    timeout=30,
    long_polling_timeout=30,
    skip_pending=True
)
