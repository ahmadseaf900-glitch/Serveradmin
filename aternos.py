import os

from python_aternos import Client_Aternos


ATERNOS_USERNAME = os.getenv("ATERNOS_USERNAME", "").strip()
ATERNOS_PASSWORD = os.getenv("ATERNOS_PASSWORD", "").strip()

if not ATERNOS_USERNAME:
    raise RuntimeError("ATERNOS_USERNAME غير موجود في Render")

if not ATERNOS_PASSWORD:
    raise RuntimeError("ATERNOS_PASSWORD غير موجود في Render")


_client = None


def get_client():
    global _client

    if _client is None:
        _client = Client_Aternos(
            ATERNOS_USERNAME,
            password=ATERNOS_PASSWORD
        )

    return _client


def get_servers():
    client = get_client()

    servers = client.list_servers()

    if not servers:
        raise RuntimeError(
            "تم تسجيل الدخول، لكن لم يتم العثور على سيرفرات في حساب Aternos."
        )

    return servers


def get_server():
    servers = get_servers()

    # السيرفر الأول
    return servers[0]


def _call_server_method(server, method_names):
    """
    يحاول العثور على اسم الدالة الصحيح في نسخة المكتبة المثبتة.
    """

    for name in method_names:
        method = getattr(server, name, None)

        if callable(method):
            return method()

    raise RuntimeError(
        "إصدار python-aternos المثبت لا يحتوي على الدالة المطلوبة. "
        f"الدوال المطلوبة: {', '.join(method_names)}"
    )


def start():
    server = get_server()

    result = _call_server_method(
        server,
        [
            "start",
            "Start",
            "start_server"
        ]
    )

    return {
        "success": True,
        "action": "start",
        "result": result
    }


def stop():
    server = get_server()

    result = _call_server_method(
        server,
        [
            "stop",
            "Stop",
            "stop_server"
        ]
    )

    return {
        "success": True,
        "action": "stop",
        "result": result
    }


def restart():
    server = get_server()

    # بعض الإصدارات لا تحتوي restart
    restart_method = getattr(server, "restart", None)

    if callable(restart_method):
        result = restart_method()

        return {
            "success": True,
            "action": "restart",
            "result": result
        }

    # إذا لم توجد restart نحاول Stop ثم Start
    _call_server_method(
        server,
        [
            "stop",
            "Stop",
            "stop_server"
        ]
    )

    result = _call_server_method(
        server,
        [
            "start",
            "Start",
            "start_server"
        ]
    )

    return {
        "success": True,
        "action": "restart",
        "result": result
    }


def get_status():
    server = get_server()

    status = getattr(server, "status", None)

    if callable(status):
        status = status()

    return {
        "success": True,
        "status": str(status),
        "server": server
    }
