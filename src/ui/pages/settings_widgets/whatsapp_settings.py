# -*- coding: utf-8 -*-
"""WhatsApp delivery mode and reminder settings."""

import json

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QPushButton, QComboBox, QFrame, QCheckBox, QTimeEdit, QSpinBox, QTextEdit, QAbstractSpinBox, QScrollArea, QBoxLayout, QSizePolicy
from PyQt6.QtCore import QTime, QTimer, Qt
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
        content.setMinimumWidth(0)
        content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        content.setStyleSheet("background: #080c14; color: #e2e8f0;")
        scroll.setWidget(content)
        self._settings_scroll = scroll
        self._settings_content = content
        root_layout.addWidget(scroll)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(8, 8, 8, 12)
        layout.setSpacing(8)
        tabs_scroll = QScrollArea(self)
        tabs_scroll.setWidgetResizable(False)
        tabs_scroll.setFixedHeight(70)
        tabs_scroll.setFrameShape(QFrame.Shape.NoFrame)
        tabs_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        tabs_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        tabs_scroll.setStyleSheet("background: transparent; border: none;")
        tabs_content = QWidget()
        self._integration_tabs_content = tabs_content
        integration_tabs = QHBoxLayout(tabs_content)
        integration_tabs.setContentsMargins(0, 0, 0, 0)
        integration_tabs.setSpacing(6)
        self._integration_tabs_layout = integration_tabs
        self._settings_page_selector = None
        self.integration_nav_buttons = []
        for label, page_id in (
            ("WhatsApp\nEntegrasyonu", 20),
            ("Entegrasyonlar\nAPI", 21),
            ("Hizli Notlar & Makrolar", 14),
            ("Kargo ve\nLojistik", 5),
            ("AI Asistan & Kestirmeler", 13),
            ("SMS & Iletisim\nSablonlari", 3),
        ):
            tab_button = QPushButton(label)
            tab_button.setText(label.replace(" & ", " &\n"))
            tab_button.setMinimumSize(145, 52)
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
        tabs_content.setMinimumWidth(6 * 145 + 5 * 6 + 260)
        tabs_scroll.setWidget(tabs_content)
        self._integration_tabs_scroll = tabs_scroll
        # Keep legacy shortcuts wired while omitting this duplicate tab bar.
        tabs_scroll.hide()
        summary = QFrame()
        summary.setObjectName("WhatsAppReferenceMetrics")
        summary.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        summary.setStyleSheet(theme_qss("QFrame#WhatsAppReferenceMetrics { background: transparent; border: none; }"))
        summary_layout = QGridLayout(summary)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        summary_layout.setHorizontalSpacing(12)
        summary_layout.setVerticalSpacing(10)
        self._summary_layout = summary_layout
        summary_cards = []
        summary_status_values = []
        summary_note_values = []
        summary_specs = (
            ("KANAL", "WHATSAPP", "Aktif kanal", "@finance_primary", "WA"),
            ("SABLON DURUMU", "HAZIR", "Onayli sablon", "@finance_secondary", "OK"),
            ("GUVENLIK KATMANI", "TOKEN KORUMALI", "256-bit", "@danger", "256"),
            ("HATIRLATMA DONGUSU", "PLANLI CRON", "Haftalik", "@finance_secondary", "7d"),
        )
        for caption, value, note, color, glyph in summary_specs:
            metric = QFrame()
            metric.setMinimumWidth(0)
            metric.setFixedHeight(66)
            metric.setStyleSheet(theme_qss(
                f"QFrame {{ background: @surface; border: 1px solid @border; border-radius: 6px; }}"
            ))
            metric_layout = QVBoxLayout(metric)
            metric_layout.setContentsMargins(12, 8, 12, 7)
            metric_layout.setSpacing(1)
            metric_header = QHBoxLayout()
            metric_header.setSpacing(8)
            cap = QLabel(caption)
            cap.setStyleSheet(theme_qss("color: @text_muted; border: none; font-size: 10px; font-weight: 700; letter-spacing: 1px;"))
            icon = QLabel(glyph)
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon.setFixedSize(28, 28)
            icon.setStyleSheet(theme_qss(
                f"color: {color}; background: @surface_alt; border: 1px solid @border; "
                "border-radius: 6px; font-size: 10px; font-weight: 800;"
            ))
            metric_header.addWidget(cap, 1)
            metric_header.addWidget(icon)
            value_label = QLabel(value)
            value_label.setWordWrap(True)
            value_label.setStyleSheet(theme_qss(
                f"color: {color}; border: none; font-size: 13px; font-weight: 800;"
            ))
            note_label = QLabel(note)
            note_label.setStyleSheet(theme_qss("color: @text_muted; border: none; font-size: 10px;"))
            metric_layout.addLayout(metric_header)
            metric_layout.addWidget(value_label, 1)
            metric_layout.addWidget(note_label)
            summary_layout.addWidget(metric, 0, len(summary_cards))
            summary_cards.append(metric)
            summary_status_values.append(value_label)
            summary_note_values.append(note_label)
        layout.addWidget(summary)
        self._summary_cards = summary_cards
        self._summary_status_values = summary_status_values
        self._summary_note_values = summary_note_values

        notice = QFrame()
        notice.setObjectName("WhatsAppReferenceNotice")
        notice.setMinimumHeight(36)
        notice.setStyleSheet(theme_qss(
            "QFrame#WhatsAppReferenceNotice { background: @surface_alt; border: 1px solid @border; border-radius: 6px; }"
        ))
        notice_layout = QHBoxLayout(notice)
        notice_layout.setContentsMargins(10, 5, 10, 5)
        notice_layout.setSpacing(8)
        notice_icon = QLabel("i")
        notice_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        notice_icon.setFixedSize(18, 18)
        notice_icon.setStyleSheet(theme_qss(
            "color: @finance_primary_text; background: @finance_primary; border: none; border-radius: 11px; font-weight: 800;"
        ))
        notice_text = QLabel(
            "Uc gonderim modu desteklenir: Meta Cloud API, resmi saglayici API ve WhatsApp Desktop "
            "kullanici onayli yardimci modu. Cloud API icin onayli sablon ve opt-in kaydi gerekir."
        )
        notice_text.setWordWrap(True)
        notice_text.setStyleSheet(theme_qss("color: @text_muted; border: none; font-size: 11px;"))
        notice_layout.addWidget(notice_icon)
        notice_layout.addWidget(notice_text, 1)
        layout.addWidget(notice)
        layout.addSpacing(10)
        whatsapp_configured = self._is_whatsapp_configured()
        sms_active = str(self.db.get_setting("sms_active", "0")) == "1"
        ai_configured = bool(SecureSettingStore.get(self.db, "gemini_api_key", ""))
        card = QFrame()
        card.setObjectName("WhatsAppProtocolCard")
        card.setStyleSheet(theme_qss(
            "QFrame#WhatsAppProtocolCard { background: #131e32; border: 1px solid #1e2e4a; border-radius: 10px; }"
        ))
        form = QGridLayout(card)
        form.setContentsMargins(10, 8, 10, 8)
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(2)
        for column in range(4):
            form.setColumnStretch(column, 1)

        def add_field(label, widget, row, column):
            label_widget = QLabel(label)
            label_widget.setStyleSheet(theme_qss(
                "color: @text_muted; font-size: 10px; font-weight: 600; border: none; background: transparent;"
            ))
            form.addWidget(label_widget, row * 2, column * 2, 1, 2)
            form.addWidget(widget, row * 2 + 1, column * 2, 1, 2)
            return label_widget

        def line(placeholder=""):
            widget = QLineEdit()
            widget.setPlaceholderText(placeholder)
            widget.setMinimumHeight(27)
            widget.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
            return widget

        self.cmb_mode = QComboBox()
        self.cmb_mode.setProperty("referenceGlyph", "chevron_down")
        self.cmb_mode.addItem("Pasif", "disabled")
        self.cmb_mode.addItem("Cloud API (Meta)", "cloud_api")
        self.cmb_mode.addItem("Saglayici API (Twilio/BSP)", "provider_api")
        self.cmb_mode.addItem("WhatsApp Desktop (Kullanici Onayi)", "desktop_manual")
        self.cmb_mode.setMinimumHeight(27)
        self.cmb_mode.setStyleSheet(theme_qss(DesignTokens.get_combobox_qss()))
        header = QWidget()
        header.setStyleSheet("background: transparent;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 6)
        header_layout.setSpacing(12)
        protocol_mark = QLabel("WA")
        protocol_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        protocol_mark.setFixedSize(32, 32)
        protocol_mark.setStyleSheet(theme_qss(
            "background: @finance_success_bg; color: @finance_secondary; border-radius: 10px; "
            "font-size: 14px; font-weight: 800; border: none;"
        ))
        header_text = QVBoxLayout()
        protocol_title = QLabel("WhatsApp Meta Cloud API Protokolu")
        protocol_title.setWordWrap(True)
        protocol_title.setStyleSheet(theme_qss("color: @text; font-size: 12px; font-weight: 800; border: none;"))
        protocol_description = QLabel("Kurumsal API kimlik dogrulamasi ve otomatik hatirlatma parametreleri")
        protocol_description.setWordWrap(True)
        protocol_description.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px; border: none;"))
        header_text.addWidget(protocol_title)
        header_text.addWidget(protocol_description)
        header_layout.addWidget(protocol_mark)
        header_layout.addLayout(header_text, 1)
        version_badge = QLabel("Canli baglanti" if whatsapp_configured else "Kurulum bekliyor")
        version_badge.setStyleSheet(theme_qss(
            "color: @finance_secondary; background: @finance_success_bg; border: 1px solid @border; "
            "border-radius: 6px; padding: 6px 10px; font-size: 11px;"
            if whatsapp_configured else
            "color: @text_muted; background: @surface_alt; border: 1px solid @border; "
            "border-radius: 6px; padding: 6px 10px; font-size: 11px;"
        ))
        header_layout.addWidget(version_badge, 0, Qt.AlignmentFlag.AlignTop)
        form.addWidget(header, 0, 0, 1, 4)
        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(theme_qss("background: @border; border: none;"))
        form.addWidget(divider, 1, 0, 1, 4)
        protocol_modes = QWidget(card)
        protocol_modes.setStyleSheet("background: transparent;")
        protocol_modes_layout = QHBoxLayout(protocol_modes)
        protocol_modes_layout.setContentsMargins(0, 0, 0, 0)
        protocol_modes_layout.setSpacing(5)
        self.protocol_mode_buttons = []
        for label, mode_value in (("Meta Cloud API", "cloud_api"), ("WA Desktop", "desktop_manual"), ("Twilio API", "provider_api")):
            mode_button = QPushButton(label)
            mode_button.setCheckable(True)
            mode_button.setMinimumHeight(28)
            mode_button.setStyleSheet(
                "QPushButton { background: #0b1322; color: #94a3b8; border: 1px solid #1e2e4a; border-radius: 5px; padding: 4px 8px; font-size: 10px; } "
                "QPushButton:checked { background: #102a28; color: #25d366; border-color: #10b981; font-weight: 700; }"
            )
            mode_button.clicked.connect(
                lambda _checked=False, value=mode_value: self.cmb_mode.setCurrentIndex(self.cmb_mode.findData(value))
            )
            protocol_modes_layout.addWidget(mode_button, 1)
            self.protocol_mode_buttons.append((mode_value, mode_button))
        form.removeWidget(divider)
        form.addWidget(protocol_modes, 1, 0, 1, 4)
        self._protocol_mode_bar = protocol_modes
        form.setRowMinimumHeight(1, 32)
        self.inp_phone = line("905XXXXXXXXX")
        self._mode_label = add_field("Gonderim modu", self.cmb_mode, 1, 0)
        self._phone_label = add_field("Isletme numarasi", self.inp_phone, 1, 1)
        self.inp_cloud_phone_id = line("Meta phone number ID")
        self._cloud_phone_id_label = add_field("Cloud phone ID", self.inp_cloud_phone_id, 2, 0)
        self.inp_cloud_token = line("Meta access token")
        self.inp_cloud_token.setEchoMode(QLineEdit.EchoMode.Password)
        self._cloud_token_label = add_field("Cloud access token", self.inp_cloud_token, 2, 1)
        token_row = QWidget()
        token_row.setStyleSheet("background: transparent;")
        token_row_layout = QHBoxLayout(token_row)
        token_row_layout.setContentsMargins(0, 0, 0, 0)
        token_row_layout.setSpacing(6)
        form.removeWidget(self.inp_cloud_token)
        token_row_layout.addWidget(self.inp_cloud_token, 1)
        self._cloud_token_reveal_button = QPushButton("Goster")
        self._cloud_token_reveal_button.setFixedWidth(54)
        self._cloud_token_reveal_button.setStyleSheet(theme_qss(
            "color: @text_muted; background: @surface_alt; border: 1px solid @border; "
            "border-radius: 5px; padding: 2px 4px; font-size: 9px;"
        ))
        self._cloud_token_reveal_button.clicked.connect(self._toggle_cloud_token_visibility)
        token_row_layout.addWidget(self._cloud_token_reveal_button)
        self.inp_cloud_template = line("payment_reminder_tr")
        self.inp_cloud_template.setMaximumWidth(170)
        self.inp_provider_sid = line("Twilio Account SID")
        provider_sid_label = add_field("Saglayici Account SID", self.inp_provider_sid, 3, 1)
        self.inp_provider_token = line("Twilio Auth Token")
        self.inp_provider_token.setEchoMode(QLineEdit.EchoMode.Password)
        provider_token_label = add_field("Saglayici Auth Token", self.inp_provider_token, 4, 0)
        self.inp_provider_from = line("whatsapp:+905XXXXXXXXX")
        provider_from_label = add_field("Saglayici gonderici", self.inp_provider_from, 4, 1)
        self._provider_fields = (
            (provider_sid_label, self.inp_provider_sid),
            (provider_token_label, self.inp_provider_token),
            (provider_from_label, self.inp_provider_from),
        )
        self.inp_template = QTextEdit()
        self.inp_template.setPlaceholderText(
            "Merhaba {musteri_adi}, {firma_adi} hesabinizda {borc_tutari} TRY borc bulunuyor."
        )
        self.inp_template.setFixedHeight(52)
        self.inp_template.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self._template_label = add_field("Odeme sablonu", self.inp_template, 5, 0)
        form.removeWidget(self._template_label)
        self._template_label.hide()
        form.addWidget(self.inp_template, 11, 0, 1, 4)
        policy_note = QFrame(card)
        policy_note.setStyleSheet(
            "QFrame { background: #0b1c35; border: 1px solid #1e3a63; border-radius: 6px; }"
        )
        policy_layout = QHBoxLayout(policy_note)
        policy_layout.setContentsMargins(8, 5, 8, 5)
        policy_layout.setSpacing(7)
        policy_icon = QLabel("i")
        policy_icon.setStyleSheet("color: #60a5fa; font-weight: 800; border: none;")
        policy_text = QLabel(
            "Meta Cloud API icin onayli sablonlar gerekir. 24 saat disinda onayli sablon kullanin."
        )
        policy_text.setWordWrap(True)
        policy_text.setStyleSheet("color: #93c5fd; font-size: 9px; border: none;")
        policy_layout.addWidget(policy_icon)
        policy_layout.addWidget(policy_text, 1)
        form.addWidget(policy_note, 12, 0, 1, 4)

        def place_field(label_widget, field_widget, row, column, span=2):
            form.removeWidget(label_widget)
            form.removeWidget(field_widget)
            form.addWidget(label_widget, row, column, 1, span)
            form.addWidget(field_widget, row + 1, column, 1, span)

        self._mode_label.hide()
        self.cmb_mode.hide()
        place_field(self._phone_label, self.inp_phone, 2, 0)
        place_field(self._cloud_phone_id_label, self.inp_cloud_phone_id, 2, 2)
        place_field(self._cloud_token_label, token_row, 4, 0, 4)
        place_field(provider_sid_label, self.inp_provider_sid, 6, 0)
        place_field(provider_token_label, self.inp_provider_token, 6, 2)
        place_field(provider_from_label, self.inp_provider_from, 8, 0, 4)
        token_toolbar = QWidget()
        token_toolbar.setStyleSheet("background: transparent;")
        token_toolbar_layout = QHBoxLayout(token_toolbar)
        token_toolbar_layout.setContentsMargins(0, 0, 0, 0)
        token_toolbar_layout.setSpacing(6)
        token_names = (
            ("Musteri adi", "{musteri_adi}"), ("Firma adi", "{firma_adi}"),
            ("Borc tutari", "{borc_tutari}"), ("Takip no", "{takip_no}"),
            ("Cihaz modeli", "{cihaz_model}"), ("Teslim tarihi", "{teslim_tarihi}"),
        )
        for label, token in token_names:
            token_button = QPushButton(f"+ {label}")
            token_button.setMinimumHeight(24)
            token_button.setStyleSheet(theme_qss("color: @text_muted; background: @surface_alt; border: 1px solid @border; border-radius: 5px; padding: 3px 6px; font-size: 9px;"))
            token_button.clicked.connect(lambda checked=False, value=token: self.inp_template.insertPlainText(value))
            token_toolbar_layout.addWidget(token_button)
        template_meta = QWidget()
        template_meta.setStyleSheet("background: transparent;")
        template_meta_layout = QHBoxLayout(template_meta)
        template_meta_layout.setContentsMargins(0, 0, 0, 0)
        template_meta_layout.setSpacing(6)
        template_meta_layout.addWidget(QLabel("Odeme sablonu"))
        template_meta_layout.addWidget(self.inp_cloud_template, 1)
        form.addWidget(template_meta, 10, 0, 1, 2)
        form.addWidget(token_toolbar, 10, 2, 1, 2)
        form.setRowMinimumHeight(10, 36)
        preview_card = QFrame()
        self._template_preview_card = preview_card
        preview_card.setStyleSheet(theme_qss("QFrame { background: #131e32; border: 1px solid #1e2e4a; border-radius: 10px; }"))
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(10, 8, 10, 8)
        preview_layout.setSpacing(4)
        preview_title = QLabel("Canli Sablon Onizlemesi")
        preview_title.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px; font-weight: 800; border: none;"))
        self.template_preview = QLabel()
        self.template_preview.setWordWrap(True)
        self.template_preview.setMinimumHeight(58)
        self.template_preview.setStyleSheet(
            "color: #e2e8f0; background: #075e54; border: 1px solid #128c7e; "
            "border-radius: 7px; padding: 9px; font-size: 10px;"
        )
        preview_layout.addWidget(preview_title)
        preview_layout.addWidget(self.template_preview)
        form.addWidget(preview_card, 12, 0, 1, 4)
        form.setRowMinimumHeight(12, 56)
        self.inp_template.textChanged.connect(self._update_template_preview)
        self.chk_reminder = QCheckBox("Haftalik borc odeme hatirlatmasini etkinlestir")
        self.chk_reminder.setStyleSheet(theme_qss("QCheckBox { color: @text; font-weight: 700; border: none; background: transparent; }"))
        reminder_card = QFrame()
        self._reminder_card = reminder_card
        reminder_card.setObjectName("WhatsAppReminderCard")
        reminder_card.setStyleSheet(theme_qss(
            "QFrame#WhatsAppReminderCard { background: #131e32; border: 1px solid #1e2e4a; border-radius: 10px; }"
        ))
        reminder_card.setMinimumHeight(88)
        reminder_layout = QGridLayout(reminder_card)
        reminder_layout.setContentsMargins(8, 6, 8, 6)
        reminder_layout.setHorizontalSpacing(12)
        reminder_layout.setVerticalSpacing(5)
        reminder_layout.addWidget(self.chk_reminder, 0, 0, 1, 4)
        self.cmb_day = QComboBox()
        self.cmb_day.setProperty("referenceGlyph", "chevron_down")
        for day, value in (("Pazartesi", 0), ("Sali", 1), ("Carsamba", 2), ("Persembe", 3), ("Cuma", 4), ("Cumartesi", 5), ("Pazar", 6)):
            self.cmb_day.addItem(day, value)
        self.cmb_day.setMinimumHeight(27)
        self.time_reminder = QTimeEdit(QTime(10, 0))
        self.time_reminder.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.time_reminder.setDisplayFormat("HH:mm")
        self.time_reminder.setMinimumHeight(27)
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
        self.spin_min_debt.setMinimumHeight(27)
        self.spin_min_debt.setStyleSheet(theme_qss(
            "QSpinBox { background: @surface_alt; color: @text; border: 1px solid @border; "
            "border-radius: 8px; padding: 6px 10px; min-height: 34px; } "
            "QSpinBox::up-button, QSpinBox::down-button { width: 0; height: 0; border: 0; }"
        ))
        self._min_debt_label = add_field("Asgari borc", self.spin_min_debt, 15, 0)
        reminder_layout.removeWidget(self.chk_reminder)
        form.removeWidget(self._min_debt_label)
        form.removeWidget(self.spin_min_debt)
        self._min_debt_label.hide()
        reminder_layout.addWidget(self._min_debt_label, 1, 4, 1, 2)
        reminder_layout.addWidget(self.spin_min_debt, 2, 4, 1, 2)
        self._min_debt_label.show()
        reminder_layout.addWidget(self.chk_reminder, 0, 0, 1, 6)
        actions = QWidget()
        actions.setStyleSheet("background: transparent;")
        actions_layout = QHBoxLayout(actions)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(8)
        actions_layout.addStretch(1)
        self.btn_test_message = QPushButton("Test Mesaji Gonder")
        self.btn_test_message.setFixedHeight(30)
        self.btn_test_message.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="md")))
        self.btn_test_message.clicked.connect(self._send_test_message)
        actions_layout.addWidget(self.btn_test_message)
        btn_save = QPushButton("AYARLARI KAYDET")
        btn_save.setFixedHeight(30)
        btn_save.setObjectName("whatsapp_settings_save")
        btn_save.setStyleSheet(theme_qss(DesignTokens.get_button_qss("success", size="md")))
        btn_save.clicked.connect(self.save_data)
        actions_layout.addWidget(btn_save)
        form.addWidget(actions, 13, 0, 1, 4)
        columns = QHBoxLayout()
        columns.setSpacing(14)
        main_column = QWidget()
        main_column_layout = QVBoxLayout(main_column)
        main_column_layout.setContentsMargins(0, 0, 0, 0)
        main_column_layout.setSpacing(12)
        main_column_layout.addWidget(card)
        side_column = QWidget()
        side_column.setMinimumWidth(0)
        side_column.setMaximumWidth(390)
        side_column_layout = QVBoxLayout(side_column)
        side_column_layout.setContentsMargins(0, 0, 0, 0)
        side_column_layout.setSpacing(24)
        side = QFrame()
        side.setMinimumWidth(0)
        side.setStyleSheet(theme_qss("QFrame { background: #0b1220; border: 1px solid #1e2b42; border-radius: 10px; }"))
        side.setMinimumHeight(0)
        side_layout = QGridLayout(side)
        side_layout.setContentsMargins(10, 10, 10, 10)
        side_layout.setHorizontalSpacing(6)
        side_layout.setVerticalSpacing(6)
        side_header = QHBoxLayout()
        bot_mark = QLabel("TG")
        bot_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bot_mark.setFixedSize(28, 28)
        bot_mark.setStyleSheet(theme_qss("background: @finance_surface_high; color: @finance_secondary; border-radius: 9px; font-weight: 800; border: none;"))
        side_title = QLabel("Telegram ve AI Masasi")
        side_title.setWordWrap(True)
        side_title.setStyleSheet(theme_qss("color: @text; font-size: 13px; font-weight: 800; border: none;"))
        telegram_token = str(SecureSettingStore.get(self.db, "telegram_bot_token", "") or "").strip()
        telegram_username = str(self.db.get_setting("telegram_bot_username", "") or "").strip()
        telegram_chat_ids_raw = str(self.db.get_setting("telegram_chat_ids", "") or "").strip()
        try:
            chat_id_values = json.loads(telegram_chat_ids_raw or "[]")
            telegram_chat_ids = ", ".join(str(value) for value in chat_id_values) if isinstance(chat_id_values, list) else str(chat_id_values)
        except (TypeError, ValueError):
            telegram_chat_ids = telegram_chat_ids_raw
        side_status = QLabel("\u25cf Hazir" if telegram_token else "\u25cf Kurulum bekliyor")
        side_status.setWordWrap(True)
        side_status.setMaximumWidth(94)
        side_status.setStyleSheet(theme_qss(
            "color: @finance_secondary; font-weight: 700; border: none;"
            if telegram_token else "color: @text_muted; font-weight: 700; border: none;"
        ))
        side_header.addWidget(bot_mark)
        side_header.addWidget(side_title, 1)
        side_header.addWidget(side_status)
        side_layout.addLayout(side_header, 0, 0, 1, 2)
        bot_card = QFrame()
        bot_card.setStyleSheet(theme_qss("QFrame { background: @surface_alt; border: 1px solid @border; border-radius: 10px; }"))
        bot_card.setMinimumHeight(42)
        bot_layout = QHBoxLayout(bot_card)
        bot_layout.setContentsMargins(7, 5, 7, 5)
        bot_info = QVBoxLayout()
        bot_name = QLabel(telegram_username or "Telegram Bot")
        bot_name.setStyleSheet(theme_qss("color: @text; font-weight: 800; border: none;"))
        bot_handle = QLabel("@" + telegram_username.lstrip("@") if telegram_username else "Baglanti testi sonrasi bot bilgisi gosterilir")
        bot_handle.setWordWrap(True)
        bot_handle.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; border: none;"))
        bot_info.addWidget(bot_name)
        bot_info.addWidget(bot_handle)
        live_badge = QLabel("Bagli" if telegram_token else "Kurulum")
        live_badge.setStyleSheet(theme_qss("color: @text; background: @surface; border: 1px solid @border; border-radius: 6px; padding: 6px 10px;"))
        bot_layout.addLayout(bot_info, 1)
        bot_layout.addWidget(live_badge)
        side_layout.addWidget(bot_card, 1, 0, 1, 2)
        self.telegram_settings_button = QPushButton("Telegram ayarlarini ac")
        self.telegram_settings_button.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        self.telegram_settings_button.setFixedHeight(28)
        self.telegram_settings_button.clicked.connect(lambda: self._navigate_to_settings_page(16))
        side_layout.addWidget(self.telegram_settings_button, 2, 0, 1, 2)
        token_summary = "Kayitli" if telegram_token else "Token gerekli"
        chat_summary = telegram_chat_ids or "Chat ID eklenmedi"
        for box_index, (label, value) in enumerate((("Bot API Token", token_summary), ("Bagli Teknisyen Grup Chat ID", chat_summary))):
            box = QFrame()
            box.setMinimumHeight(38)
            box.setStyleSheet(theme_qss("background: @surface_alt; border: 1px solid @border; border-radius: 8px;"))
            box_layout = QVBoxLayout(box)
            box_layout.setContentsMargins(7, 4, 7, 4)
            cap = QLabel(label)
            cap.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px; border: none;"))
            val = QLabel(value)
            val.setWordWrap(True)
            val.setStyleSheet(theme_qss("color: @text; font-weight: 700; border: none;"))
            box_layout.addWidget(cap)
            box_layout.addWidget(val)
            side_layout.addWidget(box, 3, box_index)
        command_box = QFrame()
        command_box.setStyleSheet(theme_qss("QFrame { background: @surface_alt; border: 1px solid @border; border-radius: 8px; }"))
        command_layout = QVBoxLayout(command_box)
        command_layout.setContentsMargins(7, 5, 7, 5)
        command_caption = QLabel("Hizli Notlar & Makro Cipleri")
        command_caption.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; border: none;"))
        command_header = QHBoxLayout()
        command_open = QPushButton("Notlari ac")
        self.quick_notes_settings_button = command_open
        command_open.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        command_open.clicked.connect(lambda: self._navigate_to_settings_page(14))
        command_header.addWidget(command_caption, 1)
        command_header.addWidget(command_open)
        command_layout.addLayout(command_header)
        command_tags = QGridLayout()
        command_tags.setHorizontalSpacing(6)
        command_tags.setVerticalSpacing(6)
        command_box.setMinimumHeight(54)
        notes_getter = getattr(self.db, "get_fast_notes", None)
        quick_notes = [row for row in (notes_getter() or []) if len(row) > 3 and row[3] == 1][:4] if callable(notes_getter) else []
        for index, note in enumerate(quick_notes):
            tag = QPushButton(str(note[1]))
            tag.setStyleSheet(theme_qss("color: @finance_secondary; background: @surface; border: 1px solid @border; border-radius: 6px; padding: 7px 5px; font-size: 10px; text-align: center;"))
            tag.clicked.connect(lambda _checked=False: self._navigate_to_settings_page(14))
            command_tags.addWidget(tag, index // 2, index % 2)
        if not quick_notes:
            empty_notes = QLabel("Etkin hizli not bulunamadi")
            empty_notes.setStyleSheet(theme_qss("color: @text_muted; border: none; font-size: 11px;"))
            command_tags.addWidget(empty_notes, 0, 0, 1, 2)
        command_layout.addLayout(command_tags)
        side_layout.addWidget(command_box, 4, 0, 1, 2)
        ai_card = QFrame()
        ai_card.setStyleSheet(theme_qss("QFrame { background: @surface_alt; border: 1px solid @border; border-radius: 8px; }"))
        ai_layout = QHBoxLayout(ai_card)
        ai_layout.setContentsMargins(7, 5, 7, 5)
        ai_description = QLabel("AYEC AI Core: Hazir" if ai_configured else "AYEC AI Core: Anahtar gerekli")
        ai_description.setStyleSheet(theme_qss(
            "color: @finance_secondary; border: none; font-weight: 700;"
            if ai_configured else "color: @text_muted; border: none; font-weight: 700;"
        ))
        ai_button = QPushButton("AI ayarlari")
        self.ai_settings_button = ai_button
        ai_button.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        ai_button.clicked.connect(lambda: self._navigate_to_settings_page(13))
        ai_layout.addWidget(ai_description, 1)
        ai_layout.addWidget(ai_button)
        side_layout.addWidget(ai_card, 5, 0, 1, 2)
        support = QFrame()
        support.setStyleSheet(theme_qss(
            "QFrame { background: @surface_alt; border: 1px solid @border; border-radius: 12px; }"
        ))
        support_layout = QVBoxLayout(support)
        support_layout.setContentsMargins(10, 8, 10, 8)
        support.setMinimumHeight(66)
        support_title = QLabel("Kargo Otomasyonu")
        support_title.setStyleSheet(theme_qss("color: @text; font-weight: 800; border: none;"))
        cargo_company = str(self.db.get_setting("cargo_default_company", "Yurtici") or "Yurtici")
        cargo_sender = str(self.db.get_setting("cargo_sender_name", "") or "-")
        cargo_branch = str(self.db.get_setting("cargo_branch_code", "") or "-")
        cargo_tracking = str(self.db.get_setting("cargo_auto_track", "1")) == "1"
        support_copy = QLabel(
            f"Varsayilan tasiyici: {cargo_company}\n"
            f"Gonderici: {cargo_sender}  |  Sube: {cargo_branch}\n"
            f"Otomatik takip: {'Acik' if cargo_tracking else 'Kapali'}"
        )
        support_copy.setWordWrap(True)
        support_copy.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px; border: none;"))
        support_layout.addWidget(support_title)
        support_layout.addWidget(support_copy)
        cargo_button = QPushButton("Kargo ayarlarini ac")
        self.cargo_settings_button = cargo_button
        cargo_button.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        cargo_button.clicked.connect(lambda: self._navigate_to_settings_page(5))
        support_layout.addWidget(cargo_button)
        side_column_layout.addWidget(side)
        side_column_layout.addWidget(support)
        side_column_layout.addStretch(1)
        sms_card = QFrame()
        self._sms_notification_card = sms_card
        sms_card.setStyleSheet(theme_qss("QFrame { background: #131e32; border: 1px solid #1e2e4a; border-radius: 10px; }"))
        sms_layout = QVBoxLayout(sms_card)
        sms_layout.setContentsMargins(12, 8, 12, 8)
        sms_layout.setSpacing(8)
        sms_header = QHBoxLayout()
        sms_title = QLabel("SMS Ag Gecidi & Servis Donguleri")
        sms_title.setStyleSheet(theme_qss("color: @text; font-size: 12px; font-weight: 800; border: none;"))
        sms_state = QLabel("Aktif" if sms_active else "Pasif")
        sms_state.setStyleSheet(theme_qss(
            "color: @finance_secondary; font-weight: 700; border: none;"
            if sms_active else "color: @text_muted; font-weight: 700; border: none;"
        ))
        sms_header.addWidget(sms_title, 1)
        sms_header.addWidget(sms_state)
        sms_layout.addLayout(sms_header)
        sms_grid = QGridLayout()
        sms_grid.setHorizontalSpacing(12)
        sms_grid.setVerticalSpacing(4)
        matrix_headers = ("Servis durumu", "WhatsApp", "SMS yedek", "Tekrar", "Meta HSM sablonu", "Durum")
        for column, label in enumerate(matrix_headers):
            heading = QLabel(label)
            heading.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px; font-weight: 700; border: none;"))
            sms_grid.addWidget(heading, 0, column)
        for row_index, (label, key, interval, template) in enumerate((
            ("Onarim tamamlandi", "loop_repaired", "1 Gun", "repair_done_notify"),
            ("Musteri onayi bekleniyor", "loop_approval", "2 Gun", "approval_pending"),
            ("Parca bekleniyor", "loop_parts", "3 Gun", "part_waiting_info"),
            ("Test asamasinda", "loop_testing", "0 (Anlik)", "testing_stage"),
            ("Teslime hazir", "loop_done", "1 Gun", "ready_for_pickup"),
        ), start=1):
            stage = QLabel(label)
            wa_state = QLabel("\u2713")
            wa_state.setAlignment(Qt.AlignmentFlag.AlignCenter)
            wa_state.setStyleSheet("color: #25d366; font-weight: 800;")
            sms_state = QLabel("\u2713" if sms_active else "\u2014")
            sms_state.setAlignment(Qt.AlignmentFlag.AlignCenter)
            sms_state.setStyleSheet("color: #06b6d4; font-weight: 800;" if sms_active else "color: #64748b;")
            count = QLabel(str(self.db.get_setting(key, interval) or interval))
            count.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hsm = QLabel(template)
            hsm.setStyleSheet("color: #a9bad3; font-family: 'JetBrains Mono'; font-size: 9px;")
            state = QCheckBox()
            state.setChecked(str(self.db.get_setting("loop_active_" + key.removeprefix("loop_"), "1")) != "0")
            state.setStyleSheet("QCheckBox::indicator { width: 12px; height: 12px; border-radius: 6px; } QCheckBox::indicator:checked { background: #10b981; border: 1px solid #10b981; } QCheckBox::indicator:unchecked { background: #334155; border: 1px solid #475569; }")
            state.toggled.connect(lambda enabled, setting_key="loop_active_" + key.removeprefix("loop_"): self.db.set_setting(setting_key, "1" if enabled else "0"))
            sms_grid.addWidget(stage, row_index, 0)
            sms_grid.addWidget(wa_state, row_index, 1)
            sms_grid.addWidget(sms_state, row_index, 2)
            sms_grid.addWidget(count, row_index, 3)
            sms_grid.addWidget(hsm, row_index, 4)
            sms_grid.addWidget(state, row_index, 5, alignment=Qt.AlignmentFlag.AlignRight)
        sms_layout.addLayout(sms_grid)
        sms_button = QPushButton("SMS ayarlarini ac")
        self.sms_settings_button = sms_button
        sms_button.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        sms_button.clicked.connect(lambda: self._navigate_to_settings_page(3))
        sms_layout.addWidget(sms_button, 0, Qt.AlignmentFlag.AlignRight)
        main_column_layout.addWidget(sms_card)
        columns.addWidget(main_column, 2)
        columns.addWidget(side_column, 1)
        columns.setAlignment(side_column, Qt.AlignmentFlag.AlignTop)
        self._columns_layout = columns
        layout.addLayout(columns)

        # Move the existing form widgets into the reference two-column structure.
        layout.removeItem(columns)
        summary.show()
        notice.show()
        form.removeWidget(self._template_preview_card)
        form.removeWidget(self._reminder_card)

        reference_body = QWidget(content)
        reference_columns = QHBoxLayout(reference_body)
        reference_columns.setContentsMargins(0, 0, 0, 0)
        reference_columns.setSpacing(12)
        reference_columns.setAlignment(Qt.AlignmentFlag.AlignTop)
        gateway_column = QWidget(reference_body)
        gateway_layout = QVBoxLayout(gateway_column)
        gateway_layout.setContentsMargins(0, 0, 0, 0)
        gateway_layout.setSpacing(10)
        notification_column = QWidget(reference_body)
        notification_layout = QVBoxLayout(notification_column)
        notification_layout.setContentsMargins(0, 0, 0, 0)
        notification_layout.setSpacing(10)

        main_column_layout.removeWidget(card)
        main_column_layout.removeWidget(sms_card)
        side_column_layout.removeWidget(side)
        side_column_layout.removeWidget(support)

        for widget in (card, self._template_preview_card):
            widget.setParent(gateway_column)
            widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
            gateway_layout.addWidget(widget)
        for widget in (sms_card, self._reminder_card, side, support):
            widget.setParent(notification_column)
            widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
            notification_layout.addWidget(widget)
        notification_layout.addStretch(1)
        reference_columns.addWidget(gateway_column, 5)
        reference_columns.addWidget(notification_column, 7)
        reference_columns.setAlignment(gateway_column, Qt.AlignmentFlag.AlignTop)
        reference_columns.setAlignment(notification_column, Qt.AlignmentFlag.AlignTop)
        side_layout.removeWidget(command_box)
        side_layout.removeWidget(ai_card)
        addons = QWidget(notification_column)
        addons_grid = QGridLayout(addons)
        addons_grid.setContentsMargins(0, 0, 0, 0)
        addons_grid.setHorizontalSpacing(9)
        addons_grid.setVerticalSpacing(9)
        notification_layout.removeWidget(side)
        notification_layout.removeWidget(support)
        for index, addon in enumerate((support, side, command_box, ai_card)):
            addon.setParent(addons)
            addon.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
            addons_grid.addWidget(addon, index // 2, index % 2)
            addon.show()
        notification_layout.addWidget(addons)
        form.removeWidget(actions)
        actions.setParent(content)
        actions.setStyleSheet(theme_qss(
            "background: @surface; border-top: 1px solid @border;"
        ))
        actions_layout.setContentsMargins(8, 6, 8, 6)
        main_column.hide()
        side_column.hide()
        self._legacy_columns_layout = columns
        self._legacy_main_column = main_column
        self._legacy_side_column = side_column
        self._columns_layout = reference_columns
        layout.addWidget(reference_body, 1)
        layout.addWidget(actions)


    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_responsive_layout()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._fit_responsive_layout)

    def _fit_responsive_layout(self):
        scroll = getattr(self, "_settings_scroll", None)
        content = getattr(self, "_settings_content", None)
        if scroll is not None and content is not None:
            viewport_width = max(0, scroll.viewport().width())
            content.setMinimumWidth(viewport_width)
            content.setMaximumWidth(viewport_width)
        summary_layout = getattr(self, "_summary_layout", None)
        if summary_layout is not None:
            columns = 1 if self.width() < 520 else 2 if self.width() < 900 else 4
            for index, card in enumerate(getattr(self, "_summary_cards", ())):
                summary_layout.removeWidget(card)
                summary_layout.addWidget(card, index // columns, index % columns)
            for column in range(4):
                summary_layout.setColumnStretch(column, 1 if column < columns else 0)
            rows = (len(getattr(self, "_summary_cards", ())) + columns - 1) // columns
            summary = getattr(self, "_summary_cards", ())[0].parentWidget()
            summary.setMaximumHeight(rows * 66 + max(0, rows - 1) * 8)
        compact_tabs = self.width() < 1100
        tab_width = 70 if self.width() < 700 else 110 if compact_tabs else 145
        tab_height = 64 if self.width() < 700 else 52
        for button in getattr(self, "integration_nav_buttons", ()):
            button.setMinimumSize(tab_width, tab_height)
        selector = getattr(self, "_settings_page_selector", None)
        selector_width = 160 if compact_tabs else 260
        if selector is not None:
            selector.setMaximumWidth(selector_width)
        tabs_content = getattr(self, "_integration_tabs_content", None)
        if tabs_content is not None:
            minimum_tabs_width = (
                len(getattr(self, "integration_nav_buttons", ())) * tab_width
                + max(0, len(getattr(self, "integration_nav_buttons", ())) - 1) * 6
                + (selector_width + 6 if selector is not None else 0)
            )
            tabs_content.setMinimumWidth(minimum_tabs_width)
            tabs_content.setMaximumWidth(max(minimum_tabs_width, self.width() - 16))
            tabs_content.resize(max(minimum_tabs_width, self.width() - 16), tabs_content.height())
        for card in getattr(self, "_summary_cards", ()):
            if self.width() < 520:
                card.setMaximumWidth(max(180, self.width() - 24))
            else:
                card.setMaximumWidth(280 if self.width() < 1160 else 360)
        columns = getattr(self, "_columns_layout", None)
        if columns is None:
            return
        if self.width() < 900:
            columns.setDirection(QBoxLayout.Direction.TopToBottom)
            columns.setStretch(0, 0)
            columns.setStretch(1, 0)
        else:
            columns.setDirection(QBoxLayout.Direction.LeftToRight)
            columns.setStretch(0, 5)
            columns.setStretch(1, 7)

    def _wire_ui_signals(self):
        self.cmb_mode.currentIndexChanged.connect(self.save_data)
        self.cmb_mode.currentIndexChanged.connect(self._update_provider_field_visibility)
        self.cmb_mode.currentIndexChanged.connect(self._update_protocol_mode_buttons)
        self.inp_cloud_template.textChanged.connect(self._refresh_whatsapp_summary)
        self.inp_cloud_token.textChanged.connect(self._refresh_whatsapp_summary)
        self.inp_provider_token.textChanged.connect(self._refresh_whatsapp_summary)
        self.inp_template.textChanged.connect(self._refresh_whatsapp_summary)
        self.chk_reminder.toggled.connect(self._refresh_whatsapp_summary)

    def _update_protocol_mode_buttons(self, *_args):
        current_mode = self.cmb_mode.currentData()
        for mode_value, button in getattr(self, "protocol_mode_buttons", ()):
            button.setChecked(mode_value == current_mode)

    def _toggle_cloud_token_visibility(self):
        visible = self.inp_cloud_token.echoMode() == QLineEdit.EchoMode.Password
        self.inp_cloud_token.setEchoMode(
            QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password
        )
        self._cloud_token_reveal_button.setText("Gizle" if visible else "Goster")

    def _send_test_message(self):
        from src.services.whatsapp_service import WhatsAppService
        from src.utils.toast_notification import show_error, show_success, show_warning

        mode = str(self.cmb_mode.currentData() or "disabled")
        if mode in {"disabled", "desktop_manual"}:
            show_warning(self, "Test mesaji icin Cloud API veya saglayici modunu secin.")
            return
        target = str(
            self.db.get_setting("whatsapp_admin_phone", "")
            or self.db.get_setting("admin_whatsapp", "")
            or ""
        ).strip()
        if not target:
            show_warning(self, "Test mesaji icin yonetici WhatsApp numarasi gerekli.")
            return
        company = str(self.db.get_setting("company_name", "AYEC Pro") or "AYEC Pro")
        message = WhatsAppService(self.db).render_template(
            self.inp_template.toPlainText(),
            {"musteri_adi": "Test", "firma_adi": company, "borc_tutari": "0.00"},
        )
        values = ["Test", company, "0.00"]
        try:
            result = WhatsAppService(self.db).send(
                target,
                message,
                self.inp_cloud_template.text().strip(),
                values,
            )
            if result.get("ok"):
                show_success(self, "Test mesaji gonderildi.")
            else:
                show_error(self, "Test mesaji gonderilemedi.")
        except Exception as error:
            show_error(self, str(error))

    def _update_provider_field_visibility(self, *_args):
        provider_mode = self.cmb_mode.currentData() == "provider_api"
        for label, widget in getattr(self, "_provider_fields", ()):
            label.setVisible(True)
            widget.setVisible(True)
            label.setEnabled(provider_mode)
            widget.setEnabled(provider_mode)

    def _update_template_preview(self):
        text = self.inp_template.toPlainText().strip()
        values = {
            "{musteri_adi}": "Ornek Musteri",
            "{firma_adi}": str(self.db.get_setting("company_name", "AYEC Pro") or "AYEC Pro"),
            "{borc_tutari}": "500.00",
        }
        for token, value in values.items():
            text = text.replace(token, value)
        self.template_preview.setText(text or "Sablon metni bos.")

    def _is_whatsapp_configured(self):
        mode = str(self.db.get_setting("whatsapp_mode", "disabled") or "disabled")
        return (
            mode == "cloud_api"
            and bool(self.db.get_setting("whatsapp_cloud_phone_id", ""))
            and bool(SecureSettingStore.get(self.db, "whatsapp_cloud_token", ""))
        ) or (
            mode == "provider_api"
            and bool(self.db.get_setting("twilio_account_sid", ""))
            and bool(SecureSettingStore.get(self.db, "twilio_auth_token", ""))
            and bool(self.db.get_setting("twilio_whatsapp_from", ""))
        ) or (mode == "desktop_manual" and bool(self.db.get_setting("whatsapp_number", "")))

    def _refresh_whatsapp_summary(self):
        if not getattr(self, "_summary_status_values", None):
            return
        configured = self._is_whatsapp_configured()
        self._summary_note_values[0].setText("Aktif" if configured else "Kurulum gerekli")
        self._summary_note_values[0].setStyleSheet(theme_qss(
            "color: @finance_secondary; border: none; font-size: 10px; font-weight: 700;"
            if configured else "color: @text_muted; border: none; font-size: 10px; font-weight: 700;"
        ))
        template_ready = bool(self.inp_cloud_template.text().strip() or self.inp_template.toPlainText().strip())
        self._summary_status_values[1].setText("HAZIR" if template_ready else "BEKLIYOR")
        token_ready = bool(self.inp_cloud_token.text().strip() or self.inp_provider_token.text().strip())
        self._summary_status_values[2].setText("TOKEN KORUMALI" if token_ready else "TOKEN EKLENMEDI")
        reminder_active = self.chk_reminder.isChecked()
        self._summary_status_values[3].setText("PLANLI CRON" if reminder_active else "KAPALI")

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

    def attach_settings_page_selector(self, selector):
        if self._settings_page_selector is selector:
            return
        if self._settings_page_selector is not None:
            self._integration_tabs_layout.removeWidget(self._settings_page_selector)
        selector.setMaximumWidth(260)
        selector.setFixedHeight(32)
        selector.setToolTip("Select a settings section")
        selector.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self._integration_tabs_layout.addWidget(selector, 0)
        selector.setVisible(True)
        self._settings_page_selector = selector

    def detach_settings_page_selector(self, selector):
        if self._settings_page_selector is not selector:
            return
        self._integration_tabs_layout.removeWidget(selector)
        selector.setParent(None)
        self._settings_page_selector = None

    def load_data(self):
        self.inp_phone.setText(self.db.get_setting("whatsapp_number", ""))
        mode = self.db.get_setting("whatsapp_mode", "")
        if not mode:
            legacy = self.db.get_setting("whatsapp_active", "0")
            mode = {"1": "desktop_manual", "2": "provider_api"}.get(str(legacy), "disabled")
        index = self.cmb_mode.findData(mode)
        self.cmb_mode.blockSignals(True)
        try:
            self.cmb_mode.setCurrentIndex(index if index >= 0 else 0)
        finally:
            self.cmb_mode.blockSignals(False)
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
        self._update_provider_field_visibility()
        self._update_protocol_mode_buttons()
        self._refresh_whatsapp_summary()

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
        self._refresh_whatsapp_summary()
        if self.main_window:
            from src.utils.toast_notification import show_success
            show_success(self.main_window, "WhatsApp ayarlari guncellendi.")
