
# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QColor
from src.utils.theme_colors import tc
from src.utils.appearance_mode import AppearanceModeManager


def is_classic_appearance(db=None):
    app = QApplication.instance()
    if app and app.property("appearanceMode") == "classic":
        return True
    try:
        if db:
            return AppearanceModeManager.is_classic(db)
    except Exception:
        pass
    return False


def with_alpha(color_value, alpha):
    color = QColor(color_value)
    if not color.isValid():
        return color_value
    color.setAlphaF(max(0.0, min(1.0, float(alpha))))
    return color.name(QColor.NameFormat.HexArgb)


def contrast_on(color_value):
    color = QColor(color_value)
    if not color.isValid():
        return tc("text")
    luminance = (0.299 * color.red()) + (0.587 * color.green()) + (0.114 * color.blue())
    return "#0F172A" if luminance > 165 else "#F8FAFC"


def hover_on(color_value):
    color = QColor(color_value)
    if not color.isValid():
        return color_value
    luminance = (0.299 * color.red()) + (0.587 * color.green()) + (0.114 * color.blue())
    return color.darker(112).name() if luminance > 120 else color.lighter(118).name()


def apply_classic_guard(*widgets, db=None):
    classic = is_classic_appearance(db=db)
    if not classic:
        return
    for widget in widgets:
        if widget is not None:
            widget.setProperty("skipThemeTransform", False)


def render_svg_icon(svg_content, color_hex, size=16):
    from src.utils.ayec_accelerator import FastIconCache
    cache_key = f"svg_{hash(svg_content)}_{color_hex}_{size}"
    cached = FastIconCache._icon_cache.get(cache_key)
    if cached is not None:
        return cached

    from PyQt6.QtSvg import QSvgRenderer
    from PyQt6.QtGui import QPainter, QPixmap, QIcon
    from PyQt6.QtCore import QByteArray, Qt
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    # Render SVG onto pixmap
    renderer = QSvgRenderer(QByteArray(str(svg_content or '').encode()))
    if not renderer.isValid():
        return QIcon()
        
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), QColor(color_hex))
    painter.end()
    icon = QIcon(pixmap)
    FastIconCache._icon_cache[cache_key] = icon
    return icon

