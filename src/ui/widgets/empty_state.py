# -*- coding: utf-8 -*-

"""
Empty State Widget
Reusable component for displaying empty states in tables and lists.
"""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QWidget

from src.utils.theme_colors import theme_qss


class EmptyState(QWidget):
    """
    Empty state widget with icon, title, message, and optional action button.

    Supports both call styles:
    - EmptyState(icon, title, message)
    - EmptyState(title, message)
    """

    action_clicked = pyqtSignal()
    DEFAULT_ICON = "📭"

    def __init__(
        self,
        icon=DEFAULT_ICON,
        title="Henüz veri yok",
        message="",
        action_text="",
        action_callback=None,
        parent=None,
    ):
        super().__init__(parent)
        self.action_callback = action_callback
        icon, title, message = self._normalize_args(icon, title, message)
        self.setup_ui(icon, title, message, action_text)

    @classmethod
    def _looks_like_icon(cls, value):
        text = str(value or "").strip()
        if not text:
            return False
        if any(ch.isspace() for ch in text):
            return False
        return len(text) <= 4

    @classmethod
    def _normalize_args(cls, icon, title, message):
        if not cls._looks_like_icon(icon):
            old_title = str(icon or "").strip()
            old_message = str(title or "").strip()
            return cls.DEFAULT_ICON, old_title or "Henüz veri yok", message or old_message
        return icon or cls.DEFAULT_ICON, title, message

    def setup_ui(self, icon, title, message, action_text):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        self._action_text = action_text

        self.panel = QFrame(self)
        self.panel.setObjectName("EmptyStatePanel")
        self.panel.setMaximumWidth(520)
        panel_layout = QVBoxLayout(self.panel)
        panel_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        panel_layout.setContentsMargins(24, 18, 24, 18)
        panel_layout.setSpacing(12)
        layout.addWidget(self.panel, 0, Qt.AlignmentFlag.AlignCenter)

        safe_icon = icon if self._looks_like_icon(icon) else self.DEFAULT_ICON
        self.lbl_icon = QLabel(safe_icon, self.panel)
        self.lbl_icon.setFont(QFont("Segoe UI Emoji", 30))
        self.lbl_icon.setFixedSize(74, 74)
        self.lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        panel_layout.addWidget(self.lbl_icon)

        self.lbl_title = QLabel(title, self.panel)
        self.lbl_title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_title.setWordWrap(True)
        panel_layout.addWidget(self.lbl_title)

        if message:
            self.lbl_message = QLabel(message, self.panel)
            self.lbl_message.setFont(QFont("Segoe UI", 10))
            self.lbl_message.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.lbl_message.setWordWrap(True)
            self.lbl_message.setMaximumWidth(360)
            panel_layout.addWidget(self.lbl_message)
        else:
            self.lbl_message = None

        if action_text:
            self.btn_action = QPushButton(action_text, self.panel)
            self.btn_action.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self.btn_action.setFixedHeight(40)
            self.btn_action.setFixedWidth(200)
            self.btn_action.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_action.setObjectName("Primary")
            self.btn_action.setToolTip(f"{action_text} - {title}")
            self.btn_action.setStatusTip(action_text)
            self.btn_action.clicked.connect(self.action_clicked.emit)
            if self.action_callback:
                self.btn_action.clicked.connect(self.action_callback)
            panel_layout.addWidget(self.btn_action, 0, Qt.AlignmentFlag.AlignCenter)
        else:
            self.btn_action = None

        self.apply_theme_styles()

    def apply_theme_styles(self):
        self.panel.setStyleSheet(
            theme_qss(
                """
                QFrame#EmptyStatePanel {
                    background-color: transparent;
                    border: none;
                }
                """
            )
        )
        self.lbl_icon.setStyleSheet(
            theme_qss(
                """
                color: @text;
                background-color: @surface;
                border: 1px solid @border;
                border-radius: 37px;
                """
            )
        )
        self.lbl_title.setStyleSheet(theme_qss("color: @text; background: transparent; border: none;"))
        if self.lbl_message is not None:
            self.lbl_message.setStyleSheet(
                theme_qss("color: @text_muted; background: transparent; border: none; line-height: 1.45;")
            )
        if self.btn_action is not None:
            self.btn_action.setStyleSheet(
                theme_qss(
                    """
                    QPushButton {
                        background: @accent;
                        color: @selection_text;
                        border: 1px solid @accent;
                        border-radius: 12px;
                        padding: 0 18px;
                    }
                    QPushButton:hover {
                        background: @accent_hover;
                        border-color: @accent_hover;
                    }
                    """
                )
            )

    def set_title(self, title):
        if hasattr(self, "lbl_title") and self.lbl_title is not None:
            self.lbl_title.setText(title)

    def set_message(self, message):
        if self.lbl_message is None:
            self.lbl_message = QLabel(message, self.panel)
            self.lbl_message.setFont(QFont("Segoe UI", 10))
            self.lbl_message.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.lbl_message.setWordWrap(True)
            self.panel.layout().insertWidget(2, self.lbl_message)
            self.apply_theme_styles()
            return
        self.lbl_message.setText(message)
