from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = ROOT / "Web_Arayuzu" / "web" / "app.js"
STYLE_SOURCE = ROOT / "Web_Arayuzu" / "web" / "control-center.css"


def test_license_requests_tab_binds_admin_order_and_inventory_contracts():
    app = APP_SOURCE.read_text(encoding="utf-8")

    assert 'data-admin-tab="license-requests"' in app
    assert 'activeAdminTab === "license-requests"' in app
    assert 'apiFetch("/api/admin/license-orders")' in app
    assert 'apiFetch("/api/admin/licenses")' in app
    assert 'apiFetch("/api/control/provision-invites")' in app
    assert 'license.display_ping_ms ?? license.ping_ms ?? license.dashboard_latency_ms' in app
    assert 'online && hasPing && ping >= 50' in app
    assert 'license-telemetry ${online?(slow?"slow":"online"):"offline"}' in app
    assert 'inviteCounts.used * 100 / invites.length' in app
    assert 'data-license-decision="approve"' in app
    assert 'data-license-decision="reject"' in app
    assert 'apiFetch(`/api/admin/license-orders/${orderId}/${decision}`' in app
    assert 'openDialog(decision==="approve"?"Lisans Talebini Etkinlestir":"Lisans Talebini Reddet"' in app
    assert 'decision==="approve"?"Etkinlestir":"Reddet"' in app
    assert 'filterRows($("#licenseOrderSearch"),"[data-license-request]")' in app
    assert 'filterRows($("#licenseInventorySearch"),".license-inventory-table tbody tr")' in app
    assert 'Lisans &amp; Yetki Da\\u011f\\u0131t\\u0131m \\u0130stasyonu' in app
    assert 'data-control-action="provision-invites"' in app
    assert 'activeAdminTab="provision-invites";loadControlCenter()' in app
    assert 'data-license-push="${esc(license.tenant_id||"")}"' in app
    assert 'data-license-freeze="${esc(license.tenant_id||"")}"' in app
    assert 'data-license-detail="${esc(license.tenant_id||"")}"' in app
    assert 'apiFetch(`/api/admin/licenses/${encodeURIComponent(license.tenant_id)}`' in app
    assert 'license-remote-actions' in app


def test_license_requests_reference_layout_stacks_cards_and_controls_on_mobile():
    styles = STYLE_SOURCE.read_text(encoding="utf-8")

    assert ".license-request-grid { display: grid; grid-template-columns: repeat(2" in styles
    assert ".license-request-actions { display: grid; grid-template-columns: repeat(2" in styles
    assert "@media (max-width: 760px)" in styles
    assert ".license-request-grid { grid-template-columns: minmax(0, 1fr); }" in styles
    assert ".license-request-actions { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); width: 100%; }" in styles
    assert ".license-inventory-wrap { width: 100%; overflow-x: auto;" in styles
    assert ".license-hsm-badge { padding: 3px 8px;" in styles
    assert "border-radius: 8px; background: linear-gradient(100deg,#4d8eff,#adc6ff,#4cd7f6);" in styles
    assert ".license-request-card::before { position: absolute; top: 0; right: 0; left: 0; height: 4px; background: linear-gradient(90deg,#4edea3,#4cd7f6,#adc6ff);" in styles
    assert ".license-request-card h3 { margin: 0; color: #dee2f6; font-size: 18px;" in styles


def test_admin_shell_header_has_live_resource_metrics_on_every_admin_tab():
    app = APP_SOURCE.read_text(encoding="utf-8")
    styles = STYLE_SOURCE.read_text(encoding="utf-8")

    assert 'const serverStatusRequest=apiFetch("/api/admin/server-status").catch(()=>({}));' in app
    assert 'else if(topActions)topActions.insertBefore(serverMetrics,$("#syncNowBtn")||null);' in app
    assert 'body[data-page="control-center"] .topbar .admin-system-metrics { order: 2; }' in styles
    assert 'body[data-page="control-center"] .topbar #notificationBtn { display: none !important; }' in styles
    assert 'id="adminHeaderUser"' in app
    assert 'body[data-page="control-center"] .admin-header-user' in styles
    assert 'globalSearch.dataset.defaultPlaceholder=globalSearch.placeholder' in app
    assert 'next!=="control-center"&&globalSearch.dataset.defaultPlaceholder' in app
