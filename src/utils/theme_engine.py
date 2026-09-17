from src.utils.theme_manager import ThemeManager


class ThemeEngine:
    """Compatibility facade expected by legacy imports."""

    def apply_theme(self, app, theme_name):
        ThemeManager.apply_theme(app, theme_name)

    def get_available_themes(self, db=None):
        return ThemeManager.get_available_themes(db)

    def get_stylesheet(self, theme_name):
        return ThemeManager.get_stylesheet(theme_name)


theme_engine = ThemeEngine()
