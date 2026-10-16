from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_company_reference_uses_summary_and_compact_workflow_panels():
    source = (ROOT / "Web_Arayuzu/web/settings-theme-reference.js").read_text(encoding="utf-8")
    styles = (ROOT / "Web_Arayuzu/web/styles.css").read_text(encoding="utf-8")
    assert 'id="companyIdentity"' in source
    assert 'sections.slice(2)' in source
    assert 'company-reference-identity' in source
    assert 'company-reference-tabs' not in source
    assert 'companyNumbersPanel(definition)' in source
    assert 'data-company-number-copy' in source
    assert 'data-company-number-excel' in source
    assert '.company-number-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr))' in styles
    assert 'company-number-grid{grid-template-columns:minmax(0,1fr)}' in styles
    assert 'data-company-open-editor' in source
    assert 'data-company-editor-tab' in source
    assert 'data-company-editor-panel' in source
    assert 'company-settings-editor' in source and '#appDialog.company-settings-dialog{width:min(865px' in styles
    assert '"social_facebook", "social_instagram", "social_youtube"' in source
    assert 'companyProforma' not in source
    assert 'data-company-proforma-preview' not in source
    assert 'Proforma & PDF Tasar' not in source
    assert '.company-reference-tags' in styles
    assert 'companyLocationPanel(field(definition, keys))' in source
    assert 'navigator.geolocation.getCurrentPosition' in source
    assert '.company-reference-map{position:relative' in styles
    assert 'data-company-location-map' in source
    assert 'initAyecTomTomMap("ayec-server-proxy"' in source
    assert 'map.onClick(async (latitude, longitude)' in source
    assert 'apiFetch("/api/desktop/field-service/reverse-geocode"' in source
    assert 'map_default_${suffix}_user_${locationUsername}' in source
    assert 'data-company-map-current' in source
    assert '.company-reference-map.is-map-open iframe' in styles
    assert 'desktopSettings.installation_lat || userLatitude || desktopSettings.map_default_lat' in source
    assert 'desktopSettings.installation_address || (username ? desktopSettings[`map_default_address_user_${username}`]' in source
    assert 'await saveUserAddress("lat", String(point.latitude))' in source
    assert 'await saveUserAddress("lng", String(point.longitude))' in source
    assert 'apiFetch("/api/desktop/company-logo"' in source
    assert 'data-company-logo-file' in source
    assert '.company-reference-visual-card' in styles
    assert '.company-bank-table-wrap{max-height:250px;overflow:auto' in styles


def test_company_bank_panel_reads_and_writes_tenant_mappings():
    source = (ROOT / "Web_Arayuzu/web/settings-theme-reference.js").read_text(encoding="utf-8")
    backend = (ROOT / "Web_Arayuzu/Main.py").read_text(encoding="utf-8")
    assert '/api/desktop/table/product_bank_mappings?limit=1000' in source
    assert '/api/desktop/table/bank_accounts?limit=500' in source
    assert 'data-company-bank-save' in source
    assert 'default_kdv_rate: Number(row.querySelector("[data-bank-vat]").value || 20)' in source
    assert 'row.dataset.mappingId = String(saved.id)' in source
    assert '"product_bank_mappings",' in backend
    assert '"internal_settings", "product_bank_mappings"' in backend
