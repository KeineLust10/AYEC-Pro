from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_google_drive_disconnect_uses_shared_confirmation_dialog():
    source = (ROOT / "Web_Arayuzu" / "web" / "backup-reference.js").read_text(encoding="utf-8")
    start = source.index("async function disconnectGoogleDrive()")
    end = source.index("function formatBackupSize", start)
    block = source[start:end]

    assert "window.confirm" not in block
    assert 'openDialog("Google Drive Ba\\u011flant\\u0131s\\u0131n\\u0131 Kald\\u0131r", "YEDEKLEME"' in block
    assert '"Ba\\u011flant\\u0131y\\u0131 Kald\\u0131r"' in block
    assert 'textContent = "Hay\\u0131r"' in block
    assert '"/api/desktop/backups/google-drive/disconnect"' in block


def test_company_wipe_requires_admin_typed_phrase_and_password():
    source = (ROOT / "Web_Arayuzu" / "web" / "backup-reference.js").read_text(encoding="utf-8")
    assert 'data-backup-wipe' in source
    assert 'userAdminRole(currentAuthUser?.role)' in source
    assert 'openDialog(' in source[source.index("function openTenantWipeDialog()"):]
    assert 'name="phrase"' in source
    assert 'name="password" type="password"' in source
    assert '"/api/admin/wipe-user-data"' in source
    assert 'await hydrateDesktop();' in source
    assert 'await loadTenantBackups();' in source


def test_wipe_all_discloses_retention_and_stale_device_sync_behavior():
    source = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")

    assert r"Bu i\u015flem tenant\u0131n sunucu verilerini" in source
    assert r"Silme \u00f6ncesi yedek 30 g\u00fcn korunur." in source
    assert r"Eski cihazlardan verilerin geri yaz\u0131lmas\u0131 engellenir; yeniden senkronizasyon gerekir." in source
    assert r"30 g\u00fcn korunan yedek #${result.backup_id}" in source
