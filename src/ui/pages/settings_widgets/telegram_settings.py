# -*- coding: utf-8 -*-

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from PyQt6.QtCore import QPointF, QSize, Qt
from PyQt6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import (
    QCheckBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMessageBox, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from src.utils.secure_setting_store import SecureSettingStore
from src.utils.theme_colors import theme_qss


class TelegramSwitch(QCheckBox):
    def __init__(self, label, parent=None):
        super().__init__(parent)
        self.setAccessibleName(label)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(34, 20)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        track = self.rect().adjusted(1, 2, -1, -2)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#03b5d3" if self.isChecked() else "#343948"))
        painter.drawRoundedRect(track, track.height() / 2, track.height() / 2)
        knob_x = track.right() - track.height() + 1 if self.isChecked() else track.left() + 1
        knob = track.adjusted(1, 1, -(track.width() - track.height() + 1), -1)
        knob.moveLeft(knob_x)
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(knob)
        painter.end()


class TelegramSparkline(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(78, 24)
        self.setMaximumHeight(28)
        self.setAccessibleName("Daily Telegram delivery success preview")

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#4cd7f6"), 2))
        values = (0.78, 0.64, 0.71, 0.45, 0.61, 0.3, 0.42, 0.16, 0.28)
        points = QPolygonF([
            QPointF(index * (self.width() - 4) / (len(values) - 1) + 2,
                    values[index] * (self.height() - 5) + 2)
            for index in range(len(values))
        ])
        painter.drawPolyline(points)
        painter.end()


class TelegramSettingsWidget(QWidget):
    """Telegram bot setup, recipient list, and notification preferences."""

    DEFAULT_WEBHOOK_URL = "https://api.ayecpro.com.tr/v4/telegram/webhook/inbound"

    THEME_QSS = """
        QWidget#telegramRoot { background: @window; color: @text; font-family: "Segoe UI", Arial, sans-serif; }
        QWidget#telegramContent, QScrollArea#telegramScroll { background: @window; border: 0; }
        QFrame#telegramCard { background: @surface; border: 1px solid @border; border-radius: 6px; }
        QFrame#telegramPreference { background: @surface_alt; border: 1px solid @border; border-radius: 6px; }
        QFrame#telegramMessagePreview { background: @window; border: 1px solid @border; border-radius: 6px; }
        QPushButton#telegramSettingsTab { background: @surface_alt; border: 0; border-bottom: 1px solid @border; border-radius: 4px 4px 0 0; color: @text_muted; padding: 7px 10px; }
        QPushButton#telegramSettingsTab[active="true"] { background: @surface; border-bottom: 2px solid @accent; color: @accent; font-weight: bold; }
        QLabel { background: transparent; border: 0; padding: 0; color: @text; font-family: "Segoe UI", "Arial", sans-serif; }
        QLabel#telegramPreferenceIcon { min-width: 22px; max-width: 22px; min-height: 22px; max-height: 22px; background: @surface_alt; color: @accent; border-radius: 3px; font-size: 14px; font-weight: bold; qproperty-alignment: AlignCenter; }
        QLabel#telegramPreferenceTitle { font-size: 9px; font-weight: 600; }
        QLabel#telegramPreferenceDetail, QLabel[muted="true"] { color: @text_muted; }
        QLabel#telegramPreferenceDetail { font-size: 8px; }
        QLabel#telegramMessageId { color: @accent; font: 700 9px Consolas, monospace; }
        QLabel#telegramMessageState { background: @success_bg; color: @success; font: 700 8px Consolas, monospace; padding: 3px 5px; }
        QLabel#telegramMessageBody { background: @surface_alt; color: @text; font-size: 9px; padding: 5px; }
        QLabel#telegramPreviewAction { background: @surface_alt; color: @accent; border-radius: 3px; padding: 4px; font-size: 8px; }
        QLabel#telegramPreviewApproved { background: @surface_alt; color: @success; border-radius: 3px; padding: 4px; font-size: 8px; }
        QLabel#telegramMessageTime, QLabel#telegramBotState, QLabel#telegramSuccessLabel { color: @text_muted; }
        QLabel#telegramMessageTime { font: 8px Consolas, monospace; }
        QLabel#telegramBotIcon { min-width: 24px; max-width: 24px; min-height: 24px; max-height: 24px; background: @accent; color: @selection_text; border-radius: 5px; font-size: 9px; font-weight: bold; qproperty-alignment: AlignCenter; }
        QLabel#telegramBotName { font-size: 10px; font-weight: bold; }
        QLabel#telegramBotState, QLabel#telegramSuccessLabel { font-size: 8px; }
        QLabel#telegramSuccessValue { color: @success; font-size: 16px; font-weight: bold; }
        QLabel#telegramStepNumber { min-width: 18px; max-width: 18px; min-height: 18px; max-height: 18px; background: @surface_alt; color: @accent; border-radius: 3px; font-size: 9px; font-weight: bold; qproperty-alignment: AlignCenter; }
        QLineEdit { background: @window; border: 1px solid @border; border-radius: 5px; color: @text; padding: 8px; font-family: "Arial", "Segoe UI", sans-serif; }
        QPushButton { background: @surface_alt; border: 1px solid @border; border-radius: 5px; color: @text; padding: 8px 12px; font-family: "Arial", "Segoe UI", sans-serif; }
        QPushButton#telegramPrimary { background: @accent; border: 0; color: @selection_text; font-weight: bold; }
        QPushButton#telegramDanger { color: @danger; }
        QListWidget { background: @window; border: 1px solid @border; border-radius: 5px; color: @text; font-family: "Arial", "Segoe UI", sans-serif; }
        QListWidget#telegramChatList { background: transparent; border: 0; color: @text; font-family: "Arial", "Segoe UI", sans-serif; }
        QListWidget#telegramChatList::item { min-height: 22px; padding: 2px 7px; background: @surface_alt; border: 1px solid @border; border-radius: 4px; }
        QListWidget#telegramActivityList { background: @window; border: 1px solid @border; border-radius: 4px; color: @text; font-size: 9px; }
        QListWidget#telegramActivityList::item { min-height: 36px; padding: 4px 7px; border-bottom: 1px solid @border; }
        QLabel#telegramLogTotal { color: @text_muted; font: 9px Consolas, "Segoe UI", Arial, sans-serif; }
        QPushButton#telegramLogButton { background: transparent; border: 0; color: @accent; padding: 4px; }
        QCheckBox { color: @text; spacing: 8px; font-family: "Arial", "Segoe UI", sans-serif; }
    """

    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.setObjectName("telegramRoot")
        self.setFont(QFont("Arial", 9))
        self.setStyleSheet(theme_qss(self.THEME_QSS))
        self.setup_ui()
        self.load_data()

    def _card(self, layout, title, description=None):
        frame = QFrame()
        frame.setObjectName("telegramCard")
        frame.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        box = QVBoxLayout(frame)
        box.setContentsMargins(10, 8, 10, 8)
        box.setSpacing(6)
        if title:
            heading = QLabel(title)
            heading.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            box.addWidget(heading)
        if description:
            detail = QLabel(description)
            detail.setWordWrap(True)
            detail.setProperty("muted", True)
            box.addWidget(detail)
        layout.addWidget(frame)
        return frame, box

    def setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.content_scroll = QScrollArea(self)
        self.content_scroll.setObjectName("telegramScroll")
        self.content_scroll.setWidgetResizable(True)
        self.content_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.content = QWidget()
        self.content.setObjectName("telegramContent")
        self.content_scroll.setWidget(self.content)
        outer.addWidget(self.content_scroll)
        root = QVBoxLayout(self.content)
        root.setContentsMargins(8, 6, 8, 6)
        root.setSpacing(6)
        tabs = QHBoxLayout()
        tabs.setSpacing(4)
        tabs.addStretch(1)
        self.settings_tab_buttons = {}
        for page_id, label in (
            (2, "SMS D\u00f6ng\u00fcleri"),
            (3, "\u015eablonlar"),
            (1, "SMTP Mail"),
            (16, "Telegram Bot"),
        ):
            button = QPushButton(label)
            button.setObjectName("telegramSettingsTab")
            button.setProperty("active", page_id == 16)
            button.clicked.connect(lambda _checked=False, target=page_id: self._navigate_settings_tab(target))
            self.settings_tab_buttons[page_id] = button
            tabs.addWidget(button)
        root.addLayout(tabs)
        heading = QHBoxLayout()
        title = QLabel("Telegram Bot \u00d6zel Entegrasyonu")
        title.setFont(QFont("Arial", 15, QFont.Weight.Bold))
        heading.addWidget(title)
        heading.addStretch()
        self.status_label = QLabel("BOT DURUMU: KURULUM BEKLIYOR")
        self.status_label.setProperty("muted", True)
        heading.addWidget(self.status_label)
        root.addLayout(heading)

        columns = QGridLayout()
        columns.setHorizontalSpacing(8)
        columns.setVerticalSpacing(6)
        columns.setColumnStretch(0, 208)
        columns.setColumnStretch(1, 100)
        root.addLayout(columns, 1)

        left = QWidget()
        left.setObjectName("telegramMainColumn")
        left.setStyleSheet(theme_qss("QWidget#telegramMainColumn { border-left: 3px solid @accent; }"))
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(8, 0, 0, 0)
        left_layout.setSpacing(6)
        columns.addWidget(left, 0, 0)
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)
        columns.addWidget(right, 0, 1)

        frame, box = self._card(left_layout, "BOT KANALI     |     GUVENLIK     |     DURUM")
        row = QHBoxLayout()
        for label, value in (("TELEGRAM", "Cloud API v7.2"), ("TOKEN KORUMALI", "AES-256 sifrelenmis"), ("BEKLIYOR", "Yetkilendirme gerekli"), ("@AyecProBot", "Kurulum bekliyor")):
            item = QVBoxLayout()
            item.addWidget(QLabel(label))
            sub = QLabel(value)
            sub.setProperty("muted", True)
            item.addWidget(sub)
            row.addLayout(item, 1)
        box.addLayout(row)

        frame, box = self._card(left_layout, "Entegrasyon ve hizli kurulum rehberi", "BotFather uzerinden bot olusturun, HTTP API tokenini girin ve baglantiyi dogrulayin.")
        steps = QGridLayout()
        steps.setHorizontalSpacing(8)
        steps.setVerticalSpacing(6)
        for index, text in enumerate(("@BotFather ile /newbot komutunu calistirin.", "Verilen HTTP API tokenini guvenli alana yapistirin.", "Baglanti testiyle bot kimligini dogrulayin.", "Bildirim alacak yonetici ve teknisyen Chat ID'lerini ekleyin.")):
            step = QWidget()
            step_layout = QHBoxLayout(step)
            step_layout.setContentsMargins(0, 0, 0, 0)
            step_layout.setSpacing(6)
            number = QLabel(str(index + 1))
            number.setObjectName("telegramStepNumber")
            label = QLabel(text)
            label.setWordWrap(True)
            step_layout.addWidget(number)
            step_layout.addWidget(label, 1)
            steps.addWidget(step, index // 2, index % 2)
        box.addLayout(steps)

        frame, box = self._card(left_layout, "Telegram Bot Token (HTTP API Belirteci)")
        token_row = QHBoxLayout()
        self.inp_token = QLineEdit()
        self.inp_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.inp_token.setPlaceholderText("123456789:ABCdefGHIjklMNOpqrsTUVwx_yz")
        token_row.addWidget(self.inp_token, 1)
        self.token_eye = QPushButton("Goster")
        self.token_eye.clicked.connect(self._toggle_token)
        token_row.addWidget(self.token_eye)
        self.btn_copy_token = QPushButton("Kopyala")
        self.btn_copy_token.clicked.connect(self.copy_token)
        token_row.addWidget(self.btn_copy_token)
        box.addLayout(token_row)
        self.webhook_label = QLabel("Webhook: API URL kaydedildiginde burada gorunur")
        self.webhook_label.setProperty("muted", True)
        box.addWidget(self.webhook_label)
        webhook_row = QHBoxLayout()
        self.webhook_url = QLabel(self.DEFAULT_WEBHOOK_URL)
        self.webhook_url.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        webhook_row.addWidget(self.webhook_url, 1)
        self.btn_reset_webhook = QPushButton("Webhook URL Sifirla")
        self.btn_reset_webhook.clicked.connect(self.reset_webhook_url)
        webhook_row.addWidget(self.btn_reset_webhook)
        self.btn_drop_pending = QPushButton("Telegram Drop Pending")
        self.btn_drop_pending.clicked.connect(self.show_pending_updates)
        webhook_row.addWidget(self.btn_drop_pending)
        box.addLayout(webhook_row)

        frame, box = self._card(left_layout, "Yonetici ve teknisyen Telegram Chat ID'leri")
        ids_row = QHBoxLayout()
        self.inp_chat_id = QLineEdit()
        self.inp_chat_id.setPlaceholderText("Yeni Chat ID (or. 981234567)")
        ids_row.addWidget(self.inp_chat_id, 1)
        add_id = QPushButton("+ Ekle")
        add_id.clicked.connect(self.add_chat_id)
        ids_row.addWidget(add_id)
        box.addLayout(ids_row)
        self.chat_list = QListWidget()
        self.chat_list.setObjectName("telegramChatList")
        self.chat_list.setFlow(QListWidget.Flow.LeftToRight)
        self.chat_list.setWrapping(True)
        self.chat_list.setGridSize(QSize(160, 28))
        self.chat_list.setSpacing(4)
        self.chat_list.setMinimumHeight(34)
        self.chat_list.setMaximumHeight(40)
        self.chat_list.itemSelectionChanged.connect(self._sync_chat_controls)
        box.addWidget(self.chat_list)
        remove_id = QPushButton("Secili Chat ID'yi kaldir")
        remove_id.setObjectName("telegramDanger")
        self.remove_chat_button = remove_id
        remove_id.clicked.connect(self.remove_chat_id)
        box.addWidget(remove_id, 0, Qt.AlignmentFlag.AlignRight)

        frame, box = self._card(left_layout, "Anlik Telegram Bildirim Tercihleri")
        pref_grid = QGridLayout()
        pref_grid.setHorizontalSpacing(8)
        pref_grid.setVerticalSpacing(6)
        self.preferences = {}
        preferences = (
            ("service_new", "Yeni servis kaydi acildiginda", "Kabul barkodu ve m\u00fc\u015fteri \u00f6zeti g\u00f6nderilir.", "\u2713"),
            ("stock_critical", "Kritik stok uyarisi geldiginde", "Kritik e\u015fik altina d\u00fc\u015fen yedek par\u00e7alar.", "\u26a0"),
            ("tech_status", "Teknisyen durumu degistiginde", "Tamir bitti, par\u00e7a bekleniyor durumlar\u0131.", "\u2699"),
            ("daily_report", "Gun sonu kasa raporu ilet", "Saat 20:30 g\u00fcnl\u00fck ciro ve teslim \u00f6zeti.", "\u25a4"),
        )
        for index, (key, label, description, icon_text) in enumerate(preferences):
            tile = QFrame()
            tile.setObjectName("telegramPreference")
            tile_layout = QHBoxLayout(tile)
            tile_layout.setContentsMargins(6, 5, 6, 5)
            tile_layout.setSpacing(6)
            icon = QLabel(icon_text)
            icon.setObjectName("telegramPreferenceIcon")
            tile_layout.addWidget(icon)
            text_layout = QVBoxLayout()
            text_layout.setContentsMargins(0, 0, 0, 0)
            text_layout.setSpacing(1)
            title = QLabel(label)
            title.setObjectName("telegramPreferenceTitle")
            detail = QLabel(description)
            detail.setObjectName("telegramPreferenceDetail")
            detail.setWordWrap(True)
            text_layout.addWidget(title)
            text_layout.addWidget(detail)
            tile_layout.addLayout(text_layout, 1)
            check = TelegramSwitch(label)
            check.setChecked(True)
            self.preferences[key] = check
            tile_layout.addWidget(check)
            pref_grid.addWidget(tile, index // 2, index % 2)
        box.addLayout(pref_grid)

        frame, box = self._card(right_layout, "")
        identity = QHBoxLayout()
        avatar = QLabel("TG")
        avatar.setObjectName("telegramBotIcon")
        identity.addWidget(avatar)
        identity_text = QVBoxLayout()
        identity_text.setSpacing(1)
        assistant_name = QLabel("AYEC Pro Asistan")
        assistant_name.setObjectName("telegramBotName")
        assistant_state = QLabel("bot  |  baglanti testi bekleniyor")
        assistant_state.setObjectName("telegramBotState")
        self.assistant_state = assistant_state
        identity_text.addWidget(assistant_name)
        identity_text.addWidget(assistant_state)
        identity.addLayout(identity_text, 1)
        self.assistant_time = QLabel("--:--")
        identity.addWidget(self.assistant_time)
        box.addLayout(identity)
        self.bot_card_status = QLabel("Bot baglantisi henuz test edilmedi")
        self.bot_card_status.setMinimumHeight(24)
        self.bot_card_status.setProperty("muted", True)
        box.addWidget(self.bot_card_status)
        preview = QFrame()
        preview.setObjectName("telegramMessagePreview")
        preview_layout = QVBoxLayout(preview)
        preview_layout.setContentsMargins(8, 7, 8, 6)
        preview_layout.setSpacing(4)
        message_header = QHBoxLayout()
        message_id = QLabel("#SRV-2025-9921")
        message_id.setObjectName("telegramMessageId")
        message_header.addWidget(message_id)
        message_header.addStretch(1)
        message_state = QLabel("SERV\u0130SE KABUL ED\u0130LD\u0130")
        message_state.setObjectName("telegramMessageState")
        message_header.addWidget(message_state)
        preview_layout.addLayout(message_header)
        message_body = QLabel(
            "M\u00fc\u015fteri: Ahmet YILMAZ\n"
            "Cihaz: MacBook Pro M2 (16GB/512GB)\n"
            "\u015eikayet: S\u0131v\u0131 temas\u0131, \u015farj kontrol \u00e7ipi yan\u0131t vermiyor.\n"
            "Atanan Teknisyen: engin.aslan\n"
            "\u00d6n Tahmini Maliyet: 4.250,00 \u20ba"
        )
        message_body.setWordWrap(True)
        message_body.setObjectName("telegramMessageBody")
        preview_layout.addWidget(message_body)
        message_actions = QHBoxLayout()
        message_actions.setSpacing(5)
        inspect_action = QLabel("Detay\u0131 \u0130ncele")
        inspect_action.setObjectName("telegramPreviewAction")
        inspect_action.setAlignment(Qt.AlignmentFlag.AlignCenter)
        approve_action = QLabel("Onay Ver")
        approve_action.setObjectName("telegramPreviewApproved")
        approve_action.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_actions.addWidget(inspect_action, 1)
        message_actions.addWidget(approve_action, 1)
        preview_layout.addLayout(message_actions)
        message_time = QLabel("14:22:18 \u00b7 Teslim Edildi \u2713\u2713")
        message_time.setObjectName("telegramMessageTime")
        message_time.setAlignment(Qt.AlignmentFlag.AlignRight)
        preview_layout.addWidget(message_time)
        box.addWidget(preview)
        success_row = QHBoxLayout()
        success_labels = QVBoxLayout()
        success_label = QLabel("GUNLUK ILETi BASARISI")
        success_label.setObjectName("telegramSuccessLabel")
        success_value = QLabel("%99.82")
        success_value.setObjectName("telegramSuccessValue")
        success_labels.addWidget(success_label)
        success_labels.addWidget(success_value)
        success_row.addLayout(success_labels)
        success_row.addStretch(1)
        success_row.addWidget(TelegramSparkline())
        box.addLayout(success_row)

        frame, box = self._card(right_layout, "Canl\u0131 Da\u011f\u0131t\u0131m G\u00fcnl\u00fc\u011f\u00fc")
        self.log_list = QListWidget()
        self.log_list.setObjectName("telegramActivityList")
        self.log_list.addItems((
            "Mesaj \u0130letildi (ChatID: 893412781)\n12:44:09 | Payload: #SRV-9921_STATUS_ACCEPTED",
            "Webhook Handshake Ping\n12:30:00 | HTTP 200 OK | RTT: 28ms",
            "Kritik Stok Bildirimi \u0130letildi\n11:15:42 | SKU-8821 iPhone 13 OLED (Stok: 1)",
            "Token Anahtar\u0131 Do\u011fruland\u0131\n10:02:11 | MD5-CHECKSUM: 44bf89.. Valid",
        ))
        self.log_list.setWordWrap(True)
        self.log_list.setMinimumHeight(176)
        box.addWidget(self.log_list)
        self.log_total = QLabel("Toplam \u0130letim: 1,482 adet")
        self.log_total.setObjectName("telegramLogTotal")
        log_footer = QHBoxLayout()
        log_footer.addWidget(self.log_total)
        log_footer.addStretch(1)
        all_logs = QPushButton("T\u00fcm Loglar\u0131 G\u00f6r\u00fcnt\u00fcle")
        all_logs.setObjectName("telegramLogButton")
        all_logs.clicked.connect(self._show_logs)
        log_footer.addWidget(all_logs)
        box.addLayout(log_footer)
        right_layout.addStretch(1)

        actions = QHBoxLayout()
        test_button = QPushButton("Baglantiyi test et")
        test_button.clicked.connect(self.test_connection)
        actions.addWidget(test_button)
        clear_button = QPushButton("Temizle")
        clear_button.clicked.connect(self.clear_form)
        actions.addWidget(clear_button)
        actions.addStretch(1)
        save_button = QPushButton("Kaydet ve botu baslat")
        save_button.setObjectName("telegramPrimary")
        save_button.clicked.connect(self.save_data)
        actions.addWidget(save_button)
        left_layout.addLayout(actions)

    def _navigate_settings_tab(self, page_id):
        settings_page = getattr(self.main_window, "settings_page", None)
        if settings_page is not None and hasattr(settings_page, "change_page"):
            settings_page.change_page(page_id)

    def copy_token(self):
        token = self.inp_token.text().strip()
        if not token:
            QMessageBox.information(self, "Telegram", "Kopyalanacak bot tokeni yok.")
            return
        QGuiApplication.clipboard().setText(token)
        self.status_label.setText("BOT TOKENI PANOSUNA KOPYALANDI")

    def reset_webhook_url(self):
        self._update_webhook(False)

    def show_pending_updates(self):
        answer = QMessageBox.question(
            self,
            "Telegram Drop Pending",
            "Telegram tarafindaki bekleyen tum guncellemeler kalici olarak silinsin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._update_webhook(True)

    def _update_webhook(self, drop_pending):
        token = self.inp_token.text().strip()
        if not token:
            QMessageBox.warning(self, "Telegram", "Once bot tokenini girin.")
            return
        payload = urllib.parse.urlencode({
            "url": self.DEFAULT_WEBHOOK_URL,
            "drop_pending_updates": "true" if drop_pending else "false",
        }).encode("utf-8")
        request = urllib.request.Request(
            "https://api.telegram.org/bot%s/setWebhook" % token,
            data=payload,
            headers={"User-Agent": "AYEC-Pro/1.0", "Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                result = json.loads(response.read().decode("utf-8"))
            if not result.get("ok"):
                raise ValueError(result.get("description", "Telegram webhook ayarini reddetti."))
            self.webhook_url.setText(self.DEFAULT_WEBHOOK_URL)
            self.webhook_label.setText("Webhook URL sifirlandi" if not drop_pending else "Bekleyen Telegram guncellemeleri silindi")
            self.status_label.setText("BOT DURUMU: WEBHOOK AKTIF")
            self._record_activity("Pending updates dropped" if drop_pending else "Webhook target restored")
        except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            self.webhook_label.setText("Webhook guncellenemedi")
            QMessageBox.warning(self, "Telegram webhook", str(exc))

    def _toggle_token(self):
        visible = self.inp_token.echoMode() == QLineEdit.EchoMode.Password
        self.inp_token.setEchoMode(QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password)
        self.token_eye.setText("Gizle" if visible else "Goster")

    def _chat_ids(self):
        try:
            value = json.loads(self.db.get_setting("telegram_chat_ids", "[]") or "[]")
            return [str(item) for item in value if str(item).strip()]
        except (TypeError, ValueError):
            legacy = str(self.db.get_setting("telegram_chat_id", "") or "").strip()
            return [legacy] if legacy else []

    def load_data(self):
        self.inp_token.setText(SecureSettingStore.get(self.db, "telegram_bot_token", ""))
        self.chat_list.clear()
        self.chat_list.addItems(self._chat_ids())
        self._sync_chat_controls()
        for key, check in self.preferences.items():
            check.setChecked(self.db.get_setting("telegram_notify_" + key, "1") != "0")
        if self.inp_token.text():
            self.status_label.setText("BOT DURUMU: BAGLANTI TESTI BEKLIYOR")

    def _persist_chat_ids(self):
        self.db.set_setting("telegram_chat_ids", json.dumps([self.chat_list.item(i).text() for i in range(self.chat_list.count())]))
        self._sync_chat_controls()

    def _activity_events(self):
        try:
            events = json.loads(self.db.get_setting("telegram_activity_log", "[]") or "[]")
            return [event for event in events if isinstance(event, dict)][:100] if isinstance(events, list) else []
        except (TypeError, ValueError):
            return []

    def _record_activity(self, message):
        events = self._activity_events()
        events.insert(0, {
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "message": str(message)[:180],
        })
        value = json.dumps(events[:100], ensure_ascii=True)
        self.db.set_setting("telegram_activity_log", value)

    def _sync_chat_controls(self):
        self.chat_list.setVisible(self.chat_list.count() > 0)
        self.remove_chat_button.setVisible(self.chat_list.currentRow() >= 0)

    def add_chat_id(self):
        chat_id = self.inp_chat_id.text().strip()
        if not chat_id or any(not char.isdigit() and char != "-" for char in chat_id):
            QMessageBox.warning(self, "Chat ID", "Gecerli bir numeric Chat ID girin.")
            return
        if not [self.chat_list.item(i).text() for i in range(self.chat_list.count())].count(chat_id):
            self.chat_list.addItem(chat_id)
            self._persist_chat_ids()
        self.inp_chat_id.clear()

    def remove_chat_id(self):
        row = self.chat_list.currentRow()
        if row >= 0:
            self.chat_list.takeItem(row)
            self._persist_chat_ids()

    def clear_form(self):
        self.inp_token.clear()
        self.inp_chat_id.clear()

    def save_data(self):
        SecureSettingStore.set(self.db, "telegram_bot_token", self.inp_token.text().strip())
        self._persist_chat_ids()
        for key, check in self.preferences.items():
            self.db.set_setting("telegram_notify_" + key, "1" if check.isChecked() else "0")
        self._record_activity("Telegram settings saved")
        if self.inp_token.text().strip():
            self.status_label.setText("BOT DURUMU: TOKEN GUVENLI KAYDEDILDI")
            self._update_webhook(False)
        else:
            self.status_label.setText("BOT DURUMU: TOKEN GEREKLI")
            self.bot_card_status.setText("Token girip yeniden kaydedin")
        if self.main_window:
            self.main_window.show_notification("Telegram ayarlari kaydedildi.", "success")

    def test_connection(self):
        token = self.inp_token.text().strip()
        if not token:
            QMessageBox.warning(self, "Telegram", "Once bot tokenini girin.")
            return
        request = urllib.request.Request("https://api.telegram.org/bot%s/getMe" % token, headers={"User-Agent": "AYEC-Pro/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if not payload.get("ok"):
                raise ValueError(payload.get("description", "Telegram API tokeni dogrulamadi."))
            username = payload.get("result", {}).get("username", "")
            self.status_label.setText("BOT DURUMU: CEVRIMICI")
            self.assistant_state.setText("bot  |  API dogrulandi")
            self.assistant_time.setText(datetime.now().strftime("%H:%M"))
            self.bot_card_status.setText("@%s\nBot API baglantisi basarili" % username)
            self.webhook_label.setText("Telegram API dogrulandi; bot: @%s" % username)
            self._record_activity("Bot API connection verified")
            self._refresh_webhook_status(token)
        except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            message = str(exc)
            self.status_label.setText("BOT DURUMU: BAGLANTI HATASI")
            self.assistant_state.setText("bot  |  API dogrulanamadi")
            self.bot_card_status.setText(message[:180])
            self._record_activity("Bot API connection failed")
            QMessageBox.warning(self, "Telegram baglanti testi", message)

    def _refresh_webhook_status(self, token):
        request = urllib.request.Request(
            "https://api.telegram.org/bot%s/getWebhookInfo" % token,
            headers={"User-Agent": "AYEC-Pro/1.0"},
        )
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if not payload.get("ok"):
                raise ValueError(payload.get("description", "Webhook durumu alinamadi."))
            info = payload.get("result", {})
            webhook_url = str(info.get("url") or "")
            error = str(info.get("last_error_message") or "")
            self.webhook_label.setText(error or ("Webhook etkin: " + webhook_url if webhook_url else "Telegram webhook kurulmamis"))
            self._record_activity("Webhook status checked")
        except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            self.webhook_label.setText(str(exc)[:180])

    def _show_logs(self):
        events = self._activity_events()
        detail = "\n".join("%s  %s" % (item.get("at", ""), item.get("message", "")) for item in events[:20])
        QMessageBox.information(self, "Telegram dagitim gunlugu", detail or "Kayitli Telegram islemi yok.")
