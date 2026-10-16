from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CAPTURES = (
    *sorted((ROOT / "tools" / "quality").glob("admin_*_dom_capture.cjs")),
    ROOT / "tools" / "quality" / "license_requests_dom_capture.cjs",
    ROOT / "tools" / "quality" / "admin_reference_capture.cjs",
    ROOT / "tools" / "quality" / "license_requests_reference_capture.cjs",
)


def test_admin_dom_captures_use_utf8_and_system_font_fallbacks():
    for path in CAPTURES:
        source = path.read_text(encoding="utf-8")
        assert 'font-family: "Segoe UI", Arial, sans-serif' in source, path.name
        assert "characterSet" in source, path.name
        assert "Plus Jakarta Sans" not in source, path.name


def test_pyqt_web_capture_uses_utf8_system_fonts_and_normalizes_local_api_paths():
    source = (ROOT / "tools" / "quality" / "admin_web_offscreen_capture.py").read_text(encoding="utf-8")

    assert 'setDefaultTextEncoding("UTF-8")' in source
    assert "Segoe UI" in source
    assert "Arial,sans-serif" in source
    assert "url.pathname.replace" in source
    assert "[A-Za-z]:/i" in source
