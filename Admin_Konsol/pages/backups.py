"""AYEC Pro Admin Console - backup catalog and remote restore operations."""
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import api_client


class _FetchCompanies(QThread):
    done = pyqtSignal(list)
    error = pyqtSignal(str)

    def run(self):
        try:
            self.done.emit(api_client.companies())
        except Exception as exc:
            self.error.emit(str(exc))


class _FetchBackups(QThread):
    done = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, tenant_id: str):
        super().__init__()
        self._tenant_id = tenant_id

    def run(self):
        try:
            self.done.emit(api_client.backups(self._tenant_id))
        except Exception as exc:
            self.error.emit(str(exc))


class _DownloadBackup(QThread):
    done = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, tenant_id: str, item: dict, target: str):
        super().__init__()
        self._tenant_id = tenant_id
        self._item = item
        self._target = target

    def run(self):
        try:
            payload = api_client.download_backup(
                self._tenant_id,
                int(self._item.get("index", 0)),
                int(self._item.get("backup_id", 0)),
            )
            Path(self._target).write_bytes(payload)
            self.done.emit(self._target)
        except Exception as exc:
            self.error.emit(str(exc))


class _RestoreBackup(QThread):
    done = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, tenant_id: str, item: dict):
        super().__init__()
        self._tenant_id = tenant_id
        self._item = item

    def run(self):
        try:
            self.done.emit(api_client.restore_backup(
                self._tenant_id,
                int(self._item.get("index", 0)),
                int(self._item.get("backup_id", 0)),
            ))
        except Exception as exc:
            self.error.emit(str(exc))


def _size_text(size_bytes: int) -> str:
    value = float(size_bytes or 0)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024.0 or unit == "GB":
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return "0 B"


class BackupsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._items: list[dict] = []
        self._workers: set[QThread] = set()
        self._build_ui()
        self._load_companies()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        title_row = QHBoxLayout()
        title = QLabel("\U0001f4be Yedekleme ve Kurtarma")
        title.setObjectName("pageTitle")
        title_row.addWidget(title)
        title_row.addStretch()
        title_row.addWidget(QLabel("Firma:"))
        self._company_combo = QComboBox()
        self._company_combo.setObjectName("combo")
        self._company_combo.currentIndexChanged.connect(self._load_backups)
        title_row.addWidget(self._company_combo)
        refresh = QPushButton("\u21bb Yenile")
        refresh.setObjectName("secondaryBtn")
        refresh.clicked.connect(self._load_backups)
        title_row.addWidget(refresh)
        root.addLayout(title_row)

        info = QLabel(
            "Masa\u00fcst\u00fc istemcilerinden gelen yedekleri izleyin, indirin ve "
            "se\u00e7ilen s\u00fcr\u00fcm\u00fc istemciye geri y\u00fckleme komutu olarak g\u00f6nderin."
        )
        info.setObjectName("metricSub")
        info.setWordWrap(True)
        root.addWidget(info)

        self._table = QTableWidget()
        self._table.setObjectName("dataTable")
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels([
            "Dosya", "Kaynak", "Tarih", "Boyut", "Durum", "Program", "Cihaz"
        ])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in range(1, 7):
            self._table.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeMode.ResizeToContents
            )
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.doubleClicked.connect(lambda _index: self._download_selected())
        root.addWidget(self._table, 1)

        action_row = QHBoxLayout()
        self._status = QLabel("")
        self._status.setObjectName("statusLabel")
        action_row.addWidget(self._status, 1)
        download = QPushButton("\u2b07 Yede\u011fi \u0130ndir")
        download.setObjectName("secondaryBtn")
        download.clicked.connect(self._download_selected)
        action_row.addWidget(download)
        restore = QPushButton("\u21bb Geri Y\u00fckleme Kuyrukla")
        restore.setObjectName("dangerBtn")
        restore.clicked.connect(self._restore_selected)
        action_row.addWidget(restore)
        root.addLayout(action_row)

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
        self._company_combo.blockSignals(True)
        self._company_combo.clear()
        for company in companies:
            self._company_combo.addItem(
                company.get("company_name", "?"), company.get("id", "")
            )
        self._company_combo.blockSignals(False)
        self._load_backups()

    def _load_backups(self):
        tenant_id = self._company_combo.currentData()
        if not tenant_id:
            return
        self._status.setText("Yedekler y\u00fckleniyor...")
        worker = _FetchBackups(str(tenant_id))
        worker.done.connect(self._populate_backups)
        worker.error.connect(lambda error: self._status.setText(f"Hata: {error}"))
        self._keep(worker)

    def _populate_backups(self, items: list):
        self._items = items
        self._table.setRowCount(0)
        for item in items:
            row = self._table.rowCount()
            self._table.insertRow(row)
            values = [
                item.get("filename", "?"),
                item.get("source", "server"),
                item.get("modified", "-"),
                _size_text(int(item.get("size_bytes", 0))),
                "Haz\u0131r",
                item.get("product_code", "teknik_servis"),
                item.get("hardware_id") or "-",
            ]
            for column, value in enumerate(values):
                self._table.setItem(row, column, QTableWidgetItem(str(value)))
        self._status.setText(
            f"{len(items)} yedek bulundu." if items else "Bu firma i\u00e7in yedek bulunamad\u0131."
        )

    def _selected(self) -> dict | None:
        row = self._table.currentRow()
        if row < 0 or row >= len(self._items):
            self._status.setText("L\u00fctfen bir yedek se\u00e7in.")
            return None
        return self._items[row]

    def _download_selected(self):
        item = self._selected()
        tenant_id = self._company_combo.currentData()
        if not item or not tenant_id:
            return
        suggested = Path(str(item.get("filename") or "Firma.db")).name.replace(" (guncel)", "")
        target, _ = QFileDialog.getSaveFileName(
            self, "Yede\u011fi Kaydet", suggested, "SQLite Veritaban\u0131 (*.db);;T\u00fcm Dosyalar (*)"
        )
        if not target:
            return
        self._status.setText("Yedek indiriliyor...")
        worker = _DownloadBackup(str(tenant_id), item, target)
        worker.done.connect(lambda path: self._status.setText(f"Yedek kaydedildi: {path}"))
        worker.error.connect(lambda error: self._status.setText(f"Hata: {error}"))
        self._keep(worker)

    def _restore_selected(self):
        item = self._selected()
        tenant_id = self._company_combo.currentData()
        if not item or not tenant_id:
            return
        company = self._company_combo.currentText()
        answer = QMessageBox.warning(
            self,
            "Geri Y\u00fckleme Onay\u0131",
            f"{company} i\u00e7in '{item.get('filename', '?')}' yede\u011fi geri y\u00fckleme "
            "kuyru\u011funa al\u0131ns\u0131n m\u0131? Masa\u00fcst\u00fc uygulamas\u0131 mevcut verinin "
            "g\u00fcvenlik kopyas\u0131n\u0131 ald\u0131ktan sonra komutu uygular.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._status.setText("Geri y\u00fckleme komutu g\u00f6nderiliyor...")
        worker = _RestoreBackup(str(tenant_id), item)
        worker.done.connect(self._restore_done)
        worker.error.connect(lambda error: self._status.setText(f"Hata: {error}"))
        self._keep(worker)

    def _restore_done(self, result: dict):
        command_id = result.get("command_id")
        suffix = f" Komut No: {command_id}" if command_id else ""
        self._status.setText(f"\u2713 Geri y\u00fckleme kuyru\u011fa al\u0131nd\u0131.{suffix}")
