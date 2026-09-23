"""AYEC Pro Admin Console - isolated customer support overview."""

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
)

import api_client


class _Customer360Thread(QThread):
    loaded = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, tenant_id: str):
        super().__init__()
        self._tenant_id = tenant_id

    def run(self):
        try:
            self.loaded.emit(api_client.customer_360(self._tenant_id))
        except Exception as exc:
            self.failed.emit(str(exc))


class Customer360Page(QWidget):
    """Single-firm support view backed by the central Admin API."""

    def __init__(self):
        super().__init__()
        self._companies = []
        self._payload = {}
        self._thread = None
        self._build_ui()
        self._load_companies()

    def set_product_filter(self, _product_name: str):
        self._load_companies()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(14)

        title = QLabel("M\u00fc\u015fteri 360")
        title.setObjectName("pageTitle")
        root.addWidget(title)
        subtitle = QLabel(
            "Firma, lisans, yedek, hata ve canl\u0131 durumunu tek destek ekran\u0131nda g\u00f6r\u00fcnt\u00fcleyin."
        )
        subtitle.setObjectName("pageSubtitle")
        root.addWidget(subtitle)

        picker_row = QHBoxLayout()
        picker_row.addWidget(QLabel("Firma:"))
        self._company_combo = QComboBox()
        self._company_combo.setObjectName("fieldInput")
        self._company_combo.currentIndexChanged.connect(self._company_changed)
        picker_row.addWidget(self._company_combo, 1)
        refresh = QPushButton("Yenile")
        refresh.setObjectName("secondaryBtn")
        refresh.clicked.connect(self._refresh)
        picker_row.addWidget(refresh)
        root.addLayout(picker_row)

        cards = QHBoxLayout()
        self._cards = {}
        for key, label in (
            ("user_count", "Kullan\u0131c\u0131"),
            ("backup_count", "Yedek"),
            ("error_count", "Hata"),
            ("online", "Canl\u0131"),
        ):
            frame = QFrame()
            frame.setObjectName("metricCard")
            lay = QVBoxLayout(frame)
            value = QLabel("-")
            value.setObjectName("metricValue")
            caption = QLabel(label)
            caption.setObjectName("metricTitle")
            lay.addWidget(value)
            lay.addWidget(caption)
            cards.addWidget(frame)
            self._cards[key] = value
        root.addLayout(cards)

        self._company_label = QLabel("Firma se\u00e7in")
        self._company_label.setObjectName("panelTitle")
        root.addWidget(self._company_label)

        self._table = QTableWidget(0, 3)
        self._table.setObjectName("dataTable")
        self._table.setHorizontalHeaderLabels(["Alan", "De\u011fer", "Kaynak"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setMinimumHeight(260)
        root.addWidget(self._table, 1)

        self._status = QLabel("")
        self._status.setObjectName("statusLabel")
        root.addWidget(self._status)

    def _load_companies(self):
        try:
            self._companies = api_client.companies()
        except Exception as exc:
            self._status.setText(f"Hata: {exc}")
            return
        current = self._company_combo.currentData()
        self._company_combo.blockSignals(True)
        self._company_combo.clear()
        for company in self._companies:
            self._company_combo.addItem(
                str(company.get("company_name") or "?") + "  [" + str(company.get("id") or "") + "]",
                company.get("id"),
            )
        self._company_combo.blockSignals(False)
        if current:
            index = self._company_combo.findData(current)
            if index >= 0:
                self._company_combo.setCurrentIndex(index)
        if self._company_combo.count():
            self._company_changed(self._company_combo.currentIndex())

    def _company_changed(self, _index: int):
        tenant_id = str(self._company_combo.currentData() or "")
        if tenant_id:
            self._load_customer(tenant_id)

    def _load_customer(self, tenant_id: str):
        self._status.setText("Merkezi destek verileri al\u0131n\u0131yor...")
        self._thread = _Customer360Thread(tenant_id)
        self._thread.loaded.connect(self._show_customer)
        self._thread.failed.connect(lambda error: self._status.setText(f"Hata: {error}"))
        self._thread.start()

    def _show_customer(self, payload: dict):
        self._payload = payload
        company = payload.get("company") or {}
        summary = payload.get("summary") or {}
        self._company_label.setText(str(company.get("company_name") or "Firma"))
        for key, value in summary.items():
            if key in self._cards:
                self._cards[key].setText("Evet" if key == "online" and value else "Hay\u0131r" if key == "online" else str(value))
        rows = [
            ("Firma kimli\u011fi", company.get("id"), "tenants"),
            ("\u00dcr\u00fcn", company.get("product_code"), "tenants"),
            ("E-posta", company.get("email"), "tenants"),
            ("Telefon", company.get("phone"), "tenants"),
            ("Adres", company.get("company_address"), "tenants"),
            ("Lisans biti\u015fi", company.get("license_end"), "tenants"),
            ("Son hata", (payload.get("error_logs") or [{}])[0].get("message"), "error_logs"),
            ("Son audit", (payload.get("audit_logs") or [{}])[0].get("event_type"), "audit_logs"),
        ]
        self._table.setRowCount(len(rows))
        for row, values in enumerate(rows):
            for column, value in enumerate(values):
                self._table.setItem(row, column, QTableWidgetItem(str(value or "-")))
        self._status.setText("Merkezi veriler g\u00fcncel.")

    def _refresh(self):
        tenant_id = str(self._company_combo.currentData() or "")
        if tenant_id:
            self._load_customer(tenant_id)
        else:
            QMessageBox.information(self, "Bilgi", "\u00d6nce bir firma se\u00e7in.")
