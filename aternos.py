import os
import time
from typing import Any, Optional

from python_aternos import Client


ATERNOS_USERNAME = os.getenv("ATERNOS_USERNAME", "").strip()
ATERNOS_PASSWORD = os.getenv("ATERNOS_PASSWORD", "").strip()
SERVER_HOST = os.getenv("MC_SERVER_HOST", "").strip()


class AternosManager:
    """
    مدير اتصال Aternos.

    يسجل الدخول بالحساب الموجود في Environment Variables،
    ثم يبحث عن السيرفر بواسطة عنوانه وينفذ Start / Stop / Restart.
    """

    def __init__(self):
        self.client: Optional[Client] = None
        self.account = None
        self.server = None

    def login(self):
        """تسجيل الدخول إلى حساب Aternos."""
        if not ATERNOS_USERNAME:
            raise RuntimeError("ATERNOS_USERNAME غير موجود.")

        if not ATERNOS_PASSWORD:
            raise RuntimeError("ATERNOS_PASSWORD غير موجود.")

        self.client = Client()
        self.client.login(
            ATERNOS_USERNAME,
            ATERNOS_PASSWORD
        )

        self.account = self.client.account

        if self.account is None:
            raise RuntimeError("فشل تسجيل الدخول إلى Aternos.")

        return True

    def find_server(self):
        """
        البحث عن السيرفر الخاص بالحساب.
        """
        if self.account is None:
            self.login()

        servers = self.account.list_servers()

        if not servers:
            raise RuntimeError(
                "لم يتم العثور على أي سيرفر في حساب Aternos."
            )

        target = SERVER_HOST.lower().strip()

        # البحث الدقيق أولاً
        for server in servers:
            address = str(
                getattr(server, "address", "")
            ).lower().strip()

            if address == target:
                self.server = server
                return server

        # البحث بدون المنفذ
        target_host = target.split(":")[0]

        for server in servers:
            address = str(
                getattr(server, "address", "")
            ).lower().strip()

            address_host = address.split(":")[0]

            if address_host == target_host:
                self.server = server
                return server

        # إذا كان عند الحساب سيرفر واحد فقط
        if len(servers) == 1:
            self.server = servers[0]
            return self.server

        available = []

        for server in servers:
            available.append(
                str(getattr(server, "address", "unknown"))
            )

        raise RuntimeError(
            "لم يتم العثور على السيرفر.\n"
            "السيرفرات الموجودة: "
            + ", ".join(available)
        )

    def get_server(self):
        """إرجاع كائن السيرفر مع إعادة تسجيل الدخول عند الحاجة."""
        if self.server is not None:
            return self.server

        return self.find_server()

    def start(self):
        """إرسال أمر Start إلى Aternos."""
        server = self.get_server()

        server.start()

        return True

    def stop(self):
        """إرسال أمر Stop إلى Aternos."""
        server = self.get_server()

        server.stop()

        return True

    def restart(self):
        """
        إعادة تشغيل السيرفر.

        إذا كانت المكتبة توفر restart() نستخدمها.
        وإلا ننفذ Stop ثم Start.
        """
        server = self.get_server()

        restart_method = getattr(
            server,
            "restart",
            None
        )

        if callable(restart_method):
            restart_method()
            return True

        server.stop()

        time.sleep(5)

        server.start()

        return True

    def info(self) -> dict[str, Any]:
        """إرجاع معلومات السيرفر من Aternos."""
        server = self.get_server()

        return {
            "address": getattr(
                server,
                "address",
                SERVER_HOST
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
            "status": getattr(
                server,
                "status",
                None
            ),
        }


_manager = AternosManager()


def start():
    """واجهة Start القديمة."""
    return _manager.start()


def stop():
    """واجهة Stop القديمة."""
    return _manager.stop()


def restart():
    """واجهة Restart القديمة."""
    return _manager.restart()


def get_status():
    """الحصول على معلومات Aternos."""
    return _manager.info()
