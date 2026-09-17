# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QHBoxLayout
from PyQt6.QtGui import QPainter, QPen, QColor, QAction
from PyQt6.QtCore import Qt, QPoint

class SignatureWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(300, 150)
        self.setStyleSheet("background-color: white; border: 1px solid #bdc3c7;")
        self.image = None
        self.last_point = QPoint()
        self.is_drawing = False

    def paintEvent(self, event):
        painter = QPainter(self)
        if self.image:
            painter.drawImage(QPoint(0, 0), self.image)
        else:
            painter.setPen(QColor("#95a5a6"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "İmza Atmak İçin Çizin")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_drawing = True
            self.last_point = event.pos()
            if not self.image:
                self.image = self.grab().toImage() # Arkaplanı al
                # Temiz beyaz sayfa yap
                self.image.fill(Qt.GlobalColor.white)

    def mouseMoveEvent(self, event):
        if (event.buttons() & Qt.MouseButton.LeftButton) and self.is_drawing:
            painter = QPainter(self.image)
            # Kalem ayarları
            painter.setPen(QPen(Qt.GlobalColor.black, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.drawLine(self.last_point, event.pos())
            self.last_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_drawing = False

    def clear(self):
        self.image = None
        self.update()
