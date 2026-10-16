# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QComboBox, QLineEdit, QGroupBox, QFormLayout, QGridLayout, QScrollArea, QSizePolicy, QTimeEdit, QAbstractSpinBox)
from PyQt6.QtCore import Qt, QSignalBlocker, QThread, pyqtSignal, QTime
from PyQt6.QtGui import QFont

from src.ui.widgets.animated_toggle import AnimatedToggle
from src.utils.theme_colors import theme_qss, tc
from src.utils.toast_notification import show_success, show_error, show_info
from src.utils.design_system import DesignTokens


class MicrophoneInputTestWorker(QThread):
    completed = pyqtSignal(str, bool)

    def __init__(self, device_index=None, parent=None):
        super().__init__(parent)
        self.device_index = device_index

    def run(self):
        try:
            import array
            import math
            import speech_recognition as sr
            from src.utils.offline_turkish_asr import OfflineTurkishASR

            recognizer = sr.Recognizer()
            recognizer.dynamic_energy_threshold = True
            with sr.Microphone(device_index=self.device_index) as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=7)
            pcm = audio.get_raw_data(convert_rate=16000, convert_width=2)
            samples = array.array("h")
            samples.frombytes(pcm)
            rms = math.sqrt(sum(sample * sample for sample in samples) / max(1, len(samples)))
            transcript = OfflineTurkishASR().transcribe_with_confidence(audio)
            text = str(transcript.get("text") or "").strip()
            confidence = float(transcript.get("confidence", 0.0))
            if text:
                result = f'Duyulan: "{text}" (g\u00fcven {confidence:.2f}, sinyal RMS {rms:.0f})'
            else:
                result = f"Konu\u015fma anla\u015f\u0131lamad\u0131 (sinyal RMS {rms:.0f}); mikrofon seviyesini kontrol edin."
            self.completed.emit(result, bool(text) and confidence >= 0.25)
        except Exception as error:
            self.completed.emit(f"Mikrofon testi ba\u015far\u0131s\u0131z: {error}", False)



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
        title = QLabel("Ses Sentezleme & Komuta Ses Profilleri")
        title.setFont(QFont(self.font().family(), 11, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("color: @text; background: transparent; border: none; padding: 0;"))
        title_block.addWidget(title)
        
        subtitle = QLabel("Yapay zeka sesli asistan parametrelerini, edge TTS ses modellerini ve otonom sesli hat\u0131rlat\u0131c\u0131 zamanlamalar\u0131n\u0131 yap\u0131land\u0131r\u0131n.")
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
        synthesis_grid.setColumnStretch(2, 1)
        synthesis_heading = QLabel("Speech Synthesis (EMA Lightning TR)")
        synthesis_heading.setStyleSheet(theme_qss("color: @text; font-size: 11px; font-weight: 700; border: none;"))
        synthesis_grid.addWidget(synthesis_heading, 0, 0, 1, 3)

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

        # Telsiz/Radyo Efekti
        self.toggle_radio = AnimatedToggle(active_color=tc("accent"))
        row2 = self._create_setting_row("Telsiz / Walkie-Talkie Efekti", "Anons \u00f6ncesi ve sonras\u0131 h\u0131\u015f\u0131rt\u0131 sesi", self.toggle_radio)
        card_layout.addWidget(row2, 1, 0)

        # Adımla Hitap Et
        self.toggle_hitap = AnimatedToggle(active_color=tc("success"))
        row3 = self._create_setting_row("Ad\u0131mla Hitap Et", "Ki\u015fiselle\u015ftirilmi\u015f hitap", self.toggle_hitap)

        self.cmb_input_device = QComboBox()
        self.cmb_input_device.setAccessibleName("Sesli asistan mikrofonu")
        self.cmb_input_device.setStyleSheet(theme_qss(self._get_combobox_style()))
        self._populate_microphone_devices()
        row_mic = self._create_setting_row(
            "M\u0130KROFON",
            "Windows varsay\u0131lan ileti\u015fim mikrofonunu otomatik kullan\u0131r; gerekirse etkin giri\u015f ayg\u0131t\u0131n\u0131 se\u00e7in.",
            self.cmb_input_device,
        )
        self.microphone_test_button = QPushButton("Mikrofonu Test Et")
        self.microphone_test_button.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        self.microphone_test_button.clicked.connect(self._test_microphone)
        mic_test_row = self._create_setting_row(
            "M\u0130KROFON TEST\u0130",
            "Komut s\u00f6yleyin; yerel tan\u0131ma sonucu ekranda g\u00f6sterilir.",
            self.microphone_test_button,
        )

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
        synthesis_grid.addWidget(row4, 1, 2)

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

        # Ses Hızı
        self.cmb_rate = QComboBox()
        self.cmb_rate.addItems(["Model Varsay\u0131lan\u0131"])
        self.cmb_rate.setEnabled(False)
        self.cmb_rate.setStyleSheet(theme_qss(self._get_combobox_style()))
        row7 = self._create_setting_row("KONU\u015eMA HIZI", "Do\u011fal konu\u015fma h\u0131z\u0131 model taraf\u0131ndan belirlenir.", self.cmb_rate)
        synthesis_grid.addWidget(row7, 1, 1)

        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(theme_qss("background: @border; max-height: 1px;"))
        sep2.deleteLater()

        # Kullanıcı Adı
        self.inp_user_name = QLineEdit()
        self.inp_user_name.setPlaceholderText("Efendim,")
        self.inp_user_name.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        row8 = self._create_setting_row("H\u0130TAP \u00d6NEK\u0130 (PREFIX)", "Asistan\u0131n size hitap \u015fekli", self.inp_user_name)
        card_layout.addWidget(row8, 2, 0)

        # Asistan Adı
        self.inp_assistant_name = QLineEdit()
        self.inp_assistant_name.setPlaceholderText("AYEC")
        self.inp_assistant_name.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        row9 = self._create_setting_row("\u00c7A\u011eRI \u0130\u015eARET\u0130 (CALL SIGN)", "Sistem anonslar\u0131ndan \u00f6nce okunur", self.inp_assistant_name)
        card_layout.addWidget(row9, 1, 1)

        self.cmb_greeting_style = QComboBox()
        self.cmb_greeting_style.addItem("Resmi / Kurumsal (Varsay\u0131lan)", "formal")
        self.cmb_greeting_style.addItem("Samimi / Teknik Ekip", "friendly")
        self.cmb_greeting_style.addItem("K\u0131sa / Kompakt", "compact")
        self.cmb_greeting_style.setStyleSheet(theme_qss(self._get_combobox_style()))
        row_greeting_style = self._create_setting_row(
            "C\u00dcMLE BA\u015eI SAYGI \u0130FADES\u0130",
            "Asistan yan\u0131tlar\u0131nda kullan\u0131lacak \u00fcslup",
            self.cmb_greeting_style,
        )
        card_layout.addWidget(row_greeting_style, 2, 1)

        speech_preview = QFrame()
        speech_preview.setStyleSheet(theme_qss("QFrame { background: @surface_alt; border: 1px solid @border; border-radius: 7px; }"))
        speech_layout = QHBoxLayout(speech_preview)
        speech_layout.setContentsMargins(10, 8, 10, 8)
        speech_text = QVBoxLayout()
        speech_title = QLabel("Canl\u0131 Ses Testi \u00d6nizlemesi")
        speech_title.setStyleSheet(theme_qss("color: @text; font-weight: 800; border: none;"))
        speech_desc = QLabel("AYEC Pro sistemleri tam kapasite \u00e7al\u0131\u015f\u0131yor, efendim.")
        speech_desc.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px; border: none;"))
        speech_text.addWidget(speech_title)
        speech_text.addWidget(speech_desc)
        speech_layout.addLayout(speech_text, 1)
        speech_test = QPushButton("Ses Testini Oynat")
        speech_test.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        speech_test.clicked.connect(self._play_speech_preview)
        self.speech_test = speech_test
        speech_layout.addWidget(speech_test)
        synthesis_grid.addWidget(speech_preview, 2, 0, 1, 3)

        workspace = QHBoxLayout()
        workspace.setSpacing(10)
        left_panel = QVBoxLayout()
        left_panel.setSpacing(8)
        left_panel.addWidget(card)
        left_panel.addWidget(synthesis_card)
        extra_card = QFrame()
        extra_card.setObjectName("voiceExtraSettingsCard")
        extra_card.setStyleSheet(theme_qss("QFrame#voiceExtraSettingsCard { background: @finance_surface; border: 1px solid @finance_outline; border-radius: 6px; }"))
        extra_layout = QVBoxLayout(extra_card)
        extra_layout.setContentsMargins(14, 12, 14, 12)
        extra_layout.setSpacing(6)
        extra_title = QLabel("Ek Ses ve Mikrofon Ayarlar\u0131")
        extra_title.setStyleSheet(theme_qss("color: @text; font-size: 11px; font-weight: 700; border: none;"))
        extra_layout.addWidget(extra_title)
        for extra_row in (row1, row3, row6, row_mic, mic_test_row):
            extra_layout.addWidget(extra_row)
        left_panel.addWidget(extra_card)
        left_panel.addStretch()
        workspace.addLayout(left_panel, 2)

        side_panel = QVBoxLayout()
        side_panel.setSpacing(10)
        reminders = QFrame()
        reminders.setObjectName("voiceSchedulePanel")
        reminders.setStyleSheet(theme_qss("QFrame#voiceSchedulePanel { background: @finance_surface; border: 1px solid @finance_outline; border-radius: 6px; }"))
        reminders_layout = QVBoxLayout(reminders)
        reminders_layout.setContentsMargins(14, 12, 14, 12)
        reminders_layout.setSpacing(8)
        reminders_title = QLabel("Vokal Hat\u0131rlat\u0131c\u0131lar")
        reminders_title.setFont(QFont(self.font().family(), 10, QFont.Weight.Bold))
        reminders_title.setStyleSheet(theme_qss("color: @text; border: none; background: transparent;"))
        reminders_layout.addWidget(reminders_title)
        reminders_desc = QLabel("Zamanlanm\u0131\u015f sesli anons kuyru\u011fu")
        reminders_desc.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px; border: none; background: transparent;"))
        reminders_layout.addWidget(reminders_desc)
        try:
            reminder_rows = {str(row["alert_type"]): dict(row) for row in self.db.get_all_scheduled_alerts()}
        except Exception:
            reminder_rows = {}
        reminder_specs = (
            ("loan_reminder", "Taksit & Banka \u00d6demeleri", "G\u00fcnl\u00fck finansal nakit ak\u0131\u015f \u00f6zeti", "11:00"),
            ("check_reminder", "\u00c7ekler & Senetler", "Vadesi gelen portf\u00f6y kontrol\u00fc", "11:30"),
            ("stock_critical", "Kritik Stok Seviyesi", "Depo eksik par\u00e7a raporu", "15:00"),
        )
        self.reminder_controls = {}
        self.reminder_times = {}
        for alert_type, title_text, desc_text, default_time in reminder_specs:
            data = reminder_rows.get(alert_type, {})
            self.reminder_times[alert_type] = str(data.get("trigger_time") or default_time)
            row = QFrame()
            row.setStyleSheet(theme_qss("background: @surface; border: 1px solid @border; border-radius: 6px;"))
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(8, 6, 8, 6)
            text_layout = QVBoxLayout()
            text_layout.setSpacing(2)
            text_head = QHBoxLayout()
            label = QLabel(title_text)
            label.setStyleSheet(theme_qss("color: @text; font-size: 10px; font-weight: 700; border: none; background: transparent;"))
            time_label = QLabel(self.reminder_times[alert_type])
            time_label.setStyleSheet(theme_qss("color: @finance_primary; font-size: 9px; font-family: monospace; border: none;"))
            text_head.addWidget(label)
            text_head.addWidget(time_label)
            text_head.addStretch()
            text_layout.addLayout(text_head)
            desc = QLabel(desc_text)
            desc.setWordWrap(True)
            desc.setStyleSheet(theme_qss("color: @text_muted; font-size: 9px; border: none; background: transparent;"))
            text_layout.addWidget(desc)
            row_layout.addLayout(text_layout, 1)
            toggle = AnimatedToggle(active_color=tc("success"))
            toggle.setFixedSize(34, 20)
            toggle.setChecked(bool(data.get("is_enabled", 1)))
            row_layout.addWidget(toggle)
            self.reminder_controls[alert_type] = toggle
            reminders_layout.addWidget(row)
        self.add_reminder_button = QPushButton("+ Yeni Hat\u0131rlat\u0131c\u0131 Ekle")
        self.add_reminder_button.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        self.add_reminder_button.clicked.connect(self._open_reminder_settings)
        reminders_layout.addWidget(self.add_reminder_button)
        side_panel.addWidget(reminders)

        quiet_panel = QFrame()
        quiet_panel.setObjectName("voiceSchedulePanel")
        quiet_panel.setStyleSheet(theme_qss("QFrame#voiceSchedulePanel { background: @finance_surface; border: 1px solid @finance_outline; border-radius: 6px; }"))
        quiet_layout = QVBoxLayout(quiet_panel)
        quiet_layout.setContentsMargins(14, 12, 14, 12)
        quiet_layout.setSpacing(8)
        quiet_title = QLabel("Gece Sessiz Saatleri")
        quiet_title.setFont(QFont(self.font().family(), 10, QFont.Weight.Bold))
        quiet_title.setStyleSheet(theme_qss("color: @text; border: none; background: transparent;"))
        quiet_layout.addWidget(quiet_title)
        quiet_desc = QLabel("Otomatik susturma ve acil durum istisnas\u0131")
        quiet_desc.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px; border: none; background: transparent;"))
        quiet_layout.addWidget(quiet_desc)
        quiet_times = QHBoxLayout()
        self.time_quiet_start = QTimeEdit()
        self.time_quiet_end = QTimeEdit()
        self.time_quiet_start.setDisplayFormat("HH:mm")
        self.time_quiet_end.setDisplayFormat("HH:mm")
        for time_edit, key, default in ((self.time_quiet_start, "quiet_hours_start", "19:00"), (self.time_quiet_end, "quiet_hours_end", "08:30")):
            time_edit.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            time_value = QTime.fromString(str(self.db.get_setting(key, default) or default), "HH:mm")
            time_edit.setTime(time_value if time_value.isValid() else QTime.fromString(default, "HH:mm"))
            time_edit.setStyleSheet(theme_qss("QTimeEdit { background: @surface; color: @text; border: 1px solid @border; border-radius: 5px; padding: 5px 8px; }"))
        quiet_times.addWidget(self._time_field("BA\u015eLANGI\u00c7", self.time_quiet_start))
        quiet_times.addWidget(self._time_field("B\u0130T\u0130\u015e", self.time_quiet_end))
        quiet_layout.addLayout(quiet_times)
        self.toggle_critical_override = AnimatedToggle(active_color=tc("danger"))
        self.toggle_critical_override.setFixedSize(34, 20)
        self.toggle_critical_override.setChecked(self.db.get_setting("critical_override_dnd", "1") == "1")
        emergency_row = self._create_setting_row("Acil Durum \u0130stisnas\u0131 (Bypass)", "Kritik alarmlar sessiz saatlerde de duyurulur.", self.toggle_critical_override)
        quiet_layout.addWidget(emergency_row)
        side_panel.addWidget(quiet_panel)
        side_panel.addStretch()
        workspace.addLayout(side_panel, 1)
        workspace_widget = QWidget()
        workspace_widget.setLayout(workspace)
        workspace_widget.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Minimum)
        workspace_scroll = QScrollArea()
        workspace_scroll.setWidgetResizable(True)
        workspace_scroll.setFrameShape(QFrame.Shape.NoFrame)
        workspace_scroll.setStyleSheet(theme_qss("QScrollArea { background: transparent; border: none; }"))
        workspace_scroll.setWidget(workspace_widget)
        layout.addWidget(workspace_scroll, 1)

        # The original full-save action now uses the reference header control.
        self.save_button = self.header_save_button


    def _get_combobox_style(self):
        """Premium combobox styling with solid light dropdown"""
        return """
            QComboBox {
                background-color: @surface;
                color: @text;
                font-family: Inter;
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
                widget.setFont(QFont(self.font().family(), 10))
                widget.setStyleSheet(theme_qss("QLineEdit { background: @finance_surface_alt; color: @text; border: 1px solid @finance_outline; border-radius: 4px; padding: 4px 8px; min-height: 16px; font-family: Inter; font-size: 11px; } QLineEdit:focus { border-color: @finance_primary; }"))
            else:
                widget.setFont(QFont(self.font().family(), 10))
            widget.setFixedHeight(30)
            h_layout.addWidget(widget)
        
        return container

    def _time_field(self, title, time_edit):
        field = QFrame()
        field.setStyleSheet(theme_qss("background: @surface; border: 1px solid @border; border-radius: 6px;"))
        layout = QVBoxLayout(field)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)
        label = QLabel(title)
        label.setStyleSheet(theme_qss("color: @text_muted; font-size: 9px; border: none;"))
        layout.addWidget(label)
        layout.addWidget(time_edit)
        return field

    def _open_reminder_settings(self):
        parent = self.parentWidget()
        while parent is not None:
            if getattr(parent, "db", None) is self.db and hasattr(parent, "open_tab_by_key"):
                return parent.open_tab_by_key("voice_training")
            parent = parent.parentWidget()
        show_info(self.main_window or self, "Sesli hatirlatma senaryolari Komut ve Senaryo ekraninda duzenlenir.")
        return False

    def _save_scheduled_settings(self):
        if getattr(self, "_loading_settings", False):
            return
        if hasattr(self.db, "update_scheduled_alert"):
            for alert_type, toggle in self.reminder_controls.items():
                trigger_time = self.reminder_times.get(alert_type)
                self.db.update_scheduled_alert(
                    alert_type,
                    trigger_time=trigger_time,
                    is_enabled=toggle.isChecked(),
                )
        if hasattr(self.db, "set_setting"):
            self.db.set_setting("quiet_hours_start", self.time_quiet_start.time().toString("HH:mm"))
            self.db.set_setting("quiet_hours_end", self.time_quiet_end.time().toString("HH:mm"))
            self.db.set_setting("critical_override_dnd", "1" if self.toggle_critical_override.isChecked() else "0")

    def _load_settings(self):
        previous = getattr(self, "_loading_settings", False)
        self._loading_settings = True
        widgets = (
            self.toggle_assistant_active, self.toggle_voice, self.toggle_radio,
            self.toggle_hitap, self.cmb_tone, self.cmb_voice, self.cmb_engine,
            self.cmb_rate, self.cmb_input_device, self.cmb_greeting_style,
            self.inp_user_name, self.inp_assistant_name, self.time_quiet_start,
            self.time_quiet_end, self.toggle_critical_override,
            *self.reminder_controls.values(),
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
        self.toggle_assistant_active.setChecked(self.db.get_setting("voice_assistant_active", "1") == "1")
        self.toggle_voice.setChecked(self.db.get_setting("asistan_voice_enabled", "1") == "1")
        self.toggle_radio.setChecked(self.db.get_setting("telsiz_efekti_aktif", "0") == "1")
        self.toggle_hitap.setChecked(self.db.get_setting("asistan_hitap_aktif", "0") == "1")
        greeting_style = str(self.db.get_setting("asistan_greeting_style", "formal") or "formal")
        greeting_index = self.cmb_greeting_style.findData(greeting_style)
        self.cmb_greeting_style.setCurrentIndex(max(0, greeting_index))
        for alert_type, toggle in self.reminder_controls.items():
            alert = next((row for row in self.db.get_all_scheduled_alerts() if row["alert_type"] == alert_type), None) if hasattr(self.db, "get_all_scheduled_alerts") else None
            if alert is not None:
                toggle.setChecked(bool(alert["is_enabled"]))
        for time_edit, key, default in ((self.time_quiet_start, "quiet_hours_start", "19:00"), (self.time_quiet_end, "quiet_hours_end", "08:30")):
            value = QTime.fromString(str(self.db.get_setting(key, default) or default), "HH:mm")
            time_edit.setTime(value if value.isValid() else QTime.fromString(default, "HH:mm"))
        self.toggle_critical_override.setChecked(self.db.get_setting("critical_override_dnd", "1") == "1")
        
        # Legacy engine preferences remain readable, but are no longer used.
        self.db.get_setting("asistan_edge_pitch", "model")
        saved_voice = self.db.get_setting("asistan_edge_voice", "ema_default")
        voice_index = self.cmb_voice.findData(saved_voice)
        if voice_index < 0:
            voice_index = 0
        self.cmb_voice.setCurrentIndex(voice_index)
        self.db.get_setting("asistan_edge_rate", "model")
        self.db.get_setting("asistan_tts_engine", "ema-lightning")

        saved_device = str(self.db.get_setting("voice_input_device", "default") or "default")
        device_index = self.cmb_input_device.findData(saved_device)
        self.cmb_input_device.setCurrentIndex(max(0, device_index))

        # Names
        self.inp_user_name.setText(self.db.get_setting("asistan_user_name", "Efendim,"))
        self.inp_assistant_name.setText(self.db.get_setting("asistan_ozel_adi", "AYEC"))

    def _save_all(self, show_feedback=True):
        """Save all settings to database"""
        old_device = str(self.db.get_setting("voice_input_device", "default") or "default")
        selected_device = str(self.cmb_input_device.currentData() or "default")
        self.db.set_setting("voice_input_device", selected_device)
        self.db.set_setting("voice_assistant_active", "1" if self.toggle_assistant_active.isChecked() else "0")
        self.db.set_setting("asistan_voice_enabled", "1" if self.toggle_voice.isChecked() else "0")
        self.db.set_setting("telsiz_efekti_aktif", "1" if self.toggle_radio.isChecked() else "0")
        self.db.set_setting("asistan_hitap_aktif", "1" if self.toggle_hitap.isChecked() else "0")
        self.db.set_setting("asistan_greeting_style", str(self.cmb_greeting_style.currentData() or "formal"))
        
        self.db.set_setting("asistan_edge_pitch", "model")
        self.db.set_setting("asistan_edge_voice", self.cmb_voice.currentData() or "ema_default")
        self.db.set_setting("asistan_tts_engine", "ema-lightning")
        self.db.set_setting("asistan_edge_rate", "model")

        # Names
        self.db.set_setting("asistan_user_name", self.inp_user_name.text())
        self.db.set_setting("asistan_ozel_adi", self.inp_assistant_name.text())
        self._save_scheduled_settings()

        if self.main_window is not None:
            try:
                assistant = getattr(self.main_window, "assistant", None)
                if self.toggle_assistant_active.isChecked():
                    if assistant is None and hasattr(self.main_window, "_ensure_assistant_manager"):
                        assistant = self.main_window._ensure_assistant_manager()
                    if assistant is not None:
                        if old_device != selected_device:
                            assistant.stop_voice_assistant()
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
        self.cmb_input_device.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_greeting_style.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.toggle_voice.toggled.connect(self._on_ui_widget_changed)
        self.toggle_hitap.toggled.connect(self._on_ui_widget_changed)
        for toggle in self.reminder_controls.values():
            toggle.toggled.connect(self._save_scheduled_settings)
        self.time_quiet_start.timeChanged.connect(self._save_scheduled_settings)
        self.time_quiet_end.timeChanged.connect(self._save_scheduled_settings)
        self.toggle_critical_override.toggled.connect(self._save_scheduled_settings)

    def _populate_microphone_devices(self):
        """Offer Windows default plus currently available capture devices."""
        self.cmb_input_device.clear()
        self.cmb_input_device.addItem("Windows Varsay\u0131lan \u0130leti\u015fim Mikrofonu (Otomatik)", "default")
        try:
            import pyaudio

            audio = pyaudio.PyAudio()
            try:
                for index in range(audio.get_device_count()):
                    info = audio.get_device_info_by_index(index)
                    if int(info.get("maxInputChannels", 0)) < 1:
                        continue
                    host = audio.get_host_api_info_by_index(info["hostApi"]).get("name", "")
                    name = str(info.get("name") or f"Input {index}").strip()
                    self.cmb_input_device.addItem(f"{name} ({host})", f"{host}::{name}")
            finally:
                audio.terminate()
        except Exception:
            self.cmb_input_device.setToolTip(
                "Mikrofon listesi okunamad\u0131; Windows varsay\u0131lan\u0131 kullan\u0131lacak."
            )

    def _test_microphone(self):
        if getattr(self, "_microphone_test_worker", None) is not None:
            if self._microphone_test_worker.isRunning():
                return
        value = str(self.cmb_input_device.currentData() or "default")
        from src.utils.asistan_motoru import resolve_microphone_device_index

        device_index = resolve_microphone_device_index(value)
        self.microphone_test_button.setEnabled(False)
        show_info(
            self.main_window or self,
            "\u015eimdi mikrofona konu\u015fun; test sonucu birka\u00e7 saniye i\u00e7inde g\u00f6r\u00fcnecek.",
        )
        worker = MicrophoneInputTestWorker(device_index, self)
        self._microphone_test_worker = worker
        worker.completed.connect(self._on_microphone_test_complete)
        worker.finished.connect(self._on_microphone_test_finished)
        worker.start()

    def _on_microphone_test_finished(self):
        worker = getattr(self, "_microphone_test_worker", None)
        self._microphone_test_worker = None
        self.microphone_test_button.setEnabled(True)
        if worker is not None:
            worker.deleteLater()

    def _on_microphone_test_complete(self, message, passed):
        target = self.main_window or self
        if passed:
            show_success(target, message)
        else:
            show_error(target, message)
