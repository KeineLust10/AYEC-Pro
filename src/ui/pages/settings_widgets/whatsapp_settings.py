# -*- coding: utf-8 -*-
"""WhatsApp delivery mode and reminder settings."""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QPushButton, QComboBox, QFrame, QCheckBox, QTimeEdit, QSpinBox, QTextEdit, QAbstractSpinBox, QScrollArea, QBoxLayout
from PyQt6.QtCore import QTime, Qt
from src.utils.theme_colors import theme_qss
from src.utils.design_system import DesignTokens
from src.utils.secure_setting_store import SecureSettingStore


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
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(theme_qss("QScrollArea { background: transparent; border: none; }"))
        content = QWidget()
        scroll.setWidget(content)
        root_layout.addWidget(scroll)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 10, 12, 20)
        layout.setSpacing(10)
        integration_tabs = QHBoxLayout()
        integration_tabs.setSpacing(6)
        self.integration_nav_buttons = []
        for label, page_id in (
            ("WhatsApp Entegrasyonu", 20),
            ("Hizli Notlar & Makrolar", 14),
            ("Kargo ve Lojistik", 5),
            ("AI Asistan & Kestirmeler", 21),
            ("SMS & Iletisim Sablonlari", 3),
        ):
            tab_button = QPushButton(label)
            tab_button.setText(label.replace(" & ", " &\n"))
            tab_button.setMinimumHeight(68)
            tab_button.setProperty("settingsPageId", page_id)
            tab_button.setStyleSheet(theme_qss(
                "QPushButton { background: transparent; color: @text_muted; border: 0; "
                "border-bottom: 2px solid transparent; border-radius: 0; padding: 8px 10px; font-size: 13px; } "
                "QPushButton:hover { background: @surface; color: @text; }"
                if page_id != 20 else
                "QPushButton { background: transparent; color: @text; border: 0; "
                "border-bottom: 2px solid @accent; border-radius: 0; padding: 8px 10px; "
                "font-size: 13px; font-weight: 800; }"
            ))
            tab_button.clicked.connect(
                lambda _checked=False, target=page_id: self._navigate_to_settings_page(target)
            )
            self.integration_nav_buttons.append(tab_button)
            integration_tabs.addWidget(tab_button, 1)
        layout.addLayout(integration_tabs)
        layout.addSpacing(20)
        summary = QFrame()
        summary.setStyleSheet(theme_qss("QFrame { background: transparent; border: none; }"))
        summary_layout = QHBoxLayout(summary)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        summary_layout.setSpacing(10)
        for caption, value, color in (("KANAL", "WHATSAPP", "@finance_primary"), ("SABLON", "HAZIR", "@finance_secondary"), ("GUVENLIK", "TOKEN KORUMALI", "@finance_tertiary"), ("HATIRLATMA", "PLANLI", "@finance_outline")):
            card = QFrame()
            card.setStyleSheet(theme_qss(f"QFrame {{ background: @surface; border: 1px solid {color}; border-radius: 14px; }}"))
            card.setFixedHeight(134)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(18, 16, 18, 16)
            card_layout.setSpacing(8)
            cap = QLabel(caption)
            cap.setStyleSheet(theme_qss("color: @text_muted; border: none; font-size: 12px; font-weight: 700;"))
            val = QLabel(value)
            val.setStyleSheet(theme_qss(f"color: {color}; border: none; font-size: 20px; font-weight: 800;"))
            card_layout.addWidget(cap)
            card_layout.addWidget(val)
            summary_layout.addWidget(card)
        layout.addWidget(summary)
        layout.addSpacing(20)
        info = QLabel("Uc gonderim modu desteklenir: Meta Cloud API, resmi saglayici API ve WhatsApp Desktop kullanici onayli yardimci modu. Cloud API icin onayli sablon ve opt-in kaydi gerekir.")
        info.setWordWrap(True)
        info.setMinimumHeight(70)
        info.setStyleSheet(theme_qss("background: @surface; color: @text_muted; padding: 14px 16px; border: 1px solid @border; border-radius: 10px; font-size: 13px;"))
        layout.addWidget(info)
        layout.addSpacing(20)
        card = QFrame()
        card.setObjectName("WhatsAppProtocolCard")
        card.setStyleSheet(theme_qss(
            "QFrame#WhatsAppProtocolCard { background: @surface; border: 1px solid @border; border-radius: 16px; }"
        ))
        form = QGridLayout(card)
        form.setContentsMargins(20, 20, 20, 20)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(16)
        for column in range(4):
            form.setColumnStretch(column, 1)

        def add_field(label, widget, row, column):
            label_widget = QLabel(label)
            label_widget.setStyleSheet(theme_qss(
                "color: @text_muted; font-size: 12px; font-weight: 600; border: none; background: transparent;"
            ))
            form.addWidget(label_widget, row * 2, column * 2, 1, 2)
            form.addWidget(widget, row * 2 + 1, column * 2, 1, 2)

        def line(placeholder=""):
            widget = QLineEdit()
            widget.setPlaceholderText(placeholder)
            widget.setMinimumHeight(34)
            widget.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
            return widget

        self.cmb_mode = QComboBox()
        self.cmb_mode.setProperty("referenceGlyph", "chevron_down")
        self.cmb_mode.addItem("Pasif", "disabled")
        self.cmb_mode.addItem("Cloud API (Meta)", "cloud_api")
        self.cmb_mode.addItem("Saglayici API (Twilio/BSP)", "provider_api")
        self.cmb_mode.addItem("WhatsApp Desktop (Kullanici Onayi)", "desktop_manual")
        self.cmb_mode.setMinimumHeight(34)
        self.cmb_mode.setStyleSheet(theme_qss(DesignTokens.get_combobox_qss()))
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 12)
        header_layout.setSpacing(12)
        protocol_mark = QLabel("WA")
        protocol_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        protocol_mark.setFixedSize(40, 40)
        protocol_mark.setStyleSheet(theme_qss(
            "background: @finance_success_bg; color: @finance_secondary; border-radius: 10px; "
            "font-size: 14px; font-weight: 800; border: none;"
        ))
        header_text = QVBoxLayout()
        protocol_title = QLabel("WhatsApp Meta Cloud API Protokolu")
        protocol_title.setStyleSheet(theme_qss("color: @text; font-size: 15px; font-weight: 800; border: none;"))
        protocol_description = QLabel("Kurumsal API kimlik dogrulamasi ve otomatik hatirlatma parametreleri")
        protocol_description.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px; border: none;"))
        header_text.addWidget(protocol_title)
        header_text.addWidget(protocol_description)
        header_layout.addWidget(protocol_mark)
        header_layout.addLayout(header_text, 1)
        version_badge = QLabel("v17.0 Entegre")
        version_badge.setStyleSheet(theme_qss(
            "color: @finance_secondary; background: @finance_success_bg; border: 1px solid @border; "
            "border-radius: 6px; padding: 6px 10px; font-size: 11px;"
        ))
        header_layout.addWidget(version_badge, 0, Qt.AlignmentFlag.AlignTop)
        form.addWidget(header, 0, 0, 1, 4)
        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(theme_qss("background: @border; border: none;"))
        form.addWidget(divider, 1, 0, 1, 4)
        form.setRowMinimumHeight(1, 32)
        self.inp_phone = line("905XXXXXXXXX")
        add_field("Gonderim modu", self.cmb_mode, 1, 0)
        add_field("Isletme numarasi", self.inp_phone, 1, 1)
        self.inp_cloud_phone_id = line("Meta phone number ID")
        add_field("Cloud phone ID", self.inp_cloud_phone_id, 2, 0)
        self.inp_cloud_token = line("Meta access token")
        self.inp_cloud_token.setEchoMode(QLineEdit.EchoMode.Password)
        add_field("Cloud access token", self.inp_cloud_token, 2, 1)
        self.inp_cloud_template = line("payment_reminder_tr")
        add_field("Cloud sablon adi", self.inp_cloud_template, 3, 0)
        self.inp_provider_sid = line("Twilio Account SID")
        add_field("Saglayici Account SID", self.inp_provider_sid, 3, 1)
        self.inp_provider_token = line("Twilio Auth Token")
        self.inp_provider_token.setEchoMode(QLineEdit.EchoMode.Password)
        add_field("Saglayici Auth Token", self.inp_provider_token, 4, 0)
        self.inp_provider_from = line("whatsapp:+905XXXXXXXXX")
        add_field("Saglayici gonderici", self.inp_provider_from, 4, 1)
        self.inp_template = QTextEdit()
        self.inp_template.setPlaceholderText(
            "Merhaba {musteri_adi}, {firma_adi} hesabinizda {borc_tutari} TRY borc bulunuyor."
        )
        self.inp_template.setFixedHeight(106)
        self.inp_template.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        add_field("Odeme sablonu", self.inp_template, 5, 0)
        form.addWidget(self.inp_template, 11, 0, 1, 4)
        token_toolbar = QWidget()
        token_toolbar_layout = QHBoxLayout(token_toolbar)
        token_toolbar_layout.setContentsMargins(0, 0, 0, 0)
        token_toolbar_layout.setSpacing(6)
        token_names = (("Musteri adi", "{musteri_adi}"), ("Firma adi", "{firma_adi}"), ("Borc tutari", "{borc_tutari}"))
        for label, token in token_names:
            token_button = QPushButton(f"+\n{label}")
            token_button.setMinimumHeight(34)
            token_button.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
            token_button.clicked.connect(lambda checked=False, value=token: self.inp_template.insertPlainText(value))
            token_toolbar_layout.addWidget(token_button)
        form.addWidget(token_toolbar, 10, 2, 1, 2)
        form.setRowMinimumHeight(10, 88)
        template_help = QLabel("Dinamik etiketler sistem veritabanindaki cari kartlar ile otomatik eslestirilir.")
        template_help.setWordWrap(True)
        template_help.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; border: none;"))
        form.addWidget(template_help, 12, 0, 1, 4)
        form.setRowMinimumHeight(12, 50)
        self.chk_reminder = QCheckBox("Haftalik borc odeme hatirlatmasini etkinlestir")
        self.chk_reminder.setStyleSheet(theme_qss("QCheckBox { color: @text; font-weight: 700; border: none; }"))
        reminder_card = QFrame()
        reminder_card.setObjectName("WhatsAppReminderCard")
        reminder_card.setStyleSheet(theme_qss(
            "QFrame#WhatsAppReminderCard { background: @surface_alt; border: 1px solid @border; border-radius: 12px; }"
        ))
        reminder_card.setMinimumHeight(170)
        reminder_layout = QGridLayout(reminder_card)
        reminder_layout.setContentsMargins(16, 20, 16, 20)
        reminder_layout.setHorizontalSpacing(18)
        reminder_layout.setVerticalSpacing(30)
        reminder_layout.addWidget(self.chk_reminder, 0, 0, 1, 4)
        self.cmb_day = QComboBox()
        self.cmb_day.setProperty("referenceGlyph", "chevron_down")
        for day, value in (("Pazartesi", 0), ("Sali", 1), ("Carsamba", 2), ("Persembe", 3), ("Cuma", 4), ("Cumartesi", 5), ("Pazar", 6)):
            self.cmb_day.addItem(day, value)
        self.cmb_day.setMinimumHeight(34)
        self.time_reminder = QTimeEdit(QTime(10, 0))
        self.time_reminder.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.time_reminder.setDisplayFormat("HH:mm")
        self.time_reminder.setMinimumHeight(34)
        self.time_reminder.setStyleSheet(theme_qss(
            "QTimeEdit { background: @surface_alt; color: @text; border: 1px solid @border; "
            "border-radius: 8px; padding: 6px 10px; min-height: 34px; } "
            "QTimeEdit::up-button, QTimeEdit::down-button { width: 0; height: 0; border: 0; }"
        ))
        for caption, widget, column in (("Hatirlatma gunu", self.cmb_day, 0), ("Hatirlatma saati", self.time_reminder, 2)):
            caption_label = QLabel(caption)
            caption_label.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px; font-weight: 600; border: none; background: transparent;"))
            reminder_layout.addWidget(caption_label, 1, column, 1, 2)
            reminder_layout.addWidget(widget, 2, column, 1, 2)
        reminder_layout.setRowMinimumHeight(1, 16)
        form.addWidget(reminder_card, 13, 0, 1, 4)
        self.spin_min_debt = QSpinBox()
        self.spin_min_debt.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.spin_min_debt.setRange(0, 100000000)
        self.spin_min_debt.setSuffix(" TRY")
        self.spin_min_debt.setMinimumHeight(34)
        self.spin_min_debt.setStyleSheet(theme_qss(
            "QSpinBox { background: @surface_alt; color: @text; border: 1px solid @border; "
            "border-radius: 8px; padding: 6px 10px; min-height: 34px; } "
            "QSpinBox::up-button, QSpinBox::down-button { width: 0; height: 0; border: 0; }"
        ))
        add_field("Asgari borc", self.spin_min_debt, 15, 0)
        btn_save = QPushButton("AYARLARI KAYDET")
        btn_save.setFixedHeight(45)
        btn_save.setObjectName("whatsapp_settings_save")
        btn_save.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="md")))
        btn_save.clicked.connect(self.save_data)
        form.addWidget(btn_save, 32, 0, 1, 4)
        columns = QHBoxLayout()
        columns.setSpacing(12)
        columns.addWidget(card, 2)
        side_column = QWidget()
        side_column_layout = QVBoxLayout(side_column)
        side_column_layout.setContentsMargins(0, 0, 0, 0)
        side_column_layout.setSpacing(24)
        side = QFrame()
        side.setStyleSheet(theme_qss("QFrame { background: @surface; border: 1px solid @border; border-radius: 16px; }"))
        side.setMinimumHeight(630)
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(16, 16, 16, 16)
        side_layout.setSpacing(16)
        side.setMaximumHeight(650)
        side_header = QHBoxLayout()
        bot_mark = QLabel("TG")
        bot_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bot_mark.setFixedSize(34, 34)
        bot_mark.setStyleSheet(theme_qss("background: @finance_surface_high; color: @finance_secondary; border-radius: 9px; font-weight: 800; border: none;"))
        side_title = QLabel("Telegram ve AI Masasi")
        side_title.setStyleSheet(theme_qss("color: @text; font-size: 14px; font-weight: 800; border: none;"))
        side_status = QLabel("\u25cf Cevrimici")
        side_status.setStyleSheet(theme_qss("color: @finance_secondary; font-weight: 700; border: none;"))
        side_header.addWidget(bot_mark)
        side_header.addWidget(side_title, 1)
        side_header.addWidget(side_status)
        side_layout.addLayout(side_header)
        bot_card = QFrame()
        bot_card.setStyleSheet(theme_qss("QFrame { background: @surface_alt; border: 1px solid @border; border-radius: 10px; }"))
        bot_card.setMinimumHeight(72)
        bot_layout = QHBoxLayout(bot_card)
        bot_layout.setContentsMargins(12, 10, 12, 10)
        bot_info = QVBoxLayout()
        bot_name = QLabel("AYEC Teknik Bot")
        bot_name.setStyleSheet(theme_qss("color: @text; font-weight: 800; border: none;"))
        bot_handle = QLabel("@ayeconline_bot")
        bot_handle.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; border: none;"))
        bot_info.addWidget(bot_name)
        bot_info.addWidget(bot_handle)
        live_badge = QLabel("Canli")
        live_badge.setStyleSheet(theme_qss("color: @text; background: @surface; border: 1px solid @border; border-radius: 6px; padding: 6px 10px;"))
        bot_layout.addLayout(bot_info, 1)
        bot_layout.addWidget(live_badge)
        side_layout.addWidget(bot_card)
        for label, value in (("Bot API Token", "****************"), ("Bagli Teknisyen Grup Chat ID", "-1001928374610")):
            box = QFrame()
            box.setMinimumHeight(76)
            box.setStyleSheet(theme_qss("background: @surface_alt; border: 1px solid @border; border-radius: 8px;"))
            box_layout = QVBoxLayout(box)
            box_layout.setContentsMargins(10, 8, 10, 8)
            cap = QLabel(label)
            cap.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px; border: none;"))
            val = QLabel(value)
            val.setWordWrap(True)
            val.setStyleSheet(theme_qss("color: @text; font-weight: 700; border: none;"))
            box_layout.addWidget(cap)
            box_layout.addWidget(val)
            side_layout.addWidget(box)
        command_box = QFrame()
        command_box.setStyleSheet(theme_qss("QFrame { background: @surface_alt; border: 1px solid @border; border-radius: 8px; }"))
        command_layout = QVBoxLayout(command_box)
        command_layout.setContentsMargins(10, 8, 10, 8)
        command_caption = QLabel("Tanimli Hizli Komutlar")
        command_caption.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; border: none;"))
        command_layout.addWidget(command_caption)
        command_tags = QGridLayout()
        command_tags.setHorizontalSpacing(6)
        command_tags.setVerticalSpacing(6)
        command_box.setMinimumHeight(126)
        for index, command in enumerate(("/servis_ac", "/stok_sorgu", "/fiyat_zam", "/acil_destek")):
            tag = QLabel(command)
            tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
            tag.setStyleSheet(theme_qss("color: @finance_secondary; background: @surface; border: 1px solid @border; border-radius: 6px; padding: 7px 5px; font-size: 10px;"))
            command_tags.addWidget(tag, index // 2, index % 2)
        command_layout.addLayout(command_tags)
        side_layout.addWidget(command_box)
        webhook = QFrame()
        webhook.setMinimumHeight(90)
        webhook.setStyleSheet(theme_qss("QFrame { background: @surface_alt; border: 1px solid @border; border-radius: 8px; }"))
        webhook_layout = QVBoxLayout(webhook)
        webhook_layout.setContentsMargins(10, 8, 10, 8)
        webhook_status = QLabel("Webhook Durumu:                                      200 OK")
        webhook_status.setStyleSheet(theme_qss("color: @finance_secondary; border: none;"))
        webhook_ping = QLabel("Son ping: 12 sn. once (gecikme 44ms)")
        webhook_ping.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px; border: none;"))
        webhook_layout.addWidget(webhook_status)
        webhook_layout.addWidget(webhook_ping)
        side_layout.addWidget(webhook)
        support = QFrame()
        support.setStyleSheet(theme_qss(
            "QFrame { background: @surface_alt; border: 1px solid @border; border-radius: 12px; }"
        ))
        support_layout = QVBoxLayout(support)
        support_layout.setContentsMargins(14, 12, 14, 12)
        support.setMinimumHeight(110)
        support_title = QLabel("Entegrasyon Destegi")
        support_title.setStyleSheet(theme_qss("color: @text; font-weight: 800; border: none;"))
        support_copy = QLabel("Meta API anahtari ve hesap onay surecleri icin yetkili yoneticinizle iletisime gecin.")
        support_copy.setWordWrap(True)
        support_copy.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px; border: none;"))
        support_layout.addWidget(support_title)
        support_layout.addWidget(support_copy)
        side_column_layout.addWidget(side)
        side_column_layout.addWidget(support)
        side_column_layout.addStretch(1)
        columns.addWidget(side_column, 1)
        columns.setAlignment(side_column, Qt.AlignmentFlag.AlignTop)
        self._columns_layout = columns
        layout.addLayout(columns)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        columns = getattr(self, "_columns_layout", None)
        if columns is None:
            return
        if self.width() < 1160:
            columns.setDirection(QBoxLayout.Direction.TopToBottom)
            columns.setStretch(0, 0)
            columns.setStretch(1, 0)
        else:
            columns.setDirection(QBoxLayout.Direction.LeftToRight)
            columns.setStretch(0, 2)
            columns.setStretch(1, 1)

    def _wire_ui_signals(self):
        self.cmb_mode.currentIndexChanged.connect(self.save_data)

    def _navigate_to_settings_page(self, page_id):
        parent = self.parentWidget()
        while parent is not None:
            if hasattr(parent, "sidebar") and hasattr(parent.sidebar, "items_map"):
                sidebar = parent.sidebar
                if hasattr(sidebar, "search_inp"):
                    sidebar.search_inp.clear()
                for row, mapped_id in enumerate(sidebar.items_map):
                    if mapped_id == page_id:
                        sidebar.list_widget.setCurrentRow(row)
                        return True
                return False
            parent = parent.parentWidget()
        return False

    def load_data(self):
        self.inp_phone.setText(self.db.get_setting("whatsapp_number", ""))
        mode = self.db.get_setting("whatsapp_mode", "")
        if not mode:
            legacy = self.db.get_setting("whatsapp_active", "0")
            mode = {"1": "desktop_manual", "2": "provider_api"}.get(str(legacy), "disabled")
        index = self.cmb_mode.findData(mode)
        self.cmb_mode.setCurrentIndex(index if index >= 0 else 0)
        self.inp_cloud_phone_id.setText(self.db.get_setting("whatsapp_cloud_phone_id", ""))
        self.inp_cloud_token.setText(
            SecureSettingStore.get(self.db, "whatsapp_cloud_token", "")
        )
        self.inp_cloud_template.setText(self.db.get_setting("whatsapp_cloud_template", "payment_reminder_tr"))
        self.inp_provider_sid.setText(self.db.get_setting("twilio_account_sid", ""))
        self.inp_provider_token.setText(
            SecureSettingStore.get(self.db, "twilio_auth_token", "")
        )
        self.inp_provider_from.setText(self.db.get_setting("twilio_whatsapp_from", ""))
        self.chk_reminder.setChecked(self.db.get_setting("whatsapp_payment_reminder_enabled", "0") == "1")
        day = int(self.db.get_setting("whatsapp_payment_reminder_day", "4") or 4)
        day_index = self.cmb_day.findData(day)
        self.cmb_day.setCurrentIndex(day_index if day_index >= 0 else 4)
        raw_time = self.db.get_setting("whatsapp_payment_reminder_time", "10:00")
        parsed_time = QTime.fromString(raw_time, "HH:mm")
        self.time_reminder.setTime(parsed_time if parsed_time.isValid() else QTime(10, 0))
        self.spin_min_debt.setValue(int(float(self.db.get_setting("whatsapp_payment_min_debt_try", "0") or 0)))
        self.inp_template.setPlainText(self.db.get_setting("whatsapp_payment_template", "Merhaba {musteri_adi}, {firma_adi} hesabinizda {borc_tutari} TRY borc bulunuyor."))

    def save_data(self):
        mode = self.cmb_mode.currentData() or "disabled"
        self.db.set_setting("whatsapp_number", self.inp_phone.text().strip())
        self.db.set_setting("whatsapp_mode", mode)
        self.db.set_setting("whatsapp_active", "1" if mode != "disabled" else "0")
        self.db.set_setting("whatsapp_cloud_phone_id", self.inp_cloud_phone_id.text().strip())
        SecureSettingStore.set(
            self.db, "whatsapp_cloud_token", self.inp_cloud_token.text().strip()
        )
        self.db.set_setting("whatsapp_cloud_template", self.inp_cloud_template.text().strip())
        self.db.set_setting("twilio_account_sid", self.inp_provider_sid.text().strip())
        SecureSettingStore.set(
            self.db, "twilio_auth_token", self.inp_provider_token.text().strip()
        )
        self.db.set_setting("twilio_whatsapp_from", self.inp_provider_from.text().strip())
        self.db.set_setting("whatsapp_payment_reminder_enabled", "1" if self.chk_reminder.isChecked() else "0")
        self.db.set_setting("whatsapp_payment_reminder_day", str(self.cmb_day.currentData()))
        self.db.set_setting("whatsapp_payment_reminder_time", self.time_reminder.time().toString("HH:mm"))
        self.db.set_setting("whatsapp_payment_min_debt_try", str(self.spin_min_debt.value()))
        self.db.set_setting("whatsapp_payment_template", self.inp_template.toPlainText().strip())
        if self.main_window:
            from src.utils.toast_notification import show_success
            show_success(self.main_window, "WhatsApp ayarlari guncellendi.")
