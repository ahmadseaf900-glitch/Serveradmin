"""
Aternos manager.

يستخدم python-aternos لإدارة سيرفر Aternos.
"""

import os
import threading

try:
    from python_aternos import Client
except ImportError:
    Client = None


class AternosManager:
    """
    مدير اتصال Aternos.

    يحتفظ بجلسة واحدة ويعيد استخدامها بدل تسجيل الدخول
    في كل عملية.
    """

    def __init__(self):
        self.username = os.getenv(
            "ATERNOS_USERNAME",
            ""
        ).strip()

        self.password = os.getenv(
            "ATERNOS_PASSWORD",
            ""
        ).strip()

        self.server_address = os.getenv(
            "ATERNOS_SERVER",
            ""
        ).strip().lower()

        self.client = None
        self.account = None
        self.server = None

        self.lock = threading.Lock()

    def _check_config(self):
        """التأكد من وجود الإعدادات المطلوبة."""

        if Client is None:
            raise RuntimeError(
                "python-aternos غير مثبت."
            )

        if not self.username:
            raise RuntimeError(
                "ATERNOS_USERNAME غير مضبوط."
            )

        if not self.password:
            raise RuntimeError(
                "ATERNOS_PASSWORD غير مضبوط."
            )

        if not self.server_address:
            raise RuntimeError(
                "ATERNOS_SERVER غير مضبوط."
            )

    def connect(self):
        """
        تسجيل الدخول والعثور على السيرفر.
        """

        self._check_config()

        with self.lock:

            if self.server is not None:
                return self.server

            self.client = Client()

            self.client.login(
                self.username,
                self.password
            )

            self.account = self.client.account

            servers = self.account.list_servers()

            for server in servers:

                address = str(
                    getattr(
                        server,
                        "address",
                        ""
                    )
                ).lower().strip()

                name = str(
                    getattr(
                        server,
                        "name",
                        ""
                    )
                ).lower().strip()

                if (
                    address == self.server_address
                    or name == self.server_address
                    or self.server_address in address
                ):

                    self.server = server

                    return server

            raise RuntimeError(
                f"لم يتم العثور على السيرفر: "
                f"{self.server_address}"
            )

    def reset(self):
        """إعادة ضبط الجلسة."""

        with self.lock:

            self.client = None
            self.account = None
            self.server = None

    def start(self):
        """تشغيل السيرفر."""

        server = self.connect()

        return server.start()

    def stop(self):
        """إيقاف السيرفر."""

        server = self.connect()

        return server.stop()

    def restart(self):
        """إعادة تشغيل السيرفر."""

        server = self.connect()

        restart = getattr(
            server,
            "restart",
            None
        )

        if callable(restart):
            return restart()

        server.stop()
        return server.start()

    def status(self):
        """الحصول على حالة السيرفر."""

        server = self.connect()

        status = getattr(
            server,
            "status",
            None
        )

        if callable(status):
            return status()

        return status
