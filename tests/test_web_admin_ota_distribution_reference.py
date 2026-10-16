from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "Web_Arayuzu" / "web" / "app.js"
CSS = ROOT / "Web_Arayuzu" / "web" / "control-center.css"


def test_ota_screen_stages_packages_and_queues_selected_targets():
    app = APP.read_text(encoding="utf-8")
    block = app.split('else if(activeAdminTab === "staged-update") {', 1)[1].split('else if(activeAdminTab === "provision-invites") {', 1)[0]

    assert 'apiFetch("/api/control/staged-update")' in block
    assert 'apiFetch("/api/admin/updates/deploy"' in block
    assert 'targets,changelog:' in block
    assert 'channel:$("#otaChannel").value' in block
    assert r'openDialog("OTA Da\u011f\u0131t\u0131m\u0131n\u0131 Kuyru\u011fa Al"' in block
    assert r'disabled title="Test u\u00e7 nokta API' in block
    assert r'disabled title="Zorunlu OTA se\u00e7ene\u011fi API taraf\u0131nda yok"' in block
    assert 'tenant.current_version||tenant.app_version||tenant.version' in block
    assert r'Kritik G\u00fcncelleme' in block
    assert r'F\u0130RMA / \u0130STASYON B\u0130LG\u0130S\u0130' in block
    assert r'MEVCUT S\u00dcR\u00dcM' in block
    assert r'Kararl\u0131 S\u00fcr\u00fcm' in block
    assert 'Da\\u011f\\u0131t\\u0131m Sunucusu' in block
    assert 'const otaMetricIcons=[' in block
    assert 'className="admin-ota-metric-icon"' in block
    assert 'stableUpdate=updates.find' in block
    assert 'pilotUpdate=updates.find' in block
    assert 'pilotSuccessRate=pilotFinishedCommands.length?Math.round(pilotSuccessful/pilotFinishedCommands.length*100):null' in block
    assert r'PILOT TEST BA\u015eARISI' in block
    assert 'class="admin-ota-status-dot stable"' in block
    assert 'class="admin-ota-status-dot pilot"' in block
    assert 'class="admin-ota-hero-icon"' in block
    assert 'class="admin-ota-hero-kicker"' in block


def test_ota_reference_layout_is_full_width_and_responsive():
    styles = CSS.read_text(encoding="utf-8")

    assert "#adminTabContent .admin-ota-page { display: grid;" in styles
    assert "#adminTabContent .admin-ota-hero { display: flex;" in styles
    assert "padding: 12px 20px 23px; background: #161b2a; box-shadow: 0 1px 2px rgba(0,0,0,.12);" in styles[styles.index("#adminTabContent .admin-ota-hero {"):styles.index("#adminTabContent .admin-ota-hero-kicker")]
    assert "#adminTabContent .admin-ota-hero-status article { display: flex; align-items: center;" in styles
    assert "#adminTabContent .admin-ota-metrics { display: grid; grid-template-columns: repeat(4" in styles
    assert "#adminTabContent .admin-ota-grid { display: grid; grid-template-columns: minmax(0,7fr) minmax(280px,5fr);" in styles
    assert "@media(max-width:1023px) { #adminTabContent .admin-ota-metrics { grid-template-columns: repeat(2,minmax(0,1fr)); }" in styles
    assert "@media(max-width:767px)" in styles
    assert "@media(max-width:430px) { #adminTabContent .admin-ota-hero { width: calc(100% + 40px); min-height: 293px; margin-left: -20px;" in styles
    assert "#adminTabContent .admin-ota-grid { grid-template-columns: minmax(0,1fr); }" in styles
    assert "#adminTabContent .admin-ota-target-row code" in styles
    assert "#adminTabContent .admin-ota-metric-icon { position: absolute; top: 13px; right: 13px;" in styles
