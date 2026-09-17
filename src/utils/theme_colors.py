from PyQt6.QtGui import QColor
from src.utils.theme_manager import ThemeManager
from src.utils.logger import logger
from PyQt6.QtWidgets import QApplication


def theme_qss(qss_text):
    """Keep semantic QSS tokens intact until the stylesheet hook applies them."""
    raw_qss = "" if qss_text is None else str(qss_text)
    try:
        ThemeManager._install_stylesheet_patch()
    except Exception as e:
        logger.debug("Theme stylesheet patch install skipped: %s", e)
    return raw_qss


def tc(key, theme_name=None, default=''):
    if theme_name is None:
        theme_name = ThemeManager._current_theme
    return ThemeManager.get_palette_color(theme_name, key, default)


def qc(key, default=None):
    return QColor(ThemeManager.get_palette_color(ThemeManager._current_theme, key, default or tc('text')))
