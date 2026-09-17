# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QLabel, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt
from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.design_system import DesignTokens

class ModernConfirmDialog(ModernDialog):
    def __init__(self, title, message, parent=None, confirm_text="Onayla", cancel_text="İptal", destructive=False):
        super().__init__(title, parent, width=520, height=330)
        
        lbl_msg = QLabel(message)
        lbl_msg.setWordWrap(True)
        lbl_msg.setMinimumHeight(120)
        lbl_msg.setStyleSheet(
            f"""
            QLabel {{
                background-color: #f8fafc;
                color: {DesignTokens.FOREGROUND};
                border: 1px solid #cbd5e1;
                border-radius: 12px;
                padding: 16px;
                font-size: 11pt;
            }}
            """
        )
        lbl_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.add_widget(lbl_msg)
        
        self.add_cancel_button(cancel_text)
        self.add_button(confirm_text, "destructive" if destructive else "primary", self.accept)
