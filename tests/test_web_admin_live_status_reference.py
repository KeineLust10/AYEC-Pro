from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "Web_Arayuzu" / "web" / "app.js"
CSS = ROOT / "Web_Arayuzu" / "web" / "control-center.css"


def test_live_status_binds_real_sessions_and_live_actions_to_supported_workflows():
    app = APP.read_text(encoding="utf-8")
    block = app.split('if(activeAdminTab === "live-status") {', 1)[1].split('else if(activeAdminTab === "dashboard") {', 1)[0]

    assert 'apiFetch("/api/admin/live-status")' in block
    assert 'row.online' in block
    assert 'Number(row.active_users)' in block
    assert r'row.last_seen||"API VER\u0130S\u0130 YOK"' in block
    assert 'row.user_id!==null&&row.user_id!==undefined' in block
    assert 'row.ping_ms??row.dashboard_latency_ms' in block
    assert 'latencySamples.reduce((sum,item)=>sum+item.value,0)' in block
    assert 'row.ip_address||"IP bilgisi API\'de yok"' in block
    assert 'row.db_filename||"Veritaban\\u0131 bilgisi API\'de yok"' in block
    assert r'U\u00e7tan uca h\u0131z verisi yok' in block
    assert 'liveActionButton("ping"' in block
    assert 'liveActionButton("diagnostics"' in block
    assert 'liveActionButton("message"' in block
    assert 'liveActionButton("backup"' in block
    assert 'liveActionButton("audit"' in block
    assert 'adminNotificationPrefillTenant=String(row.id)' in block
    assert 'activeBackupTenant=String(row.id)' in block
    assert 'data-live-filter="online"' in block
    assert 'data-control-action="notifications"' in block
    assert 'const liveMetricIcons=[' in block
    assert 'class="admin-live-metric-icon"' in block


def test_live_status_layout_expands_and_stacks_on_mobile():
    styles = CSS.read_text(encoding="utf-8")

    assert "#adminTabContent .admin-live-page { display: grid;" in styles
    assert "@media(max-width:1279px) { #adminTabContent .admin-live-metrics { grid-template-columns: repeat(2,minmax(0,1fr)); } }" in styles
    assert "@media(max-width:639px) { #adminTabContent .admin-live-metrics { grid-template-columns: minmax(0,1fr); } }" in styles
    assert "#adminTabContent .admin-live-companies { display: grid; grid-template-columns: repeat(2" in styles
    assert "@media(max-width:650px)" in styles
    assert "#adminTabContent .admin-live-companies { grid-template-columns: minmax(0,1fr); }" in styles
    assert "#adminTabContent .admin-live-latency-row { display: grid;" in styles
    assert "#adminTabContent .admin-live-metric-icon { position: absolute; top: 32px; right: 14px;" in styles
