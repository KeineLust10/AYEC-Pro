"""
AYEC Pro Admin Konsol - SQL & Veritaban\u0131 Y\u00f6neticisi Sayfas\u0131
Se\u00e7ilen firma veritaban\u0131nda uzaktan SQL komutlar\u0131 \u00e7al\u0131\u015ft\u0131rma.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QSplitter, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
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
    done = pyqtSignal(list)

    def run(self):
        try:
            self.done.emit(api_client.companies())
        except Exception:
            self.done.emit([])


class DatabaseManagerPage(QWidget):
    def __init__(self):
        super().__init__()
        self._thread = None
        self._build_ui()
        self._load_companies()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        # \u00dcst K\u0131s\u0131m
        top = QHBoxLayout()
        title = QLabel("\ud83d\uddd4 Uzak SQL Sorgu Yoneticisi")
        title.setObjectName("pageTitle")
        top.addWidget(title)
        top.addStretch()

        top.addWidget(QLabel("Firma Secin:"))
        self._firm_combo = QComboBox()
        self._firm_combo.setObjectName("combo")
        top.addWidget(self._firm_combo)
        root.addLayout(top)

        splitter = QSplitter(Qt.Orientation.Vertical)

        # Sorgu Giri\u015f Alan\u0131
        input_frame = QFrame()
        input_lay = QVBoxLayout(input_frame)
        input_lay.setContentsMargins(0, 0, 0, 0)
        
        input_lay.addWidget(QLabel(
            "Salt okunur teshis sorgusu (SELECT, EXPLAIN QUERY PLAN veya guvenli PRAGMA):"
        ))
        self._sql_input = QTextEdit()
        self._sql_input.setObjectName("codeBox")
        self._sql_input.setPlaceholderText(
            "SELECT id, username, role FROM users ORDER BY id LIMIT 100;"
        )
        self._sql_input.setFont(__import__("PyQt6.QtGui", fromlist=["QFont"]).QFont("Consolas", 10))
        input_lay.addWidget(self._sql_input)

        btn_row = QHBoxLayout()
        run_btn = QPushButton("\u26a1 Sorguyu Calistir")
        run_btn.setObjectName("primaryBtn")
        run_btn.clicked.connect(self._run_query)
        btn_row.addWidget(run_btn)
        btn_row.addStretch()
        input_lay.addLayout(btn_row)
        splitter.addWidget(input_frame)

        # Sorgu \u00c7\u0131kt\u0131 Tablosu
        output_frame = QFrame()
        output_lay = QVBoxLayout(output_frame)
        output_lay.setContentsMargins(0, 0, 0, 0)
        output_lay.addWidget(QLabel("Sorgu Sonuclari:"))

        self._table = QTableWidget()
        self._table.setObjectName("dataTable")
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        output_lay.addWidget(self._table)
        splitter.addWidget(output_frame)

        splitter.setSizes([200, 300])
        root.addWidget(splitter, 1)

        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("statusLabel")
        root.addWidget(self._status_lbl)

    def _load_companies(self):
        t = _FetchCompanies()
        t.done.connect(self._populate_companies)
        t.start()
        self._thread = t

    def _populate_companies(self, companies: list):
        self._firm_combo.clear()
        for c in companies:
            self._firm_combo.addItem(c.get("company_name", "?"), c.get("id", ""))

    def _run_query(self):
        tid = self._firm_combo.currentData()
        sql = self._sql_input.toPlainText().strip()
        if not tid:
            self._status_lbl.setText("Lutfen bir firma secin.")
            return
        if not sql:
            self._status_lbl.setText("Sorgu metni bos olamaz.")
            return

        self._status_lbl.setText("Sorgu calistiriliyor...")
        t = _RunSqlThread(tid, sql)
        t.done.connect(self._show_results)
        t.error.connect(lambda e: self._status_lbl.setText(f"Sorgu Hatasi: {e}"))
        t.start()
        self._thread = t

    def _show_results(self, data: dict):
        suffix = " Ilk 1000 satir gosteriliyor." if data.get("truncated") else ""
        self._status_lbl.setText(f"\u2705 Sorgu basariyla tamamlandi.{suffix}")
        columns = data.get("columns", [])
        rows = data.get("rows", [])
        
        self._table.setColumnCount(len(columns))
        self._table.setHorizontalHeaderLabels(columns)
        self._table.setRowCount(0)
        
        for r in rows:
            row_idx = self._table.rowCount()
            self._table.insertRow(row_idx)
            for col_idx, val in enumerate(r):
                self._table.setItem(row_idx, col_idx, QTableWidgetItem(str(val if val is not None else "NULL")))
        
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
