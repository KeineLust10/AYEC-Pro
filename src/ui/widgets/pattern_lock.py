
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor
from PyQt6.QtCore import Qt, QPoint


def _is_classic_appearance():
    app = QApplication.instance()
    return bool(app and str(app.property("appearanceMode") or "").lower() == "classic")

class PatternLockWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(240, 240)
        self.points = []
        self.selected_points = []
        self.is_drawing = False
        self.read_only = False
        
        self._update_points()

    def _update_points(self):
        self.points = []
        width = max(1, self.width())
        height = max(1, self.height())
        margin = max(16, min(width, height) * 0.2)
        for row in range(3):
            for col in range(3):
                x = round(margin + col * (width - 2 * margin) / 2)
                y = round(margin + row * (height - 2 * margin) / 2)
                self.points.append(QPoint(x, y))

    def resizeEvent(self, event):
        self._update_points()
        super().resizeEvent(event)

    def setReadOnly(self, state):
        self.read_only = state
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        classic = _is_classic_appearance()
        bg_color = QColor("#FFFFFF" if classic else "#0F172A")
        border_color = QColor("#B8C0CC" if classic else "#0F172A")
        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(border_color, 1) if classic else Qt.PenStyle.NoPen)
        radius = 8 if classic else 16
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), radius, radius)
        spacing = max(1, (min(self.width(), self.height()) - 2 * max(16, min(self.width(), self.height()) * 0.2)) / 2)
        halo_radius = max(5, min(18, round(spacing * 0.34)))
        core_radius = max(3, min(7, round(spacing * 0.13)))
        idle_radius = max(2, min(5, round(spacing * 0.08)))
        painter.setPen(Qt.PenStyle.NoPen)
        
        # Draw connections
        if len(self.selected_points) > 1: # Changed from > 0 to > 1
            pen = QPen(QColor("#2563EB" if classic else "#3B82F6"), max(2, round(spacing * 0.11)))
            pen.setCapStyle(Qt.PenCapStyle.RoundCap) # Changed Qt.RoundCap to Qt.PenCapStyle.RoundCap
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin) # Changed Qt.RoundJoin to Qt.PenJoinStyle.RoundJoin
            painter.setPen(pen)
            
            for i in range(len(self.selected_points) - 1):
                p1 = self.points[self.selected_points[i]]
                p2 = self.points[self.selected_points[i+1]]
                painter.drawLine(p1, p2)
            
            # Draw temporary line to mouse
            if self.is_drawing and not self.read_only and hasattr(self, 'current_mouse_pos'):
                last_point = self.points[self.selected_points[-1]]
                painter.drawLine(last_point, self.current_mouse_pos)

        painter.setPen(Qt.PenStyle.NoPen)
        # Draw Points
        for i, point in enumerate(self.points):
            is_selected = i in self.selected_points
            
            # Outer halo for selected
            if is_selected:
                halo = QColor(37, 99, 235, 38) if classic else QColor(59, 130, 246, 40)
                painter.setBrush(QBrush(halo))
                painter.drawEllipse(point, halo_radius, halo_radius)
                
                # Active core
                painter.setBrush(QBrush(QColor("#2563EB" if classic else "#3B82F6")))
                painter.drawEllipse(point, core_radius, core_radius)
            else:
                # Dimmed dot for unselected
                painter.setBrush(QBrush(QColor("#94A3B8" if classic else "#475569")))
                painter.drawEllipse(point, idle_radius, idle_radius)

    def mousePressEvent(self, event):
        if self.read_only: return
        self.is_drawing = True
        self.selected_points = []
        self.check_point(event.pos())
        self.update()

    def mouseMoveEvent(self, event):
        if self.read_only: return
        if self.is_drawing:
            self.current_mouse_pos = event.pos()
            self.check_point(event.pos())
            self.update()

    def mouseReleaseEvent(self, event):
        if self.read_only: return
        self.is_drawing = False
        self.update()

    def check_point(self, pos):
        spacing = max(1, (min(self.width(), self.height()) - 2 * max(16, min(self.width(), self.height()) * 0.2)) / 2)
        hit_radius = min(25, spacing * 0.42)
        for i, point in enumerate(self.points):
            # Use smaller hit area for precision
            if (point - pos).manhattanLength() < hit_radius:
                if i not in self.selected_points:
                    self.selected_points.append(i)
                    
    def get_pattern_string(self):
        return "-".join(map(str, self.selected_points))

    def set_pattern_string(self, pattern_str):
        if not pattern_str: 
            self.selected_points = []
            self.update()
            return
        try:
            self.selected_points = [int(x) for x in pattern_str.split("-") if x.isdigit()]
            self.update()
        except ValueError:
            self.selected_points = []
            self.update()

    def clear_pattern(self):
        self.selected_points = []
        if hasattr(self, 'current_mouse_pos'):
            delattr(self, 'current_mouse_pos')
        self.update()

    def get_pattern(self):
        return self.get_pattern_string()

    def set_pattern(self, pattern_str):
        self.set_pattern_string(pattern_str)
