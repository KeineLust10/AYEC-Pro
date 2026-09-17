from PyQt6.QtWidgets import QWidget, QCheckBox
from PyQt6.QtCore import Qt, QVariantAnimation, QEasingCurve, QRectF, QAbstractAnimation, QSize
from PyQt6.QtGui import QPainter, QColor, QPen

class AnimatedToggle(QCheckBox):
    def __init__(self, parent=None, active_color="#2563EB", handle_color="#FFFFFF", bg_color="#94A3B8"):
        super().__init__(parent)
        self._active_color = QColor(active_color)
        self._handle_color = QColor(handle_color)
        self._bg_color = QColor(bg_color)
        self._border_color = QColor("#64748B")
        self._disabled_color = QColor("#E5E7EB")
        
        # Internal position state
        self._circle_position = 3.0
        
        self.setObjectName("AnimatedToggle")
        self.setFixedSize(54, 28)
        self.setMinimumSize(34, 18)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setStyleSheet('AnimatedToggle { background: transparent; border: none; } AnimatedToggle::indicator { width: 0; height: 0; border: none; background: transparent; }')
        
        # Use VariantAnimation for robustness
        self.animation = QVariantAnimation(self)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.animation.setDuration(250)
        self.animation.valueChanged.connect(self._update_position)
        
        # Connect state change to animation
        self.stateChanged.connect(self.start_animation)

    def start_animation(self, state):
        self.animation.stop()
        diameter = max(10.0, float(self.height() - 6))
        max_x = max(3.0, float(self.width()) - diameter - 3.0)
        target = max_x if state == Qt.CheckState.Checked else 3.0
        self.animation.setStartValue(self._circle_position)
        self.animation.setEndValue(target)
        self.animation.start()

    def _update_position(self, value):
        self._circle_position = float(value)
        self.update()

    def hitButton(self, pos):
        return self.contentsRect().contains(pos)

    def sizeHint(self):
        return QSize(54, 28)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw Background
        rect = QRectF(0, 0, self.width(), self.height())
        bg = self._active_color if self.isChecked() else self._bg_color
        border = QColor("#1D4ED8") if self.isChecked() else self._border_color
        if not self.isEnabled():
            bg = self._disabled_color
            border = QColor("#94A3B8")
        p.setPen(QPen(border, 1.4))
        p.setBrush(bg)
        p.drawRoundedRect(rect, self.height() / 2, self.height() / 2)
        
        # Draw Handle
        p.setBrush(self._handle_color)
        p.setPen(QPen(QColor("#94A3B8"), 0.6))
        
        # If not animating, correct position just in case
        if self.animation.state() != QAbstractAnimation.State.Running:
            diameter = max(10.0, float(self.height() - 6))
            max_x = max(3.0, float(self.width()) - diameter - 3.0)
            target = max_x if self.isChecked() else 3.0
            self._circle_position = target
             
        diameter = max(10.0, float(self.height() - 6))
        circle_rect = QRectF(self._circle_position, 3, diameter, diameter)
        p.drawEllipse(circle_rect)

