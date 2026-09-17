# -*- coding: utf-8 -*-
"""WhatsApp delivery mode and reminder settings."""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QFrame, QFormLayout, QCheckBox, QTimeEdit, QSpinBox
from PyQt6.QtGui import QFont
from PyQt6.QtCore import QTime, Qt
from src.utils.theme_colors import theme_qss
from src.utils.design_system import DesignTokens


class WhatsAppSettingsWidget(QWidget):
    """Configure Cloud API, provider API, or desktop-assisted delivery."""

    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.setup_ui()
        self._wire_ui_signals()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        title = QLabel("WhatsApp Entegrasyonu")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("color: @text;"))
        layout.addWidget(title)
        info = QLabel("Uc gonderim modu desteklenir: Meta Cloud API, resmi saglayici API ve WhatsApp Desktop kullanici onayli yardimci modu. Cloud API icin onayli sablon ve opt-in kaydi gerekir.")
        info.setWordWrap(True)
        info.setStyleSheet(theme_qss("background: @surface; color: @text_muted; padding: 10px 14px; border: 1px solid @border; border-radius: 10px;"))
        layout.addWidget(info)
        card = QFrame()
        card.setStyleSheet(theme_qss("background: @surface; border: 1px solid @border; border-radius: 16px;"))
        form = QFormLayout(card)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(6)
        form.setHorizontalSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        def line(placeholder=""):
            widget = QLineEdit()
            widget.setPlaceholderText(placeholder)
            widget.setMinimumHeight(34)
            widget.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
            return widget

        self.cmb_mode = QComboBox()
        self.cmb_mode.addItem("Pasif", "disabled")
        self.cmb_mode.addItem("Cloud API (Meta)", "cloud_api")
        self.cmb_mode.addItem("Saglayici API (Twilio/BSP)", "provider_api")
        self.cmb_mode.addItem("WhatsApp Desktop (Kullanici Onayi)", "desktop_manual")
        self.cmb_mode.setMinimumHeight(34)
        self.cmb_mode.setStyleSheet(theme_qss(DesignTokens.get_combobox_qss()))
        form.addRow("Gonderim modu", self.cmb_mode)
        self.inp_template = line("Merhaba {musteri_adi}, {firma_adi} hesabinizda {borc_tutari} TRY borc bulunuyor.")
        form.addRow("Odeme sablonu", self.inp_template)
        self.inp_phone = line("905XXXXXXXXX")
        form.addRow("Isletme numarasi", self.inp_phone)
        self.inp_cloud_phone_id = line("Meta phone number ID")
        form.addRow("Cloud phone ID", self.inp_cloud_phone_id)
        self.inp_cloud_token = line("Meta access token")
        self.inp_cloud_token.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Cloud access token", self.inp_cloud_token)
        self.inp_cloud_template = line("payment_reminder_tr")
        form.addRow("Cloud sablon adi", self.inp_cloud_template)
        self.inp_provider_sid = line("Twilio Account SID")
        form.addRow("Saglayici Account SID", self.inp_provider_sid)
        self.inp_provider_token = line("Twilio Auth Token")
        self.inp_provider_token.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Saglayici Auth Token", self.inp_provider_token)
        self.inp_provider_from = line("whatsapp:+905XXXXXXXXX")
        form.addRow("Saglayici gonderici", self.inp_provider_from)
        self.chk_reminder = QCheckBox("Haftalik borc odeme hatirlatmasini etkinlestir")
        form.addRow("Otomasyon", self.chk_reminder)
        self.cmb_day = QComboBox()
        for day, value in (("Pazartesi", 0), ("Sali", 1), ("Carsamba", 2), ("Persembe", 3), ("Cuma", 4), ("Cumartesi", 5), ("Pazar", 6)):
            self.cmb_day.addItem(day, value)
        self.cmb_day.setMinimumHeight(34)
        form.addRow("Hatirlatma gunu", self.cmb_day)
        self.time_reminder = QTimeEdit(QTime(10, 0))
        self.time_reminder.setDisplayFormat("HH:mm")
        self.time_reminder.setMinimumHeight(34)
        form.addRow("Hatirlatma saati", self.time_reminder)
        self.spin_min_debt = QSpinBox()
        self.spin_min_debt.setRange(0, 100000000)
        self.spin_min_debt.setSuffix(" TRY")
        self.spin_min_debt.setMinimumHeight(34)
        form.addRow("Asgari borc", self.spin_min_debt)
        btn_save = QPushButton("AYARLARI KAYDET")
        btn_save.setFixedHeight(45)
        btn_save.setStyleSheet(theme_qss(DesignTokens.get_button_qss("success", size="md")))
        btn_save.clicked.connect(self.save_data)
        form.addRow("", btn_save)
        layout.addWidget(card)
        layout.addStretch()

    def _wire_ui_signals(self):
        self.cmb_mode.currentIndexChanged.connect(self.save_data)

    def load_data(self):
        self.inp_phone.setText(self.db.get_setting("whatsapp_number", ""))
        mode = self.db.get_setting("whatsapp_mode", "")
        if not mode:
            legacy = self.db.get_setting("whatsapp_active", "0")
            mode = {"1": "desktop_manual", "2": "provider_api"}.get(str(legacy), "disabled")
        index = self.cmb_mode.findData(mode)
        self.cmb_mode.setCurrentIndex(index if index >= 0 else 0)
        self.inp_cloud_phone_id.setText(self.db.get_setting("whatsapp_cloud_phone_id", ""))
        self.inp_cloud_token.setText(self.db.get_setting("whatsapp_cloud_token", ""))
        self.inp_cloud_template.setText(self.db.get_setting("whatsapp_cloud_template", "payment_reminder_tr"))
        self.inp_provider_sid.setText(self.db.get_setting("twilio_account_sid", ""))
        self.inp_provider_token.setText(self.db.get_setting("twilio_auth_token", ""))
        self.inp_provider_from.setText(self.db.get_setting("twilio_whatsapp_from", ""))
        self.chk_reminder.setChecked(self.db.get_setting("whatsapp_payment_reminder_enabled", "0") == "1")
        day = int(self.db.get_setting("whatsapp_payment_reminder_day", "4") or 4)
        day_index = self.cmb_day.findData(day)
        self.cmb_day.setCurrentIndex(day_index if day_index >= 0 else 4)
        raw_time = self.db.get_setting("whatsapp_payment_reminder_time", "10:00")
        parsed_time = QTime.fromString(raw_time, "HH:mm")
        self.time_reminder.setTime(parsed_time if parsed_time.isValid() else QTime(10, 0))
        self.spin_min_debt.setValue(int(float(self.db.get_setting("whatsapp_payment_min_debt_try", "0") or 0)))
        self.inp_template.setText(self.db.get_setting("whatsapp_payment_template", "Merhaba {musteri_adi}, {firma_adi} hesabinizda {borc_tutari} TRY borc bulunuyor."))

    def save_data(self):
        mode = self.cmb_mode.currentData() or "disabled"
        self.db.set_setting("whatsapp_number", self.inp_phone.text().strip())
        self.db.set_setting("whatsapp_mode", mode)
        self.db.set_setting("whatsapp_active", "1" if mode != "disabled" else "0")
        self.db.set_setting("whatsapp_cloud_phone_id", self.inp_cloud_phone_id.text().strip())
        self.db.set_setting("whatsapp_cloud_token", self.inp_cloud_token.text().strip())
        self.db.set_setting("whatsapp_cloud_template", self.inp_cloud_template.text().strip())
        self.db.set_setting("twilio_account_sid", self.inp_provider_sid.text().strip())
        self.db.set_setting("twilio_auth_token", self.inp_provider_token.text().strip())
        self.db.set_setting("twilio_whatsapp_from", self.inp_provider_from.text().strip())
        self.db.set_setting("whatsapp_payment_reminder_enabled", "1" if self.chk_reminder.isChecked() else "0")
        self.db.set_setting("whatsapp_payment_reminder_day", str(self.cmb_day.currentData()))
        self.db.set_setting("whatsapp_payment_reminder_time", self.time_reminder.time().toString("HH:mm"))
        self.db.set_setting("whatsapp_payment_min_debt_try", str(self.spin_min_debt.value()))
        self.db.set_setting("whatsapp_payment_template", self.inp_template.text().strip())
        if self.main_window:
            from src.utils.toast_notification import show_success
            show_success(self.main_window, "WhatsApp ayarlari guncellendi.")
