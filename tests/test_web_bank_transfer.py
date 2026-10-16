import pytest

from Web_Arayuzu import Main as web_main


class FakeTransferCursor:
    def __init__(self, rows):
        self.rows = rows
        self.query = None
        self.params = None

    def execute(self, query, params=()):
        self.query = query
        self.params = params

    def fetchall(self):
        return list(self.rows)


class FakeTransferDatabase:
    rows = [(2, 1), (7, 1)]

    def __init__(self, **_kwargs):
        self.cursor = FakeTransferCursor(self.rows)
        self.transfer = None
        self.closed = False

    def transfer_between_accounts(self, source_id, target_id, amount, description):
        self.transfer = (source_id, target_id, amount, description)
        return True, "ok"

    def close(self):
        self.closed = True


def _patch_transfer_environment(monkeypatch, tmp_path, database):
    import src.database

    monkeypatch.setattr(src.database, "Database", lambda **_kwargs: database)
    monkeypatch.setattr(web_main, "active_tenant_id", lambda: "tenant-a")
    monkeypatch.setattr(web_main, "active_db_path", lambda: tmp_path / "tenant-a.db")


def test_bank_transfer_uses_active_tenant_and_bounded_description(monkeypatch, tmp_path):
    database = FakeTransferDatabase()
    _patch_transfer_environment(monkeypatch, tmp_path, database)
    description = "x" * 250

    result = web_main.desktop_bank_account_transfer(
        {"id": 14, "role": "Admin", "_tenant_id": "tenant-a"},
        {
            "from_account_id": "2",
            "to_account_id": "7",
            "amount": "45.5",
            "description": description,
        },
    )

    assert result == {"ok": True}
    assert database.cursor.params == (2, 7)
    assert database.transfer == (2, 7, 45.5, "x" * 200)
    assert database.closed is True


def test_bank_transfer_rejects_inactive_or_missing_accounts(monkeypatch, tmp_path):
    database = FakeTransferDatabase()
    database.cursor.rows = [(2, 1), (7, 0)]
    _patch_transfer_environment(monkeypatch, tmp_path, database)

    with pytest.raises(ValueError, match="two active"):
        web_main.desktop_bank_account_transfer(
            {"id": 14, "role": "Admin", "_tenant_id": "tenant-a"},
            {"from_account_id": 2, "to_account_id": 7, "amount": 10},
        )

    assert database.transfer is None
    assert database.closed is True


@pytest.mark.parametrize("payload", [
    {"from_account_id": 2, "to_account_id": 2, "amount": 10},
    {"from_account_id": 2, "to_account_id": 7, "amount": 0},
    {"from_account_id": 2, "to_account_id": 7, "amount": "nan"},
    {"from_account_id": 2, "to_account_id": 7, "amount": 1_000_000_001},
])
def test_bank_transfer_rejects_invalid_values_before_database_open(monkeypatch, tmp_path, payload):
    import src.database

    monkeypatch.setattr(src.database, "Database", lambda **_kwargs: pytest.fail("invalid transfer opened database"))
    monkeypatch.setattr(web_main, "active_tenant_id", lambda: "tenant-a")
    monkeypatch.setattr(web_main, "active_db_path", lambda: tmp_path / "tenant-a.db")

    with pytest.raises(ValueError):
        web_main.desktop_bank_account_transfer(
            {"id": 14, "role": "Admin", "_tenant_id": "tenant-a"}, payload
        )


def test_bank_transfer_rejects_actor_from_another_tenant(monkeypatch, tmp_path):
    monkeypatch.setattr(web_main, "active_tenant_id", lambda: "tenant-a")

    with pytest.raises(PermissionError, match="active company"):
        web_main.desktop_bank_account_transfer(
            {"id": 14, "role": "Admin", "_tenant_id": "tenant-b"},
            {"from_account_id": 2, "to_account_id": 7, "amount": 10},
        )


@pytest.mark.parametrize("role", ["Manager", "Technician", "User"])
def test_bank_management_rejects_non_admin_roles(role):
    with pytest.raises(PermissionError, match="Admin permission"):
        web_main._bank_manager_required({"id": 14, "role": role})


def test_bank_transfer_denies_non_admin_before_opening_tenant_database(monkeypatch, tmp_path):
    import src.database

    monkeypatch.setattr(src.database, "Database", lambda **_kwargs: pytest.fail("unauthorized transfer opened database"))
    monkeypatch.setattr(web_main, "active_tenant_id", lambda: "tenant-a")
    monkeypatch.setattr(web_main, "active_db_path", lambda: tmp_path / "tenant-a.db")

    with pytest.raises(PermissionError, match="Admin permission"):
        web_main.desktop_bank_account_transfer(
            {"id": 14, "role": "Manager", "_tenant_id": "tenant-a"},
            {"from_account_id": 2, "to_account_id": 7, "amount": 10},
        )


def test_generic_bank_account_writes_use_admin_guard():
    source = (web_main.ROOT / "Main.py").read_text(encoding="utf-8")
    assert 'if table == "bank_accounts":' in source
    assert '_bank_manager_required(user)' in source
