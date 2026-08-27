import os
import threading

from python_aternos import Client


class AternosManager:
    """
    مدير اتصال Aternos.
    يسجل الدخول مرة واحدة ويحاول العثور على السيرفر المطلوب.
    """

    def __init__(self):
        self.username = os.getenv("ATERNOS_USERNAME", "").strip()
        self.password = os.getenv("ATERNOS_PASSWORD", "").strip()
        self.server_address = os.getenv(
            "ATERNOS_SERVER",
            "MACESMP37.aternos.me"
        ).strip().lower()

        self.client = None
        self.server = None
        self.lock = threading.Lock()

    def _login(self):
        """تسجيل الدخول إلى حساب Aternos."""
        if not self.username:
            raise RuntimeError("ATERNOS_USERNAME غير موجود.")

        if not self.password:
            raise RuntimeError("ATERNOS_PASSWORD غير موجود.")

        self.client = Client()
        self.client.login(self.username, self.password)

    def get_server(self):
        """العثور على السيرفر بالـ IP/Address أو الاسم."""
        with self.lock:
            if self.server is not None:
                return self.server

            if self.client is None:
                self._login()

            servers = self.client.account.list_servers()

            wanted = self.server_address

            for server in servers:
                address = str(
                    getattr(server, "address", "")
                ).strip().lower()

                name = str(
                    getattr(server, "name", "")
                ).strip().lower()

                if (
                    wanted == address
                    or wanted == name
                    or wanted in address
                ):
                    self.server = server
                    return server

            available = []

            for server in servers:
                available.append(
                    str(
                        getattr(server, "address", "")
                    )
                )

            raise RuntimeError(
                f"لم يتم العثور على السيرفر: {wanted}. "
                f"السيرفرات الموجودة: {available}"
            )

    def start(self):
        """تشغيل السيرفر."""
        server = self.get_server()
        result = server.start()
        return str(result) if result is not None else "تم إرسال طلب التشغيل."

    def stop(self):
        """إيقاف السيرفر."""
        server = self.get_server()
        result = server.stop()
        return str(result) if result is not None else "تم إرسال طلب الإيقاف."

    def restart(self):
        """إعادة تشغيل السيرفر."""
        server = self.get_server()

        if hasattr(server, "restart"):
            result = server.restart()
            return (
                str(result)
                if result is not None
                else "تم إرسال طلب إعادة التشغيل."
            )

        # بعض الإصدارات لا توفر restart مباشرة.
        server.stop()

        raise RuntimeError(
            "المكتبة الحالية لا توفر restart مباشرًا لهذا السيرفر."
        )

    def status(self):
        """قراءة حالة السيرفر."""
        server = self.get_server()

        status = getattr(server, "status", None)

        if callable(status):
            status = status()

        return str(status) if status is not None else "غير معروف"
