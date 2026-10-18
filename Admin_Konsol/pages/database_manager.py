"""
AYEC Pro Admin Konsol - SQL & Veritaban\u0131 Y\u00f6neticisi Sayfas\u0131
Se\u00e7ilen firma veritaban\u0131nda uzaktan SQL komutlar\u0131 \u00e7al\u0131\u015ft\u0131rma.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog,
    QComboBox, QTextEdit, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QScrollArea, QSizePolicy, QGridLayout, QBoxLayout, QStackedWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont
import api_client


class _RunSqlThread(QThread):
    done = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, tenant_id: str, sql: str):
        super().__init__()
        self._tid = tenant_id
        self._sql = sql

    def run(self):
        try:
            self.done.emit(api_client.readonly_query(self._tid, self._sql))
        except Exception as exc:
            self.error.emit(str(exc))


class _FetchCompanies(QThread):
    done = pyqtSignal(dict)

    def run(self):
        payload = {"companies": [], "server": {}, "audit": [], "backups": []}
        try:
            payload["companies"] = api_client.companies()
        except Exception:
            pass
        try:
            payload["server"] = api_client.server_status()
        except Exception:
            pass
        try:
            payload["audit"] = api_client.audit_logs(limit=8)
        except Exception:
            pass
        companies = payload.get("companies", [])
        if companies:
            try:
                payload["backups"] = api_client.backups(companies[0].get("id", ""))
            except Exception:
                pass
        self.done.emit(payload)


class _FetchBackups(QThread):
    done = pyqtSignal(str, list)

    def __init__(self, tenant_id: str):
        super().__init__()
        self._tenant_id = tenant_id

    def run(self):
        try:
            rows = api_client.backups(self._tenant_id)
        except Exception:
            rows = []
        self.done.emit(self._tenant_id, rows)


class _DownloadBackup(QThread):
    done = pyqtSignal(str, object, str)

    def __init__(self, tenant_id: str, backup_index: int, backup_id: int, destination: str):
        super().__init__()
        self._tenant_id = tenant_id
        self._backup_index = backup_index
        self._backup_id = backup_id
        self._destination = destination

    def run(self):
        try:
            data = api_client.download_backup(
                self._tenant_id, self._backup_index, backup_id=self._backup_id
            )
            self.done.emit(self._destination, data, "")
        except Exception as exc:
            self.done.emit(self._destination, b"", str(exc))


class DatabaseManagerPage(QWidget):
    navigate_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._thread = None
        self._backup_threads = []
        self._download_threads = []
        self._company_backup_signal_connected = False
        self._sql_history: list[str] = []
        self._submitted_sql = ""
        self._build_ui()
        self._load_companies()

    def _build_ui(self):
        self.setObjectName("databaseManagerPage")
        self.setStyleSheet("""
            QWidget#databaseManagerPage { background: #0e1321; color: #dee2f6; }
            QWidget#databaseManagerPage QLabel { background: transparent; }
            QWidget#sqlContent { background: #0e1321; }
            QFrame#sqlPanel { background: #111827; border: 1px solid #252a39; border-radius: 6px; }
            QFrame#sqlPlatformMetrics { background: transparent; border: none; }
            QLabel#sqlKicker { color: #4cd7f6; font: 700 9px 'Segoe UI', Arial; letter-spacing: 1px; }
            QLabel#sqlTitle { color: #dee2f6; font-size: 20px; font-weight: 700; }
            QLabel#sqlMuted { color: #8c909f; }
            QLabel#sqlSectionTitle { color: #dee2f6; font-size: 15px; font-weight: 700; }
            QLabel#sqlQueryKicker { color: #8c909f; font: 700 10px 'Segoe UI', Arial; }
            QLabel#sqlState { color: #4edea3; font: 700 9px 'Segoe UI', Arial; }
            QLabel#statusLabel { color: #c2c6d6; }
            QComboBox#combo, QComboBox#historyCombo { min-height: 28px; padding: 2px 6px; color: #dee2f6; border: 1px solid #424754; border-radius: 4px; background: #090e1c; }
            QTextEdit#codeBox { padding: 2px; color: #dee2f6; border: 1px solid #252a39; border-radius: 5px; background: #090e1c; selection-background-color: #4d8eff; }
            QPushButton#primaryBtn { min-height: 24px; padding: 2px 8px; color: #00285d; border: 1px solid #4d8eff; border-radius: 4px; background: #4d8eff; font-weight: 700; }
            QPushButton#secondaryBtn { min-height: 24px; padding: 2px 6px; color: #c2c6d6; border: 1px solid #303444; border-radius: 4px; background: #252a39; }
            QPushButton:disabled { color: #8c909f; background: #161b2a; }
            QTableWidget#dataTable { color: #dee2f6; font: 9px "JetBrains Mono", "Segoe UI", Arial; border: 1px solid #252a39; gridline-color: #252a39; background: #090e1c; alternate-background-color: #161b2a; selection-background-color: #252a39; }
            QTableWidget#dataTable::item { padding: 7px 8px; }
            QTableWidget#dataTable QHeaderView { background: #090e1c; }
            QTableWidget#dataTable QHeaderView::section { padding: 8px; color: #8c909f; border: none; background: #161b2a; font: 700 9px "JetBrains Mono", "Segoe UI", Arial; }
            QFrame#sqlResultCard { background: #161b2a; border: 0; border-radius: 6px; }
            QLabel#sqlResultKey { color: #8c909f; font: 700 9px 'Segoe UI', Arial; }
            QLabel#sqlResultValue { color: #dee2f6; font: 10px 'Segoe UI', Arial; }
            QScrollArea#sqlScroll, QScrollArea#sqlScroll QWidget#qt_scrollarea_viewport { background: #0e1321; }
            QScrollBar:vertical { width: 10px; background: #090e1c; }
            QScrollBar::handle:vertical { min-height: 24px; border-radius: 4px; background: #424754; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self._scroll = QScrollArea(self)
        self._scroll.setObjectName("sqlScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content.setObjectName("sqlContent")
        content.setMinimumWidth(0)
        content.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Minimum)
        root = QVBoxLayout(content)
        self._root_layout = root
        root.setContentsMargins(40, 4, 16, 16)
        root.setSpacing(12)

        self._module_nav = QFrame()
        self._module_nav.setObjectName("sqlPanel")
        nav_layout = QHBoxLayout(self._module_nav)
        nav_layout.setContentsMargins(8, 6, 8, 6)
        nav_layout.setSpacing(4)
        self._module_buttons = []
        for key, label in (
            ("dashboard", "Merkezi Konsol"),
            ("backups", "Yedekleme & Kurtarma"),
            ("updates", "G\u00fcncelleme Da\u011f\u0131t\u0131m\u0131"),
            ("limits", "Kota & Limitler"),
            ("database_manager", "SQL Sorgu Y\u00f6neticisi"),
            ("error_logs", "Hata & Telemetri"),
            ("audit_logs", "Denetim (Audit)"),
            ("server_settings", "Sunucu Ayarlar\u0131"),
        ):
            button = QPushButton(label)
            button.setObjectName("secondaryBtn")
            button.setMinimumWidth(0)
            button.clicked.connect(lambda checked=False, page=key: self.navigate_requested.emit(page))
            if key == "database_manager":
                button.setObjectName("primaryBtn")
            nav_layout.addWidget(button)
            self._module_buttons.append(button)
        self._module_nav_scroll = QScrollArea()
        self._module_nav_scroll.setObjectName("sqlModuleNavScroll")
        self._module_nav_scroll.setWidgetResizable(True)
        self._module_nav_scroll.setStyleSheet(
            "QScrollArea#sqlModuleNavScroll { background: #0e1321; border: none; }"
            "QWidget#qt_scrollarea_viewport { background: #0e1321; }"
        )
        self._module_nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._module_nav_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._module_nav_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._module_nav_scroll.setFixedHeight(44)
        self._module_nav_scroll.setWidget(self._module_nav)
        root.addWidget(self._module_nav_scroll)

        self._platform_panel = QFrame()
        self._platform_panel.setObjectName("sqlPanel")
        platform_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight, self._platform_panel)
        platform_layout.setContentsMargins(0, 0, 0, 0)
        platform_layout.setSpacing(10)
        self._platform_panel.setFixedHeight(92)
        self._platform_values = []
        self._platform_details = []
        for card_index, (title_text, initial, detail) in enumerate((
            ("VER\u0130TABANI YOLU", "Kontrol ediliyor", "SQLite WAL / Tenant DB"),
            ("DONANIM & KAYNAK T\u00dcKET\u0130M\u0130", "CPU --%  |  RAM --%  |  Disk --%", "Sunucu kaynak kullan\u0131m\u0131"),
            ("GATEWAY & L\u0130SANS API", "Kontrol ediliyor", "Aktif tenant: --"),
        )):
            card = QFrame()
            card.setObjectName("sqlResultCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 10, 12, 10)
            card_layout.setSpacing(3)
            title_label = QLabel(title_text)
            title_label.setObjectName("sqlQueryKicker")
            value_label = QLabel(initial)
            value_label.setObjectName("sqlSectionTitle")
            value_label.setMinimumWidth(0)
            value_label.setWordWrap(True)
            detail_label = QLabel(detail)
            detail_label.setObjectName("sqlMuted")
            detail_label.setWordWrap(True)
            card_layout.addWidget(title_label)
            card_layout.addWidget(value_label)
            card_layout.addWidget(detail_label)
            platform_layout.addWidget(card, (1, 2, 1)[card_index])
            self._platform_values.append(value_label)
            self._platform_details.append(detail_label)
        root.addWidget(self._platform_panel)

        header = QFrame()
        header.setObjectName("sqlPanel")
        header_layout = QGridLayout(header)
        header_layout.setContentsMargins(34, 4, 12, 4)
        header_layout.setHorizontalSpacing(16)
        header_layout.setVerticalSpacing(4)
        self._header_layout = header_layout
        kicker = QLabel("READ-ONLY DIAGNOSTIC / TENANT DATABASE")
        kicker.setObjectName("sqlKicker")
        kicker.setWordWrap(True)
        kicker.setMinimumWidth(0)
        kicker.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        kicker.hide()
        title = QLabel("Salt Okunur SQL Te\u015fhis Sorgulay\u0131c\u0131")
        title.setObjectName("sqlTitle")
        title.setWordWrap(True)
        header_layout.addWidget(title, 1, 0)
        intro = QLabel("G\u00fcvenli SELECT, EXPLAIN QUERY PLAN ve salt okunur PRAGMA sorgular\u0131n\u0131 se\u00e7ili tenant veritaban\u0131nda \u00e7al\u0131\u015ft\u0131r\u0131n.")
        intro.setObjectName("sqlMuted")
        intro.setWordWrap(True)
        intro.setMinimumWidth(0)
        intro.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        header_layout.addWidget(intro, 2, 0, 1, 2)
        controls = QHBoxLayout()
        self._header_controls = controls
        controls.addWidget(QLabel("Firma:"))
        self._firm_combo = QComboBox()
        self._firm_combo.setObjectName("combo")
        self._firm_combo.setMinimumWidth(0)
        controls.addWidget(self._firm_combo)
        self._history_combo = QComboBox()
        self._history_combo.setObjectName("historyCombo")
        self._history_combo.addItem("Son sorgular")
        self._history_combo.currentIndexChanged.connect(self._restore_history)
        self._history_combo.hide()
        header_layout.addLayout(controls, 1, 1, 1, 1)

        self._query_panel = QFrame()
        self._query_panel.setObjectName("sqlPanel")
        query_layout = QVBoxLayout(self._query_panel)
        query_layout.setContentsMargins(18, 8, 8, 8)
        query_layout.setSpacing(8)
        query_heading = QHBoxLayout()
        self._query_heading_layout = query_heading
        query_heading.setContentsMargins(8, 0, 0, 0)
        query_title = QLabel("QUERY BUFFER [READ-ONLY TX]")
        query_title.setObjectName("sqlQueryKicker")
        query_title.setWordWrap(False)
        query_title.setMinimumWidth(0)
        query_heading.addWidget(query_title)
        query_heading.addStretch()
        safe_mode = QLabel("KORUMALI MOD")
        safe_mode.setObjectName("sqlState")
        query_heading.addWidget(safe_mode)
        query_layout.addLayout(query_heading)
        self._sql_input = QTextEdit()
        self._sql_input.setObjectName("codeBox")
        initial_query = "SELECT id, username, role, last_login, disk_usage_mb\nFROM users\nWHERE status = 'active'\nORDER BY id ASC\nLIMIT 50;"
        self._sql_input.setPlaceholderText(initial_query)
        self._sql_input.setPlainText(initial_query)
        code_font = QFont("JetBrains Mono")
        code_font.setPixelSize(9)
        self._sql_input.setFont(code_font)
        self._sql_input.setMinimumHeight(112)
        self._sql_input.setMaximumHeight(112)
        self._sql_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        query_layout.addWidget(self._sql_input)
        actions = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._actions_layout = actions
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(6)
        self._run_btn = QPushButton("Sorguyu \u00c7al\u0131\u015ft\u0131r")
        self._run_btn.setObjectName("primaryBtn")
        self._run_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._run_btn.clicked.connect(self._run_query)
        self._action_buttons = []
        self._action_buttons.append(self._run_btn)
        self._explain_btn = QPushButton("EXPLAIN QUERY PLAN")
        self._explain_btn.setObjectName("secondaryBtn")
        self._explain_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._explain_btn.clicked.connect(self._run_explain_query)
        self._action_buttons.append(self._explain_btn)
        clear = QPushButton("Temizle")
        clear.setObjectName("secondaryBtn")
        clear.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        clear.clicked.connect(self._clear_query)
        self._action_buttons.append(clear)
        query_layout.addLayout(actions)
        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("statusLabel")
        self._status_lbl.setWordWrap(False)

        result_panel = QFrame()
        result_panel.setObjectName("sqlPanel")
        self._result_panel = result_panel
        result_layout = QVBoxLayout(result_panel)
        result_layout.setContentsMargins(0, 0, 0, 0)
        result_heading = QHBoxLayout()
        self._result_heading_layout = result_heading
        result_heading.setContentsMargins(34, 4, 12, 4)
        result_title = QLabel("Sorgu Sonu\u00e7lar\u0131")
        result_title.setObjectName("sqlSectionTitle")
        result_title.setWordWrap(True)
        result_heading.addWidget(result_title)
        result_heading.addStretch()
        self._result_count = QLabel("Hen\u00fcz sorgu \u00e7al\u0131\u015ft\u0131r\u0131lmad\u0131")
        self._result_count.setObjectName("sqlKicker")
        self._result_count.setWordWrap(True)
        self._result_count.setMinimumWidth(0)
        self._result_count.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self._result_count.hide()
        result_heading.addWidget(self._result_count)
        self._result_stack = QStackedWidget()
        self._result_stack.setObjectName("sqlResultStack")
        self._table = QTableWidget(0, 0)
        self._table.setObjectName("dataTable")
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setMinimumHeight(104)
        self._table.setMinimumWidth(0)
        self._table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setFixedHeight(22)
        self._table.verticalHeader().setDefaultSectionSize(18)
        self._table.verticalHeader().setVisible(False)
        self._mobile_results = QWidget()
        self._mobile_results.setObjectName("sqlMobileResults")
        self._mobile_results_layout = QVBoxLayout(self._mobile_results)
        self._mobile_results_layout.setContentsMargins(8, 8, 8, 8)
        self._mobile_results_layout.setSpacing(8)
        self._result_stack.addWidget(self._table)
        self._result_stack.addWidget(self._mobile_results)
        result_layout.addWidget(self._result_stack)

        self._workspace = QWidget()
        self._workspace_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight, self._workspace)
        self._workspace_layout.setContentsMargins(0, 0, 0, 0)
        self._workspace_layout.setSpacing(12)
        self._workspace_left = QWidget()
        self._workspace_left_layout = QVBoxLayout(self._workspace_left)
        self._workspace_left_layout.setContentsMargins(0, 0, 0, 0)
        self._workspace_left_layout.setSpacing(2)
        self._workspace_left_layout.addWidget(header)
        self._workspace_left_layout.addWidget(self._query_panel)
        self._workspace_left_layout.addWidget(result_panel, 1)
        self._workspace_layout.addWidget(self._workspace_left, 1)

        self._operations_panel = QFrame()
        self._operations_panel.setObjectName("sqlPanel")
        self._operations_panel.setMinimumWidth(260)
        operations_layout = QVBoxLayout(self._operations_panel)
        operations_layout.setContentsMargins(10, 8, 10, 8)
        operations_layout.setSpacing(4)
        operations_title = QLabel("Yedekleme & S\u00fcr\u00fcm G\u00fcncelleme Da\u011f\u0131t\u0131m\u0131")
        operations_title.setObjectName("sqlSectionTitle")
        operations_title.setWordWrap(True)
        operations_title.setContentsMargins(28, 0, 0, 0)
        operations_title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        operations_layout.addWidget(operations_title)
        operations_hint = QLabel("OTA g\u00fcncelleme paketlerini da\u011f\u0131t\u0131n ve anl\u0131k veritaban\u0131 anl\u0131k g\u00f6r\u00fcnt\u00fclerini y\u00f6netin")
        operations_hint.setObjectName("sqlMuted")
        operations_hint.setWordWrap(True)
        operations_hint.setContentsMargins(28, 0, 0, 0)
        operations_hint.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        operations_layout.addWidget(operations_hint)
        deploy_form = QWidget()
        deploy_form_layout = QGridLayout(deploy_form)
        deploy_form_layout.setContentsMargins(0, 0, 0, 0)
        deploy_form_layout.setHorizontalSpacing(6)
        deploy_form_layout.setVerticalSpacing(4)
        version_label = QLabel("Da\u011f\u0131t\u0131m S\u00fcr\u00fcm\u00fc")
        version_label.setObjectName("sqlQueryKicker")
        channel_label = QLabel("Kanal Hedefi")
        channel_label.setObjectName("sqlQueryKicker")
        notes_label = QLabel("S\u00fcr\u00fcm De\u011fi\u015fiklik Notlar\u0131")
        notes_label.setObjectName("sqlQueryKicker")
        deploy_form_layout.addWidget(version_label, 0, 0)
        deploy_form_layout.addWidget(channel_label, 0, 1)
        self._release_input = QLineEdit("2.0.1-rc3")
        self._release_input.setObjectName("combo")
        self._release_input.setPlaceholderText("Da\u011f\u0131t\u0131m s\u00fcr\u00fcm\u00fc")
        self._channel_combo = QComboBox()
        self._channel_combo.setObjectName("combo")
        self._channel_combo.addItems(["Pilot M\u00fc\u015fteriler", "Stable", "Beta"])
        self._deploy_button = QPushButton("Da\u011f\u0131t\u0131m\u0131 Kuyrukla")
        self._deploy_button.setObjectName("primaryBtn")
        self._deploy_button.clicked.connect(lambda: self.navigate_requested.emit("updates"))
        deploy_form_layout.addWidget(self._release_input, 1, 0)
        deploy_form_layout.addWidget(self._channel_combo, 1, 1)
        deploy_form_layout.addWidget(self._deploy_button, 1, 2)
        deploy_form_layout.addWidget(notes_label, 2, 0, 1, 3)
        self._release_notes = QLineEdit()
        self._release_notes.setObjectName("combo")
        self._release_notes.setPlaceholderText("S\u00fcr\u00fcm de\u011fi\u015fiklik notlar\u0131")
        deploy_form_layout.addWidget(self._release_notes, 3, 0, 1, 3)
        operations_layout.addWidget(deploy_form)
        backup_title = QLabel("SON ALINAN S\u0130STEM YEDEKLER\u0130")
        backup_title.setObjectName("sqlQueryKicker")
        backup_title.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        backup_header = QHBoxLayout()
        backup_header.addWidget(backup_title)
        backup_header.addStretch(1)
        self._backup_state = QLabel("Yedekler kontrol ediliyor")
        self._backup_state.setObjectName("sqlState")
        self._backup_state.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        backup_header.addWidget(self._backup_state)
        operations_layout.addLayout(backup_header)
        self._backup_table = QTableWidget(0, 6)
        self._backup_table.setObjectName("dataTable")
        self._backup_table.setStyleSheet(
            "QTableWidget::item { padding: 1px 4px; }"
            "QHeaderView::section { padding: 2px 4px; }"
        )
        self._backup_table.setHorizontalHeaderLabels([
            "DOSYA ADI", "KAYNAK", "TAR\u0130H", "BOYUT", "DURUM", "EYLEM"
        ])
        self._backup_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._backup_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._backup_table.verticalHeader().setVisible(False)
        self._backup_table.verticalHeader().setDefaultSectionSize(20)
        self._backup_table.horizontalHeader().setFixedHeight(22)
        self._backup_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in range(1, 6):
            self._backup_table.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeMode.ResizeToContents
            )
        self._backup_table.setMinimumHeight(76)
        self._backup_table.setMaximumHeight(160)
        self._backup_table.setColumnWidth(1, 62)
        self._backup_table.setColumnWidth(2, 72)
        self._backup_table.setColumnWidth(3, 50)
        self._backup_table.setColumnWidth(4, 60)
        self._backup_table.setColumnWidth(5, 144)
        operations_layout.addWidget(self._backup_table, 1)
        self._workspace_layout.addWidget(self._operations_panel, 1)
        root.addWidget(self._workspace)

        self._telemetry_panel = QFrame()
        self._telemetry_panel.setObjectName("sqlPanel")
        telemetry_layout = QVBoxLayout(self._telemetry_panel)
        telemetry_layout.setContentsMargins(12, 10, 12, 12)
        telemetry_header = QHBoxLayout()
        telemetry_title = QLabel("Canl\u0131 Telemetri, Hata ve Denetim (Audit) Loglar\u0131")
        telemetry_title.setObjectName("sqlSectionTitle")
        telemetry_header.addWidget(telemetry_title)
        telemetry_header.addStretch(1)
        self._telemetry_state = QLabel("CANLI VER\u0130")
        self._telemetry_state.setObjectName("sqlState")
        telemetry_header.addWidget(self._telemetry_state)
        telemetry_layout.addLayout(telemetry_header)
        self._telemetry_table = QTableWidget(0, 6)
        self._telemetry_table.setObjectName("dataTable")
        self._telemetry_table.setHorizontalHeaderLabels([
            "Tarih / Saat", "Firma / Kaynak", "Olay Kodu", "Seviye", "A\u00e7\u0131klama", "Durum"
        ])
        self._telemetry_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._telemetry_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._telemetry_table.verticalHeader().setVisible(False)
        self._telemetry_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._telemetry_table.setMinimumHeight(150)
        self._telemetry_table.setMaximumHeight(230)
        telemetry_layout.addWidget(self._telemetry_table)
        self._audit_console = QTextEdit()
        self._audit_console.setObjectName("codeBox")
        self._audit_console.setReadOnly(True)
        self._audit_console.setMinimumHeight(76)
        self._audit_console.setMaximumHeight(100)
        self._audit_console.setFont(QFont("JetBrains Mono", 8))
        telemetry_layout.addWidget(self._audit_console)
        root.addWidget(self._telemetry_panel)
        self._scroll.setWidget(content)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer.addWidget(self._scroll, 1)
        self._set_header_layout()
        self._set_action_layout()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._root_layout.setContentsMargins(12, 12, 12, 12) if self.width() < 720 else self._root_layout.setContentsMargins(40, 4, 16, 16)
        self._module_nav.setMinimumWidth(820 if self.width() < 720 else 0)
        self._platform_panel.layout().setDirection(
            QBoxLayout.Direction.TopToBottom if self.width() < 720
            else QBoxLayout.Direction.LeftToRight
        )
        self._set_backup_table_layout()
        if self.width() >= 1000:
            self._workspace.setMinimumHeight(412)
            self._workspace.setMaximumHeight(412)
        else:
            self._workspace.setMinimumHeight(0)
            self._workspace.setMaximumHeight(16777215)
        self._workspace_left_layout.setSpacing(8 if self.width() < 720 else 2)
        self._workspace_layout.setDirection(
            QBoxLayout.Direction.TopToBottom if self.width() < 1000
            else QBoxLayout.Direction.LeftToRight
        )
        if hasattr(self, "_header_layout"):
            self._set_header_layout()
            self._set_action_layout()
            self._set_table_layout()
            code_font = QFont("JetBrains Mono")
            code_font.setPixelSize(12 if self.width() < 720 else 9)
            self._sql_input.setFont(code_font)
            self._sql_input.setMinimumHeight(130 if self.width() < 720 else 112)
            self._sql_input.setMaximumHeight(150 if self.width() < 720 else 112)

    def _set_table_layout(self):
        mobile = self.width() < 720
        self._result_stack.setCurrentWidget(self._mobile_results if mobile else self._table)
        self._result_panel.setMaximumHeight(116 if mobile else 16777215)
        self._table.setMaximumHeight(104 if mobile else 16777215)
        self._result_heading_layout.setDirection(
            QBoxLayout.Direction.TopToBottom if mobile else QBoxLayout.Direction.LeftToRight
        )
        mode = QHeaderView.ResizeMode.Stretch if mobile else QHeaderView.ResizeMode.ResizeToContents
        self._table.horizontalHeader().setSectionResizeMode(mode)
        self._table.horizontalHeader().setMinimumHeight(22)
        self._table.horizontalHeader().setMaximumHeight(22)

    def _set_backup_table_layout(self):
        mobile = self.width() < 720
        for column in (1, 2, 4):
            self._backup_table.setColumnHidden(column, mobile)
        self._backup_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        for column in (1, 2, 3, 4, 5):
            self._backup_table.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeMode.Fixed
            )

    def _set_header_layout(self):
        layout = self._header_layout
        index = layout.indexOf(self._header_controls)
        if index >= 0:
            layout.takeAt(index)
        if self.width() < 720:
            layout.addLayout(self._header_controls, 3, 0, 1, 2)
        else:
            layout.addLayout(self._header_controls, 1, 1, 1, 1)

    def _set_action_layout(self):
        layout = self._actions_layout
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        if self.width() < 720:
            self._query_panel.setMinimumHeight(310)
            self._scroll.widget().setMinimumHeight(max(1200, self._scroll.widget().layout().sizeHint().height()))
            layout.setDirection(QBoxLayout.Direction.TopToBottom)
            layout.setSpacing(6)
            for button in self._action_buttons:
                button.setMinimumWidth(0)
                button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                layout.addWidget(button)
            layout.addWidget(self._status_lbl)
        else:
            self._query_panel.setMinimumHeight(194)
            self._scroll.widget().setMinimumHeight(0)
            layout.setDirection(QBoxLayout.Direction.LeftToRight)
            layout.setSpacing(6)
            for button in self._action_buttons:
                button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
                layout.addWidget(button)
            layout.addWidget(self._status_lbl, 1)
            layout.addStretch(1)

    def _load_companies(self):
        t = _FetchCompanies()
        t.done.connect(self._populate_companies)
        t.start()
        self._thread = t

    def _populate_companies(self, payload):
        if isinstance(payload, list):
            payload = {"companies": payload, "server": {}, "audit": [], "backups": []}
        self._firm_combo.blockSignals(True)
        self._firm_combo.clear()
        for c in payload.get("companies", []):
            self._firm_combo.addItem(c.get("company_name", "?"), c.get("id", ""))
        self._firm_combo.blockSignals(False)
        if not self._company_backup_signal_connected:
            self._firm_combo.currentIndexChanged.connect(self._load_selected_backups)
            self._company_backup_signal_connected = True
        server = payload.get("server", {})
        values = (
            str(server.get("db_path", "Veritaban\u0131 yolu bildirilmiyor")),
            f"CPU {server.get('cpu_percent', '--')}%  |  RAM {server.get('ram_percent', '--')}%  |  Disk {server.get('disk_percent', '--')}%",
            "200 OK" if server else "API eri\u015filemiyor",
        )
        for label, value in zip(self._platform_values, values):
            label.setText(value)
        details = (
            "SQLite WAL / tenant veritaban\u0131",
            str(server.get("hardware_summary", "Sunucu kaynak kullan\u0131m\u0131")),
            f"Uptime: {server.get('uptime', '--')}  |  Aktif tenant: {server.get('tenant_count', len(payload.get('companies', [])))}",
        )
        for label, value in zip(self._platform_details, details):
            label.setText(value)
        audit = payload.get("audit", [])
        self._telemetry_table.setRowCount(len(audit))
        console_lines = []
        for row, entry in enumerate(audit):
            detail = entry.get("description", entry.get("detail", "--"))
            if isinstance(detail, dict):
                detail = "; ".join(f"{key}: {value}" for key, value in detail.items())
            cells = (
                entry.get("timestamp", entry.get("created_at", "--")),
                entry.get("company_name", entry.get("company", "--")),
                entry.get("action", entry.get("event", "--")),
                entry.get("severity", entry.get("level", "INFO")),
                detail,
                entry.get("status", entry.get("severity", "Kaydedildi")),
            )
            for column, text in enumerate(cells):
                self._telemetry_table.setItem(row, column, QTableWidgetItem(str(text)))
            console_lines.append(f"[{cells[0]}] {cells[2]} - {cells[4]}")
        self._audit_console.setPlainText("\n".join(console_lines))
        self._populate_backups(payload.get("backups", []))

    def _populate_backups(self, backups: list):
        self._backup_items = list(backups or [])
        self._backup_table.setRowCount(min(2, len(self._backup_items)))
        self._backup_state.setText(f"{len(backups)} yedek kayd\u0131")
        for row, entry in enumerate(self._backup_items[:2]):
            self._backup_table.setRowHeight(row, 26)
            filename = entry.get("filename", entry.get("name", "--"))
            size = entry.get("size_bytes", 0)
            size_text = f"{size / (1024 * 1024):.1f} MB" if size else "--"
            source = " / ".join(
                str(value) for value in (entry.get("source"), entry.get("product_code")) if value
            ) or "server"
            modified = entry.get("created_at", entry.get("modified", "--"))
            status = "Haz\u0131r" if entry.get("sha256") else "Hash yok"
            for column, value in enumerate((filename, source, modified, size_text, status)):
                item = QTableWidgetItem(str(value))
                self._backup_table.setItem(row, column, item)
            action_cell = QWidget()
            action_layout = QHBoxLayout(action_cell)
            action_layout.setContentsMargins(2, 0, 2, 0)
            action_layout.setSpacing(3)
            download = QPushButton("\u0130ndir")
            download.setObjectName("secondaryBtn")
            download.setFixedSize(55, 22)
            download.clicked.connect(lambda _checked=False, index=row: self._download_backup(index))
            restore = QPushButton("Kurtar")
            restore.setObjectName("secondaryBtn")
            restore.setFixedSize(55, 22)
            restore.clicked.connect(lambda: self.navigate_requested.emit("backups"))
            action_layout.addWidget(download)
            action_layout.addWidget(restore)
            self._backup_table.setCellWidget(row, 5, action_cell)

    def _download_backup(self, row: int):
        if row < 0 or row >= len(self._backup_items):
            return
        tenant_id = str(self._firm_combo.currentData() or "")
        entry = self._backup_items[row]
        filename = str(entry.get("filename", "backup.db"))
        destination, _selected_filter = QFileDialog.getSaveFileName(
            self, "Yedek Dosyas\u0131n\u0131 Kaydet", filename,
            "Database backups (*.db);;All files (*)",
        )
        if not destination:
            return
        worker = _DownloadBackup(
            tenant_id, row, int(entry.get("id", 0) or 0), destination
        )
        worker.done.connect(self._save_downloaded_backup)
        worker.finished.connect(lambda current=worker: self._discard_download_thread(current))
        self._download_threads.append(worker)
        self._backup_state.setText("Yedek indiriliyor...")
        worker.start()

    def _save_downloaded_backup(self, destination: str, data, error: str):
        if error:
            self._backup_state.setText(f"\u0130ndirme hatas\u0131: {error}")
            return
        try:
            with open(destination, "wb") as output:
                output.write(data)
            self._backup_state.setText("Yedek dosyas\u0131 kaydedildi")
        except OSError as exc:
            self._backup_state.setText(f"Dosya kaydedilemedi: {exc}")

    def _discard_download_thread(self, worker):
        if worker in self._download_threads:
            self._download_threads.remove(worker)

    def _load_selected_backups(self, _index=0):
        tenant_id = str(self._firm_combo.currentData() or "")
        if not tenant_id:
            return
        worker = _FetchBackups(tenant_id)
        worker.done.connect(self._show_selected_backups)
        worker.finished.connect(lambda current=worker: self._discard_backup_thread(current))
        self._backup_threads.append(worker)
        worker.start()

    def _show_selected_backups(self, tenant_id: str, rows: list):
        if tenant_id == str(self._firm_combo.currentData() or ""):
            self._populate_backups(rows)

    def _discard_backup_thread(self, worker):
        if worker in self._backup_threads:
            self._backup_threads.remove(worker)

    def _run_query(self):
        self._execute_query(self._sql_input.toPlainText().strip())

    def _run_explain_query(self):
        query = self._sql_input.toPlainText().strip().rstrip(";").strip()
        if query:
            self._execute_query("EXPLAIN QUERY PLAN " + query)
        else:
            self._status_lbl.setText("Sorgu metni bos olamaz.")

    def _execute_query(self, sql: str):
        tid = self._firm_combo.currentData()
        sql = str(sql or "").strip()
        if not tid:
            self._status_lbl.setText("Lutfen bir firma secin.")
            return
        if not sql:
            self._status_lbl.setText("Sorgu metni bos olamaz.")
            return
        if self._thread is not None and self._thread.isRunning():
            return

        self._status_lbl.setText("Sorgu calistiriliyor...")
        self._submitted_sql = sql
        self._run_btn.setEnabled(False)
        self._explain_btn.setEnabled(False)
        t = _RunSqlThread(tid, sql)
        t.done.connect(self._show_results)
        t.error.connect(self._show_error)
        t.finished.connect(self._query_finished)
        t.start()
        self._thread = t

    def _query_finished(self):
        self._run_btn.setEnabled(True)
        self._explain_btn.setEnabled(True)

    def _show_error(self, error: str):
        self._status_lbl.setText(f"Sorgu Hatasi: {error}")
        self._result_count.setText("Sorgu basarisiz")

    def _clear_query(self):
        self._sql_input.clear()
        self._table.clear()
        self._table.setRowCount(0)
        self._table.setColumnCount(0)
        while self._mobile_results_layout.count():
            item = self._mobile_results_layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                widget.setParent(None)
                widget.deleteLater()
        self._result_count.setText("Hen\u00fcz sorgu \u00e7al\u0131\u015ft\u0131r\u0131lmad\u0131")
        self._status_lbl.setText("Sorgu temizlendi.")

    def _restore_history(self, index: int):
        query = self._history_combo.itemData(index)
        if query:
            self._sql_input.setPlainText(str(query))

    def _show_results(self, data: dict):
        suffix = " Ilk 1000 satir gosteriliyor." if data.get("truncated") else ""
        columns = data.get("columns", [])
        rows = data.get("rows", [])
        self._status_lbl.setText(
            f"Sorgu basariyla tamamlandi: {len(rows)} satir.{suffix}"
        )
        self._result_count.setText(f"{len(rows)} satir / {len(columns)} sutun")
        query = self._submitted_sql or self._sql_input.toPlainText().strip()
        if query:
            self._sql_history = [query] + [
                saved for saved in self._sql_history if saved != query
            ]
            self._sql_history = self._sql_history[:8]
            self._history_combo.blockSignals(True)
            self._history_combo.clear()
            self._history_combo.addItem("Son sorgular")
            for saved in self._sql_history:
                self._history_combo.addItem(saved[:48], saved)
            self._history_combo.setCurrentIndex(0)
            self._history_combo.blockSignals(False)
        
        display_headers = {
            "role": "ROL",
            "last_login": "SON G\u0130R\u0130\u015e",
            "disk_usage_mb": "D\u0130SK (MB)",
        }
        self._table.setColumnCount(len(columns))
        self._table.setHorizontalHeaderLabels([
            display_headers.get(str(column).casefold(), str(column).upper())
            for column in columns
        ])
        self._table.setRowCount(min(len(rows), 1000))
        mono_font = QFont("JetBrains Mono")
        mono_font.setPixelSize(10)
        bold_font = QFont("JetBrains Mono")
        bold_font.setPixelSize(10)
        bold_font.setWeight(QFont.Weight.Bold)
        for row_idx, r in enumerate(rows[:1000]):
            self._table.setRowHeight(row_idx, 25)
            for col_idx, val in enumerate(r):
                item = QTableWidgetItem(str(val if val is not None else "NULL"))
                item.setFont(mono_font)
                item.setForeground(QColor("#dee2f6"))
                column_name = str(columns[col_idx]).casefold()
                if column_name == "id":
                    item.setForeground(QColor("#4cd7f6"))
                    item.setFont(bold_font)
                elif column_name == "role":
                    item.setForeground(QColor("#adc6ff"))
                    item.setBackground(QColor("#252a39"))
                elif column_name == "disk_usage_mb":
                    item.setForeground(QColor("#4edea3"))
                self._table.setItem(row_idx, col_idx, item)
        self._render_mobile_results(columns, rows[:1000])
        self._set_table_layout()
        self._table.scrollToTop()

    def _render_mobile_results(self, columns: list, rows: list):
        while self._mobile_results_layout.count():
            item = self._mobile_results_layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                widget.setParent(None)
                widget.deleteLater()
        for row_values in rows:
            card = QFrame()
            card.setObjectName("sqlResultCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(10, 8, 10, 8)
            card_layout.setSpacing(5)
            for column, value in zip(columns, row_values):
                line = QHBoxLayout()
                key_label = QLabel(str(column))
                key_label.setObjectName("sqlResultKey")
                key_label.setMinimumWidth(0)
                key_label.setWordWrap(True)
                value_label = QLabel(str(value if value is not None else "NULL"))
                value_label.setObjectName("sqlResultValue")
                value_label.setMinimumWidth(0)
                value_label.setWordWrap(True)
                line.addWidget(key_label, 1)
                line.addWidget(value_label, 2)
                card_layout.addLayout(line)
            self._mobile_results_layout.addWidget(card)
        self._mobile_results_layout.addStretch(1)
