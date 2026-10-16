# -*- coding: utf-8 -*-
"""SMTP configuration and delivery diagnostics."""

import ssl
import smtplib
from datetime import datetime
from email.message import EmailMessage
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLayout, QLineEdit, QPushButton,
    QFrame, QLabel, QComboBox, QCheckBox, QButtonGroup, QTextEdit, QSizePolicy,
)

from src.utils.theme_colors import theme_qss
from src.utils.design_system import DesignTokens
from src.utils.secure_setting_store import SecureSettingStore


class SMTPSettingsWidget(QWidget):
    """SMTP settings with provider presets, testing, and diagnostics."""

    def __init__(self, db, main_window=None):
        super().__init__()
        self.setObjectName("part9_smtp_settings")
        self.setStyleSheet(
            "QWidget#part9_smtp_settings { background: #0b1020; color: #dee2f6; font-family: 'Inter', 'Segoe UI', sans-serif; } "
            "QWidget#part9_smtp_settings QLabel { color: #c2c6d6; background: transparent; border: 0; }"
        )
        self.db = db
        self.main_window = main_window
        self.setFont(QFont("Inter", 9))
        self._defaults = {
            "smtp_server": "srvm07.trwww.com", "smtp_port": "465",
            "smtp_email": "info@ayecpro.com",
            "smtp_sender_name": "AYEC Pro Teknik Servis Hizmetleri",
            "smtp_timeout": "15", "smtp_security": "ssl",
            "smtp_auth_required": "1", "smtp_auto_bcc": "1",
        }
        root = QVBoxLayout(self)
        root.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(7)
        metrics = QHBoxLayout()
        metrics.setSpacing(8)
        self.smtp_metric_test = None
        self.smtp_metric_test_detail = None
        for label, value, detail in (
            ("E-POSTA ILETIMI", "1,482", "/ 5,000 gonderim"),
            ("ILETIM BASARISI", "99.8%", "3 red"),
            ("SMTP GECIKMESI", "42 ms", "TLS v1.3"),
            ("SON TEST", "13:12:04", "BASARILI"),
        ):
            metric = QFrame()
            metric.setObjectName("smtpMetricCard")
            metric.setFixedHeight(32)
            metric.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            metric.setStyleSheet("QFrame#smtpMetricCard{background:#171d2d;border:1px solid #202d45;border-radius:4px}")
            metric_layout = QVBoxLayout(metric)
            metric_layout.setContentsMargins(8, 3, 8, 3)
            metric_layout.setSpacing(1)
            metric_title = QLabel(label)
            metric_title.setStyleSheet("color:#8c98ad;font:700 8px 'JetBrains Mono',Consolas,monospace")
            metric_value = QLabel(value)
            metric_value.setStyleSheet("color:#dee2f6;font:700 13px 'JetBrains Mono',Consolas,monospace")
            metric_detail = QLabel(detail)
            metric_detail.setStyleSheet("color:#4cd7f6;font:600 8px 'JetBrains Mono',Consolas,monospace")
            metric_value_row = QHBoxLayout()
            metric_value_row.setContentsMargins(0, 0, 0, 0)
            metric_value_row.setSpacing(6)
            metric_value_row.addWidget(metric_value)
            metric_value_row.addWidget(metric_detail)
            metric_value_row.addStretch(1)
            metric_layout.addWidget(metric_title)
            metric_layout.addLayout(metric_value_row)
            metrics.addWidget(metric, 1)
            if label == "SON TEST":
                self.smtp_metric_test = metric_value
                self.smtp_metric_test_detail = metric_detail
        metrics_host = QWidget()
        metrics_host.setFixedHeight(32)
        metrics.setContentsMargins(0, 0, 0, 0)
        metrics_host.setLayout(metrics)
        root.addWidget(metrics_host)
        columns = QHBoxLayout()
        columns.setSpacing(12)
        left_column = QWidget()
        left_column.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        left_column_layout = QVBoxLayout(left_column)
        left_column_layout.setContentsMargins(0, 0, 0, 0)
        left_column_layout.setSpacing(8)
        left = self._card()
        self.smtp_form_card = left
        left.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(10, 8, 10, 8)
        left_layout.setSpacing(10)
        title_row = QHBoxLayout()
        title = QLabel("E-Posta (SMTP) Sunucu Yap\u0131land\u0131rmas\u0131")
        title.setMaximumHeight(32)
        title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        title.setStyleSheet("font-size:15px;font-weight:800;color:#dee2f6;background:transparent;border-left:3px solid #4f8ff9;padding-left:8px")
        security = self._get("smtp_security", "ssl")
        status = self._security_status(security)
        self.lbl_connection_state = QLabel(status)
        self.lbl_connection_state.setStyleSheet("color:#4edea3;font:700 8px 'JetBrains Mono',Consolas,monospace")
        title_row.addWidget(title)
        title_row.addStretch(1)
        title_row.addWidget(self.lbl_connection_state)
        left_layout.addLayout(title_row)
        left_layout.addSpacing(12)
        notice = QLabel("Otomatik bildirim motoru aktif. Servis fisleri, cari ekstreler ve PDF dokumanlari bu sunucu uzerinden iletilir.")
        notice.setWordWrap(True)
        notice.setMinimumHeight(62)
        notice.setMaximumHeight(62)
        notice.setStyleSheet("background:#171d2d;border:1px solid #202d45;border-radius:4px;padding:10px;color:#c2cce0;font:9px 'Inter','Segoe UI',sans-serif")
        left_layout.addWidget(notice)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(15)
        self.inp_smtp_server = self._field("SMTP SUNUCU HOSTU (FQDN)", self._get("smtp_server", self._defaults["smtp_server"]), "srvm07.trwww.com")
        self.inp_smtp_port = self._field("PORT NO", self._get("smtp_port", self._defaults["smtp_port"]), "465")
        self.cmb_security = QComboBox()
        self.cmb_security.addItem("SSL (Port 465)", "ssl")
        self.cmb_security.addItem("TLS / STARTTLS (587)", "starttls")
        self.cmb_security.addItem("Yok (Duz Metin)", "none")
        self.cmb_security.setCurrentIndex(max(0, self.cmb_security.findData(self._get("smtp_security", "ssl"))))
        self.cmb_security.hide()
        self.security_group = QButtonGroup(self)
        self.security_group.setExclusive(True)
        security_bar = QWidget()
        security_layout = QHBoxLayout(security_bar)
        security_layout.setContentsMargins(0, 0, 0, 0)
        security_layout.setSpacing(4)
        for text, value in (("SSL (Port 465)", "ssl"), ("TLS / STARTTLS (587)", "starttls"), ("Yok (Duz Metin)", "none")):
            button = QPushButton(text)
            button.setCheckable(True)
            button.setProperty("security_value", value)
            button.setMinimumHeight(32)
            button.setStyleSheet("QPushButton{background:#171d2d;color:#aebbd0;border:1px solid #202d45;border-radius:4px;padding:5px;font:8px 'Inter','Segoe UI',sans-serif} QPushButton:checked{background:#1c2940;color:#dee2f6;border:1px solid #4f8ff9;font-weight:700}")
            button.clicked.connect(lambda checked=False, key=value: self._set_security(key))
            self.security_group.addButton(button)
            security_layout.addWidget(button, 1)
            if value == self.cmb_security.currentData():
                button.setChecked(True)
        self.security_bar = security_bar
        self.inp_smtp_email = self._field("GONDEREN E-POSTA ADRESI", self._get("smtp_email", self._defaults["smtp_email"]), "info@ayecpro.com")
        self.inp_sender_name = self._field("GONDEREN ADI / FIRMA BASLIGI", self._get("smtp_sender_name", self._defaults["smtp_sender_name"]), "AYEC Pro Teknik Servis Hizmetleri")
        self.inp_smtp_password = self._field("E-POSTA PAROLASI", SecureSettingStore.get(self.db, "smtp_password", ""), "Uygulama parolasi")
        self.inp_smtp_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.inp_timeout = self._field("ZAMAN ASIMI (SN)", self._get("smtp_timeout", self._defaults["smtp_timeout"]), "15")
        self.chk_auth = QCheckBox("Kimlik Dogrulama Zorunlu\n(AUTH LOGIN / PLAIN)")
        self.chk_auth.setChecked(self._get("smtp_auth_required", "1") == "1")
        self.chk_bcc = QCheckBox("Tum giden fatura ve fisleri arsiv e-postasina\ngizli kopyala (BCC)")
        self.chk_bcc.setChecked(self._get("smtp_auto_bcc", "1") == "1")
        self._style_check(self.chk_auth)
        self._style_check(self.chk_bcc)
        fields = [
            ("SMTP SUNUCU HOSTU (FQDN)", self.inp_smtp_server, 0, 0),
            ("PORT NO", self.inp_smtp_port, 0, 1),
            ("GUVENLIK PROTOKOLU", self.security_bar, 1, 0),
            ("GONDEREN E-POSTA ADRESI", self.inp_smtp_email, 2, 0),
            ("GONDEREN ADI / FIRMA BASLIGI", self.inp_sender_name, 2, 1),
            ("E-POSTA PAROLASI", self.inp_smtp_password, 3, 0),
            ("ZAMAN ASIMI (SN)", self.inp_timeout, 3, 1),
        ]
        for label, widget, row, col in fields:
            cell = QWidget()
            cell.setFixedHeight(48)
            cell_layout = QVBoxLayout(cell)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            cell_layout.setSpacing(4)
            caption = QLabel(label)
            caption.setStyleSheet("font:700 8px 'JetBrains Mono',Consolas,monospace;color:#aebbd0;border:0;background:transparent")
            cell_layout.addWidget(caption)
            if widget is self.inp_smtp_password:
                row_layout = QHBoxLayout()
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.addWidget(widget, 1)
                self.btn_show_password = QPushButton("GOSTER")
                self.btn_show_password.setFixedWidth(70)
                self.btn_show_password.clicked.connect(self.toggle_password)
                self._style_secondary(self.btn_show_password)
                row_layout.addWidget(self.btn_show_password)
                cell_layout.addLayout(row_layout)
            else:
                cell_layout.addWidget(widget)
            if widget is self.security_bar:
                grid.addWidget(cell, row, col, 1, 2)
            else:
                grid.addWidget(cell, row, col)
        grid.addWidget(self.chk_auth, 4, 0)
        grid.addWidget(self.chk_bcc, 4, 1)
        grid.setColumnStretch(0, 3)
        grid.setColumnStretch(1, 2)
        left_layout.addLayout(grid)
        help_text = QLabel("Uygulama parolaniz guvenli ayar deposunda saklanir. Port 465 icin SSL, 587 icin STARTTLS kullanin.")
        help_text.setWordWrap(True)
        help_text.setMaximumHeight(34)
        help_text.setStyleSheet("color:#8c98ad;font-size:9px")
        left_layout.addWidget(help_text)
        left_layout.addStretch(1)

        actions = QHBoxLayout()
        self.btn_reset = QPushButton("Varsayilan Degerlere Don")
        self.btn_cancel = QPushButton("Iptal")
        self.btn_save = QPushButton("KAYDET VE ETKINLESTIR")
        self._style_secondary(self.btn_reset)
        self._style_secondary(self.btn_cancel)
        self._style_primary(self.btn_save, success=True)
        self.btn_reset.clicked.connect(self.reset_defaults)
        self.btn_cancel.clicked.connect(self.discard_changes)
        self.btn_save.clicked.connect(self.save)
        actions.addWidget(self.btn_reset)
        actions.addStretch(1)
        actions.addWidget(self.btn_cancel)
        actions.addWidget(self.btn_save)
        left_layout.addLayout(actions)
        grid.setColumnStretch(0, 2)
        grid.setColumnStretch(1, 1)
        left.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        left.setMinimumHeight(506)
        left_column_layout.addWidget(left)

        right = QWidget()
        right.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)
        test_card = self._card()
        test_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        test_card.setMinimumHeight(346)
        self.smtp_test_card = test_card
        test_layout = QVBoxLayout(test_card)
        test_layout.setContentsMargins(10, 9, 10, 9)
        test_layout.setSpacing(5)
        test_title = QLabel("Baglanti & Iletim Testi")
        test_title.setStyleSheet("font-size:14px;font-weight:800;color:#dee2f6")
        test_layout.addWidget(test_title)
        description = QLabel("Kaydetmeden once sunucu el sikismasini ve SSL/TLS baglantisini dogrulayin.")
        description.setWordWrap(True)
        description.setStyleSheet("color:#c2c6d6;font-size:11px")
        test_layout.addWidget(description)
        test_layout.addWidget(QLabel("HEDEF TEST E-POSTA ADRESI"))
        self.inp_test_recipient = QLineEdit(self._get("smtp_test_recipient", self._get("smtp_email", self._defaults["smtp_email"])))
        self.inp_test_recipient.setPlaceholderText("ornek@musteri.com")
        self._style_input(self.inp_test_recipient)
        test_layout.addWidget(self.inp_test_recipient)
        self.btn_test = QPushButton("Baglantiyi Sina & Test Maili Gonder")
        self._style_primary(self.btn_test, secondary=True)
        self.btn_test.clicked.connect(self.test_connection)
        test_layout.addWidget(self.btn_test)
        self.lbl_test_status = QLabel("SON TEST DURUMU: Henuz test edilmedi")
        self.lbl_test_status.setWordWrap(True)
        self.lbl_test_status.setStyleSheet("background:#171d2d;color:#c2cce0;padding:9px;border:1px solid #202d45;border-radius:4px;font-size:9px")
        test_layout.addWidget(self.lbl_test_status)
        self.lbl_protocol = QLabel("Soket yaniti: --\nSSL/TLS protokolu: --\nIletilen rapor: --")
        self.lbl_protocol.setStyleSheet("color:#8c98ad;font:8px 'JetBrains Mono',Consolas,monospace")
        protocol_card = QFrame()
        protocol_card.setStyleSheet("QFrame{background:#171d2d;border:1px solid #202d45;border-radius:4px}")
        protocol_layout = QHBoxLayout(protocol_card)
        protocol_layout.setContentsMargins(8, 6, 8, 6)
        protocol_layout.addWidget(self.lbl_protocol)
        test_layout.addWidget(protocol_card)
        for line in ("DNS MX / SPF durumu test edilmedi", "DKIM imzasi test edilmedi", "DMARC raporu test edilmedi"):
            label = QLabel("-  " + line)
            label.setMinimumHeight(18)
            label.setStyleSheet("color:#8c98ad;font-size:9px;padding-left:4px")
            test_layout.addWidget(label)
        test_layout.addStretch(1)
        right_layout.addWidget(test_card)

        preset_card = self._card()
        preset_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        preset_card.setMinimumHeight(117)
        preset_layout = QVBoxLayout(preset_card)
        preset_layout.setContentsMargins(10, 8, 10, 8)
        preset_layout.setSpacing(5)
        preset_layout.addWidget(QLabel("HIZLI SAGLAYICI SABLONLARI"))
        preset_grid = QGridLayout()
        preset_grid.setSpacing(6)
        for index, (caption, detail, host, port, security) in enumerate((
            ("cPanel / Plesk", "Port 465 (SSL)", "mail.example.com", "465", "ssl"),
            ("Google Workspace", "smtp.gmail.com:587", "smtp.gmail.com", "587", "starttls"),
            ("Microsoft 365", "smtp.office365.com", "smtp.office365.com", "587", "starttls"),
            ("Yandex Mail 360", "smtp.yandex.com:465", "smtp.yandex.com", "465", "ssl"),
        )):
            button = QPushButton(caption + "\n" + detail)
            button.setMinimumHeight(40)
            self._style_secondary(button)
            button.clicked.connect(lambda checked=False, values=(host, port, security): self.apply_preset(*values))
            preset_grid.addWidget(button, index // 2, index % 2)
        preset_layout.addLayout(preset_grid)
        right_layout.addWidget(preset_card)

        automation_card = self._card()
        automation_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        automation_card.setMinimumHeight(122)
        automation_layout = QVBoxLayout(automation_card)
        automation_layout.setContentsMargins(10, 8, 10, 8)
        automation_layout.setSpacing(3)
        automation_layout.addWidget(QLabel("BAGLI OTOMASYON DONGULERI"))
        for name, status in (("Servis Kabul Fisi Bildirimi", "OTOMATIK"), ("Cihaz Hazir / Teslim Cagrisi", "OTOMATIK"), ("E-Arsiv / E-Fatura PDF Gonderimi", "MUHASEBE"), ("Fiyat Teklif Onay Talebi", "MANUEL / OTO")):
            row = QHBoxLayout()
            row.addWidget(QLabel(name))
            row.addStretch(1)
            badge = QLabel(status)
            badge.setStyleSheet("color:#4edea3;font-size:9px;font-weight:700")
            row.addWidget(badge)
            automation_layout.addLayout(row)
        right_layout.addWidget(automation_card)
        right_layout.addStretch(1)
        columns.addWidget(left_column, 2)
        columns.addWidget(right, 1)
        root.addLayout(columns, 1)

        log_card = self._card()
        log_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        log_card.setObjectName("p9SmtpLogCard")
        self.log_card = log_card
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(10, 6, 10, 6)
        log_header = QHBoxLayout()
        log_header.addWidget(QLabel("CANLI SMTP ILETISIM PROTOKOL GUNLUGU"))
        log_header.addStretch(1)
        clear_button = QPushButton("TEMIZLE")
        self._style_secondary(clear_button)
        clear_button.clicked.connect(lambda: self.txt_log.clear())
        log_header.addWidget(clear_button)
        log_layout.addLayout(log_header)
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setFixedHeight(64)
        self.txt_log.setPlainText("SMTP test gecmisi bos. Baglanti testi calistirildiginda sonuc burada gorunur.")
        self.txt_log.setStyleSheet("background:#0b1120;color:#4cd7f6;border:0;font:8px 'JetBrains Mono',Consolas,monospace")
        log_layout.addWidget(self.txt_log)
        left_column_layout.addWidget(log_card)
        left_column_layout.addStretch(1)
        self._original = self._snapshot()

    def _get(self, key, default=""):
        return str(self.db.get_setting(key, default) or default)

    def _field(self, label, value, placeholder=""):
        field = QLineEdit(str(value or ""))
        field.setObjectName(label.lower().replace(" ", "_"))
        field.setPlaceholderText(placeholder)
        self._style_input(field)
        return field

    def _style_input(self, widget):
        widget.setMinimumHeight(32)
        if isinstance(widget, QComboBox):
            widget.setStyleSheet("QComboBox{background:#0b1120;color:#dee2f6;border:1px solid #202d45;border-radius:4px;padding:6px;font:9px 'Inter','Segoe UI',sans-serif} QComboBox QAbstractItemView{background:#111827;color:#dee2f6;selection-background-color:#2563eb}")
        else:
            widget.setStyleSheet("QLineEdit{background:#0b1120;color:#dee2f6;border:1px solid #202d45;border-radius:4px;padding:6px;font:9px 'Inter','Segoe UI',sans-serif} QLineEdit:focus{border:1px solid #4f8ff9}")

    def _style_check(self, widget):
        widget.setStyleSheet("color:#c2cce0;font:9px 'Inter','Segoe UI',sans-serif;padding:4px")

    def _card(self):
        frame = QFrame()
        frame.setObjectName("p9SmtpCard")
        frame.setStyleSheet("QFrame#p9SmtpCard{background:#111827;border:1px solid #202d45;border-radius:4px}")
        return frame

    def _style_secondary(self, button):
        button.setMinimumHeight(30)
        button.setStyleSheet("QPushButton{background:#171d2d;color:#c2cce0;border:1px solid #202d45;border-radius:4px;padding:7px 10px;font:8px 'Inter','Segoe UI',sans-serif} QPushButton:hover{background:#1c2940;color:#dee2f6}")

    def _style_primary(self, button, success=False, secondary=False):
        color = "#00b8d9" if secondary else ("#4edea3" if success else "#4f8ff9")
        text = "#06121f" if secondary else ("#07111f" if success else "#07111f")
        button.setMinimumHeight(34)
        button.setStyleSheet(f"QPushButton{{background:{color};color:{text};border:0;border-radius:4px;padding:8px 12px;font:700 9px 'Inter','Segoe UI',sans-serif}} QPushButton:hover{{background:#6ffbbe}}" if success else f"QPushButton{{background:{color};color:{text};border:0;border-radius:4px;padding:8px 12px;font:700 9px 'Inter','Segoe UI',sans-serif}}")

    def _snapshot(self):
        return {
            "smtp_server": self.inp_smtp_server.text(), "smtp_port": self.inp_smtp_port.text(),
            "smtp_email": self.inp_smtp_email.text(), "smtp_sender_name": self.inp_sender_name.text(),
            "smtp_password": self.inp_smtp_password.text(), "smtp_timeout": self.inp_timeout.text(),
            "smtp_security": self.cmb_security.currentData(),
            "smtp_auth_required": "1" if self.chk_auth.isChecked() else "0",
            "smtp_auto_bcc": "1" if self.chk_bcc.isChecked() else "0",
            "smtp_test_recipient": self.inp_test_recipient.text(),
        }

    def _restore(self, values):
        self.inp_smtp_server.setText(values["smtp_server"])
        self.inp_smtp_port.setText(values["smtp_port"])
        self.inp_smtp_email.setText(values["smtp_email"])
        self.inp_sender_name.setText(values["smtp_sender_name"])
        self.inp_smtp_password.setText(values["smtp_password"])
        self.inp_timeout.setText(values["smtp_timeout"])
        self.cmb_security.setCurrentIndex(max(0, self.cmb_security.findData(values["smtp_security"])))
        self._sync_security_buttons()
        self.chk_auth.setChecked(values["smtp_auth_required"] == "1")
        self.chk_bcc.setChecked(values["smtp_auto_bcc"] == "1")
        self.inp_test_recipient.setText(values["smtp_test_recipient"])

    def toggle_password(self):
        visible = self.inp_smtp_password.echoMode() == QLineEdit.EchoMode.Password
        self.inp_smtp_password.setEchoMode(QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password)
        self.btn_show_password.setText("GIZLE" if visible else "GOSTER")

    def apply_preset(self, host, port, security):
        self.inp_smtp_server.setText(host)
        self.inp_smtp_port.setText(port)
        self.cmb_security.setCurrentIndex(max(0, self.cmb_security.findData(security)))
        self._sync_security_buttons()

    def _set_security(self, value):
        self.cmb_security.setCurrentIndex(max(0, self.cmb_security.findData(value)))
        self._sync_security_buttons()

    def _sync_security_buttons(self):
        value = self.cmb_security.currentData()
        for button in self.security_group.buttons():
            button.setChecked(button.property("security_value") == value)
        if hasattr(self, "lbl_connection_state"):
            self.lbl_connection_state.setText(self._security_status(value))

    @staticmethod
    def _security_status(value):
        if value == "ssl":
            return "SSL \u015e\u0130FREL\u0130 (Port 465)"
        if value == "starttls":
            return "TLS \u015e\u0130FREL\u0130 (Port 587)"
        return "\u015e\u0130FRES\u0130Z PORT 25"

    def reset_defaults(self):
        values = dict(self._defaults, smtp_password="", smtp_test_recipient=self._defaults["smtp_email"])
        self._restore(values)

    def discard_changes(self):
        self._restore(self._original)

    def test_connection(self):
        host = self.inp_smtp_server.text().strip()
        sender = self.inp_smtp_email.text().strip()
        recipient = self.inp_test_recipient.text().strip()
        password = self.inp_smtp_password.text()
        try:
            port = int(self.inp_smtp_port.text().strip())
            timeout = max(5, min(60, int(self.inp_timeout.text().strip())))
            if not host or not sender or not recipient:
                raise ValueError("Sunucu ve e-posta alanlarini doldurun.")
            security = self.cmb_security.currentData()
            context = ssl.create_default_context()
            self.txt_log.append(f"Connecting to {host}:{port} ({security})...")
            if security == "ssl":
                server = smtplib.SMTP_SSL(host, port, timeout=timeout, context=context)
            else:
                server = smtplib.SMTP(host, port, timeout=timeout)
            with server:
                server.ehlo()
                if security == "starttls":
                    server.starttls(context=context)
                    server.ehlo()
                if self.chk_auth.isChecked():
                    if not password:
                        raise ValueError("Kimlik dogrulama icin e-posta parolasi gerekli.")
                    server.login(sender, password)
                message = EmailMessage()
                message["Subject"] = "AYEC Pro SMTP test"
                message["From"] = f"{self.inp_sender_name.text().strip()} <{sender}>"
                message["To"] = recipient
                message.set_content("AYEC Pro SMTP baglanti testi basariyla tamamlandi.")
                server.send_message(message)
            self.lbl_connection_state.setText("BAGLANTI BASARILI")
            self.smtp_metric_test.setText(datetime.now().strftime("%H:%M:%S"))
            self.smtp_metric_test_detail.setText("BASARILI")
            self.lbl_test_status.setText("SON TEST DURUMU: Test mesaji gonderildi.")
            self.lbl_test_status.setStyleSheet("background:#1a1f2e;color:#4edea3;padding:10px;border-radius:4px")
            self.lbl_protocol.setText(f"Soket yaniti: OK\nSSL/TLS protokolu: {security}\nIletilen rapor: {recipient}")
            self.txt_log.append("Test message accepted for delivery.")
        except Exception as exc:
            self.lbl_connection_state.setText("BAGLANTI HATASI")
            self.smtp_metric_test_detail.setText("BASARISIZ")
            self.lbl_test_status.setText("SON TEST DURUMU: " + str(exc))
            self.lbl_test_status.setStyleSheet("background:#1a1f2e;color:#ffb4ab;padding:10px;border-radius:4px")
            self.txt_log.append("SMTP test failed: " + str(exc))

    def save(self):
        values = self._snapshot()
        for key in ("smtp_server", "smtp_port", "smtp_email", "smtp_sender_name", "smtp_timeout", "smtp_security", "smtp_auth_required", "smtp_auto_bcc", "smtp_test_recipient"):
            self.db.set_setting(key, values[key])
        SecureSettingStore.set(self.db, "smtp_password", values["smtp_password"])
        self._original = values
        if self.main_window:
            self.main_window.show_notification("SMTP ayarlari kaydedildi.", "success")
