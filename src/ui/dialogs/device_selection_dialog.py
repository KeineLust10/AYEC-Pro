# -*- coding: utf-8 -*-

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QHeaderView,
)

from src.ui.widgets.premium_dialog import PremiumDialog
from src.utils.status_utils import is_active_device_status
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import show_warning


class DeviceSelectionDialog(PremiumDialog):
    def __init__(self, db, parent=None):
        super().__init__("Islem Yapilacak Cihazi Secin", parent)
        self.db = db
        self.selected_device = None
        self.resize(1100, 700)
        self.setup_ui()
        self.apply_theme_styles()

    def setup_ui(self):
        layout = self.body_layout

        self.lbl_subtitle = QLabel(
            "Teknisyen paneline giris yapmak icin listeden bir cihaza cift tiklayin veya birini secip ilerleyin."
        )
        layout.addWidget(self.lbl_subtitle)

        self.search_container = QFrame()
        search_layout = QHBoxLayout(self.search_container)
        search_layout.setContentsMargins(15, 0, 15, 0)

        self.lbl_search_icon = QLabel("Ara")
        search_layout.addWidget(self.lbl_search_icon)

        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("Takip No, Musteri Adi veya Seri No ile hizli arama...")
        self.inp_search.setFixedHeight(45)
        self.inp_search.textChanged.connect(self.search)
        search_layout.addWidget(self.inp_search)
        layout.addWidget(self.search_container)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["TAKIP NO", "MUSTERI", "CIHAZ BILGISI", "DURUM", "GIRIS TARIHI"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.doubleClicked.connect(self.select_and_close)
        self.table.verticalHeader().setDefaultSectionSize(60)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Vazgec")
        self.btn_cancel.setFixedSize(140, 48)
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_select = QPushButton("Secimi Onayla ve Ilerle")
        self.btn_select.setFixedSize(220, 48)
        self.btn_select.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select.clicked.connect(self.select_and_close)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_select)
        layout.addLayout(btn_layout)

        QTimer.singleShot(50, self.load_data)

    def apply_theme_styles(self):
        self.lbl_subtitle.setStyleSheet(theme_qss("color: @text_muted; font-size: 14px;"))
        self.search_container.setStyleSheet(
            theme_qss(
                """
                QFrame {
                    background-color: @surface_alt;
                    border-radius: 12px;
                    border: 1px solid @border;
                }
                """
            )
        )
        self.lbl_search_icon.setStyleSheet(
            theme_qss("color: @text_muted; font-size: 13px; font-weight: 700;")
        )
        self.inp_search.setStyleSheet(
            theme_qss(
                """
                QLineEdit {
                    border: none;
                    background: transparent;
                    font-size: 14px;
                    color: @text;
                }
                """
            )
        )
        self.table.setStyleSheet(
            theme_qss(
                """
                QTableWidget {
                    border: 1px solid @border;
                    border-radius: 12px;
                    background-color: @surface;
                    gridline-color: transparent;
                    alternate-background-color: @surface_alt;
                    font-size: 13px;
                    color: @text;
                    outline: 0;
                }
                QTableWidget::item {
                    padding: 12px;
                    border-bottom: 1px solid @border;
                }
                QTableWidget::item:selected {
                    background-color: @selection_bg;
                    color: @selection_text;
                    font-weight: bold;
                    border: none;
                }
                QHeaderView::section {
                    background-color: @surface_alt;
                    padding: 12px;
                    border: none;
                    font-weight: 800;
                    color: @text_muted;
                    text-align: left;
                    font-size: 11px;
                }
                """
            )
        )
        self.btn_cancel.setStyleSheet(
            theme_qss(
                """
                QPushButton {
                    background-color: @surface;
                    color: @text_muted;
                    border: 1px solid @border;
                    border-radius: 12px;
                    font-weight: 700;
                }
                QPushButton:hover {
                    background-color: @surface_alt;
                    color: @text;
                }
                """
            )
        )
        self.btn_select.setStyleSheet(
            theme_qss(
                """
                QPushButton {
                    background-color: @accent;
                    color: @selection_text;
                    border-radius: 12px;
                    font-weight: 800;
                    border: none;
                }
                QPushButton:hover {
                    background-color: @accent_hover;
                }
                """
            )
        )

    def refresh_theme(self):
        self.apply_theme_styles()

    def _get_active_devices(self, query=""):
        query = str(query or "").strip()
        cols = set()
        try:
            if hasattr(self.db, "_get_table_columns"):
                cols = set(self.db._get_table_columns("devices"))
        except Exception:
            cols = set()

        where_clauses = ["1=1"]
        params = []
        if "is_deleted" in cols:
            where_clauses.append("COALESCE(is_deleted, 0)=0")
        if "is_archived" in cols:
            where_clauses.append("(is_archived = 0 OR is_archived IS NULL)")
        if query:
            where_clauses.append("(tracking_no LIKE ? OR customer_name LIKE ? OR serial_no LIKE ?)")
            like_q = f"%{query}%"
            params.extend([like_q, like_q, like_q])

        select_cols = (
            "id, tracking_no, customer_name, device_brand, device_model, "
            "serial_no, status, entry_date"
        )
        sql = (
            f"SELECT {select_cols} FROM devices WHERE "
            + " AND ".join(where_clauses)
            + " ORDER BY id DESC LIMIT 1000"
        )
        try:
            self.db.cursor.execute(sql, params)
            rows = self.db.cursor.fetchall() or []
            return [
                row
                for row in rows
                if is_active_device_status(self._row_value(row, "status", 6))
            ]
        except Exception:
            try:
                all_devices = self.db.get_all_devices() or []
            except Exception:
                all_devices = []
            filtered = []
            for d in all_devices:
                try:
                    is_deleted = False
                    if hasattr(d, "keys") and "is_deleted" in d.keys():
                        is_deleted = bool(d["is_deleted"])
                    elif isinstance(d, dict):
                        is_deleted = bool(d.get("is_deleted"))
                    if is_deleted:
                        continue
                    if len(d) > 8 and is_active_device_status(d[8]):
                        filtered.append(d)
                except Exception:
                    continue
            if query:
                q = query.lower()
                filtered = [d for d in filtered if q in f"{d[1]} {d[2]} {d[5]}".lower()]
            return filtered

    @staticmethod
    def _row_value(row, key, index, default=""):
        try:
            if hasattr(row, "keys") and key in row.keys():
                return row[key]
        except Exception:
            pass
        if isinstance(row, dict):
            return row.get(key, default)
        try:
            return row[index]
        except Exception:
            return default

    def load_data(self, devices=None):
        if devices is None:
            devices = self._get_active_devices()
        if devices is None:
            devices = []

        self.table.setRowCount(0)
        for i, d in enumerate(devices):
            self.table.insertRow(i)
            tracking = str(self._row_value(d, "tracking_no", 1))
            customer = str(self._row_value(d, "customer_name", 2))
            device = (
                f"{self._row_value(d, 'device_brand', 3)} "
                f"{self._row_value(d, 'device_model', 4)}"
            ).strip()
            status = str(self._row_value(d, "status", 6))
            entry_date = str(self._row_value(d, "entry_date", 7))

            self.table.setItem(i, 0, QTableWidgetItem(tracking))
            self.table.setItem(i, 1, QTableWidgetItem(customer))
            self.table.setItem(i, 2, QTableWidgetItem(device))
            self.table.setItem(i, 3, QTableWidgetItem(status))
            self.table.setItem(i, 4, QTableWidgetItem(entry_date))
            self.table.item(i, 0).setData(Qt.ItemDataRole.UserRole, d)

    def search(self):
        query = self.inp_search.text().lower()
        if not query:
            self.load_data()
            return
        self.load_data(self._get_active_devices(query))

    def select_and_close(self):
        row = self.table.currentRow()
        if row < 0:
            selected_indexes = self.table.selectionModel().selectedRows()
            if selected_indexes:
                row = selected_indexes[0].row()
        if row >= 0:
            selected = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            tracking_no = self.table.item(row, 0).text() if self.table.item(row, 0) else ""
            if tracking_no and hasattr(self.db, "get_device_by_tracking_no"):
                try:
                    self.selected_device = self.db.get_device_by_tracking_no(tracking_no) or selected
                except Exception:
                    self.selected_device = selected
            else:
                self.selected_device = selected
            self.accept()
        else:
            show_warning(self, "Lutfen listeden bir cihaz seciniz.")
