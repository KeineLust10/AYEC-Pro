from pathlib import Path
import re

from PyQt6.QtGui import QColor, QFontDatabase

from src.utils.theme_colors import tc, theme_qss


_CUSTOMER_FONT_IDS = []
_CUSTOMER_FONTS_LOADED = False


def ensure_customer_reference_fonts():
    global _CUSTOMER_FONTS_LOADED
    if _CUSTOMER_FONTS_LOADED:
        return
    root = Path(__file__).resolve().parents[3]
    font_paths = (
        root / "assets" / "fonts" / "Inter-Variable.ttf",
        root / "assets" / "fonts" / "JetBrainsMono-Regular.ttf",
        root / "Admin_Konsol" / "assets" / "fonts" / "PlusJakartaSans-400.ttf",
        root / "Admin_Konsol" / "assets" / "fonts" / "PlusJakartaSans-600.ttf",
        root / "Admin_Konsol" / "assets" / "fonts" / "PlusJakartaSans-700.ttf",
    )
    for font_path in font_paths:
        if font_path.is_file():
            font_id = QFontDatabase.addApplicationFont(str(font_path))
            if font_id >= 0:
                _CUSTOMER_FONT_IDS.append(font_id)
    _CUSTOMER_FONTS_LOADED = True


def customer_theme_qss(widget, qss):
    raw_qss = "" if qss is None else str(qss)
    if widget.__class__.__name__ == "CustomersPage":
        ensure_customer_reference_fonts()
    raw_qss = re.sub(
        r"@(?!customer_)([A-Za-z][A-Za-z0-9_]*)",
        lambda match: "@customer_" + match.group(1),
        raw_qss,
    )
    return theme_qss(raw_qss)


def customer_theme_color(widget, key):
    return tc("customer_" + key) or tc(key)


def customer_theme_qcolor(widget, key, alpha=None):
    raw_color = str(customer_theme_color(widget, key)).strip()
    rgba_match = re.fullmatch(
        r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([0-9.]+)\s*\)",
        raw_color,
        re.IGNORECASE,
    )
    if rgba_match:
        red, green, blue = (int(rgba_match.group(index)) for index in range(1, 4))
        alpha_value = float(rgba_match.group(4))
        if alpha_value <= 1:
            alpha_value *= 255
        color = QColor(red, green, blue, round(max(0, min(255, alpha_value))))
    else:
        color = QColor(raw_color)
    if alpha is not None and color.isValid():
        color.setAlpha(int(alpha))
    return color
