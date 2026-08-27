import os
from mcstatus import JavaServer


# =========================================================
# إعدادات Aternos
# =========================================================

ATERNOS_URL = os.getenv(
    "ATERNOS_URL",
    "https://aternos.org/"
)

SERVER_ADDRESS = os.getenv(
    "ATERNOS_SERVER",
    "MACESMP37.aternos.me"
).strip()


# =========================================================
# فتح لوحة Aternos
# =========================================================

def get_panel_url():
    """إرجاع رابط لوحة Aternos."""
    return ATERNOS_URL


# =========================================================
# تشغيل السيرفر
# =========================================================

def start():
    """
    Aternos لا يوفر API رسميًا عامًا لتشغيل السيرفر
    من بوت خارجي، لذلك نعيد رابط لوحة التحكم.
    """
    return {
        "success": False,
        "manual": True,
        "url": get_panel_url(),
        "message": "افتح لوحة Aternos واضغط Start."
    }


# =========================================================
# إيقاف السيرفر
# =========================================================

def stop():
    """إرجاع رابط لوحة Aternos لإيقاف السيرفر."""
    return {
        "success": False,
        "manual": True,
        "url": get_panel_url(),
        "message": "افتح لوحة Aternos واضغط Stop."
    }


# =========================================================
# إعادة التشغيل
# =========================================================

def restart():
    """إرجاع رابط لوحة Aternos لإعادة تشغيل السيرفر."""
    return {
        "success": False,
        "manual": True,
        "url": get_panel_url(),
        "message": "افتح لوحة Aternos واضغط Restart."
    }


# =========================================================
# حالة السيرفر
# =========================================================

def status():
    """
    فحص حالة Minecraft مباشرة باستخدام mcstatus.
    لا يحتاج تسجيل دخول إلى Aternos.
    """

    try:
        server = JavaServer.lookup(SERVER_ADDRESS)

        result = server.status()

        return {
            "success": True,
            "online": True,
            "players": result.players.online,
            "max_players": result.players.max,
            "latency": round(result.latency),
            "motd": str(result.motd),
            "version": str(result.version.name)
        }

    except Exception as exc:
        return {
            "success": True,
            "online": False,
            "players": 0,
            "max_players": 0,
            "latency": None,
            "motd": None,
            "version": None,
            "error": str(exc)
        }


# =========================================================
# توافق مع الاسم القديم get_status
# =========================================================

def get_status():
    """Alias للتوافق مع أي كود قديم يستعمل get_status()."""
    return status()
