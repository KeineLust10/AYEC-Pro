from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"
DESKTOP = ROOT / "src" / "ui" / "dialogs" / "add_customer_dialog.py"


def test_customer_editor_covers_reference_fields_and_persists_schema_fields():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    desktop = DESKTOP.read_text(encoding="utf-8")
    for name in (
        "company_name", "tc_no", "phone2", "tax_number", "tax_office",
        "term_days", "limit_amount", "commission_rate", "service_type",
        "city", "district", "neighborhood", "zip_code", "street", "address", "notes",
    ):
        assert f'name="{name}"' in app
        assert f"{name}:data.{name}" in app or f"{name}:+data.{name}" in app
    assert 'customer-editor-dialog' in app
    assert 'class="customer-type-switch" role="radiogroup"' in app
    assert 'data-customer-type-field="corporate"' in app
    assert 'data-customer-type-field="individual"' in app
    assert 'syncCustomerTypeFields(form)' in app
    assert 'name="service_type" list="customerServiceTypeOptions"' in app
    assert '["Genel","Telefon Servisi","Bilgisayar Servisi","Aksesuar / Sat\\u0131\\u015f"]' in app
    assert '["Genel", "Telefon Servisi", "Bilgisayar Servisi", "Aksesuar / Sat' + "\u0131\u015f" + '"]' in desktop
    assert "editable=True" in desktop
    index = (WEB / "index.html").read_text(encoding="utf-8")
    assert '<script src="app.js?v=' in index
    assert 'map_default_${name}_user_${username}' in app
    assert 'customerFormLocationDefaults(arguments.length===0?null:c)' in app
    assert 'name="city" list="customerCityOptions"' in app
    assert 'name="district" list="customerDistrictOptions"' in app
    assert 'name="neighborhood" list="customerNeighborhoodOptions"' in app
    assert 'name="street" list="customerStreetOptions"' in app
    assert 'district.value=city.value==="Bal\\u0131kesir"?"G\\u00f6nen":"Merkez"' in app
    assert 'id:"customerAddressCombo"' in app
    assert 'data-customer-address-value="${esc(value)}"' in app
    assert 'event.key==="ArrowDown"||event.key==="ArrowUp"' in app
    combo_styles = (WEB / "styles.css").read_text(encoding="utf-8")
    assert '.customer-address-combo[hidden]{display:none}' in combo_styles
    assert 'styles.css?v=20261016-company-location-picker-1' in index


def test_customer_editor_has_wide_desktop_and_stacked_mobile_layout():
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")
    assert '#appDialog.customer-editor-dialog{width:min(980px' in styles
    assert '.customer-editor{display:grid;grid-template-columns:repeat(2,minmax(0,1fr))' in styles
    assert '.customer-type-switch label.active' in styles
    assert '.customer-editor input[data-customer-type-field][readonly]' in styles
    assert '@media(max-width:700px){#appDialog.customer-editor-dialog' in styles
    assert '@media(max-width:420px){.customer-editor-section .form-grid{grid-template-columns:minmax(0,1fr)}' in styles
