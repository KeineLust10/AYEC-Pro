from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "Web_Arayuzu" / "web" / "app.js"
CSS = ROOT / "Web_Arayuzu" / "web" / "control-center.css"


def test_admin_notifications_use_supported_api_and_truthful_audit_history():
    app = APP.read_text(encoding="utf-8")
    block = app.split('else if(activeAdminTab === "notifications") {', 1)[1].split('else if(activeAdminTab === "staged-update") {', 1)[0]

    assert 'apiFetch("/api/control/send-notification"' in block
    assert 'target_tenant_id:targetTenantId' in block
    assert 'message_title:titleInput.value.trim()' in block
    assert 'message_content:bodyInput.value.trim()' in block
    assert 'popup:$("#notifyPopup").checked' in block
    assert 'row.action==="control_notification_sent"' in block
    assert 'openDialog("Duyuruyu Yayina Al"' in block
    assert 'apiFetch("/api/control/send-notification"' in block
    assert 'data-notify-audience="pilot" disabled' in block
    assert 'disabled title="Planlama API tarafinda sunulmuyor"' in block
    assert r'Merkezi Bildirim &amp; Anl\u0131k Mesaj G\u00f6nderimi' in block
    assert 'notificationHero.innerHTML=' in block
    assert r'value="Acil Sistem G\u00fcncellemesi v2.0.2: L\u00fctfen A\u00e7\u0131k Fi\u015flerinizi Kaydediniz!"' in block
    assert 'let audience="selected",notifyType="danger";' in block
    assert 'form.reset();titleInput.value="";bodyInput.value="";' in block
    assert 'admin-notify-preview-heading' in block
    assert '<svg viewBox="0 0 24 24"><path d="M3 9v6h4l5 4V5L7 9H3' in block
    assert '1920x1080 &#xD6;L&#xC7;EK' in block
    assert 'id="notifyTemplateBtn"' in block
    assert 'id="notifyLogsBtn"' in block
    assert 'notifyTemplateBtn")?.addEventListener("click"' in block
    assert 'notifyLogsBtn")?.addEventListener("click"' in block

    capture = (ROOT / "tools" / "quality" / "admin_web_offscreen_capture.py").read_text(encoding="utf-8")
    assert '"/api/admin/audit-logs?limit=100": {"logs": NOTIFICATION_LOGS}' in capture
    assert 'notificationDraftType' in capture
    assert 'notificationLatestTime' in capture
    assert 'notificationPreviewHeading' in capture


def test_admin_notifications_fill_width_and_stack_on_mobile():
    styles = CSS.read_text(encoding="utf-8")

    assert "#adminTabContent .admin-notification-layout { display: grid;" in styles
    assert "width: 100%;" in styles[styles.index("#adminTabContent .admin-notification-layout {"):styles.index("#adminTabContent .admin-notification-composer")]
    assert "@media (max-width: 1023px)" in styles
    assert "@media (max-width: 760px)" in styles
    assert "#adminTabContent .admin-notification-layout { grid-template-columns: minmax(0, 1fr); }" in styles
    assert "#adminTabContent .admin-notification-hero { display: flex; grid-column: 1 / -1;" in styles


def test_admin_notifications_formatting_toolbar_matches_reference_height():
    styles = CSS.read_text(encoding="utf-8")
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")

    assert "admin-notify-formatbar" in app
    assert "data-notify-format" in app
    assert "height: 40px; min-height: 40px; max-height: 40px;" in styles
    assert "height: 120px; min-height: 120px; margin-top: -9px;" in styles
