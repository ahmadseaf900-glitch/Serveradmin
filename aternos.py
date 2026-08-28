import os
import threading

from python_aternos import Client


ATERNOS_SESSION = os.getenv("ATERNOS_SESSION", "").strip()
ATERNOS_USERNAME = os.getenv("ATERNOS_USERNAME", "").strip()
ATERNOS_PASSWORD = os.getenv("ATERNOS_PASSWORD", "").strip()

MC_SERVER_HOST = os.getenv(
    "MC_SERVER_HOST",
    "MACESMP37.aternos.me"
).strip()


_lock = threading.Lock()
_client = None
_account = None
_server = None


def _login():
    global _client, _account

    if _account is not None:
        return _account

    with _lock:

        if _account is not None:
            return _account

        client = Client()

        if ATERNOS_SESSION:
            client.login_with_session(ATERNOS_SESSION)

        elif ATERNOS_USERNAME and ATERNOS_PASSWORD:
            client.login(
                ATERNOS_USERNAME,
                ATERNOS_PASSWORD
            )

        else:
            raise RuntimeError(
                "ضع ATERNOS_SESSION أو "
                "ATERNOS_USERNAME + ATERNOS_PASSWORD"
            )

        _client = client
        _account = client.account

        return _account


def get_servers():
    account = _login()
    return account.list_servers()


def get_server():
    global _server

    with _lock:

        servers = get_servers()

        if not servers:
            raise RuntimeError(
                "لم يتم العثور على أي سيرفر في حساب Aternos."
            )

        target = MC_SERVER_HOST.lower()

        # البحث بالعنوان
        for server in servers:

            try:
                address = str(server.address).lower()
            except Exception:
                address = ""

            try:
                domain = str(server.domain).lower()
            except Exception:
                domain = ""

            if target in (address, domain):
                _server = server
                return server

        # إذا لم يجد العنوان نستخدم الأول
        _server = servers[0]

        return _server


def refresh():
    global _server

    server = get_server()

    try:
        server.fetch()
    except Exception:
        pass

    return server


# ============================================================
# START
# ============================================================

def start():
    server = get_server()

    server.start()

    return {
        "success": True,
        "action": "start",
        "status": str(server.status)
    }


# ============================================================
# STOP
# ============================================================

def stop():
    server = get_server()

    server.stop()

    return {
        "success": True,
        "action": "stop",
        "status": str(server.status)
    }


# ============================================================
# RESTART
# ============================================================

def restart():
    server = get_server()

    server.restart()

    return {
        "success": True,
        "action": "restart",
        "status": str(server.status)
    }


# ============================================================
# ATERNOS STATUS
# ============================================================

def status():
    server = refresh()

    return {
        "success": True,
        "status": str(server.status),
        "address": str(server.address),
        "domain": str(server.domain),
        "port": int(server.port),
        "players": int(server.players_count),
        "player_list": list(server.players_list),
        "slots": int(server.slots),
        "software": str(server.software),
        "version": str(server.version),
        "edition": str(server.edition),
        "ram": int(server.ram)
    }


# ============================================================
# PLAYERS
# ============================================================

def players():
    server = refresh()

    return {
        "success": True,
        "online": int(server.players_count),
        "max": int(server.slots),
        "players": list(server.players_list)
    }


# ============================================================
# WHITELIST
#
# نحاول استخدام واجهة Players الخاصة بالمكتبة.
# ============================================================

def get_whitelist_object():
    server = get_server()

    try:
        from python_aternos.atplayers import Lists

        return server.players(
            Lists.WHITELIST
        )

    except Exception as exc:
        raise RuntimeError(
            "تعذر الوصول إلى قائمة Whitelist عبر "
            "إصدار python-aternos الموجود: "
            + str(exc)
        )


def whitelist_list():
    whitelist = get_whitelist_object()

    try:
        whitelist.fetch()
    except Exception:
        pass

    try:
        values = list(whitelist)
    except Exception:
        try:
            values = list(whitelist.players)
        except Exception:
            values = []

    return [
        str(x)
        for x in values
    ]


def whitelist_add(player):
    player = str(player).strip()

    if not player:
        raise ValueError(
            "اسم اللاعب فارغ."
        )

    whitelist = get_whitelist_object()

    if hasattr(whitelist, "add"):
        whitelist.add(player)

    elif hasattr(whitelist, "append"):
        whitelist.append(player)

    else:
        raise RuntimeError(
            "إصدار python-aternos لا يدعم إضافة اللاعب "
            "بالطريقة الحالية."
        )

    return {
        "success": True,
        "player": player
    }


def whitelist_remove(player):
    player = str(player).strip()

    if not player:
        raise ValueError(
            "اسم اللاعب فارغ."
        )

    whitelist = get_whitelist_object()

    if hasattr(whitelist, "remove"):
        whitelist.remove(player)

    elif hasattr(whitelist, "delete"):
        whitelist.delete(player)

    else:
        raise RuntimeError(
            "إصدار python-aternos لا يدعم إزالة اللاعب "
            "بالطريقة الحالية."
        )

    return {
        "success": True,
        "player": player
    }
