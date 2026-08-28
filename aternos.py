import os
import threading
import time

from python_aternos import Client


ATERNOS_USERNAME = os.getenv("ATERNOS_USERNAME", "").strip()
ATERNOS_PASSWORD = os.getenv("ATERNOS_PASSWORD", "").strip()
MC_SERVER_HOST = os.getenv(
    "MC_SERVER_HOST",
    "MACESMP37.aternos.me"
).strip()


_client = None
_account = None
_server = None
_lock = threading.Lock()


def _get_client():
    global _client

    with _lock:
        if _client is None:
            if not ATERNOS_USERNAME or not ATERNOS_PASSWORD:
                raise RuntimeError(
                    "ATERNOS_USERNAME أو ATERNOS_PASSWORD غير موجود"
                )

            _client = Client()
            _client.login(
                ATERNOS_USERNAME,
                ATERNOS_PASSWORD
            )

        return _client


def get_server():
    global _account
    global _server

    with _lock:
        client = _get_client()

        if _account is None:
            _account = client.account

        servers = _account.list_servers()

        if not servers:
            raise RuntimeError(
                "لم يتم العثور على أي سيرفر في حساب Aternos"
            )

        # البحث بالعنوان أولاً
        wanted = MC_SERVER_HOST.lower()

        for server in servers:
            address = str(
                getattr(server, "address", "")
            ).lower()

            if address == wanted:
                _server = server
                return server

        # إذا لم يجد العنوان، استخدم السيرفر الأول
        _server = servers[0]

        return _server


def refresh():
    global _server

    with _lock:
        _server = None

    return get_server()


def start():
    server = get_server()

    server.start()

    return {
        "success": True,
        "action": "start",
        "message": "تم إرسال طلب تشغيل السيرفر إلى Aternos."
    }


def stop():
    server = get_server()

    server.stop()

    return {
        "success": True,
        "action": "stop",
        "message": "تم إرسال طلب إيقاف السيرفر إلى Aternos."
    }


def restart():
    server = get_server()

    # بعض إصدارات python-aternos توفر restart مباشرة
    restart_method = getattr(
        server,
        "restart",
        None
    )

    if callable(restart_method):
        restart_method()

        return {
            "success": True,
            "action": "restart",
            "message": "تم إرسال طلب Restart إلى Aternos."
        }

    # fallback
    server.stop()

    time.sleep(3)

    server.start()

    return {
        "success": True,
        "action": "restart",
        "message": "تم تنفيذ Stop ثم Start."
    }


def get_info():
    server = get_server()

    data = {
        "name": getattr(server, "name", None),
        "address": getattr(server, "address", MC_SERVER_HOST),
        "software": getattr(server, "software", None),
        "version": getattr(server, "version", None),
        "status": None
    }

    for attribute in (
        "status",
        "state"
    ):
        try:
            value = getattr(server, attribute)

            if callable(value):
                value = value()

            data["status"] = str(value)
            break

        except Exception:
            pass

    return data


def login_test():
    server = get_server()

    return {
        "success": True,
        "name": getattr(server, "name", "Unknown"),
        "address": getattr(
            server,
            "address",
            MC_SERVER_HOST
        )
    }
