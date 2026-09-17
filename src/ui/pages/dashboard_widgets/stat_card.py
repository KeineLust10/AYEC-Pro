# -*- coding: utf-8 -*-


"""
Stat Card Widget
İstatistik kartı widget'ı
"""
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QByteArray
from PyQt6.QtGui import QColor, QPixmap, QPainter
from PyQt6.QtSvg import QSvgRenderer
from src.utils.theme_colors import tc, theme_qss


class StatCard(QFrame):
    """İstatistik kartı widget'ı"""
    
    def __init__(self, title, value, icon_svg, color, callback=None, parent=None):
        super().__init__(parent)
        self.callback = callback
        self._color_raw = color
        self._icon_svg = icon_svg
        self._is_svg = "<svg" in str(icon_svg).lower()
        self.setFixedHeight(95)

        if self.callback:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Shadow Effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 10))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(15)

        # Left Side: Icon in Circle
        self.icon_container = QLabel()
        self.icon_container.setFixedSize(46, 46)
        self.icon_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon_container)

        # Right Side: Text Info
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.val_lbl = QLabel(str(value))
        text_layout.addWidget(self.val_lbl)

        self.title_lbl = QLabel(title)
        text_layout.addWidget(self.title_lbl)

        layout.addLayout(text_layout)
        layout.addStretch()

        self.apply_theme_styles()

    def apply_theme_styles(self):
        color = self._color_raw
        hex_color = tc(color) if not color.startswith("#") else color

        self.setStyleSheet(theme_qss(f"""
            QFrame {{
                background-color: @surface;
                border-radius: 16px;
                border: 1px solid @border;
            }}
            QFrame:hover {{
                border: 1px solid {hex_color};
                background-color: @surface_alt;
            }}
        """))

        if self._is_svg:
            self.icon_container.setStyleSheet(theme_qss(f"background-color: {hex_color}15; border-radius: 23px;"))
            icon_pixmap = self.render_colored_svg(self._icon_svg, hex_color, size=24)
            self.icon_container.setPixmap(icon_pixmap)
        else:
            self.icon_container.setText(str(self._icon_svg))
            self.icon_container.setStyleSheet(theme_qss(f"background-color: {hex_color}15; border-radius: 23px; color: {hex_color}; font-size: 22px;"))

        self.val_lbl.setStyleSheet(theme_qss(
            "color: @text; font-size: 26px; font-weight: 800; "
            "font-family: 'Inter', 'Segoe UI'; border:none; background:transparent;"
        ))
        self.title_lbl.setStyleSheet(theme_qss(
            "color: @text_muted; font-size: 12px; font-weight: 500; "
            "font-family: 'Segoe UI'; border:none; background:transparent;"
        ))

    def render_colored_svg(self, svg_content, color_hex, size=24):
        """Render SVG with specific color"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        renderer = QSvgRenderer(QByteArray(str(svg_content or '').encode()))
        if pixmap.isNull() or not renderer.isValid():
            return pixmap
        painter = QPainter(pixmap)
        if not painter.isActive():
            return pixmap
        renderer.render(painter)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), QColor(color_hex))
        painter.end()
        return pixmap

    def mousePressEvent(self, event):
        """Handle click event"""
        if self.callback:
            self.callback()
        super().mousePressEvent(event)
