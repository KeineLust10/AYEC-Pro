"""Offline reference navigation glyph coverage and state rendering."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from src.ui.widgets._side_menu_constants import PAGE_ICONS
from src.ui.widgets.navigation_glyph import NavigationChevron, NavigationGlyph, PAGE_KINDS, PATHS
from src.utils.theme_colors import qc
from src.utils.theme_manager import ThemeManager


def test_all_existing_navigation_pages_have_vector_glyphs():
    assert set(PAGE_ICONS).issubset(PAGE_KINDS)
    assert set(PAGE_KINDS.values()).issubset(PATHS)


def test_glyph_preserves_metadata_and_renders_token_states():
    app = QApplication.instance() or QApplication([])
    glyph = NavigationGlyph(PAGE_ICONS[145], page_id=145, title="Brands")
    glyph.resize(22, 22)
    assert glyph.text() == PAGE_ICONS[145]
    assert glyph.accessibleName() == "Brands"
    for active, disabled, token in (
        (False, False, "text_muted"),
        (True, False, "selection_text"),
        (True, True, "border"),
    ):
        glyph.set_navigation_state(active, disabled)
        assert not glyph.grab().isNull()
        assert glyph._renderer.isValid()
        assert glyph._render_key == ("tag", qc(token).name())
    glyph.close()
    glyph.deleteLater()
    app.processEvents()


def test_disclosure_preserves_legacy_state_text():
    app = QApplication.instance() or QApplication([])
    glyph = NavigationChevron()
    glyph.resize(16, 20)
    for state, kind in ((">", "chevron_right"), ("v", "chevron_down")):
        glyph.setText(state)
        assert glyph.text() == state
        assert not glyph.grab().isNull()
        assert glyph.kind == kind
        assert glyph.active == (state == "v")
    glyph.deleteLater()
    app.processEvents()


def test_glyph_rebuilds_stroke_colors_after_theme_change():
    app = QApplication.instance() or QApplication([])
    previous = ThemeManager._current_theme
    glyph = NavigationGlyph(page_id=145)
    glyph.resize(22, 22)
    try:
        for theme in ("AYEC", "Koyu Mavi"):
            ThemeManager._activate_runtime_cache(theme)
            for active, token in ((False, "text_muted"), (True, "selection_text")):
                glyph.set_navigation_state(active)
                glyph.grab()
                assert glyph._render_key == ("tag", qc(token).name())
                assert glyph._renderer.isValid()
    finally:
        ThemeManager._activate_runtime_cache(previous)
        glyph.deleteLater()
        app.processEvents()
