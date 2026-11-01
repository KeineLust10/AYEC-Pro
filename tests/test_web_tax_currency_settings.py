import json
import sqlite3
import subprocess
from pathlib import Path

import pytest

from Web_Arayuzu import Main as web_main
from src.utils.tax_settings import TaxSettings


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
    assert '["tax-currency","license"].includes(settingsSection)?"":' in settings_renderer
    assert "async function saveWebBankSettings()" in app
    assert 'new Set(["bank_default_currency","bank_auto_fx","bank_sync_finance","bank_warn_negative"])' in app
    assert 'invoiceLineMarkup(1,ayecNormalizeVatPercent(desktopSettings?.default_vat_percent??desktopSettings?.vat_default_rate))' in app
    assert 'invoiceLineMarkup(rows().length+1,ayecNormalizeVatPercent(desktopSettings?.default_vat_percent??desktopSettings?.vat_default_rate))' in app
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


def test_web_vat_normalization_matches_desktop_tax_settings():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    pc_builder = (WEB / "pc-builder-reference.js").read_text(encoding="utf-8")
    smart_home = (WEB / "smart-home-sales-reference.js").read_text(encoding="utf-8")
    start = app.index("function ayecNormalizeVatPercent")
    end = app.index("\nconst money", start)
    helper = app[start:end]
    values = [None, 0, 0.08, "", 8, 8.5, 18, 20, 150, -2, "invalid"]
    node_script = (
        helper
        + "\nprocess.stdout.write(JSON.stringify("
        + json.dumps(values)
        + ".map(ayecNormalizeVatPercent)));"
    )
    result = subprocess.run(["node", "-e", node_script], capture_output=True, text=True, check=True)

    assert json.loads(result.stdout) == [TaxSettings.normalize_percent(value) for value in values]
    assert "vat=ayecNormalizeVatPercent(settings.default_vat_percent??settings.vat_default_rate)" in app
    assert "ayecNormalizeVatPercent(desktopSettings?.default_vat_percent??db.settings?.default_vat_percent)" in app
    assert "ayecNormalizeVatPercent(desktopSettings?.default_vat_percent)" in pc_builder
    assert "ayecNormalizeVatPercent(desktopSettings?.default_vat_percent ?? db.settings?.default_vat_percent)" in smart_home


def test_invoice_lines_allow_the_same_custom_vat_rates_as_desktop():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    start = app.index("function invoiceLineMarkup")
    end = app.index("\nfunction renderInvoiceComposer", start)
    markup_function = app[start:end]
    normalize_start = app.index("function ayecNormalizeVatPercent")
    normalize_end = app.index("\nconst money", normalize_start)
    node_script = (
        app[normalize_start:normalize_end]
        + "\n"
        + markup_function
        + "\nprocess.stdout.write(JSON.stringify([invoiceLineMarkup(1, 8.5), invoiceLineMarkup(2, 0.08), invoiceLineMarkup(3, 0)]));"
    )
    result = subprocess.run(["node", "-e", node_script], capture_output=True, text=True, check=True)
    rows = json.loads(result.stdout)

    assert 'class="invoice-line-vat" type="number" min="0" max="100" step="any" value="8.5"' in rows[0]
    assert 'class="invoice-line-vat" type="number" min="0" max="100" step="any" value="8"' in rows[1]
    assert 'class="invoice-line-vat" type="number" min="0" max="100" step="any" value="0"' in rows[2]
    assert '<select class="invoice-line-vat"' not in "".join(rows)


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
