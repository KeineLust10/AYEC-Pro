# -*- coding: utf-8 -*-
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QColor, QPainter, QLinearGradient
from PyQt6.QtWidgets import QWidget


class _ThemeRevealOverlay(QWidget):
    """Full-window soft curtain overlay for theme transitions."""

    def __init__(self, parent, curtain_color, accent_color):
        super().__init__(parent)
        self._progress = 0.0
        self._opacity = 0.0
        self._curtain_color = QColor(curtain_color)
        self._accent_color = QColor(accent_color)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setGeometry(parent.rect())

    def _get_progress(self):
        return self._progress

    def _set_progress(self, value):
        self._progress = float(value)
        self.update()

    progress = pyqtProperty(float, fget=_get_progress, fset=_set_progress)

    def _get_opacity(self):
        return self._opacity

    def _set_opacity(self, value):
        self._opacity = float(value)
        self.update()

    curtainOpacity = pyqtProperty(float, fget=_get_opacity, fset=_set_opacity)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = self.rect()

        wash = QColor(self._curtain_color)
        wash.setAlphaF(max(0.0, min(1.0, self._opacity * 0.92)))
        painter.fillRect(rect, wash)

        band_width = max(140, int(rect.width() * 0.24))
        center_x = int((rect.width() + band_width) * self._progress) - band_width
        gradient = QLinearGradient(center_x - band_width, 0, center_x + band_width, 0)
        edge = QColor(self._curtain_color)
        edge.setAlphaF(0.0)
        accent = QColor(self._accent_color)
        accent.setAlphaF(max(0.0, min(1.0, self._opacity * 0.18)))
        highlight = QColor("#FFFFFF")
        highlight.setAlphaF(max(0.0, min(1.0, self._opacity * 0.11)))
        gradient.setColorAt(0.0, edge)
        gradient.setColorAt(0.35, accent)
        gradient.setColorAt(0.5, highlight)
        gradient.setColorAt(0.65, accent)
        gradient.setColorAt(1.0, edge)
        painter.fillRect(rect, gradient)

        vignette = QLinearGradient(0, 0, 0, rect.height())
        top = QColor(self._curtain_color)
        top.setAlphaF(max(0.0, min(1.0, self._opacity * 0.18)))
        bottom = QColor(self._curtain_color)
        bottom.setAlphaF(max(0.0, min(1.0, self._opacity * 0.30)))
        vignette.setColorAt(0.0, top)
        vignette.setColorAt(1.0, bottom)
        painter.fillRect(rect, vignette)
        painter.end()

