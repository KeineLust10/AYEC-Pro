from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_brands_desktop_header_and_filters_follow_reference_geometry():
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")
    assert 'body[data-page="brands"] .page-head {\n    min-height: 104px;' in styles
    assert 'body[data-page="brands"] .page-head > div:first-child {\n    position: relative;\n    margin-left: 57px;\n    padding-top: 0;' in styles
    assert 'body[data-page="brands"] .brands-reference-toolbar {\n    min-height: 104px;' in styles


def test_brands_refresh_export_and_add_actions_keep_distinct_rows():
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")
    assert "grid-template-columns: 250px repeat(3, 94px);" in styles
    assert "grid-column: 2 / 5;\n    grid-row: 1;" in styles
    assert "grid-column: 1;\n    grid-row: 2;" in styles

