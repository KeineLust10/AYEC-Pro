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
