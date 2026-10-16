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
from math import isfinite
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import QEvent, Qt, QTimer, QSize, pyqtSignal, QFileInfo
from PyQt6.QtGui import QColor, QCursor, QFont, QIcon, QPainter, QPixmap, QPageLayout, QTextDocument, QPdfWriter
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QGridLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyledItemDelegate,
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
from src.ui.widgets.modern_inputs import ModernComboBox
from src.ui.widgets.financial_reference_controls import FinancialMetricGlyph, FinancialReferenceActionButton
from src.utils.theme_colors import tc, theme_qss
from src.utils.toast_notification import show_error, show_info, show_success, show_warning


class _ServiceListCompactDelegate(QStyledItemDelegate):
    def __init__(self, kind, parent=None):
        super().__init__(parent)
        self.kind = kind

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        value = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
        if self.kind == "tracking":
            option.text = value.replace("-", "-\n", 2)
        elif self.kind == "date" and "-" in value:
            year, remainder = value.split("-", 1)
            option.text = year + "-\n" + remainder
        elif self.kind == "price" and " " in value:
            amount, currency = value.rsplit(" ", 1)
            option.text = amount + "\n" + currency
        option.textElideMode = Qt.TextElideMode.ElideNone
        option.font.setFamily(DesignTokens.MONO_FONT_NAME)
        option.font.setPixelSize(9 if self.kind in {"date", "price"} else 10)
        if self.kind == "price":
            option.displayAlignment = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter


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
        self._page_size = 15
        self._all_records: List[Dict[str, Any]] = []
        self._filtered_records: List[Dict[str, Any]] = []

        # Chip button map
        self._chip_buttons: Dict[str, QPushButton] = {}
        self._reference_kpi_values = []

        self.init_ui()
        QTimer.singleShot(50, self.refresh_data)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.Resize and watched is getattr(self, "table", None):
            QTimer.singleShot(0, self._fit_reference_table_columns)
            QTimer.singleShot(0, self._fit_reference_table_height)
        if event.type() == QEvent.Type.MouseButtonPress:
            row = watched.property("serviceRow") if hasattr(watched, "property") else None
            if row is not None:
                try:
                    self.table.selectRow(int(row))
                except (AttributeError, TypeError, ValueError):
                    pass
        return super().eventFilter(watched, event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_reference_filter_controls()
        if hasattr(self, "table"):
            QTimer.singleShot(0, self._fit_reference_table_columns)

    def _fit_reference_filter_controls(self):
        if self.main_window is None or not hasattr(self, "combo_status"):
            return
        compact = self.width() < 850
        controls = (self.combo_status, self.combo_date, self.combo_priority)
        for control in controls:
            if not hasattr(control, "_reference_original_style"):
                control._reference_original_style = control.styleSheet()
            style = control._reference_original_style
            if compact:
                style = style.replace("min-width: 140px", "min-width: 105px")
                style = style.replace("min-width: 112px", "min-width: 84px")
            control.setStyleSheet(style)
        self.search_input.setMinimumWidth(150 if compact else 0)

    def _fit_reference_table_columns(self):
        if not hasattr(self, "table") or self.table.width() <= 0:
            return
        available = self.table.viewport().width()
        if self.main_window is None:
            return
        if available <= 820:
            widths = [26, 58, 70, 80, 56, 50, 50, 76, 58, max(188, available - 524)]
            compact_headers = [
                "", "TAK\u0130P\nNO", "M\u00dc\u015eTER\u0130", "C\u0130HAZ /\nMODEL",
                "KABUL\nTAR\u0130H\u0130", "TESL\u0130M\nTAR\u0130H\u0130", "\u00dcCRET",
                "DURUM", "AC\u0130L\u0130YET", "\u0130\u015eLEMLER",
            ]
        else:
            ratios = (0.04, 0.085, 0.095, 0.11, 0.09, 0.09, 0.07, 0.105, 0.07, 0.245)
            minimums = (24, 48, 58, 64, 54, 54, 48, 60, 42, 140)
            widths = [max(minimum, int(available * ratio)) for ratio, minimum in zip(ratios, minimums)]
            overflow = sum(widths) - available
            for index in (9, 3, 2, 7, 1, 4, 5, 6, 8, 0):
                if overflow <= 0:
                    break
                reducible = max(0, widths[index] - minimums[index])
                reduction = min(reducible, overflow)
                widths[index] -= reduction
                overflow -= reduction
            compact_headers = self._reference_headers
        header = self.table.horizontalHeader()
        if getattr(self, "_reference_compact_headers_active", None) != (available <= 820):
            self.table.setHorizontalHeaderLabels(compact_headers)
            header.setFixedHeight(40 if available <= 820 else 42)
            self._reference_compact_headers_active = available <= 820
        for index, width in enumerate(widths):
            self.table.setColumnWidth(index, width)
        for row in range(self.table.rowCount()):
            self.table.setRowHeight(row, max(70 if self.main_window is not None else 74,
                                              self.table.rowHeight(row)))
        self._fit_reference_table_height()

    def _install_row_selection(self, widget, row_idx):
        widget.setProperty("serviceRow", int(row_idx))
        widget.installEventFilter(self)
        return widget

    def init_ui(self):
        self.setObjectName("ServiceListPage")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(theme_qss("background-color: @finance_canvas;"))

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 8 if self.main_window is not None else 0, 12 if self.main_window is not None else 0, 0)
        main_layout.setSpacing(8)

        # 1. Top Header
        self._create_header(main_layout)

        # 1b. Compact reference KPI strip.
        self._create_reference_kpis(main_layout)

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
        self._create_reference_footer(main_layout)
        self.reference_summary_frame.setVisible(self.main_window is None)
        main_layout.addStretch(0)

    def _create_reference_kpis(self, parent_layout):
        strip = QFrame(self)
        strip.setStyleSheet(theme_qss("background: transparent; border: none;"))
        grid = QGridLayout(strip)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(8)
        items = [
            ("Aktif Tamirde", "--", "@service_kpi_active", "repair"),
            ("Par\u00e7a Bekleyen", "--", "@service_kpi_parts", "hourglass"),
            ("Teslime Haz\u0131r", "--", "@service_kpi_ready", "collection"),
            ("Kargo Sevkiyat", "--", "@service_kpi_cargo", "truck"),
            ("Tahmini Ciro", "--", "@service_kpi_revenue", "wallet"),
            ("Ort. \u00c7\u00f6z\u00fcm S\u00fcresi", "--", "@service_kpi_duration", "clock"),
        ]
        self._reference_kpi_values = []
        self._reference_kpi_notes = []
        self._reference_kpi_pills = []
        reference_host = self.main_window is not None
        notes = (
            "At\u00f6lyede \u0130\u015flemde", "Normal Ak\u0131\u015f", "WhatsApp",
            "Kurye \u00c7a\u011fr\u0131ld\u0131", "Kay\u0131tl\u0131 Tutar", "Ayn\u0131 G\u00fcn Teslim",
        )
        for index, (title, value, accent, glyph) in enumerate(items):
            card = QFrame(strip)
            card.setObjectName("ServiceKpiCard")
            card.setStyleSheet(theme_qss(
                "QFrame#ServiceKpiCard { background: @finance_surface; "
                "border: 1px solid @finance_outline; border-radius: 6px; }"
                if reference_host else
                "QFrame#ServiceKpiCard { background: @finance_surface; border: none; border-radius: 4px; }"
            ))
            box = QVBoxLayout(card)
            box.setContentsMargins(8, 6 if reference_host else 5, 8, 6 if reference_host else 5)
            box.setSpacing(2)
            card.setFixedHeight(114)
            label = QLabel(title.upper() if reference_host else title)
            label.setWordWrap(True)
            label.setMinimumWidth(0)
            label.setStyleSheet(theme_qss(
                f"color: @finance_text_muted; font-size: {10 if reference_host else 11}px; "
                "font-weight: 700; border: none; background: transparent;"
            ))
            amount = QLabel(value)
            amount.setStyleSheet(theme_qss(
                f"color: {'@finance_text' if reference_host else accent}; "
                "font-size: 18px; font-weight: 900; border: none;"
            ))
            title_row = QHBoxLayout()
            title_row.setSpacing(4)
            title_row.addWidget(label, 1)
            icon = FinancialMetricGlyph(glyph, accent.lstrip("@"))
            if reference_host:
                icon_box = QFrame(card)
                icon_box.setFixedSize(26, 26)
                icon_box.setStyleSheet(theme_qss(
                    f"background: @finance_active_bg; border: 1px solid {accent}; border-radius: 5px;"
                ))
                icon_layout = QHBoxLayout(icon_box)
                icon_layout.setContentsMargins(3, 3, 3, 3)
                icon_layout.addWidget(icon)
                title_row.addWidget(icon_box)
            else:
                title_row.addWidget(icon)
            box.addLayout(title_row)
            box.addWidget(amount)
            if reference_host:
                if index == 0:
                    self._reference_kpi_capacity = QProgressBar(card)
                    self._reference_kpi_capacity.setTextVisible(False)
                    self._reference_kpi_capacity.setFixedHeight(5)
                    self._reference_kpi_capacity.setRange(0, 100)
                    self._reference_kpi_capacity.setStyleSheet(theme_qss(
                        "QProgressBar { background: @finance_surface_high; border: none; border-radius: 2px; } "
                        "QProgressBar::chunk { background: @service_kpi_active; border-radius: 2px; }"
                    ))
                    box.addWidget(self._reference_kpi_capacity)
                foot_row = QHBoxLayout()
                foot_row.setSpacing(3)
                note = QLabel(notes[index], card)
                note.setWordWrap(True)
                note.setMinimumWidth(0)
                note.setStyleSheet(theme_qss(
                    "color: @finance_text_muted; font-size: 9px; border: none; background: transparent;"
                ))
                pill = QLabel("--", card)
                pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
                pill.setStyleSheet(theme_qss(
                    f"color: {accent}; background: @finance_active_bg; "
                    f"border: 1px solid {accent}; border-radius: 3px; font-size: 9px; padding: 1px 3px;"
                ))
                foot_row.addWidget(note, 1)
                foot_row.addWidget(pill)
                box.addLayout(foot_row)
                self._reference_kpi_notes.append(note)
                self._reference_kpi_pills.append(pill)
            self._reference_kpi_values.append(amount)
            grid.addWidget(card, 0, index)
        parent_layout.addWidget(strip)

    def _update_reference_kpis(self):
        records = self._all_records
        active = sum(1 for rec in records if (
            str(rec.get("status") or "").casefold() in {
                "tamirde", "onar\u0131mda", "i\u015flemde", "serviste"
            }
            if self.main_window is not None else is_active_device_status(rec.get("status"))
        ))
        parts = sum(1 for rec in records if normalize_device_status(rec.get("status")) == "Par\u00e7a Bekliyor")
        ready = sum(1 for rec in records if normalize_device_status(rec.get("status")) == "Teslime Hazir")
        cargo = sum(1 for rec in records if str(rec.get("delivery_type") or "").casefold() in {"kargo", "cargo"})
        revenue = 0.0
        durations = []
        delivered_today = 0
        today = datetime.now().date()
        for record in records:
            try:
                amount = float(record.get("price") or 0)
                if isfinite(amount):
                    revenue += amount
            except (ValueError, TypeError):
                pass
            entry_date = self._reference_date(record.get("entry_date"))
            exit_date = self._reference_date(record.get("exit_date"))
            status = normalize_device_status(record.get("status"))
            if status in {"Teslim Edildi", "Teslim", "Tamir Edildi"} and entry_date and exit_date and exit_date >= entry_date:
                durations.append((exit_date - entry_date).days)
            if status in {"Teslim Edildi", "Teslim"} and exit_date == today:
                delivered_today += 1
        average = f"{sum(durations) / len(durations):.1f} G\u00fcn" if durations else "Veri yok"
        revenue_text = CurrencyHelper.format_amount(revenue, db=self.db)
        values = [f"{active} Cihaz", f"{parts} Cihaz", f"{ready} Cihaz", f"{cargo} Paket", revenue_text, average]
        for label, value in zip(self._reference_kpi_values, values):
            display_value = value
            if self.main_window is not None:
                display_value = value.replace(".00 ", " ")
                if value == "Veri yok":
                    display_value = "0.0 G\u00fcn"
            label.setText(display_value)
            label.setToolTip(value)
        if self.main_window is not None:
            capacity = min(100, round(active * 100 / max(1, len(records))))
            critical = sum(
                1 for rec in records
                if str(rec.get("urgency") or rec.get("priority") or "").casefold()
                in {"acil", "y\u00fcksek"}
            )
            delivered = sum(
                1 for rec in records
                if normalize_device_status(rec.get("status")) in {"Teslim Edildi", "Teslim"}
            )
            sla = round(delivered * 100 / max(1, len(records)))
            try:
                revenue_goal = float(self.db.get_setting("service_revenue_target", "0") or 0)
            except (TypeError, ValueError, AttributeError):
                revenue_goal = 0
            goal_label = (
                "Hedef: " + CurrencyHelper.format_amount(revenue_goal, db=self.db).replace(".00 ", " ")
                if revenue_goal > 0 else "Hedef: --"
            )
            pills = (
                f"%{capacity} Kapasite", f"Kritik: {critical}", f"{ready} Bekleyen",
                f"{cargo} / {max(4, cargo)} Sevk", goal_label, f"%{sla} SLA",
            )
            for label, value in zip(self._reference_kpi_pills, pills):
                label.setText(value)
            self._reference_kpi_capacity.setValue(capacity)
        footer_values = [str(len(records)), average, f"{delivered_today} Cihaz", revenue_text]
        for label, value in zip(getattr(self, "_reference_footer_values", []), footer_values):
            label.setText(value)

    @staticmethod
    def _reference_date(value):
        if not value:
            return None
        text = str(value).strip()
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
        except ValueError:
            for format_string in ("%d.%m.%Y", "%d/%m/%Y"):
                try:
                    return datetime.strptime(text, format_string).date()
                except ValueError:
                    continue
        return None

    def _create_reference_footer(self, parent_layout):
        frame = QWidget(self)
        self.reference_summary_frame = frame
        frame.setObjectName("ServiceReferenceSummary")
        frame.setFixedHeight(84)
        frame.setStyleSheet("background: transparent; border: none;")
        grid = QHBoxLayout(frame)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(8)
        summary = QFrame(frame)
        summary.setObjectName("ServiceMovementSummary")
        summary.setStyleSheet(theme_qss(
            "QFrame#ServiceMovementSummary { background: @finance_surface; "
            "border: none; border-radius: 6px; }"
        ))
        summary_box = QVBoxLayout(summary)
        summary_box.setContentsMargins(8, 8, 8, 8)
        summary_box.setSpacing(6)
        heading = QLabel("Son Servis Hareketleri \u00d6zeti", summary)
        heading.setStyleSheet(theme_qss(
            "color: @finance_text; font-size: 14px; font-weight: 700; border: none; background: transparent;"
        ))
        summary_box.addWidget(heading)
        cards = QHBoxLayout()
        cards.setSpacing(4)
        summary_box.addLayout(cards)
        grid.addWidget(summary, 2)
        self._reference_footer_values = []
        items = [("Toplam Kay\u0131t", "--"), ("Ort. \u00c7\u00f6z\u00fcm S\u00fcresi", "--"), ("Bug\u00fcnk\u00fc Teslimatlar", "--"), ("Kay\u0131tl\u0131 Servis Tutar\u0131", "--")]
        for index, (title, value) in enumerate(items):
            card = QFrame(frame)
            card.setObjectName("ServiceSummaryCard" + str(index))
            card.setStyleSheet(theme_qss(
                "QFrame#ServiceSummaryCard" + str(index) + " { background: @finance_surface_alt; "
                "border: none; border-radius: 4px; }"
            ))
            box = QVBoxLayout(card)
            box.setContentsMargins(10, 6, 10, 6)
            title_label = QLabel(title)
            title_label.setStyleSheet(theme_qss("color: @finance_text_muted; font-size: 10px; border: none;"))
            value_label = QLabel(value)
            value_label.setStyleSheet(theme_qss("color: @finance_text; font-size: 14px; font-weight: 700; border: none; background: transparent;"))
            title_label.setStyleSheet(theme_qss("color: @finance_text_muted; font-size: 10px; border: none; background: transparent;"))
            box.addWidget(title_label)
            box.addWidget(value_label)
            if index < 3:
                cards.addWidget(card, 1)
            else:
                card.setStyleSheet(theme_qss(
                    "QFrame#ServiceSummaryCard3 { background: @finance_surface; "
                    "border: none; border-left: 3px solid @finance_secondary; border-radius: 6px; }"
                ))
                box.addStretch(1)
                note = QLabel("Mevcut servis kay\u0131tlar\u0131", card)
                note.setStyleSheet(theme_qss("color: @finance_text_muted; font-size: 10px; border: none; background: transparent;"))
                box.addWidget(note)
                grid.addWidget(card, 1)
            self._reference_footer_values.append(value_label)
        parent_layout.addWidget(frame)

    def _create_header(self, parent_layout: QVBoxLayout):
        header_widget = QFrame(self)
        header_widget.setObjectName("ServiceListHeader")
        header_widget.setFixedHeight(82)
        header_widget.setStyleSheet(theme_qss(
            "QFrame#ServiceListHeader { background: @finance_surface; "
            "border: 1px solid @finance_outline; border-radius: 6px; }"
        ))
        reference_host = self.main_window is not None
        h_layout = QVBoxLayout(header_widget) if reference_host else QHBoxLayout(header_widget)
        h_layout.setContentsMargins(10, 7, 10, 5) if reference_host else h_layout.setContentsMargins(12, 8, 12, 8)
        h_layout.setSpacing(4 if reference_host else 8)
        buttons_layout = QHBoxLayout() if reference_host else h_layout
        if reference_host:
            buttons_layout.setSpacing(6)

        # Title & subtitle
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        self.lbl_title = QLabel("Servis Listesi")
        self.lbl_title.setStyleSheet(theme_qss(
            f"font-size: {18 if reference_host else 23}px; font-weight: 900; "
            "color: @finance_text; border: none; background: transparent;"
        ))

        self.lbl_subtitle = QLabel(
            "T\u00fcm teknik servis ve onar\u0131m kay\u0131tlar\u0131n\u0131 tek ekrandan "
            "y\u00f6netin, filtreleyin ve yazd\u0131r\u0131n."
        )
        self.lbl_subtitle.setStyleSheet(theme_qss(
            f"font-size: {10 if reference_host else 12}px; color: @finance_text_muted; "
            "border: none; background: transparent;"
        ))

        title_line = QHBoxLayout()
        title_line.setSpacing(6)
        header_glyph = FinancialMetricGlyph(
            "repair", "finance_primary_text" if reference_host else "finance_text",
            glyph_size=18 if reference_host else 24,
        )
        if reference_host:
            icon_box = QFrame(header_widget)
            icon_box.setFixedSize(30, 30)
            icon_box.setStyleSheet(theme_qss(
                "background: @finance_primary; border: none; border-radius: 5px;"
            ))
            icon_layout = QHBoxLayout(icon_box)
            icon_layout.setContentsMargins(6, 6, 6, 6)
            icon_layout.addWidget(header_glyph)
            title_line.addWidget(icon_box)
            title_line.addWidget(self.lbl_title)
            self.lbl_live_data = QLabel("\u25cf CANLI VER\u0130", header_widget)
            self.lbl_live_data.setStyleSheet(theme_qss(
                "color: @finance_secondary; background: @finance_success_bg; "
                "border: 1px solid @finance_secondary; border-radius: 7px; "
                "font-size: 9px; font-weight: 800; padding: 1px 5px;"
            ))
            title_line.addWidget(self.lbl_live_data)
            title_line.addStretch()
        else:
            title_line.addWidget(header_glyph)
            title_line.addWidget(self.lbl_title, 1)
        title_box.addLayout(title_line)
        title_box.addWidget(self.lbl_subtitle)
        h_layout.addLayout(title_box)
        if reference_host:
            h_layout.addLayout(buttons_layout)
        else:
            h_layout.addStretch()

        if reference_host:
            self.btn_refresh = QPushButton("\u21bb  Yenile")
            self.btn_refresh.setFixedHeight(24)
            self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_refresh.setStyleSheet(theme_qss(
                "QPushButton { background: @finance_surface_high; color: @finance_text; "
                "border: none; border-radius: 4px; padding: 0 8px; font-size: 10px; }"
            ))
            self.btn_refresh.clicked.connect(self.refresh_data)
            buttons_layout.addWidget(self.btn_refresh)

        self.btn_bulk_actions = QPushButton("Toplu \u0130\u015flemler")
        self.btn_bulk_actions.setFixedHeight(28)
        self.btn_bulk_actions.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_bulk_actions.setToolTip("Bu sayfadaki se\u00e7ili servis kay\u0131tlar\u0131")
        self.btn_bulk_actions.setStyleSheet(theme_qss("background: @finance_surface_high; color: @finance_text; border: none; border-radius: 4px; padding: 0 12px; font-size: 11px; font-weight: 700;"))
        self.reference_bulk_menu = QMenu(self.btn_bulk_actions)
        self.reference_bulk_menu.addAction("Se\u00e7ili kay\u0131tlar\u0131 d\u0131\u015fa aktar", self._export_selected_services)
        self.reference_bulk_menu.addAction("Se\u00e7ili servis fi\u015flerini yazd\u0131r", self._print_selected_services)
        self.reference_bulk_menu.addSeparator()
        self.reference_bulk_menu.addAction("Bu sayfan\u0131n t\u00fcm\u00fcn\u00fc se\u00e7", lambda: self._set_visible_service_selection(True))
        self.reference_bulk_menu.addAction("Se\u00e7imi kald\u0131r", lambda: self._set_visible_service_selection(False))
        self.btn_bulk_actions.setMenu(self.reference_bulk_menu)
        buttons_layout.addWidget(self.btn_bulk_actions)

        # Right Action Buttons: "+ Cihaz Ekle" and "Dışa Aktar"
        self.btn_add_device = QPushButton("+ Cihaz Ekle")
        self.btn_add_device.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_device.setFixedHeight(36)
        self.btn_add_device.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: #2563EB;
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 800;
                border: none;
                border-radius: 6px;
                padding: 0 14px;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
            QPushButton:pressed {
                background-color: #1E40AF;
            }
        """))
        self.btn_add_device.clicked.connect(self.open_service_form_shortcut)

        self.btn_export = QPushButton("D\u0131\u015fa Aktar (Excel/PDF)")
        self.btn_export.setToolTip("Excel, CSV veya PDF olarak d\u0131\u015fa aktar")
        self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export.setFixedHeight(36)
        self.btn_export.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @surface;
                color: @text;
                font-size: 13px;
                font-weight: 700;
                border: 1px solid @border;
                border-radius: 6px;
                padding: 0 14px;
            }
            QPushButton:hover {
                background-color: @hover_bg;
                border-color: @accent;
            }
        """))
        self.btn_export.clicked.connect(self.export_records)
        self.btn_add_device.setFixedHeight(28)
        self.btn_add_device.setStyleSheet(theme_qss("background: @finance_primary; color: @finance_primary_text; border: none; border-radius: 4px; padding: 0 12px; font-size: 11px; font-weight: 700;"))
        self.btn_export.setFixedHeight(28)
        self.btn_export.setStyleSheet(theme_qss("background: @finance_surface_high; color: @finance_text; border: none; border-radius: 4px; padding: 0 12px; font-size: 11px; font-weight: 700;"))
        if reference_host:
            for button in (self.btn_bulk_actions, self.btn_export, self.btn_add_device):
                button.setFixedHeight(24)
        buttons_layout.addWidget(self.btn_export)
        buttons_layout.addWidget(self.btn_add_device)
        if reference_host:
            buttons_layout.addStretch()

        parent_layout.addWidget(header_widget)

    def _create_filter_chips(self, parent_layout: QVBoxLayout):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(32)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        chip_container = QWidget()
        chip_container.setStyleSheet("background: transparent;")
        c_layout = QHBoxLayout(chip_container)
        c_layout.setContentsMargins(0, 2, 0, 2)
        c_layout.setSpacing(4)

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
            btn.setFixedHeight(24)
            btn.setCheckable(True)
            btn.setChecked(key == self.current_filter_category)
            btn.setProperty("chipKey", key)
            btn.setStyleSheet(self._chip_style(key == self.current_filter_category))
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
                    background-color: @finance_action_collection;
                    color: @finance_action_collection_text;
                    font-size: 10px;
                    font-weight: 800;
                    border: none;
                    border-radius: 4px;
                    padding: 0 6px;
                }
            """)
        return theme_qss("""
            QPushButton {
                background-color: @finance_surface_high;
                color: @finance_text;
                font-size: 10px;
                font-weight: 700;
                border: none;
                border-radius: 4px;
                padding: 0 6px;
            }
            QPushButton:hover {
                background-color: @hover_bg;
                border-color: @accent;
            }
        """)

    def _create_filter_bar(self, parent_layout: QVBoxLayout):
        bar = QFrame(self)
        bar.setObjectName("serviceReferenceFilterBar")
        bar.setStyleSheet(theme_qss("""
            QFrame {
                background-color: @surface;
                border: 1px solid @border;
                border-radius: 12px;
            }
        """))
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(6, 3 if self.main_window is not None else 6,
                                  6, 3 if self.main_window is not None else 6)
        layout.setSpacing(6)

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
        self.combo_status = ModernComboBox()
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
        self.combo_date = ModernComboBox()
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
        if self.main_window is not None:
            self.combo_date.setCurrentIndex(self.combo_date.findData("last_30"))
        self.combo_date.currentIndexChanged.connect(self._on_combo_filter_changed)
        layout.addWidget(self.combo_date, 1)

        self.combo_priority = ModernComboBox()
        self.combo_priority.setFixedHeight(36)
        self.combo_priority.setStyleSheet(theme_qss("""
            QComboBox {
                background-color: @surface_alt;
                color: @text;
                font-size: 12px;
                font-weight: 700;
                border: 1px solid @border;
                border-radius: 8px;
                padding: 0 12px;
                min-width: 112px;
            }
            QComboBox::drop-down { border: none; }
        """))
        self.combo_priority.addItem("Oncelik: Tum", "all")
        self.combo_priority.addItem("Normal", "Normal")
        self.combo_priority.addItem("Acil", "Acil")
        self.combo_priority.currentIndexChanged.connect(self._on_combo_filter_changed)
        layout.addWidget(self.combo_priority, 1)

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

        bar.setStyleSheet(theme_qss("QFrame#serviceReferenceFilterBar { background: @finance_surface; border: 1px solid @finance_outline; border-radius: 4px; }"))
        for control in (self.search_input, self.combo_status, self.combo_date, self.combo_priority):
            control.setFixedHeight(28)
            control.setStyleSheet(theme_qss("QLineEdit, QComboBox { background: @finance_canvas; color: @finance_text; border: 1px solid @finance_outline; border-radius: 4px; padding: 3px 6px; font-size: 10px; } QComboBox::drop-down { border: none; width: 20px; }"))
            if isinstance(control, ModernComboBox):
                control.set_reference_chevron()
        btn_filter.setFixedHeight(28)
        btn_filter.setStyleSheet(theme_qss("background: @finance_primary; color: @finance_primary_text; border: none; border-radius: 4px; padding: 3px 12px; font-size: 10px; font-weight: 700;"))
        btn_clear.setFixedHeight(28)
        btn_clear.setStyleSheet(theme_qss("background: @finance_surface_high; color: @finance_text; border: none; border-radius: 4px; padding: 3px 12px; font-size: 10px; font-weight: 700;"))

        parent_layout.addWidget(bar)

    def _create_action_bar(self, parent_layout: QVBoxLayout):
        bar = QFrame(self)
        bar.setObjectName("ServiceQuickActions")
        bar.setFixedHeight(26 if self.main_window is not None else 32)
        bar.setStyleSheet(theme_qss("QFrame#ServiceQuickActions { background: @finance_canvas; border: none; border-radius: 4px; }"))
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(6, 1 if self.main_window is not None else 4,
                                  6, 1 if self.main_window is not None else 4)
        layout.setSpacing(4)

        actions = [
            ("Servis Ge\u00e7mi\u015fi", "clock", self._action_service_history),
            ("Detayl\u0131 Fi\u015f Yazd\u0131r", "print", self._action_print_detail),
            ("Kargo Fi\u015fi Yazd\u0131r", "truck", self._action_print_cargo),
            ("E-\u0130rsaliye", "pdf", self._action_dispatch_note),
            ("E-Fatura", "excel", self._action_e_invoice),
            ("WhatsApp Bildirim", "pending", self._action_whatsapp),
        ]

        self.reference_quick_actions = []
        for text, glyph, callback in actions:
            btn = FinancialReferenceActionButton(text, glyph, bar, stacked=False)
            btn.setAccessibleName(text)
            btn.setToolTip(text)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(24)
            btn.setStyleSheet(theme_qss("""
                QPushButton {
                    background-color: @finance_surface_high;
                    color: @finance_text;
                    font-size: 11px;
                    font-weight: 700;
                    border: none;
                    border-radius: 4px;
                    padding: 0 6px 0 28px;
                }
                QPushButton:hover {
                    background-color: @finance_active_bg;
                }
            """))
            label_width = btn.fontMetrics().horizontalAdvance(text)
            btn.setMinimumWidth(max(btn.sizeHint().width(), label_width + 34))
            btn.clicked.connect(callback)
            layout.addWidget(btn)
            self.reference_quick_actions.append(btn)

        layout.addStretch()
        parent_layout.addWidget(bar)

    def _action_whatsapp(self):
        tracking_no = self._get_selected_tracking_no()
        if tracking_no:
            self.open_context_menu_action("whatsapp", tracking_no)

    def _create_table_widget(self, parent_layout: QVBoxLayout):
        wrapper = QFrame(self)
        self.reference_table_wrapper = wrapper
        wrapper.setObjectName("ServiceListTableWrapper")
        wrapper.setStyleSheet(theme_qss("""
            QFrame#ServiceListTableWrapper {
                background-color: @finance_surface;
                border: 1px solid @finance_outline;
                border-radius: 6px;
            }
        """))
        wrap_layout = QVBoxLayout(wrapper)
        wrap_layout.setContentsMargins(0, 0, 0, 0)
        wrap_layout.setSpacing(0)

        self.table = QTableWidget(0, 10, wrapper)
        self.table.setMinimumWidth(0)
        if self.main_window is not None:
            for column, kind in ((1, "tracking"), (4, "date"), (5, "date"), (6, "price")):
                self.table.setItemDelegateForColumn(
                    column, _ServiceListCompactDelegate(kind, self.table)
                )
        self.table.installEventFilter(self)
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
        self._reference_headers = headers
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setAlternatingRowColors(True)
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
        header.setFixedHeight(38 if self.main_window is not None else 32)
        header.setMinimumSectionSize(20)
        header.setStretchLastSection(False)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 32)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 112)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 100)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 108)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 104)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 104)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(6, 90)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(7, 124)
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(8, 68)
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(9, 224)

        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(64)
        self.table.setWordWrap(True)
        self.table.setTextElideMode(Qt.TextElideMode.ElideRight)

        self.table.setStyleSheet(theme_qss("""
            QTableWidget#ServiceListTable {
                background-color: @finance_surface;
                alternate-background-color: @finance_surface_container;
                color: @finance_text;
                border: none;
                border-radius: 0px;
                gridline-color: transparent;
            }
            QTableWidget#ServiceListTable::item {
                padding: 6px 8px;
                background-color: @finance_surface;
                border: none;
            }
            QTableWidget#ServiceListTable::item:alternate { background-color: @finance_surface_container; }
            QTableWidget#ServiceListTable::item:selected {
                background-color: @finance_active_bg;
                color: @finance_text;
            }
            QHeaderView::section {
                background-color: @finance_canvas;
                color: @finance_text_muted;
                font-size: 11px;
                font-weight: 800;
                border: none;
                padding: 10px 8px;
                letter-spacing: 0.5px;
            }
        """))

        wrap_layout.addWidget(self.table)
        parent_layout.addWidget(wrapper, 1)

    def _create_pagination_footer(self, parent_layout: QVBoxLayout):
        footer = QWidget(self)
        footer.setStyleSheet(theme_qss(
            "background: @finance_surface_high; border: none; border-top: 1px solid @finance_outline;"
            if self.main_window is not None else "background: transparent; border: none;"
        ))
        if self.main_window is not None:
            footer.setFixedHeight(42)
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
        self.combo_page_size.setCurrentIndex(self.combo_page_size.findData(15))
        self.combo_page_size.currentIndexChanged.connect(self._on_page_size_changed)
        layout.addWidget(self.combo_page_size)

        # Pagination buttons container
        self.page_btn_container = QWidget()
        self.page_btn_container.setStyleSheet("background: transparent;")
        self.page_btn_layout = QHBoxLayout(self.page_btn_container)
        self.page_btn_layout.setContentsMargins(0, 0, 0, 0)
        self.page_btn_layout.setSpacing(4)
        layout.addWidget(self.page_btn_container)

        if self.main_window is not None:
            self.reference_pagination_footer = footer
            parent_layout.removeWidget(footer)
            footer.setParent(self.reference_table_wrapper)
            self.reference_table_wrapper.layout().addWidget(footer)
            self._fit_reference_table_height()
        else:
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
            btn.setChecked(is_active)
            btn.setStyleSheet(self._chip_style(is_active))
        self._apply_all_filters()

    def show_service_list(self, category="all"):
        """External entry point: set filter category and update UI immediately."""
        self.set_filter_category(category)

    def refresh_data(self):
        """Fetch records from database and refresh table."""
        self._fetch_records()
        self._update_reference_kpis()
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
            "tracking_no", "customer_name", "customer_phone", "customer_contact", "company_name",
            "device_type", "device_brand", "device_model", "serial_no", "fault_description",
            "entry_date", "exit_date", "estimated_date", "price", "labor_cost",
            "status", "urgency", "approval_status", "payment_status",
            "service_source", "delivery_type", "is_invoiced",
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
        order_fields = (["id"] if "id" in cols else []) + [field for field in ("entry_date", "tracking_no") if field in cols]
        if order_fields:
            query += " ORDER BY " + ", ".join(field + " DESC" for field in order_fields)

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
        invoice_flags = ServiceListPage._read_service_invoice_flags(read_cursor)
        for record in records:
            record.setdefault("is_invoiced", invoice_flags.get(str(record.get("tracking_no") or ""), False))
        self._all_records = records

    @staticmethod
    def _read_service_invoice_flags(read_cursor):
        """Read the existing invoice workflow flags; never create billing state."""
        flags = {}
        for table, kind_column, kind_value in (
            ("accounting", "type", "Gelir"),
            ("currency_transactions", "transaction_type", "DEBIT"),
        ):
            try:
                read_cursor.execute("PRAGMA table_info(" + table + ")")
                columns = {row[1] for row in read_cursor.fetchall()}
                if not {"tracking_no", "is_invoiced", kind_column}.issubset(columns):
                    continue
                clauses = ["t." + kind_column + " = ?"]
                parameters = [kind_value]
                if table == "accounting":
                    if "category" not in columns:
                        continue
                    clauses.append("t.category = ?")
                    parameters.append("Sat\u0131\u015f")
                if "is_deleted" in columns:
                    clauses.append("COALESCE(t.is_deleted, 0) = 0")
                read_cursor.execute(
                    "SELECT t.tracking_no, t.is_invoiced FROM " + table + " t "
                    "INNER JOIN devices d ON d.tracking_no = t.tracking_no WHERE "
                    + " AND ".join(clauses), parameters,
                )
                for tracking, invoiced in read_cursor.fetchall():
                    key = str(tracking or "")
                    issued = str(invoiced or "0").strip().lower() in {"1", "true"}
                    flags[key] = flags.get(key, True) and issued
            except Exception as error:
                logger.warning("Service invoice flags unavailable for %s: %s", table, error)
        return flags

    @staticmethod
    def _service_is_invoiced(record):
        return str(record.get("is_invoiced") or "0").strip().lower() in {"1", "true"}

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
            counts["invoiced" if self._service_is_invoiced(rec) else "uninvoiced"] += 1
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
        self.combo_priority.setCurrentIndex(0)
        self.set_filter_category("all")

    def _apply_all_filters(self):
        cat = self.current_filter_category
        sq = self._current_search_query
        sf = self._current_status_filter
        df = self._current_date_filter
        pf = self.combo_priority.currentData() if hasattr(self, "combo_priority") else "all"

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

            if pf != "all" and str(rec.get("urgency") or rec.get("priority") or "Normal") != pf:
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
                if not self._service_is_invoiced(rec):
                    continue
            elif cat == "uninvoiced":
                if self._service_is_invoiced(rec):
                    continue
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
            chk.setFixedSize(20, 20)
            chk.setAccessibleName(tracking_no + " kayd\u0131n\u0131 se\u00e7")
            chk.stateChanged.connect(self._update_bulk_selection)
            chk.setCursor(Qt.CursorShape.PointingHandCursor)
            chk.setToolTip("Sat\u0131r\u0131 se\u00e7")
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
            chk_wrap.setStyleSheet("background: transparent; border: none;")
            chk_lay = QHBoxLayout(chk_wrap)
            chk_lay.setContentsMargins(0, 0, 0, 0)
            chk_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chk_lay.addWidget(chk)
            self.table.setCellWidget(row_idx, 0, chk_wrap)

            # 1: TAKIP NO
            item_tno = QTableWidgetItem(tracking_no)
            item_tno.setToolTip(tracking_no)
            item_tno.setFont(self._reference_table_font(bold=True))
            item_tno.setForeground(QColor(tc("finance_text")))
            item_tno.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row_idx, 1, item_tno)

            # 2: MUSTERI (transparent two-line cell)
            cust_name = str(rec.get("customer_name") or "-")
            company = str(rec.get("company_name") or "").strip()
            phone = str(rec.get("customer_phone") or rec.get("customer_contact") or "").strip()
            customer_detail = "\n".join(value for value in (company, phone) if value)
            self.table.setCellWidget(
                row_idx, 2,
                self._install_row_selection(
                    self._make_text_cell(cust_name, customer_detail, bold=True), row_idx
                ),
            )

            # 3: CIHAZ / MODEL (transparent two-line cell)
            brand = str(rec.get("device_brand") or rec.get("device_type") or "-")
            model = str(rec.get("device_model") or "").strip()
            serial = str(rec.get("serial_no") or "").strip()
            device_detail = "\n".join(value for value in (model, "SN: " + serial if serial else "") if value)
            self.table.setCellWidget(
                row_idx, 3,
                self._install_row_selection(
                    self._make_text_cell(brand, device_detail, bold=True), row_idx
                ),
            )

            # 4: KABUL TARIHI
            entry_date = str(rec.get("entry_date") or "-")
            parsed_entry = self._reference_date(entry_date)
            item_entry = QTableWidgetItem(parsed_entry.isoformat() if parsed_entry else entry_date)
            item_entry.setToolTip(entry_date)
            item_entry.setData(Qt.ItemDataRole.UserRole, entry_date)
            item_entry.setFont(self._reference_table_font())
            self.table.setItem(row_idx, 4, item_entry)

            # 5: TESLIM TARIHI
            exit_date = str(rec.get("exit_date") or "-")
            parsed_exit = self._reference_date(exit_date)
            item_exit = QTableWidgetItem(parsed_exit.isoformat() if parsed_exit else exit_date)
            item_exit.setToolTip(exit_date)
            item_exit.setData(Qt.ItemDataRole.UserRole, exit_date)
            item_exit.setFont(self._reference_table_font())
            self.table.setItem(row_idx, 5, item_exit)

            # 6: UCRET
            price_val = 0.0
            try:
                price_val = float(rec.get("price") or 0)
            except Exception:
                price_val = 0.0
            price_str = CurrencyHelper.format_amount(price_val, db=self.db)
            item_price = QTableWidgetItem(price_str)
            item_price.setFont(self._reference_table_font(bold=True))
            item_price.setToolTip(price_str)
            self.table.setItem(row_idx, 6, item_price)

            # 7: DURUM (Badge)
            status_text = (
                str(rec.get("status") or "Bekliyor")
                if self.main_window is not None else
                normalize_device_status(rec.get("status") or "Bekliyor")
            )
            badge_durum = self._create_status_badge(status_text)
            self.table.setCellWidget(row_idx, 7, self._install_row_selection(badge_durum, row_idx))

            # 8: ACILIYET (Badge)
            urgency_text = str(rec.get("urgency") or "Normal")
            badge_urgency = self._create_urgency_badge(urgency_text)
            self.table.setCellWidget(row_idx, 8, self._install_row_selection(badge_urgency, row_idx))

            # 9: ISLEMLER (View, Edit, Print, More)
            actions_widget = self._create_row_actions(tracking_no)
            self.table.setCellWidget(row_idx, 9, actions_widget)
            required_height = 64
            for column in (2, 3):
                cell = self.table.cellWidget(row_idx, column)
                content_width = max(1, self.table.columnWidth(column) - 16)
                for label in cell.findChildren(QLabel):
                    label.ensurePolished()
                    label.setMinimumHeight(label.heightForWidth(max(1, content_width - 16)))
                required_height = max(required_height, cell.layout().heightForWidth(content_width) + 12)
            self.table.setRowHeight(row_idx, required_height)
        self._fit_reference_table_height()
        self._update_bulk_selection()

    def _fit_reference_table_height(self):
        if not hasattr(self, "reference_table_wrapper"):
            return
        row_height = sum(self.table.rowHeight(row) for row in range(self.table.rowCount())) or 48
        height = self.table.horizontalHeader().height() + row_height + 2
        if self.table.horizontalScrollBar().maximum() > 0:
            height += self.table.horizontalScrollBar().sizeHint().height()
        footer = getattr(self, "reference_pagination_footer", None)
        if footer is not None and footer.parentWidget() is self.reference_table_wrapper:
            height += footer.height()
        self.reference_table_wrapper.setMaximumHeight(height)

    def _make_text_cell(self, primary: str, secondary: str = "", bold: bool = False) -> QWidget:
        """Create a transparent two-line cell without an extra panel/shadow."""
        cell = QWidget()
        cell.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        cell.setStyleSheet("background: transparent; border: none;")
        layout = QVBoxLayout(cell)
        inset = 2 if self.main_window is not None else 8
        layout.setContentsMargins(inset, 2 if self.main_window is not None else 4, inset, 2 if self.main_window is not None else 4)
        layout.setSpacing(0)
        primary_label = QLabel(str(primary or "-"))
        primary_label.setTextFormat(Qt.TextFormat.PlainText)
        primary_label.setFont(QFont(DesignTokens.FONT_NAME, 10 if self.main_window is not None else 11, QFont.Weight.Bold if bold else QFont.Weight.DemiBold))
        primary_label.setStyleSheet(
            theme_qss(
                "background: transparent; border: none; color: @text; "
                f"font-size: {10 if self.main_window is not None else 12}px; font-weight: {'800' if bold else '600'};"
            )
        )
        primary_label.setWordWrap(True)
        primary_label.setToolTip(str(primary))
        layout.addWidget(primary_label)
        if secondary:
            secondary_label = QLabel(str(secondary))
            secondary_label.setTextFormat(Qt.TextFormat.PlainText)
            secondary_label.setFont(QFont(DesignTokens.FONT_NAME, 9 if self.main_window is not None else 10))
            secondary_label.setStyleSheet(
                theme_qss(
                    "background: transparent; border: none; color: @text_muted; "
                    f"font-size: {10 if self.main_window is not None else 11}px; font-weight: 500;"
                )
            )
            secondary_label.setWordWrap(True)
            secondary_label.setToolTip(str(secondary))
            layout.addWidget(secondary_label)
        return cell

    def _reference_table_font(self, bold=False):
        font = QFont(self.font())
        font.setFamily(DesignTokens.MONO_FONT_NAME)
        font.setPixelSize(11)
        font.setBold(bool(bold))
        return font

    def _create_status_badge(self, status: str) -> QWidget:
        container = QWidget()
        container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        container.setStyleSheet("background: transparent; border: none;")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 6, 4, 6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        norm = normalize_device_status(status)
        display_source = str(status) if self.main_window is not None else norm
        display_status = display_source.replace("i", "\u0130").replace("\u0131", "I").upper()
        if self.main_window is not None and " " in display_status:
            display_status = display_status.replace(" ", "\n", 1)
        badge = QLabel(display_status)
        badge.setTextFormat(Qt.TextFormat.PlainText)
        badge.setAccessibleName(norm)
        badge.setToolTip(norm)
        badge.setFixedHeight(30 if self.main_window is not None else 18)
        badge.setWordWrap(self.main_window is not None)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if self.main_window is not None and status == "Kargoda":
            bg, fg = "@finance_active_bg", "@service_kpi_active"
        elif self.main_window is not None and status == "Onayland\u0131":
            bg, fg = "@finance_success_bg", "@service_kpi_ready"
        elif self.main_window is not None and status == "Onar\u0131mda":
            bg, fg = "@finance_active_bg", "@service_kpi_duration"
        elif norm == "Tamirde":
            bg, fg = "@warning_bg", "@warning"
        elif norm in {"Teslim Edildi", "Teslim", "Tamir Edildi", "Teslime Hazir"}:
            bg, fg = "@finance_success_bg", "@finance_secondary"
        elif norm == "\u0130ptal":
            bg, fg = "@danger_bg", "@danger"
        elif norm == "Par\u00e7a Bekliyor":
            bg, fg = "@finance_warning_bg", "@finance_tertiary"
        elif norm == "Test S\u00fcrecinde":
            bg, fg = "@finance_active_bg", "@finance_primary"
        elif norm == "Onay Bekliyor":
            bg, fg = "@warning_bg", "@warning"
        else:
            bg, fg = "@finance_active_bg", "@finance_primary"

        badge.setStyleSheet(theme_qss(f"""
            QLabel {{
                background-color: {bg};
                color: {fg};
                font-size: {8 if self.main_window is not None else 9}px;
                font-weight: 800;
                border: none;
                border-radius: 3px;
                padding: 0 2px;
            }}
        """))
        layout.addWidget(badge)
        return container

    def _create_urgency_badge(self, urgency: str) -> QWidget:
        container = QWidget()
        container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        container.setStyleSheet("background: transparent; border: none;")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(1 if self.main_window is not None else 4, 6, 1 if self.main_window is not None else 4, 6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        badge = QLabel(str(urgency))
        badge.setTextFormat(Qt.TextFormat.PlainText)
        badge.setAccessibleName(str(urgency))
        badge.setToolTip(str(urgency))
        badge.setFixedHeight(18)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

        u_lower = urgency.lower()
        if "y\u00fcksek" in u_lower or "acil" in u_lower:
            bg, fg = "@finance_warning_bg", "@finance_tertiary"
        elif "d\u00fc\u015f\u00fck" in u_lower:
            bg, fg = "transparent", "@finance_text_muted"
        else:
            bg, fg = "transparent", "@finance_text_muted"

        badge.setStyleSheet(theme_qss(f"""
            QLabel {{
                background-color: {bg};
                color: {fg};
                font-size: {8 if self.main_window is not None else 10}px;
                font-weight: 800;
                border: none;
                border-radius: 3px;
                padding: 0 2px;
            }}
        """))
        layout.addWidget(badge)
        return container

    def _create_row_actions(self, tracking_no: str) -> QWidget:
        container = QWidget()
        container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        container.setStyleSheet("background: transparent; border: none;")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(3)
        layout.addStretch(1)
        container.setMinimumWidth(188 if self.main_window is not None else 208)
        container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        btn_style = theme_qss("""
            QPushButton {
                background-color: transparent;
                color: @finance_text;
                border: none;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: @finance_surface_high;
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

        action_colors = (
            "#22d3ee", "#fbbf24", "#a5b4fc", "#c084fc",
            "#38bdf8", "#34d399", "#fb923c", "#f87171",
        )
        for index, button in enumerate(container.findChildren(QPushButton)):
            button.setFixedSize(20 if self.main_window is not None else 22, 22)
            button.setAccessibleName(button.toolTip())
            if self.main_window is not None:
                color = action_colors[index]
                red, green, blue = (
                    int(color[offset:offset + 2], 16) for offset in (1, 3, 5)
                )
                button.setStyleSheet(
                    f"QPushButton {{ background: rgba({red}, {green}, {blue}, 34); "
                    "border: none; border-radius: 4px; } "
                    f"QPushButton:hover {{ background: rgba({red}, {green}, {blue}, 85); }}"
                )
                svg = button.property("serviceActionSvg")
                if svg:
                    button.setIcon(render_svg_icon(svg, color, size=16))
        return container

    def refresh_theme(self):
        self.setStyleSheet(theme_qss("background-color: @finance_canvas;"))
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
        self._export_service_records(self._filtered_records)

    def _export_service_records(self, records):
        if not records:
            self.notify("D\u0131\u015fa aktar\u0131lacak servis kayd\u0131 bulunamad\u0131.", "warning")
            return
        try:
            file_path, selected_filter = QFileDialog.getSaveFileName(
                self,
                "Servis Listesini D\u0131\u015fa Aktar",
                f"servis_listesi_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                "Excel Dosyas\u0131 (*.xlsx);;CSV Dosyas\u0131 (*.csv);;PDF Rapor (*.pdf)",
            )
            if not file_path:
                return

            rows_to_export = []
            for r in records:
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
            if file_path.lower().endswith(".pdf") or selected_filter.startswith("PDF"):
                if not file_path.lower().endswith(".pdf"):
                    file_path += ".pdf"
                self._write_service_pdf(file_path, rows_to_export)
            else:
                import pandas as pd
                df = pd.DataFrame(rows_to_export)
                if file_path.lower().endswith(".csv"):
                    df.to_csv(file_path, index=False, encoding="utf-8-sig")
                else:
                    df.to_excel(file_path, index=False)
            self.notify("Servis listesi ba\u015far\u0131yla d\u0131\u015fa aktar\u0131ld\u0131.", "success")
        except Exception as e:
            logger.error(f"Service export error: {e}")
            self.notify(f"D\u0131\u015fa aktarma hatas\u0131: {e}", "error")

    def _write_service_pdf(self, file_path, rows):
        headers = list(rows[0])
        header_html = "".join("<th>" + html.escape(header) + "</th>" for header in headers)
        body_html = []
        for row in rows:
            cells = []
            for header in headers:
                value = row.get(header)
                if header == "\u00dccret":
                    value = CurrencyHelper.format_amount(value or 0, db=self.db)
                cells.append("<td>" + html.escape("" if value is None else str(value)) + "</td>")
            body_html.append("<tr>" + "".join(cells) + "</tr>")
        document = QTextDocument()
        document.setDefaultFont(self.font())
        document.setHtml("<html><head><meta charset='UTF-8'><style>body { color: #172033; } table { width: 100%; border-collapse: collapse; font-size: 7pt; } th, td { border: 1px solid #CBD5E1; padding: 4px; text-align: left; } th { background: #EEF2F7; } </style></head><body><h2>AYEC Pro - Servis Listesi</h2><p>" + str(len(rows)) + " kay\u0131t</p><table><thead><tr>" + header_html + "</tr></thead><tbody>" + "".join(body_html) + "</tbody></table></body></html>")
        writer = QPdfWriter(file_path)
        writer.setCreator("AYEC Pro")
        writer.setTitle("Servis Listesi")
        writer.setPageOrientation(QPageLayout.Orientation.Landscape)
        document.print(writer)
        del writer
        if not QFileInfo(file_path).exists() or QFileInfo(file_path).size() < 8:
            raise OSError("PDF output could not be written")

    def _checked_service_records(self):
        tracking_numbers = set()
        for row in range(self.table.rowCount()):
            widget = self.table.cellWidget(row, 0)
            checkbox = widget.findChild(QCheckBox) if widget is not None else None
            item = self.table.item(row, 1)
            if checkbox is not None and checkbox.isChecked() and item is not None:
                tracking_numbers.add(item.text().strip())
        return [record for record in self._filtered_records if record.get("tracking_no") in tracking_numbers]

    def _update_bulk_selection(self, *args):
        if not hasattr(self, "btn_bulk_actions"):
            return
        count = len(self._checked_service_records())
        self.btn_bulk_actions.setText("Toplu \u0130\u015flemler" + (" (" + str(count) + ")" if count else ""))

    def _set_visible_service_selection(self, checked):
        for row in range(self.table.rowCount()):
            widget = self.table.cellWidget(row, 0)
            checkbox = widget.findChild(QCheckBox) if widget is not None else None
            if checkbox is not None:
                checkbox.setChecked(bool(checked))

    def _export_selected_services(self):
        records = self._checked_service_records()
        if not records:
            self.notify("L\u00fctfen d\u0131\u015fa aktar\u0131lacak kay\u0131tlar\u0131 se\u00e7in.", "warning")
            return
        self._export_service_records(records)

    def _print_selected_services(self):
        records = self._checked_service_records()
        if not records:
            self.notify("L\u00fctfen yazd\u0131r\u0131lacak kay\u0131tlar\u0131 se\u00e7in.", "warning")
            return
        for record in records:
            self.print_service(record["tracking_no"])

    def notify(self, message, level="info"):
        target = self.main_window or self.window()
        if hasattr(target, "show_notification"):
            target.show_notification(message, level)
            return
        callback = {"error": show_error, "success": show_success, "warning": show_warning}.get(level, show_info)
        callback(self.window(), message)
