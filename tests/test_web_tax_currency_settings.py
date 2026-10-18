import sqlite3
from pathlib import Path

import pytest

from Web_Arayuzu import Main as web_main


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_tax_and_exchange_settings_are_available_and_drive_invoice_defaults():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    server = (ROOT / "Web_Arayuzu" / "Main.py").read_text(encoding="utf-8")
    tax_start = app.index('"tax-currency":{')
    tax_end = app.index("\n integrations:", tax_start)
    tax_definition = app[tax_start:tax_end]

    assert '["tax-currency","%","KDV & Kur Senkronizasyonu"]' in app
    assert '"tax-currency":{title:"KDV & Kur Senkronizasyonu"' in app
    assert '"vat_default_rate"' in app
    assert '"bank_auto_fx"' in app
    assert '"bank_fx_update_minutes"' in app
    assert '"currency_precision"' in app
    assert '["currency_precision","Para Birimi Hassasiyeti","select","2",["0","1","2","3"]]' in app
    company_reference = (WEB / "settings-theme-reference.js").read_text(encoding="utf-8")
    assert "Array.isArray(configuredOptions)" in company_reference
    assert "options.map(option => `<option value=\"${option}\"" in company_reference
    assert '"bank_auto_fx"' not in tax_definition
    assert '"bank_fx_update_minutes"' not in tax_definition
    assert '"currency_precision"' not in tax_definition
    settings_renderer = app[app.index("function renderSettings()"):app.index("\nfunction ", app.index("function renderSettings()"))]
    assert 'settingsSection==="tax-currency"?"":' in settings_renderer
    assert "async function saveWebBankSettings()" in app
    assert 'new Set(["bank_default_currency","bank_auto_fx","bank_sync_finance","bank_warn_negative"])' in app
    assert 'invoiceLineMarkup(1,desktopSettings.vat_default_rate??20)' in app
    assert 'invoiceLineMarkup(rows().length+1,desktopSettings.vat_default_rate??20)' in app
    assert 'data-tax-currency-action="save-vat"' in app
    assert 'data-tax-currency-action="save-rates"' in app
    assert 'data-tax-currency-action="fetch-rates"' in app
    assert 'data-tax-currency-action="sync"' in app
    assert 'data-tax-currency-action="backup"' in app
    assert '"USD","EUR","GBP"' in app
    assert '"/api/desktop/tax-currency/vat"' in app
    assert '"/api/desktop/exchange-rates/manual"' in app
    assert 'def save_desktop_manual_exchange_rates(conn: sqlite3.Connection, rates) -> dict:' in server
    assert 'if not role_is_admin(user.get("role")):' in server
    assert '"/api/desktop/tax-currency/vat"' in server
    assert '"/api/desktop/exchange-rates/manual"' in server


def _financial_connection():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE product_bank_mappings (
            id INTEGER PRIMARY KEY,
            default_kdv_rate REAL,
            updated_at TEXT
        );
        INSERT INTO product_bank_mappings(default_kdv_rate) VALUES (20);
        CREATE TABLE exchange_rates (
            id INTEGER PRIMARY KEY,
            currency TEXT NOT NULL,
            buying_rate REAL NOT NULL,
            selling_rate REAL NOT NULL,
            effective_date TEXT,
            source TEXT,
            created_at TEXT
        );
        """
    )
    return conn


def test_tax_currency_settings_store_tenant_defaults_and_all_desktop_rates():
    conn = _financial_connection()
    try:
        assert web_main.save_desktop_vat_percent(conn, 8.5) == 8.5
        settings = dict(conn.execute("SELECT key,value FROM settings").fetchall())
        assert settings["default_vat_percent"] == "8.5"
        assert settings["vat_default_rate"] == "8.5"
        assert settings["financial_defaults_revision"]
        assert conn.execute("SELECT default_kdv_rate FROM product_bank_mappings").fetchone()[0] == 8.5

        saved = web_main.save_desktop_manual_exchange_rates(
            conn,
            {"USD": 45.5, "EUR": 49.25, "GBP": 58.75},
        )
        assert saved == {"USD": 45.5, "EUR": 49.25, "GBP": 58.75}
        rows = conn.execute(
            "SELECT currency,buying_rate,selling_rate,source FROM exchange_rates ORDER BY currency"
        ).fetchall()
        assert [(row[0], row[1], row[2], row[3]) for row in rows] == [
            ("EUR", 49.25, 49.25, "MANUAL"),
            ("GBP", 58.75, 58.75, "MANUAL"),
            ("USD", 45.5, 45.5, "MANUAL"),
        ]
    finally:
        conn.close()


def test_tax_currency_settings_reject_invalid_rates_without_partial_writes():
    conn = _financial_connection()
    try:
        with pytest.raises(ValueError):
            web_main.save_desktop_vat_percent(conn, 101)
        with pytest.raises(ValueError):
            web_main.save_desktop_manual_exchange_rates(conn, {"USD": 45, "EUR": -1})
        assert conn.execute("SELECT COUNT(*) FROM exchange_rates").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM settings").fetchone()[0] == 0
    finally:
        conn.close()
