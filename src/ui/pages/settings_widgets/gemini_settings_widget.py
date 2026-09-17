# -*- coding: utf-8 -*-

from src.utils.design_system import DesignTokens
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QMessageBox,
                             QLineEdit, QComboBox, QTextEdit, QDialog as QtDialog, QListWidget, QListWidgetItem,
                             QSizePolicy, QScrollArea, QGridLayout, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QThread, QEvent, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor

from src.utils.theme_colors import theme_qss, tc
from src.utils.toast_notification import show_success, show_error, show_warning
from src.ui.widgets.animated_toggle import AnimatedToggle
from src.utils.ai_service import (
    DEFAULT_GEMINI_MODEL,
    RECOMMENDED_GEMINI_MODELS,
    normalize_gemini_model,
)
import json
import logging
import os
from src.ui.widgets.modern_dialog import ModernDialog

logger = logging.getLogger(__name__)


class ModelListWorker(QThread):
    finished = pyqtSignal(bool, object)

    def __init__(self, keys_list):
        super().__init__()
        self.keys_list = keys_list

    def run(self):
        try:
            from src.utils.ai_service import AIService
            service = AIService(self.keys_list)
            models = service.get_available_models()
            self.finished.emit(bool(models), models or [])
        except Exception as exc:
            self.finished.emit(False, str(exc))


class GeminiSettingsWidget(QWidget):
    """Gemini AI API Ayarları - Premium Brain Center Design"""
    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        # Set expanding size policy for 100% space usage
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setup_ui()
        self._wire_ui_signals()
        self.load_data()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        header = QFrame()
        header.setStyleSheet(theme_qss(f"""
            QFrame {{
                background: {DesignTokens.CARD};
                border-bottom: 1px solid {DesignTokens.BORDER};
            }}
        """))
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 18, 24, 18)
        
        title_col = QVBoxLayout()
        title_lbl = QLabel("Gemini AI Ayarları")
        title_lbl.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title_lbl.setStyleSheet(theme_qss(f"color: {DesignTokens.FOREGROUND}; background: transparent; border:none;"))
        sub_lbl = QLabel("API bağlantısı, model yönetimi ve otonom yetenekler")
        sub_lbl.setFont(QFont("Segoe UI", 10))
        sub_lbl.setStyleSheet(theme_qss(f"color: {DesignTokens.MUTED_FOREGROUND}; background: transparent; border:none;"))
        title_col.addWidget(title_lbl)
        title_col.addWidget(sub_lbl)
        header_layout.addLayout(title_col)
        header_layout.addStretch()
        
        self.status_badge = QLabel("BAĞLANTI BEKLENİYOR")
        self.status_badge.setStyleSheet(theme_qss(f"""
            color: {DesignTokens.MUTED_FOREGROUND};
            font-weight: 700;
            padding: 6px 12px;
            background: {DesignTokens.SECONDARY};
            border-radius: 12px;
            border: 1px solid {DesignTokens.BORDER};
        """))
        header_layout.addWidget(self.status_badge)
        main_layout.addWidget(header)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(theme_qss("QScrollArea { background: transparent; }"))
        
        content = QWidget()
        content.setStyleSheet(theme_qss(f"background: {DesignTokens.BACKGROUND};"))
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(24, 24, 24, 24)
        self.content_layout.setSpacing(16)
        
        self.content_layout.addLayout(self.create_summary_row())
        
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)
        
        left_col = QVBoxLayout()
        left_col.setSpacing(16)
        right_col = QVBoxLayout()
        right_col.setSpacing(16)
        
        left_col.addWidget(self.create_card_api())
        left_col.addWidget(self.create_card_model())
        right_col.addWidget(self.create_card_autonomous())
        right_col.addWidget(self.create_card_communication())
        left_col.addStretch()
        right_col.addStretch()
        
        grid.addLayout(left_col, 0, 0)
        grid.addLayout(right_col, 0, 1)
        grid.setColumnStretch(0, 3)
        grid.setColumnStretch(1, 2)
        
        self.content_layout.addLayout(grid)
        self.content_layout.addStretch()
        
        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(12)
        
        self.btn_save = QPushButton("Ayarları Kaydet")
        self.btn_save.setFixedHeight(44)
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="lg")))
        self.btn_save.clicked.connect(self.save_data)
        
        footer_layout.addStretch()
        footer_layout.addWidget(self.btn_save)
        
        self.content_layout.addLayout(footer_layout)
        
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def _wire_ui_signals(self):
        self.cmb_model.currentIndexChanged.connect(self.save_data)

    def create_card_container(self, title, icon="\u2699\ufe0f"):
        """creates a styled whitespace card"""
        card = QFrame()
        card.setStyleSheet(theme_qss(f"""
            QFrame {{
                background-color: {DesignTokens.CARD};
                border-radius: {DesignTokens.RADIUS_LG};
                border: 1px solid {DesignTokens.BORDER};
            }}
        """))
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(18)
        shadow.setColor(QColor(0,0,0,18))
        shadow.setOffset(0, 6)
        card.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)
        
        # Card Header
        header = QHBoxLayout()
        lbl_icon = QLabel(icon)
        lbl_icon.setFont(QFont("Segoe UI Emoji", 14))
        lbl_icon.setStyleSheet(theme_qss("border: none;"))
        
        lbl_title = QLabel(title)
        lbl_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl_title.setStyleSheet(theme_qss(f"color: {DesignTokens.FOREGROUND}; border: none;"))
        
        header.addWidget(lbl_icon)
        header.addWidget(lbl_title)
        header.addStretch()
        
        layout.addLayout(header)
        
        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(theme_qss(f"background: {DesignTokens.BORDER}; max-height: 1px;"))
        layout.addWidget(line)
        
        return card, layout

    def create_summary_row(self):
        row = QHBoxLayout()
        row.setSpacing(12)
        
        key_card = self.create_stat_card("API Anahtarları", "0 adet", "🔑")
        model_card = self.create_stat_card("Aktif Model", "Seçilmedi", "🧬")
        auto_card = self.create_stat_card("Otonom Mod", "Kapalı", "🦾")
        
        row.addWidget(key_card)
        row.addWidget(model_card)
        row.addWidget(auto_card)
        
        return row

    def create_stat_card(self, title, value, icon):
        card = QFrame()
        card.setStyleSheet(theme_qss(f"""
            QFrame {{
                background: {DesignTokens.CARD};
                border-radius: {DesignTokens.RADIUS_LG};
                border: 1px solid {DesignTokens.BORDER};
            }}
        """))
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)
        
        icon_lbl = QLabel(icon)
        icon_lbl.setFont(QFont("Segoe UI Emoji", 16))
        icon_lbl.setStyleSheet(theme_qss("border:none;"))
        layout.addWidget(icon_lbl)
        
        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        title_lbl.setStyleSheet(theme_qss(f"color: {DesignTokens.MUTED_FOREGROUND}; border:none;"))
        value_lbl = QLabel(value)
        value_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        value_lbl.setStyleSheet(theme_qss(f"color: {DesignTokens.FOREGROUND}; border:none;"))
        text_col.addWidget(title_lbl)
        text_col.addWidget(value_lbl)
        layout.addLayout(text_col)
        layout.addStretch()
        
        if title == "API Anahtarları":
            self.lbl_key_count = value_lbl
        elif title == "Aktif Model":
            self.lbl_active_model = value_lbl
        elif title == "Otonom Mod":
            self.lbl_auto_state = value_lbl
        
        return card

    def create_card_api(self):
        card, layout = self.create_card_container("API Anahtar Havuzu", "🔑")
        
        info = QLabel(
            "Jarvis'in sürekli aktif kalması için buraya birden fazla API anahtarı girebilirsiniz.\n"
            "Anahtarları alt alta veya virgülle ayırarak yazın. Jarvis birinde kota hatası alırsa diğerine geçer.\n\n"
            "API Anahtarlarını https://aistudio.google.com/app/apikey adresinden ücretsiz alabilirsiniz."
        )
        info.setWordWrap(True)
        info.setOpenExternalLinks(True)
        info.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        info.setStyleSheet(theme_qss(f"color: {DesignTokens.MUTED_FOREGROUND}; font-size: 12px; margin-bottom: 10px; border:none;"))
        layout.addWidget(info)
        
        self.inp_api_key = QTextEdit()
        self.inp_api_key.setPlaceholderText("API Anahtarlarını buraya yapıştırın...\n(Örn: AIzaSy...)")
        self.inp_api_key.setFixedHeight(80)
        self.inp_api_key.setStyleSheet(theme_qss(self.get_input_style()))
        
        lbl_key = QLabel("🔑 API Anahtar Havuzu")
        lbl_key.setStyleSheet(theme_qss("font-weight: 600; color: @text; border:none;"))
        layout.addWidget(lbl_key)
        layout.addWidget(self.inp_api_key)

        self.btn_test = QPushButton("API ve Modeli Test Et")
        self.btn_test.setFixedHeight(40)
        self.btn_test.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_test.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="md")))
        self.btn_test.clicked.connect(self.test_connection)
        layout.addWidget(self.btn_test)
        
        return card

    def create_card_model(self):
        card, layout = self.create_card_container("Model Yönetimi", "🧬")
        
        info = QLabel("Model adresini manuel yazabilir veya bulut listesinden seçim yapabilirsiniz.")
        info.setWordWrap(True)
        info.setStyleSheet(theme_qss(f"color: {DesignTokens.MUTED_FOREGROUND}; font-size: 12px; border:none;"))
        layout.addWidget(info)
        
        self.cmb_model = QComboBox()
        self.cmb_model.setFixedHeight(44)
        self.cmb_model.setEditable(True)
        self.cmb_model.setPlaceholderText(DEFAULT_GEMINI_MODEL)
        self.cmb_model.setStyleSheet(theme_qss(self.get_input_style()))
        for index, model_name in enumerate(RECOMMENDED_GEMINI_MODELS):
            label = (
                f"{model_name} (\u00d6nerilen)"
                if index == 0
                else model_name
            )
            self.cmb_model.addItem(label, model_name)
        if self.cmb_model.lineEdit():
            self.cmb_model.lineEdit().installEventFilter(self)
        
        lbl_model = QLabel("Model Adresi / ID")
        lbl_model.setStyleSheet(theme_qss("font-weight: 600; color: @text; border:none;"))
        layout.addWidget(lbl_model)
        layout.addWidget(self.cmb_model)
        
        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        
        self.btn_manual_connect = QPushButton("Bağlan")
        self.btn_manual_connect.setFixedHeight(40)
        self.btn_manual_connect.setToolTip("Girilen Model Adresine Manuel Bağlan ve Test Et")
        self.btn_manual_connect.setStyleSheet(theme_qss(DesignTokens.get_button_qss("outline", size="md")))
        self.btn_manual_connect.clicked.connect(self.test_manual_connection)
        
        self.btn_list_models = QPushButton("Modelleri Listele")
        self.btn_list_models.setFixedHeight(40)
        self.btn_list_models.setToolTip("Google sunucularindan guncel modelleri ara")
        self.btn_list_models.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="md")))
        self.btn_list_models.clicked.connect(self.list_available_models)
        
        action_row.addWidget(self.btn_manual_connect)
        action_row.addWidget(self.btn_list_models)
        action_row.addStretch()
        
        layout.addLayout(action_row)
        
        return card

    def create_card_autonomous(self):
        card, layout = self.create_card_container("Otonom Yetenekler", "🦾")
        
        desc = QLabel("Jarvis'in sizin yerinize yapabileceği işlemleri buradan kontrol edin.")
        desc.setStyleSheet(theme_qss(f"color: {DesignTokens.MUTED_FOREGROUND}; border:none;"))
        layout.addWidget(desc)
        
        grid = QGridLayout()
        grid.setSpacing(20)
        
        features = [
             ("Sistemi Aktifleştir", "Jarvi's AI çekirdeğini devreye alır.", "jarvis_enabled", True),
             ("Sesli Geri Bildirim", "İşlemleri ve sonuçları sesli okur.", "jarvis_voice_enabled", False),
             ("Otomatik WhatsApp", "Kritik raporları cebe gönderir.", "jarvis_whatsapp_enabled", False),
             ("Akıllı Müşteri Analizi", "Müşteri kaydında istihbarat sağlar.", "jarvis_intel_enabled", True),
             ("Sesli Not Çevirisi", "Teknik terimleri düzeltir.", "jarvis_voice_refine_enabled", True),
             ("Hata İzleyici", "Yazılım hatalarını raporlar.", "jarvis_log_watcher_enabled", False),
             ("Asistan Simgesini G\u00f6ster", "S\u00fcr\u00fcklenebilir robot simgesini ana ekranda g\u00f6sterir.", "assistant_fab_enabled", True),
        ]
        
        self.toggles = {}
        
        row = 0
        col = 0
        for title, subtitle, db_key, default in features:
            wrapper = QFrame()
            wrapper.setStyleSheet(theme_qss(f"background: {DesignTokens.CARD}; border-radius: {DesignTokens.RADIUS_MD}; border: 1px solid {DesignTokens.BORDER};"))
            w_layout = QHBoxLayout(wrapper)
            w_layout.setContentsMargins(15, 15, 15, 15)
            
            # Text
            t_layout = QVBoxLayout()
            l_title = QLabel(title)
            l_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            l_title.setStyleSheet(theme_qss(f"border:none; color: {DesignTokens.FOREGROUND};"))
            l_sub = QLabel(subtitle)
            l_sub.setFont(QFont("Segoe UI", 9))
            l_sub.setStyleSheet(theme_qss(f"border:none; color: {DesignTokens.MUTED_FOREGROUND};"))
            l_sub.setWordWrap(True)
            t_layout.addWidget(l_title)
            t_layout.addWidget(l_sub)
            
            # Toggle
            toggle = AnimatedToggle()
            toggle.setFixedSize(60, 40)
            self.toggles[db_key] = toggle
            toggle.stateChanged.connect(self.update_autonomous_summary)
            
            w_layout.addLayout(t_layout)
            w_layout.addWidget(toggle)
            
            grid.addWidget(wrapper, row, col)
            
            # Grid Logic (2 columns)
            col += 1
            if col > 1:
                col = 0
                row += 1
                
        layout.addLayout(grid)
        return card

    def create_card_communication(self):
        card, layout = self.create_card_container("Haberleşme & Entegrasyon", "📡")
        
        # WhatsApp Form
        wa_layout = QHBoxLayout()
        wa_layout.setSpacing(15)
        
        self.inp_wa_token = QLineEdit()
        self.inp_wa_token.setPlaceholderText("UltraMsg Token (Örn: yx2s...)")
        self.inp_wa_token.setFixedHeight(40)
        self.inp_wa_token.setStyleSheet(theme_qss(self.get_input_style()))
        
        self.inp_wa_phone = QLineEdit()
        self.inp_wa_phone.setPlaceholderText("905xxxxxxxxx")
        self.inp_wa_phone.setFixedHeight(40)
        self.inp_wa_phone.setStyleSheet(theme_qss(self.get_input_style()))
        
        v1 = QVBoxLayout()
        v1.addWidget(QLabel("UltraMsg Token"))
        v1.addWidget(self.inp_wa_token)
        
        v2 = QVBoxLayout()
        v2.addWidget(QLabel("Admin Telefon No"))
        v2.addWidget(self.inp_wa_phone)
        
        wa_layout.addLayout(v1, 2)
        wa_layout.addLayout(v2, 1)
        
        layout.addLayout(wa_layout)
        
        help_lbl = QLabel("WhatsApp entegrasyonu için ultramsg.com hesabı gereklidir. Token bilgisini oradan alabilirsiniz.")
        help_lbl.setStyleSheet(theme_qss(f"color: {DesignTokens.MUTED_FOREGROUND}; border:none; margin-top: 5px;"))
        layout.addWidget(help_lbl)
        
        return card

    def get_input_style(self):
        return DesignTokens.get_input_qss() + DesignTokens.get_combobox_qss()

    def eventFilter(self, obj, event):
        if hasattr(self, "cmb_model") and obj == self.cmb_model.lineEdit():
            if event.type() == QEvent.Type.MouseButtonRelease and not self.cmb_model.view().isVisible():
                QTimer.singleShot(0, self.cmb_model.showPopup)
        return super().eventFilter(obj, event)

    def refresh_summary(self, keys_list=None, model_name=None):
        if keys_list is None and hasattr(self, "inp_api_key"):
            raw_text = self.inp_api_key.toPlainText()
            keys_list = [k.strip() for k in raw_text.replace(',', '\n').split('\n') if k.strip()]
        if model_name is None and hasattr(self, "cmb_model"):
            model_name = self.cmb_model.currentText().split(" ")[0].strip()
        if hasattr(self, "lbl_key_count") and keys_list is not None:
            self.lbl_key_count.setText(f"{len(keys_list)} adet")
        if hasattr(self, "lbl_active_model"):
            self.lbl_active_model.setText(model_name if model_name else "Seçilmedi")
        self.update_autonomous_summary()

    def update_autonomous_summary(self):
        enabled = False
        if hasattr(self, "toggles") and "jarvis_enabled" in self.toggles:
            enabled = self.toggles["jarvis_enabled"].isChecked()
        else:
            enabled = self.db.get_setting("jarvis_enabled", "0") == "1"
        if hasattr(self, "lbl_auto_state"):
            self.lbl_auto_state.setText("Aktif" if enabled else "Kapalı")
            self.lbl_auto_state.setStyleSheet(theme_qss(
                f"color: {DesignTokens.STATUS_SUCCESS_FG if enabled else DesignTokens.MUTED_FOREGROUND}; border:none;"
            ))

    def load_data(self):
        # API - Load multiline
        keys_str = self.db.get_setting("gemini_api_key", "")
        
        # If no keys are set, ensure it's empty
        if not keys_str:
            keys_str = ""
            
        # Convert comma to newlines if exists for better view
        formatted_keys = keys_str.replace(",", "\n")
        self.inp_api_key.setText(formatted_keys)
        
        saved_model = self.db.get_setting("gemini_model", DEFAULT_GEMINI_MODEL)
        current_model = normalize_gemini_model(saved_model)
        if current_model != saved_model:
            self.db.set_setting("gemini_model", current_model)
        self._load_cached_models()
        self.cmb_model.blockSignals(True)
        idx = self.cmb_model.findText(current_model, Qt.MatchFlag.MatchContains)
        if idx >= 0:
            self.cmb_model.setCurrentIndex(idx)
        else:
            self.cmb_model.insertItem(0, f"{current_model} (Kay\u0131tl\u0131)", current_model)
            self.cmb_model.setCurrentIndex(0)
        self.cmb_model.blockSignals(False)
        
        # WhatsApp
        self.inp_wa_token.setText(self.db.get_setting("whatsapp_api_token", ""))
        self.inp_wa_phone.setText(self.db.get_setting("whatsapp_admin_phone", ""))
        
        # Toggles
        for key, toggle in self.toggles.items():
            # Default logic handles "1" or "0"
            enabled_by_default = {
                "jarvis_enabled",
                "jarvis_intel_enabled",
                "assistant_fab_enabled",
            }
            val = self.db.get_setting(key, "1" if key in enabled_by_default else "0")
            toggle.setChecked(val == "1")
            
        # Update Badge
        if self.inp_api_key.toPlainText():
            self.status_badge.setText("KURULUM YAPILDI")
            self.status_badge.setStyleSheet(theme_qss(f"""
                color: {DesignTokens.STATUS_SUCCESS_FG}; font-weight: 700; padding: 6px 12px; 
                background: {DesignTokens.STATUS_SUCCESS_BG}; border-radius: 12px; border: 1px solid {DesignTokens.BORDER};
            """))
        else:
            self.status_badge.setText("ANAHTAR EKSİK")
            self.status_badge.setStyleSheet(theme_qss(f"""
                color: {DesignTokens.STATUS_DANGER_FG}; font-weight: 700; padding: 6px 12px; 
                background: {DesignTokens.STATUS_DANGER_BG}; border-radius: 12px; border: 1px solid {DesignTokens.BORDER};
            """))
        self.refresh_summary(keys_list=[k for k in formatted_keys.split("\n") if k.strip()], model_name=current_model)

    def _load_cached_models(self):
        try:
            if hasattr(self.db, "get_internal_setting"):
                raw_cache = self.db.get_internal_setting("gemini_available_models_cache", "")
            else:
                raw_cache = self.db.get_setting("gemini_available_models_cache", "")
            models = json.loads(raw_cache) if raw_cache else []
            if not isinstance(models, list):
                return
            existing = {self.cmb_model.itemText(i).split(" ")[0] for i in range(self.cmb_model.count())}
            for model in models:
                model_name = normalize_gemini_model(model)
                if model_name and model_name not in existing:
                    self.cmb_model.addItem(model_name)
                    existing.add(model_name)
        except Exception as e:
            logger.warning(f"Cached Gemini models could not be loaded: {e}")

    def save_data(self):
        # Save Basic
        # Format keys: replace newlines with commas and strip empty ones
        raw_text = self.inp_api_key.toPlainText()
        keys_list = [k.strip() for k in raw_text.replace(',', '\n').split('\n') if k.strip()]
        keys_str = ",".join(keys_list) # Store as comma separated
        
        self.db.set_setting("gemini_api_key", keys_str)
        model = normalize_gemini_model(self.cmb_model.currentText())
        self.db.set_setting("gemini_model", model)
        self.db.set_setting("whatsapp_api_token", self.inp_wa_token.text().strip())
        self.db.set_setting("whatsapp_admin_phone", self.inp_wa_phone.text().strip())
        
        # Save Toggles
        for key, toggle in self.toggles.items():
            val = "1" if toggle.isChecked() else "0"
            self.db.set_setting(key, val)
            
        show_success(self, f"Yapılandırma Kaydedildi!\n{len(keys_list)} Adet API Anahtarı havuza eklendi.")
        
        if keys_list:
            self.status_badge.setText("KURULUM YAPILDI")
            self.status_badge.setStyleSheet(theme_qss(f"""
                color: {DesignTokens.STATUS_SUCCESS_FG}; font-weight: 700; padding: 6px 12px; 
                background: {DesignTokens.STATUS_SUCCESS_BG}; border-radius: 12px; border: 1px solid {DesignTokens.BORDER};
            """))
        else:
            self.status_badge.setText("ANAHTAR EKSİK")
            self.status_badge.setStyleSheet(theme_qss(f"""
                color: {DesignTokens.STATUS_DANGER_FG}; font-weight: 700; padding: 6px 12px; 
                background: {DesignTokens.STATUS_DANGER_BG}; border-radius: 12px; border: 1px solid {DesignTokens.BORDER};
            """))
        self.refresh_summary(keys_list=keys_list, model_name=model)
        
        # Notify Main Window
        if getattr(self.main_window, 'assistant_sidebar', None):
            if getattr(self.main_window.assistant_sidebar, 'ai_service', None):
                self.main_window.assistant_sidebar.ai_service.api_keys = keys_list
                # Trigger setup with first key if available
                if keys_list:
                     self.main_window.assistant_sidebar.ai_service.current_key_index = 0
                     self.main_window.assistant_sidebar.ai_service.setup_gemini(keys_list[0])
            else:
                pass # Silent fail or log if logger available


    def test_connection(self):
        raw_text = self.inp_api_key.toPlainText()
        keys_list = [k.strip() for k in raw_text.replace(',', '\n').split('\n') if k.strip()]
        
        if not keys_list:
            show_error(self, "Hata", "Test etmeden önce en az bir API anahtarı girmelisiniz.")
            return
            
        self.btn_test.setText("⏳ HAVUZ TEST EDİLİYOR...")
        self.btn_test.setEnabled(False)
        
        # Threaded Worker
        self.worker = TestWorker(self.cmb_model.currentText().split(" ")[0], keys_list)
        self.worker.finished.connect(self.on_test_finished)
        self.worker.start()

    def test_manual_connection(self):
        """Sadece manuel girilen model adresini test eder"""
        model_name = self.cmb_model.currentText().strip().split(" ")[0]
        if not model_name:
            show_warning(self, "Lütfen bir model adresi girin.")
            return

        raw_text = self.inp_api_key.toPlainText()
        keys_list = [k.strip() for k in raw_text.replace(',', '\n').split('\n') if k.strip()]
        
        if not keys_list:
             show_error(self, "API Anahtarı eksik.")
             return
             
        self.btn_manual_connect.setText("\u23f3")
        self.btn_manual_connect.setEnabled(False)
        
        # Tek kullanımlık worker ile test et
        self.worker = TestWorker(model_name, keys_list)
        self.worker.finished.connect(self.on_manual_test_finished)
        self.worker.start()

    def on_manual_test_finished(self, success, result_data):
        self.btn_manual_connect.setText("BAĞLAN")
        self.btn_manual_connect.setEnabled(True)
        
        if success:
             ans = result_data.get('answer','')
             show_success(self, f"Bağlantı Başarılı!\nModel: {self.worker.model_name}\nJarvis: {ans}")
             self.status_badge.setText("✅ BAĞLANDI")
             self.status_badge.setStyleSheet(theme_qss("color: @selection_text; font-weight: bold; padding: 6px 12px; background: @success; border-radius: 15px;"))
        else:
             err = result_data.get('error', 'Hata')
             show_error(self, f"Bu model adresiyle bağlantı kurulamadı.\n{err}")

    def on_test_finished(self, success, result_data):
        self.btn_test.setEnabled(True)
        self.btn_test.setText("\u26a1 API HAVUZUNU TEST ET")
        
        if success:
             active_key = result_data.get('key', 'Unknown')
             answer = result_data.get('answer', '')
             show_success(self, f"Bağlantı Başarılı!\nAktif Anahtar: {active_key[:8]}...\nCevap: {answer}")
             self.status_badge.setText("✅ HAVUZ AKTİF")
             self.status_badge.setStyleSheet(theme_qss("color: @selection_text; font-weight: bold; padding: 6px 12px; background: @success; border-radius: 15px;"))
        else:
             err_msg = result_data.get('error', 'Bilinmeyen Hata')
             show_error(self, f"Test Başarısız: Tüm anahtarlar denendi.\nSon Hata: {err_msg}")
             self.status_badge.setText("❌ BAĞLANTI HATASI")

    def list_available_models(self):
        raw_text = self.inp_api_key.toPlainText()
        keys_list = [k.strip() for k in raw_text.replace(',', '\n').split('\n') if k.strip()]
        if not keys_list:
            show_error(self, "Lütfen önce bir API anahtarı girin.")
            return

        if hasattr(self, "btn_list_models"):
            self.btn_list_models.setEnabled(False)
            self.btn_list_models.setText("Listeleniyor...")

        self.model_list_worker = ModelListWorker(keys_list)
        self.model_list_worker.finished.connect(self.on_models_listed)
        self.model_list_worker.finished.connect(self.model_list_worker.deleteLater)
        self.model_list_worker.start()

    def on_models_listed(self, success, result):
        if hasattr(self, "btn_list_models"):
            self.btn_list_models.setEnabled(True)
            self.btn_list_models.setText("Modelleri Listele")

        if success and result:
            display_models = [str(m).replace('models/', '') for m in result]
            dlg = ModelListDialog(display_models, parent=self, callback=self.use_selected_model)
            dlg.exec()
        else:
            message = result if isinstance(result, str) else "API anahtarlarınızı kontrol edin."
            show_error(self, f"Modeller listelenemedi. {message}")

    def use_selected_model(self, model_name):
        idx = self.cmb_model.findText(model_name, Qt.MatchFlag.MatchContains)
        if idx == -1:
             self.cmb_model.insertItem(0, f"{model_name} (AYECtan)")
             self.cmb_model.setCurrentIndex(0)
        else:
             self.cmb_model.setCurrentIndex(idx)
        show_success(self, f"Model seçildi: {model_name}")




class TestWorker(QThread):
    finished = pyqtSignal(bool, dict)

    def __init__(self, model_name, keys_list):
        super().__init__()
        self.model_name = model_name
        self.keys_list = keys_list

    def run(self):
        try:
            from src.utils.ai_service import AIService
            srv = AIService(self.keys_list, model_name=self.model_name)
            srv.api_keys = self.keys_list
            
            success_key = None
            last_result = None
            
            for i, key in enumerate(self.keys_list):
                srv.current_key_index = i
                if srv.setup_gemini(key):
                    res = srv.ask_jarvis("Sistem bağlantı testi. Durum nedir")
                    if res['success']:
                        success_key = key
                        last_result = res
                        break
                    else:
                        last_result = res
                        continue
                else:
                     pass
            
            if success_key and last_result:
                self.finished.emit(True, {'key': success_key, 'answer': last_result['answer']})
            else:
                err = last_result['answer'] if last_result else "Bilinmeyen Hata"
                self.finished.emit(False, {'error': err})
        except Exception as e:
            self.finished.emit(False, {'error': str(e)})


class ModelListDialog(ModernDialog):
    """Modern ve Premium Model Listesi Dialogu"""
    def __init__(self, models, parent=None, callback=None):
        super().__init__(parent)
        self.callback = callback
        self.setWindowTitle("Erişilebilir Yapay Zeka Modelleri")
        self.setFixedSize(500, 600)
        self.setStyleSheet(theme_qss("""
            QDialog { background-color: @surface; }
            QLabel { font-family: 'Segoe UI'; }
        """))
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        header = QFrame()
        header.setStyleSheet(theme_qss("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 @accent, stop:1 @accent);"))
        header.setFixedHeight(100)
        hl = QVBoxLayout(header)
        hl.setContentsMargins(25, 25, 25, 25)
        
        h_title = QLabel("🤖 Aktif Modeller")
        h_title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        h_title.setStyleSheet(theme_qss("color: @selection_text;"))
        hl.addWidget(h_title)
        
        h_sub = QLabel(f"Hesabınızda {len(models)} adet model aktif.")
        h_sub.setStyleSheet(theme_qss("color: @selection_text; font-size: 14px;"))
        hl.addWidget(h_sub)
        
        layout.addWidget(header)
        
        # List Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(theme_qss("QScrollArea { background: transparent; }"))
        
        content = QWidget()
        content.setStyleSheet(theme_qss("background: @surface_alt;"))
        cl = QVBoxLayout(content)
        cl.setSpacing(15)
        cl.setContentsMargins(20, 20, 20, 20)
        
        for m in models:
            card = QFrame()
            card.setStyleSheet(theme_qss("""
                QFrame {
                    background-color: @surface;
                    border-radius: 12px;
                    border: 1px solid @border;
                }
                QFrame:hover {
                    border: 1px solid @accent;
                    background-color: @surface_alt;
                }
            """))
            card.setFixedHeight(70)
            
            # Shadow
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(10)
            shadow.setColor(QColor(0,0,0,15))
            shadow.setOffset(0, 2)
            card.setGraphicsEffect(shadow)
            
            # Make clickable
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            
            # Simple click handler using event filter or custom logic requires more code.
            # Using a transparent button overlay is easier.
            btn_overlay = QPushButton(card)
            btn_overlay.setStyleSheet(theme_qss("background: transparent; border: none;"))
            btn_overlay.setFixedSize(440, 70) # Approx size of card
            btn_overlay.clicked.connect(lambda checked, m=m: self.on_model_clicked(m))
            
            # Layout logic
            row = QHBoxLayout(card)
            row.setContentsMargins(15, 10, 15, 10)
            
            icon_lbl = QLabel("✨")
            icon_lbl.setFont(QFont("Segoe UI Emoji", 18))
            icon_lbl.setStyleSheet(theme_qss("border:none; background:transparent;"))
            row.addWidget(icon_lbl)
            
            text_lay = QVBoxLayout()
            text_lay.setSpacing(2)
            
            m_name = QLabel(m)
            m_name.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            m_name.setStyleSheet(theme_qss("color: @text; border:none; background:transparent;"))
            
            m_desc = QLabel("Google DeepMind")
            m_desc.setFont(QFont("Segoe UI", 9))
            m_desc.setStyleSheet(theme_qss("color: @disabled_text; border:none; background:transparent;"))
            
            text_lay.addWidget(m_name)
            text_lay.addWidget(m_desc)
            row.addLayout(text_lay)
            
            row.addStretch()
            
            # Select/Check Icon (Visual only)
            chk = QLabel("Seç")
            chk.setStyleSheet(theme_qss("color: @accent; font-weight: bold; font-size: 13px; border: 1px solid @accent; border-radius: 5px; padding: 4px 10px;"))
            row.addWidget(chk)
            
            cl.addWidget(card)
            
        cl.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        # Footer
        footer = QFrame()
        footer.setStyleSheet(theme_qss("background: @surface; border-top: 1px solid @border;"))
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(20, 15, 20, 15)
        
        fl.addStretch()
        btn_close = QPushButton("Kapat")
        btn_close.setFixedSize(120, 40)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @surface_alt;
                color: @text;
                border: none;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: @border; }
        """))
        btn_close.clicked.connect(self.accept)
        fl.addWidget(btn_close)
        
        layout.addWidget(footer)
        
    def on_model_clicked(self, model_name):
        if self.callback:
            self.callback(model_name)
        self.accept()
