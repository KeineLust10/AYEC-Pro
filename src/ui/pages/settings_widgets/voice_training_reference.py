from PyQt6.QtCore import Qt, QSize, QTime
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QToolButton,
    QSlider,
    QSizePolicy,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from src.ui.pages.settings_widgets.voice_training_base import VoiceTrainingWidget as BaseVoiceTrainingWidget
from src.utils.design_system import DesignTokens
from src.utils.theme_colors import tc, theme_qss
from src.ui.widgets.animated_toggle import AnimatedToggle


class VoiceTrainingWidget(BaseVoiceTrainingWidget):
    """Part 9 voice command settings layout backed by the existing behaviors."""

    def _panel(self, accent="@border"):
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background:@surface; border:1px solid @border; border-radius:11px; }"
            "QFrame QLabel { border:0; background:transparent; color:@text; }"
        )
        frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        return frame

    def _button(self, text, primary=False):
        button = QPushButton(text)
        button.setMinimumHeight(32)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        bg = "@accent" if primary else "@surface_alt"
        border = "@accent" if primary else "@border"
        button.setStyleSheet(
            f"QPushButton{{background:{bg};color:@accent_foreground;border:1px solid {border};"
            "border-radius:5px;padding:6px 10px;font-size:11px;font-weight:700;}"
            "QPushButton:hover{border-color:@accent;background:@hover_bg;}"
        )
        return button

    def _heading(self, text, subtitle=""):
        title = QLabel(text)
        title.setStyleSheet("font-size:13px;font-weight:800;color:@text;")
        if not subtitle:
            return title
        detail = QLabel(subtitle)
        detail.setWordWrap(True)
        detail.setStyleSheet("font-size:10px;color:@text_muted;")
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        layout.addWidget(title)
        layout.addWidget(detail)
        return box

    def _time_field(self, time):
        field = QTimeEdit()
        field.setDisplayFormat("HH:mm")
        field.setTime(QTime.fromString(time, "HH:mm"))
        field.setFixedSize(74, 32)
        field.setButtonSymbols(QTimeEdit.ButtonSymbols.NoButtons)
        field.setStyleSheet(
            "QTimeEdit{background:@surface_alt;color:@text;border:1px solid @border;"
            "border-radius:5px;padding:4px;font-family:'Segoe UI','Arial';}"
        )
        return field

    def setup_ui(self):
        theme_qss("")
        self.setStyleSheet(
            "VoiceTrainingWidget{background:@window;color:@text;font-family:'Segoe UI','Arial';}"
            "VoiceTrainingWidget QLabel{border:0;background:transparent;color:@text;}"
            "QLineEdit{background:@surface;color:@text;border:1px solid @border;border-radius:6px;padding:7px;}"
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 56)
        root.setSpacing(14)

        header = QHBoxLayout()
        brand_mark = QLabel("\u25c6")
        brand_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_mark.setFixedSize(36, 36)
        brand_mark.setStyleSheet("color:@accent_foreground;background:@accent;border-radius:9px;font-size:21px;font-weight:800;")
        brand = QLabel("<b>AYEC Pro | Sesli Senaryo &amp; AI Komut Merkezi</b>")
        brand.setTextFormat(Qt.TextFormat.RichText)
        brand.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        brand.setStyleSheet("QLabel{color:@text;font-size:16px;font-weight:700;}")
        version = QLabel("v3.2 BETA\nAk\u0131ll\u0131 Sesli Asistan, Tetikleyici Senaryolar ve Zamanlanm\u0131\u015f Bildirim Y\u00f6netimi")
        version.setStyleSheet("font-size:10px;color:@text_muted;")
        header.addWidget(brand_mark)
        header.addWidget(brand)
        header.addWidget(version, 1, Qt.AlignmentFlag.AlignLeft)
        self.lbl_engine_status = QLabel("\u25cf  Ses Motoru: Aktif & Dinlemede")
        self.lbl_engine_status.setStyleSheet("color:@success;background:@surface_alt;border:1px solid @border;border-radius:6px;padding:7px;font-size:10px;font-weight:700;")
        self.btn_engine_refresh = self._button("\u27f3  Yenile")
        self.btn_engine_refresh.setFixedHeight(32)
        self.lbl_engine_status.setMinimumHeight(32)
        self.lbl_engine_status.setMaximumHeight(32)
        header.addWidget(self.lbl_engine_status)
        header.addWidget(self.btn_engine_refresh)
        root.addLayout(header)
        root.addSpacing(14)

        stats = QHBoxLayout()
        stats.setSpacing(10)
        for title, value, note, color in (
            ("HAZIR KOMUT \u015eABLONLARI", "10 G\u00f6m\u00fcl\u00fc Senaryo", "\u00d6ntan\u0131ml\u0131 kurumsal aksiyon havuzu haz\u0131r", "@accent"),
            ("TET\u0130KLEME MANTI\u011eI", "Uyanma Ad\u0131 + En Uzun E\u015fle\u015fme", "Ba\u011flant\u0131/MLP a\u011f\u0131rl\u0131kl\u0131 tespit", "@success"),
            ("D\u00dcZENLEME DAVRANI\u015eI", "An\u0131nda Kaydet, \u0130sterse Sil", "Canl\u0131 veri senkronizasyonu devrede", "@info"),
        ):
            card = self._panel()
            card.setStyleSheet(card.styleSheet() + f"QFrame{{border-top:2px solid {color};}}")
            card.setFixedHeight(74)
            layout = QVBoxLayout(card)
            layout.setContentsMargins(12, 8, 12, 8)
            layout.setSpacing(3)
            cap = QLabel(title)
            cap.setStyleSheet(f"font-size:9px;font-weight:800;color:{color};")
            val = QLabel(value)
            val.setWordWrap(True)
            val.setStyleSheet("QLabel{font-size:12px;font-weight:800;color:@text;}")
            note_label = QLabel(note)
            note_label.setStyleSheet("font-size:9px;color:@text_muted;")
            layout.addWidget(cap)
            layout.addWidget(val)
            layout.addWidget(note_label)
            stats.addWidget(card, 1)
        root.addLayout(stats)

        main = QHBoxLayout()
        main.setSpacing(12)
        command_panel = self._panel()
        command = QVBoxLayout(command_panel)
        command_panel.setMinimumHeight(586)
        command_panel.setMaximumHeight(600)
        command.setContentsMargins(14, 12, 20, 12)
        command.setSpacing(8)
        command_header = QWidget()
        command_header_layout = QHBoxLayout(command_header)
        command_header_layout.setContentsMargins(0, 0, 0, 4)
        command_header_layout.setSpacing(8)
        command_heading = self._heading("\u2726  \u00d6nerilen En G\u00fc\u00e7l\u00fc Komutlar", "Ses K\u00fct\u00fcphanesi & Operasyonel H\u0131zl\u0131 Tetikleyiciler")
        command_title = command_heading.findChild(QLabel)
        if command_title:
            command_title.setStyleSheet("font-size:16px;font-weight:800;color:@text;")
        command_header_layout.addWidget(command_heading, 1)
        command_count = QLabel("6 Komut Haz\u0131r")
        command_count.setStyleSheet("color:@accent;background:@accent_soft;border:1px solid @accent;border-radius:4px;padding:4px 7px;font-family:Consolas,'Segoe UI','Arial';font-size:9px;font-weight:700;")
        command_header_layout.addWidget(command_count, 0, Qt.AlignmentFlag.AlignVCenter)
        command_header.setObjectName("voiceCommandHeader")
        command_header.setStyleSheet("QWidget#voiceCommandHeader{border-bottom:1px solid @border;}")
        command.addWidget(command_header)
        command.addSpacing(8)
        self.inp_command_search = QLineEdit()
        self.inp_command_search.setFixedHeight(26)
        self.inp_command_search.setPlaceholderText("\u2315  Komut veya tetikleyici ara...")
        command.addWidget(self.inp_command_search)
        filters = QHBoxLayout()
        for label in ("T\u00fcm\u00fc", "Finans", "Stok", "Servis", "Raporlar"):
            button = self._button(label, primary=(label == "T\u00fcm\u00fc"))
            button.setProperty("voiceFilter", label)
            button.setFixedHeight(20)
            filters.addWidget(button)
        filters.addStretch(1)
        command.addLayout(filters)
        self.list_recommended_commands = QListWidget()
        self.list_recommended_commands.setStyleSheet(
            "QListWidget{background:transparent;border:0;}"
            "QListWidget::item{background:transparent;border:0;padding:0;margin:0;color:@text;}"
            "QListWidget::item:selected{background:transparent;border:0;}"
        )
        self.list_recommended_commands.setMinimumHeight(250)
        self.list_recommended_commands.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.list_recommended_commands.setSpacing(1)
        self._command_details = {
            "Asistan finans \u00f6zet": ("Finans Konsolu & Ayl\u0131k Nakit Ak\u0131\u015f\u0131 Ekran\u0131", "\u00d6zet"),
            "Asistan geli\u015fmi\u015f finansal \u00f6zet": ("Bilan\u00e7o, Karl\u0131l\u0131k ve Tahsilat Grafikleri", "Geli\u015fmi\u015f"),
            "Asistan kritik stoklar\u0131 listele": ("Asgari Stok Alt\u0131 \u00dcr\u00fcnler ve Tedarik \u00d6nerileri", "Kritik Stok"),
            "Asistan yeni servis kayd\u0131 a\u00e7": ("H\u0131zl\u0131 Cihaz Kabul\u00fc ve M\u00fc\u015fteri Bildirimi", "Servis A\u00e7"),
            "Asistan g\u00fcn sonu kasa raporu": ("G\u00fcnl\u00fck Ciro, Kasa Durumu & Tahsilat Sesli Dinleme", "Kasa Raporu"),
            "Asistan teknisyen durumlar\u0131": ("Saha Personeli G\u00f6rev Da\u011f\u0131l\u0131m\u0131 ve \u0130\u015f Emri Takibi", "Saha Ekibi"),
        }
        try:
            from PyQt6.QtTextToSpeech import QTextToSpeech
            self._speech = QTextToSpeech(self)
        except Exception:
            self._speech = None
        self._populate_command_rows(self._default_commands())
        command.addWidget(self.list_recommended_commands, 1)
        command_actions = QHBoxLayout()
        self.btn_new_voice_command = self._button("\uff0b  Yeni Sesli Komut Ekle", primary=True)
        self.btn_new_voice_command.setStyleSheet("QPushButton{background:@accent_soft;color:@accent;border:1px solid @accent;border-radius:7px;padding:6px 10px;font-size:11px;font-weight:700;}QPushButton:hover{background:@hover_bg;border-color:@accent;}")
        self.btn_export_scenarios = self._button("\u21e7  \u015eablonlar\u0131 D\u0131\u015fa Aktar")
        self.btn_export_scenarios.setFixedWidth(122)
        command_divider = QFrame()
        command_divider.setFixedHeight(1)
        command_divider.setStyleSheet("background:@border;border:0;")
        command.addWidget(command_divider)
        command_actions.addWidget(self.btn_new_voice_command, 1)
        command_actions.addWidget(self.btn_export_scenarios)
        command.addLayout(command_actions)
        main.addWidget(command_panel, 5, Qt.AlignmentFlag.AlignTop)

        right_column = QVBoxLayout()
        right_column.setSpacing(10)
        operation = self._panel()
        operation.setMinimumHeight(198)
        op = QVBoxLayout(operation)
        op.setContentsMargins(14, 12, 14, 12)
        op.setSpacing(8)
        op_header = QHBoxLayout()
        op_header.addWidget(self._heading("\U0001f399 Sesli Senaryo Operasyon Masas\u0131", "Senaryolar sayfada da\u011f\u0131n\u0131k g\u00f6r\u00fcnmez. Ekleme, d\u00fczenleme ve test i\u015flemleri modern pencereden yap\u0131l\u0131r."), 1)
        self.lbl_active_scenario = QLabel("\u25cf Aktif Senaryo: AI Asistan Sayfas\u0131")
        self.lbl_active_scenario.setStyleSheet("color:@accent;border:1px solid @accent;border-radius:5px;padding:5px;font-size:9px;font-weight:700;")
        op_header.addWidget(self.lbl_active_scenario, alignment=Qt.AlignmentFlag.AlignTop)
        op.addLayout(op_header)
        self.lbl_scenario_meta = QLabel("\u2139  AI Asistan Sayfasi: 24 tetikleyici kural tanimli, islem hedefi: Sayfa 170. Duzenleme icin pencereyi acabilirsiniz.")
        self.lbl_scenario_meta.setWordWrap(True)
        self.lbl_scenario_meta.setStyleSheet("background:@surface_alt;border:1px solid @border;border-radius:5px;padding:7px;color:@text_muted;font-size:9px;")
        op.addWidget(self.lbl_scenario_meta)
        actions = QGridLayout()
        actions.setSpacing(6)
        self.btn_open_scenarios = self._button("\u2723  Senaryolar\u0131 Y\u00f6net", primary=True)
        self.btn_add_scen = self._button("\uff0b  Senaryo Ekle")
        self.btn_load_defaults = self._button("\u21e9  Haz\u0131r Senaryolar\u0131 Y\u00fckle")
        self.btn_fix_legacy = self._button("\u270e  Eski Senaryolar\u0131 D\u00fczelt")
        self.btn_test_scenario = self._button("\U0001f399  Aktif Senaryoyu Test Et")
        self.btn_healthcheck = self._button("\u2667  Sa\u011fl\u0131k Testi \u00c7al\u0131\u015ft\u0131r")
        self.btn_open_scenarios.clicked.connect(self.open_scenario_manager)
        self.btn_add_scen.clicked.connect(self.open_new_scenario_dialog)
        self.btn_load_defaults.clicked.connect(self.load_default_scenarios)
        self.btn_fix_legacy.clicked.connect(self.repair_legacy_scenarios)
        self.btn_test_scenario.clicked.connect(self.test_active_scenario)
        self.btn_healthcheck.clicked.connect(self.run_healthcheck)
        self.btn_new_voice_command.clicked.connect(self.open_new_scenario_dialog)
        self.btn_export_scenarios.clicked.connect(self.export_scenarios)
        for index, button in enumerate((self.btn_open_scenarios, self.btn_add_scen, self.btn_load_defaults, self.btn_fix_legacy, self.btn_test_scenario, self.btn_healthcheck)):
            actions.addWidget(button, index // 3, index % 3)
        op.addLayout(actions)
        right_column.addWidget(operation)

        live = self._panel()
        live.setMinimumHeight(144)
        live_layout = QVBoxLayout(live)
        live_layout.setContentsMargins(14, 11, 14, 11)
        live_layout.setSpacing(8)
        live_header = QHBoxLayout()
        live_header.addWidget(QLabel("\u25c9 CANLI SES ALGILAMA & AI TANIMA TEST PANELI"), 1)
        live_header.addWidget(QLabel("\u25cf  Ses Motoru: Aktif & Dinlemede"))
        live_layout.addLayout(live_header)
        live_body = QHBoxLayout()
        self.lbl_mic_status = QLabel("Mikrofon\nHazir\nAlgilama Gecikmesi: < 18ms\nSon Test Durumu: Hazir / Beklemede")
        self.lbl_mic_status.setStyleSheet("background:@surface_alt;border:1px solid @border;border-radius:7px;padding:10px;color:@text_muted;font-size:10px;")
        spectrum = QLabel("\u2582 \u2585 \u2583 \u2587 \u2584 \u2586 \u2582 \u2585\nCANLI SPEKTRUM ANALIZI")
        spectrum.setAlignment(Qt.AlignmentFlag.AlignCenter)
        spectrum.setStyleSheet("color:@accent;background:@surface_alt;border:1px solid @border;border-radius:7px;padding:10px;font-family:'Segoe UI','Arial';font-size:12px;font-weight:700;")
        live_body.addWidget(self.lbl_mic_status, 1)
        live_body.addWidget(spectrum, 1)
        live_layout.addLayout(live_body)
        right_column.addWidget(live)
        main.addLayout(right_column, 7)
        root.addLayout(main, 1)

        lower = QHBoxLayout()
        lower.setSpacing(10)
        schedule = self._panel()
        schedule_layout = QVBoxLayout(schedule)
        schedule_layout.setContentsMargins(13, 11, 13, 11)
        schedule_layout.setSpacing(7)
        schedule_layout.addWidget(self._heading("\u25f7 Zamanlanm\u0131\u015f Uyar\u0131lar", "Uyar\u0131 saatlerini ve aktiflik durumlar\u0131n\u0131 y\u00f6netin."))
        self.time_loan = self._time_field("11:00")
        self.time_check = self._time_field("11:30")
        self.time_stock = self._time_field("15:00")
        self.time_service = self._time_field("17:30")
        self.chk_loan_enabled = AnimatedToggle(active_color=tc("accent"))
        self.chk_check_enabled = AnimatedToggle(active_color=tc("accent"))
        self.chk_stock_enabled = AnimatedToggle(active_color=tc("accent"))
        self.chk_service_enabled = AnimatedToggle(active_color=tc("accent"))
        for toggle in (self.chk_loan_enabled, self.chk_check_enabled, self.chk_stock_enabled, self.chk_service_enabled):
            toggle.setChecked(True)
        for number, (label, detail_text, time, toggle) in enumerate((("Kredi Taksit", "G\u00fcnl\u00fck Hat\u0131rlatma", self.time_loan, self.chk_loan_enabled), ("\u00c7ek / Senet", "Vade Takibi", self.time_check, self.chk_check_enabled), ("Kritik Stok", "Depo E\u015fik Kontrol\u00fc", self.time_stock, self.chk_stock_enabled), ("Servis Teslim Uyar\u0131s\u0131", "Geciken \u0130\u015f Emirleri", self.time_service, self.chk_service_enabled)), 1):
            row = QHBoxLayout()
            badge = QLabel(f"{number:02d}")
            badge.setStyleSheet("color:@accent;background:@surface_alt;border:1px solid @border;border-radius:4px;padding:4px;font-weight:800;")
            detail = QLabel(label + "\n" + detail_text)
            detail.setStyleSheet("font-size:10px;font-weight:700;")
            row.addWidget(badge)
            row.addWidget(detail, 1)
            row.addWidget(time)
            row.addWidget(toggle)
            schedule_layout.addLayout(row)
        schedule_layout.addWidget(QLabel("4 zamanlanm\u0131\u015f g\u00f6rev aktif.                    Zamanlay\u0131c\u0131 G\u00fcnl\u00fc\u011f\u00fc \u2192"))
        lower.addWidget(schedule, 5)

        dnd = self._panel()
        dnd_layout = QVBoxLayout(dnd)
        dnd_layout.setContentsMargins(13, 11, 13, 11)
        dnd_layout.setSpacing(7)
        dnd_layout.addWidget(self._heading("\u263e Sessiz Saatler & Sentez", "Bildirim susturma ve konu\u015fma sesi ayarlar\u0131."))
        time_row = QHBoxLayout()
        self.time_dnd_start = self._time_field("19:00")
        self.time_dnd_end = self._time_field("08:30")
        time_row.addWidget(QLabel("Ba\u015flang\u0131\u00e7"))
        time_row.addWidget(self.time_dnd_start)
        time_row.addWidget(QLabel("Biti\u015f"))
        time_row.addWidget(self.time_dnd_end)
        dnd_layout.addLayout(time_row)
        self.chk_critical_override = QCheckBox("Kritik uyar\u0131larda sessiz modu yoksay")
        self.chk_critical_override.setChecked(self.db.get_setting("critical_override_dnd", "1") == "1")
        self.chk_critical_override.setStyleSheet("color:@text_muted;font-size:10px;")
        dnd_layout.addWidget(self.chk_critical_override)
        synthesis = QHBoxLayout()
        synthesis.addWidget(QLabel("\u25d6 Ses \u015eiddeti"))
        self.voice_volume = QSlider(Qt.Orientation.Horizontal)
        self.voice_volume.setRange(0, 100)
        self.voice_volume.setValue(int(self.db.get_setting("voice_volume", "85") or 85))
        self.voice_volume.setStyleSheet("QSlider::groove:horizontal{height:4px;background:@border;}QSlider::handle:horizontal{width:12px;margin:-5px 0;border-radius:6px;background:@accent;}")
        synthesis.addWidget(self.voice_volume, 1)
        self.lbl_voice_volume = QLabel(f"%{self.voice_volume.value()}")
        synthesis.addWidget(self.lbl_voice_volume)
        synthesis.addWidget(QLabel("H\u0131z"))
        self.voice_speed = QComboBox()
        self.voice_speed.addItems(["0.8x", "1.0x", "1.2x"])
        self.voice_speed.setCurrentText(str(self.db.get_setting("voice_speed", "1.0") or "1.0") + "x")
        self.voice_speed.setStyleSheet("QComboBox{background:@surface_alt;color:@text;border:1px solid @border;border-radius:5px;padding:5px;}")
        synthesis.addWidget(self.voice_speed)
        synthesis.addWidget(QLabel("\u2713 Senkronize"))
        dnd_layout.addStretch(1)
        dnd_layout.addLayout(synthesis)
        self.voice_volume.valueChanged.connect(lambda value: self.lbl_voice_volume.setText(f"%{value}"))
        lower.addWidget(dnd, 5)
        right_column.addLayout(lower, 2)

        self.lbl_test_result = QLabel("Son test sonucu: Hen\u00fcz \u00e7al\u0131\u015ft\u0131r\u0131lmad\u0131")
        self.lbl_test_result.setVisible(False)
        self.btn_healthcheck_details = self._button("Detaylar\u0131 G\u00f6r")
        self.btn_healthcheck_details.setVisible(False)
        self.btn_save = self._button("\u2713  T\u00dcM E\u011e\u0130T\u0130M\u0130 KAYDET", primary=True)
        self.btn_save.setMinimumHeight(38)
        self.btn_save.setVisible(False)
        self.btn_save.clicked.connect(self.save_data)
        self.btn_engine_refresh.clicked.connect(self._refresh_engine)
        self._active_command_filter = "T\u00fcm\u00fc"
        self.inp_command_search.textChanged.connect(self._filter_commands)
        for field in (self.time_loan, self.time_check, self.time_stock, self.time_service, self.time_dnd_start, self.time_dnd_end):
            field.timeChanged.connect(self.save_data)
        self.chk_service_enabled.toggled.connect(self.save_data)
        self.voice_speed.currentTextChanged.connect(self._save_voice_synthesis)
        self.voice_volume.valueChanged.connect(self._save_voice_synthesis)
        for button in command_panel.findChildren(QPushButton):
            category = button.property("voiceFilter")
            if category:
                button.clicked.connect(lambda checked=False, value=category: self._select_command_filter(value))
        self._load_scheduled_alerts()

    def _refresh_engine(self):
        self.lbl_engine_status.setText("\u25cf  Ses Motoru: Aktif & Dinlemede")
        self.lbl_mic_status.setText("Mikrofon\nHazir\nAlgilama Gecikmesi: < 18ms\nSon Test Durumu: Hazir / Beklemede")

    def export_scenarios(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "Sesli komut \u015fablonlar\u0131n\u0131 d\u0131\u015fa aktar", "sesli-komut-sablonlari.json", "JSON (*.json)")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as stream:
            import json
            json.dump(self.data, stream, ensure_ascii=False, indent=2)

    def _filter_commands(self, query="", category=None):
        query = str(query or "").strip().casefold()
        category = category or getattr(self, "_active_command_filter", "T\u00fcm\u00fc")
        current_item = self.list_recommended_commands.currentItem()
        current = current_item.data(Qt.ItemDataRole.UserRole) if current_item else ""
        self.list_recommended_commands.clear()
        category_terms = {"Finans": ("finans", "kasa", "\u00f6deme", "fatura"), "Stok": ("stok", "\u00fcr\u00fcn"), "Servis": ("servis", "cihaz", "teknisyen"), "Raporlar": ("rapor", "\u00f6zet", "kapan\u0131\u015f")}
        commands = self._recommended_commands() if query or category != "T\u00fcm\u00fc" else self._default_commands()
        visible = []
        for command in commands:
            if query and query not in command.casefold():
                continue
            terms = category_terms.get(category, ())
            if terms and not any(term in command.casefold() for term in terms):
                continue
            visible.append(command)
        self._populate_command_rows(visible, current)

    def _default_commands(self):
        commands = self._recommended_commands()
        preferred = (
            "Asistan finans \u00f6zet",
            "Asistan geli\u015fmi\u015f finansal \u00f6zet",
            "Asistan kritik stoklar\u0131 listele",
            "Asistan yeni servis kayd\u0131 a\u00e7",
            "Asistan g\u00fcn sonu kasa raporu",
            "Asistan teknisyen durumlar\u0131",
        )
        by_normalized = {command.casefold(): command for command in commands}
        return [by_normalized[key.casefold()] for key in preferred if key.casefold() in by_normalized]

    def _recommended_commands(self):
        commands = super()._recommended_commands()
        commands.extend(("Asistan yeni servis kayd\u0131 a\u00e7", "Asistan g\u00fcn sonu kasa raporu", "Asistan teknisyen durumlar\u0131"))
        return commands

    def _populate_command_rows(self, commands, selected=""):
        self.list_recommended_commands.clear()
        for command in commands:
            subtitle, trigger = self._command_details.get(command, ("Sesli komut ve hizli islem", command.removeprefix("Asistan ").title()))
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, command)
            item.setSizeHint(QSize(0, 62))
            self.list_recommended_commands.addItem(item)
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(10, 4, 5, 4)
            row_layout.setSpacing(6)
            text_layout = QVBoxLayout()
            text_layout.setContentsMargins(0, 0, 0, 0)
            text_layout.setSpacing(2)
            title = QLabel(f"\u223f {command}")
            title.setMinimumWidth(0)
            title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            title.setStyleSheet("color:@accent;font-size:11px;font-weight:800;font-family:Consolas,'Segoe UI','Arial';")
            detail = QLabel(subtitle)
            detail.setMinimumWidth(0)
            detail.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            detail.setWordWrap(True)
            detail.setStyleSheet("color:@text_muted;font-size:9px;")
            text_layout.addWidget(title)
            text_layout.addWidget(detail)
            row_layout.addLayout(text_layout, 1)
            trigger_label = QLabel(f'Tetikleyici: "{trigger}"')
            trigger_label.setMinimumWidth(128)
            trigger_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            trigger_label.setStyleSheet("color:@text_muted;background:@surface_alt;border:1px solid @border;border-radius:4px;padding:4px;font-family:Consolas,'Segoe UI','Arial';font-size:9px;")
            row_layout.addWidget(trigger_label)
            copy_button = QToolButton()
            copy_button.setText("\u29c9")
            copy_button.setToolTip("Komutu panoya kopyala")
            copy_button.clicked.connect(lambda checked=False, text=command: QApplication.clipboard().setText(text))
            play_button = QToolButton()
            play_button.setText("▶")
            play_button.setToolTip("Komutu seslendir")
            play_button.clicked.connect(lambda checked=False, text=command: self._speak_command(text))
            for button in (copy_button, play_button):
                button.setFixedSize(26, 27)
                button.setStyleSheet("QToolButton{background:@surface_alt;color:@text_muted;border:1px solid @border;border-radius:4px;font-size:12px;}QToolButton:hover{border-color:@accent;color:@accent;}")
                row_layout.addWidget(button)
            row.setObjectName("voiceCommandRow")
            row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            row.setStyleSheet("QWidget#voiceCommandRow{background:@window;border:1px solid @surface_alt;border-radius:10px;}QWidget#voiceCommandRow:hover{background:@hover_bg;border-color:@accent;}")
            self.list_recommended_commands.setItemWidget(item, row)
            row_height = 74 if command == "Asistan g\u00fcn sonu kasa raporu" else 60 if command == "Asistan teknisyen durumlar\u0131" else 60
            row.setMinimumHeight(row_height)
            item.setSizeHint(QSize(0, row_height))
            if command == selected:
                self.list_recommended_commands.setCurrentItem(item)

    def _speak_command(self, command):
        if self._speech is not None:
            self._speech.say(command)

    def _select_command_filter(self, category):
        self._active_command_filter = category
        for button in self.findChildren(QPushButton):
            value = button.property("voiceFilter")
            if value:
                button.setStyleSheet(self._button(button.text(), primary=(value == category)).styleSheet())
        self._filter_commands(self.inp_command_search.text(), category)

    def save_data(self):
        super().save_data()

    def _save_voice_synthesis(self):
        try:
            self.db.set_setting("voice_volume", str(self.voice_volume.value()))
            self.db.set_setting("voice_speed", self.voice_speed.currentText().rstrip("x"))
        except Exception:
            pass
