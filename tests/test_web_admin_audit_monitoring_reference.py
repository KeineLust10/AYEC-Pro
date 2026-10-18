from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = ROOT / "Web_Arayuzu" / "web" / "app.js"
STYLE_SOURCE = ROOT / "Web_Arayuzu" / "web" / "control-center.css"


def test_audit_monitoring_tab_reads_support_audit_and_binds_all_filters():
    app = APP_SOURCE.read_text(encoding="utf-8")

    assert 'data-admin-tab="audit"' in app
    assert 'activeAdminTab === "audit"' in app
    assert 'apiFetch("/api/admin/audit-logs?limit=200")' in app
    assert 'data-audit-category' in app
    assert 'id="auditCompanyFilter"' in app
    assert 'id="auditRiskFilter"' in app
    assert 'id="auditSearch"' in app
    assert 'crypto.subtle.digest("SHA-256",bytes)' in app
    assert 'data-audit-integrity' in app
    assert 'class="audit-data-object" aria-label="Olay verisi"><svg viewBox="0 0 24 24"' in app
    assert '>data_object</button>' not in app
    assert 'id="auditSelectedId" class="audit-selected-badge"' in app
    assert 'class="audit-inspector-subtitle">\\u0130mzal\\u0131 adli bili\\u015fim kayd\\u0131 ve kriptografik i\\u015flem verisi' in app
    assert 'mismatches?`Hash zincirinde' in app
    assert 'row.risk_level||row.severity||detail.risk_level||detail.severity' in app
    assert 'className="audit-metric-head"' in app
    assert 'className="audit-metric-value"' in app
    assert 'body[data-page="control-center"] .audit-data-object svg { width: 16px;' in (ROOT / "Web_Arayuzu" / "web" / "control-center.css").read_text(encoding="utf-8")
    assert 'body[data-page="control-center"] .audit-selected-badge {' in (ROOT / "Web_Arayuzu" / "web" / "control-center.css").read_text(encoding="utf-8")
    assert 'Son ${logs.length.toLocaleString("tr-TR")} olay listeleniyor' in app
    assert 'password_reset|restore|cancel|revoke|delete|permission' not in app
    assert 'adminAuditTimer=window.setInterval' in app
    capture = (ROOT / "tools" / "quality" / "admin_audit_dom_capture.cjs").read_text(encoding="utf-8")
    assert 'selectOption("dashboard")' in capture
    assert 'selectOption("audit")' in capture
    assert "geometry.viewport !== geometry.document" in capture
    assert "geometry.metricsColumns.trim().split(/\\s+/).length !== 2" in capture
    assert 'integrityWarningShown' in capture


def test_audit_monitoring_workspace_stacks_and_keeps_event_stream_usable_on_mobile():
    styles = STYLE_SOURCE.read_text(encoding="utf-8")

    assert ".audit-workspace { display: grid; grid-template-columns: minmax(0, 7fr) minmax(300px, 5fr);" in styles
    assert ".audit-category-tabs { display: flex;" in styles
    assert ".audit-compliance-badges button { display: inline-flex;" in styles
    assert ".audit-event-list { display: grid;" in styles
    assert ".audit-detail-json { max-height: 240px;" in styles
    assert ".audit-workspace { grid-template-columns: minmax(0, 1fr); }" in styles
    assert ".audit-metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }" in styles
    assert "body[data-page=\"control-center\"] .audit-metrics { grid-template-columns: minmax(0, 1fr);" in styles
    assert 'body[data-page="control-center"] .audit-page-title-row { display: grid; grid-template-columns: minmax(0,132px) minmax(0,1fr);' in styles
    assert 'body[data-page="control-center"] .audit-compliance-tags span:first-child { min-height: 48px; margin-top: 12px;' in styles

