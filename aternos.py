import os
import requests

ATERNOS_URL = os.getenv(
"ATERNOS_URL",
"https://aternos.org/server/"
)

def get_status(server_address: str):
"""
يتحقق من حالة سيرفر Minecraft عبر عنوانه.
لا يحتاج إلى تسجيل الدخول إلى Aternos.
"""
try:
from mcstatus import JavaServer

    server = JavaServer.lookup(server_address)
    status = server.status()

    return {
        "online": True,
        "players": status.players.online,
        "max_players": status.players.max,
        "latency": round(status.latency),
        "motd": str(status.motd),
    }

except Exception:
    return {
        "online": False,
        "players": 0,
        "max_players": 0,
        "latency": None,
        "motd": None,
    }

def panel_url():
"""يعيد رابط لوحة Aternos التي يمكن للمالك استخدامها يدويًا."""
return ATERNOS_URL

def start():
"""
Aternos لا يوفر API عامة لتشغيل السيرفر.
لذلك نعيد رابط اللوحة بدل تنفيذ أتمتة مخالفة.
"""
return {
"success": False,
"manual": True,
"message": "افتح لوحة Aternos واضغط Start.",
"url": panel_url(),
}

def stop():
"""إرشاد المستخدم لإيقاف السيرفر من لوحة Aternos."""
return {
"success": False,
"manual": True,
"message": "افتح لوحة Aternos واضغط Stop.",
"url": panel_url(),
}

def restart():
"""إرشاد المستخدم لإعادة تشغيل السيرفر من لوحة Aternos."""
return {
"success": False,
"manual": True,
"message": "افتح لوحة Aternos ونفّذ Restart.",
"url": panel_url(),
}
