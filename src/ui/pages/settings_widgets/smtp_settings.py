# -*- coding: utf-8 -*-

"""
SMTP Settings Widget
E-posta (SMTP) ayarlari widget'i
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QFrame, QLabel

from src.utils.theme_colors import theme_qss
from src.utils.design_system import DesignTokens


class SMTPSettingsWidget(QWidget):
    """E-posta (SMTP) Ayarlari Widget"""

    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        title = QLabel("E-Posta (SMTP)")
        title.setStyleSheet(theme_qss("font-size: 18px; font-weight: 800; color: @text;"))
        layout.addWidget(title)

        card = QFrame()
        card.setStyleSheet(theme_qss("background: @surface; border: 1px solid @border; border-radius: 16px;"))
        form = QFormLayout(card)
        form.setContentsMargins(24, 24, 24, 24)
        form.setSpacing(14)

        self.inp_smtp_server = QLineEdit(self.db.get_setting("smtp_server", "srvm07.trwww.com"))
        self.inp_smtp_port = QLineEdit(self.db.get_setting("smtp_port", "465"))
        self.inp_smtp_email = QLineEdit(self.db.get_setting("smtp_email", "info@ayecpro.com"))
        self.inp_smtp_password = QLineEdit(self.db.get_setting("smtp_password", ""))
        self.inp_smtp_password.setEchoMode(QLineEdit.EchoMode.Password)
        for field in (
            self.inp_smtp_server,
            self.inp_smtp_port,
            self.inp_smtp_email,
            self.inp_smtp_password,
        ):
            field.setMinimumHeight(42)
            field.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        form.addRow("Sunucu:", self.inp_smtp_server)
        form.addRow("Port:", self.inp_smtp_port)
        form.addRow("Email:", self.inp_smtp_email)
        form.addRow("Şifre:", self.inp_smtp_password)

        btn_save = QPushButton("Kaydet")
        btn_save.setMinimumHeight(42)
        btn_save.setFixedWidth(180)
        btn_save.setStyleSheet(theme_qss(DesignTokens.get_button_qss("success", size="md")))
        btn_save.clicked.connect(self.save)
        form.addRow(btn_save)

        layout.addWidget(card)
        layout.addStretch()

    def save(self):
        """SMTP ayarlarini kaydet"""
        self.db.set_setting("smtp_server", self.inp_smtp_server.text())
        self.db.set_setting("smtp_port", self.inp_smtp_port.text())
        self.db.set_setting("smtp_email", self.inp_smtp_email.text())
        self.db.set_setting("smtp_password", self.inp_smtp_password.text())

        if self.main_window:
            self.main_window.show_notification("SMTP ayarları kaydedildi.", "success")
