# -*- coding: utf-8 -*-
"""
ServiceListPage - Dedicated Service List and Management Screen
Matches Resim 2 design: search & filter bar, quick status chips,
multi-line data table, pagination, print actions, and export.
"""

from __future__ import annotations

import os
import html
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import QEvent, Qt, QTimer, QSize, pyqtSignal
from PyQt6.QtGui import QColor, QCursor, QFont, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.ui.pages._dashboard_utils import render_svg_icon
from src.ui.pages.dashboard_actions_mixin import DashboardActionsMixin
from src.utils.currency_helper import CurrencyHelper
from src.utils.design_system import DesignTokens
from src.utils.logger import logger
from src.utils.status_utils import is_active_device_status, normalize_device_status
from src.utils.theme_colors import tc, theme_qss


class ServiceListPage(DashboardActionsMixin, QWidget):
    """
    Dedicated Service List page matching Resim 2.
    Inherits all business logic (database queries, dialogs, printing, SMS/WhatsApp)
    from DashboardActionsMixin while presenting a standalone, ultra-clean UI.
    """

    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.current_filter_category = "all"
        self._current_search_query = ""
        self._current_status_filter = "all"
        self._current_date_filter = "all"

        # Pagination state
        self._current_page = 1
        self._page_size = 8
        self._all_records: List[Dict[str, Any]] = []
        self._filtered_records: List[Dict[str, Any]] = []

        # Chip button map
        self._chip_buttons: Dict[str, QPushButton] = {}

        self.init_ui()
        QTimer.singleShot(50, self.refresh_data)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.MouseButtonPress:
            row = watched.property("serviceRow") if hasattr(watched, "property") else None
            if row is not None:
                try:
                    self.table.selectRow(int(row))
                except (AttributeError, TypeError, ValueError):
                    pass
        return super().eventFilter(watched, event)

    def _install_row_selection(self, widget, row_idx):
        widget.setProperty("serviceRow", int(row_idx))
        widget.installEventFilter(self)
        return widget

    def init_ui(self):
        self.setObjectName("ServiceListPage")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(theme_qss("background-color: @surface_alt;"))

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(14)

        # 1. Top Header
        self._create_header(main_layout)

        # 2. Quick Filter Chips / Tabs
        self._create_filter_chips(main_layout)

        # 3. Search & Filter Bar
        self._create_filter_bar(main_layout)

        # 4. Action Toolbar
        self._create_action_bar(main_layout)

        # 5. Data Table Container
        self._create_table_widget(main_layout)

        # 6. Pagination Footer
        self._create_pagination_footer(main_layout)

    def _create_header(self, parent_layout: QVBoxLayout):
        header_widget = QWidget(self)
        header_widget.setStyleSheet("background: transparent; border: none;")
        h_layout = QHBoxLayout(header_widget)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(12)

        # Title & subtitle
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        self.lbl_title = QLabel("Servis Listesi")
        self.lbl_title.setStyleSheet(theme_qss(
            "font-size: 26px; font-weight: 900; color: @text; border: none;"
        ))

        self.lbl_subtitle = QLabel("T\u00fcm servis kay\u0131tlar\u0131n\u0131 tek ekrandan y\u00f6netin.")
        self.lbl_subtitle.setStyleSheet(theme_qss(
            "font-size: 13px; color: @text_muted; border: none;"
        ))

        title_box.addWidget(self.lbl_title)
        title_box.addWidget(self.lbl_subtitle)
        h_layout.addLayout(title_box)
        h_layout.addStretch()

        # Right Action Buttons: "+ Cihaz Ekle" and "Dışa Aktar"
        self.btn_add_device = QPushButton("+ Cihaz Ekle")
        self.btn_add_device.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_device.setFixedHeight(40)
        self.btn_add_device.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: #2563EB;
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 800;
                border: none;
                border-radius: 10px;
                padding: 0 18px;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
            QPushButton:pressed {
                background-color: #1E40AF;
            }
        """))
        self.btn_add_device.clicked.connect(self.open_service_form_shortcut)
        h_layout.addWidget(self.btn_add_device)

        self.btn_export = QPushButton("D\u0131\u015fa Aktar")
        self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export.setFixedHeight(40)
        self.btn_export.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @surface;
                color: @text;
                font-size: 13px;
                font-weight: 700;
                border: 1px solid @border;
                border-radius: 10px;
                padding: 0 16px;
            }
            QPushButton:hover {
                background-color: @hover_bg;
                border-color: @accent;
            }
        """))
        self.btn_export.clicked.connect(self.export_records)
        h_layout.addWidget(self.btn_export)

        parent_layout.addWidget(header_widget)

    def _create_filter_chips(self, parent_layout: QVBoxLayout):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(46)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        chip_container = QWidget()
        chip_container.setStyleSheet("background: transparent;")
        c_layout = QHBoxLayout(chip_container)
        c_layout.setContentsMargins(0, 2, 0, 2)
        c_layout.setSpacing(8)

        # Chip definitions: (key, title)
        chips_def = [
            ("all", "T\u00fcm Cihazlar"),
            ("today", "Randevulu"),
            ("pending_approval", "Onay Bekleyen"),
            ("cargo_waiting", "Kargosu Beklenen"),
            ("invoiced", "Faturas\u0131 Kesilen"),
            ("uninvoiced", "Faturas\u0131 Kesilmeyen"),
            ("external_out", "Onar\u0131ma Giden"),
            ("external_return", "Onar\u0131mdan Gelen"),
        ]

        for key, title in chips_def:
            btn = QPushButton(title)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(34)
            btn.setProperty("chipKey", key)
            btn.setStyleSheet(self._chip_style(False))
            btn.clicked.connect(lambda checked=False, k=key: self.set_filter_category(k))
            c_layout.addWidget(btn)
            self._chip_buttons[key] = btn

        c_layout.addStretch()
        scroll.setWidget(chip_container)
        parent_layout.addWidget(scroll)

    def _chip_style(self, active: bool = False) -> str:
        if active:
            return theme_qss("""
                QPushButton {
                    background-color: #2563EB;
                    color: #FFFFFF;
                    font-size: 12px;
                    font-weight: 800;
                    border: 1px solid #2563EB;
                    border-radius: 17px;
                    padding: 0 14px;
                }
            """)
        return theme_qss("""
            QPushButton {
                background-color: @surface;
                color: @text;
                font-size: 12px;
                font-weight: 700;
                border: 1px solid @border;
                border-radius: 17px;
                padding: 0 14px;
            }
            QPushButton:hover {
                background-color: @hover_bg;
                border-color: @accent;
            }
        """)

    def _create_filter_bar(self, parent_layout: QVBoxLayout):
        bar = QFrame(self)
        bar.setStyleSheet(theme_qss("""
            QFrame {
                background-color: @surface;
                border: 1px solid @border;
                border-radius: 12px;
            }
        """))
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        # Search box
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Takip no, m\u00fc\u015fteri veya cihaz ara...")
        self.search_input.setFixedHeight(36)
        self.search_input.setStyleSheet(theme_qss("""
            QLineEdit {
                background-color: @surface_alt;
                color: @text;
                font-size: 13px;
                border: 1px solid @border;
                border-radius: 8px;
                padding: 0 12px;
            }
            QLineEdit:focus {
                border: 1px solid @accent;
            }
        """))
        self.search_input.textChanged.connect(self._on_search_changed)
        layout.addWidget(self.search_input, 3)

        # Status dropdown
        self.combo_status = QComboBox()
        self.combo_status.setFixedHeight(36)
        self.combo_status.setStyleSheet(theme_qss("""
            QComboBox {
                background-color: @surface_alt;
                color: @text;
                font-size: 12px;
                font-weight: 700;
                border: 1px solid @border;
                border-radius: 8px;
                padding: 0 12px;
                min-width: 140px;
            }
            QComboBox::drop-down { border: none; }
        """))
        self.combo_status.addItem("Durum: T\u00fcm\u00fc", "all")
        self.combo_status.addItem("Bekliyor", "Bekliyor")
        self.combo_status.addItem("Tamirde", "Tamirde")
        self.combo_status.addItem("Par\u00e7a Bekliyor", "Par\u00e7a Bekliyor")
        self.combo_status.addItem("Test S\u00fcrecinde", "Test S\u00fcrecinde")
        self.combo_status.addItem("Teslim Edildi", "Teslim Edildi")
        self.combo_status.addItem("\u0130ptal / \u0130ade", "\u0130ptal")
        self.combo_status.currentIndexChanged.connect(self._on_combo_filter_changed)
        layout.addWidget(self.combo_status, 1)

        # Date range dropdown
        self.combo_date = QComboBox()
        self.combo_date.setFixedHeight(36)
        self.combo_date.setStyleSheet(theme_qss("""
            QComboBox {
                background-color: @surface_alt;
                color: @text;
                font-size: 12px;
                font-weight: 700;
                border: 1px solid @border;
                border-radius: 8px;
                padding: 0 12px;
                min-width: 140px;
            }
            QComboBox::drop-down { border: none; }
        """))
        self.combo_date.addItem("Tarih Aral\u0131\u011f\u0131: T\u00fcm\u00fc", "all")
        self.combo_date.addItem("Bug\u00fcn", "today")
        self.combo_date.addItem("Bu Hafta", "week")
        self.combo_date.addItem("Bu Ay", "month")
        self.combo_date.addItem("Son 30 G\u00fcn", "last_30")
        self.combo_date.addItem("Bu Y\u0131l", "year")
        self.combo_date.currentIndexChanged.connect(self._on_combo_filter_changed)
        layout.addWidget(self.combo_date, 1)

        # Filter button
        btn_filter = QPushButton("Filtrele")
        btn_filter.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_filter.setFixedHeight(36)
        btn_filter.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: #2563EB;
                color: #FFFFFF;
                font-weight: 800;
                font-size: 12px;
                border: none;
                border-radius: 8px;
                padding: 0 16px;
            }
            QPushButton:hover { background-color: #1D4ED8; }
        """))
        btn_filter.clicked.connect(self._apply_all_filters)
        layout.addWidget(btn_filter)

        # Clear button
        btn_clear = QPushButton("Temizle")
        btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear.setFixedHeight(36)
        btn_clear.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @surface_alt;
                color: @text;
                font-weight: 700;
                font-size: 12px;
                border: 1px solid @border;
                border-radius: 8px;
                padding: 0 14px;
            }
            QPushButton:hover { background-color: @hover_bg; }
        """))
        btn_clear.clicked.connect(self.clear_filters)
        layout.addWidget(btn_clear)

        parent_layout.addWidget(bar)

    def _create_action_bar(self, parent_layout: QVBoxLayout):
        bar = QWidget(self)
        bar.setStyleSheet("background: transparent; border: none;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        actions = [
            ("\U0001f552 Servis Ge\u00e7mi\u015fi", self._action_service_history),
            ("\U0001f5a8 Detayl\u0131 Fi\u015f Yazd\u0131r", self._action_print_detail),
            ("\U0001f4e6 Kargo Fi\u015fi Yazd\u0131r", self._action_print_cargo),
            ("\U0001f4c4 E-\u0130rsaliye", self._action_dispatch_note),
            ("\U0001f4b3 E-Fatura", self._action_e_invoice),
        ]

        for text, callback in actions:
            btn = QPushButton(text)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(32)
            btn.setStyleSheet(theme_qss("""
                QPushButton {
                    background-color: @surface;
                    color: @text;
                    font-size: 12px;
                    font-weight: 700;
                    border: 1px solid @border;
                    border-radius: 8px;
                    padding: 0 12px;
                }
                QPushButton:hover {
                    background-color: @hover_bg;
                    border-color: @accent;
                }
            """))
            btn.clicked.connect(callback)
            layout.addWidget(btn)

        layout.addStretch()
        parent_layout.addWidget(bar)

    def _create_table_widget(self, parent_layout: QVBoxLayout):
        wrapper = QFrame(self)
        wrapper.setObjectName("ServiceListTableWrapper")
        wrapper.setStyleSheet(theme_qss("""
            QFrame#ServiceListTableWrapper {
                background-color: @surface;
                border: 1px solid @border;
                border-radius: 10px;
            }
        """))
        wrap_layout = QVBoxLayout(wrapper)
        wrap_layout.setContentsMargins(0, 0, 0, 0)
        wrap_layout.setSpacing(0)

        self.table = QTableWidget(0, 10, wrapper)
        self.table.setObjectName("ServiceListTable")
        headers = [
            "",
            "TAK\u0130P NO",
            "M\u00dc\u015eTER\u0130",
            "C\u0130HAZ / MODEL",
            "KABUL TAR\u0130H\u0130",
            "TESL\u0130M TAR\u0130H\u0130",
            "\u00dcCRET",
            "DURUM",
            "AC\u0130L\u0130YET",
            "\u0130\u015eLEMLER",
        ]
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setAlternatingRowColors(False)
        self.table.setShowGrid(False)
        self.table.setWordWrap(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.open_context_menu)
        self.table.cellDoubleClicked.connect(self._on_table_double_clicked)

        # Header styling and resize modes
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 44)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 184)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 232)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 224)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 104)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 104)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(6, 92)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(7, 116)
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(8, 92)
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.Stretch)

        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(58)
        self.table.setWordWrap(False)
        self.table.setTextElideMode(Qt.TextElideMode.ElideRight)

        self.table.setStyleSheet(theme_qss("""
            QTableWidget#ServiceListTable {
                background-color: @surface;
                border: none;
                border-radius: 0px;
                gridline-color: transparent;
            }
            QTableWidget#ServiceListTable::item {
                padding: 6px 8px;
                background-color: @surface;
                border-bottom: 1px solid @border;
            }
            QTableWidget#ServiceListTable::item:alternate { background-color: @surface; }
            QTableWidget#ServiceListTable::item:selected {
                background-color: @hover_bg;
                color: @text;
            }
            QHeaderView::section {
                background-color: @surface_alt;
                color: @text_muted;
                font-size: 11px;
                font-weight: 800;
                border: none;
                border-bottom: 1px solid @border;
                padding: 10px 8px;
                letter-spacing: 0.5px;
            }
        """))

        wrap_layout.addWidget(self.table)
        parent_layout.addWidget(wrapper, 1)

    def _create_pagination_footer(self, parent_layout: QVBoxLayout):
        footer = QWidget(self)
        footer.setStyleSheet("background: transparent; border: none;")
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(12)

        self.lbl_page_info = QLabel("0 kay\u0131ttan 0-0 aras\u0131")
        self.lbl_page_info.setStyleSheet(theme_qss(
            "color: @text_muted; font-size: 12px; font-weight: 600;"
        ))
        layout.addWidget(self.lbl_page_info)
        layout.addStretch()

        # Page size
        self.combo_page_size = QComboBox()
        self.combo_page_size.setFixedHeight(30)
        self.combo_page_size.setStyleSheet(theme_qss("""
            QComboBox {
                background-color: @surface;
                color: @text;
                font-size: 11px;
                font-weight: 700;
                border: 1px solid @border;
                border-radius: 6px;
                padding: 0 8px;
            }
            QComboBox::drop-down { border: none; }
        """))
        for size in [8, 15, 25, 50, 100]:
            self.combo_page_size.addItem(f"{size} / sayfa", size)
        self.combo_page_size.currentIndexChanged.connect(self._on_page_size_changed)
        layout.addWidget(self.combo_page_size)

        # Pagination buttons container
        self.page_btn_container = QWidget()
        self.page_btn_container.setStyleSheet("background: transparent;")
        self.page_btn_layout = QHBoxLayout(self.page_btn_container)
        self.page_btn_layout.setContentsMargins(0, 0, 0, 0)
        self.page_btn_layout.setSpacing(4)
        layout.addWidget(self.page_btn_container)

        parent_layout.addWidget(footer)

    def set_filter_category(self, category: str):
        category_value = str(category or "all")
        self.current_filter_category = {
            "test": "test",
            "tamirde": "active",
            "bekliyor": "waiting",
            "kargo": "cargo_waiting",
            "parca": "part",
            "borclu": "debt",
        }.get(category_value, category_value)
        for key, btn in self._chip_buttons.items():
            is_active = (key == self.current_filter_category)
            btn.setStyleSheet(self._chip_style(is_active))
        self._apply_all_filters()

    def show_service_list(self, category="all"):
        """External entry point: set filter category and update UI immediately."""
        self.set_filter_category(category)

    def refresh_data(self):
        """Fetch records from database and refresh table."""
        self._fetch_records()
        self._update_chip_counts()
        self._apply_all_filters()

    def _fetch_records(self):
        if not self.db:
            return
        conn = getattr(self.db, "conn", None)
        read_cursor = conn.cursor() if conn is not None else self.db.cursor
        try:
            read_cursor.execute("PRAGMA table_info(devices)")
            cols = {row[1] for row in (read_cursor.fetchall() or []) if len(row) > 1}
        except Exception:
            cols = self._get_devices_columns()
        wanted = [
            "tracking_no", "customer_name", "customer_phone", "company_name",
            "device_type", "device_brand", "device_model", "fault_description",
            "entry_date", "exit_date", "estimated_date", "price", "labor_cost",
            "status", "urgency", "approval_status", "payment_status",
            "service_source", "delivery_type",
        ]
        selected = [c for c in wanted if c in cols]
        if not selected:
            self._all_records = []
            return

        where = []
        if "is_deleted" in cols:
            where.append("COALESCE(is_deleted, 0) = 0")
        if "is_archived" in cols:
            where.append("COALESCE(is_archived, 0) = 0")

        query = f"SELECT {', '.join(selected)} FROM devices"
        if where:
            query += " WHERE " + " AND ".join(where)
        query += " ORDER BY id DESC"

        try:
            read_cursor.execute(query)
            rows = read_cursor.fetchall() or []
        except Exception as first_error:
            # Some older databases do not expose the id column consistently.
            # Retry without ordering before treating the page as empty.
            try:
                read_cursor.execute(f"SELECT {', '.join(selected)} FROM devices" + (" WHERE " + " AND ".join(where) if where else ""))
                rows = read_cursor.fetchall() or []
            except Exception as second_error:
                logger.error(f"ServiceListPage fetch error: {first_error}; retry failed: {second_error}")
                return
        records = []
        for row in rows:
            rec = {col_name: row[idx] for idx, col_name in enumerate(selected)}
            records.append(rec)
        self._all_records = records

    def _update_chip_counts(self):
        counts = {key: 0 for key in {
            "all", "today", "pending_approval", "cargo_waiting", "invoiced",
            "uninvoiced", "external_out", "external_return", "done", "active",
            "waiting", "iptal", "teslim", "part", "debt",
        }}
        for rec in self._all_records:
            status = normalize_device_status(rec.get("status"))
            price = 0.0
            try:
                price = float(rec.get("price") or 0)
            except Exception:
                price = 0.0
            payment_status = str(rec.get("payment_status") or "").lower()

            counts["all"] += 1
            if status in {"Tamirde", "Serviste", "\u0130\u015flemde"}:
                counts["active"] += 1
            elif status in {"Teslim Edildi", "Teslim", "Haz\u0131r", "Tamir Edildi"}:
                counts["done"] += 1
                counts["teslim"] += 1
            elif status in {"Bekliyor", "\u0130\u015fleme Al\u0131nacak"}:
                counts["waiting"] += 1
            elif status in {"\u0130ptal", "\u0130ade"}:
                counts["iptal"] += 1
            elif status in {"Par\u00e7a Bekliyor"}:
                counts["part"] += 1
            elif status in {"Test S\u00fcrecinde"}:
                counts["external_return"] += 1

            if price > 0 and status != "Teslim Edildi" and payment_status not in {"\u00f6dendi", "odendi", "paid"}:
                counts["debt"] += 1

            shipment = (str(rec.get("delivery_type") or "") + " " + str(rec.get("service_source") or "")).lower()
            if "kargo" in shipment or status in {"Kargo Bekliyor", "Kargoya Verildi"}:
                counts["cargo_waiting"] += 1

        for key, btn in self._chip_buttons.items():
            base_text = btn.text().split(" (")[0]
            cnt = counts.get(key, 0)
            btn.setText(f"{base_text} ({cnt})")

    def _on_search_changed(self, text: str):
        self._current_search_query = str(text or "").strip().lower()
        self._apply_all_filters()

    def _on_combo_filter_changed(self):
        self._current_status_filter = self.combo_status.currentData() or "all"
        self._current_date_filter = self.combo_date.currentData() or "all"
        self._apply_all_filters()

    def clear_filters(self):
        self.search_input.clear()
        self.combo_status.setCurrentIndex(0)
        self.combo_date.setCurrentIndex(0)
        self.set_filter_category("all")

    def _apply_all_filters(self):
        cat = self.current_filter_category
        sq = self._current_search_query
        sf = self._current_status_filter
        df = self._current_date_filter

        filtered = []
        for rec in self._all_records:
            status = normalize_device_status(rec.get("status"))
            status_raw = str(rec.get("status") or "")
            tracking = str(rec.get("tracking_no") or "").lower()
            cust = str(rec.get("customer_name") or "").lower()
            dev = (str(rec.get("device_brand") or "") + " " + str(rec.get("device_model") or "")).lower()

            # Search query filter
            if sq and (sq not in tracking and sq not in cust and sq not in dev):
                continue

            entry_text = str(rec.get("entry_date") or "")
            entry_date = None
            if entry_text:
                try:
                    entry_date = datetime.fromisoformat(entry_text[:19]).date()
                except (TypeError, ValueError):
                    entry_date = None

            today = datetime.now().date()
            if df == "today" and entry_date != today:
                continue
            if df == "week" and (entry_date is None or entry_date < today - timedelta(days=6)):
                continue
            if df == "month" and (
                entry_date is None or
                (entry_date.year, entry_date.month) != (today.year, today.month)
            ):
                continue
            if df == "last_30" and (entry_date is None or entry_date < today - timedelta(days=29)):
                continue
            if df == "year" and (entry_date is None or entry_date.year != today.year):
                continue

            # Status dropdown filter
            if sf != "all" and sf != status and sf != status_raw:
                continue

            # Chip category filter
            if cat == "all":
                pass
            elif cat == "active":
                if status not in {"Tamirde", "Serviste", "\u0130\u015flemde"}:
                    continue
            elif cat == "done":
                if status not in {"Tamir Edildi", "Teslim Edildi", "Teslim", "Haz\u0131r"} and status_raw not in {"Tamir Edildi", "Tamir Edildi"}:
                    continue
            elif cat == "test":
                if status != "Test S\u00fcrecinde":
                    continue
            elif cat == "waiting":
                if status not in {"Bekliyor", "\u0130\u015fleme Al\u0131nacak"}:
                    continue
            elif cat == "iptal":
                if status not in {"\u0130ptal", "\u0130ade"}:
                    continue
            elif cat == "teslim":
                if status not in {"Teslim Edildi", "Teslim"}:
                    continue
            elif cat == "part":
                if status not in {"Par\u00e7a Bekliyor"}:
                    continue
            elif cat == "debt":
                price = 0.0
                try:
                    price = float(rec.get("price") or 0)
                except Exception:
                    price = 0.0
                payment_status = str(rec.get("payment_status") or "").lower()
                if not (price > 0 and status != "Teslim Edildi" and payment_status not in {"\u00f6dendi", "odendi", "paid"}):
                    continue
            elif cat == "cargo_waiting":
                shipment = (str(rec.get("delivery_type") or "") + " " + str(rec.get("service_source") or "")).lower()
                if "kargo" not in shipment and status not in {"Kargo Bekliyor", "Kargoya Verildi"}:
                    continue
            elif cat == "invoiced":
                pass
            elif cat == "uninvoiced":
                pass
            elif cat == "today":
                entry = str(rec.get("entry_date") or "")
                today_str = datetime.now().strftime("%Y-%m-%d")
                if not entry.startswith(today_str):
                    continue

            filtered.append(rec)

        self._filtered_records = filtered
        self._current_page = 1
        self._render_current_page()

    def _on_page_size_changed(self):
        self._page_size = self.combo_page_size.currentData() or 8
        self._current_page = 1
        self._render_current_page()

    def _render_current_page(self):
        total = len(self._filtered_records)
        page_size = self._page_size
        total_pages = max(1, (total + page_size - 1) // page_size)
        self._current_page = min(max(1, self._current_page), total_pages)

        start_idx = (self._current_page - 1) * page_size
        end_idx = min(start_idx + page_size, total)
        page_records = self._filtered_records[start_idx:end_idx]

        # Update info label
        if total == 0:
            self.lbl_page_info.setText("0 kay\u0131ttan 0-0 aras\u0131")
        else:
            self.lbl_page_info.setText(f"{total} kay\u0131ttan {start_idx + 1}-{end_idx} aras\u0131")

        # Update pagination buttons
        self._build_pagination_buttons(total_pages)

        # Populate table
        self.table.setRowCount(0)
        self.table.setRowCount(len(page_records))

        for row_idx, rec in enumerate(page_records):
            tracking_no = str(rec.get("tracking_no") or "")

            # 0: Checkbox
            chk = QCheckBox()
            chk.setCursor(Qt.CursorShape.PointingHandCursor)
            chk.setToolTip("Satiri sec")
            chk.setStyleSheet(theme_qss("""
                QCheckBox {
                    background: transparent;
                    border: none;
                    spacing: 0;
                }
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                    background-color: @surface;
                    border: 1px solid @border;
                    border-radius: 3px;
                }
                QCheckBox::indicator:hover {
                    border-color: @accent;
                    background-color: @hover_bg;
                }
                QCheckBox::indicator:checked {
                    background-color: @accent;
                    border-color: @accent;
                }
            """))
            chk_wrap = QWidget()
            chk_lay = QHBoxLayout(chk_wrap)
            chk_lay.setContentsMargins(0, 0, 0, 0)
            chk_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chk_lay.addWidget(chk)
            self.table.setCellWidget(row_idx, 0, chk_wrap)

            # 1: TAKIP NO
            item_tno = QTableWidgetItem(tracking_no)
            item_tno.setToolTip(tracking_no)
            item_tno.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            item_tno.setForeground(QColor("#1D4ED8"))
            item_tno.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row_idx, 1, item_tno)

            # 2: MUSTERI (transparent two-line cell)
            cust_name = str(rec.get("customer_name") or "-")
            company = str(rec.get("company_name") or "").strip()
            self.table.setCellWidget(
                row_idx, 2,
                self._install_row_selection(
                    self._make_text_cell(cust_name, company, bold=True), row_idx
                ),
            )

            # 3: CIHAZ / MODEL (transparent two-line cell)
            brand = str(rec.get("device_brand") or rec.get("device_type") or "-")
            model = str(rec.get("device_model") or "").strip()
            self.table.setCellWidget(
                row_idx, 3,
                self._install_row_selection(
                    self._make_text_cell(brand, model, bold=True), row_idx
                ),
            )

            # 4: KABUL TARIHI
            entry_date = str(rec.get("entry_date") or "-")
            item_entry = QTableWidgetItem(entry_date)
            item_entry.setFont(QFont("Segoe UI", 10))
            self.table.setItem(row_idx, 4, item_entry)

            # 5: TESLIM TARIHI
            exit_date = str(rec.get("exit_date") or "-")
            item_exit = QTableWidgetItem(exit_date if exit_date else "-")
            item_exit.setFont(QFont("Segoe UI", 10))
            self.table.setItem(row_idx, 5, item_exit)

            # 6: UCRET
            price_val = 0.0
            try:
                price_val = float(rec.get("price") or 0)
            except Exception:
                price_val = 0.0
            price_str = CurrencyHelper.format_amount(price_val, db=self.db)
            item_price = QTableWidgetItem(price_str)
            item_price.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self.table.setItem(row_idx, 6, item_price)

            # 7: DURUM (Badge)
            status_text = normalize_device_status(rec.get("status") or "Bekliyor")
            badge_durum = self._create_status_badge(status_text)
            self.table.setCellWidget(row_idx, 7, self._install_row_selection(badge_durum, row_idx))

            # 8: ACILIYET (Badge)
            urgency_text = str(rec.get("urgency") or "Normal")
            badge_urgency = self._create_urgency_badge(urgency_text)
            self.table.setCellWidget(row_idx, 8, self._install_row_selection(badge_urgency, row_idx))

            # 9: ISLEMLER (View, Edit, Print, More)
            actions_widget = self._create_row_actions(tracking_no)
            self.table.setCellWidget(row_idx, 9, actions_widget)

    def _make_text_cell(self, primary: str, secondary: str = "", bold: bool = False) -> QWidget:
        """Create a transparent two-line cell without an extra panel/shadow."""
        cell = QWidget()
        cell.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        cell.setStyleSheet("background: transparent; border: none;")
        layout = QVBoxLayout(cell)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(0)
        primary_label = QLabel(html.escape(str(primary or "-")))
        primary_label.setTextFormat(Qt.TextFormat.RichText)
        primary_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold if bold else QFont.Weight.DemiBold))
        primary_label.setStyleSheet(
            theme_qss(
                "background: transparent; border: none; color: @text; "
                f"font-size: 11px; font-weight: {'800' if bold else '600'};"
            )
        )
        primary_label.setWordWrap(False)
        layout.addWidget(primary_label)
        if secondary:
            secondary_label = QLabel(html.escape(str(secondary)))
            secondary_label.setTextFormat(Qt.TextFormat.RichText)
            secondary_label.setFont(QFont("Segoe UI", 9))
            secondary_label.setStyleSheet(
                theme_qss(
                    "background: transparent; border: none; color: @text_muted; "
                    "font-size: 10px; font-weight: 500;"
                )
            )
            secondary_label.setWordWrap(False)
            layout.addWidget(secondary_label)
        return cell

    def _create_status_badge(self, status: str) -> QWidget:
        container = QWidget()
        container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        container.setStyleSheet("background: transparent; border: none;")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 6, 4, 6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        norm = normalize_device_status(status)
        badge = QLabel(f" {norm} ")
        badge.setFixedHeight(26)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if norm == "Tamirde":
            bg, fg = "#FEF3C7", "#D97706"
        elif norm in {"Teslim Edildi", "Teslim", "Tamir Edildi"}:
            bg, fg = "#D1FAE5", "#059669"
        elif norm == "\u0130ptal":
            bg, fg = "#FEE2E2", "#DC2626"
        elif norm == "Par\u00e7a Bekliyor":
            bg, fg = "#FFEDD5", "#EA580C"
        elif norm == "Test S\u00fcrecinde":
            bg, fg = "#EDE9FE", "#7C3AED"
        elif norm == "Onay Bekliyor":
            bg, fg = "#FEF9C3", "#CA8A04"
        else:
            bg, fg = "#E0F2FE", "#0284C7"

        badge.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                color: {fg};
                font-size: 11px;
                font-weight: 800;
                border-radius: 12px;
                padding: 0 10px;
            }}
        """)
        layout.addWidget(badge)
        return container

    def _create_urgency_badge(self, urgency: str) -> QWidget:
        container = QWidget()
        container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        container.setStyleSheet("background: transparent; border: none;")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 6, 4, 6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        badge = QLabel(f" {urgency} ")
        badge.setFixedHeight(24)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

        u_lower = urgency.lower()
        if "y\u00fcksek" in u_lower or "acil" in u_lower:
            bg, fg = "#FEE2E2", "#DC2626"
        elif "d\u00fc\u015f\u00fck" in u_lower:
            bg, fg = "#F1F5F9", "#64748B"
        else:
            bg, fg = "#EFF6FF", "#2563EB"

        badge.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                color: {fg};
                font-size: 10px;
                font-weight: 800;
                border-radius: 10px;
                padding: 0 8px;
            }}
        """)
        layout.addWidget(badge)
        return container

    def _create_row_actions(self, tracking_no: str) -> QWidget:
        container = QWidget()
        container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        container.setStyleSheet("background: transparent; border: none;")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(6, 2, 8, 2)
        layout.setSpacing(4)
        layout.addStretch(1)
        container.setMinimumWidth(280)
        container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        btn_style = theme_qss("""
            QPushButton {
                background-color: @surface_alt;
                color: @text;
                border: 1px solid @border;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: @hover_bg;
                border-color: @accent;
            }
        """)

        def set_svg_icon(button, svg):
            icon = render_svg_icon(svg, tc("text"), size=16)
            button.setIcon(icon)
            button.setIconSize(QSize(16, 16))
            button.setText("")
            button.setProperty("serviceActionSvg", svg)

        # 1. View / Info
        btn_view = QPushButton()
        btn_view.setToolTip("G\u00f6r\u00fcnt\u00fcle / Detaylar")
        btn_view.setFixedSize(26, 26)
        btn_view.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_view.setStyleSheet(btn_style)
        set_svg_icon(btn_view, '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z"/><circle cx="12" cy="12" r="2.5"/></svg>')
        btn_view.clicked.connect(lambda: self.open_context_menu_action("info", tracking_no))
        layout.addWidget(btn_view)

        # 2. Edit / Technician Panel
        btn_edit = QPushButton()
        btn_edit.setToolTip("D\u00fczenle / Teknisyen Paneli")
        btn_edit.setFixedSize(26, 26)
        btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_edit.setStyleSheet(btn_style)
        set_svg_icon(btn_edit, '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m4 20 4.5-1 10-10a2.1 2.1 0 0 0-3-3l-10 10L4 20Z"/><path d="m13.5 7.5 3 3"/></svg>')
        btn_edit.clicked.connect(lambda: self.open_technician_panel(tracking_no))
        layout.addWidget(btn_edit)

        # 3. Print
        btn_print = QPushButton()
        btn_print.setToolTip("Yazd\u0131r")
        btn_print.setFixedSize(26, 26)
        btn_print.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_print.setStyleSheet(btn_style)
        set_svg_icon(btn_print, '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9V3h12v6"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><path d="M6 14h12v7H6z"/></svg>')
        btn_print.clicked.connect(lambda: self.print_service(tracking_no))
        layout.addWidget(btn_print)

        # Keep every service action directly accessible in the row.
        actions = [
            ("payment", "\u00d6deme Al", '<rect x="2" y="5" width="20" height="14" rx="2"/><circle cx="12" cy="12" r="3"/><path d="M5 9h2m10 6h2"/>', lambda: self.open_context_menu_action("payment", tracking_no)),
            ("sms", "SMS G\u00f6nder", '<path d="M21 11a8 8 0 0 1-8 8H7l-5 3 2-6a8 8 0 0 1-1-5 8 8 0 0 1 8-8h2a8 8 0 0 1 8 8Z"/><path d="M7 9h10M7 13h7"/>', lambda: self.open_context_menu_action("sms", tracking_no)),
            ("whatsapp", "WhatsApp", '<path d="M20 11.5a8.5 8.5 0 0 1-12.5 7.5L3 21l1.5-5A8.5 8.5 0 1 1 20 11.5Z"/><path d="M8 7c0 5 4 9 8 9l1-3-3-1-1 1-3-3 1-1-1-3Z"/>', lambda: self.open_context_menu_action("whatsapp", tracking_no)),
            ("status", "Durum De\u011fi\u015ftir", '<path d="M20 7v5h-5M4 17v-5h5"/><path d="M6 7a7 7 0 0 1 12-2l2 3M4 16l2 3a7 7 0 0 0 12-2"/>', lambda: self.change_status(tracking_no)),
            ("delete", "Sil / Ar\u015fivle", '<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7"/>', lambda: self.delete_service(tracking_no)),
        ]
        for action_id, label, paths, callback in actions:
            button = QPushButton()
            button.setObjectName("service_action_" + action_id)
            button.setToolTip(label)
            button.setAccessibleName(label)
            button.setFixedSize(26, 26)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(btn_style)
            set_svg_icon(button, '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">' + paths + '</svg>')
            button.clicked.connect(callback)
            layout.addWidget(button)

        return container

    def refresh_theme(self):
        self.setStyleSheet(theme_qss("background-color: @surface_alt;"))
        for button in self.findChildren(QPushButton):
            svg = button.property("serviceActionSvg")
            if svg:
                button.setIcon(render_svg_icon(str(svg), tc("text"), size=16))
                button.setIconSize(QSize(16, 16))
        self._apply_all_filters()

    apply_theme_styles = refresh_theme

    def _build_pagination_buttons(self, total_pages: int):
        # Clear existing buttons
        while self.page_btn_layout.count():
            item = self.page_btn_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Prev button
        btn_prev = QPushButton("<")
        btn_prev.setFixedSize(30, 30)
        btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_prev.setEnabled(self._current_page > 1)
        btn_prev.setStyleSheet(self._page_button_style(False))
        btn_prev.clicked.connect(lambda: self._go_to_page(self._current_page - 1))
        self.page_btn_layout.addWidget(btn_prev)

        # Page numbers
        pages_to_show = []
        if total_pages <= 7:
            pages_to_show = list(range(1, total_pages + 1))
        else:
            if self._current_page <= 4:
                pages_to_show = [1, 2, 3, 4, 5, "...", total_pages]
            elif self._current_page >= total_pages - 3:
                pages_to_show = [1, "...", total_pages - 4, total_pages - 3, total_pages - 2, total_pages - 1, total_pages]
            else:
                pages_to_show = [1, "...", self._current_page - 1, self._current_page, self._current_page + 1, "...", total_pages]

        for p in pages_to_show:
            if p == "...":
                lbl_dots = QLabel("...")
                lbl_dots.setStyleSheet("color: #94A3B8; font-weight: 800; padding: 0 4px;")
                self.page_btn_layout.addWidget(lbl_dots)
            else:
                btn_page = QPushButton(str(p))
                btn_page.setFixedSize(30, 30)
                btn_page.setCursor(Qt.CursorShape.PointingHandCursor)
                is_current = (p == self._current_page)
                btn_page.setStyleSheet(self._page_button_style(is_current))
                btn_page.clicked.connect(lambda checked=False, target_page=p: self._go_to_page(target_page))
                self.page_btn_layout.addWidget(btn_page)

        # Next button
        btn_next = QPushButton(">")
        btn_next.setFixedSize(30, 30)
        btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_next.setEnabled(self._current_page < total_pages)
        btn_next.setStyleSheet(self._page_button_style(False))
        btn_next.clicked.connect(lambda: self._go_to_page(self._current_page + 1))
        self.page_btn_layout.addWidget(btn_next)

    def _page_button_style(self, is_active: bool) -> str:
        if is_active:
            return theme_qss("""
                QPushButton {
                    background-color: #2563EB;
                    color: #FFFFFF;
                    font-size: 12px;
                    font-weight: 800;
                    border: none;
                    border-radius: 6px;
                }
            """)
        return theme_qss("""
            QPushButton {
                background-color: @surface;
                color: @text;
                font-size: 12px;
                font-weight: 700;
                border: 1px solid @border;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: @hover_bg;
                border-color: @accent;
            }
            QPushButton:disabled {
                color: @text_muted;
                background-color: @surface_alt;
            }
        """)

    def _go_to_page(self, page_num: int):
        self._current_page = page_num
        self._render_current_page()

    def _on_table_double_clicked(self, row: int, col: int):
        item = self.table.item(row, 1)
        if item:
            tracking_no = item.text().strip()
            self.open_technician_panel(tracking_no)

    def _get_selected_tracking_no(self) -> Optional[str]:
        row = self.table.currentRow()
        if row >= 0:
            item = self.table.item(row, 1)
            if item:
                return item.text().strip()
        return None

    def _action_service_history(self):
        tno = self._get_selected_tracking_no()
        if not tno:
            self.notify("L\u00fctfen ge\u00e7mi\u015fini g\u00f6rmek istedi\u011finiz bir servis se\u00e7in.", "warning")
            return
        self.open_context_menu_action("info", tno)

    def _action_print_detail(self):
        tno = self._get_selected_tracking_no()
        if not tno:
            self.notify("L\u00fctfen fi\u015fini yazd\u0131rmak istedi\u011finiz bir servis se\u00e7in.", "warning")
            return
        self.print_detailed_receipt(tno)

    def _action_print_cargo(self):
        tno = self._get_selected_tracking_no()
        if not tno:
            self.notify("L\u00fctfen kargo fi\u015fini yazd\u0131rmak istedi\u011finiz bir servis se\u00e7in.", "warning")
            return
        self.print_cargo_receipt(tno)

    def _action_dispatch_note(self):
        tno = self._get_selected_tracking_no()
        if not tno:
            self.notify("L\u00fctfen i\u015flem yapmak istedi\u011finiz bir servis se\u00e7in.", "warning")
            return
        self.notify(f"Takip No: {tno} i\u00e7in E-\u0130rsaliye mod\u00fcl\u00fc haz\u0131rlan\u0131yor...", "info")

    def _action_e_invoice(self):
        tno = self._get_selected_tracking_no()
        if not tno:
            self.notify("L\u00fctfen fatura d\u00fczenlemek istedi\u011finiz bir servis se\u00e7in.", "warning")
            return
        if self.main_window and hasattr(self.main_window, "switch_page"):
            from src.utils.page_ids import PageIds
            self.main_window.switch_page(PageIds.INVOICE)

    def export_records(self):
        """Export current filtered table data to Excel or CSV."""
        if not self._filtered_records:
            self.notify("D\u0131\u015fa aktar\u0131lacak servis kayd\u0131 bulunamad\u0131.", "warning")
            return
        try:
            import pandas as pd
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Servis Listesini D\u0131\u015fa Aktar",
                f"servis_listesi_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                "Excel Dosyas\u0131 (*.xlsx);;CSV Dosyas\u0131 (*.csv)",
            )
            if not file_path:
                return

            rows_to_export = []
            for r in self._filtered_records:
                rows_to_export.append({
                    "Takip No": r.get("tracking_no"),
                    "M\u00fc\u015fteri": r.get("customer_name"),
                    "\u015eirket": r.get("company_name"),
                    "Cihaz T\u00fcr\u00fc": r.get("device_type"),
                    "Marka": r.get("device_brand"),
                    "Model": r.get("device_model"),
                    "Giri\u015f Tarihi": r.get("entry_date"),
                    "\u00c7\u0131k\u0131\u015f Tarihi": r.get("exit_date"),
                    "\u00dccret": r.get("price"),
                    "Durum": r.get("status"),
                    "Aciliyet": r.get("urgency"),
                })
            df = pd.DataFrame(rows_to_export)
            if file_path.endswith(".csv"):
                df.to_csv(file_path, index=False, encoding="utf-8-sig")
            else:
                df.to_excel(file_path, index=False)
            self.notify("Servis listesi ba\u015far\u0131yla d\u0131\u015fa aktar\u0131ld\u0131.", "success")
        except Exception as e:
            logger.error(f"Service export error: {e}")
            self.notify(f"D\u0131\u015fa aktarma hatas\u0131: {e}", "error")
