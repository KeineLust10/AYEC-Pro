# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QComboBox, QLineEdit, QGroupBox, QFormLayout)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from src.ui.widgets.animated_toggle import AnimatedToggle
from src.utils.theme_colors import theme_qss, tc
from src.utils.toast_notification import show_success, show_error, show_info
from src.utils.design_system import DesignTokens



class VoiceAssistantSettingsWidget(QWidget):

    def _on_ui_widget_changed(self, *args):
        if getattr(self, "_loading_settings", False):
            return
        self._save_all(show_feedback=False)
    """Voice Assistant Settings with Form Layout (Toggle switches, dropdowns, inputs)"""
    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self._build_ui()
        self._loading_settings = True
        self._load_settings()
        self._loading_settings = False
        self._wire_ui_signals()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(18)

        # Top Bar with Title (Compact)
        top_bar = QFrame()
        top_bar.setStyleSheet(theme_qss("""
            QFrame {
                background: @surface_alt;
                border-radius: 10px;
                padding: 12px;
            }
        """))
        
        top_layout = QVBoxLayout(top_bar)
        top_layout.setContentsMargins(18, 12, 18, 12)
        top_layout.setSpacing(4)
        
        title = QLabel("🎙️ Sesli Asistan Ayarları")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("color: @text; background: transparent;"))
        top_layout.addWidget(title)
        
        subtitle = QLabel("Asistanınızın davranışlarını, ses özelliklerini ve hitap şeklini özelleştirin.")
        subtitle.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; background: transparent;"))
        subtitle.setWordWrap(True)
        top_layout.addWidget(subtitle)
        
        layout.addWidget(top_bar)

        # Main Settings Card
        card = QFrame()
        card.setStyleSheet(theme_qss("""
            QFrame {
                background: @surface;
                border: 1px solid @border;
                border-radius: 14px;
            }
        """))
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 28, 28, 28)
        card_layout.setSpacing(20)

        # Ana Asistan Aç/Kapat
        self.toggle_assistant_active = AnimatedToggle(active_color=tc("success"))
        row_main = self._create_setting_row("🎙️ Asistanı Aktif Et", "Sesli asistanı tamamen açıp kapatın", self.toggle_assistant_active)
        card_layout.addWidget(row_main)

        # Separator
        sep_main = QFrame()
        sep_main.setFrameShape(QFrame.Shape.HLine)
        sep_main.setStyleSheet(theme_qss("background: @border; max-height: 1px;"))
        card_layout.addWidget(sep_main)

        # Sesli Onay Ver
        self.toggle_voice = AnimatedToggle(active_color=tc("accent"))
        row1 = self._create_setting_row("🔊 Sesli Onay Ver", "Asistan komutları sesli olarak onaylasın", self.toggle_voice)
        card_layout.addWidget(row1)

        # Telsiz/Radyo Efekti
        self.toggle_radio = AnimatedToggle(active_color=tc("accent"))
        row2 = self._create_setting_row("📻 Telsiz/Radyo Efekti", "Seste radyo efekti uygulasın", self.toggle_radio)
        card_layout.addWidget(row2)

        # Adımla Hitap Et
        self.toggle_hitap = AnimatedToggle(active_color=tc("success"))
        row3 = self._create_setting_row("👤 Adımla Hitap Et", "Asistan size adınızla hitap etsin", self.toggle_hitap)
        card_layout.addWidget(row3)

        # Separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setStyleSheet(theme_qss("background: @border; max-height: 1px;"))
        card_layout.addWidget(sep1)

        # Ses Tonu
        self.cmb_tone = QComboBox()
        self.cmb_tone.addItems(["Kalın", "Normal", "İnce"])
        self.cmb_tone.setStyleSheet(theme_qss(self._get_combobox_style()))
        row4 = self._create_setting_row("🎵 Ses Tonu", "Ses kalınlığı/inceliği", self.cmb_tone)
        card_layout.addWidget(row4)

        # Ses Seçimi (Premium)
        self.cmb_voice = QComboBox()
        self.cmb_voice.addItems(["Ahmet (Kalın)", "Emel (Profesyonel)"])
        self.cmb_voice.setStyleSheet(theme_qss(self._get_combobox_style()))
        row5 = self._create_setting_row("🎤 Ses Seçimi (Premium)", "Edge TTS ses karakteri", self.cmb_voice)
        card_layout.addWidget(row5)

        # Ses Motoru
        self.cmb_engine = QComboBox()
        self.cmb_engine.addItems(["Otomatik", "Sistem", "Premium (Edge TTS)"])
        self.cmb_engine.setStyleSheet(theme_qss(self._get_combobox_style()))
        row6 = self._create_setting_row("⚙️ Ses Motoru", "TTS motoru seçimi", self.cmb_engine)
        card_layout.addWidget(row6)

        # Ses Hızı
        self.cmb_rate = QComboBox()
        self.cmb_rate.addItems(["Yavaş", "Normal", "Hızlı"])
        self.cmb_rate.setStyleSheet(theme_qss(self._get_combobox_style()))
        row7 = self._create_setting_row("⏩ Ses Hızı", "Konuşma hızı ayarı", self.cmb_rate)
        card_layout.addWidget(row7)

        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(theme_qss("background: @border; max-height: 1px;"))
        card_layout.addWidget(sep2)

        # Kullanıcı Adı
        self.inp_user_name = QLineEdit()
        self.inp_user_name.setPlaceholderText("Efendim")
        self.inp_user_name.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        row8 = self._create_setting_row("👨 Kullanıcı Adı", "Asistanın size hitap şekli", self.inp_user_name)
        card_layout.addWidget(row8)

        # Asistan Adı
        self.inp_assistant_name = QLineEdit()
        self.inp_assistant_name.setPlaceholderText("AYEC")
        self.inp_assistant_name.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        row9 = self._create_setting_row("🤖 Asistan Adı", "Asistanınızın özel adı", self.inp_assistant_name)
        card_layout.addWidget(row9)

        layout.addWidget(card)

        # Save Button
        btn_save = QPushButton("💾 Tümünü Kaydet")
        btn_save.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="lg")))
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(self._save_all)
        layout.addWidget(btn_save)

        layout.addStretch()

    def _get_combobox_style(self):
        """Premium combobox styling with solid light dropdown"""
        return """
            QComboBox {
                background-color: @surface;
                color: @text;
                border: 1px solid @border;
                border-radius: 8px;
                padding: 8px 12px;
                font-family: 'Segoe UI';
                font-size: 13px;
                min-height: 20px;
            }
            QComboBox:hover {
                border: 1px solid @accent;
                background-color: @surface_alt;
            }
            QComboBox:focus {
                border: 2px solid @accent;
                background-color: @surface;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
                background: transparent;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid @text_muted;
                width: 0;
                height: 0;
                margin-right: 8px;
            }
            QComboBox::down-arrow:hover {
                border-top-color: @accent;
            }
            QComboBox QAbstractItemView {
                background-color: @surface;
                border: 1px solid @border;
                border-radius: 8px;
                padding: 4px;
                selection-background-color: @selection_bg;
                selection-color: @selection_text;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                padding: 10px 12px;
                border-radius: 4px;
                min-height: 24px;
                background-color: @surface;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: @surface_alt;
                color: @text;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: @selection_bg;
                color: @selection_text;
            }
        """

    def _create_setting_row(self, title, description, widget):
        """Create a setting row with title, description, and widget"""
        container = QFrame()
        container.setStyleSheet(theme_qss("background: transparent; border: none;"))
        container.setMinimumHeight(60)
        
        h_layout = QHBoxLayout(container)
        h_layout.setContentsMargins(0, 12, 0, 12)
        h_layout.setSpacing(20)
        
        # Left: Title and Description
        v_layout = QVBoxLayout()
        v_layout.setSpacing(4)
        
        lbl_title = QLabel(title)
        lbl_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_title.setStyleSheet(theme_qss("color: @text; background: transparent;"))
        v_layout.addWidget(lbl_title)
        
        lbl_desc = QLabel(description)
        lbl_desc.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; background: transparent;"))
        lbl_desc.setWordWrap(True)
        v_layout.addWidget(lbl_desc)
        
        h_layout.addLayout(v_layout, 1)
        
        # Right: Widget
        widget.setFixedWidth(220)
        if hasattr(widget, 'minimumSizeHint'):
            widget.setMinimumHeight(36)
        h_layout.addWidget(widget, 0, Qt.AlignmentFlag.AlignVCenter)
        
        return container

    def _load_settings(self):
        """Load settings from database"""
        self.toggle_assistant_active.setChecked(self.db.get_setting("voice_assistant_active", "1") == "1")
        self.toggle_voice.setChecked(self.db.get_setting("asistan_voice_enabled", "1") == "1")
        self.toggle_radio.setChecked(self.db.get_setting("telsiz_efekti_aktif", "0") == "1")
        self.toggle_hitap.setChecked(self.db.get_setting("asistan_hitap_aktif", "0") == "1")
        
        # Tone
        pitch = self.db.get_setting("asistan_edge_pitch", "-5Hz")
        tone = "Kalın" if "-" in pitch else ("İnce" if "+" in pitch else "Normal")
        self.cmb_tone.setCurrentText(tone)
        
        # Voice
        voice = self.db.get_setting("asistan_edge_voice", "tr-TR-AhmetNeural")
        self.cmb_voice.setCurrentText("Ahmet (Kalın)" if "Ahmet" in voice else "Emel (Profesyonel)")
        
        # Engine
        engine = self.db.get_setting("asistan_tts_engine", "auto")
        engine_map = {"auto": "Otomatik", "system": "Sistem", "edge": "Premium (Edge TTS)"}
        self.cmb_engine.setCurrentText(engine_map.get(engine, "Otomatik"))
        
        # Rate
        rate = self.db.get_setting("asistan_edge_rate", "+0%")
        rate_map = {"-10%": "Yavaş", "+0%": "Normal", "+10%": "Hızlı"}
        self.cmb_rate.setCurrentText(rate_map.get(rate, "Normal"))
        
        # Names
        self.inp_user_name.setText(self.db.get_setting("asistan_user_name", "Efendim"))
        self.inp_assistant_name.setText(self.db.get_setting("asistan_ozel_adi", "AYEC"))

    def _save_all(self, show_feedback=True):
        """Save all settings to database"""
        self.db.set_setting("voice_assistant_active", "1" if self.toggle_assistant_active.isChecked() else "0")
        self.db.set_setting("asistan_voice_enabled", "1" if self.toggle_voice.isChecked() else "0")
        self.db.set_setting("telsiz_efekti_aktif", "1" if self.toggle_radio.isChecked() else "0")
        self.db.set_setting("asistan_hitap_aktif", "1" if self.toggle_hitap.isChecked() else "0")
        
        # Tone
        tone_map = {"Kalın": "-5Hz", "Normal": "+0Hz", "İnce": "+10Hz"}
        self.db.set_setting("asistan_edge_pitch", tone_map[self.cmb_tone.currentText()])
        
        # Voice
        voice = "tr-TR-AhmetNeural" if "Ahmet" in self.cmb_voice.currentText() else "tr-TR-EmelNeural"
        self.db.set_setting("asistan_edge_voice", voice)
        
        # Engine
        engine_map = {"Otomatik": "auto", "Sistem": "system", "Premium (Edge TTS)": "edge"}
        self.db.set_setting("asistan_tts_engine", engine_map[self.cmb_engine.currentText()])
        
        # Rate
        rate_map = {"Yavaş": "-10%", "Normal": "+0%", "Hızlı": "+10%"}
        self.db.set_setting("asistan_edge_rate", rate_map[self.cmb_rate.currentText()])
        
        # Names
        self.db.set_setting("asistan_user_name", self.inp_user_name.text())
        self.db.set_setting("asistan_ozel_adi", self.inp_assistant_name.text())
        
        if show_feedback:
            show_success(self.main_window or self, "Tüm ayarlar başarıyla kaydedildi!")



    def _wire_ui_signals(self):
        self.toggle_assistant_active.toggled.connect(self._on_ui_widget_changed)
        self.toggle_voice.toggled.connect(self._on_ui_widget_changed)
        self.toggle_radio.toggled.connect(self._on_ui_widget_changed)
        self.toggle_hitap.toggled.connect(self._on_ui_widget_changed)
        self.cmb_tone.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_voice.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_engine.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_rate.currentIndexChanged.connect(self._on_ui_widget_changed)
