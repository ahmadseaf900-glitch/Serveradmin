# aternos.py

import os
from python_aternos import Client_Aternos

ATERNOS_USER = os.getenv("ATERNOS_USERNAME", "").strip()
ATERNOS_PASS = os.getenv("ATERNOS_PASSWORD", "").strip()

if not ATERNOS_USER or not ATERNOS_PASS:
    raise RuntimeError(
        "ATERNOS_USERNAME و ATERNOS_PASSWORD غير موجودين في Environment Variables"
    )

# تسجيل الدخول إلى حساب Aternos
aternos = Client_Aternos(
    ATERNOS_USER,
    password=ATERNOS_PASS
)

# جلب السيرفرات
servers = aternos.list_servers()

if not servers:
    raise RuntimeError("لم يتم العثور على أي سيرفر في حساب Aternos")

# السيرفر الافتراضي
myserver = servers[0]


def get_server():
    """إرجاع السيرفر المحدد."""
    return myserver


def get_status():
    """إرجاع حالة السيرفر من Aternos."""
    try:
        myserver.fetch()

        status = str(
            getattr(myserver, "status", "")
        ).lower()

        return {
            "success": True,
            "status": status,
            "online": status in (
                "online",
                "running"
            )
        }

    except Exception as exc:
        return {
            "success": False,
            "online": False,
            "status": "unknown",
            "error": str(exc)
        }


def start():
    """تشغيل السيرفر عبر حساب Aternos."""

    try:
        myserver.start()

        return {
            "success": True,
            "message": "تم إرسال أمر تشغيل السيرفر إلى Aternos."
        }

    except Exception as exc:
        return {
            "success": False,
            "message": str(exc)
        }


def stop():
    """إيقاف السيرفر عبر حساب Aternos."""

    try:
        myserver.stop()

        return {
            "success": True,
            "message": "تم إرسال أمر إيقاف السيرفر إلى Aternos."
        }

    except Exception as exc:
        return {
            "success": False,
            "message": str(exc)
        }


def restart():
    """إعادة تشغيل السيرفر عبر Aternos."""

    try:
        myserver.restart()

        return {
            "success": True,
            "message": "تم إرسال أمر Restart إلى Aternos."
        }

    except Exception as exc:
        return {
            "success": False,
            "message": str(exc)
        }
