from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_system_identity_reference_preserves_desktop_setting_keys():
    source = (ROOT / "Web_Arayuzu/web/settings-theme-reference.js").read_text(encoding="utf-8")
    for key in (
        "current_sector",
        "device_business_profiles",
        '"operations"',
        '"finance"',
        '"stock"',
        '"projects"',
        '"crm"',
        '"personnel"',
        '"asistan"',
        '"wizard_upload"',
        '"iban_verify"',
        '"voice_alerts"',
        '"scheduled_alerts"',
        '"usage_guides"',
    ):
        assert key in source
    assert '`${prefix}_${key}_active`' in source
    assert '/api/desktop/system-info' in source
    assert 'data-identity-startup' in source
    assert 'launch_on_startup' not in source
    assert 'field.type === "checkbox" ? (field.checked ? "1" : "0") : field.value' in source
    assert 'apiFetch(`/api/desktop/table/${item.scope}`' in source


def test_system_identity_save_action_does_not_cover_form_controls():
    styles = (ROOT / "Web_Arayuzu/web/styles.css").read_text(encoding="utf-8")
    assert 'body[data-settings-section="identity"] .identity-reference{gap:8px;padding-bottom:76px}' in styles
    assert 'body[data-settings-section="identity"] .page-head .actions{display:flex!important' in styles


def test_system_identity_endpoint_is_authenticated_and_uses_active_tenant_database():
    source = (ROOT / "Web_Arayuzu/Main.py").read_text(encoding="utf-8")
    start = source.index('if path == "/api/desktop/system-info":')
    end = source.index('if path == "/api/desktop/exchange-rates":', start)
    endpoint = source[start:end]
    assert 'if not self.current_user()' in endpoint
    assert 'database = Path(active_db_path())' in endpoint
    assert 'with closing(db_connect()) as conn:' in endpoint
    assert '"accounting_stock": 0' in endpoint


def test_system_identity_mobile_rules_keep_forms_full_width():
    styles = (ROOT / "Web_Arayuzu/web/desktop-parity.css").read_text(encoding="utf-8")
    assert 'body[data-page="settings"] .identity-option-grid {\n    grid-template-columns: minmax(0, 1fr);' in styles
    assert 'body[data-page="settings"] .identity-system-info > div {\n    overflow-wrap: anywhere;' in styles


def test_security_settings_reference_uses_authenticated_password_api():
    script = (ROOT / "Web_Arayuzu/web/settings-theme-reference.js").read_text(encoding="utf-8")
    server = (ROOT / "Web_Arayuzu/Main.py").read_text(encoding="utf-8")
    assert '"security", "license"].includes(settingsSection)' in script
    assert 'apiFetch("/api/desktop/security-settings"' in script
    assert 'path == "/api/desktop/security-settings"' in server
    assert 'hash_password(admin_password)' in server
    assert 'security_answer_hash' in server
    assert 'role_is_admin(user.get("role"))' in server


def test_license_reference_uses_tenant_scoped_central_catalog():
    script = (ROOT / "Web_Arayuzu/web/settings-theme-reference.js").read_text(encoding="utf-8")
    app = (ROOT / "Web_Arayuzu/web/app.js").read_text(encoding="utf-8")
    css = (ROOT / "Web_Arayuzu/web/desktop-parity.css").read_text(encoding="utf-8")
    assert 'apiFetch("/api/license/status")' in script
    assert 'apiFetch("/api/license/orders"' in script
    assert 'apiFetch(`/api/license/orders/${Number(order.id)}/payment-reported`' in script
    assert 'licenseClientHardwareId()' in script
    assert 'license-plan-grid { display: grid; grid-template-columns: repeat(2,minmax(0,1fr));' in css
    assert 'function licenseClientHardwareId()' in app
