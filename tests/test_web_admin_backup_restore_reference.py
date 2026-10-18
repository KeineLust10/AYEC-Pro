from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "Web_Arayuzu/web/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "Web_Arayuzu/web/control-center.css").read_text(encoding="utf-8")


def test_admin_backup_restore_binds_existing_tenant_backup_contract():
    assert 'data-admin-tab="backup-restore"' in APP
    assert '/api/admin/backups/${encodeURIComponent(tenantId)}' in APP
    assert '/download/${encodeURIComponent(item.index)}' in APP
    assert 'backup_id=${encodeURIComponent(item.backup_id)}' in APP
    assert 'JSON.stringify({backup_index:item.index,backup_id:item.backup_id||0})' in APP
    assert 'data-backup-row' in APP
    assert 'item.sha256' in APP
    assert 'id="backupTenantSelect"' in APP
    assert 'id="backupSearch"' in APP
    assert 'Geri Yuklemeyi Kuyruga Al' in APP
    assert '/api/control/backups/create' in APP
    assert 'JSON.stringify({tenant_id:tenantId})' in APP
    assert 'Admin yedek yukleme API' in APP
    assert 'backupTable.querySelectorAll("thead th")[6]?.remove()' in APP
    assert 'row.cells[6]?.remove()' in APP
    assert 'dateFilter.value="7";applyFilter()' in APP
    assert 'row.dataset.hardware' in APP
    assert 'cihaz ara...' in APP
    assert 'const backupMetricIcons=[' in APP
    assert 'className="admin-backup-metric-icon"' in APP


def test_admin_backup_restore_has_fluid_desktop_mobile_styles():
    assert '#adminTabContent .admin-backup-page' in CSS
    assert '#adminTabContent .admin-backup-metrics { display: grid; grid-template-columns: repeat(4,minmax(0,1fr))' in CSS
    assert 'border-bottom: 3px solid #4d8eff' in CSS
    assert '@media(max-width:1023px) { #adminTabContent .admin-backup-metrics { grid-template-columns: repeat(2,minmax(0,1fr)); } }' in CSS
    assert '@media (min-width: 640px) and (max-width: 1023px)' in CSS
    assert '@media(max-width:760px) { #adminTabContent .admin-backup-hero' in CSS
    assert '#adminTabContent .admin-backup-metrics { grid-template-columns: minmax(0,1fr); }' in CSS
    assert '#adminTabContent .admin-backup-table-wrap table { min-width: 1120px; }' in CSS
    assert '#adminTabContent .admin-backup-safety-body' in CSS
    assert '#adminTabContent .admin-backup-metric-icon { position: absolute; top: 13px; right: 13px;' in CSS
    assert '#adminTabContent .admin-backup-hero #backupRefresh { color: #dee2f6; border-color: #303444; background: #252a39; }' in CSS
    assert '#adminTabContent .admin-backup-hero button:last-of-type { box-sizing: border-box; flex: 0 0 206px; width: 206px; }' in CSS
