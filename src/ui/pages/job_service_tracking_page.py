# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMenu, QLabel, QFrame, QPushButton, QDialog,
    QGridLayout, QLineEdit
)
from PyQt6.QtCore import Qt, QDate, QSize
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import QGraphicsDropShadowEffect
from datetime import datetime
from src.utils.theme_colors import theme_qss, tc
from src.utils.design_system import DesignTokens
from src.utils.currency_helper import CurrencyHelper
from src.utils.context_menu_settings import is_context_menu_enabled
from src.utils.logger import logger
from src.ui.widgets.empty_state import EmptyState
from src.ui.pages._dashboard_utils import render_svg_icon



class JobServiceTrackingPage(QWidget):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.setup_ui()
        self._wire_ui_signals()
        self.load_jobs()
        self.load_services()
        self.update_stat_cards()

    def show_service_list(self, category="all"):
        """Open the service tab and apply a dashboard status filter."""
        self.tabs.setCurrentWidget(self.service_tab)
        self._service_category = str(category or "all")
        self.apply_service_filter()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)

        header = QLabel("İş / Servis Takibi Raporları")
        header.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        header.setStyleSheet(theme_qss("color: @text;"))
        header_row.addWidget(header)
        header_row.addStretch()

        self.btn_report = QPushButton("Rapor / Analiz")
        self.btn_report.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_report.setFixedHeight(36)
        try:
            self.btn_report.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="sm")))
        except Exception:
            self.btn_report.setStyleSheet(theme_qss(
                "QPushButton { background-color: @accent_hover; color: white; border-radius: 8px; padding: 6px 14px; "
                "border: none; font-weight: 600; } QPushButton:hover { background-color: @accent_pressed; }"
            ))
        self.btn_report.clicked.connect(self.show_monthly_report)
        header_row.addWidget(self.btn_report)

        layout.addLayout(header_row)

        # Renkli İstatistik Kartları
        stats_layout = QHBoxLayout()
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(16)

        # Card 1: Toplam İşler
        self.card_total_jobs = self._create_stat_card("📋 Toplam İşler", "0", tc("accent"), tc("accent"))
        self.card_total_jobs.setMinimumWidth(160)
        stats_layout.addWidget(self.card_total_jobs)

        # Card 2: Açık İşler
        self.card_open_jobs = self._create_stat_card("⏳ Açık İşler", "0", tc("warning"), tc("warning"))
        self.card_open_jobs.setMinimumWidth(160)
        stats_layout.addWidget(self.card_open_jobs)

        # Card 3: Tahsil Edilen İşler
        self.card_paid_jobs = self._create_stat_card("✅ Tahsil Edilen", "0", tc("success"), tc("success"))
        self.card_paid_jobs.setMinimumWidth(160)
        stats_layout.addWidget(self.card_paid_jobs)

        # Card 4: Toplam Servisler
        self.card_total_services = self._create_stat_card("🛠️ Toplam Servis", "0", tc("accent_hover"), tc("accent_hover"))
        self.card_total_services.setMinimumWidth(160)
        stats_layout.addWidget(self.card_total_services)

        # Card 5: Tamamlanan Servisler
        self.card_completed_services = self._create_stat_card("🎯 Tamamlanan", "0", tc("warning"), tc("warning"))
        self.card_completed_services.setMinimumWidth(160)
        stats_layout.addWidget(self.card_completed_services)

        # Card 6: Toplam Tahsilat
        self.card_total_revenue = self._create_stat_card(
            "💰 Tahsilat",
            CurrencyHelper.format_try_for_display(0, db=self.db, include_try_reference=False),
            tc("success"),
            tc("success"),
        )
        self.card_total_revenue.setMinimumWidth(160)
        stats_layout.addWidget(self.card_total_revenue)

        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        # Boşluk
        layout.addSpacing(8)

        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs.setDocumentMode(True)
        self.tabs.setStyleSheet(theme_qss(
            "QTabWidget::pane { border: none; } "
            "QTabBar::tab {"
            "  background: @border;"
            "  color: @selection_text;"
            "  padding: 10px 26px;"
            "  border-radius: 999px;"
            "  margin-right: 8px;"
            "  font-weight: 700;"
            "  font-size: 13px;"
            "  min-height: 32px;"
            "} "
            "QTabBar::tab:selected {"
            "  background: @accent_hover;"
            "  color: white;"
            "} "
            "QTabBar::tab:hover {"
            "  background: @selection_bg;"
            "} "
            "QTabBar::tab:selected:hover {"
            "  background: @accent_pressed;"
            "}"
        ))
        layout.addWidget(self.tabs)

        # İş Takip sekmesi (Yeni İşlemler)
        self.job_table = QTableWidget()
        self.job_table.setColumnCount(7)
        self.job_table.setHorizontalHeaderLabels([
            "İş No", "Müşteri", "Durum", "Açıklama", "Tutar", "Tarih", "Para Br."
        ])
        self._style_table(self.job_table)
        self.job_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.job_table.customContextMenuRequested.connect(self.on_job_context_menu)
        self.job_table.cellDoubleClicked.connect(self._open_job_detail_from_cell)
        self.job_tab = QWidget()
        job_tab_layout = QVBoxLayout(self.job_tab)
        job_tab_layout.setContentsMargins(0, 0, 0, 0)
        job_tab_layout.setSpacing(8)
        self.job_search_input = QLineEdit()
        self.job_search_input.setPlaceholderText("İş no, müşteri, açıklama, durum veya para birimi ara...")
        self.job_search_button = QPushButton("Ara")
        self.job_search_clear_button = QPushButton("Temizle")
        job_tab_layout.addLayout(self._create_search_bar(
            self.job_search_input,
            self.job_search_button,
            self.job_search_clear_button,
            self.apply_job_filter,
        ))
        self.job_empty_state = EmptyState("Açık iş kaydı yok", "Bu görünümde gösterilecek iş kaydı bulunamadı.", parent=self)
        self.job_empty_state.hide()
        job_tab_layout.addWidget(self.job_table)
        job_tab_layout.addWidget(self.job_empty_state)
        self.tabs.addTab(self.job_tab, "İş Takip")

        # Servis Takip sekmesi (Servis Formları / Devices)
        self.service_table = QTableWidget()
        self.service_table.setColumnCount(9)
        self.service_table.setHorizontalHeaderLabels([
            "Servis No", "M\u00fc\u015fteri", "Durum", "Cihaz / \u0130\u015f", "Toplam",
            "Giri\u015f Tarihi", "Teslim Tarihi", "Teknisyen", "\u0130\u015flemler"
        ])
        self._style_table(self.service_table)
        self.service_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.service_table.customContextMenuRequested.connect(self.on_service_context_menu)
        self.service_table.cellDoubleClicked.connect(self._open_service_detail_from_cell)
        self.service_tab = QWidget()
        service_tab_layout = QVBoxLayout(self.service_tab)
        service_tab_layout.setContentsMargins(0, 0, 0, 0)
        service_tab_layout.setSpacing(8)
        self.service_search_input = QLineEdit()
        self.service_search_input.setPlaceholderText("Servis no, müşteri, cihaz, durum, teknisyen veya tarih ara...")
        self.service_search_button = QPushButton("Ara")
        self.service_search_clear_button = QPushButton("Temizle")
        service_tab_layout.addLayout(self._create_search_bar(
            self.service_search_input,
            self.service_search_button,
            self.service_search_clear_button,
            self.apply_service_filter,
        ))
        self.service_empty_state = EmptyState("Açık servis kaydı yok", "Bu görünümde gösterilecek servis kaydı bulunamadı.", parent=self)
        self.service_empty_state.hide()
        service_tab_layout.addWidget(self.service_table)
        service_tab_layout.addWidget(self.service_empty_state)
        self.tabs.addTab(self.service_tab, "Servis Takip")

    def _wire_ui_signals(self):
        self.job_search_button.clicked.connect(self._on_ui_widget_changed)
        self.job_search_clear_button.clicked.connect(self._on_ui_widget_changed)
        self.service_search_button.clicked.connect(self._on_ui_widget_changed)
        self.service_search_clear_button.clicked.connect(self._on_ui_widget_changed)

    def _create_search_bar(self, search_input, search_button, clear_button, apply_callback):
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        search_input.setClearButtonEnabled(True)
        search_input.setFixedHeight(34)
        search_input.returnPressed.connect(apply_callback)
        search_button.clicked.connect(apply_callback)
        clear_button.clicked.connect(lambda: self._clear_search(search_input, apply_callback))

        search_input.setStyleSheet(theme_qss("""
            QLineEdit {
                background: @surface;
                color: @text;
                border: 1px solid @border;
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid @accent;
                background: @surface;
            }
        """))
        button_qss = """
            QPushButton {
                background: #FFFFFF;
                color: #0F172A;
                border: 1px solid #B8C7DA;
                border-radius: 8px;
                padding: 6px 14px;
                font-weight: 700;
                min-width: 78px;
            }
            QPushButton:hover {
                background: #EAF2FF;
                color: #0F172A;
                border: 1px solid #3B82F6;
            }
            QPushButton:pressed {
                background: #3B82F6;
                color: #FFFFFF;
                border: 1px solid #2563EB;
            }
            QPushButton:disabled {
                background: #EEF2F7;
                color: #64748B;
                border: 1px solid #CBD5E1;
            }
        """
        search_button.setStyleSheet(button_qss)
        clear_button.setStyleSheet(button_qss)

        row.addWidget(search_input, 1)
        row.addWidget(search_button)
        row.addWidget(clear_button)
        return row

    def _clear_search(self, search_input, apply_callback):
        search_input.clear()
        apply_callback()

    def _style_table(self, table):
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        if table.columnCount() > 7:
            header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        if table.columnCount() > 8:
            header.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)
            table.setColumnWidth(8, 126)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.setShowGrid(False)
        table.verticalHeader().setVisible(False)
        table.setMouseTracking(True)
        table.setStyleSheet(theme_qss("""
            QTableWidget {
                background: @surface;
                border: 1px solid @border;
                border-radius: 12px;
                outline: none;
            }
            QTableWidget::item {
                padding: 8px 10px;
                border-bottom: 1px solid @border;
                outline: none;
            }
            QTableWidget::item:hover {
                background: @surface_alt;
            }
            QTableWidget::item:selected {
                background: @accent;
                color: white;
                outline: none;
            }
            QTableWidget::item:focus {
                outline: none;
                border: none;
            }
        """))

    def _create_stat_card(self, title, value, color_primary, color_accent):
        """Renkli istatistik kartı oluştur"""
        card = QFrame()
        card.setFixedHeight(100)
        card.setStyleSheet(theme_qss(f"""
            QFrame {{
                background: linear-gradient(135deg, {color_primary}15 0%, {color_primary}08 100%);
                border: 2px solid {color_primary};
                border-radius: 12px;
            }}
        """))

        # Gölge efekti ekle
        try:
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(8)
            shadow.setColor(QColor(0, 0, 0, 15))
            shadow.setOffset(0, 2)
            card.setGraphicsEffect(shadow)
        except Exception as e:
            logger.error(f"Archive context menu action failed: {e}")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(6)

        # Title
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(theme_qss(f"""
            color: {color_primary};
            font-size: 11px;
            font-weight: 700;
        """))
        layout.addWidget(lbl_title)

        # Value
        lbl_value = QLabel(value)
        lbl_value.setStyleSheet(theme_qss(f"""
            color: {color_accent};
            font-size: 24px;
            font-weight: 800;
        """))
        layout.addWidget(lbl_value)
        layout.addStretch()

        return card

    def _format_tr_date(self, value):
        text = str(value or "").strip()
        if not text or text in {"-", "None", "NULL"}:
            return "-"

        normalized = text.replace("T", " ").replace("/", "-")
        if "." in normalized:
            normalized = normalized.split(".", 1)[0]

        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%d-%m-%Y %H:%M:%S",
            "%d-%m-%Y %H:%M",
            "%d-%m-%Y",
        ):
            try:
                dt = datetime.strptime(normalized, fmt)
                if "%H" in fmt:
                    return dt.strftime("%d.%m.%Y %H:%M")
                return dt.strftime("%d.%m.%Y")
            except ValueError:
                continue
        return text

    def _row_matches_query(self, table, row, query):
        if not query:
            return True
        needle = query.casefold()
        for col in range(table.columnCount()):
            item = table.item(row, col)
            if item and needle in item.text().casefold():
                return True
        return False

    def _apply_table_filter(self, table, search_input, empty_state):
        query = search_input.text().strip()
        visible_count = 0
        for row in range(table.rowCount()):
            visible = self._row_matches_query(table, row, query)
            table.setRowHidden(row, not visible)
            if visible:
                visible_count += 1

        table.setVisible(visible_count > 0)
        empty_state.setVisible(visible_count == 0)

    def apply_job_filter(self):
        self._apply_table_filter(self.job_table, self.job_search_input, self.job_empty_state)

    def apply_service_filter(self):
        self._apply_table_filter(self.service_table, self.service_search_input, self.service_empty_state)
        category = getattr(self, "_service_category", "all")
        aliases = {
            "test": ("test",), "tamirde": ("tamir",),
            "bekliyor": ("bekliyor", "al"), "iptal": ("iptal", "iade"),
            "kargo": ("kargo",), "teslim": ("teslim",),
            "parca": ("parça",), "borclu": ("borç", "borclu"),
        }.get(category, ())
        if aliases:
            for row in range(self.service_table.rowCount()):
                status = self._table_text(self.service_table, row, 2).casefold()
                visible = any(alias in status for alias in aliases)
                self.service_table.setRowHidden(row, not visible)
        visible_count = sum(not self.service_table.isRowHidden(row) for row in range(self.service_table.rowCount()))
        self.service_table.setVisible(visible_count > 0)
        self.service_empty_state.setVisible(visible_count == 0)

    def _table_text(self, table, row, col):
        item = table.item(row, col)
        return item.text().strip() if item else ""

    def _open_job_detail_from_cell(self, row, column):
        self._open_job_detail(row)

    def _open_service_detail_from_cell(self, row, column):
        tracking_no = self._table_text(self.service_table, row, 0)
        if tracking_no:
            self._open_service_archive_detail(tracking_no)

    def _open_service_archive_detail(self, tracking_no):
        try:
            row = self.db.cursor.execute(
                "SELECT * FROM devices WHERE tracking_no=? AND COALESCE(is_deleted, 0)=0",
                (tracking_no,),
            ).fetchone()
            if row:
                from src.utils.system_config import SystemConfig
                is_auto = SystemConfig.get_current_sector(self.db) == "otomotiv" if hasattr(SystemConfig, "get_current_sector") else False
                if is_auto:
                    from src.ui.dialogs.automotive_technician_panel import AutomotiveTechnicianPanel as panel_cls
                else:
                    from src.ui.dialogs.technical_service_technician_panel import TechnicalServiceTechnicianPanel as panel_cls

                panel = panel_cls(
                    self.db,
                    row,
                    self,
                    sector_manager=getattr(self.main_window, "sector_manager", None),
                    read_only=True
                )
                panel.exec()
            else:
                from src.ui.dialogs.archive_detail_dialog import ArchiveDetailDialog
                dlg = ArchiveDetailDialog(self.db, tracking_no, self)
                dlg.exec()
        except Exception as e:
            logger.error(f"Service archive detail open failed: {e}", exc_info=True)

    def _open_service_technician_panel(self, tracking_no):
        opener = getattr(self.main_window, "open_technician_panel", None)
        if callable(opener):
            opener(tracking_no)

    def _open_service_form(self, tracking_no):
        opener = getattr(self.main_window, "open_service_form", None)
        if callable(opener):
            opener(tracking_no)

    def _service_action_button(self, tooltip, svg_content, callback, color):
        button = QPushButton()
        button.setToolTip(tooltip)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFixedSize(32, 30)
        button.setIcon(render_svg_icon(svg_content, color, size=16))
        button.setIconSize(QSize(16, 16))
        button.setStyleSheet(theme_qss("""
            QPushButton {
                background: @surface_alt;
                border: 1px solid @border;
                border-radius: 7px;
                padding: 0;
            }
            QPushButton:hover {
                background: @selection_bg;
                border-color: @accent;
            }
            QPushButton:pressed {
                background: @accent;
            }
        """))
        button.clicked.connect(callback)
        return button

    def _set_service_actions(self, row, tracking_no):
        container = QWidget(self.service_table)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)
        icons = {
            "detail": (
                '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                'stroke-width="2"><circle cx="12" cy="12" r="3"/>'
                '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/></svg>'
            ),
            "technician": (
                '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                'stroke-width="2"><path d="M14.7 6.3a4 4 0 0 0-5-5L8 3l3 3 1.7-1.7a4 4 0 0 0 2 2z"/>'
                '<path d="m5 21 9-9"/><path d="m3 17 4 4"/></svg>'
            ),
            "form": (
                '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                'stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
                '<path d="M14 2v6h6M8 13h8M8 17h8"/></svg>'
            ),
        }
        layout.addWidget(self._service_action_button(
            "Detay",
            icons["detail"],
            lambda checked=False, value=tracking_no: self._open_service_archive_detail(value),
            tc("accent"),
        ))
        layout.addWidget(self._service_action_button(
            "Teknisyen Paneli",
            icons["technician"],
            lambda checked=False, value=tracking_no: self._open_service_technician_panel(value),
            tc("success"),
        ))
        layout.addWidget(self._service_action_button(
            "Servis Formu",
            icons["form"],
            lambda checked=False, value=tracking_no: self._open_service_form(value),
            tc("warning"),
        ))
        self.service_table.setCellWidget(row, 8, container)


    def _fetch_job_detail(self, job_no):
        detail = {
            "job_no": job_no,
            "customer": "",
            "customer_id": None,
            "description": "",
            "status": "",
            "currency": "",
            "debit": 0.0,
            "credit": 0.0,
            "remaining": 0.0,
            "created_at": "",
            "transactions": [],
            "service": None,
        }
        cur = getattr(self.db, "cursor", None)
        if cur is None or not job_no:
            return detail

        try:
            cur.execute(
                """
                SELECT ct.id,
                       ct.transaction_type,
                       ct.amount,
                       ct.currency,
                       ct.try_equivalent,
                       ct.description,
                       ct.created_at,
                       ct.customer_id,
                       COALESCE(c.name, '') AS customer_name
                FROM currency_transactions ct
                LEFT JOIN customers c ON c.id = ct.customer_id
                WHERE ct.tracking_no=?
                ORDER BY ct.created_at ASC, ct.id ASC
                """,
                (job_no,),
            )
            rows = cur.fetchall() or []
            for row in rows:
                if hasattr(row, "keys"):
                    typ = str(row["transaction_type"] or "")
                    amount = float(row["amount"] or 0.0)
                    currency = str(row["currency"] or "")
                    try_amount = float(row["try_equivalent"] or 0.0)
                    desc = str(row["description"] or "")
                    created = str(row["created_at"] or "")
                    customer_id = row["customer_id"]
                    customer = str(row["customer_name"] or "")
                else:
                    typ = str(row[1] or "")
                    amount = float(row[2] or 0.0)
                    currency = str(row[3] or "")
                    try_amount = float(row[4] or 0.0)
                    desc = str(row[5] or "")
                    created = str(row[6] or "")
                    customer_id = row[7]
                    customer = str(row[8] or "")

                if typ == "DEBIT":
                    detail["debit"] += amount
                elif typ == "CREDIT":
                    detail["credit"] += amount
                if not detail["customer"] and customer:
                    detail["customer"] = customer
                if detail["customer_id"] is None and customer_id is not None:
                    detail["customer_id"] = customer_id
                if not detail["description"] and desc:
                    detail["description"] = desc
                if not detail["created_at"] and created:
                    detail["created_at"] = created
                if not detail["currency"] and currency:
                    detail["currency"] = currency
                detail["transactions"].append((created, typ, desc, amount, currency, try_amount))
        except Exception as e:
            logger.error(f"Job detail transaction query failed: {e}", exc_info=True)

        detail["remaining"] = detail["debit"] - detail["credit"]
        detail["status"] = "Tahsil Edildi" if detail["remaining"] <= 0.01 else "Açık"

        try:
            cur.execute(
                """
                SELECT tracking_no, customer_name, status, device_brand, device_model,
                       labor_cost, entry_date, exit_date, delivered_at, technician, general_note, technician_note
                FROM devices
                WHERE tracking_no=?
                LIMIT 1
                """,
                (job_no,),
            )
            row = cur.fetchone()
            if row:
                if hasattr(row, "keys"):
                    detail["service"] = {key: row[key] for key in row.keys()}
                else:
                    keys = [
                        "tracking_no", "customer_name", "status", "device_brand", "device_model",
                        "labor_cost", "entry_date", "exit_date", "delivered_at", "technician",
                        "general_note", "technician_note",
                    ]
                    detail["service"] = dict(zip(keys, row))
                if not detail["customer"]:
                    detail["customer"] = str(detail["service"].get("customer_name") or "")
        except Exception as e:
            logger.debug(f"Job detail service lookup skipped: {e}")

        return detail

    def _open_job_detail(self, row):
        job_no = self._table_text(self.job_table, row, 0)
        if not job_no:
            return
        detail = self._fetch_job_detail(job_no)

        dlg = QDialog(self)
        dlg.setWindowTitle(f"İş Detayı - {job_no}")
        dlg.resize(980, 680)
        dlg.setModal(True)
        dlg.setStyleSheet(theme_qss("""
            QDialog { background: @surface_alt; color: @text; }
            QFrame#DetailCard { background: @surface; border: 1px solid @border; border-radius: 14px; }
            QLabel { color: @text; }
            QTableWidget { background: @surface; color: @text; border: 1px solid @border; border-radius: 10px; gridline-color: @border; outline: none; }
            QHeaderView::section { background: @surface_alt; color: @text; border: 1px solid @border; padding: 7px; font-weight: 700; }
            QTableWidget::item { padding: 7px; border-bottom: 1px solid @border; outline: none; }
            QTableWidget::item:focus { outline: none; border: none; }
            QTableWidget::item:selected { outline: none; }
            QPushButton { background: @accent; color: @selection_text; border: none; border-radius: 8px; padding: 9px 18px; font-weight: 700; }
            QPushButton:hover { background: @accent_hover; }
        """))

        root = QVBoxLayout(dlg)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        title = QLabel(f"Yapılan İş Özeti - {job_no}")
        title.setFont(QFont("Segoe UI", 17, QFont.Weight.Bold))
        root.addWidget(title)

        summary = QFrame()
        summary.setObjectName("DetailCard")
        summary_layout = QGridLayout(summary)
        summary_layout.setContentsMargins(16, 14, 16, 14)
        summary_layout.setHorizontalSpacing(18)
        summary_layout.setVerticalSpacing(10)

        def add_summary(label, value, r, c):
            lbl = QLabel(label)
            lbl.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; font-weight: 700;"))
            val = QLabel(str(value or "-"))
            val.setWordWrap(True)
            val.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            summary_layout.addWidget(lbl, r * 2, c)
            summary_layout.addWidget(val, r * 2 + 1, c)

        add_summary("Müşteri", detail["customer"], 0, 0)
        add_summary("Durum", detail["status"], 0, 1)
        add_summary("Borçlandırılan", f"{detail['debit']:,.2f} {detail['currency'] or ''}".strip(), 0, 2)
        add_summary("Tahsil Edilen", f"{detail['credit']:,.2f} {detail['currency'] or ''}".strip(), 0, 3)
        add_summary("Kalan", f"{detail['remaining']:,.2f} {detail['currency'] or ''}".strip(), 1, 0)
        add_summary("Tarih", self._format_tr_date(detail["created_at"]), 1, 1)
        add_summary("Açıklama", detail["description"], 1, 2)
        if detail["service"]:
            service = detail["service"]
            device = f"{service.get('device_brand') or ''} {service.get('device_model') or ''}".strip()
            add_summary("Servis / Cihaz", device, 1, 3)
        root.addWidget(summary)

        if detail["service"]:
            service = detail["service"]
            service_frame = QFrame()
            service_frame.setObjectName("DetailCard")
            service_layout = QGridLayout(service_frame)
            service_layout.setContentsMargins(16, 12, 16, 12)
            service_layout.setHorizontalSpacing(18)
            service_layout.setVerticalSpacing(8)
            fields = [
                ("Servis Durumu", service.get("status")),
                ("Giriş Tarihi", self._format_tr_date(service.get("entry_date"))),
                ("Teslim Tarihi", self._format_tr_date(service.get("exit_date") or service.get("delivered_at"))),
                ("Teknisyen", service.get("technician")),
                ("Müşteri Notu", service.get("general_note")),
                ("Teknik Not", service.get("technician_note")),
            ]
            for idx, (label, value) in enumerate(fields):
                r = idx // 3
                c = idx % 3
                box = QLabel(f"<b>{label}</b><br>{str(value or '-')}")
                box.setWordWrap(True)
                service_layout.addWidget(box, r, c)
            root.addWidget(service_frame)

        tx_table = QTableWidget()
        tx_table.setColumnCount(6)
        tx_table.setHorizontalHeaderLabels(["Tarih", "Tür", "Açıklama", "Tutar", "Para Br.", "TRY Karşılığı"])
        tx_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        tx_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        tx_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        tx_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        tx_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        tx_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        tx_table.setAlternatingRowColors(True)
        tx_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tx_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tx_table.verticalHeader().setVisible(False)
        for created, typ, desc, amount, currency, try_amount in detail["transactions"]:
            r = tx_table.rowCount()
            tx_table.insertRow(r)
            display_type = "Borç" if typ == "DEBIT" else "Tahsilat" if typ == "CREDIT" else typ
            values = [
                self._format_tr_date(created),
                display_type,
                desc,
                f"{amount:,.2f}",
                currency,
                CurrencyHelper.format_try_for_display(try_amount, db=self.db, include_try_reference=False),
            ]
            for c, value in enumerate(values):
                tx_table.setItem(r, c, QTableWidgetItem(str(value or "")))
        root.addWidget(tx_table, 1)

        actions = QHBoxLayout()
        actions.addStretch()
        btn_close = QPushButton("Kapat")
        btn_close.clicked.connect(dlg.accept)
        actions.addWidget(btn_close)
        root.addLayout(actions)
        dlg.exec()

    def load_jobs(self):
        self.job_table.setRowCount(0)
        cur = getattr(self.db, "cursor", None)
        if cur is None:
            return

        try:
            cur.execute(
                """
                SELECT ct.customer_id,
                       ct.tracking_no,
                       MAX(ct.description) AS description,
                       SUM(CASE WHEN ct.transaction_type='DEBIT' THEN ct.amount ELSE 0 END) AS debit_amount,
                       MAX(ct.currency) AS currency,
                       MAX(ct.created_at) AS created_at,
                       COALESCE(c.name, '') AS customer_name,
                       SUM(CASE WHEN ct.transaction_type='DEBIT' THEN ct.amount ELSE 0 END) -
                       SUM(CASE WHEN ct.transaction_type='CREDIT' THEN ct.amount ELSE 0 END) AS remaining_amount
                FROM currency_transactions ct
                LEFT JOIN customers c
                    ON c.id = ct.customer_id
                   AND COALESCE(c.is_deleted, 0) = 0
                WHERE ct.tracking_no IS NOT NULL
                  AND TRIM(COALESCE(ct.tracking_no, '')) <> ''
                  AND ct.transaction_type = 'DEBIT'
                GROUP BY ct.customer_id, ct.tracking_no, c.name
                ORDER BY MAX(ct.created_at) DESC
                """,
            )
            rows = cur.fetchall()
        except Exception:
            rows = []

        for row in rows:
            try:
                if hasattr(row, "keys"):
                    job_no = str(row["tracking_no"] or "")
                    customer = str(row["customer_name"] or "")
                    desc = str(row["description"] or "")
                    amt = float(row["debit_amount"] or 0.0)
                    currency = str(row["currency"] or "TRY")
                    date_val = str(row["created_at"] or "")
                    remaining = float(row["remaining_amount"] or 0.0)
                else:
                    job_no = str(row[1] or "")
                    customer = str(row[6] or "")
                    desc = str(row[2] or "")
                    amt = float(row[3] or 0.0)
                    currency = str(row[4] or "TRY")
                    date_val = str(row[5] or "")
                    remaining = float(row[7] or 0.0) if len(row) > 7 else 0.0
            except Exception:
                continue

            status = "Tahsil Edildi" if remaining <= 0.01 else "Açık"
            note = desc

            r = self.job_table.rowCount()
            self.job_table.insertRow(r)
            self.job_table.setItem(r, 0, QTableWidgetItem(job_no))
            self.job_table.setItem(r, 1, QTableWidgetItem(customer))
            self.job_table.setItem(r, 2, QTableWidgetItem(status))
            self.job_table.setItem(r, 3, QTableWidgetItem(note))
            self.job_table.setItem(r, 4, QTableWidgetItem(f"{amt:,.2f}"))
            self.job_table.setItem(r, 5, QTableWidgetItem(self._format_tr_date(date_val)))
            self.job_table.setItem(r, 6, QTableWidgetItem(currency))
        has_rows = self.job_table.rowCount() > 0
        self.job_table.setVisible(has_rows)
        self.job_empty_state.setVisible(not has_rows)
        self.apply_job_filter()

    def load_services(self):
        self.service_table.setRowCount(0)
        cur = getattr(self.db, "cursor", None)
        if cur is None:
            return
        try:
            cur.execute("""
                SELECT tracking_no, customer_name, status, device_brand, device_model,
                       labor_cost, entry_date, exit_date, technician
                FROM devices
                WHERE COALESCE(is_deleted, 0) = 0
                ORDER BY entry_date DESC
            """)
            rows = cur.fetchall()
        except Exception:
            rows = []
        for row in rows:
            srv_no = row[0] or ""
            customer = row[1] or ""
            status = row[2] or ""
            dev = f"{row[3] or ''} {row[4] or ''}".strip()
            labor_cost = float(row[5] or 0.0)
            entry_date = row[6] or ""
            exit_date = row[7] or ""
            tech = row[8] or ""
            parts_total = 0.0
            try:
                cur.execute(
                    """
                    SELECT COALESCE(SUM(COALESCE(price, 0) * COALESCE(quantity, 1)), 0)
                    FROM used_parts
                    WHERE tracking_no=?
                      AND (is_deleted IS NULL OR is_deleted=0)
                    """,
                    (srv_no,),
                )
                parts_total = float(cur.fetchone()[0] or 0.0)
            except Exception:
                parts_total = 0.0
            total = labor_cost + parts_total
            r = self.service_table.rowCount()
            self.service_table.insertRow(r)
            self.service_table.setItem(r, 0, QTableWidgetItem(srv_no))
            self.service_table.setItem(r, 1, QTableWidgetItem(customer))
            self.service_table.setItem(r, 2, QTableWidgetItem(status))
            self.service_table.setItem(r, 3, QTableWidgetItem(dev))
            self.service_table.setItem(r, 4, QTableWidgetItem(f"{total:,.2f}"))
            self.service_table.setItem(r, 5, QTableWidgetItem(self._format_tr_date(entry_date)))
            self.service_table.setItem(r, 6, QTableWidgetItem(self._format_tr_date(exit_date)))
            self.service_table.setItem(r, 7, QTableWidgetItem(tech))
            self._set_service_actions(r, srv_no)
        has_rows = self.service_table.rowCount() > 0
        self.service_table.setVisible(has_rows)
        self.service_empty_state.setVisible(not has_rows)
        self.apply_service_filter()

    def update_stat_cards(self):
        """İstatistik kartlarını güncelle"""
        try:
            cur = getattr(self.db, "cursor", None)
            if cur is None:
                return

            # İş Takip Istatistikleri
            try:
                # Toplam İşler
                cur.execute("""
                    SELECT COUNT(DISTINCT tracking_no)
                    FROM currency_transactions
                    WHERE transaction_type = 'DEBIT'
                      AND tracking_no IS NOT NULL
                      AND TRIM(COALESCE(tracking_no, '')) <> ''
                """)
                total_jobs = cur.fetchone()[0] or 0
                labels = self.card_total_jobs.findChildren(QLabel)
                if len(labels) > 1:
                    labels[1].setText(str(total_jobs))

                # Açık İşler
                cur.execute("""
                    SELECT COUNT(DISTINCT tracking_no)
                    FROM currency_transactions
                    WHERE tracking_no IS NOT NULL
                      AND TRIM(COALESCE(tracking_no, '')) <> ''
                    GROUP BY tracking_no
                    HAVING SUM(CASE WHEN transaction_type='DEBIT' THEN amount ELSE 0 END) >
                           SUM(CASE WHEN transaction_type='CREDIT' THEN amount ELSE 0 END)
                """)
                open_groups = cur.fetchall() or []
                open_jobs = len(open_groups)
                labels = self.card_open_jobs.findChildren(QLabel)
                if len(labels) > 1:
                    labels[1].setText(str(open_jobs))

                # Tahsil Edilen İşler
                cur.execute("""
                    SELECT COUNT(DISTINCT tracking_no)
                    FROM currency_transactions
                    WHERE tracking_no IS NOT NULL
                      AND TRIM(COALESCE(tracking_no, '')) <> ''
                    GROUP BY tracking_no
                    HAVING ABS(
                        SUM(CASE WHEN transaction_type='DEBIT' THEN amount ELSE 0 END) -
                        SUM(CASE WHEN transaction_type='CREDIT' THEN amount ELSE 0 END)
                    ) <= 0.01
                """)
                paid_groups = cur.fetchall() or []
                paid_jobs = len(paid_groups)
                labels = self.card_paid_jobs.findChildren(QLabel)
                if len(labels) > 1:
                    labels[1].setText(str(paid_jobs))

                # Servis Takip Istatistikleri
                cur.execute("SELECT COUNT(*) FROM devices")
                total_services = cur.fetchone()[0] or 0
                labels = self.card_total_services.findChildren(QLabel)
                if len(labels) > 1:
                    labels[1].setText(str(total_services))

                # Tamamlanan Servisler
                cur.execute("""
                    SELECT COUNT(*) FROM devices
                    WHERE status IN ('Teslim Edildi', 'Tamir Edildi', 'Hazır')
                """)
                completed_services = cur.fetchone()[0] or 0
                labels = self.card_completed_services.findChildren(QLabel)
                if len(labels) > 1:
                    labels[1].setText(str(completed_services))

                # Toplam Tahsilat
                cur.execute("""
                    SELECT SUM(try_equivalent) FROM currency_transactions
                    WHERE transaction_type = 'CREDIT'
                """)
                total_revenue = float(cur.fetchone()[0] or 0)
                labels = self.card_total_revenue.findChildren(QLabel)
                if len(labels) > 1:
                    labels[1].setText(
                        CurrencyHelper.format_try_for_display(total_revenue, db=self.db, include_try_reference=False)
                    )

            except Exception:
                pass

        except Exception:
            pass

    def show_monthly_report(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Aylık İş / Servis Analizi")
        dlg.resize(600, 400)
        dlg.setModal(True)
        dlg.setStyleSheet(theme_qss("QDialog { background-color: @surface_alt; }"))

        vbox = QVBoxLayout(dlg)
        vbox.setContentsMargins(24, 24, 24, 24)
        vbox.setSpacing(18)

        title = QLabel("Aylık Özet")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("color: @selection_text;"))
        vbox.addWidget(title)

        desc = QLabel("Son 12 ay için gelen cihaz ve iş adetleri, kapanan servisler ve tahsilatlı işler.")
        desc.setStyleSheet(theme_qss("color: @text_muted;"))
        desc.setWordWrap(True)
        vbox.addWidget(desc)

        today = QDate.currentDate()
        cur = getattr(self.db, "cursor", None)

        rows = []
        for i in range(12):
            month_date = today.addMonths(-i)
            month_label = month_date.toString("MM.yyyy")

            srv_new = 0
            srv_done = 0
            job_paid = 0
            job_total = 0.0

            if cur is not None:
                try:
                    start = QDate(month_date.year(), month_date.month(), 1).toString("yyyy-MM-dd")
                    next_month = month_date.addMonths(1)
                    end = QDate(next_month.year(), next_month.month(), 1).toString("yyyy-MM-dd")
                    
                    # 1. Yeni Servis Kaydı
                    cur.execute(
                        "SELECT COUNT(*) FROM devices WHERE entry_date >= ? AND entry_date < ?",
                        (start, end),
                    )
                    srv_new = cur.fetchone()[0] or 0
                except Exception as e:
                    logger.error(f"JobServiceTrackingPage new services stat error: {e}")
                    srv_new = 0

                try:
                    # 2. Tamamlanan Servis
                    cur.execute(
                        "SELECT COUNT(*) FROM devices WHERE status IN ('Teslim Edildi','Tamir Edildi','Hazır') "
                        "AND COALESCE(exit_date, delivered_at, entry_date) >= ? AND COALESCE(exit_date, delivered_at, entry_date) < ?",
                        (start, end),
                    )
                    srv_done = cur.fetchone()[0] or 0
                except Exception as e:
                    logger.error(f"JobServiceTrackingPage done services stat error: {e}")
                    srv_done = 0

                try:
                    # 3. Tahsilatlı İş ve Tutar
                    # (Note: Job tracking uses currency_transactions DEBIT/CREDIT now in AYEC Pro, 
                    # but if 'Peşin Satış: JOB%' works, we keep it, or we look at currency_transactions)
                    # For safety, let's fix the SQL syntax first.
                    cur.execute(
                        "SELECT COUNT(*), SUM(amount) FROM accounting WHERE category='Tahsilat' "
                        "AND date >= ? AND date < ?",
                        (start, end),
                    )
                    res = cur.fetchone() or (0, 0.0)
                    job_paid = res[0] or 0
                    job_total = float(res[1] or 0.0)
                except Exception as e:
                    logger.error(f"JobServiceTrackingPage paid jobs stat error: {e}")
                    job_paid = 0
                    job_total = 0.0

            rows.append((month_label, srv_new, srv_done, job_paid, job_total))

        if rows:
            current = rows[0]
        else:
            current = ("", 0, 0, 0, 0.0)

        cards = QHBoxLayout()
        cards.setSpacing(12)

        def add_card(title_text, value_text, color_bg, color_fg):
            card = QFrame()
            card.setStyleSheet(theme_qss(
                f"QFrame {{ background-color: {color_bg}; border-radius: 12px; padding: 12px 16px; }} "
                "QLabel { border: none; }"
            ))
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(0, 0, 0, 0)
            c_layout.setSpacing(4)
            lbl_t = QLabel(title_text)
            lbl_t.setStyleSheet(theme_qss(f"color: {color_fg}; font-size: 11px; font-weight: 600;"))
            lbl_v = QLabel(value_text)
            lbl_v.setStyleSheet(theme_qss(f"color: {color_fg}; font-size: 18px; font-weight: 700;"))
            c_layout.addWidget(lbl_t)
            c_layout.addWidget(lbl_v)
            cards.addWidget(card)

        add_card("Bu Ay Gelen Servis", str(current[1]), tc("selection_bg"), tc("accent_pressed"))
        add_card("Bu Ay Tamamlanan Servis", str(current[2]), tc("surface_alt"), tc("success"))
        add_card("Bu Ay Tahsilatlı İş", str(current[3]), tc("warning_bg"), tc("warning"))
        add_card(
            "Bu Ay Tahsilat Tutarı",
            CurrencyHelper.format_try_for_display(current[4], db=self.db, include_try_reference=False),
            tc("warning_bg"),
            tc("warning"),
        )

        cards.addStretch()
        vbox.addLayout(cards)

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)

        header_labels = ["Ay", "Yeni Servis Kaydı", "Tamamlanan Servis", "Tahsilatlı İş", "Tahsilat Tutarı"]
        for c, text in enumerate(header_labels):
            lbl = QLabel(text)
            lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            lbl.setStyleSheet(theme_qss("color: @text_muted;"))
            grid.addWidget(lbl, 0, c)

        for row_idx, (month_label, srv_new, srv_done, job_paid, job_total) in enumerate(rows, start=1):
            lbl_month = QLabel(month_label)
            lbl_month.setStyleSheet(theme_qss("color: @selection_text;"))
            grid.addWidget(lbl_month, row_idx, 0)

            lbl_new = QLabel(str(srv_new))
            lbl_new.setStyleSheet(theme_qss("color: @accent_hover; font-weight: 600;"))
            grid.addWidget(lbl_new, row_idx, 1)

            lbl_done = QLabel(str(srv_done))
            lbl_done.setStyleSheet(theme_qss("color: @success; font-weight: 600;"))
            grid.addWidget(lbl_done, row_idx, 2)

            lbl_job = QLabel(str(job_paid))
            lbl_job.setStyleSheet(theme_qss("color: @warning; font-weight: 600;"))
            grid.addWidget(lbl_job, row_idx, 3)

            lbl_total = QLabel(f"{job_total:,.2f}")
            lbl_total.setStyleSheet(theme_qss("color: @selection_text; font-weight: 600;"))
            grid.addWidget(lbl_total, row_idx, 4)

        vbox.addLayout(grid)

        close_row = QHBoxLayout()
        close_row.addStretch()
        btn_close = QPushButton("Kapat")
        btn_close.setFixedHeight(34)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        try:
            btn_close.setStyleSheet(theme_qss(DesignTokens.get_button_qss("outline", size="sm")))
        except Exception:
            btn_close.setStyleSheet(theme_qss(
                "QPushButton { background-color: @border; color: @selection_text; border-radius: 8px; padding: 6px 16px; "
                "border: 1px solid @border; } QPushButton:hover { background-color: @border; }"
            ))
        btn_close.clicked.connect(dlg.accept)
        close_row.addWidget(btn_close)
        vbox.addLayout(close_row)

        dlg.exec()

    def on_job_context_menu(self, pos):
        if not is_context_menu_enabled(self.db, page_id=201):
            return
        index = self.job_table.indexAt(pos)
        if not index.isValid():
            return
        row = index.row()
        self.job_table.selectRow(row)
        job_no_item = self.job_table.item(row, 0)
        if not job_no_item:
            pass # Keep logic intact if they were just read for some side effect, or just read the item. Actually, better just remove the assignment.
        menu = QMenu(self)
        menu.setStyleSheet(theme_qss("""
            QMenu { background-color: @surface; border: 1px solid @border; padding: 4px; }
            QMenu::item { padding: 8px 18px; color: @selection_text; }
            QMenu::item:selected { background-color: @accent_hover; color: @surface; }
        """))
        act_detail = menu.addAction("🔍 İş Detayı")
        action = menu.exec(self.job_table.viewport().mapToGlobal(pos))
        if action != act_detail:
            return
        try:
            self._open_job_detail(row)
        except Exception as e:
            logger.error(f"Archive action failed: {e}")

    def on_service_context_menu(self, pos):
        if not is_context_menu_enabled(self.db, page_id=201):
            return
        index = self.service_table.indexAt(pos)
        if not index.isValid():
            return
        row = index.row()
        self.service_table.selectRow(row)
        item_tracking = self.service_table.item(row, 0)
        tracking_no = item_tracking.text() if item_tracking else ""
        menu = QMenu(self)
        menu.setStyleSheet(theme_qss("""
            QMenu { background-color: @surface; border: 1px solid @border; padding: 4px; }
            QMenu::item { padding: 8px 18px; color: @selection_text; }
            QMenu::item:selected { background-color: @accent_hover; color: @surface; }
        """))
        act_detail = menu.addAction("🔍 Detay")
        act_panel = menu.addAction("🛠️ Teknisyen Paneli")
        act_form = menu.addAction("📝 Servis Formu")
        action = menu.exec(self.service_table.viewport().mapToGlobal(pos))
        if not tracking_no:
            return
        try:
            if action == act_detail:
                self._open_service_archive_detail(tracking_no)
            elif action == act_panel and self.main_window is not None and hasattr(self.main_window, "open_technician_panel"):
                self.main_window.open_technician_panel(tracking_no)
            elif action == act_form and self.main_window is not None and hasattr(self.main_window, "open_service_form"):
                self.main_window.open_service_form(tracking_no)
        except Exception as e:
            logger.error(f"Archive action failed: {e}")


