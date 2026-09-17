"""AYEC Pro Admin Console - privileged operation audit trail."""
import json

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import api_client


_ACTION_LABELS = {
    "admin_company_updated": "Firma g\u00fcncellendi",
    "company_sector_changed": "Sekt\u00f6r de\u011fi\u015ftirildi",
    "admin_password_reset": "Parola s\u0131f\u0131rland\u0131",
    "password_reset_link_created": "Parola ba\u011flant\u0131s\u0131 olu\u015fturuldu",
    "password_reset_completed": "Parola yenilendi",
    "admin_license_updated": "Lisans g\u00fcncellendi",
    "admin_notification_sent": "Bildirim g\u00f6nderildi",
    "admin_update_deployed": "G\u00fcncelleme da\u011f\u0131t\u0131ld\u0131",
    "admin_readonly_query": "Salt okunur sorgu \u00e7al\u0131\u015ft\u0131r\u0131ld\u0131",
    "desktop_restore_queued": "Geri y\u00fckleme kuyrukland\u0131",
    "admin_legacy_restore_queued": "Eski yedek geri y\u00fckleme kuyrukland\u0131",
    "control_company_updated": "Firma ayarlar\u0131 g\u00fcncellendi",
    "control_user_updated": "Kullan\u0131c\u0131 g\u00fcncellendi",
    "control_notification_sent": "Y\u00f6netim bildirimi g\u00f6nderildi",
    "control_update_staged": "G\u00fcncelleme yay\u0131na haz\u0131rland\u0131",
}


class _FetchCompanies(QThread):
    done = pyqtSignal(list)
    error = pyqtSignal(str)

    def run(self):
        try:
            self.done.emit(api_client.companies())
        except Exception as exc:
            self.error.emit(str(exc))


class _FetchAudit(QThread):
    done = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, tenant_id: str):
        super().__init__()
        self._tenant_id = tenant_id

    def run(self):
        try:
            self.done.emit(api_client.audit_logs(self._tenant_id, 500))
        except Exception as exc:
            self.error.emit(str(exc))


class AuditLogsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._logs: list[dict] = []
        self._workers: set[QThread] = set()
        self._build_ui()
        self._load_companies()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        top = QHBoxLayout()
        title = QLabel("\U0001f6e1 Denetim Kay\u0131tlar\u0131")
        title.setObjectName("pageTitle")
        top.addWidget(title)
        top.addStretch()
        top.addWidget(QLabel("Firma:"))
        self._company = QComboBox()
        self._company.setObjectName("combo")
        self._company.currentIndexChanged.connect(self._load_logs)
        top.addWidget(self._company)
        refresh = QPushButton("\u21bb Yenile")
        refresh.setObjectName("secondaryBtn")
        refresh.clicked.connect(self._load_logs)
        top.addWidget(refresh)
        root.addLayout(top)

        info = QLabel(
            "Parola, lisans, sekt\u00f6r, yedek, bildirim, g\u00fcncelleme ve uzaktan sorgu "
            "gibi ayr\u0131cal\u0131kl\u0131 i\u015flemler burada de\u011fi\u015ftirilemez bi\u00e7imde izlenir."
        )
        info.setObjectName("metricSub")
        info.setWordWrap(True)
        root.addWidget(info)

        splitter = QSplitter()
        self._table = QTableWidget()
        self._table.setObjectName("dataTable")
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels([
            "Tarih", "\u0130\u015flem", "Firma", "Y\u00f6netici", "Kay\u0131t No"
        ])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.currentCellChanged.connect(self._show_detail)
        splitter.addWidget(self._table)

        self._detail = QTextEdit()
        self._detail.setObjectName("codeBox")
        self._detail.setReadOnly(True)
        self._detail.setPlaceholderText("Denetim ayr\u0131nt\u0131lar\u0131")
        splitter.addWidget(self._detail)
        splitter.setSizes([900, 420])
        root.addWidget(splitter, 1)

        self._status = QLabel("")
        self._status.setObjectName("statusLabel")
        root.addWidget(self._status)

    def _keep(self, worker: QThread):
        self._workers.add(worker)
        worker.finished.connect(lambda: self._workers.discard(worker))
        worker.start()

    def _load_companies(self):
        worker = _FetchCompanies()
        worker.done.connect(self._populate_companies)
        worker.error.connect(lambda error: self._status.setText(f"Hata: {error}"))
        self._keep(worker)

    def _populate_companies(self, companies: list):
        self._company.blockSignals(True)
        self._company.clear()
        self._company.addItem("T\u00fcm firmalar", "")
        for company in companies:
            self._company.addItem(company.get("company_name", "?"), company.get("id", ""))
        self._company.blockSignals(False)
        self._load_logs()

    def _load_logs(self):
        self._status.setText("Denetim kay\u0131tlar\u0131 y\u00fckleniyor...")
        worker = _FetchAudit(str(self._company.currentData() or ""))
        worker.done.connect(self._populate_logs)
        worker.error.connect(self._load_error)
        self._keep(worker)

    def _load_error(self, error: str):
        self._status.setText(
            f"Denetim kay\u0131tlar\u0131 al\u0131namad\u0131: {error}. "
            "Sunucu taraf\u0131n\u0131n bu konsol s\u00fcr\u00fcm\u00fcyle g\u00fcncel oldu\u011funu do\u011frulay\u0131n."
        )

    def _populate_logs(self, logs: list):
        self._logs = logs
        self._table.setRowCount(0)
        for entry in logs:
            row = self._table.rowCount()
            self._table.insertRow(row)
            action = str(entry.get("action") or "")
            values = [
                entry.get("created_at", ""),
                _ACTION_LABELS.get(action, action),
                entry.get("company_name", "Sistem"),
                entry.get("actor_user_id", "-"),
                entry.get("id", ""),
            ]
            for column, value in enumerate(values):
                self._table.setItem(row, column, QTableWidgetItem(str(value)))
        self._status.setText(f"{len(logs)} denetim kayd\u0131 g\u00f6steriliyor.")
        if logs:
            self._table.selectRow(0)
            self._show_detail(0, 0, -1, -1)
        else:
            self._detail.clear()

    def _show_detail(self, row: int, _column: int, _old_row: int, _old_column: int):
        if row < 0 or row >= len(self._logs):
            return
        entry = self._logs[row]
        detail = {
            "record_id": entry.get("id"),
            "created_at": entry.get("created_at"),
            "action": entry.get("action"),
            "company": entry.get("company_name"),
            "actor_tenant_id": entry.get("actor_tenant_id"),
            "actor_user_id": entry.get("actor_user_id"),
            "target_tenant_id": entry.get("target_tenant_id"),
            "target_user_id": entry.get("target_user_id"),
            "detail": entry.get("detail") or {},
        }
        self._detail.setPlainText(json.dumps(detail, ensure_ascii=True, indent=2))
