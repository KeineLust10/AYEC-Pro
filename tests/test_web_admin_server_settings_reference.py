from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "Web_Arayuzu/web/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "Web_Arayuzu/web/control-center.css").read_text(encoding="utf-8")


def test_admin_server_settings_uses_authoritative_status_api():
    assert 'data-admin-tab="server-settings"' in APP
    assert '/api/admin/server-status' in APP
    assert 'status.cpu_percent' in APP
    assert 'status.ram_percent' in APP
    assert 'status.disk_percent' in APP
    assert 'metricValue("cpu_cores")' in APP
    assert 'metricValue("ram_type")' in APP
    assert 'status.ram_used_gb' in APP
    assert 'metricValue("disk_type")' in APP
    assert 'metricValue("disk_free_gb")' in APP
    assert 'status.database_size_bytes' in APP
    assert 'status.network_mbps' in APP
    assert 'document.createTextNode(`SSL: ${metricValue("network_tls")}`)' in APP
    assert 'status.tenant_count' in APP
    assert 'status.db_path' in APP
    assert r'API anahtarlar\u0131' in APP
    assert r'Gizli de\u011ferler API yan\u0131t\u0131nda sunulmaz' in APP
    assert r'title="Sunucu konfig\u00fcrasyonu g\u00fcncelleme API' in APP
    assert r'title="Sunucu bak\u0131m komutu API' in APP


def test_admin_server_settings_is_full_width_and_mobile_responsive():
    assert '#adminTabContent .admin-server-page' in CSS
    assert '#adminTabContent .admin-server-metrics { display: grid; grid-template-columns: repeat(5,minmax(0,1fr))' in CSS
    assert '#adminTabContent .admin-server-metric { display: grid; align-content: space-between; gap: 10px; min-width: 0; min-height: 186px;' in CSS
    assert '#adminTabContent .admin-server-metric-value strong' in CSS
    assert 'database_size_bytes' in APP and 'network_mbps' in APP
    assert 'admin-server-topology' in APP and 'admin-server-replication' in APP
    assert '#adminTabContent .admin-server-hero #serverStatusRefresh { width: 217px; color: #dee2f6; border-color: #303444; background: #252a39;' in CSS
    assert '#adminTabContent .admin-server-infrastructure { grid-template-columns: 220px minmax(0,1fr); grid-template-rows: 28px minmax(0,1fr);' in CSS
    assert '#adminTabContent .admin-server-node::before { display: block; width: 44px; height: 62px;' in CSS
    assert '@media(max-width:1279px) {\n  #adminTabContent .admin-server-infrastructure { grid-template-columns: minmax(0,1fr);' in CSS
    assert '#adminTabContent .admin-server-layout { display: grid; grid-template-columns: minmax(0,1.3fr) minmax(300px,.7fr)' in CSS
    assert '@media(max-width:1279px) { #adminTabContent .admin-server-metrics { grid-template-columns: repeat(2,minmax(0,1fr)); }' in CSS
    assert '@media(max-width:767px)' in CSS and '#adminTabContent .admin-server-metrics { grid-template-columns: minmax(0,1fr); }' in CSS
    assert '#adminTabContent .admin-server-fields { grid-template-columns: minmax(0,1fr); }' in CSS
