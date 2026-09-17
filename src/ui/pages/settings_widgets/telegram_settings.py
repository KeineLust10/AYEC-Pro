# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFrame
from PyQt6.QtGui import QFont

from src.utils.toast_notification import show_success
from src.utils.theme_colors import theme_qss
from src.utils.design_system import DesignTokens


class TelegramSettingsWidget(QWidget):
    """Telegram Bot Entegrasyonu Ayarları"""

    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        title = QLabel("Telegram Bot Entegrasyonu")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("color: @text;"))
        layout.addWidget(title)

        info = QLabel(
            "Bu entegrasyonu etkinleştirmek için bir Telegram botu oluşturmanız gerekir.\n"
            "1. Telegram'da @BotFather ile bir bot oluşturun.\n"
            "2. Size verilen token'i aşağıya yapıştırın.\n"
            "3. Kaydet butonuna basın ve programı yeniden başlatın."
        )
        info.setWordWrap(True)
        info.setStyleSheet(theme_qss(
            "background: @surface; color: @text_muted; padding: 14px 16px; border: 1px solid @border; border-radius: 12px;"
        ))
        layout.addWidget(info)

        card = QFrame()
        card.setStyleSheet(theme_qss("background: @surface; border: 1px solid @border; border-radius: 16px;"))
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(12)

        lbl_token = QLabel("Telegram Bot Token:")
        lbl_token.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_token.setStyleSheet(theme_qss("color: @text;"))
        card_layout.addWidget(lbl_token)

        self.inp_token = QLineEdit()
        self.inp_token.setPlaceholderText("123456789:ABCdefGHIjklMNOpqrsTUVwx_yz")
        self.inp_token.setMinimumHeight(44)
        self.inp_token.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        card_layout.addWidget(self.inp_token)

        btn_save = QPushButton("KAYDET")
        btn_save.setMinimumHeight(44)
        btn_save.setFixedWidth(200)
        btn_save.setStyleSheet(theme_qss(DesignTokens.get_button_qss("success", size="md")))
        btn_save.clicked.connect(self.save_data)
        card_layout.addWidget(btn_save)
        layout.addWidget(card)
        layout.addStretch()

    def load_data(self):
        token = self.db.get_setting("telegram_bot_token", "")
        self.inp_token.setText(token)

    def save_data(self):
        token = self.inp_token.text().strip()
        self.db.set_setting("telegram_bot_token", token)

        if self.main_window:
            self.main_window.show_notification("Telegram ayarları kaydedildi. Lütfen programı yeniden başlatın.", "success")
        else:
            show_success(self, "Kaydedildi")
