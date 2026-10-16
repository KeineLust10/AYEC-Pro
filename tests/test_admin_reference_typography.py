from pathlib import Path

from PyQt6.QtGui import QRawFont


ROOT = Path(__file__).resolve().parents[1]
DESIGN_REFERENCE_ROOT = Path("C:/Users/yedek/Desktop/Y\u00f6netim Konsolu Tasar\u0131m")
FONT_ROOT = ROOT / "Web_Arayuzu" / "web" / "assets" / "fonts"


def test_admin_reference_font_files_cover_turkish_glyphs():
    for weight in (400, 500, 600, 700):
        font_path = FONT_ROOT / f"PlusJakartaSans-{weight}.ttf"
        assert font_path.is_file()
        font = QRawFont(str(font_path), 12)
        assert font.isValid()
        assert all(font.supportsCharacter(ord(character)) for character in "\u00c7\u011e\u0130\u00d6\u015e\u00dc\u00e7\u011f\u0131\u00f6\u015f\u00fc")


def test_reference_design_system_typography_is_applied_to_admin_content():
    reference_files = tuple(DESIGN_REFERENCE_ROOT.glob("*.md"))
    assert reference_files
    for path in reference_files:
        source = path.read_text(encoding="utf-8")
        assert "fontFamily: Plus Jakarta Sans" in source
        assert "fontFamily: JetBrains Mono" in source
        assert "surface-container-low: '#161b2a'" in source
        assert "surface-container: '#1a1f2e'" in source
        assert "on-surface: '#dee2f6'" in source
        assert "on-surface-variant: '#c2c6d6'" in source
        assert "outline-variant: '#424754'" in source
        assert "primary: '#adc6ff'" in source

    font_css = (ROOT / "Web_Arayuzu" / "web" / "reference-fonts.css").read_text(encoding="utf-8")
    admin_css = (ROOT / "Web_Arayuzu" / "web" / "control-center.css").read_text(encoding="utf-8")
    assert all(f"PlusJakartaSans-{weight}.ttf" in font_css for weight in (400, 500, 600, 700))
    assert 'body[data-page="control-center"] #content' in admin_css
    assert 'font-family:"Plus Jakarta Sans","Segoe UI",Arial,sans-serif' in admin_css
    for token in ("--surface: #161b2a", "--surface-2: #1a1f2e", "--text: #dee2f6", "--muted: #c2c6d6", "--line: #424754", "--primary: #adc6ff"):
        assert token in admin_css


def test_admin_offscreen_capture_pipelines_force_utf8_and_system_font_fallbacks():
    quality_root = ROOT / "tools" / "quality"
    customer_capture = (quality_root / "admin_customer_360_offscreen_capture.py").read_text(encoding="utf-8")
    notification_capture = (quality_root / "admin_notifications_offscreen_capture.py").read_text(encoding="utf-8")
    reference_capture = (quality_root / "admin_reference_offscreen_capture.py").read_text(encoding="utf-8")
    web_capture = (quality_root / "admin_web_offscreen_capture.py").read_text(encoding="utf-8")
    font_loader = (quality_root / "admin_capture_fonts.py").read_text(encoding="utf-8")

    for source in (customer_capture, notification_capture, reference_capture, web_capture):
        assert "Segoe UI" in source
        assert "Arial" in source
    assert "PYTHONIOENCODING" in customer_capture
    assert "reconfigure(encoding=\"utf-8\"" in customer_capture
    assert "reconfigure(encoding=\"utf-8\"" in notification_capture
    assert "reconfigure(encoding=\"utf-8\"" in reference_capture
    assert 'setDefaultTextEncoding("UTF-8")' in web_capture
    assert "load_system_fallback_fonts" in customer_capture
    assert 'font-family:"Plus Jakarta Sans","Segoe UI",Arial,sans-serif' in notification_capture
    assert 'font-family:"Plus Jakarta Sans","Segoe UI",Arial,sans-serif' in reference_capture
    assert "fontFallback.textContent" in web_capture
    assert "segoeui.ttf" in font_loader
    assert "arial.ttf" in font_loader
