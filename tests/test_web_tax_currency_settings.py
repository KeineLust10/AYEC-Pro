from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_tax_and_exchange_settings_are_available_and_drive_invoice_defaults():
    app = (WEB / "app.js").read_text(encoding="utf-8")

    assert '["tax-currency","%","KDV & Kur Senkronizasyonu"]' in app
    assert '"tax-currency":{title:"KDV & Kur Senkronizasyonu"' in app
    assert '"vat_default_rate"' in app
    assert '"bank_auto_fx"' in app
    assert '"bank_fx_update_minutes"' in app
    assert 'invoiceLineMarkup(1,desktopSettings.vat_default_rate??20)' in app
    assert 'invoiceLineMarkup(rows().length+1,desktopSettings.vat_default_rate??20)' in app
