# -*- coding: utf-8 -*-

"""
SVG Icon Button Widget
SVG ikonlu buton widget'ı
"""
from PyQt6.QtWidgets import QPushButton, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QByteArray
from PyQt6.QtGui import QIcon, QPainter, QColor, QPixmap, QAction
from PyQt6.QtSvg import QSvgRenderer


class SvgIconButton(QPushButton):
    """Button with colored background and white SVG icon"""
    
    def __init__(self, svg_content, bg_color, hover_color, tooltip, parent=None):
        super().__init__(parent)
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(32, 32)
        
        # Create icon from SVG
        icon_pixmap = self.render_svg(svg_content)
        self.setIcon(QIcon(icon_pixmap))
        self.setIconSize(QSize(18, 18))
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:pressed {{
                background-color: {bg_color};
                margin-top: 1px;
            }}
        """)

    def render_svg(self, svg_content):
        """Render SVG to pixmap"""
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        renderer = QSvgRenderer(QByteArray(str(svg_content or '').encode()))
        if pixmap.isNull() or not renderer.isValid():
            return pixmap
        painter = QPainter(pixmap)
        if not painter.isActive():
            return pixmap
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        renderer.render(painter)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), Qt.GlobalColor.white)
        painter.end()
        return pixmap
