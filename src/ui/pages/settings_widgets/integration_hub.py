# -*- coding: utf-8 -*-

from PyQt6.QtCore import Qt, QSignalBlocker
from PyQt6.QtWidgets import (
    QApplication,
    QFormLayout,
    QFrame,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.ui.pages.settings_widgets.sms_settings import (
    SMSSettingsWidget as SMSSettingsWidgetMod,
    SMSTemplatesWidget as SMSTemplatesWidgetMod,
)
from src.ui.pages.settings_widgets.smtp_settings import SMTPSettingsWidget as SMTPSettingsWidgetMod
from src.ui.pages.settings_widgets.telegram_settings import TelegramSettingsWidget
from src.ui.pages.settings_widgets.voice_assistant_settings import VoiceAssistantSettingsWidget
from src.ui.pages.settings_widgets.voice_assistant_shortcuts import VoiceAssistantShortcutsWidget
from src.ui.pages.settings_widgets.voice_training_widget import VoiceTrainingWidget
from src.ui.pages.settings_widgets.whatsapp_settings import WhatsAppSettingsWidget
from src.utils.theme_colors import tc, theme_qss
from src.utils.appearance_mode import AppearanceModeManager


class IntegrationHubWidget(QWidget):
    """Entegrasyon ve API ayarları için sekmeli hub."""

    def __init__(self, db, main_window=None):
        super().__init__()
        self.setObjectName("IntegrationHubWidget")
        self.db = db
        self.main_window = main_window
        self._pages = {}
        self._loading_tab = False
        self._build_ui()

    def _is_classic_appearance(self):
        app = QApplication.instance()
        return bool(app and app.property("appearanceMode") == AppearanceModeManager.CLASSIC)

    def _tabs_qss(self):
        if self._is_classic_appearance():
            return AppearanceModeManager.classic_tab_qss()
        return theme_qss(
            """
            QTabWidget::pane {
                border: 1px solid @border;
                background: @surface;
                border-radius: 12px;
                top: -1px;
            }
            QTabBar::tab {
                background: @surface_alt;
                color: @text_muted;
                padding: 12px 18px;
                margin-right: 4px;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                font-weight: 600;
                font-size: 12px;
                min-width: 96px;
                max-width: 180px;
            }
            QTabBar::tab:selected {
                background: @surface;
                color: @accent;
                border-bottom: 3px solid @accent;
                font-weight: 700;
            }
            QTabBar::tab:hover {
                background: @surface_alt;
                color: @text;
            }
            QTabBar::scroller {
                width: 28px;
            }
            """
        )

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("SettingsInnerTabs")
        self.tabs.setProperty("settingsTabs", True)
        if self._is_classic_appearance():
            self.tabs.setProperty("skipThemeTransform", False)
        self.tabs.setUsesScrollButtons(True)
        self.tabs.tabBar().setExpanding(False)
        self.tabs.tabBar().setElideMode(Qt.TextElideMode.ElideRight)
        self.tabs.setStyleSheet(self._tabs_qss())

        assistant_name = str(self.db.get_setting("asistan_ozel_adi", "AYEC") or "AYEC")
        tab_structure = [
            ("🔑", f"API Anahtarları ({assistant_name}/Gemini)", "gemini", tc("accent")),
            ("🎛", "AYEC Pro Sesli Asistan", "voice_assistant", tc("accent_hover")),
            ("🎙", "AYEC Pro Sesli Komut Ayarlari", "voice_training", tc("danger")),
            ("✨", "AI Asistan Kestirmeler", "voice_shortcuts", tc("accent_pressed")),
            ("💬", "SMS Entegrasyonu", "sms", tc("warning")),
            ("✏", "SMS Şablonları", "sms_templates", tc("accent_hover")),
            ("📧", "E-Posta (SMTP)", "smtp", tc("success")),
            ("🤖", "Telegram Bot", "telegram", tc("accent")),
            ("🟢", "WhatsApp", "whatsapp", tc("success")),
        ]

        self._pages = {}
        self._tab_keys = []

        for icon, label, key, color in tab_structure:
            placeholder = QWidget()
            placeholder_layout = QVBoxLayout(placeholder)
            placeholder_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            loading_label = QLabel("⏳ Yükleniyor...")
            loading_label.setStyleSheet(theme_qss("color: @disabled_text; font-size: 14px;"))
            placeholder_layout.addWidget(loading_label)

            self.tabs.addTab(placeholder, f"{icon}  {label}")
            self._tab_keys.append((key, color, label))

        self.tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self.tabs)

        if self._tab_keys:
            self._load_tab(0)

    def apply_theme_styles(self):
        if self._is_classic_appearance():
            self.setProperty("skipThemeTransform", False)
            if hasattr(self, "tabs"):
                self.tabs.setProperty("skipThemeTransform", False)
        self.setStyleSheet("""
            QWidget#IntegrationHubWidget,
            QWidget#IntegrationHubWidget QWidget {
                background: #FFFFFF;
                color: #111827;
            }
            QLabel {
                color: #111827;
                background: transparent;
                border: none;
            }
        """ if self._is_classic_appearance() else "")
        if hasattr(self, "tabs"):
            self.tabs.setStyleSheet(self._tabs_qss())

    def _on_tab_changed(self, index):
        if self._loading_tab:
            return
        if 0 <= index < len(self._tab_keys):
            self._load_tab(index)

    def _load_tab(self, index):
        if self._loading_tab:
            return
        self._loading_tab = True
        try:
            key, color, title = self._tab_keys[index]
            if key in self._pages:
                self.tabs.setCurrentWidget(self._pages[key])
                return

            page = self._create_page(key, color, title)
            self._pages[key] = page

            old_widget = self.tabs.widget(index)
            tab_text = self.tabs.tabText(index)
            with QSignalBlocker(self.tabs):
                self.tabs.removeTab(index)
                self.tabs.insertTab(index, page, tab_text)
                self.tabs.setCurrentIndex(index)
            if old_widget:
                old_widget.deleteLater()
        finally:
            self._loading_tab = False

    def open_tab_by_key(self, key):
        for idx, (tab_key, _, _) in enumerate(self._tab_keys):
            if tab_key == key:
                self.tabs.setCurrentIndex(idx)
                return True
        return False

    def _create_page(self, key, accent, title):
        def wrap(inner: QWidget):
            wrapper = QWidget()
            wrapper.setStyleSheet("background: #FFFFFF; color: #111827;" if self._is_classic_appearance() else "")
            layout = QVBoxLayout(wrapper)
            layout.setContentsMargins(10 if self._is_classic_appearance() else 24, 10 if self._is_classic_appearance() else 24, 10 if self._is_classic_appearance() else 24, 10 if self._is_classic_appearance() else 24)
            layout.setSpacing(8 if self._is_classic_appearance() else 16)

            head = QLabel(title)
            head.setStyleSheet("color: #111827; font-size: 12px; font-weight: 800; border: none; background: transparent;" if self._is_classic_appearance() else theme_qss("color: @text; font-size: 18px; font-weight: 900; border: none;"))
            layout.addWidget(head)

            card = QFrame()
            card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            card.setStyleSheet(
                theme_qss(
                    f"""
                    QFrame {{
                        border-left: 4px solid {accent};
                        background: @surface;
                        border: 1px solid @border;
                        border-radius: 14px;
                        padding: 8px;
                        color: @text;
                    }}
                    QLabel {{ color: @text; background: transparent; }}
                    QLineEdit, QComboBox, QSpinBox, QTextEdit {{
                        color: @text;
                        background: @surface_alt;
                        border: 1px solid @border;
                        border-radius: 10px;
                        padding: 8px 10px;
                    }}
                    QPushButton {{
                        min-height: 40px;
                        border-radius: 10px;
                    }}
                    """
                )
            )
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(18, 18, 18, 18)
            card_layout.setSpacing(12)
            inner.setParent(card)
            card_layout.addWidget(inner)
            layout.addWidget(card)
            layout.addStretch()
            return wrapper

        if key == "gemini":
            from src.ui.pages.settings_page import GeminiSettingsWidget

            return GeminiSettingsWidget(self.db, self.main_window)
        if key == "voice_assistant":
            return VoiceAssistantSettingsWidget(self.db, self.main_window)
        if key == "voice_training":
            return VoiceTrainingWidget(self.db, self.main_window)
        if key == "voice_shortcuts":
            return VoiceAssistantShortcutsWidget(self.db, self.main_window)
        if key == "sms":
            return wrap(SMSSettingsWidgetMod(self.db, self.main_window))
        if key == "sms_templates":
            return wrap(SMSTemplatesWidgetMod(self.db, self.main_window))
        if key == "smtp":
            return wrap(SMTPSettingsWidgetMod(self.db, self.main_window))
        if key == "telegram":
            return wrap(TelegramSettingsWidget(self.db, self.main_window))
        if key == "whatsapp":
            return wrap(WhatsAppSettingsWidget(self.db, self.main_window))

        return self._generic_integration_page(key, title)

    def _generic_integration_page(self, key, title):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        head = QLabel(f"{title} Ayarları")
        head.setStyleSheet(theme_qss("color: @text; font-size: 18px; font-weight: 800;"))
        layout.addWidget(head)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)

        endpoint = QLineEdit(str(self.db.get_setting(f"{key}_endpoint", "") or ""))
        api_key = QLineEdit(str(self.db.get_setting(f"{key}_api_key", "") or ""))
        api_key.setEchoMode(QLineEdit.EchoMode.Password)
        webhook = QLineEdit(str(self.db.get_setting(f"{key}_webhook", "") or ""))

        form.addRow("Endpoint:", endpoint)
        form.addRow("API Key:", api_key)
        form.addRow("Webhook URL:", webhook)
        layout.addLayout(form)

        save_btn = QPushButton("Kaydet")
        save_btn.setStyleSheet(
            theme_qss(
                """
                QPushButton { background: @accent; color: @selection_text; border: 1px solid @border; border-radius: 8px; padding: 8px 14px; font-weight: 700; }
                QPushButton:hover { background: @accent_hover; }
                """
            )
        )

        def _save():
            self.db.set_setting(f"{key}_endpoint", endpoint.text().strip())
            self.db.set_setting(f"{key}_api_key", api_key.text().strip())
            self.db.set_setting(f"{key}_webhook", webhook.text().strip())

        save_btn.clicked.connect(_save)
        layout.addWidget(save_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch()
        return widget
