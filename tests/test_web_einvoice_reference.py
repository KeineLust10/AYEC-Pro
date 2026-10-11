from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_invoice_reference_controls_and_mobile_line_cards_are_present():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    styles = (WEB / "styles.css").read_text(encoding="utf-8")
    assert 'id="invoiceVkn"' in app
    assert 'id="invoiceScenario"' in app
    assert 'id="invoiceDeliveryRef"' in app
    assert 'id="invoiceLinesBody"' in app
    assert 'data-invoice-action="send"' in app
    assert '@media(max-width:620px){.einvoice-ribbon' in styles
    assert '.einvoice-table tbody{display:grid;gap:10px' in styles


def test_invoice_persists_numeric_total_without_parsing_localized_currency_text():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    assert 'let savedId=null,currentTotal=0' in app
    assert 'currentTotal=total' in app
    assert 'amount:currentTotal,status,json_data:' in app
    assert 'invoiceGrandTotal").textContent.replace(/[^0-9.-]/g' not in app


def test_invoice_reference_typography_remains_readable_on_narrow_screens():
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")
    assert ".einvoice-fields label,.einvoice-payment label,.einvoice-notes label{font-size:12px}" in styles
    assert ".einvoice-table td,.einvoice-table input,.einvoice-table select{font-size:12px}" in styles
    assert "@media(max-width:620px){.einvoice-ribbon p,.einvoice-summary p{font-size:12px}" in styles


def test_invoice_summary_rows_keep_semantic_colors_without_filled_blocks():
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")
    assert ".einvoice-summary .invoice-total-row.danger" in styles
    assert ".einvoice-summary .invoice-total-row.success" in styles
    assert "background: transparent;" in styles


def test_invoice_desktop_uses_a_single_reference_header_and_full_width_columns():
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")

    assert 'body[data-page="invoices"] .content > .page-head' in styles
    assert "grid-template-rows: 32px 52px;" in styles
    assert 'content: "GIB UBL 2.1 TR";' in styles
    assert "gap: 27px;" in styles
