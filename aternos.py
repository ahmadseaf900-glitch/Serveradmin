import os
import threading
import time

try:
    from python_aternos import Client
except ImportError as exc:
    Client = None
    IMPORT_ERROR = exc


ATERNOS_USERNAME = os.getenv("ATERNOS_USERNAME", "").strip()
ATERNOS_PASSWORD = os.getenv("ATERNOS_PASSWORD", "").strip()

DEFAULT_SERVER_HOST = os.getenv(
    "MC_SERVER_HOST",
    "MACESMP37.aternos.me"
).strip().lower()


_client = None
_account = None
_servers = None

_lock = threading.RLock()


def _check_library():
    """يتأكد من تثبيت مكتبة python-aternos."""
    if Client is None:
        raise RuntimeError(
            "python-aternos غير مثبت. "
            "أضفه إلى requirements.txt."
        )


def _check_credentials():
    """يتأكد من وجود بيانات حساب Aternos."""
    if not ATERNOS_USERNAME:
        raise RuntimeError(
            "ATERNOS_USERNAME غير موجود في Environment Variables."
        )

    if not ATERNOS_PASSWORD:
        raise RuntimeError(
            "ATERNOS_PASSWORD غير موجود في Environment Variables."
        )


def login(force=False):
    """
    تسجيل الدخول إلى حساب Aternos.

    يتم الاحتفاظ بالجلسة في الذاكرة حتى لا نسجل الدخول
    عند كل ضغطة زر.
    """

    global _client
    global _account
    global _servers

    with _lock:

        _check_library()
        _check_credentials()

        if (
            not force
            and _client is not None
            and _account is not None
        ):
            return _account

        _client = Client()

        try:
            _client.login(
                ATERNOS_USERNAME,
                ATERNOS_PASSWORD
            )
        except Exception as exc:
            _client = None
            _account = None
            _servers = None

            raise RuntimeError(
                f"فشل تسجيل الدخول إلى Aternos: {exc}"
            ) from exc

        _account = _client.account
        _servers = None

        return _account


def list_servers():
    """جلب قائمة السيرفرات الموجودة في حساب Aternos."""

    global _servers

    with _lock:

        account = login()

        try:
            _servers = account.list_servers()
        except Exception as exc:
            _servers = None

            raise RuntimeError(
                f"فشل جلب سيرفرات Aternos: {exc}"
            ) from exc

        return _servers


def _server_address(server):
    """استخراج عنوان السيرفر من كائن Aternos."""

    for attr in (
        "address",
        "ip",
        "host"
    ):
        try:
            value = getattr(server, attr, None)

            if value:
                return str(value).strip().lower()
        except Exception:
            pass

    return ""


def find_server(host=None):
    """
    العثور على السيرفر من حساب Aternos.

    المطابقة تتم أولًا بالعنوان الكامل.
    """

    target = (
        host or DEFAULT_SERVER_HOST
    ).strip().lower()

    target = target.split(":")[0]

    servers = list_servers()

    if not servers:
        raise RuntimeError(
            "لم يتم العثور على أي سيرفر في حساب Aternos."
        )

    # المطابقة الدقيقة
    for server in servers:

        address = _server_address(server)

        if address == target:
            return server

    # مطابقة بدون .aternos.me في حال وجود اختلاف
    for server in servers:

        address = _server_address(server)

        if (
            address.rstrip(".")
            == target.rstrip(".")
        ):
            return server

    available = []

    for server in servers:

        address = _server_address(server)

        if address:
            available.append(address)

    available_text = ", ".join(
        available
    ) or "لا توجد عناوين معروفة"

    raise RuntimeError(
        "لم أجد السيرفر المطلوب في حساب Aternos.\n"
        f"المطلوب: {target}\n"
        f"السيرفرات الموجودة: {available_text}"
    )


def _server_status(server):
    """
    محاولة الحصول على حالة السيرفر من كائن Aternos.
    """

    for attr in (
        "status",
        "state"
    ):
        try:
            value = getattr(
                server,
                attr,
                None
            )

            if value is not None:
                return str(value).lower()
        except Exception:
            pass

    return ""


def start(host=None):
    """تشغيل السيرفر عبر حساب Aternos."""

    with _lock:

        server = find_server(host)

        before = _server_status(server)

        try:
            result = server.start()
        except Exception as exc:
            # محاولة إعادة تسجيل الدخول مرة واحدة
            login(force=True)

            server = find_server(host)

            try:
                result = server.start()
            except Exception as retry_exc:
                raise RuntimeError(
                    f"فشل تشغيل السيرفر: {retry_exc}"
                ) from retry_exc

        return {
            "success": True,
            "action": "start",
            "address": _server_address(server),
            "previous_status": before,
            "result": str(result)
        }


def stop(host=None):
    """إيقاف السيرفر عبر حساب Aternos."""

    with _lock:

        server = find_server(host)

        before = _server_status(server)

        try:
            result = server.stop()
        except Exception as exc:
            login(force=True)

            server = find_server(host)

            try:
                result = server.stop()
            except Exception as retry_exc:
                raise RuntimeError(
                    f"فشل إيقاف السيرفر: {retry_exc}"
                ) from retry_exc

        return {
            "success": True,
            "action": "stop",
            "address": _server_address(server),
            "previous_status": before,
            "result": str(result)
        }


def restart(host=None):
    """
    إعادة تشغيل السيرفر.

    إذا كانت نسخة المكتبة توفر restart() نستعملها.
    وإذا لم توفرها، ننفذ Stop ثم ننتظر قليلًا ثم Start.
    """

    with _lock:

        server = find_server(host)

        restart_method = getattr(
            server,
            "restart",
            None
        )

        if callable(restart_method):

            try:
                result = restart_method()

                return {
                    "success": True,
                    "action": "restart",
                    "address": _server_address(server),
                    "result": str(result)
                }

            except Exception:
                # ننتقل إلى Stop/Start
                pass

        # fallback
        stop_result = stop(host)

        time.sleep(3)

        start_result = start(host)

        return {
            "success": True,
            "action": "restart",
            "address": start_result.get(
                "address",
                stop_result.get("address", "")
            ),
            "stop": stop_result,
            "start": start_result
        }


def get_status(host=None):
    """
    قراءة حالة السيرفر من حساب Aternos إن أمكن.
    """

    server = find_server(host)

    status = _server_status(server)

    return {
        "success": True,
        "address": _server_address(server),
        "status": status,
        "server": server
    }


def reset_session():
    """مسح جلسة Aternos من الذاكرة."""

    global _client
    global _account
    global _servers

    with _lock:
        _client = None
        _account = None
        _servers = None
