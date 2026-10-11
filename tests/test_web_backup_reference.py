from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "Web_Arayuzu" / "web" / "app.js"
CSS = ROOT / "Web_Arayuzu" / "web" / "midnight-reference.css"


def test_backup_page_matches_reference_structure_without_inventing_server_state():
    source = APP.read_text(encoding="utf-8")
    assert "function renderBackupPage()" in source
    assert "backup-ref-metrics" in source
    assert "backup-ref-archive" in source
    assert r"Web kullan\u0131c\u0131s\u0131 i\u00e7in ar\u015fiv listeleme u\u00e7 noktas\u0131 tan\u0131ml\u0131 de\u011fildir." in source
    assert 'backup:renderBackupPage' in source
    assert 'data-action="export-all"' in source
    assert 'data-action="restore-backup"' in source


def test_backup_page_is_responsive_and_printable():
    css = CSS.read_text(encoding="utf-8")
    assert 'body[data-page="backup"] .backup-ref-layout' in css
    assert "@media(max-width:900px){body[data-page=\"backup\"]" in css
    assert "@media(max-width:560px){body[data-page=\"backup\"]" in css
    assert "@media print{body[data-page=\"backup\"]" in css
