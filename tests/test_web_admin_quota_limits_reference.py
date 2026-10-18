from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "Web_Arayuzu/web/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "Web_Arayuzu/web/control-center.css").read_text(encoding="utf-8")


def test_admin_quota_screen_reads_usage_and_binds_real_tenant_values():
    assert 'data-admin-tab="quota-limits"' in APP
    assert '/api/admin/licenses/usage' in APP
    assert 'item.db_size_mb' in APP
    assert 'item.users_count' in APP
    assert 'item.devices_count' in APP
    assert 'item.services_count' in APP
    assert 'data-quota-row' in APP
    assert 'id="quotaSearch"' in APP
    assert 'Kota guncelleme API' in APP
    assert 'data-quota-upgrade=' in APP
    assert 'id="quotaPlan"' in APP
    assert 'id="quotaCsv"' in APP
    assert 'id="quotaXlsx"' in APP
    assert 'packageFilter.addEventListener("change",applyFilter)' in APP
    assert 'const quotaIcons=[' in APP
    assert 'className="admin-quota-metric-icon"' in APP
    assert 'quotaCount.id="quotaCount"' in APP
    assert 'quotaCount.setAttribute("aria-live","polite")' in APP


def test_admin_quota_screen_has_fluid_desktop_and_mobile_layout():
    assert '#adminTabContent .admin-quota-page' in CSS
    assert '#adminTabContent .admin-quota-metrics { display: grid; grid-template-columns: repeat(4,minmax(0,1fr))' in CSS
    assert '@media(max-width:1279px) { #adminTabContent .admin-quota-metrics { grid-template-columns: repeat(2,minmax(0,1fr)); } }' in CSS
    assert '@media(max-width:767px) { #adminTabContent .admin-quota-metrics { grid-template-columns: minmax(0,1fr); } }' in CSS
    assert '#adminTabContent .admin-quota-table-wrap table { min-width: 900px; }' in CSS
    assert '#adminTabContent .admin-quota-policy > div { grid-template-columns: minmax(0,1fr); }' in CSS
    assert '#adminTabContent .admin-quota-policy input[type="checkbox"] { position: relative; flex: 0 0 40px; appearance: none;' in CSS
    assert '#adminTabContent .admin-quota-policy input[type="checkbox"]:checked::before { transform: translateX(18px);' in CSS
    assert '#adminTabContent .admin-quota-metric-icon { position: absolute; top: 12px; right: 12px;' in CSS


def test_admin_quota_upgrade_actions_select_the_tenant_without_claiming_a_mutation_api():
    assert "$$('[data-quota-upgrade]')" in APP
    assert 'activeQuotaUpgradeTenant=button.dataset.quotaUpgrade;quotaUpgradeTenant.value=activeQuotaUpgradeTenant' in APP
    assert 'if(usages.some(item=>String(item.tenant_id)===String(activeQuotaUpgradeTenant)))quotaUpgradeTenant.value=activeQuotaUpgradeTenant' in APP
    assert 'Kota ve fiyat degisiklikleri merkezi katalog ve lisans API\'siyle yonetilmeli.' in APP
    assert 'quotaUpgradePanel.querySelectorAll(".admin-quota-upgrade-options input").forEach(control=>control.disabled=true)' in APP
    assert 'quotaUpgradePanel.querySelectorAll(".admin-quota-upgrade-options strong").forEach(price=>price.remove())' in APP
    assert '$("#quotaPlan").addEventListener("click",event=>{event.stopImmediatePropagation();quotaUpgradeTenant.scrollIntoView({ block: "center", behavior: "smooth" })})' in APP
    assert 'Kota paketi islemi Admin API tarafinda desteklenmiyor.' not in APP


def test_admin_shell_header_compacts_between_desktop_and_mobile_widths():
    assert '@media (min-width: 761px) and (max-width: 1399px)' in CSS
    assert 'body[data-page="control-center"] .topbar #adminSystemMetrics,' in CSS
    assert 'body[data-page="control-center"] .topbar .admin-system-metrics { display: none !important; }' in CSS
