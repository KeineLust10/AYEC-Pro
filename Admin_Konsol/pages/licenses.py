"""
AYEC Pro Admin Konsol - Lisans Yonetimi
"""
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QDateTimeEdit, QMessageBox, QFrame, QGridLayout, QLineEdit, QDialog,
    QFormLayout, QTextEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QDateTime
from PyQt6.QtGui import QColor

import api_client
from product_catalog import product_code


class _FetchLicenses(QThread):
    done = pyqtSignal(list)
    error = pyqtSignal(str)

    def run(self):
        try:
            self.done.emit(api_client.licenses(getattr(self, 'product_code', '')))
        except Exception as exc:
            self.error.emit(str(exc))


class _UpdateLicense(QThread):
    done = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, tenant_id: str, data: dict):
        super().__init__()
        self._tid = tenant_id
        self._data = data

    def run(self):
        try:
            self.done.emit(api_client.update_license(self._tid, self._data))
        except Exception as exc:
            self.error.emit(str(exc))


class LicensesPage(QWidget):
    def __init__(self):
        super().__init__()
        self._licenses: list[dict] = []
        self._threads = set()
        self._build_ui()
        self._load()

    def set_product_filter(self, product_name: str):
        self.product_code = product_code(product_name)
        self._load()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(18)

        title_row = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(3)
        title = QLabel("\ud83c\udf9f\ufe0f Lisans Yonetimi")
        title.setObjectName("pageTitle")
        title_col.addWidget(title)
        subtitle = QLabel("Lisans durumlarini, tarihlerini ve aktivasyon islemlerini tek ekrandan yonetin.")
        subtitle.setObjectName("pageSubtitle")
        title_col.addWidget(subtitle)
        title_row.addLayout(title_col)
        title_row.addStretch()
        refresh = QPushButton("\u21bb Yenile")
        refresh.setObjectName("secondaryBtn")
        refresh.clicked.connect(self._load)
        title_row.addWidget(refresh)
        root.addLayout(title_row)

        self._metric_values = {}
        metrics = QHBoxLayout()
        metrics.setSpacing(12)
        for key, label, detail in (
            ("total", "Toplam Lisans", "Kayitli firma lisanslari"),
            ("active", "Aktif", "Su anda kullanilabilir"),
            ("attention", "Kontrol Gereken", "Demo veya pasif lisanslar"),
        ):
            card = QFrame()
            card.setObjectName("metricCard")
            card_lay = QVBoxLayout(card)
            card_lay.setContentsMargins(16, 12, 16, 12)
            card_lay.setSpacing(3)
            card_title = QLabel(label)
            card_title.setObjectName("metricTitle")
            card_lay.addWidget(card_title)
            value = QLabel("0")
            value.setObjectName("metricValue")
            card_lay.addWidget(value)
            card_detail = QLabel(detail)
            card_detail.setObjectName("metricSub")
            card_lay.addWidget(card_detail)
            metrics.addWidget(card, 1)
            self._metric_values[key] = value
        root.addLayout(metrics)

        table_card = QFrame()
        table_card.setObjectName("tableCard")
        table_card_lay = QVBoxLayout(table_card)
        table_card_lay.setContentsMargins(0, 0, 0, 0)
        table_card_lay.setSpacing(0)

        table_toolbar = QFrame()
        table_toolbar.setObjectName("tableToolbar")
        table_toolbar_lay = QHBoxLayout(table_toolbar)
        table_toolbar_lay.setContentsMargins(18, 14, 18, 14)
        table_heading_col = QVBoxLayout()
        table_heading_col.setSpacing(2)
        table_heading = QLabel("Kayitli Lisanslar")
        table_heading.setObjectName("panelTitle")
        table_heading_col.addWidget(table_heading)
        table_hint = QLabel("Bir firmaya tiklayarak lisans ayrintilarini ve islemleri acin.")
        table_hint.setObjectName("metricSub")
        table_heading_col.addWidget(table_hint)
        table_toolbar_lay.addLayout(table_heading_col)
        table_toolbar_lay.addStretch()
        self._search_input = QLineEdit()
        self._search_input.setObjectName("searchInput")
        self._search_input.setPlaceholderText("Firma, lisans veya durum ara...")
        self._search_input.setMinimumWidth(270)
        self._search_input.textChanged.connect(self._filter_table)
        table_toolbar_lay.addWidget(self._search_input)
        table_card_lay.addWidget(table_toolbar)

        self._table = QTableWidget()
        self._table.setObjectName("dataTable")
        self._table.setColumnCount(9)
        self._table.setHorizontalHeaderLabels([
            "Firma", "Lisans Turu", "Lisans Kodu", "Baslangic", "Bitis", "Durum",
            "Son Islem", "Islemler", "ID",
        ])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setAlternatingRowColors(True)
        self._table.setShowGrid(False)
        self._table.setWordWrap(False)
        self._table.setMinimumHeight(330)
        self._table.verticalHeader().setDefaultSectionSize(48)
        self._table.verticalHeader().setVisible(False)
        self._table.setColumnHidden(8, True)
        self._table.itemSelectionChanged.connect(self._selection_changed)
        self._table.itemDoubleClicked.connect(self._show_license_details)
        table_card_lay.addWidget(self._table, 1)
        root.addWidget(table_card, 1)

        # Alt kontroller
        ctrl = QFrame()
        ctrl.setObjectName("ctrlFrame")
        ctrl_lay = QGridLayout(ctrl)
        ctrl_lay.setContentsMargins(16, 14, 16, 14)
        ctrl_lay.setHorizontalSpacing(12)
        ctrl_lay.setVerticalSpacing(10)

        editor_heading = QLabel("Secili Firma Lisans Islemleri")
        editor_heading.setObjectName("panelTitle")
        ctrl_lay.addWidget(editor_heading, 0, 0, 1, 3)
        self._selection_info = QLabel("Islem yapmak icin tablodan bir firma secin.")
        self._selection_info.setObjectName("selectionInfo")
        ctrl_lay.addWidget(self._selection_info, 0, 3, 1, 3)

        ctrl_lay.addWidget(QLabel("Lisans Turu"), 1, 0)
        self._type_combo = QComboBox()
        self._type_combo.addItems(["Demo", "Standart", "Premium", "Suresiz"])
        self._type_combo.setObjectName("combo")
        self._type_combo.currentTextChanged.connect(self._license_type_changed)
        ctrl_lay.addWidget(self._type_combo, 1, 1)

        ctrl_lay.addWidget(QLabel("Baslangic Tarih / Saat"), 1, 2)
        self._start_date = QDateTimeEdit()
        self._start_date.setObjectName("dateEdit")
        self._start_date.setCalendarPopup(True)
        self._start_date.setDisplayFormat("dd.MM.yyyy HH:mm:ss")
        self._start_date.setDateTime(QDateTime.currentDateTime())
        ctrl_lay.addWidget(self._start_date, 1, 3)

        ctrl_lay.addWidget(QLabel("Bitis Tarih / Saat"), 1, 4)
        self._end_date = QDateTimeEdit()
        self._end_date.setObjectName("dateEdit")
        self._end_date.setCalendarPopup(True)
        self._end_date.setDisplayFormat("dd.MM.yyyy HH:mm:ss")
        self._end_date.setDateTime(QDateTime.currentDateTime().addYears(1))
        ctrl_lay.addWidget(self._end_date, 1, 5)

        self._activate_btn = QPushButton("Aktif Et ve Masaustune Gonder")
        self._activate_btn.setObjectName("primaryBtn")
        self._activate_btn.setEnabled(False)
        self._activate_btn.clicked.connect(self._update_selected)
        ctrl_lay.addWidget(self._activate_btn, 2, 3, 1, 2)

        self._cancel_btn = QPushButton("Lisansi Pasif Et ve Bildir")
        self._cancel_btn.setObjectName("dangerBtn")
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.clicked.connect(lambda: self._quick_action("Pasif"))
        ctrl_lay.addWidget(self._cancel_btn, 2, 5)

        root.addWidget(ctrl)

        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("statusLabel")
        root.addWidget(self._status_lbl)

    def _load(self):
        t = _FetchLicenses()
        t.done.connect(self._populate)
        t.error.connect(lambda e: self._status_lbl.setText(f"Hata: {e}"))
        self._keep_thread(t)
        t.start()

    def _keep_thread(self, thread):
        self._threads.add(thread)
        thread.finished.connect(
            lambda current=thread: self._threads.discard(current)
        )

    def _populate(self, data: list):
        self._licenses = data
        active_count = sum(
            1 for item in data if str(item.get("status") or "").casefold() == "aktif"
        )
        self._metric_values["total"].setText(str(len(data)))
        self._metric_values["active"].setText(str(active_count))
        self._metric_values["attention"].setText(str(max(0, len(data) - active_count)))
        self._table.setRowCount(0)
        for lic in data:
            row = self._table.rowCount()
            self._table.insertRow(row)
            status = lic.get("status", "Aktif")
            color = {"Aktif": "#10b981", "Pasif": "#f87171", "Demo": "#f59e0b"}.get(status, "#9ca3af")
            items = [
                lic.get("company_name", "?"),
                lic.get("license_type", "-"),
                lic.get("license_code", "-") or "-",
                self._display_datetime(lic.get("license_start")),
                (
                    "Suresiz" if not str(lic.get("license_end") or "").strip()
                    else self._display_datetime(lic.get("license_end"))
                ),
                status,
                self._display_datetime(lic.get("license_updated_at")),
                "\u2022\u2022\u2022",
                lic.get("tenant_id", ""),
            ]
            for col, val in enumerate(items):
                item = QTableWidgetItem(str(val))
                if col == 5:
                    item.setForeground(QColor(color))
                self._table.setItem(row, col, item)
        self._table.clearSelection()
        self._table.setCurrentItem(None)
        self._activate_btn.setEnabled(False)
        self._cancel_btn.setEnabled(False)
        self._selection_info.setText("Islem yapmak icin tablodan bir firma secin.")
        self._filter_table(self._search_input.text())

    def _filter_table(self, text: str):
        query = str(text or "").strip().casefold()
        for row in range(self._table.rowCount()):
            searchable = " ".join(
                self._table.item(row, column).text()
                for column in range(self._table.columnCount())
                if self._table.item(row, column) is not None
            ).casefold()
            self._table.setRowHidden(row, bool(query and query not in searchable))

    def _selected_tenant_id(self) -> str | None:
        row = self._table.currentRow()
        if row < 0:
            return None
        return self._table.item(row, 8).text()

    @staticmethod
    def _parse_server_datetime(value):
        text = str(value or "").strip().replace("Z", "")
        for pattern in (Qt.DateFormat.ISODate,):
            parsed = QDateTime.fromString(text, pattern)
            if parsed.isValid():
                return parsed
        parsed = QDateTime.fromString(text, "yyyy-MM-dd HH:mm:ss")
        return parsed if parsed.isValid() else QDateTime()

    @classmethod
    def _display_datetime(cls, value):
        parsed = cls._parse_server_datetime(value)
        if parsed.isValid():
            return parsed.toString("dd.MM.yyyy HH:mm:ss")
        return "-"

    def _selection_changed(self):
        row = self._table.currentRow()
        if row < 0:
            return
        tenant_id = self._table.item(row, 8).text()
        license_data = next(
            (item for item in self._licenses if str(item.get("tenant_id")) == tenant_id),
            {},
        )
        type_text = str(license_data.get("license_type") or "Standart")
        index = self._type_combo.findText(type_text)
        if index >= 0:
            self._type_combo.setCurrentIndex(index)
        start = self._parse_server_datetime(license_data.get("license_start"))
        end = self._parse_server_datetime(license_data.get("license_end"))
        self._start_date.setDateTime(start if start.isValid() else QDateTime.currentDateTime())
        if end.isValid():
            self._end_date.setDateTime(end)
        self._selection_info.setText(
            f"Secili firma: {license_data.get('company_name') or '-'} | "
            f"Durum: {license_data.get('status') or '-'}"
        )
        self._activate_btn.setEnabled(True)
        self._cancel_btn.setEnabled(True)
        self._license_type_changed(self._type_combo.currentText())

    def _show_license_details(self, item):
        row = item.row()
        if row < 0 or row >= self._table.rowCount():
            return
        tenant_id = self._table.item(row, 8).text()
        license_data = next(
            (entry for entry in self._licenses if str(entry.get("tenant_id")) == tenant_id),
            {},
        )
        dialog = QDialog(self)
        dialog.setWindowTitle("Firma ve Lisans Ayrintilari")
        dialog.setMinimumWidth(560)
        layout = QVBoxLayout(dialog)
        title = QLabel(str(license_data.get("company_name") or "Firma"))
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        form = QFormLayout()
        form.setVerticalSpacing(10)
        fields = (
            ("Firma", "company_name"), ("Firma Kimligi", "tenant_id"),
            ("Lisans Turu", "license_type"), ("Lisans Kodu", "license_code"),
            ("Durum", "status"), ("Baslangic", "license_start"),
            ("Bitis", "license_end"), ("Son Islem", "license_updated_at"),
            ("Yetkili", "contact_name"), ("E-posta", "email"),
            ("Telefon", "phone"), ("Adres", "company_address"),
            ("Enlem", "installation_lat"), ("Boylam", "installation_lng"),
        )
        for label, key in fields:
            value = license_data.get(key)
            if key in {"license_start", "license_end", "license_updated_at"}:
                value = "Suresiz" if key == "license_end" and not value else self._display_datetime(value)
            value = str(value or "-")
            if key == "license_code":
                code_row = QHBoxLayout()
                field = QLineEdit(value)
                field.setReadOnly(True)
                copy_button = QPushButton("Kodu Kopyala")
                copy_button.clicked.connect(
                    lambda _checked=False, code=value, button=copy_button: (
                        QApplication.clipboard().setText(code),
                        button.setText("Kopyalandi"),
                    )
                )
                code_row.addWidget(field, 1)
                code_row.addWidget(copy_button)
                form.addRow(QLabel(label + ":"), code_row)
                continue
            field = QTextEdit()
            field.setReadOnly(True)
            field.setPlainText(value)
            field.setMaximumHeight(42 if key != "company_address" else 64)
            form.addRow(QLabel(label + ":"), field)
        layout.addLayout(form)
        close_button = QPushButton("Kapat")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        dialog.exec()

    def _license_type_changed(self, license_type):
        lifetime = str(license_type or "").casefold() == "suresiz"
        self._end_date.setEnabled(not lifetime)

    def _update_selected(self):
        tid = self._selected_tenant_id()
        if not tid:
            self._status_lbl.setText("Lutfen bir firma secin.")
            return
        data = {
            "license_type": self._type_combo.currentText(),
            "license_start": self._start_date.dateTime().toString("yyyy-MM-ddTHH:mm:ss"),
            "license_end": (
                "" if self._type_combo.currentText() == "Suresiz"
                else self._end_date.dateTime().toString("yyyy-MM-ddTHH:mm:ss")
            ),
            "status": "Aktif",
        }
        if data["license_end"] and self._end_date.dateTime() <= self._start_date.dateTime():
            self._status_lbl.setText("Bitis tarih ve saati baslangictan sonra olmalidir.")
            return
        t = _UpdateLicense(tid, data)
        t.done.connect(
            lambda _: (
                self._status_lbl.setText(
                    "Lisans kaydedildi. Masaustu bildirimi yayinlandi; cevrimdisi cihaz "
                    "ilk senkronizasyonda lisansi alir."
                ),
                self._load(),
            )
        )
        t.error.connect(lambda e: self._status_lbl.setText(f"Hata: {e}"))
        self._keep_thread(t)
        t.start()

    def _quick_action(self, action: str):
        tid = self._selected_tenant_id()
        if not tid:
            self._status_lbl.setText("Lutfen bir firma secin.")
            return
        reply = QMessageBox.question(self, "Onay", f"Lisansi '{action}' olarak isaretle?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        t = _UpdateLicense(tid, {"status": action})
        t.done.connect(lambda _: (self._status_lbl.setText(f"\u2705 Isaret: {action}"), self._load()))
        t.error.connect(lambda e: self._status_lbl.setText(f"Hata: {e}"))
        self._keep_thread(t)
        t.start()
