from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "Web_Arayuzu/web/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "Web_Arayuzu/web/control-center.css").read_text(encoding="utf-8")
CAPTURE = (ROOT / "tools/quality/admin_web_offscreen_capture.py").read_text(encoding="utf-8")


def test_sql_diagnostics_match_reference_workbench_and_controls():
    assert 'class="admin-query-page"' in APP
    assert "Salt Okunur SQL Te\\u015fhis Sorgulay\\u0131c\\u0131" in APP
    assert 'id="adminQueryTenant"' in APP
    assert 'id="adminQueryInput"' in APP
    assert 'id="adminQueryRun"' in APP
    assert 'id="adminQueryExplain"' in APP
    assert 'id="adminQueryClear"' in APP
    assert '/api/admin/companies/${encodeURIComponent(tenantId)}/query' in APP
    assert 'className="admin-query-nav"' in APP
    assert 'data-query-nav="database-query" class="active"' in APP
    assert 'apiFetch("/api/admin/server-status")' in APP
    assert 'apiFetch("/api/admin/live-status")' in APP
    assert 'data-query-download="${esc(item.index)}"' in APP
    assert 'data-query-download]' in APP
    assert 'backup_index:item.index' in APP
    assert 'const auditLogs=Array.isArray(auditResponse.logs)?auditResponse.logs.slice(0,200):[];' in APP
    assert 'data-query-audit-filter="${key}"' in APP
    assert 'queryAuditCategory=button.dataset.queryAuditFilter' in APP
    assert 'id="adminQueryAuditSearch"' in APP
    assert 'const renderQueryAudit=()=>{' in APP


def test_sql_diagnostic_layout_and_offscreen_capture_are_responsive():
    assert "#adminTabContent .admin-query-page" in CSS
    assert "@media(max-width:760px)" in CSS
    assert "#adminTabContent .admin-query-platform-status" in CSS
    assert "@media(max-width:1279px) {" in CSS
    assert "#adminTabContent .admin-query-platform-status { grid-template-columns: minmax(0,1fr); }" in CSS
    assert "#adminTabContent .admin-query-nav" in CSS
    assert "#adminTabContent .admin-query-backup-table th:nth-child(6)" in CSS
    assert "#adminTabContent .admin-query-results { min-height: 117px; }" in CSS
    assert '"database-query"' in CAPTURE
    assert 'query_workbench' in CAPTURE
    assert '#adminTabContent .admin-query-audit-filters button.active' in CSS
    assert '#adminTabContent .admin-query-audit-tools input' in CSS
    assert 'class="admin-query-audit-heading"' in APP
    assert 'G\\u00fcvenli SELECT &amp; EXPLAIN sorgular\\u0131 \\u00e7al\\u0131\\u015ft\\u0131r\\u0131r' in APP
    assert '<th>Durum</th>' in APP
    assert '<div class="admin-query-trace">' in APP
    assert 'Token verification payload' in APP
    assert '#adminTabContent .admin-query-trace-lines' in CSS
    assert '#adminTabContent .admin-query-telemetry-table th:nth-child(6)' in CSS
    assert 'checks["query_audit_filter_and_search"]' in CAPTURE
    assert 'checks["query_telemetry_reference_columns"]' in CAPTURE
    assert 'checks["query_telemetry_reference_data"]' in CAPTURE
    assert 'checks["query_telemetry_fits_content"]' in CAPTURE
    assert 'checks["query_reference_trace_console"]' in CAPTURE
    assert 'checks["query_desktop_reference_geometry"]' in CAPTURE
    assert 'queryAuditBehavior' in CAPTURE
