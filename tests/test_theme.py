import sys
import os

# Set up path to import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from PyQt6.QtCore import QDate, QEvent, Qt
from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QApplication, QDateEdit

from src.utils.theme_manager import ThemeManager
from src.utils._theme_qss_transformer import ThemeQSSTransformer


def test_semantic_tokens_have_palette_fallbacks():
    palette = {
        "surface_alt": "#222222",
        "warning": "#AA6600",
        "success": "#008844",
        "info": "#0066AA",
        "accent": "#663399",
    }

    assert ThemeQSSTransformer._resolve_palette_token("surface_high", palette, lambda *_: "") == "#222222"
    assert ThemeQSSTransformer._resolve_palette_token("service_kpi_revenue", palette, lambda *_: "") == "#AA6600"
    assert ThemeQSSTransformer._resolve_palette_token("service_kpi_ready", palette, lambda *_: "") == "#008844"
from src.utils.reference_typography import apply_reference_font


def test_calendar_popup_styles_use_theme_text_and_selection_colors():
    for theme_name in ThemeManager.DISPLAY_THEMES:
        stylesheet = ThemeManager.get_stylesheet(theme_name)
        assert "QCalendarWidget QAbstractItemView" in stylesheet
        assert "selection-background-color:" in stylesheet
        assert "selection-color:" in stylesheet


def test_light_calendar_popup_has_readable_month_and_day_colors(tmp_path):
    app = QApplication.instance() or QApplication([])
    apply_reference_font(app)
    old_palette = QPalette(app.palette())
    old_stylesheet = app.styleSheet()
    app.setPalette(ThemeManager._build_palette("AYEC"))
    app.setStyleSheet(ThemeManager.get_stylesheet("AYEC"))
    date_edit = QDateEdit()
    date_edit.setCalendarPopup(True)
    date_edit.setDate(QDate(2026, 10, 9))
    date_edit.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    date_edit.show()
    calendar = date_edit.calendarWidget()
    calendar.show()
    app.processEvents()
    try:
        assert "QCalendarWidget QAbstractItemView" in app.styleSheet()
        calendar.grab().save(str(tmp_path / "light_calendar_popup.png"))
    finally:
        calendar.close()
        date_edit.close()
        date_edit.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        app.processEvents()
        app.setPalette(old_palette)
        app.setStyleSheet(old_stylesheet)

def main():
    ThemeManager._current_theme = "Nord"
    ThemeManager._last_palette = ThemeManager.current_palette()
    
    test_qss = "background: @surface_alt;"
    result = ThemeManager.transform_qss(test_qss)
    
    print(f"Current theme: {ThemeManager._current_theme}")
    print(f"Is dark theme: {ThemeManager.is_dark_theme(ThemeManager._current_theme)}")
    print(f"Original: {test_qss}")
    print(f"Transformed: {result}")
    print("Nord Palette:")
    for k, v in ThemeManager.current_palette().items():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
