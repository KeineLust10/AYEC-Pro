from types import SimpleNamespace

from PyQt6.QtWidgets import QApplication

from src.ui.pages.authorization_groups_widget import AddAuthGroupDialog
from src.utils.theme_manager import ThemeManager


def test_authorization_group_dialog_theme_refresh_and_footer():
    app = QApplication.instance() or QApplication([])
    previous = ThemeManager._current_theme
    try:
        dialog = AddAuthGroupDialog(SimpleNamespace())
        assert dialog.footer_layout.count() == 2
        assert not dialog.footer.isHidden()
        checkbox = dialog.permissions["dashboard"]
        ThemeManager._activate_runtime_cache("AYEC")
        dialog.apply_theme_styles()
        light_text = ThemeManager.get_palette_color("AYEC", "text")
        assert light_text.lower() in checkbox.styleSheet().lower()
        ThemeManager._activate_runtime_cache("Koyu Mavi")
        dialog.apply_theme_styles()
        dark_text = ThemeManager.get_palette_color("Koyu Mavi", "text")
        assert dark_text.lower() in checkbox.styleSheet().lower()
    finally:
        ThemeManager._current_theme = previous
        app.processEvents()
