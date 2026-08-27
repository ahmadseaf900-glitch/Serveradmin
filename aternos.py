import os
import threading
from typing import Any, Optional, Tuple


try:
    from python_aternos import Client
except ImportError:
    Client = None


class AternosManager:
    """
    A small wrapper around the py-aternos package.

    Environment variables:

        ATERNOS_USERNAME
        ATERNOS_PASSWORD
        ATERNOS_SERVER

    ATERNOS_SERVER can be:
        MACESMP37.aternos.me

    or the server name visible in Aternos.
    """

    def __init__(self):
        self.username = os.getenv(
            "ATERNOS_USERNAME",
            "",
        ).strip()

        self.password = os.getenv(
            "ATERNOS_PASSWORD",
            "",
        ).strip()

        self.server_name = os.getenv(
            "ATERNOS_SERVER",
            "",
        ).strip().lower()

        self._client: Optional[Any] = None
        self._account: Optional[Any] = None
        self._server: Optional[Any] = None

        self._lock = threading.RLock()

    # ========================================================
    # Validation
    # ========================================================

    def _validate_config(self):
        """Validate required Aternos configuration."""

        if Client is None:
            return False, (
                "مكتبة py-aternos غير مثبتة.\n"
                "تأكد أن requirements.txt يحتوي:\n"
                "py-aternos==3.0.74"
            )

        if not self.username:
            return False, (
                "ATERNOS_USERNAME غير موجود "
                "في Render Environment Variables."
            )

        if not self.password:
            return False, (
                "ATERNOS_PASSWORD غير موجود "
                "في Render Environment Variables."
            )

        if not self.server_name:
            return False, (
                "ATERNOS_SERVER غير موجود "
                "في Render Environment Variables."
            )

        return True, "OK"

    # ========================================================
    # Login
    # ========================================================

    def _login(self):
        """Login to Aternos and cache the account session."""

        valid, message = self._validate_config()

        if not valid:
            return False, message

        with self._lock:
            try:
                client = Client()

                client.login(
                    self.username,
                    self.password,
                )

                self._client = client
                self._account = client.account

                return True, "تم تسجيل الدخول إلى Aternos."

            except Exception as exc:
                self._client = None
                self._account = None
                self._server = None

                return False, str(exc)

    # ========================================================
    # Find server
    # ========================================================

    def _get_server(self):
        """Login if necessary and find the configured server."""

        with self._lock:

            if self._server is not None:
                return True, self._server

            if self._account is None:

                ok, result = self._login()

                if not ok:
                    return False, result

            try:
                servers = self._account.list_servers()

                wanted = self.server_name

                for server in servers:

                    address = str(
                        getattr(
                            server,
                            "address",
                            "",
                        )
                    ).strip().lower()

                    name = str(
                        getattr(
                            server,
                            "name",
                            "",
                        )
                    ).strip().lower()

                    if (
                        wanted == address
                        or wanted == name
                        or wanted in address
                    ):
                        self._server = server

                        return True, server

                return False, (
                    f"لم يتم العثور على السيرفر: "
                    f"{self.server_name}"
                )

            except Exception as exc:
                self._client = None
                self._account = None
                self._server = None

                return False, str(exc)

    # ========================================================
    # Generic action
    # ========================================================

    def _action(self, action: str):
        """Execute an Aternos server action."""

        ok, server_or_error = self._get_server()

        if not ok:
            return False, server_or_error

        server = server_or_error

        try:
            method = getattr(server, action)

            result = method()

            if result is None:
                return True, "OK"

            return True, str(result)

        except Exception as exc:
            # Clear cached session so the next operation
            # attempts a fresh login.
            with self._lock:
                self._client = None
                self._account = None
                self._server = None

            return False, str(exc)

    # ========================================================
    # Public actions
    # ========================================================

    def start(self):
        """Start the Aternos server."""
        return self._action("start")

    def stop(self):
        """Stop the Aternos server."""
        return self._action("stop")

    def restart(self):
        """Restart the Aternos server."""
        return self._action("restart")

    # ========================================================
    # Status
    # ========================================================

    def status(self) -> Tuple[bool, str]:
        """Return the server status."""

        ok, server_or_error = self._get_server()

        if not ok:
            return False, str(server_or_error)

        server = server_or_error

        try:
            status = getattr(
                server,
                "status",
                None,
            )

            if callable(status):
                status = status()

            if status is None:
                return True, "Status غير متوفر."

            return True, str(status)

        except Exception as exc:
            return False, str(exc)

    # ========================================================
    # Server info
    # ========================================================

    def info(self) -> Tuple[bool, str]:
        """Return useful server information."""

        ok, server_or_error = self._get_server()

        if not ok:
            return False, str(server_or_error)

        server = server_or_error

        try:
            address = getattr(
                server,
                "address",
                "غير معروف",
            )

            name = getattr(
                server,
                "name",
                "غير معروف",
            )

            software = getattr(
                server,
                "software",
                "غير معروف",
            )

            version = getattr(
                server,
                "version",
                "غير معروف",
            )

            status = getattr(
                server,
                "status",
                "غير معروف",
            )

            if callable(status):
                status = status()

            text = (
                f"Name: {name}\n"
                f"Address: {address}\n"
                f"Software: {software}\n"
                f"Version: {version}\n"
                f"Status: {status}"
            )

            return True, text

        except Exception as exc:
            return False, str(exc)

    # ========================================================
    # Players
    # ========================================================

    def players(self) -> Tuple[bool, str]:
        """
        Return player information if the library exposes it.

        Aternos-side availability of player data can vary.
        """

        ok, server_or_error = self._get_server()

        if not ok:
            return False, str(server_or_error)

        server = server_or_error

        try:
            candidates = [
                "players",
                "player_list",
                "online_players",
            ]

            for attribute in candidates:

                value = getattr(
                    server,
                    attribute,
                    None,
                )

                if value is None:
                    continue

                if callable(value):
                    value = value()

                return True, str(value)

            return True, (
                "لا توجد معلومات لاعبين متاحة "
                "من واجهة Aternos الحالية."
            )

        except Exception as exc:
            return False, str(exc)

    # ========================================================
    # Console
    # ========================================================

    def console(self, command: str) -> Tuple[bool, str]:
        """
        Execute a console command when supported by the
        installed Aternos library.

        This is intentionally capability-detected instead
        of assuming a method exists.
        """

        command = command.strip()

        if not command:
            return False, "الأمر فارغ."

        ok, server_or_error = self._get_server()

        if not ok:
            return False, str(server_or_error)

        server = server_or_error

        try:
            methods = [
                "command",
                "send_command",
                "console",
            ]

            for method_name in methods:

                method = getattr(
                    server,
                    method_name,
                    None,
                )

                if not callable(method):
                    continue

                result = method(command)

                if result is None:
                    return True, "تم إرسال الأمر."

                return True, str(result)

            return False, (
                "نسخة py-aternos الحالية لا توفر "
                "واجهة Console لهذا السيرفر."
            )

        except Exception as exc:
            return False, str(exc)
