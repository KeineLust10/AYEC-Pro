from types import SimpleNamespace
import sqlite3

from src.ui.pages._accounting_func_mixin import AccountingFuncMixin
from src.ui.pages._stock_export import StockExportMixin
from src.utils import desktop_web_sync
from src.utils import toast_notification
from src.ui import modern_login_window


def test_toast_uses_central_manager(monkeypatch):
    calls = []
    manager = SimpleNamespace(
        show_toast=lambda message, toast_type, duration: calls.append(
            (message, toast_type, duration)
        )
    )
    monkeypatch.setattr(
        toast_notification, "_get_central_toast_manager", lambda: manager
    )

    toast_notification.show_toast(None, "Saved", "success", 2500)

    assert calls == [("Saved", "success", 2500)]


def test_login_failure_does_not_provision_duplicate_company(monkeypatch):
    events = []

    class FakeClient:
        provision_calls = 0

        def __init__(self, *args, **kwargs):
            self.cookies = {}

        def load_session(self, path):
            return {}

        def login(self, *args, **kwargs):
            raise desktop_web_sync.WebSyncError("login failed")

        def provision_desktop_tenant(self, payload):
            FakeClient.provision_calls += 1
            return {}

        @staticmethod
        def clear_session(path):
            return None

    monkeypatch.setattr(desktop_web_sync, "WebSyncClient", FakeClient)
    monkeypatch.setattr(
        desktop_web_sync, "configured_sync_url", lambda: "http://127.0.0.1"
    )
    monkeypatch.setattr(desktop_web_sync, "sync_session_path", lambda: "session.json")
    worker = desktop_web_sync.DesktopWebSyncWorker(
        username="demo",
        password="secret",
        tenant_id="tenant-1",
        allow_new_tenant=True,
    )
    worker.completed.connect(lambda ok, payload: events.append((ok, payload)))

    worker.run()

    assert FakeClient.provision_calls == 0
    assert events and events[0][0] is False
    assert "login failed" in events[0][1]["error"]


def test_deploy_update_command_is_consumed_and_forwarded_to_update_manager(monkeypatch):
    events = []
    completed_commands = []

    class FakeClient:
        def __init__(self, *args, **kwargs):
            self.cookies = {}

        def load_session(self, path):
            return {}

        def login(self, *args, **kwargs):
            return {
                "user": {
                    "username": "demo",
                    "tenant_id": "tenant-1",
                    "company_name": "Demo Company",
                }
            }

        def save_session(self, path, metadata):
            return None

        def sync_sqlite(self, path, push_local=True):
            return {"ok": True, "pulled": 0, "pushed": {"applied": 0}}

        def update_company_location(self, payload):
            return {"ok": True}

        def pending_commands(self):
            return [
                {
                    "id": 7,
                    "command_type": "deploy_update",
                    "payload": {
                        "version": "2.0.7",
                        "channel": "pilot",
                        "changelog": "Client update test",
                    },
                }
            ]

        def complete_command(self, command_id, success, result=None):
            completed_commands.append((command_id, success, result or {}))
            return {"ok": True}

        def upload_backup(self, path):
            return {"ok": True}

        @staticmethod
        def clear_session(path):
            return None

    monkeypatch.setattr(desktop_web_sync, "WebSyncClient", FakeClient)
    monkeypatch.setattr(
        desktop_web_sync, "configured_sync_url", lambda: "http://127.0.0.1"
    )
    monkeypatch.setattr(desktop_web_sync, "sync_session_path", lambda: "session.json")
    monkeypatch.setattr(
        desktop_web_sync.PathHelper, "get_db_path", lambda name: "company.db"
    )
    worker = desktop_web_sync.DesktopWebSyncWorker(
        username="demo",
        password="Secret123",
        tenant_id="tenant-1",
    )
    worker.completed.connect(lambda ok, payload: events.append((ok, payload)))

    worker.run()

    assert events and events[0][0] is True
    assert events[0][1]["update_requests"] == [
        {
            "version": "2.0.7",
            "channel": "pilot",
            "changelog": "Client update test",
        }
    ]
    assert completed_commands[0][0:2] == (7, True)


def test_first_sync_reads_and_forwards_saved_installation_location(
    monkeypatch, tmp_path
):
    database_path = tmp_path / "location.db"
    with sqlite3.connect(database_path) as conn:
        conn.execute(
            "CREATE TABLE company_info(company_name TEXT, authorized_person TEXT, "
            "phone TEXT, email TEXT, address TEXT)"
        )
        conn.execute(
            "INSERT INTO company_info VALUES(?,?,?,?,?)",
            ("Demo Company", "Demo User", "05000000000", "demo@example.com", "Istanbul"),
        )
        conn.execute("CREATE TABLE users(username TEXT, full_name TEXT, email TEXT)")
        conn.execute(
            "INSERT INTO users VALUES(?,?,?)",
            ("demo", "Demo User", "demo@example.com"),
        )
        conn.execute("CREATE TABLE settings(key TEXT, value TEXT)")
        conn.executemany(
            "INSERT INTO settings(key,value) VALUES(?,?)",
            [
                ("installation_lat", "41.0082"),
                ("installation_lng", "28.9784"),
                ("installation_address", "Istanbul"),
            ],
        )

    monkeypatch.setattr(
        desktop_web_sync.PathHelper,
        "get_db_path",
        lambda name: str(database_path),
    )

    payload = desktop_web_sync.local_provisioning_payload(
        "ayecpro.db", "demo", "Secret123"
    )

    assert payload["installation_lat"] == 41.0082
    assert payload["installation_lng"] == 28.9784
    assert payload["installation_address"] == "Istanbul"


def test_first_local_setup_can_provision_then_sync(monkeypatch):
    events = []

    class FakeClient:
        provision_calls = 0

        def __init__(self, *args, **kwargs):
            self.cookies = {}

        def load_session(self, path):
            return {}

        def login(self, *args, **kwargs):
            raise desktop_web_sync.WebSyncError("login failed")

        def provision_desktop_tenant(self, payload):
            FakeClient.provision_calls += 1
            return {
                "user": {
                    "username": payload["username"],
                    "tenant_id": "tenant-new",
                    "company_name": "New Company",
                }
            }

        def save_session(self, path, metadata):
            return None

        def sync_sqlite(self, path, push_local=True):
            return {"ok": True, "pulled": 0, "pushed": {"applied": 0}}

        def pending_commands(self):
            return []

        def upload_backup(self, path):
            return {"ok": True}

        @staticmethod
        def clear_session(path):
            return None

    monkeypatch.setattr(desktop_web_sync, "WebSyncClient", FakeClient)
    monkeypatch.setattr(
        desktop_web_sync, "configured_sync_url", lambda: "http://127.0.0.1"
    )
    monkeypatch.setattr(desktop_web_sync, "sync_session_path", lambda: "session.json")
    monkeypatch.setattr(
        desktop_web_sync,
        "local_provisioning_payload",
        lambda *args, **kwargs: {
            "username": "newuser",
            "password": "Secret123",
            "full_name": "New User",
            "email": "new@example.com",
            "company_name": "New Company",
            "sector": "teknik_servis",
        },
    )
    monkeypatch.setattr(
        desktop_web_sync.PathHelper, "get_db_path", lambda name: "company.db"
    )
    worker = desktop_web_sync.DesktopWebSyncWorker(
        username="newuser",
        password="Secret123",
        allow_new_tenant=True,
    )
    worker.completed.connect(lambda ok, payload: events.append((ok, payload)))

    worker.run()

    assert FakeClient.provision_calls == 1
    assert events and events[0][0] is True
    assert events[0][1]["session"]["tenant_id"] == "tenant-new"


def test_finance_export_keeps_original_currency_and_try_value():
    manager = SimpleNamespace(
        get_unified_ledger=lambda limit: [
            {
                "date": "2026-08-24",
                "type_label": "Gider",
                "description": "Stock purchase",
                "amount": 100,
                "currency": "USD",
                "rate": 48,
                "amount_try": 4800,
                "payment_method": "Cash",
                "ref_no": "REF-1",
                "status": "Done",
            }
        ]
    )
    page = SimpleNamespace(finance_manager=manager, ledger_data=[])

    row = AccountingFuncMixin._collect_ledger_export_rows(page)[0]

    assert row["Orijinal Tutar"] == 100
    assert row["Para Birimi"] == "USD"
    assert row["Doviz Kuru"] == 48
    assert row["TRY Karsiligi"] == 4800


def test_stock_export_adds_currency_rate_and_try_values(monkeypatch):
    monkeypatch.setattr(
        "src.ui.pages._stock_export.CurrencyHelper.require_rate",
        lambda db, currency: 50 if currency == "USD" else 1,
    )
    page = SimpleNamespace(db=object())

    row = StockExportMixin._build_stock_export_rows(
        page,
        [{"currency": "USD", "purchase_price": 10, "price": 15, "stock": 3}],
    )[0]

    assert row["export_exchange_rate"] == 50
    assert row["purchase_price_try"] == 500
    assert row["sale_price_try"] == 750
    assert row["stock_value_original"] == 30
    assert row["stock_value_try"] == 1500


def test_deleted_company_is_an_authoritative_login_denial(monkeypatch):
    events = []

    class FakeLicenseClient:
        def __init__(self, *args, **kwargs):
            pass

        def status_for_credentials(self, identifier, password, tenant_id):
            raise modern_login_window.LicenseApiError("Firma bulunamadi.")

    monkeypatch.setattr(
        modern_login_window, "LicenseApiClient", FakeLicenseClient
    )
    worker = modern_login_window._ServerAccessCheckWorker(
        "owner", "secret", "deleted-tenant"
    )
    worker.completed.connect(
        lambda reachable, allowed, message, payload: events.append(
            (reachable, allowed, message)
        )
    )

    worker.run()

    assert events == [(True, False, "Firma bulunamadi.")]


def test_unreachable_server_is_not_reported_as_company_revocation(monkeypatch):
    events = []

    class FakeLicenseClient:
        def __init__(self, *args, **kwargs):
            pass

        def status_for_credentials(self, identifier, password, tenant_id):
            raise modern_login_window.LicenseApiError(
                "AYEC Pro lisans servisine baglanilamadi: timeout"
            )

    monkeypatch.setattr(
        modern_login_window, "LicenseApiClient", FakeLicenseClient
    )
    worker = modern_login_window._ServerAccessCheckWorker(
        "owner", "secret", "active-tenant"
    )
    worker.completed.connect(
        lambda reachable, allowed, message, payload: events.append(
            (reachable, allowed)
        )
    )

    worker.run()

    assert events == [(False, False)]


def test_bad_gateway_is_treated_as_temporary_offline_state(monkeypatch):
    events = []

    class FakeLicenseClient:
        def __init__(self, *args, **kwargs):
            pass

        def status_for_credentials(self, identifier, password, tenant_id):
            raise modern_login_window.LicenseApiError(
                "HTTP Error 502: Bad Gateway",
                status_code=502,
            )

    monkeypatch.setattr(
        modern_login_window, "LicenseApiClient", FakeLicenseClient
    )
    worker = modern_login_window._ServerAccessCheckWorker(
        "owner", "secret", "active-tenant"
    )
    worker.completed.connect(
        lambda reachable, allowed, message, payload: events.append(
            (reachable, allowed)
        )
    )

    worker.run()

    assert events == [(False, False)]


def test_revoked_local_profile_can_be_removed_from_login_screen(monkeypatch):
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute(
        "CREATE TABLE users (username TEXT,active INTEGER,is_active INTEGER,"
        "auto_login INTEGER,remember_token TEXT)"
    )
    connection.execute(
        "INSERT INTO users VALUES ('ECAY',1,1,1,'token')"
    )
    settings = {
        "last_login_user": "ECAY",
        "server_access_revoked": "1",
        "web_sync_tenant_id": "deleted-tenant",
        "web_sync_enabled": "1",
    }

    class FakeDb:
        conn = connection
        cursor = connection.cursor()

        @staticmethod
        def _get_table_columns(table):
            return ["username", "active", "is_active", "auto_login", "remember_token"]

        @staticmethod
        def get_setting(key, default=""):
            return settings.get(key, default)

        @staticmethod
        def set_setting(key, value):
            settings[key] = value

    auth = SimpleNamespace(clear_token=lambda: None, logout=lambda: None)
    refreshed = []
    page = SimpleNamespace(
        db=FakeDb(),
        auth_manager=auth,
        refresh_user_list=lambda: refreshed.append(True),
    )
    monkeypatch.setattr(
        modern_login_window.QMessageBox,
        "question",
        lambda *args, **kwargs: modern_login_window.QMessageBox.StandardButton.Yes,
    )
    monkeypatch.setattr(modern_login_window, "show_success", lambda *args: None)
    monkeypatch.setattr(
        modern_login_window.WebSyncClient, "clear_session", lambda path: None
    )
    monkeypatch.setattr(
        modern_login_window, "sync_session_path", lambda: "session.json"
    )

    modern_login_window.ModernLoginWindow._remove_local_profile(page, "ECAY")

    user = connection.execute(
        "SELECT active,is_active,auto_login,remember_token FROM users"
    ).fetchone()
    assert tuple(user) == (0, 0, 0, None)
    assert settings["web_sync_tenant_id"] == ""
    assert settings["web_sync_enabled"] == "0"
    assert settings["server_access_revoked"] == "0"
    assert refreshed == [True]
