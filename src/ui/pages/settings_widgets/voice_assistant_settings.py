# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QComboBox, QLineEdit, QGroupBox, QFormLayout, QGridLayout)
from PyQt6.QtCore import Qt, QSignalBlocker
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
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Top Bar with Title (Compact)
        top_bar = QFrame()
        top_bar.setObjectName("voiceSettingsHeader")
        top_bar.setFixedHeight(116)
        top_bar.setStyleSheet(theme_qss("""
            QFrame#voiceSettingsHeader {
                background: @surface_alt;
                border-radius: 6px;
            }
        """))
        
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(18, 12, 18, 12)
        top_layout.setSpacing(4)
        title_block = QVBoxLayout()
        title_block.setSpacing(3)
        title = QLabel("[VOICE] Sesli Asistan & TTS Motoru")
        title.setFont(QFont(self.font().family(), 11, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("color: @text; background: transparent; border: none; padding: 0;"))
        title_block.addWidget(title)
        
        subtitle = QLabel("Configure the local Turkish voice assistant and reminder schedule.")
        subtitle.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; background: transparent; border: none; padding: 0;"))
        subtitle.setWordWrap(True)
        title_block.addWidget(subtitle)
        top_layout.addLayout(title_block, 1)
        btn_defaults = QPushButton("Varsay\u0131lanlara D\u00f6n")
        btn_defaults.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_defaults.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="md")))
        btn_defaults.clicked.connect(self._load_settings)
        top_layout.addWidget(btn_defaults)
        btn_header_save = QPushButton("Ayarlar\u0131 Kaydet")
        btn_header_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_header_save.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="md")))
        btn_header_save.clicked.connect(lambda: self._save_all(show_feedback=True))
        self.header_save_button = btn_header_save
        self.reload_button = btn_defaults
        btn_defaults.setText("Kaydedileni Y\u00fckle")
        top_layout.addWidget(btn_header_save)
        
        layout.addWidget(top_bar)

        # Main Settings Card
        card = QFrame()
        card.setObjectName("voiceProtocolCard")
        card.setStyleSheet(theme_qss("""
            QFrame#voiceProtocolCard {
                background: @surface;
                border: 1px solid @border;
                border-radius: 6px;
            }
        """))
        
        card_layout = QGridLayout(card)
        card_layout.setContentsMargins(18, 14, 18, 14)
        card_layout.setHorizontalSpacing(14)
        card_layout.setVerticalSpacing(10)
        card_layout.setColumnStretch(0, 1)
        card_layout.setColumnStretch(1, 1)
        synthesis_card = QFrame()
        synthesis_card.setObjectName("voiceSynthesisCard")
        synthesis_card.setStyleSheet(theme_qss("QFrame#voiceSynthesisCard { background: @finance_surface; border: 1px solid @finance_outline; border-radius: 6px; }"))
        synthesis_grid = QGridLayout(synthesis_card)
        synthesis_grid.setContentsMargins(18, 14, 18, 14)
        synthesis_grid.setSpacing(8)
        synthesis_grid.setColumnStretch(0, 1)
        synthesis_grid.setColumnStretch(1, 1)
        synthesis_heading = QLabel("Speech Synthesis (EMA Lightning TR)")
        synthesis_heading.setStyleSheet(theme_qss("color: @text; font-size: 11px; font-weight: 700; border: none;"))
        synthesis_grid.addWidget(synthesis_heading, 0, 0, 1, 2)

        # Ana Asistan Aç/Kapat
        self.toggle_assistant_active = AnimatedToggle(active_color=tc("success"))
        row_main = self._create_setting_row("Asistan & Hitap Protokol\u00fc", "Sesli komut yan\u0131tlar\u0131 ve telsiz ses efektleri", self.toggle_assistant_active)
        card_layout.addWidget(row_main, 0, 0, 1, 2)

        # Separator
        sep_main = QFrame()
        sep_main.setFrameShape(QFrame.Shape.HLine)
        sep_main.setStyleSheet(theme_qss("background: @border; max-height: 1px;"))
        sep_main.deleteLater()

        # Sesli Onay Ver
        self.toggle_voice = AnimatedToggle(active_color=tc("accent"))
        row1 = self._create_setting_row("Sesli Onay Ver", "Komutlar\u0131 sesli olarak onayla", self.toggle_voice)
        card_layout.addWidget(row1, 1, 1)

        # Telsiz/Radyo Efekti
        self.toggle_radio = AnimatedToggle(active_color=tc("accent"))
        row2 = self._create_setting_row("Telsiz / Walkie-Talkie Efekti", "Anons \u00f6ncesi ve sonras\u0131 h\u0131\u015f\u0131rt\u0131 sesi", self.toggle_radio)
        card_layout.addWidget(row2, 1, 0)

        # Adımla Hitap Et
        self.toggle_hitap = AnimatedToggle(active_color=tc("success"))
        row3 = self._create_setting_row("Ad\u0131mla Hitap Et", "Ki\u015fiselle\u015ftirilmi\u015f hitap", self.toggle_hitap)
        card_layout.addWidget(row3, 3, 0, 1, 2)

        # Separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setStyleSheet(theme_qss("background: @border; max-height: 1px;"))
        sep1.deleteLater()

        # Ses Tonu
        self.cmb_tone = QComboBox()
        self.cmb_tone.addItems(["Model Varsay\u0131lan\u0131"])
        self.cmb_tone.setEnabled(False)
        self.cmb_tone.setStyleSheet(theme_qss(self._get_combobox_style()))
        row4 = self._create_setting_row("PERDE AYARI", "Do\u011fal perde ve vurgu yerel model taraf\u0131ndan korunur.", self.cmb_tone)
        synthesis_grid.addWidget(row4, 2, 1)

        # Ses Seçimi (Premium)
        self.cmb_voice = QComboBox()
        self.cmb_voice.addItem("EMA Do\u011fal T\u00fcrk\u00e7e Ses", "ema_default")
        self.cmb_voice.setStyleSheet(theme_qss(self._get_combobox_style()))
        row5 = self._create_setting_row("SES MODELI", "T\u00fcrk\u00e7e i\u00e7in e\u011fitilmi\u015f tek ses; rakam ve TL tutarlar\u0131 do\u011fal okunur.", self.cmb_voice)
        synthesis_grid.addWidget(row5, 1, 0)

        # Ses Motoru
        self.cmb_engine = QComboBox()
        self.cmb_engine.addItems(["EMA Lightning (Yerel)"])
        self.cmb_engine.setStyleSheet(theme_qss(self._get_combobox_style()))
        row6 = self._create_setting_row("SES MOTORU", "\u00c7evrimd\u0131\u015f\u0131 \u00e7al\u0131\u015f\u0131r; ilk kullan\u0131mda 34 MB model indirilir.", self.cmb_engine)
        synthesis_grid.addWidget(row6, 1, 1)

        # Ses Hızı
        self.cmb_rate = QComboBox()
        self.cmb_rate.addItems(["Model Varsay\u0131lan\u0131"])
        self.cmb_rate.setEnabled(False)
        self.cmb_rate.setStyleSheet(theme_qss(self._get_combobox_style()))
        row7 = self._create_setting_row("KONU\u015eMA HIZI", "Do\u011fal konu\u015fma h\u0131z\u0131 model taraf\u0131ndan belirlenir.", self.cmb_rate)
        synthesis_grid.addWidget(row7, 2, 0)

        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(theme_qss("background: @border; max-height: 1px;"))
        sep2.deleteLater()

        # Kullanıcı Adı
        self.inp_user_name = QLineEdit()
        self.inp_user_name.setPlaceholderText("Efendim")
        self.inp_user_name.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        row8 = self._create_setting_row("HITAP ONEKI (PREFIX)", "Asistan\u0131n size hitap \u015fekli", self.inp_user_name)
        card_layout.addWidget(row8, 2, 0)

        # Asistan Adı
        self.inp_assistant_name = QLineEdit()
        self.inp_assistant_name.setPlaceholderText("AYEC")
        self.inp_assistant_name.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        row9 = self._create_setting_row("\u00c7A\u011eRI I\u015eARETI (CALL SIGN)", "Sistem anonslar\u0131ndan \u00f6nce okunur", self.inp_assistant_name)
        card_layout.addWidget(row9, 2, 1)

        speech_preview = QFrame()
        speech_preview.setStyleSheet(theme_qss("QFrame { background: @surface_alt; border: 1px solid @border; border-radius: 7px; }"))
        speech_layout = QHBoxLayout(speech_preview)
        speech_layout.setContentsMargins(10, 8, 10, 8)
        speech_text = QVBoxLayout()
        speech_title = QLabel("Speech Synthesis (EMA Lightning TR)")
        speech_title.setStyleSheet(theme_qss("color: @text; font-weight: 800; border: none;"))
        speech_desc = QLabel("Yapay zeka ses modeli ve tonlama parametrelerini test edin.")
        speech_desc.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px; border: none;"))
        speech_text.addWidget(speech_title)
        speech_text.addWidget(speech_desc)
        speech_layout.addLayout(speech_text, 1)
        speech_test = QPushButton("Ses Testini Oynat")
        speech_test.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        speech_test.clicked.connect(self._play_speech_preview)
        self.speech_test = speech_test
        speech_layout.addWidget(speech_test)
        synthesis_grid.addWidget(speech_preview, 3, 0, 1, 2)

        workspace = QHBoxLayout()
        workspace.setSpacing(10)
        left_panel = QVBoxLayout()
        left_panel.setSpacing(8)
        left_panel.addWidget(card)
        left_panel.addWidget(synthesis_card)
        left_panel.addStretch()
        workspace.addLayout(left_panel, 2)

        side_panel = QVBoxLayout()
        side_panel.setSpacing(10)
        for title_text, subtitle_text, rows in (
            ("Vokal Hatirlaticilar", "Zamanlanmis sesli anons kuyrugu", ("Taksit ve Banka Odemeleri", "Cekler ve Senetler", "Kritik Stok Seviyesi")),
            ("Gece Sessiz Saatleri", "Zamanlama motoru hen\u00fcz ba\u011fl\u0131 de\u011fil", ("Ba\u015flang\u0131\u00e7", "Biti\u015f", "Acil Durum Istisnas\u0131")),
        ):
            panel = QFrame()
            panel.setObjectName("voiceSchedulePanel")
            panel.setStyleSheet(theme_qss("QFrame#voiceSchedulePanel { background: @finance_surface; border: 1px solid @finance_outline; border-radius: 6px; }"))
            panel_layout = QVBoxLayout(panel)
            panel_layout.setContentsMargins(14, 12, 14, 12)
            panel_layout.setSpacing(8)
            panel_title = QLabel(title_text)
            panel_title.setFont(QFont(self.font().family(), 10, QFont.Weight.Bold))
            panel_title.setStyleSheet(theme_qss("color: @text; border: none; background: transparent;"))
            panel_layout.addWidget(panel_title)
            panel_desc = QLabel(subtitle_text)
            panel_desc.setWordWrap(True)
            panel_desc.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px; border: none; background: transparent;"))
            panel_layout.addWidget(panel_desc)
            for row_text in rows:
                row = QFrame()
                row.setStyleSheet(theme_qss("background: @surface; border: 1px solid @border; border-radius: 6px;"))
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(8, 7, 8, 7)
                label = QLabel(row_text)
                label.setStyleSheet(theme_qss("color: @text; border: none; background: transparent;"))
                row_layout.addWidget(label)
                row_layout.addStretch()
                state = QLabel("-")
                state.setToolTip("Zamanlama kayd\u0131 / motor ba\u011flant\u0131s\u0131 bulunmuyor.")
                state.setStyleSheet(theme_qss("color: @text_muted; font-weight: 700; border: none; background: transparent;"))
                row_layout.addWidget(state)
                panel_layout.addWidget(row)
            side_panel.addWidget(panel)
        side_panel.addStretch()
        workspace.addLayout(side_panel, 1)
        layout.addLayout(workspace)

        # The original full-save action now uses the reference header control.
        self.save_button = self.header_save_button


    def _get_combobox_style(self):
        """Premium combobox styling with solid light dropdown"""
        return """
            QComboBox {
                background-color: @surface;
                color: @text;
                border: 1px solid @border;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                min-height: 16px;
            }
            QComboBox:hover {
                border: 1px solid @accent;
                background-color: @surface_alt;
            }
            QComboBox:focus {
                border: 1px solid @accent;
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
        container.setMinimumHeight(56)
        
        is_toggle = isinstance(widget, AnimatedToggle)
        if is_toggle:
            widget.setProperty("activeThemeToken", "finance_secondary")
        h_layout = QHBoxLayout(container) if is_toggle else QVBoxLayout(container)
        h_layout.setContentsMargins(4, 4, 4, 4)
        h_layout.setSpacing(4)
        
        # Left: Title and Description
        v_layout = QVBoxLayout()
        v_layout.setSpacing(4)
        
        lbl_title = QLabel(title)
        lbl_title.setFont(QFont(self.font().family(), 9, QFont.Weight.Bold))
        lbl_title.setWordWrap(True)
        lbl_title.setStyleSheet(theme_qss("color: @text; background: transparent;"))
        v_layout.addWidget(lbl_title)
        
        lbl_desc = QLabel(description)
        lbl_desc.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px; background: transparent;"))
        lbl_desc.setWordWrap(True)
        v_layout.addWidget(lbl_desc)
        
        h_layout.addLayout(v_layout, 1)
        
        # Right: Widget
        if is_toggle:
            widget.setFixedSize(40, 24)
            h_layout.addWidget(widget, 0, Qt.AlignmentFlag.AlignVCenter)
        else:
            if isinstance(widget, QLineEdit):
                widget.setStyleSheet(theme_qss("QLineEdit { background: @finance_surface_alt; color: @text; border: 1px solid @finance_outline; border-radius: 4px; padding: 4px 8px; min-height: 16px; font-size: 11px; } QLineEdit:focus { border-color: @finance_primary; }"))
            widget.setFixedHeight(30)
            h_layout.addWidget(widget)
        
        return container

    def _load_settings(self):
        previous = getattr(self, "_loading_settings", False)
        self._loading_settings = True
        widgets = (
            self.toggle_assistant_active, self.toggle_voice, self.toggle_radio,
            self.toggle_hitap, self.cmb_tone, self.cmb_voice, self.cmb_engine,
            self.cmb_rate, self.inp_user_name, self.inp_assistant_name,
        )
        blockers = [QSignalBlocker(widget) for widget in widgets]
        try:
            self._load_settings_values()
        finally:
            del blockers
            self._loading_settings = previous

    def _play_speech_preview(self):
        """Use the existing TTS engine with the currently displayed settings."""
        try:
            from src.utils.asistan_motoru import sesli_cevap_ver_async
            engine = "ema-lightning"
            text = f"{self.inp_assistant_name.text() or 'AYEC'} ses testi, {self.inp_user_name.text() or 'Efendim'}."
            sesli_cevap_ver_async(text, engine, voice=self.cmb_voice.currentData(),
                                 efekt_aktif=self.toggle_radio.isChecked())
        except Exception as error:
            show_error(self, f"Ses testi ba\u015flat\u0131lamad\u0131: {error}")

    def _load_settings_values(self):
        """Load settings from database"""
        self.toggle_assistant_active.setChecked(self.db.get_setting("voice_assistant_active", "0") == "1")
        self.toggle_voice.setChecked(self.db.get_setting("asistan_voice_enabled", "1") == "1")
        self.toggle_radio.setChecked(self.db.get_setting("telsiz_efekti_aktif", "0") == "1")
        self.toggle_hitap.setChecked(self.db.get_setting("asistan_hitap_aktif", "0") == "1")
        
        # Legacy engine preferences remain readable, but are no longer used.
        self.db.get_setting("asistan_edge_pitch", "model")
        saved_voice = self.db.get_setting("asistan_edge_voice", "ema_default")
        voice_index = self.cmb_voice.findData(saved_voice)
        if voice_index < 0:
            voice_index = 0
        self.cmb_voice.setCurrentIndex(voice_index)
        self.db.get_setting("asistan_edge_rate", "model")
        self.db.get_setting("asistan_tts_engine", "ema-lightning")

        # Names
        self.inp_user_name.setText(self.db.get_setting("asistan_user_name", "Efendim"))
        self.inp_assistant_name.setText(self.db.get_setting("asistan_ozel_adi", "AYEC"))

    def _save_all(self, show_feedback=True):
        """Save all settings to database"""
        self.db.set_setting("voice_assistant_active", "1" if self.toggle_assistant_active.isChecked() else "0")
        self.db.set_setting("asistan_voice_enabled", "1" if self.toggle_voice.isChecked() else "0")
        self.db.set_setting("telsiz_efekti_aktif", "1" if self.toggle_radio.isChecked() else "0")
        self.db.set_setting("asistan_hitap_aktif", "1" if self.toggle_hitap.isChecked() else "0")
        
        self.db.set_setting("asistan_edge_pitch", "model")
        self.db.set_setting("asistan_edge_voice", self.cmb_voice.currentData() or "ema_default")
        self.db.set_setting("asistan_tts_engine", "ema-lightning")
        self.db.set_setting("asistan_edge_rate", "model")

        # Names
        self.db.set_setting("asistan_user_name", self.inp_user_name.text())
        self.db.set_setting("asistan_ozel_adi", self.inp_assistant_name.text())

        if self.main_window is not None:
            try:
                assistant = getattr(self.main_window, "assistant", None)
                if self.toggle_assistant_active.isChecked():
                    if assistant is None and hasattr(self.main_window, "_ensure_assistant_manager"):
                        assistant = self.main_window._ensure_assistant_manager()
                    if assistant is not None:
                        assistant.start_voice_assistant()
                elif assistant is not None:
                    assistant.stop_voice_assistant()
            except Exception:
                pass
        
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
