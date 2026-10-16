from PyQt6.QtWidgets import QApplication

from src.database import Database
from src.ui.pages.announcements_page import AnnouncementsPage
from src.utils.theme_manager import ThemeManager


def test_announcement_table_header_uses_theme_contrast(tmp_path):
    app = QApplication.instance() or QApplication([])
    db = Database(str(tmp_path / "announcement_theme.db"))
    previous = ThemeManager._current_theme
    try:
        page = AnnouncementsPage(db)
        page._is_classic_appearance = lambda: False
        for theme_name in ("AYEC", "Koyu Mavi"):
            ThemeManager._activate_runtime_cache(theme_name)
            page.apply_theme_styles()
            expected_bg = ThemeManager.get_palette_color(theme_name, "surface_alt")
            expected_text = ThemeManager.get_palette_color(theme_name, "text")
            style = page.table.styleSheet().lower()
            assert expected_bg.lower() in style
            assert expected_text.lower() in style
            assert "color: white" not in style
        page.close()
        page.deleteLater()
        app.processEvents()
    finally:
        ThemeManager._activate_runtime_cache(previous)
        db.close()
