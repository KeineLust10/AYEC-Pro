from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "Web_Arayuzu" / "web" / "app.js"
CSS = ROOT / "Web_Arayuzu" / "web" / "control-center.css"
CAPTURE = ROOT / "tools" / "quality" / "admin_web_offscreen_capture.py"


def test_company_360_uses_admin_customer_data_and_supported_actions():
    app = APP.read_text(encoding="utf-8")
    block = app.split('else if(activeAdminTab === "tenants") {', 1)[1].split('else if(activeAdminTab === "notifications") {', 1)[0]

    assert 'apiFetch("/api/admin/companies")' in block
    assert 'apiFetch(`/api/admin/customer-360/${encodeURIComponent(id)}`)' in block
    assert 'apiFetch("/api/control/tenant"' in block
    assert 'apiFetch("/api/control/password-reset"' in block
    assert r'disabled title="Ge\u00e7ici parola atama API taraf\u0131nda desteklenmiyor"' in block
    assert 'data-company-filter="active"' in block
    assert 'data-company-filter="inactive"' in block
    assert 'class="admin-company-list-column"><section class="admin-company-list-panel">' in block
    assert '<div id="company360List"></div><footer class="admin-company-list-footer">' in block


def test_company_360_reference_uses_fluid_split_and_mobile_stack():
    styles = CSS.read_text(encoding="utf-8")

    assert "#adminTabContent .admin-company-360 { display: grid;" in styles
    assert "grid-template-columns: minmax(300px,365px) minmax(0,1fr)" in styles
    assert "@media(max-width:760px)" in styles
    assert "#adminTabContent .admin-company-360-grid { grid-template-columns: minmax(0,1fr); }" in styles
    assert "#adminTabContent .admin-company-list-column { display: grid; align-content: start;" in styles
    assert "#adminTabContent .admin-company-list-row { display: grid; grid-template-columns: minmax(0,1fr) auto; gap: 5px 8px; width: 100%; min-height: 86px;" in styles
    assert "#adminTabContent .admin-company-info { min-height: 264px; }" in styles
    assert "#adminTabContent .admin-company-users { min-height: 216px; margin-top: 4px; }" in styles
    assert "#adminTabContent .admin-company-kpis article { display: grid; gap: 5px; min-width: 0; min-height: 97px;" in styles


def test_company_360_list_cards_bind_company_contact_and_license_data():
    app = APP.read_text(encoding="utf-8")
    block = app.split('else if(activeAdminTab === "tenants") {', 1)[1].split('else if(activeAdminTab === "notifications") {', 1)[0]

    assert 'tenant.contact_name||tenant.owner_name' in block
    assert 'tenant.phone||"-"' in block
    assert 'tenant.email||tenant.id' in block
    assert 'tenant.license_type||"Lifetime Pro"' in block
    assert 'const company360Icons=[' in block
    assert 'className="admin-company-kpi-icon"' in block


def test_company_360_offscreen_capture_has_desktop_mobile_fixture_coverage():
    capture = CAPTURE.read_text(encoding="utf-8")

    assert 'choices=("dashboard", "audit", "live-status", "license-requests", "server-settings", "notifications", "tenants", "error-telemetry", "backup-restore", "quota-limits", "staged-update", "database-query")' in capture
    assert '"/api/admin/companies": {"companies": COMPANY_PROFILES}' in capture
    assert 'company_detail_binding' in capture
    assert 'companyFieldCount' in capture
    assert '#adminTabContent .admin-company-kpi-icon { position: absolute; top: 10px; right: 10px;' in CSS.read_text(encoding="utf-8")
