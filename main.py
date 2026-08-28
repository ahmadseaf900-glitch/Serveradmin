import telebot
from python_aternos import Client

# بيانات حساب البوت المشترك الذي أنشأته
ATERNOS_USER = "MCADMIN90"
ATERNOS_PASS = "111seafalden111"
TELEGRAM_TOKEN = "ضع_هنا_توكن_البوت_الخاص_بك_من_تلغرام"

print("⏳ جاري الاتصال التلقائي باتيرنوس وتوليد الجلسة...")

try:
    # هذا السطر يتكفل بتوليد وتحديث الكوكي تلقائياً على خوادم Render دون تدخل منك
    aternos = Client.from_credentials(ATERNOS_USER, ATERNOS_PASS)
    servers = aternos.list_servers()
    server = servers[0] # يختار السيرفر الأول تلقائياً
    print("✅ تم الاتصال بنجاح وتجهيز السيرفر!")
except Exception as e:
    print(f"❌ فشل الاتصال التلقائي: {e}")

bot = telebot.TeleBot(TELEGRAM_TOKEN)

@bot.message_handler(commands=['start_server'])
def start_minecraft(message):
    try:
        server.start()
        bot.reply_to(message, "⏳ جاري تشغيل سيرفر ماينكرافت الآن...")
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ أثناء التشغيل: {e}")

@bot.message_handler(commands=['stop_server'])
def stop_minecraft(message):
    try:
        server.stop()
        bot.reply_to(message, "🛑 تم إرسال أمر إيقاف السيرفر.")
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ أثناء الإيقاف: {e}")

@bot.message_handler(commands=['status'])
def server_status(message):
    try:
        server.fetch() # تحديث البيانات الحالية
        bot.reply_to(message, f"📊 حالة السيرفر الحالية: {server.status}")
    except Exception as e:
        bot.reply_to(message, f"❌ فشل جلب الحالة: {e}")

print("🚀 البوت جاهز ويستقبل الأوامر الآن على تلغرام...")
bot.polling(none_stop=True)

