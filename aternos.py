import os
from mcstatus import JavaServer

ATERNOS_URL = os.getenv(
"ATERNOS_URL",
"https://aternos.org/"
)

SERVER_ADDRESS = os.getenv(
"ATERNOS_SERVER",
"MACESMP37.aternos.me"
)

def panel_url():
"""Return the Aternos panel URL."""
return ATERNOS_URL

def status():
"""Check the Minecraft server status without logging into Aternos."""
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
    }

except Exception as exc:
    return {
        "success": True,
        "online": False,
        "players": 0,
        "max_players": 0,
        "latency": None,
        "motd": None,
        "error": str(exc),
    }

def start():
"""Return instructions for manually starting the Aternos server."""
return {
"success": False,
"manual": True,
"url": panel_url(),
"message": "افتح لوحة Aternos واضغط Start.",
}

def stop():
"""Return instructions for manually stopping the Aternos server."""
return {
"success": False,
"manual": True,
"url": panel_url(),
"message": "افتح لوحة Aternos واضغط Stop.",
}

def restart():
"""Return instructions for manually restarting the Aternos server."""
return {
"success": False,
"manual": True,
"url": panel_url(),
"message": "افتح لوحة Aternos واضغط Restart.",
}
