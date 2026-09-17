# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFrame,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

from src.utils import message_helper
from src.utils.theme_colors import theme_qss
from src.utils.design_system import DesignTokens
from src.ui.widgets.animated_toggle import AnimatedToggle


class RemoteSettingsWidget(QWidget):
    """
    Uzak Masaüstü (AYEC Pro) Ayarları Widget'i
    Sunucu IP, port ve bağlantı protokollerini yönetir.
    """

    def __init__(self, db, main_window):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.setup_ui()
        self._wire_ui_signals()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        title = QLabel("Uzak Masaüstü (AYEC Pro) Ayarları")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("color: @text; margin-bottom: 10px;"))
        layout.addWidget(title)

        conn_group = QGroupBox("Sunucu Bağlantı Bilgileri")
        conn_group.setStyleSheet(theme_qss(
            "QGroupBox { color: @text; border: 1px solid @border; border-radius: 8px; "
            "margin-top: 8px; padding-top: 12px; font-weight: bold; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 4px; color: @text; }"
        ))
        conn_layout = QGridLayout(conn_group)
        conn_layout.setSpacing(15)

        lbl_ip = QLabel("Sunucu IP:")
        lbl_ip.setStyleSheet(theme_qss("color: @text;"))
        lbl_port = QLabel("Bağlantı Portu:")
        lbl_port.setStyleSheet(theme_qss("color: @text;"))

        self.inp_server_ip = QLineEdit()
        self.inp_server_ip.setPlaceholderText("Örn: 85.117.239.60")
        self.inp_server_ip.setMinimumHeight(40)
        self.inp_server_ip.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.inp_server_port = QLineEdit()
        self.inp_server_port.setPlaceholderText("Örn: 5000")
        self.inp_server_port.setMinimumHeight(40)
        self.inp_server_port.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        conn_layout.addWidget(lbl_ip, 0, 0)
        conn_layout.addWidget(self.inp_server_ip, 0, 1)
        conn_layout.addWidget(lbl_port, 1, 0)
        conn_layout.addWidget(self.inp_server_port, 1, 1)

        layout.addWidget(conn_group)

        sec_group = QGroupBox("Güvenlik ve Protokol")
        sec_group.setStyleSheet(theme_qss(
            "QGroupBox { color: @text; border: 1px solid @border; border-radius: 8px; "
            "margin-top: 8px; padding-top: 12px; font-weight: bold; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 4px; color: @text; }"
        ))
        sec_layout = QVBoxLayout(sec_group)

        self.toggle_remote = AnimatedToggle(active_color="#27ae60")
        remote_row = QHBoxLayout()
        lbl_remote = QLabel("Uzak Bağlantı İzin Ver:")
        lbl_remote.setStyleSheet(theme_qss("color: @text;"))
        remote_row.addWidget(lbl_remote)
        remote_row.addStretch()
        remote_row.addWidget(self.toggle_remote)
        sec_layout.addLayout(remote_row)

        self.toggle_log = AnimatedToggle(active_color="#2980b9")
        log_row = QHBoxLayout()
        lbl_log = QLabel("Bağlantı İsteklerini Günlüğe Kaydet (Audit):")
        lbl_log.setStyleSheet(theme_qss("color: @text;"))
        log_row.addWidget(lbl_log)
        log_row.addStretch()
        log_row.addWidget(self.toggle_log)
        sec_layout.addLayout(log_row)

        layout.addWidget(sec_group)

        info_card = QFrame()
        info_card.setStyleSheet(theme_qss(
            "background: @surface; border: 1px solid @border; border-radius: 8px; padding: 15px;"
        ))
        ic_layout = QVBoxLayout(info_card)
        lbl_info = QLabel(
            "Not: Sunucu IP adresini değiştirdiğinizde, mobil uygulama ve diğer istemcilerin "
            "bu yeni adrese göre güncellenmesi gerekir."
        )
        lbl_info.setStyleSheet(theme_qss("color: @text_muted; font-size: 13px; font-style: italic;"))
        lbl_info.setWordWrap(True)
        ic_layout.addWidget(lbl_info)
        layout.addWidget(info_card)

        layout.addStretch()

        btn_save = QPushButton("AYARLARI KAYDET")
        btn_save.setFixedHeight(50)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet(theme_qss(DesignTokens.get_button_qss("success", size="lg")))
        btn_save.clicked.connect(self.save_data)
        layout.addWidget(btn_save)

    def _wire_ui_signals(self):
        self.toggle_remote.toggled.connect(self.save_data)
        self.toggle_log.toggled.connect(self.save_data)

    def load_data(self):
        self.inp_server_ip.setText(self.db.get_setting("remote_server_ip", "85.117.239.60"))
        self.inp_server_port.setText(self.db.get_setting("remote_server_port", "5000"))
        self.toggle_remote.setChecked(self.db.get_setting("remote_enabled", "1") == "1")
        self.toggle_log.setChecked(self.db.get_setting("remote_logging", "1") == "1")

    def save_data(self):
        self.db.set_setting("remote_server_ip", self.inp_server_ip.text())
        self.db.set_setting("remote_server_port", self.inp_server_port.text())
        self.db.set_setting("remote_enabled", "1" if self.toggle_remote.isChecked() else "0")
        self.db.set_setting("remote_logging", "1" if self.toggle_log.isChecked() else "0")

        if self.main_window:
            self.main_window.show_notification("Uzak bağlantı ayarları güncellendi.", "success")
        else:
            message_helper.show_info(self, "Başarılı", "Uzak bağlantı ayarları kaydedildi.")
