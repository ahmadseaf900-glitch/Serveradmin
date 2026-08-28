import os
import threading

from python_aternos import Client


ATERNOS_USERNAME = os.getenv("ATERNOS_USERNAME", "").strip()
ATERNOS_PASSWORD = os.getenv("ATERNOS_PASSWORD", "").strip()
ATERNOS_SESSION = os.getenv("ATERNOS_SESSION", "").strip()

MC_SERVER_HOST = os.getenv(
    "MC_SERVER_HOST",
    "MACESMP37.aternos.me"
).strip()


_lock = threading.RLock()
_client = None
_account = None
_server = None


def _login():
    global _client, _account, _server

    with _lock:
        if _server is not None:
            return _server

        if not ATERNOS_USERNAME and not ATERNOS_SESSION:
            raise RuntimeError(
                "ضع ATERNOS_USERNAME أو ATERNOS_SESSION في Render."
            )

        client = Client()

        if ATERNOS_SESSION:
            client.login_with_session(ATERNOS_SESSION)
        else:
            if not ATERNOS_PASSWORD:
                raise RuntimeError(
                    "ATERNOS_PASSWORD غير موجود."
                )

            client.login(
                ATERNOS_USERNAME,
                ATERNOS_PASSWORD
            )

        account = client.account
        servers = account.list_servers()

        if not servers:
            raise RuntimeError(
                "لم يتم العثور على أي سيرفر في حساب Aternos."
            )

        selected = None

        wanted = MC_SERVER_HOST.lower().strip()

        for server in servers:
            try:
                address = str(server.address).lower()

                if wanted in address or address in wanted:
                    selected = server
                    break
            except Exception:
                pass

        if selected is None:
            selected = servers[0]

        _client = client
        _account = account
        _server = selected

        return _server


def get_server():
    return _login()


def refresh():
    global _server

    with _lock:
        _server = None

    return _login()


def server_info():
    server = get_server()

    result = {}

    for name in (
        "name",
        "address",
        "status",
        "status_num",
        "software",
        "version",
        "port",
        "ram",
        "players_count",
        "players_list",
    ):
        try:
            value = getattr(server, name)

            if callable(value):
                value = value()

            result[name] = value
        except Exception:
            result[name] = None

    return result


def start():
    server = get_server()

    try:
        result = server.start()
    except Exception:
        refresh()
        result = _server.start()

    return {
        "success": True,
        "message": "تم إرسال أمر تشغيل السيرفر إلى Aternos.",
        "result": result,
    }


def stop():
    server = get_server()

    try:
        result = server.stop()
    except Exception:
        refresh()
        result = _server.stop()

    return {
        "success": True,
        "message": "تم إرسال أمر إيقاف السيرفر إلى Aternos.",
        "result": result,
    }


def restart():
    server = get_server()

    try:
        result = server.restart()
    except Exception:
        refresh()
        result = _server.restart()

    return {
        "success": True,
        "message": "تم إرسال أمر Restart إلى Aternos.",
        "result": result,
    }


def get_status():
    server = get_server()

    try:
        status = server.status
    except Exception:
        refresh()
        status = _server.status

    if callable(status):
        status = status()

    return {
        "status": str(status),
        "status_num": getattr(
            server,
            "status_num",
            None
        ),
        "address": getattr(
            server,
            "address",
            MC_SERVER_HOST
        ),
        "software": getattr(
            server,
            "software",
            None
        ),
        "version": getattr(
            server,
            "version",
            None
        ),
        "players": get_players(),
    }


def get_players():
    server = get_server()

    try:
        players = server.players_list
    except Exception:
        players = []

    if callable(players):
        players = players()

    if players is None:
        return []

    try:
        return list(players)
    except Exception:
        return [str(players)]


def players_count():
    server = get_server()

    try:
        value = server.players_count
    except Exception:
        return len(get_players())

    if callable(value):
        value = value()

    try:
        return int(value)
    except Exception:
        return len(get_players())


def _players_list(list_type):
    server = get_server()

    try:
        from python_aternos.atplayers import Lists
    except ImportError:
        from python_aternos import atplayers
        Lists = atplayers.Lists

    return server.players(
        getattr(Lists, list_type)
    )


def whitelist():
    return _players_list("WHITELIST")


def operators():
    return _players_list("OPERATORS")


def whitelist_list():
    wl = whitelist()

    for attr in ("list", "players", "names"):
        try:
            value = getattr(wl, attr)

            if callable(value):
                value = value()

            if value is not None:
                return list(value)
        except Exception:
            pass

    try:
        return list(wl)
    except Exception:
        return []


def whitelist_add(player):
    wl = whitelist()

    for method in ("add", "add_player"):
        if hasattr(wl, method):
            fn = getattr(wl, method)

            if callable(fn):
                return fn(player)

    raise RuntimeError(
        "إصدار مكتبة Aternos الحالي لا يوفر دالة إضافة Whitelist."
    )


def whitelist_remove(player):
    wl = whitelist()

    for method in (
        "remove",
        "remove_player",
        "delete",
    ):
        if hasattr(wl, method):
            fn = getattr(wl, method)

            if callable(fn):
                return fn(player)

    raise RuntimeError(
        "إصدار مكتبة Aternos الحالي لا يوفر دالة حذف Whitelist."
    )


def op_add(player):
    ops = operators()

    for method in ("add", "add_player"):
        if hasattr(ops, method):
            fn = getattr(ops, method)

            if callable(fn):
                return fn(player)

    raise RuntimeError(
        "إصدار مكتبة Aternos الحالي لا يوفر دالة OP."
    )


def op_remove(player):
    ops = operators()

    for method in (
        "remove",
        "remove_player",
        "delete",
    ):
        if hasattr(ops, method):
            fn = getattr(ops, method)

            if callable(fn):
                return fn(player)

    raise RuntimeError(
        "إصدار مكتبة Aternos الحالي لا يوفر دالة DeOP."
    )
