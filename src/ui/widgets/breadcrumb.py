# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontMetrics
from src.utils.theme_colors import theme_qss
from src.utils.design_system import DesignTokens

class Breadcrumb(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 0, 10, 0)
        self.layout.setSpacing(10)
        
        # Left side: Path items
        self.path_container = QWidget()
        self.path_layout = QHBoxLayout(self.path_container)
        self.path_layout.setContentsMargins(0, 0, 0, 0)
        self.path_layout.setSpacing(5)
        self.path_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.layout.addWidget(self.path_container)
        
        self.layout.addStretch()

        self.assistant_btn = QPushButton(" 🤖 AYEC PRO CORE")
        self.assistant_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.assistant_btn.setFixedWidth(170)
        self.assistant_btn.setFixedHeight(32)
        self.assistant_btn.setStyleSheet(theme_qss(f"""
            QPushButton {{
                background-color: @accent;
                color: @selection_text;
                border: 1px solid @accent_pressed;
                border-radius: 16px;
                font-family: 'Segoe UI';
                font-weight: bold;
                font-size: 12px;
                padding-right: 10px;
            }}
            QPushButton:hover {{
                background-color: @accent_hover;
                border-color: {DesignTokens.ACCENT};
                color: @selection_text;
            }}
        """))
        self.assistant_btn.clicked.connect(self.main_window.toggle_assistant)

        self.mute_btn = QPushButton("🔊")
        self.mute_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mute_btn.setFixedSize(32, 32)
        self.mute_btn.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @surface_alt;
                color: @text;
                border: 1px solid @border;
                border-radius: 16px;
                font-size: 16px;
                font-weight: bold;
                padding: 0px;
            }
            QPushButton:hover { 
                background-color: @border;
                border-color: @border;
            }
            QPushButton:pressed {
                background-color: @border;
                border-color: @disabled_text;
            }
        """))
        self.mute_btn.clicked.connect(self.toggle_assistant_silent_mode)
        
        # User Welcome Label (Moved here per user request)
        user_name = "Admin Kullanıcısı"
        if hasattr(self.main_window, 'current_user') and self.main_window.current_user:
             user_name = self.main_window.current_user.get('name', 'Admin Kullanıcısı')
             
        self._user_label_full = f"👋 {user_name}"
        self.user_lbl = QLabel(self._user_label_full)
        self.user_lbl.setStyleSheet(theme_qss("color: @text; font-weight: 600; font-size: 13px;"))
        
        # Add widgets in correct order
        self.layout.addWidget(self.user_lbl)
        self.layout.addWidget(self.mute_btn)
        self.layout.addWidget(self.assistant_btn)
        self.layout.setAlignment(self.user_lbl, Qt.AlignmentFlag.AlignVCenter)
        self.layout.setAlignment(self.mute_btn, Qt.AlignmentFlag.AlignVCenter)
        self.layout.setAlignment(self.assistant_btn, Qt.AlignmentFlag.AlignVCenter)
        
        # Initial State
        self.refresh_assistant_silent_mode()
        self._refresh_user_label_text()
        self.update_path([("Ana Sayfa", 40)])

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_user_label_text()

    def _refresh_user_label_text(self):
        full = getattr(self, "_user_label_full", "")
        if not full:
            return
        metrics = QFontMetrics(self.user_lbl.font())
        available = max(80, self.width() - self.assistant_btn.width() - self.mute_btn.width() - 110)
        available = min(240, available)
        self.user_lbl.setText(metrics.elidedText(full, Qt.TextElideMode.ElideRight, available))

    def refresh_assistant_silent_mode(self):
        silent = False
        try:
            silent = bool(self.main_window.is_assistant_silent_mode())
        except Exception:
            silent = False
        self.mute_btn.setText("🔇" if silent else "🔊")

    def toggle_assistant_silent_mode(self):
        silent = False
        try:
            silent = bool(self.main_window.is_assistant_silent_mode())
        except Exception:
            silent = False
        new_val = not silent
        applied = True
        try:
            applied = bool(self.main_window.set_assistant_silent_mode(new_val))
        except Exception:
            applied = False
        if not applied:
            self.refresh_assistant_silent_mode()
            return
        self.mute_btn.setText("🔇" if new_val else "🔊")

    def update_path(self, path_items):
        """
        path_items: List of tuples ("Title", page_id)
        e.g. [("Ana Sayfa", 40), ("Müşteriler", 21), ("Detay", None)]
        """
        # Clear existing path layout
        while self.path_layout.count():
            item = self.path_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        for i, (text, page_id) in enumerate(path_items):
            if i > 0:
                arrow = QLabel("›")
                arrow.setStyleSheet(theme_qss(f"color: {DesignTokens.MUTED_FOREGROUND}; font-size: 14px; font-weight: bold;"))
                self.path_layout.addWidget(arrow)
            
            btn = QPushButton(text)
            if page_id is not None and i < len(path_items) - 1:
                # Clickable ancestor
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setStyleSheet(theme_qss(f"""
                    QPushButton {{
                        border: none; 
                        color: {DesignTokens.MUTED_FOREGROUND}; 
                        font-weight: normal;
                        background: transparent;
                        text-align: left;
                    }}
                    QPushButton:hover {{
                        color: {DesignTokens.ACCENT};
                        text-decoration: underline;
                    }}
                """))
                btn.clicked.connect(lambda checked, pid=page_id: self.main_window.switch_page(pid))
            else:
                # Current page (Active)
                btn.setStyleSheet(theme_qss(f"""
                    QPushButton {{
                        border: none; 
                        color: {DesignTokens.FOREGROUND}; 
                        font-weight: bold;
                        background: transparent;
                        text-align: left;
                    }}
                """))
                
            self.path_layout.addWidget(btn)

