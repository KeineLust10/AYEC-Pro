from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_customer_editor_covers_reference_fields_and_persists_schema_fields():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    for name in (
        "company_name", "tc_no", "phone2", "tax_number", "tax_office",
        "term_days", "limit_amount", "commission_rate", "service_type",
        "city", "district", "neighborhood", "zip_code", "street", "address", "notes",
    ):
        assert f'name="{name}"' in app
        assert f"{name}:data.{name}" in app or f"{name}:+data.{name}" in app
    assert 'customer-editor-dialog' in app


def test_customer_editor_has_wide_desktop_and_stacked_mobile_layout():
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")
    assert '#appDialog.customer-editor-dialog{width:min(980px' in styles
    assert '.customer-editor{display:grid;grid-template-columns:repeat(2,minmax(0,1fr))' in styles
    assert '@media(max-width:700px){#appDialog.customer-editor-dialog' in styles
    assert '@media(max-width:420px){.customer-editor-section .form-grid{grid-template-columns:minmax(0,1fr)}' in styles
