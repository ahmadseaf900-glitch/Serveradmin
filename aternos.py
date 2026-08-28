import os
import threading
from typing import Optional

from python_aternos import Client


# ============================================================
# CONFIG
# ============================================================

ATERNOS_SESSION = os.getenv("ATERNOS_SESSION", "").strip()

MC_SERVER_HOST = os.getenv(
    "MC_SERVER_HOST",
    "MACESMP37.aternos.me"
).strip().lower()

# ============================================================
# GLOBAL
# ============================================================

_client = None
_account = None
_server = None
_lock = threading.RLock()


# ============================================================
# LOGIN
# ============================================================

def connect():
    """
    تسجيل الدخول إلى Aternos باستخدام Session.
    """

    global _client, _account, _server

    if not ATERNOS_SESSION:
        raise RuntimeError(
            "ATERNOS_SESSION غير موجود في Environment Variables"
        )

    with _lock:

        if _account is not None:
            return _account

        _client = Client()

        # تسجيل الدخول باستخدام Session
        _client.login_with_session(
            ATERNOS_SESSION
        )

        _account = _client.account

        # جلب السيرفرات
        servers = _account.list_servers()

        if not servers:
            raise RuntimeError(
                "لم يتم العثور على أي سيرفر في حساب Aternos."
            )

        # البحث عن السيرفر حسب العنوان
        selected = None

        for server in servers:

            address = str(
                getattr(server, "address", "")
            ).lower().strip()

            if address == MC_SERVER_HOST:
                selected = server
                break

            # بعض الحالات يكون العنوان بدون نطاق
            if MC_SERVER_HOST in address:
                selected = server
                break

        # إذا لم نجده نستخدم أول سيرفر
        if selected is None:
            selected = servers[0]

        _server = selected

        return _account


# ============================================================
# GET SERVER
# ============================================================

def get_server():
    """
    إرجاع سيرفر Aternos المرتبط بالحساب.
    """

    global _server

    with _lock:

        if _server is None:
            connect()

        if _server is None:
            raise RuntimeError(
                "تعذر الحصول على سيرفر Aternos."
            )

        return _server


# ============================================================
# REFRESH
# ============================================================

def refresh():
    """
    إعادة جلب معلومات السيرفر من Aternos.
    """

    global _server

    with _lock:

        account = connect()

        servers = account.list_servers()

        selected = None

        for server in servers:

            address = str(
                getattr(server, "address", "")
            ).lower().strip()

            if address == MC_SERVER_HOST:
                selected = server
                break

        if selected is None and servers:
            selected = servers[0]

        _server = selected

        return _server


# ============================================================
# START
# ============================================================

def start():
    """
    تشغيل السيرفر فعليًا من خلال حساب Aternos.
    """

    server = get_server()

    try:
        result = server.start()

        return {
            "success": True,
            "action": "start",
            "message": "تم إرسال أمر تشغيل السيرفر إلى Aternos.",
            "result": result
        }

    except Exception as exc:

        return {
            "success": False,
            "action": "start",
            "message": str(exc)
        }


# ============================================================
# STOP
# ============================================================

def stop():
    """
    إيقاف السيرفر فعليًا.
    """

    server = get_server()

    try:
        result = server.stop()

        return {
            "success": True,
            "action": "stop",
            "message": "تم إرسال أمر إيقاف السيرفر إلى Aternos.",
            "result": result
        }

    except Exception as exc:

        return {
            "success": False,
            "action": "stop",
            "message": str(exc)
        }


# ============================================================
# RESTART
# ============================================================

def restart():
    """
    إعادة تشغيل السيرفر.
    """

    server = get_server()

    try:

        # بعض إصدارات المكتبة توفر restart مباشرة
        if hasattr(server, "restart"):

            result = server.restart()

            return {
                "success": True,
                "action": "restart",
                "message": "تم إرسال أمر Restart إلى Aternos.",
                "result": result
            }

        # fallback
        stop_result = server.stop()

        return {
            "success": True,
            "action": "restart",
            "message": (
                "تم إرسال أمر الإيقاف. "
                "إذا كانت نسخة المكتبة لا توفر restart "
                "مباشرة، يجب تشغيل السيرفر بعد توقفه."
            ),
            "result": stop_result
        }

    except Exception as exc:

        return {
            "success": False,
            "action": "restart",
            "message": str(exc)
        }


# ============================================================
# ATERNOS STATUS
# ============================================================

def get_aternos_status():
    """
    إرجاع حالة السيرفر من Aternos نفسه.
    """

    try:

        server = get_server()

        # تحديث البيانات إن أمكن
        try:
            server = refresh()
        except Exception:
            pass

        data = {}

        # الخصائص المحتملة في python-aternos
        for key in [
            "status",
            "online",
            "players",
            "max_players",
            "address",
            "software",
            "version",
            "motd",
            "host",
            "port"
        ]:

            try:
                data[key] = getattr(server, key)
            except Exception:
                pass

        return {
            "success": True,
            "server": data
        }

    except Exception as exc:

        return {
            "success": False,
            "error": str(exc)
        }


# ============================================================
# PLAYERS
# ============================================================

def get_players():
    """
    محاولة الحصول على قائمة اللاعبين من Aternos.
    """

    server = get_server()

    players = []

    # بعض نسخ المكتبة توفر playerlist
    for attribute in [
        "players",
        "playerlist"
    ]:

        try:

            value = getattr(server, attribute)

            if isinstance(value, (list, tuple, set)):
                players = list(value)
                break

        except Exception:
            pass

    return players


# ============================================================
# CONSOLE COMMAND
# ============================================================

def send_command(command: str):
    """
    إرسال أمر Minecraft إلى Console.

    يعتمد على WebSocket/Console API في المكتبة إذا كان متاحًا.
    """

    command = str(command).strip()

    if not command:
        raise ValueError(
            "الأمر فارغ."
        )

    server = get_server()

    # بعض نسخ python-aternos توفر command()
    if hasattr(server, "command"):

        return server.command(command)

    # وبعض النسخ توفر send_command()
    if hasattr(server, "send_command"):

        return server.send_command(command)

    raise RuntimeError(
        "نسخة python-aternos الحالية لا توفر "
        "واجهة Console command مباشرة."
    )


# ============================================================
# WHITELIST
# ============================================================

def whitelist_add(player: str):
    """
    إضافة لاعب إلى Whitelist.
    """

    player = str(player).strip()

    if not player:
        raise ValueError("اسم اللاعب فارغ.")

    return send_command(
        f"whitelist add {player}"
    )


def whitelist_remove(player: str):
    """
    إزالة لاعب من Whitelist.
    """

    player = str(player).strip()

    if not player:
        raise ValueError("اسم اللاعب فارغ.")

    return send_command(
        f"whitelist remove {player}"
    )


def whitelist_on():
    return send_command(
        "whitelist on"
    )


def whitelist_off():
    return send_command(
        "whitelist off"
    )


def whitelist_list():
    return send_command(
        "whitelist list"
    )


# ============================================================
# CONSOLE
# ============================================================

def console(command: str):
    return send_command(command)


# ============================================================
# GET STATUS ALIAS
# ============================================================

def get_status():
    return get_aternos_status()


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("Connecting to Aternos...")

    try:

        connect()

        server = get_server()

        print(
            "Connected to:",
            getattr(
                server,
                "address",
                "Unknown"
            )
        )

        print(
            "Status:",
            get_aternos_status()
        )

    except Exception as exc:

        print(
            "Aternos error:",
            exc
            )
