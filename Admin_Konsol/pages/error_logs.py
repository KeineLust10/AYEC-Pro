"""
AYEC Pro Admin Konsol - Hata Loglari (Telemetri)
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QTextEdit, QSplitter, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor
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
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        # Baslik & filtreler
        top = QHBoxLayout()
        title = QLabel("\ud83d\udcdb Hata Loglari / Telemetri")
        title.setObjectName("pageTitle")
        top.addWidget(title)
        top.addStretch()

        top.addWidget(QLabel("Firma:"))
        self._firm_combo = QComboBox()
        self._firm_combo.setObjectName("combo")
        self._firm_combo.addItem("Tum Firmalar", "")
        self._firm_combo.currentIndexChanged.connect(self._load_logs)
        top.addWidget(self._firm_combo)

        refresh = QPushButton("\u21bb Yenile")
        refresh.setObjectName("secondaryBtn")
        refresh.clicked.connect(self._load_logs)
        top.addWidget(refresh)
        root.addLayout(top)

        # Splitter: tablo + detay
        splitter = QSplitter(Qt.Orientation.Vertical)

        self._table = QTableWidget()
        self._table.setObjectName("dataTable")
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(["Tarih", "Firma", "Bilgisayar", "Hata Turu", "Satir", "Mesaj"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.cellClicked.connect(self._show_detail)
        splitter.addWidget(self._table)

        detail_frame = QFrame()
        detail_frame.setObjectName("detailCard")
        detail_lay = QVBoxLayout(detail_frame)
        detail_lay.setContentsMargins(12, 12, 12, 12)
        detail_lbl = QLabel("Stack Trace / Detay:")
        detail_lbl.setObjectName("sectionTitle")
        detail_lay.addWidget(detail_lbl)
        self._detail = QTextEdit()
        self._detail.setObjectName("codeBox")
        self._detail.setReadOnly(True)
        self._detail.setFont(__import__("PyQt6.QtGui", fromlist=["QFont"]).QFont("Consolas", 10))
        detail_lay.addWidget(self._detail)
        splitter.addWidget(detail_frame)

        splitter.setSizes([400, 200])
        root.addWidget(splitter, 1)

        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("statusLabel")
        root.addWidget(self._status_lbl)

        self._logs: list[dict] = []

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
            level = str(log.get("level", "ERROR"))
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
                if col == 3:
                    item.setForeground(QColor(color))
                self._table.setItem(row, col, item)

    def _show_detail(self, row: int, col: int):
        if row < len(self._logs):
            log = self._logs[row]
            trace = log.get("traceback") or log.get("message") or "-"
            detail = f"Tarih: {log.get('timestamp')}\nFirma: {log.get('company')}\nDosya: {log.get('file')}\nSatir: {log.get('line')}\nHata: {log.get('level')}\n\n--- Stack Trace ---\n{trace}"
            self._detail.setText(detail)
