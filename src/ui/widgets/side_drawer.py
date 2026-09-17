# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QFrame, QGraphicsDropShadowEffect, QSizePolicy)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QSize, pyqtProperty
from src.utils.theme_colors import theme_qss
from PyQt6.QtGui import QColor

class SideDrawer(QWidget):
    def get_drawer_width(self):
        return self.width()

    def set_drawer_width(self, w):
        self.setFixedWidth(w)
        # Parent'ın sağ tarafına yapışık kalması için reposition
        if self.parentWidget():
            parent_w = self.parentWidget().width()
            self.move(parent_w - w, 0)

    drawer_width = pyqtProperty(int, get_drawer_width, set_drawer_width)

    def __init__(self, parent=None, width=400):
        # Parent MUST be a widget with a layout or geometry management
        super().__init__(parent)
        self.target_width = width
        self.setFixedWidth(0) # Start closed
        self.setStyleSheet(theme_qss("background-color: transparent;"))
        
        # Container with shadow
        self.container = QFrame(self)
        self.container.setStyleSheet(theme_qss("""
            QFrame {
                background-color: @surface;
                border-left: 1px solid @border;
            }
        """))
        
        # Shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setXOffset(-5)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 0, 0, 40))
        self.container.setGraphicsEffect(shadow)
        
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Header
        self.header = QFrame()
        self.header.setFixedHeight(60)
        self.header.setStyleSheet(theme_qss("border-bottom: 1px solid @border; background-color: @surface_alt;"))
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(20, 0, 20, 0)
        
        self.title_label = QLabel("Başlık")
        self.title_label.setStyleSheet(theme_qss("font-size: 16px; font-weight: bold; color: @text;"))
        
        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: transparent; border: none; font-size: 16px; color: @text_muted;
            }
            QPushButton:hover {
                background-color: @surface_alt; color: @danger; border-radius: 15px;
            }
        """))
        self.btn_close.clicked.connect(self.close_drawer)
        
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_close)
        
        self.layout.addWidget(self.header)
        
        # Content Area
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.content_area)
        
        # Animation
        self.anim = QPropertyAnimation(self, b"drawer_width") # Using custom property
        self.anim.setDuration(400)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def set_content(self, widget):
        # clear old
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.content_layout.addWidget(widget)

    def set_title(self, title):
        self.title_label.setText(title)

    def open_drawer(self):
        # Update height and position before opening
        if self.parentWidget():
            self.setFixedHeight(self.parentWidget().height())
            self.move(self.parentWidget().width() - self.width(), 0)
            
        self.show()
        self.raise_()
        self.anim.stop()
        self.anim.setStartValue(self.width())
        self.anim.setEndValue(self.target_width)
        self.anim.start()

    def close_drawer(self):
        self.anim.stop()
        self.anim.setStartValue(self.width())
        self.anim.setEndValue(0)
        try:
            self.anim.finished.disconnect()
        except Exception:
            pass
        self.anim.finished.connect(self.hide)
        self.anim.start()

    def resizeEvent(self, event):
        self.container.resize(self.size())
        super().resizeEvent(event)


