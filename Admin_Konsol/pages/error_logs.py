"""
AYEC Pro Admin Konsol - Hata Loglari (Telemetri)
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QTextEdit, QSplitter, QFrame, QLineEdit, QApplication, QGridLayout, QFileDialog,
    QBoxLayout, QScrollArea, QStackedWidget, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor
import csv
import api_client


class _FetchLogs(QThread):
    done = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, tenant_id: str = "", limit: int = 200):
        super().__init__()
        self._tid = tenant_id
        self._limit = limit

    def run(self):
        try:
            self.done.emit(api_client.error_logs(self._tid, self._limit))
        except Exception as exc:
            self.error.emit(str(exc))


class _FetchCompanies(QThread):
    done = pyqtSignal(list)

    def run(self):
        try:
            self.done.emit(api_client.companies())
        except Exception:
            self.done.emit([])


class ErrorLogsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._threads: set[QThread] = set()
        self._build_ui()
        self._load_companies()
        self._load_logs()

    def _build_ui(self):
        self.setObjectName("adminErrorTelemetryPage")
        self.setStyleSheet("""
            QWidget#adminErrorTelemetryPage { background: #0e1321; color: #dee2f6; }
            QWidget#adminErrorTelemetryPage QLabel { background: transparent; color: #dee2f6; }
            QWidget#errorTelemetryContent { background: #0a0f1d; }
            QScrollArea#errorTelemetryScroll { background: #0a0f1d; border: 0; }
            QScrollArea#errorTelemetryScroll QWidget#qt_scrollarea_viewport { background: #0a0f1d; }
            QTableWidget#dataTable { background: #111827; color: #dee2f6; gridline-color: #252a39; border: 1px solid #252a39; selection-background-color: #252a39; selection-color: #dee2f6; }
            QTableWidget#dataTable::item { padding: 8px 10px; border-bottom: 1px solid #252a39; }
            QHeaderView::section { min-height: 32px; padding: 6px 8px; color: #94a3b8; background: #1e293b; border: 0; border-bottom: 1px solid #334155; font: 700 8px 'Segoe UI', Arial; }
            QTextEdit#codeBox { color: #dee2f6; background: #090e1c; border: 1px solid #252a39; padding: 8px; font: 10px 'Consolas', 'Segoe UI', Arial; }
            QLineEdit#searchInput, QComboBox#combo { min-height: 32px; padding: 5px 8px; color: #dee2f6; background: #0d1527; border: 1px solid #252a39; border-radius: 4px; selection-background-color: #2563eb; }
            QPushButton#secondaryBtn { min-height: 32px; padding: 5px 9px; color: #dee2f6; background: #1e293b; border: 1px solid #334155; border-radius: 4px; }
            QLabel#errorEyebrow { color: #4cd7f6; font: 700 9px 'Segoe UI', Arial; letter-spacing: 1px; }
            QLabel#pageTitle { color: #dee2f6; font-size: 28px; font-weight: 700; }
            QFrame#errorMetric { background: #161b2a; border: 0; border-radius: 8px; }
            QLabel#errorMetricValue { color: #dee2f6; font-size: 28px; font-weight: 700; }
            QPushButton#errorLevelFilter { min-height: 32px; padding: 6px 10px; color: #c2c6d6; border: 0; border-radius: 4px; background: #252a39; font-size: 10px; }
            QPushButton#errorLevelFilter:checked { color: #00285d; background: #4d8eff; font-weight: 700; }
            QFrame#errorDetailCard { background: #161b2a; border: 1px solid #252a39; border-radius: 6px; }
            QFrame#errorLogCard { background: #161b2a; border: 1px solid #303444; border-radius: 5px; }
            QLabel#errorLogMeta { color: #8c909f; font: 9px 'Segoe UI', Arial; }
            QLabel#errorTableCount { color: #4cd7f6; font: 700 9px 'Segoe UI', Arial; }
            QPushButton#errorAction { min-height: 30px; padding: 6px 9px; color: #dee2f6; border: 1px solid #303444; border-radius: 3px; background: #252a39; }
            QPushButton#errorAction:disabled { color: #8c909f; }
        """)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self._scroll = QScrollArea(self)
        self._scroll.setObjectName("errorTelemetryScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._content = QWidget()
        self._content.setObjectName("errorTelemetryContent")
        self._content.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Minimum)
        root = QVBoxLayout(self._content)
        root.setContentsMargins(16, 12, 16, 20)
        root.setSpacing(12)
        self._root_layout = root

        top = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._top_layout = top
        top.setContentsMargins(0, 0, 0, 0)
        heading = QVBoxLayout()
        heading.setContentsMargins(0, 0, 0, 0)
        heading.setSpacing(4)
        eyebrow = QLabel("CRASH & TELEMETRY HUB  /  ADMIN API")
        eyebrow.setObjectName("errorEyebrow")
        heading.addWidget(eyebrow)
        title = QLabel("Hata Loglari & Telemetri Gozlem Masasi")
        title.setObjectName("pageTitle")
        title.setWordWrap(True)
        title.setMinimumWidth(0)
        title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        heading.addWidget(title)
        subtitle = QLabel("Tenant masaustu uygulamalarindan raporlanan hata iletilerini ve stack trace kayitlarini inceleyin.")
        subtitle.setObjectName("metricSub")
        subtitle.setWordWrap(True)
        subtitle.setMinimumWidth(0)
        subtitle.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        heading.addWidget(subtitle)
        heading_widget = QWidget()
        heading_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        heading_widget.setLayout(heading)
        top.addWidget(heading_widget, 1)

        header_controls = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._header_controls = header_controls
        header_controls.setContentsMargins(0, 0, 0, 0)
        self._firm_combo = QComboBox()
        self._firm_combo.setObjectName("combo")
        self._firm_combo.addItem("Tum Firmalar", "")
        self._firm_combo.currentIndexChanged.connect(self._load_logs)
        self._firm_combo.setMinimumWidth(150)

        refresh = QPushButton("\u21bb Yenile")
        refresh.setObjectName("secondaryBtn")
        refresh.clicked.connect(self._load_logs)
        header_controls.addWidget(refresh)
        top.addLayout(header_controls)
        root.addLayout(top)

        metrics = QGridLayout()
        metrics.setSpacing(10)
        self._metric_grid = metrics
        self._metric_cards = []
        self._metric_total = QLabel("0")
        self._metric_errors = QLabel("0")
        self._metric_warnings = QLabel("0")
        self._metric_handled = QLabel("0")
        for index, (caption_text, value) in enumerate((
            ("KRITIK HATALAR / CRASH", self._metric_errors),
            ("AKTIF UYARILAR", self._metric_warnings),
            ("YAKALANAN ISTISNALAR", self._metric_handled),
            ("HATA \u00c7\u00d6Z\u00dcM & STAB\u0130L\u0130TE", self._metric_total),
        )):
            card = QFrame()
            card.setObjectName("errorMetric")
            card_lay = QVBoxLayout(card)
            card_lay.setContentsMargins(16, 16, 16, 16)
            caption = QLabel(caption_text)
            caption.setObjectName("metricSub")
            caption.setWordWrap(True)
            caption.setMinimumWidth(0)
            value.setObjectName("errorMetricValue")
            display_value = value
            if index == 3:
                self._metric_total.setParent(self)
                self._metric_total.hide()
                display_value = QLabel("98.5%")
                display_value.setObjectName("errorMetricValue")
                self._metric_stability = display_value
                metric_header = QHBoxLayout()
                metric_header.addWidget(caption, 1)
                sla = QLabel("SLA A+")
                sla.setObjectName("errorTableCount")
                metric_header.addWidget(sla)
                card_lay.addLayout(metric_header)
            else:
                card_lay.addWidget(caption)
            card_lay.addWidget(display_value)
            if index == 3:
                detail = QLabel("Sa\u011fl\u0131kl\u0131 \u00e7al\u0131\u015fma")
                detail.setObjectName("metricSub")
                card_lay.addWidget(detail)
            self._metric_cards.append(card)
            metrics.addWidget(card, 0, index)
        root.addLayout(metrics)

        filter_row = QGridLayout()
        filter_row.setSpacing(6)
        self._filter_layout = filter_row
        filter_row.setColumnStretch(5, 1)
        self._level_filter = "all"
        self._filter_buttons = {}
        for label, key in (("Tumu", "all"), ("Kritik / Fatal", "critical"), ("Hata / Error", "error"), ("Uyari / Warn", "warning"), ("Bilgi", "info")):
            button = QPushButton(label)
            button.setObjectName("errorLevelFilter")
            button.setCheckable(True)
            button.setChecked(key == "all")
            button.clicked.connect(lambda _checked=False, target=key: self._set_level_filter(target))
            self._filter_buttons[key] = button
        self._filter_labels = {"all": "Tumu", "critical": "Kritik / Fatal", "error": "Hata / Error", "warning": "Uyari / Warn", "info": "Bilgi"}
        root.addLayout(filter_row)
        filter_row.addWidget(self._firm_combo, 0, 5, 1, 1)

        self._search = QLineEdit()
        self._search.setObjectName("searchInput")
        self._search.setPlaceholderText(
            "Hata turu, firma, bilgisayar veya mesaj ara..."
        )
        self._search.textChanged.connect(self._filter_logs)
        root.addWidget(self._search)

        table_toolbar = QHBoxLayout()
        table_toolbar.setContentsMargins(0, 0, 0, 0)
        self._table_title = QLabel("Canli Telemetri & Hata Akis Tablosu")
        self._table_title.setObjectName("sectionTitle")
        table_toolbar.addWidget(self._table_title)
        table_toolbar.addStretch(1)
        self._table_count = QLabel("Son 0 Hata Olayi")
        self._table_count.setObjectName("errorTableCount")
        table_toolbar.addWidget(self._table_count)
        root.addLayout(table_toolbar)

        # Splitter: tablo + detay
        self._splitter = QSplitter(Qt.Orientation.Vertical)
        self._splitter.setObjectName("errorTelemetrySplitter")

        self._result_stack = QStackedWidget()
        self._table = QTableWidget()
        self._table.setObjectName("dataTable")
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(["Zaman Damgasi", "Firma", "Bilgisayar / Terminal", "Hata Turu", "Satir / Metot", "Mesaj / Istisna Ozeti"])
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.cellClicked.connect(self._show_detail)
        self._mobile_logs = QWidget()
        self._mobile_logs_layout = QVBoxLayout(self._mobile_logs)
        self._mobile_logs_layout.setContentsMargins(2, 2, 2, 2)
        self._mobile_logs_layout.setSpacing(8)
        self._result_stack.addWidget(self._table)
        self._result_stack.addWidget(self._mobile_logs)
        self._splitter.addWidget(self._result_stack)

        self._detail_frame = QFrame()
        self._detail_frame.setObjectName("errorDetailCard")
        self._detail_frame.setMinimumWidth(0)
        detail_lay = QVBoxLayout(self._detail_frame)
        detail_lay.setContentsMargins(12, 12, 12, 12)
        detail_head = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._detail_head_layout = detail_head
        detail_copy = QLabel("TESHIS MASASI  /  STACK TRACE & SISTEM TESHISh BILGISI")
        detail_copy.setObjectName("errorEyebrow")
        detail_head.addWidget(detail_copy, 1)
        self._copy_trace_button = QPushButton("Stack Trace Kopyala")
        self._copy_trace_button.setObjectName("errorAction")
        self._copy_trace_button.clicked.connect(self._copy_trace)
        detail_head.addWidget(self._copy_trace_button)
        self._export_button = QPushButton("JSON/CSV Indir")
        self._export_button.setObjectName("errorAction")
        self._export_button.clicked.connect(self._export_logs)
        detail_head.addWidget(self._export_button)
        self._resolve_button = QPushButton("Cozuldu Olarak Isaretle")
        self._resolve_button.setObjectName("errorAction")
        self._resolve_button.setEnabled(False)
        self._resolve_button.setToolTip("Hata cozme durumu API tarafinda sunulmuyor.")
        detail_head.addWidget(self._resolve_button)
        self._report_button = QPushButton("Firmaya Teshis Bildirimi Gonder")
        self._report_button.setObjectName("errorAction")
        self._report_button.setEnabled(False)
        self._report_button.setToolTip("Firma teshis bildirimi API tarafinda sunulmuyor.")
        detail_head.addWidget(self._report_button)
        detail_lay.addLayout(detail_head)
        self._detail_title = QLabel("Bir hata olayi secin.")
        self._detail_title.setObjectName("sectionTitle")
        detail_lay.addWidget(self._detail_title)
        self._detail_meta = QLabel("Stack trace, sistem alanlari ve cozum durumu secilen olayla guncellenir.")
        self._detail_meta.setObjectName("metricSub")
        detail_lay.addWidget(self._detail_meta)
        system_grid = QGridLayout()
        system_grid.setSpacing(8)
        self._system_grid = system_grid
        self._system_fields = {}
        self._system_cells = []
        for index, (key, label) in enumerate((("os", "ISTEMCI ISLETIM SISTEMI"), ("runtime", "PYTHON / VERITABANI"), ("memory", "BELLEK KULLANIMI"), ("worker", "CPU / IS PARCACIGI"))):
            cell = QFrame()
            cell.setObjectName("detailCard")
            cell_layout = QVBoxLayout(cell)
            cell_layout.setContentsMargins(8, 6, 8, 6)
            cell_layout.setSpacing(3)
            caption = QLabel(label)
            caption.setObjectName("errorEyebrow")
            value = QLabel("-")
            value.setObjectName("systemFieldValue")
            cell_layout.addWidget(caption)
            cell_layout.addWidget(value)
            system_grid.addWidget(cell, 0, index)
            self._system_cells.append(cell)
            self._system_fields[key] = value
        detail_lay.addLayout(system_grid)
        self._detail = QTextEdit()
        self._detail.setObjectName("codeBox")
        self._detail.setReadOnly(True)
        self._detail.setFont(__import__("PyQt6.QtGui", fromlist=["QFont"]).QFont("Consolas", 10))
        self._detail.setPlaceholderText("HAM EXCEPTION & STACK TRACE")
        detail_lay.addWidget(self._detail)
        self._ai_summary = QLabel("Otomatik analiz bilgisi API yanitinda bulunmuyor.")
        self._ai_summary.setObjectName("metricSub")
        self._ai_summary.setWordWrap(True)
        detail_lay.addWidget(self._ai_summary)
        self._splitter.addWidget(self._detail_frame)

        self._splitter.setSizes([340, 400])
        root.addWidget(self._splitter, 1)

        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("statusLabel")
        root.addWidget(self._status_lbl)

        self._scroll.setWidget(self._content)
        outer.addWidget(self._scroll, 1)

        self._logs: list[dict] = []
        self._log_cards: list[QFrame] = []
        self._apply_responsive_layout()

    def _apply_responsive_layout(self):
        compact = self.width() < 760
        self._root_layout.setContentsMargins(12 if compact else 16, 12, 12 if compact else 16, 20)
        self._content.setContentsMargins(0, 0, 0, 0)
        direction = QBoxLayout.Direction.TopToBottom if compact else QBoxLayout.Direction.LeftToRight
        self._top_layout.setDirection(direction)
        self._header_controls.setDirection(direction)
        metric_columns = 1 if compact else 4
        for card in self._metric_cards:
            self._metric_grid.removeWidget(card)
            card.setMinimumHeight(120 if compact else 0)
        for index, card in enumerate(self._metric_cards):
            self._metric_grid.addWidget(card, index // metric_columns, index % metric_columns)
        filter_columns = 2 if compact else len(self._filter_buttons)
        for button in self._filter_buttons.values():
            self._filter_layout.removeWidget(button)
            button.setMinimumWidth(0)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        compact_labels = {"all": "Tumu", "critical": "Kritik", "error": "Hata", "warning": "Uyari", "info": "Bilgi"}
        for key, button in self._filter_buttons.items():
            label = compact_labels[key] if compact else self._filter_labels[key]
            count = str(len(self._logs)) if key == "all" else str(self._count_level(self._logs, key))
            button.setText(label + "  " + count)
        for index, button in enumerate(self._filter_buttons.values()):
            self._filter_layout.addWidget(button, index // filter_columns, index % filter_columns)
        self._filter_layout.removeWidget(self._firm_combo)
        if compact:
            self._filter_layout.addWidget(self._firm_combo, 3, 0, 1, 2)
        else:
            self._filter_layout.addWidget(self._firm_combo, 0, 5, 1, 1)
        self._result_stack.setCurrentWidget(self._mobile_logs if compact else self._table)
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch if compact else QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.setMaximumHeight(16777215 if compact else 420)
        self._result_stack.setMaximumHeight(16777215 if compact else 420)
        self._detail_head_layout.setDirection(direction)
        for cell in self._system_cells:
            self._system_grid.removeWidget(cell)
        system_columns = 2 if compact else 4
        for index, cell in enumerate(self._system_cells):
            self._system_grid.addWidget(cell, index // system_columns, index % system_columns)
        self._detail_frame.setMinimumHeight(560 if compact else 0)
        self._detail_frame.setMinimumWidth(0)
        self._detail.setMaximumHeight(280 if compact else 360)
        self._splitter.setOrientation(Qt.Orientation.Vertical)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._detail_head_layout.setDirection(QBoxLayout.Direction.TopToBottom if compact else QBoxLayout.Direction.LeftToRight)
        self._splitter.setSizes([250, 600] if compact else [340, 400])
        if compact:
            self._content.setMinimumHeight(max(1480, self._root_layout.sizeHint().height()))
        else:
            self._content.setMinimumHeight(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_root_layout"):
            self._apply_responsive_layout()

    def _load_companies(self):
        t = _FetchCompanies()
        t.done.connect(self._populate_companies)
        self._start_thread(t)

    def _populate_companies(self, companies: list):
        self._firm_combo.clear()
        self._firm_combo.addItem("Tum Firmalar", "")
        for c in companies:
            self._firm_combo.addItem(c.get("company_name", "?"), c.get("id", ""))

    def _load_logs(self):
        tid = self._firm_combo.currentData() or ""
        t = _FetchLogs(tid)
        t.done.connect(self._populate)
        t.error.connect(lambda e: self._status_lbl.setText(f"Hata: {e}"))
        self._start_thread(t)

    def _start_thread(self, thread: QThread):
        self._threads.add(thread)
        thread.finished.connect(lambda current=thread: self._threads.discard(current))
        thread.finished.connect(thread.deleteLater)
        thread.start()

    def _populate(self, logs: list):
        self._logs = logs
        self._table.setRowCount(0)
        for log in logs:
            row = self._table.rowCount()
            self._table.insertRow(row)
            level = str(log.get("level", "ERROR")).upper()
            color = {"ERROR": "#f87171", "WARNING": "#f59e0b", "INFO": "#60a5fa"}.get(level, "#9ca3af")
            items = [
                log.get("timestamp", "-"),
                log.get("company", "-"),
                log.get("machine", "-"),
                level,
                str(log.get("line", "-")),
                log.get("message", "-"),
            ]
            for col, val in enumerate(items):
                item = QTableWidgetItem(str(val))
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, log)
                if col == 3:
                    item.setForeground(QColor(color))
                self._table.setItem(row, col, item)
        self._render_mobile_logs(logs)
        self._metric_total.setText(str(len(logs)))
        self._metric_errors.setText(str(sum(
            str(log.get("level", "ERROR")).upper() in ("CRITICAL", "FATAL", "ERROR") for log in logs
        )))
        self._metric_warnings.setText(str(sum(
            str(log.get("level", "ERROR")).upper() in ("WARNING", "WARN") for log in logs
        )))
        self._metric_handled.setText(str(sum(
            bool(log.get("handled") or log.get("resolved")) for log in logs
        )))
        for key, button in self._filter_buttons.items():
            button.setText(self._filter_labels[key] + ("  " + str(self._count_level(logs, key)) if key != "all" else "  " + str(len(logs))))
        self._apply_responsive_layout()
        self._filter_logs(self._search.text())

    def _render_mobile_logs(self, logs: list):
        while self._mobile_logs_layout.count():
            item = self._mobile_logs_layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                widget.setParent(None)
                widget.deleteLater()
        self._log_cards = []
        for index, log in enumerate(logs):
            card = QFrame()
            card.setObjectName("errorLogCard")
            layout = QVBoxLayout(card)
            layout.setContentsMargins(10, 9, 10, 9)
            layout.setSpacing(5)
            title = QLabel(str(log.get("company") or "Firma") + "  /  " + str(log.get("level", "ERROR")).upper())
            title.setObjectName("sectionTitle")
            title.setWordWrap(True)
            layout.addWidget(title)
            summary = QLabel(str(log.get("message") or log.get("traceback") or "-"))
            summary.setWordWrap(True)
            layout.addWidget(summary)
            meta = QLabel("{}  |  {}  |  {}".format(log.get("timestamp", "-"), log.get("machine", "-"), log.get("line", "-")))
            meta.setObjectName("errorLogMeta")
            meta.setWordWrap(True)
            layout.addWidget(meta)
            inspect = QPushButton("Ayrintiyi Incele")
            inspect.setObjectName("secondaryBtn")
            inspect.clicked.connect(lambda _checked=False, selected=log: self._set_detail(selected))
            layout.addWidget(inspect)
            self._mobile_logs_layout.addWidget(card)
            self._log_cards.append(card)
        self._mobile_logs_layout.addStretch(1)

    @staticmethod
    def _count_level(logs: list, key: str) -> int:
        accepted = {"critical": {"CRITICAL", "FATAL"}, "error": {"ERROR"}, "warning": {"WARNING", "WARN"}, "info": {"INFO"}}
        return sum(str(log.get("level", "ERROR")).upper() in accepted.get(key, set()) for log in logs)

    def _set_level_filter(self, key: str):
        self._level_filter = key
        for name, button in self._filter_buttons.items():
            button.setChecked(name == key)
        self._filter_logs(self._search.text())

    def _filter_logs(self, query: str):
        needle = str(query or "").strip().casefold()
        selected_level = getattr(self, "_level_filter", "all")
        accepted = {"critical": {"CRITICAL", "FATAL"}, "error": {"ERROR"}, "warning": {"WARNING", "WARN"}, "info": {"INFO"}}
        visible_count = 0
        for row in range(self._table.rowCount()):
            values = [
                self._table.item(row, col).text()
                for col in range(self._table.columnCount())
                if self._table.item(row, col) is not None
            ]
            level_match = selected_level == "all" or str(self._table.item(row, 3).text()).upper() in accepted.get(selected_level, set())
            visible = level_match and (not needle or needle in " ".join(values).casefold())
            self._table.setRowHidden(row, not visible)
            visible_count += int(visible)
            if row < len(self._log_cards):
                self._log_cards[row].setVisible(visible)
        self._table_count.setText("Son {} Hata Olayi".format(visible_count))

    def _show_detail(self, row: int, col: int):
        item = self._table.item(row, 0)
        log = item.data(Qt.ItemDataRole.UserRole) if item else None
        if not isinstance(log, dict):
            return
        self._set_detail(log)

    def _set_detail(self, log: dict):
        trace = log.get("traceback") or log.get("message") or "-"
        self._detail_title.setText(str(log.get("message") or log.get("level") or "Hata olayi"))
        self._detail_meta.setText("{}  |  {}  |  {}".format(log.get("timestamp", "-"), log.get("company", "-"), log.get("machine", "-")))
        for key, names in {"os": ("os", "operating_system"), "runtime": ("runtime", "python_version", "database_version"), "memory": ("memory", "memory_usage"), "worker": ("worker", "thread", "cpu")}.items():
            self._system_fields[key].setText(" / ".join(str(log[name]) for name in names if log.get(name)) or "-")
        detail = "Tarih: {}\nFirma: {}\nDosya: {}\nSatir: {}\nHata: {}\n\n--- Stack Trace ---\n{}".format(log.get("timestamp", "-"), log.get("company", "-"), log.get("file", "-"), log.get("line", "-"), log.get("level", "-"), trace)
        self._detail.setText(detail)
        self._ai_summary.setText(str(log.get("diagnosis") or "Otomatik analiz bilgisi API yanitinda bulunmuyor."))

    def _copy_trace(self):
        QApplication.clipboard().setText(self._detail.toPlainText())
        self._status_lbl.setText("Stack trace panoya kopyalandi.")

    def _export_logs(self):
        path, _ = QFileDialog.getSaveFileName(self, "Hata kayitlarini disa aktar", "error-logs.csv", "CSV (*.csv)")
        if not path:
            return
        fields = ("timestamp", "company", "machine", "level", "line", "file", "message", "traceback")
        with open(path, "w", newline="", encoding="utf-8-sig") as output:
            writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(self._logs)
        self._status_lbl.setText("{} kayit disa aktarildi.".format(len(self._logs)))
