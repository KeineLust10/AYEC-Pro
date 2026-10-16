# -*- coding: utf-8 -*-

from PyQt6.QtCore import Qt, QSignalBlocker
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QScrollArea,
    QVBoxLayout,
    QWidget,
    QGridLayout,
)

from src.ui.pages.settings_widgets.sms_settings import (
    SMSSettingsWidget as SMSSettingsWidgetMod,
    SMSTemplatesWidget as SMSTemplatesWidgetMod,
)
from src.ui.pages.settings_widgets.smtp_settings import SMTPSettingsWidget as SMTPSettingsWidgetMod
from src.ui.pages.settings_widgets.telegram_settings import TelegramSettingsWidget
from src.ui.pages.settings_widgets.voice_assistant_settings import VoiceAssistantSettingsWidget
from src.ui.pages.settings_widgets.voice_assistant_shortcuts import VoiceAssistantShortcutsWidget
from src.ui.pages.settings_widgets.voice_training_reference import VoiceTrainingWidget
from src.ui.pages.settings_widgets.whatsapp_settings import WhatsAppSettingsWidget
from src.utils.theme_colors import tc, theme_qss
from src.utils.appearance_mode import AppearanceModeManager
from src.utils.secure_setting_store import SecureSettingStore


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
                border: 0;
                background: @window;
                border-radius: 0;
                top: 0;
            }
            QTabBar::tab {
                background: transparent;
                color: @text_muted;
                padding: 4px 8px;
                margin-right: 4px;
                border-radius: 4px;
                font-weight: 600;
                font-size: 12px;
                min-width: 0;
                max-width: 180px;
            }
            QTabBar::tab:selected {
                background: @surface_alt;
                color: @accent;
                border-bottom: 2px solid @accent;
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
        self.tabs.tabBar().setElideMode(Qt.TextElideMode.ElideNone)
        self.tabs.setStyleSheet(self._tabs_qss())

        assistant_name = str(self.db.get_setting("asistan_ozel_adi", "AYEC") or "AYEC")
        tab_structure = [
            ("🔑", f"API Anahtarları ({assistant_name}/Gemini)", "gemini", tc("accent")),
            ("[AI]", "Otonom Ajanlar ve Entegrasyon Hub", "autonomous_agents", tc("accent_pressed")),
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

            tab_index = self.tabs.addTab(placeholder, f"{icon}  {label}")
            self.tabs.setTabToolTip(tab_index, label)
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
        self._apply_adaptive_integration_styles(self)

    @staticmethod
    def _apply_adaptive_integration_styles(root):
        """Convert legacy integration-tab dark literals to semantic theme tokens."""
        theme_qss("")
        replacements = {
            "#0e1321": "@window",
            "#090e1c": "@window",
            "#0e1525": "@surface",
            "#0b1220": "@surface_alt",
            "#0b1322": "@surface_alt",
            "#0a1120": "@surface_alt",
            "#14233a": "@surface_alt",
            "#111a2a": "@surface_alt",
            "#111b2d": "@surface_alt",
            "#161b2a": "@surface",
            "#1a1f2e": "@surface_alt",
            "#1b2638": "@surface_alt",
            "#1c293d": "@surface_alt",
            "#19273b": "@surface_alt",
            "#252a39": "@border",
            "#26334a": "@border",
            "#303444": "@border",
            "#334155": "@border",
            "#24314b": "@border",
            "#424754": "@border",
            "#dee2f6": "@text",
            "#dbe5f8": "@text",
            "#e5edf9": "@text",
            "#e2e8f0": "@text",
            "#dce4f2": "@text",
            "#c2c6d6": "@text_muted",
            "#cbd5e1": "@text_muted",
            "#94a3b8": "@text_muted",
        }
        targets = [root, *root.findChildren(QWidget)]
        for target in targets:
            try:
                if target.property("skipThemeTransform") is True:
                    continue
                target.setProperty("skipThemeTransform", False)
                current = getattr(target, "_theme_raw_stylesheet", None)
                if current is None:
                    current = target.styleSheet()
                previous = getattr(target, "_integration_theme_applied", None)
                if current != previous:
                    target._integration_theme_source = current
                source = getattr(target, "_integration_theme_source", current)
                if not source:
                    continue
                adapted = str(source)
                for literal, token in replacements.items():
                    adapted = adapted.replace(literal, token).replace(literal.upper(), token)
                if adapted != current:
                    target.setStyleSheet(theme_qss(adapted))
                target._integration_theme_applied = adapted
            except (RuntimeError, AttributeError):
                continue
        for target in targets:
            apply_reference_typography = getattr(target, "apply_reference_typography", None)
            if callable(apply_reference_typography):
                try:
                    apply_reference_typography()
                except RuntimeError:
                    continue

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
            self._apply_adaptive_integration_styles(page)
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

    def _wrap_gemini_page(self, page):
        from src.ui.pages.settings_widgets.gemini_reference_canvas import GeminiReferenceCanvas
        canvas = GeminiReferenceCanvas(page)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(canvas)
        return scroll

    def _create_page(self, key, accent, title):
        def bare(inner: QWidget):
            wrapper = QWidget()
            layout = QVBoxLayout(wrapper)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            layout.addWidget(inner)
            return wrapper

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
                        background: @surface;
                        border: 1px solid @border;
                        border-left: 4px solid {accent};
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
            card_layout.addWidget(inner, 1)
            layout.addWidget(card, 1)
            return wrapper

        if key == "gemini":
            from src.ui.pages.settings_widgets.gemini_settings_widget import GeminiSettingsWidget
            return self._wrap_gemini_page(GeminiSettingsWidget(self.db, self.main_window))
        if key == "autonomous_agents":
            from src.ui.pages.settings_widgets.autonomous_agents_widget import AutonomousAgentsWidget
            scroll = QScrollArea(self)
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll.setWidget(AutonomousAgentsWidget(self.db, self.main_window))
            return scroll
        if key == "voice_assistant":
            return VoiceAssistantSettingsWidget(self.db, self.main_window)
        if key == "voice_training":
            return VoiceTrainingWidget(self.db, self.main_window)
        if key == "voice_shortcuts":
            return VoiceAssistantShortcutsWidget(self.db, self.main_window)
        if key == "sms":
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll.setWidget(SMSSettingsWidgetMod(self.db, self.main_window, use_internal_scroll=False))
            return scroll
        if key == "sms_templates":
            return bare(SMSTemplatesWidgetMod(self.db, self.main_window))
        if key == "smtp":
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll.setWidget(SMTPSettingsWidgetMod(self.db, self.main_window))
            return scroll
        if key == "telegram":
            return bare(TelegramSettingsWidget(self.db, self.main_window))
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
        api_key = QLineEdit(
            SecureSettingStore.get(self.db, f"{key}_api_key", "")
        )
        api_key.setEchoMode(QLineEdit.EchoMode.Password)
        webhook = QLineEdit(
            SecureSettingStore.get(self.db, f"{key}_webhook", "")
        )

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
            SecureSettingStore.set(self.db, f"{key}_api_key", api_key.text().strip())
            SecureSettingStore.set(
                self.db, f"{key}_webhook", webhook.text().strip()
            )

        save_btn.clicked.connect(_save)
        layout.addWidget(save_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch()
        return widget
