from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = ROOT / "Web_Arayuzu" / "web" / "app.js"
STYLE_SOURCE = ROOT / "Web_Arayuzu" / "web" / "control-center.css"


def test_dashboard_matches_reference_metrics_and_five_column_activity_table():
    app = APP_SOURCE.read_text(encoding="utf-8")

    assert 'activeAdminTab === "dashboard"' in app
    assert 'apiFetch("/api/admin/dashboard")' in app
    assert 'apiFetch("/api/admin/audit-logs?limit=20")' in app
    assert 'new Intl.DateTimeFormat("sv-SE"' in app
    assert 'timeZone:"UTC"' in app
    assert '<h3>Son \\u0130\\u015flemler &amp; Sistem Telemetrisi</h3>' in app
    assert 'class="control-audit-title-icon" aria-hidden="true"' in app
    assert 'class="control-kpi-badge"' in app
    assert 'class="control-kpi-progress"' in app
    assert 'dashboard.online_users??users' in app
    assert 'metric("Canl\\u0131 \\u0130stemci & Kullan\\u0131c\\u0131"' in app
    assert 'metric("Yedek Kapsam\\u0131",`${backupCoverage} / ${tenants.length} Firma`' in app
    assert 'backupPercent===100?"Tam Koruma (Bulut)":"Koruma (Bulut)"' in app
    assert 'metric("Bekleyen Komut",pendingCommands' in app
    assert 'const metricIcons=[' in app
    assert '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="${metricIcons[metricIndex++]' in app
    assert 'adminDashboardSamples.push({at:Date.now(),ms:Math.max(0,performance.now()-dashboardRequestStarted)})' in app
    assert 'Array.isArray(window.__adminDashboardSamples)' in app
    assert 'control-performance-chart' in app
    assert '</footer><section class="control-dashboard-panel control-performance-panel">' in app
    assert 'adminAuditTimer=window.setInterval(()=>{if(activeAdminTab==="dashboard")loadControlCenter()},30000)' in app
    assert '<th>Operat\\u00f6r</th>' in app
    assert 'colspan="5"' in app
    assert 'id="controlAuditSearch"' in app
    assert '${logItems.length} sistem kay\\u0131d\\u0131 listeleniyor (Canl\\u0131 ak\\u0131\\u015f)' in app
    assert '\\u25cf WebSocket Sync: Aktif' in app
    assert 'Audit trail ve u\\u00e7 nokta i\\u015flem log ak\\u0131\\u015f\\u0131' in app
    assert 'dashboardLatencyAverage.toFixed(1):"--"}ms' in app
    assert 'row.textContent.toLowerCase().includes(auditSearch.value.toLowerCase())' in app
    assert 'data-control-export' in app
    assert 'class="control-dashboard-icon"' in app
    assert 'class="control-dashboard-title-line"' in app
    assert 'class="control-live-version">CANLI V2.4' in app
    assert 'AYEC Pro Enterprise Da\\u011f\\u0131t\\u0131m Lisans &amp; Telemetri Hub' in app
    assert 'data-control-action="license-requests">H\\u0131zl\\u0131 Lisans A\\u00e7' in app
    assert 'data-control-action="backup-restore">' in app
    assert 'data-control-action="notifications">' in app
    assert 'data-control-action="server-settings">' in app
    assert '$$(`[data-control-action]`).forEach(button=>button.addEventListener("click",()=>{activeAdminTab=button.dataset.controlAction;loadControlCenter()}))' in app


def test_dashboard_activity_table_scrolls_without_forcing_mobile_page_width():
    styles = STYLE_SOURCE.read_text(encoding="utf-8")

    assert ".control-kpi-primary .control-kpi-value .control-kpi-badge" in styles
    assert ".control-audit-table-wrap { width: 100%; overflow-x: auto;" in styles
    assert ".control-audit-table { width: 100%; min-width: 690px;" in styles
    assert "#adminTabContent .control-audit-table { min-width: 0; table-layout: fixed; }" in styles
    assert "#adminTabContent .control-audit-table { min-width: 690px; }" in styles
    assert ".control-audit-status.pending" in styles
    assert ".control-audit-status.error" in styles
    assert ".control-kpi-primary .control-kpi { min-height: 108px; }" in styles
    assert ".control-kpi-secondary .control-kpi { min-height: 106px; }" in styles
    assert "@media (max-width: 639px) {\n  .control-kpi-primary,\n  .control-kpi-secondary { grid-template-columns: minmax(0, 1fr); }" in styles
    assert ".control-kpi .control-kpi-heading svg" in styles
    assert ".control-performance-line { fill: none; stroke: #538dff;" in styles
    assert ".control-audit-panel .control-performance-panel {" in styles
    assert "background: rgba(37, 42, 57, .4);" in styles
    assert "border-radius: 8px;" in styles
    assert ".control-dashboard-panel h3 { margin: 0; color: #dee2f6; font-size: 18px; }" in styles


def test_dashboard_mobile_matches_reference_kpi_and_activity_columns():
    styles = STYLE_SOURCE.read_text(encoding="utf-8")

    assert "#adminTabContent .control-kpi-grid { width: calc(100% - 8px); margin-left: 8px; }" in styles
    assert "#adminTabContent .control-kpi-primary { grid-auto-rows: 108px; gap: 12px; }" in styles
    assert "#adminTabContent .control-kpi-secondary { grid-template-rows: 92px 106px repeat(3, 92px); gap: 12px; }" in styles
    assert "#adminTabContent .control-kpi-secondary .control-kpi:nth-child(2) { height: 106px; min-height: 106px; }" in styles
    assert "#adminTabContent .control-audit-table-wrap { height: 358px; }" in styles
    assert "#adminTabContent .control-audit-table tr > :nth-child(4)" in styles
    assert "#adminTabContent .control-audit-table tr > :nth-child(5) { display: none; }" in styles
    assert "#adminTabContent .control-audit-table th:nth-child(1) { width: 27%; }" in styles
    assert "#adminTabContent .control-audit-table th:nth-child(2) { width: 35%; }" in styles
    assert "#adminTabContent .control-audit-table th:nth-child(3) { width: 38%; }" in styles
    assert ".control-audit-title-icon svg" in styles
    assert ".control-performance-chart { display: block; width: 100%; height: 64px; overflow: visible; }" in styles


def test_admin_topbar_keeps_the_reference_breadcrumb_visible_on_desktop():
    styles = STYLE_SOURCE.read_text(encoding="utf-8")
    app = APP_SOURCE.read_text(encoding="utf-8")

    assert 'body[data-page="control-center"] .topbar {\n  height: 56px;' in styles
    assert 'body[data-page="control-center"] .topbar > div:first-of-type { display: block;' in styles
    assert 'body[data-page="control-center"] .topbar #breadcrumb {\n  display: flex !important;' in styles
    assert '  white-space: nowrap;\n' in styles
    assert '  text-overflow: ellipsis;\n' not in styles[styles.index('body[data-page="control-center"] .topbar #breadcrumb {'):styles.index('body[data-page="control-center"] .topbar #pageTitle')]
    assert 'body[data-page="control-center"] .admin-tabs { display: none !important; }' in styles
    assert 'class="admin-breadcrumb-tab"' in app
    assert 'activeAdminTab=event.currentTarget.value;loadControlCenter()' in app
    assert 'body[data-page="control-center"] .app-shell > .topbar > div:first-of-type::before { content: none !important;' in styles
    assert 'body[data-page="control-center"] .topbar #pageTitle { display: none; }' in styles
    assert '.admin-system-metrics { display: flex; flex: 0 0 auto;' in styles
    assert 'body[data-page="control-center"] .admin-header-user > span:last-child { display: none; }' in styles
    assert 'headerUser.setAttribute("aria-label",`${userName} (${userRole})`);' in app
    assert "body[data-page=\"control-center\"] .topbar .admin-header-user { flex: 0 0 32px;" in styles


def test_admin_reference_breadcrumb_uses_shared_reference_labels():
    styles = STYLE_SOURCE.read_text(encoding="utf-8")
    app = APP_SOURCE.read_text(encoding="utf-8")

    assert 'const consoleTabs=["backup-restore","quota-limits","server-settings","staged-update"];' in app
    assert '<span class="admin-breadcrumb-segment">KONSOL</span>' in app
    assert '<span>Y\\u00d6NET\\u0130M</span>' in app
    assert '<span>Canl\\u0131</span><span>\\u0130zleme</span>' in app
    assert 'flex: 0 0 138px; width: 138px; min-width: 138px;' in styles


def test_admin_mobile_topbar_keeps_reference_breadcrumb_segments_and_search():
    styles = STYLE_SOURCE.read_text(encoding="utf-8")

    assert "flex: 0 0 160px; width: 160px; min-width: 160px;" in styles
    assert "#breadcrumb .admin-breadcrumb-segment,\n  body[data-page=\"control-center\"] .topbar #breadcrumb > span[aria-hidden=\"true\"] { display: inline-block !important; }" in styles
    assert "#breadcrumb .admin-breadcrumb-current { max-width: 82px; overflow: visible; white-space: normal; }" in styles

