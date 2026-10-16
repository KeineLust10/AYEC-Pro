# -*- coding: utf-8 -*-
import os
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PyQt6.QtGui import QFont, QFontDatabase, QFontInfo
from PyQt6.QtWidgets import QApplication, QLabel

from src.utils.reference_typography import apply_reference_font, load_reference_fonts
from src.utils.theme_manager import ThemeManager
from src.ui.widgets.financial_reference_controls import ReferenceTotalLabel


def test_reference_fonts_load_offline_and_preserve_point_size():
    app = QApplication.instance() or QApplication([])
    original = QFont(app.font())
    try:
        app.setFont(QFont('sans-serif', 11))
        families = apply_reference_font(app)
        assert 'Inter' in families
        assert 'JetBrains Mono' in families
        assert app.font().family() == 'Inter'
        assert app.font().pointSize() == 11
        assert QFontInfo(QFont('Inter')).family() == 'Inter'
        assert QFontInfo(QFont('JetBrains Mono')).family() == 'JetBrains Mono'
        assert load_reference_fonts() == families
        assert 'JetBrains Mono' in QFontDatabase.families()
        amount = ReferenceTotalLabel('1,234.00 TRY')
        amount.resize(240, 80)
        assert QFontInfo(amount.amount_font(amount.text(), 24)).family() == 'JetBrains Mono'
    finally:
        app.setFont(original)


def test_system_fallback_fonts_resolve_after_reference_font_registration():
    app = QApplication.instance() or QApplication([])
    apply_reference_font(app)
    windir = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts'
    for family, filename in (('Segoe UI', 'segoeui.ttf'), ('Arial', 'arial.ttf')):
        if (windir / filename).is_file():
            assert QFontInfo(QFont(family)).family() == family


def test_web_and_desktop_share_offline_font_payloads():
    root = Path(__file__).resolve().parents[1]
    web = root / 'Web_Arayuzu' / 'web'
    css = (web / 'reference-fonts.css').read_text(encoding='utf-8')
    html = (web / 'index.html').read_text(encoding='utf-8')
    assert html.index('reference-fonts.css') < html.index('styles.css')
    for filename in ('Inter-Variable.ttf', 'JetBrainsMono-Regular.ttf'):
        assert 'assets/fonts/' + filename in css
        assert (web / 'assets' / 'fonts' / filename).read_bytes() == (
            root / 'assets' / 'fonts' / filename
        ).read_bytes()
    assert 'https://' not in css


def test_reference_font_cache_reloads_ids_reused_for_another_family(monkeypatch):
    app = QApplication.instance() or QApplication([])
    from src.utils import reference_typography
    load_reference_fonts()
    mono_id = reference_typography._font_ids['JetBrainsMono-Regular.ttf']
    monkeypatch.setitem(reference_typography._font_ids, 'Inter-Variable.ttf', mono_id)
    families = load_reference_fonts()
    assert 'Inter' in families
    assert 'JetBrains Mono' in families
    inter_id = reference_typography._font_ids['Inter-Variable.ttf']
    assert inter_id != mono_id
    assert 'Inter' in QFontDatabase.applicationFontFamilies(inter_id)
    assert 'JetBrains Mono' in QFontDatabase.applicationFontFamilies(mono_id)
    assert app is QApplication.instance()


def test_global_stylesheet_uses_readable_body_font_without_icon_font_override(monkeypatch):
    app = QApplication.instance() or QApplication([])
    original_font = QFont(app.font())
    original_stylesheet = app.styleSheet()
    from src.utils import reference_typography

    monkeypatch.setattr(reference_typography, 'load_reference_fonts', lambda: ())
    try:
        app.setFont(QFont('sans-serif', 10))
        apply_reference_font(app)
        assert app.font().family() == 'Segoe UI'

        stylesheet = ThemeManager.get_stylesheet('Koyu Mavi')
        assert 'font-family: "Segoe UI";' in stylesheet
        assert 'FontAwesome' not in stylesheet
        assert 'Font Awesome' not in stylesheet

        app.setStyleSheet(stylesheet)
        label = QLabel('Readable body text')
        label.show()
        app.processEvents()
        assert QFontInfo(label.font()).family() == QFontInfo(app.font()).family()
        label.close()
    finally:
        app.setStyleSheet(original_stylesheet)
        app.setFont(original_font)


def test_apply_reference_font_skips_reapplying_same_application_font(monkeypatch):
    from src.utils import reference_typography

    class FontApp:
        def __init__(self):
            self._font = QFont("Inter")
            self.set_count = 0

        def font(self):
            return QFont(self._font)

        def setFont(self, font):
            self.set_count += 1
            self._font = QFont(font)

    app = FontApp()
    monkeypatch.setattr(reference_typography, "load_reference_fonts", lambda: ("Inter",))

    reference_typography.apply_reference_font(app)
    reference_typography.apply_reference_font(app)

    assert app.set_count == 1
