import pytest
from pathlib import Path

from Web_Arayuzu import Main as web_main


def test_check_note_context_menu_matches_desktop_detail_and_status_actions():
    root = Path(__file__).resolve().parents[1]
    desktop = (root / "src/ui/pages/finance/check_note_page.py").read_text(encoding="utf-8")
    web = (root / "Web_Arayuzu/web/check-notes-parity.js").read_text(encoding="utf-8")
    assert 'QAction("Detay G\u00f6r\u00fcnt\u00fcle", self)' in desktop
    assert 'menu.addMenu("Durum De\u011fi\u015ftir")' in desktop
    for status in (
        '"Portf\\u00f6yde"',
        '"Tahsil Edildi"',
        '"Ciro Edildi"',
        '"\\u00d6dendi"',
        '"Kar\\u015f\\u0131l\\u0131ks\\u0131z"',
        '"\\u0130ade"',
    ):
        assert status in web
    assert 'data-check-context-action="detail"' in web
    assert 'data-check-status-toggle' in web


class FakeCheckCursor:
    def __init__(self, record):
        self.record = record
        self.rowcount = 0

    def execute(self, query, params=()):
        if query.startswith("UPDATE checks_notes"):
            self.record[7] = params[0]
            self.rowcount = 1

    def fetchone(self):
        return tuple(self.record)


class FakeCheckDatabase:
    record = [9, "Check", "Giri\u015f (Al\u0131nan)", 125.0, "Example Bank", "Issuer", "Recipient", "Portf\u00f6yde"]

    def __init__(self, **_kwargs):
        self.cursor = FakeCheckCursor(self.record)
        self.conn = self
        self.transactions = []
        self.closed = False
        self.committed = False
        self.rolled_back = False

    def get_bank_accounts(self):
        return [(4, "Main Bank")]

    def add_transaction(self, **values):
        self.transactions.append(values)
        return len(self.transactions) + 100

    def add_check_note(self, data):
        self.created_check = dict(data)
        return 31

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def test_check_note_status_options_and_update_preserve_desktop_finance_effects(monkeypatch, tmp_path):
    import src.database

    FakeCheckDatabase.record = [9, "Check", "Giri\u015f (Al\u0131nan)", 125.0, "Example Bank", "Issuer", "Recipient", "Portf\u00f6yde"]
    instances = []

    def create_database(**kwargs):
        database = FakeCheckDatabase(**kwargs)
        instances.append(database)
        return database

    audits = []
    monkeypatch.setattr(src.database, "Database", create_database)
    monkeypatch.setattr(web_main, "active_tenant_id", lambda: "tenant-a")
    monkeypatch.setattr(web_main, "active_db_path", lambda: tmp_path / "tenant-a.db")
    monkeypatch.setattr(web_main, "_support_audit", lambda *args, **kwargs: audits.append((args, kwargs)))
    actor = {"id": 17, "role": "Admin", "_tenant_id": "tenant-a"}

    options = web_main.desktop_check_note_status_options(actor, 9, "Tahsil Edildi")
    result = web_main.desktop_update_check_note_status(actor, 9, "Tahsil Edildi", 4)

    assert options["bank_transaction_type"] == "Gelir"
    assert options["reversal_transaction_type"] == "Gider"
    assert options["bank_accounts"] == [{"id": 4, "bank_name": "Main Bank"}]
    assert result["transaction_ids"] == [101, 102]
    transactions = instances[-1].transactions
    assert [item["t_type"] for item in transactions] == ["Gider", "Gelir"]
    assert transactions[0]["category"] == "Check Portf\u00f6y \u00c7\u0131k\u0131\u015f\u0131"
    assert transactions[1]["bank_account_id"] == 4
    assert all(item["commit"] is False for item in transactions)
    assert instances[-1].committed is True
    assert instances[-1].closed is True
    assert audits


def test_check_note_status_update_rejects_another_bank_account(monkeypatch, tmp_path):
    import src.database

    FakeCheckDatabase.record = [9, "Check", "Giri\u015f (Al\u0131nan)", 125.0, "Example Bank", "Issuer", "Recipient", "Portf\u00f6yde"]
    database = FakeCheckDatabase()
    monkeypatch.setattr(src.database, "Database", lambda **_kwargs: database)
    monkeypatch.setattr(web_main, "active_tenant_id", lambda: "tenant-a")
    monkeypatch.setattr(web_main, "active_db_path", lambda: tmp_path / "tenant-a.db")

    with pytest.raises(ValueError, match="available bank"):
        web_main.desktop_update_check_note_status(
            {"id": 17, "_tenant_id": "tenant-a"}, 9, "Tahsil Edildi", 99
        )

    assert database.rolled_back is True
    assert database.committed is False
    assert database.transactions == []
    assert database.closed is True


def test_check_note_finance_rules_match_desktop_status_side_effects():
    assert web_main._check_note_finance_effects("Giri\u015f (Al\u0131nan)", "Tahsil Edildi") == ("Gelir", "Gider")
    assert web_main._check_note_finance_effects("\u00c7\u0131k\u0131\u015f (Verilen)", "\u00d6dendi") == ("Gider", "Gelir")
    assert web_main._check_note_finance_effects("Giri\u015f (Al\u0131nan)", "Ciro Edildi") == (None, "Gider")
    assert web_main._check_note_finance_effects("Giri\u015f (Al\u0131nan)", "\u0130ade") == (None, None)


def test_check_note_routes_reject_another_tenant_context(monkeypatch):
    monkeypatch.setattr(web_main, "active_tenant_id", lambda: "tenant-a")

    with pytest.raises(PermissionError, match="active company"):
        web_main._check_note_tenant_required({"id": 20, "_tenant_id": "tenant-b", "role": "Admin"})


def test_check_note_create_matches_desktop_initial_finance_entry(monkeypatch, tmp_path):
    import src.database

    database = FakeCheckDatabase()
    audits = []
    monkeypatch.setattr(src.database, "Database", lambda **_kwargs: database)
    monkeypatch.setattr(web_main, "active_tenant_id", lambda: "tenant-a")
    monkeypatch.setattr(web_main, "active_db_path", lambda: tmp_path / "tenant-a.db")
    monkeypatch.setattr(web_main, "_support_audit", lambda *args, **kwargs: audits.append((args, kwargs)))

    result = web_main.desktop_add_check_note(
        {"id": 17, "_tenant_id": "tenant-a"},
        {
            "type": "\u00c7ek",
            "direction": "Giri\u015f (Al\u0131nan)",
            "amount": "125.50",
            "due_date": "2026-11-15",
            "issuer": "Issuer",
            "recipient": "",
            "bank_name": "Example Bank",
            "branch_name": "Main",
            "status": "Portf\u00f6yde",
            "id": 999,
            "image_path": "untrusted-path",
        },
    )

    assert result == {"ok": True, "id": 31, "finance_warning": None}
    assert database.created_check == {
        "type": "\u00c7ek",
        "direction": "Giri\u015f (Al\u0131nan)",
        "amount": 125.5,
        "due_date": "2026-11-15",
        "issuer": "Issuer",
        "recipient": "",
        "bank_name": "Example Bank",
        "branch_name": "Main",
        "status": "Portf\u00f6yde",
    }
    assert database.transactions == [{
        "t_type": "Gelir",
        "category": "Al\u0131nan \u00c7ek",
        "amount": 125.5,
        "description": "\u00c7ek Al\u0131nd\u0131 - D\u00fczenleyen: Issuer (Vade: 2026-11-15)",
        "customer_name": "Issuer",
        "payment_method": "\u00c7ek/Senet",
    }]
    assert audits
    assert database.closed is True


@pytest.mark.parametrize("changes", [
    {"amount": "nan"},
    {"amount": "0"},
    {"due_date": "15/11/2026"},
    {"issuer": "", "recipient": ""},
    {"type": "Other"},
    {"direction": "unknown"},
])
def test_check_note_create_rejects_invalid_desktop_form_data(monkeypatch, tmp_path, changes):
    import src.database

    monkeypatch.setattr(src.database, "Database", lambda **_kwargs: pytest.fail("invalid input opened database"))
    monkeypatch.setattr(web_main, "active_tenant_id", lambda: "tenant-a")
    monkeypatch.setattr(web_main, "active_db_path", lambda: tmp_path / "tenant-a.db")
    payload = {
        "type": "\u00c7ek",
        "direction": "Giri\u015f (Al\u0131nan)",
        "amount": "12",
        "due_date": "2026-11-15",
        "issuer": "Issuer",
        "recipient": "",
        "status": "Portf\u00f6yde",
    }
    payload.update(changes)

    with pytest.raises(ValueError):
        web_main.desktop_add_check_note({"id": 17, "_tenant_id": "tenant-a"}, payload)
