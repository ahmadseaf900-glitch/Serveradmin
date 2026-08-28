import os
from python_aternos import Client_Aternos

ATERNOS_USER = os.getenv("ATERNOS_USERNAME", "").strip()
ATERNOS_PASS = os.getenv("ATERNOS_PASSWORD", "").strip()

if not ATERNOS_USER or not ATERNOS_PASS:
    raise RuntimeError(
        "ATERNOS_USERNAME و ATERNOS_PASSWORD غير موجودين في Environment Variables"
    )

aternos = Client_Aternos(
    ATERNOS_USER,
    password=ATERNOS_PASS
)


def get_servers():
    return aternos.list_servers()


def get_server():
    servers = get_servers()

    if not servers:
        raise RuntimeError("لم يتم العثور على أي سيرفر في حساب Aternos")

    return servers[0]


def start():
    server = get_server()

    result = server.start()

    return {
        "success": True,
        "action": "start",
        "server": server,
        "result": result
    }


def stop():
    server = get_server()

    result = server.stop()

    return {
        "success": True,
        "action": "stop",
        "server": server,
        "result": result
    }


def restart():
    server = get_server()

    result = server.restart()

    return {
        "success": True,
        "action": "restart",
        "server": server,
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
