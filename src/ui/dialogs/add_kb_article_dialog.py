# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QTextEdit, QPushButton, QFormLayout)
from src.utils.toast_notification import show_success, show_error, show_warning, show_info
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QAction
from src.utils.theme_colors import theme_qss
from src.utils.design_system import DesignTokens
from src.ui.widgets.modern_dialog import ModernDialog

class AddKBArticleDialog(ModernDialog):
    def __init__(self, parent=None):
        super().__init__(title="Yeni Cozum Ekle", parent=parent, width=500, height=500)
        self.set_footer_visible(False)
        self.setup_ui()

    def setup_ui(self):
        self.setStyleSheet(theme_qss("""
            QDialog { background: @surface; color: @text; }
            QLabel { color: @text; }
            QLineEdit, QTextEdit {
                background: @surface_alt;
                color: @text;
                border: 1px solid @border;
                border-radius: 8px;
                padding: 8px;
            }
        """))
        layout = self.content_layout
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_lbl = QLabel("Yeni Bilgi Bankası Makalesi")
        title_lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        layout.addWidget(title_lbl)

        form = QFormLayout()
        self.inp_title = QLineEdit()
        self.inp_title.setPlaceholderText("Makale başlığını giriniz...")
        form.addRow("Başlık*:", self.inp_title)

        self.inp_tags = QLineEdit()
        self.inp_tags.setPlaceholderText("anahtar, kelimeler, virgülle, ayırın")
        form.addRow("Etiketler:", self.inp_tags)

        layout.addLayout(form)

        layout.addWidget(QLabel("Çözüm/İçerik*:"))
        self.txt_content = QTextEdit()
        layout.addWidget(self.txt_content)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("KAYDET")
        self.btn_save.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary")))
        self.btn_save.clicked.connect(self.validate_and_accept)

        self.btn_cancel = QPushButton("İPTAL")
        self.btn_cancel.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary")))
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

    def validate_and_accept(self):
        if not self.inp_title.text().strip():
            show_warning(self, "Başlık alanı zorunludur!")
            return
        if not self.txt_content.toPlainText().strip():
            show_warning(self, "İçerik alanı zorunludur!")
            return
        self.accept()

    def get_data(self):
        return {
            "title": self.inp_title.text().strip(),
            "content": self.txt_content.toPlainText().strip(),
            "tags": self.inp_tags.text().strip()
        }

