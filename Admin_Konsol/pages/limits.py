"""
AYEC Pro Admin Konsol - Kota & Limit Y\u00f6netimi Sayfas\u0131
Firmalar\u0131n veritaban\u0131 limitleri, cihaz kotalar\u0131 ve kullan\u0131m seviyeleri.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor
import api_client


class _FetchLimits(QThread):
    done = pyqtSignal(list)
    error = pyqtSignal(str)

    def run(self):
        try:
            # Sunucu limit verilerini listele
            import requests
            import config
            h = {"Content-Type": "application/json"}
            if api_client._session_token:
                h["Cookie"] = f"ayec_session={api_client._session_token}"
            resp = requests.get(
                config.server_url() + "/api/admin/licenses/usage",
                headers=h,
                timeout=config.timeout()
            )
            if not resp.ok:
                raise RuntimeError(resp.json().get("error") or "Kullanim verisi alinamadi")
            self.done.emit(resp.json().get("usages", []))
        except Exception as exc:
            self.error.emit(str(exc))


class LimitsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._thread = None
        self._build_ui()
        self._load()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(20)

        title_row = QHBoxLayout()
        title = QLabel("\ud83d\udcca Kota & Limit Kontrolu (SaaS)")
        title.setObjectName("pageTitle")
        title_row.addWidget(title)
        title_row.addStretch()
        refresh = QPushButton("\u21bb Yenile")
        refresh.setObjectName("secondaryBtn")
        refresh.clicked.connect(self._load)
        title_row.addWidget(refresh)
        root.addLayout(title_row)

        self._table = QTableWidget()
        self._table.setObjectName("dataTable")
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels([
            "Firma", "DB Boyutu (MB)", "Kullanici Sayisi", "Kayitli Cihaz", "Servis Formu", "Durum"
        ])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        root.addWidget(self._table, 1)

        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("statusLabel")
        root.addWidget(self._status_lbl)

    def _load(self):
        t = _FetchLimits()
        t.done.connect(self._populate)
        t.error.connect(lambda e: self._status_lbl.setText(f"Hata: {e}"))
        t.start()
        self._thread = t

    def _populate(self, usages: list):
        self._status_lbl.setText("")
        self._table.setRowCount(0)
        for u in usages:
            row = self._table.rowCount()
            self._table.insertRow(row)
            
            db_size = f"{u.get('db_size_mb', 0):.2f} MB"
            users = f"{u.get('users_count', 0)} / {u.get('users_limit', 10)}"
            devices = f"{u.get('devices_count', 0)} / {u.get('devices_limit', 100)}"
            services = f"{u.get('services_count', 0)} / {u.get('services_limit', 1000)}"
            
            status = "Normal"
            color = "#10b981"
            if u.get("db_size_mb", 0) > 100 or u.get("devices_count", 0) >= u.get("devices_limit", 100):
                status = "Limit Asimi/Kritik"
                color = "#f87171"
                
            items = [
                u.get("company_name", "?"),
                db_size,
                users,
                devices,
                services,
                status
            ]
            
            for col, val in enumerate(items):
                item = QTableWidgetItem(str(val))
                if col == 5:
                    item.setForeground(QColor(color))
                self._table.setItem(row, col, item)
