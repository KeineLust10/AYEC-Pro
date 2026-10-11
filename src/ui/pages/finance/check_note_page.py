# -*- coding: utf-8 -*-

import csv

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QToolButton,
    QLabel,
    QHeaderView,
    QDialog,
    QFormLayout,
    QComboBox,
    QLineEdit,
    QDateEdit,
    QDoubleSpinBox,
    QGridLayout,
    QFrame,
    QSizePolicy,
    QFileDialog,
)
from PyQt6.QtCore import Qt, QDate, QSize, QEvent
from PyQt6.QtGui import QFont

from src.utils.theme_colors import theme_qss, qc
from src.utils.design_system import DesignTokens
from src.ui.widgets.modern_inputs import ModernComboBox
from src.ui.widgets.reference_date_edit import ReferenceDateEdit
from src.ui.widgets.financial_reference_controls import ReferenceMetricValueLabel
from src.ui.widgets.navigation_glyph import navigation_icon
from src.utils.toast_notification import show_success, show_error
from src.ui.dialogs.base_modern_dialog import BaseModernDialog
from src.utils.context_menu_settings import is_context_menu_enabled
from src.utils.logger import logger
from src.utils.currency_helper import CurrencyHelper



class CheckNotePage(QWidget):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    def __init__(self, db, main_window):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.init_ui()

    def _display_currency(self):
        return CurrencyHelper.get_code(self.db)

    def _format_display_money(self, amount_try):
        formatted = CurrencyHelper.format_from_try(
            amount_try, db=self.db, currency_code=getattr(self, "selected_currency", self._display_currency())
        )
        currency_code = getattr(self, "selected_currency", self._display_currency()).upper()
        if currency_code in ("USD", "EUR") and " " in formatted:
            amount_text, symbol = formatted.rsplit(" ", 1)
            return f"{symbol}{amount_text}"
        return formatted

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 30, 26, 14)
        layout.setSpacing(18)
        self.selected_currency = self._display_currency()
        self.setStyleSheet(theme_qss(
            "QWidget { color: @text; } QFrame#PortfolioCard { background: @finance_surface; "
            "border: 1px solid @border; border-radius: 12px; }"
        ))

        header_layout = QHBoxLayout()
        title_column = QVBoxLayout()
        title_column.setSpacing(0)
        title_header = QHBoxLayout()
        title_header.setSpacing(12)
        title = QLabel("\u00c7ek & Senet Portf\u00f6y Y\u00f6netimi")
        self.page_title = title
        title.setFont(QFont(DesignTokens.FONT_NAME, 17, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("color: @text; background: transparent;"))
        title_header.addWidget(title)
        portfolio_badge = QLabel("Canl\u0131 Portf\u00f6y Mod\u00fcl\u00fc")
        self.portfolio_badge = portfolio_badge
        portfolio_badge.setStyleSheet(theme_qss(
            "color: @accent; background: @finance_surface_alt; border: 1px solid @border; border-radius: 10px; "
            "padding: 5px 9px; font-size: 10px;"
        ))
        title_header.addWidget(portfolio_badge)
        title_header.addStretch(1)
        title_column.addLayout(title_header)
        subtitle = QLabel("Al\u0131nan ve verilen vadeli k\u0131ymetli evraklar\u0131n takas, ciro, tahsilat ve reeskont operasyonlar\u0131")
        self.page_subtitle = subtitle
        subtitle.setStyleSheet(theme_qss("color: @text_muted; background: transparent; font-size: 10px;"))
        title_column.addWidget(subtitle)
        header_layout.addLayout(title_column, 1)
        self.btn_bulk_clearance = QPushButton("Toplu Banka Takas\u0131na Ver")
        self.btn_bulk_clearance.setMinimumWidth(0)
        self.btn_bulk_clearance.setFixedSize(230, 44)
        self.btn_bulk_clearance.clicked.connect(self.bulk_bank_clearance)
        self.btn_bulk_clearance.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        self.btn_bulk_clearance.setIcon(navigation_icon("bank", 16, "finance_breadcrumb_active"))
        self.btn_bulk_clearance.setIconSize(QSize(16, 16))
        header_layout.addWidget(self.btn_bulk_clearance)
        self.btn_export = QPushButton("Excel \u00c7\u0131kt\u0131")
        self.btn_export.setMinimumWidth(0)
        self.btn_export.setFixedSize(128, 44)
        self.btn_export.clicked.connect(self.export_excel)
        self.btn_export.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        self.btn_export.setIcon(navigation_icon("document", 16, "success"))
        self.btn_export.setIconSize(QSize(16, 16))
        header_layout.addWidget(self.btn_export)
        self.btn_add = QPushButton("+ Yeni \u00c7ek / Senet Giri\u015fi")
        self.btn_add.setMinimumWidth(0)
        self.btn_add.setFixedSize(234, 44)
        self.btn_add.clicked.connect(self.open_add_dialog)
        self.btn_add.setStyleSheet(theme_qss(DesignTokens.get_button_qss("success", size="sm")))
        self.btn_add.setIcon(navigation_icon("plus_circle", 16, "selection_text"))
        self.btn_add.setIconSize(QSize(16, 16))
        header_layout.addWidget(self.btn_add)
        layout.addLayout(header_layout)

        layout.addSpacing(11)
        self._metric_values = {}
        self._metric_details = {}
        metrics = QGridLayout()
        metrics.setHorizontalSpacing(18)
        metrics.setVerticalSpacing(10)
        for column, (key, label, color) in enumerate((
            ("portfolio", "Portf\u00f6ydeki Toplam Tutar", "success"),
            ("due", "Bu Ay Vadesi Gelenler", "warning"),
            ("received", "Al\u0131nan vs Verilen", "finance_secondary"),
            ("discounted", "Tahsildeki (Banka Takas\u0131)", "finance_tertiary"),
        )):
            card = QFrame()
            card.setObjectName("PortfolioCard")
            card.setFixedHeight(194)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(20, 20, 20, 19)
            card_layout.setSpacing(0)
            caption_row = QHBoxLayout()
            caption = QLabel(label)
            caption.setStyleSheet(theme_qss("color: @text_muted; border: none; font-size: 11px;"))
            caption_row.addWidget(caption, 1)
            glyph = {"portfolio": "\u25a3", "due": "\u25a6", "received": "\u2195", "discounted": "$"}[key]
            glyph_label = QLabel(glyph)
            glyph_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            glyph_label.setFixedSize(40, 40)
            glyph_label.setStyleSheet(theme_qss(
                f"color: @{color}; background: @finance_surface_alt; border: 1px solid @{color}; "
                "border-radius: 8px; font-size: 16px; font-weight: 700;"
            ))
            caption_row.addWidget(glyph_label)
            if key == "received":
                value = QLabel()
                value.setTextFormat(Qt.TextFormat.RichText)
                value.setFixedHeight(34)
                value.setStyleSheet(theme_qss("color: @text; font: 20px Inter; border: none;"))
            else:
                value = ReferenceMetricValueLabel("0", primary_token=color, primary_size=28)
                value.setFixedHeight(34)
            value.setToolTip(label)
            card_layout.addLayout(caption_row)
            card_layout.addStretch(1)
            card_layout.addWidget(value)
            card_layout.addSpacing(6)
            detail_frame = QFrame(card)
            detail_frame.setObjectName("metric_detail_frame_" + key)
            detail_frame.setStyleSheet("background: transparent; border: none;")
            detail_row = QHBoxLayout(detail_frame)
            detail_row.setContentsMargins(0, 0, 0, 0)
            detail_row.setSpacing(6)
            detail = QLabel("")
            detail.setObjectName("metric_detail_" + key)
            detail.setMinimumHeight(16)
            detail.setWordWrap(True)
            detail.setAlignment(
                Qt.AlignmentFlag.AlignLeft
                | (Qt.AlignmentFlag.AlignTop if key == "portfolio" else Qt.AlignmentFlag.AlignVCenter)
            )
            if key == "portfolio":
                detail.setContentsMargins(0, 8, 0, 0)
            detail.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; border: none;"))
            detail_row.addWidget(detail, 1)
            self._metric_details[key] = detail
            badge = QLabel("")
            badge.setObjectName("metric_badge_" + key)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setStyleSheet(theme_qss(
                "QLabel { border: 1px solid @border; border-radius: 6px; padding: 3px 6px; "
                "font-size: 10px; font-weight: 700; }"
            ))
            badge_styles = {
                "portfolio": ("success", "finance_success_bg"),
                "due": ("warning", "finance_warning_bg"),
                "received": ("finance_breadcrumb_active", "finance_surface_alt"),
                "discounted": ("finance_tertiary", "finance_tertiary_bg"),
            }
            badge_foreground, badge_background = badge_styles[key]
            badge.setStyleSheet(theme_qss(
                f"QLabel {{ color: @{badge_foreground}; background: @{badge_background}; "
                f"border: 1px solid @{badge_foreground}; border-radius: 6px; padding: 3px 6px; "
                "font-size: 10px; font-weight: 700; }"
            ))
            if key == "portfolio":
                detail_frame.setFixedHeight(58)
                badge.setFixedSize(90, 56)
                badge.setText("Portf\u00f6y\nAktif")
            elif key in ("due", "received"):
                detail_frame.setFixedHeight(34)
                badge.setFixedHeight(32)
            else:
                detail_frame.setFixedHeight(32)
                badge.setFixedHeight(30)
            detail_row.addWidget(badge, 0, Qt.AlignmentFlag.AlignVCenter)
            card_layout.addWidget(detail_frame)
            metrics.addWidget(card, 0, column)
            self._metric_values[key] = value
        layout.addLayout(metrics)
        layout.addSpacing(2)

        self.reference_filter = "all"
        filter_card = QFrame()
        filter_card.setObjectName("PortfolioCard")
        filter_card.setMinimumHeight(149)
        filter_layout = QVBoxLayout(filter_card)
        filter_layout.setContentsMargins(17, 14, 20, 12)
        filter_layout.setSpacing(17)
        top_filter_row = QHBoxLayout()
        top_filter_row.setSpacing(12)
        reference_tabs_frame = QFrame()
        self.reference_tabs_frame = reference_tabs_frame
        reference_tabs_frame.setObjectName("ReferenceFilterTabs")
        reference_tabs_frame.setFixedHeight(46)
        reference_tabs_frame.setStyleSheet(theme_qss(
            "QFrame#ReferenceFilterTabs { background: @surface; border: 1px solid @border; border-radius: 10px; }"
        ))
        reference_tabs_layout = QHBoxLayout(reference_tabs_frame)
        reference_tabs_layout.setContentsMargins(4, 5, 4, 5)
        reference_tabs_layout.setSpacing(0)
        self.reference_filter_buttons = {}
        for key, label in ((
            ("all", "T\u00fcm Evraklar"), ("checks", "Al\u0131nan \u00c7ekler"), ("notes", "Al\u0131nan Senetler"),
            ("own", "Kendi \u00c7eklerimiz"), ("endorsed", "Tahsile Verilenler (Takas)"),
        )):
            tab_button = QPushButton(label)
            tab_button.setCheckable(True)
            tab_button.setChecked(key == "all")
            tab_button.setFixedHeight(34)
            tab_button.setFixedWidth({"all": 157, "checks": 158, "notes": 153, "own": 157, "endorsed": 201}[key])
            tab_button.setStyleSheet(theme_qss(
                "QPushButton { background: @finance_surface_alt; color: @text_muted; border: 1px solid @border; "
                "border-radius: 7px; padding: 6px 11px; font-size: 14px; } "
                "QPushButton:checked { background: @accent; color: @selection_text; border-color: @accent; font-weight: 700; }"
            ))
            tab_button.clicked.connect(lambda _checked=False, value=key: self._select_reference_filter(value))
            reference_tabs_layout.addWidget(tab_button)
            self.reference_filter_buttons[key] = tab_button
            if key == "endorsed":
                tab_button.setStyleSheet(theme_qss(
                    "QPushButton { background: @finance_surface_alt; color: @finance_tertiary; border: 1px solid @border; "
                    "border-radius: 7px; padding: 6px 8px; font-size: 13px; } "
                    "QPushButton:checked { background: @accent; color: @selection_text; border-color: @accent; font-weight: 700; }"
                ))
        top_filter_row.addWidget(reference_tabs_frame)
        top_filter_row.addStretch(1)
        currency_frame = QFrame()
        self.currency_frame = currency_frame
        currency_frame.setObjectName("ReferenceCurrencyTabs")
        currency_frame.setFixedSize(288, 46)
        currency_frame.setStyleSheet(theme_qss(
            "QFrame#ReferenceCurrencyTabs { background: @surface; border: 1px solid @border; border-radius: 10px; }"
        ))
        currency_layout = QHBoxLayout(currency_frame)
        currency_layout.setContentsMargins(5, 5, 5, 5)
        currency_layout.setSpacing(2)
        self.currency_buttons = {}
        for code, label in (("USD", "USD ($)"), ("TRY", "TRY (\u20ba)"), ("EUR", "EUR (\u20ac)")):
            currency_button = QPushButton(label)
            currency_button.setCheckable(True)
            currency_button.setChecked(code == self.selected_currency)
            currency_button.setFixedHeight(34)
            currency_button.setMinimumWidth(0)
            currency_button.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            currency_button.clicked.connect(lambda _checked=False, value=code: self.select_currency(value))
            currency_button.setStyleSheet(theme_qss(
                "QPushButton { background: @surface; color: @text_muted; border: 1px solid @border; border-radius: 6px; padding: 5px 9px; } "
                "QPushButton:checked { background: @surface_alt; color: @finance_breadcrumb_active; border-color: @finance_breadcrumb_active; font-weight: 700; }"
            ))
            currency_layout.addWidget(currency_button, 1)
            self.currency_buttons[code] = currency_button
        top_filter_row.addWidget(currency_frame)
        filter_layout.addLayout(top_filter_row)

        control_row = QHBoxLayout()
        control_row.setSpacing(13)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Ke\u015fideci, bor\u00e7lu, banka veya evrak no ara...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self.load_data)
        self.search_input.setMinimumWidth(0)
        self.search_input.setFixedSize(232, 42)
        control_row.addWidget(self.search_input)
        self.filter_status = ModernComboBox()
        self.filter_status.set_reference_chevron()
        self.filter_status.addItems(["Portf\u00f6yde (Kasada)", "Tahsil Edildi", "Ciro Edildi", "\u00d6dendi", "Kar\u015f\u0131l\u0131ks\u0131z", "\u0130ade", "T\u00fcm\u00fc"])
        self.filter_status.setCurrentText("Portf\u00f6yde (Kasada)")
        self.filter_status.currentTextChanged.connect(self.load_data)
        self.filter_status.setMinimumWidth(0)
        self.filter_status.setFixedSize(232, 42)
        control_row.addWidget(self.filter_status)
        self.bank_filter = ModernComboBox()
        self.bank_filter.set_reference_chevron()
        self.bank_filter.addItem("Banka: T\u00fcm Bankalar")
        self.bank_filter.currentTextChanged.connect(self.load_data)
        self.bank_filter.setMinimumWidth(0)
        self.bank_filter.setFixedSize(232, 42)
        control_row.addWidget(self.bank_filter)
        self.date_start = ReferenceDateEdit(QDate.currentDate())
        self.date_start.setDisplayFormat("yyyy-MM-dd")
        self.date_start.setDateRange(QDate(1900, 1, 1), QDate(2099, 12, 31))
        range_start = QDate.currentDate().addDays(1 - QDate.currentDate().day())
        range_end = range_start.addMonths(12)
        self.date_start.setDate(range_start)
        self.date_start.setFixedSize(112, 34)
        self.date_start.setStyleSheet(theme_qss(
            "QDateEdit { background: @finance_surface_alt; color: @text; border: 1px solid @border; font-family: 'JetBrains Mono'; font-size: 11px; "
            "border-radius: 6px; padding: 7px 8px; } QDateEdit::drop-down { width: 24px; background: transparent; border: none; } "
            "QDateEdit::down-arrow { image: none; width: 0; height: 0; border: none; }"
        ))
        self.date_start.dateChanged.connect(self.load_data)
        self.date_end = ReferenceDateEdit(QDate.currentDate())
        self.date_end.setDisplayFormat("yyyy-MM-dd")
        self.date_end.setDateRange(QDate(1900, 1, 1), QDate(2099, 12, 31))
        self.date_end.setDate(range_end)
        self.date_end.setFixedSize(104, 34)
        self.date_end.setStyleSheet(theme_qss(
            "QDateEdit { background: @finance_surface_alt; color: @text; border: 1px solid @border; font-family: 'JetBrains Mono'; font-size: 11px; "
            "border-radius: 6px; padding: 7px 8px; } QDateEdit::drop-down { width: 24px; background: transparent; border: none; } "
            "QDateEdit::down-arrow { image: none; width: 0; height: 0; border: none; }"
        ))
        self.date_end.dateChanged.connect(self.load_data)
        date_range = QFrame()
        self.date_range = date_range
        date_range.setObjectName("CheckDateRange")
        date_range.setFixedSize(232, 42)
        date_range.setStyleSheet(theme_qss(
            "QFrame#CheckDateRange { background: @finance_surface_alt; border: 1px solid @border; border-radius: 8px; } "
            "QFrame#CheckDateRange QLabel { background: transparent; border: none; }"
        ))
        date_range_layout = QHBoxLayout(date_range)
        date_range_layout.setContentsMargins(4, 2, 4, 2)
        date_range_layout.setSpacing(0)
        date_range_layout.addWidget(self.date_start)
        range_separator = QToolButton()
        range_separator.setText("-")
        range_separator.setAutoRaise(True)
        range_separator.setEnabled(False)
        range_separator.setFixedWidth(4)
        range_separator.setStyleSheet(theme_qss("QToolButton { background: transparent; border: none; padding: 0; }"))
        date_range_layout.addWidget(range_separator)
        date_range_layout.addWidget(self.date_end)
        control_row.addWidget(date_range)
        self.btn_clear_filters = QPushButton("Filtreyi Temizle")
        self.btn_clear_filters.setMinimumWidth(0)
        self.btn_clear_filters.clicked.connect(self.clear_filters)
        self.btn_clear_filters.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        self.btn_clear_filters.setIcon(navigation_icon("filter", 14, "finance_breadcrumb_active"))
        self.btn_clear_filters.setIconSize(QSize(14, 14))
        self.btn_clear_filters.setFixedWidth(224)
        control_row.addWidget(self.btn_clear_filters)
        filter_layout.addLayout(control_row)
        layout.addWidget(filter_card)

        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            "\u2610", "#", "EVRAK\nT\u00dcR\u00dc", "Y\u00d6N", "KE\u015e\u0130DEC\u0130 /\nBOR\u00c7LU CAR\u0130", "BANKA &\n\u015eUBE",
            "EVRAK /\nSER\u0130 NO", "TUTAR ($ / TRY)", "VADE\nTAR\u0130H\u0130", "DURUM", "HIZLI \u0130\u015eLEMLER"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        for column, width in enumerate((58, 60, 105, 100, 150, 115, 105, 135, 90, 126, 190)):
            self.table.setColumnWidth(column, width)
        header.setStretchLastSection(False)
        for column in range(11):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Interactive)
        header.setFixedHeight(72)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setMinimumWidth(0)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.open_context_menu)
        self.table.cellDoubleClicked.connect(self.on_row_double_click)
        self.table.cellClicked.connect(self._toggle_row_selection)
        self.table.horizontalHeader().sectionClicked.connect(self._toggle_table_selection)
        self.table.setStyleSheet(theme_qss(
            "QTableWidget { background: @finance_surface; alternate-background-color: @finance_surface_alt; "
            "gridline-color: @border; border: 1px solid @border; border-radius: 12px; } "
            "QTableWidget::item { padding: 8px 10px; border-bottom: 1px solid @border; } "
            "QHeaderView::section { background: @finance_surface; color: @text_muted; border: none; "
                "border-bottom: 1px solid @border; padding: 10px 8px; font-size: 10px; font-weight: 700; }"
        ))
        layout.addWidget(self.table, 1)
        self.empty_state = QLabel("G\u00f6r\u00fcnt\u00fclenecek evrak bulunamad\u0131.", self.table.viewport())
        self.empty_state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_state.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.empty_state.setStyleSheet(theme_qss(
            "color: @text_muted; font-size: 14px; font-weight: 600; background: transparent;"
        ))
        self.table.viewport().installEventFilter(self)
        self._update_empty_state()
        self.load_data()

    def eventFilter(self, watched, event):
        if watched is self.table.viewport() and event.type() == QEvent.Type.Resize:
            self.empty_state.setGeometry(self.table.viewport().rect())
            self._fit_table_columns()
        return super().eventFilter(watched, event)

    def _fit_table_columns(self):
        if not hasattr(self, "table"):
            return
        available = self.table.viewport().width()
        if available <= 0:
            available = self.table.width()
        if available <= 0:
            return
        weights = (35, 45, 75, 65, 130, 85, 90, 100, 75, 85, 215)
        minimums = (44, 48, 76, 70, 135, 110, 110, 120, 92, 100, 170)
        widths = [max(minimum, available * weight // 1000) for minimum, weight in zip(minimums, weights)]
        if sum(widths) < available:
            widths[-1] += available - sum(widths)
        header = self.table.horizontalHeader()
        for column, width in enumerate(widths):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Interactive)
            self.table.setColumnWidth(column, width)

    def _update_empty_state(self):
        if not hasattr(self, "empty_state"):
            return
        self.empty_state.setGeometry(self.table.viewport().rect())
        self.empty_state.setVisible(self.table.rowCount() == 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        compact = self.width() < 1280
        if not hasattr(self, "search_input"):
            return
        if compact:
            header = self.table.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            self.reference_tabs_frame.setFixedWidth(765)
            self.currency_frame.setFixedWidth(230)
            compact_tab_widths = {"all": 138, "checks": 145, "notes": 145, "own": 147, "endorsed": 180}
            for key, button in self.reference_filter_buttons.items():
                button.setFixedWidth(compact_tab_widths[key])
                button.setStyleSheet(theme_qss(
                    "QPushButton { background: @finance_surface_alt; color: @text_muted; border: 1px solid @border; "
                    "border-radius: 7px; padding: 6px 7px; font-size: 12px; } "
                    "QPushButton:checked { background: @accent; color: @selection_text; border-color: @accent; font-weight: 700; }"
                ))
                if key == "endorsed":
                    button.setStyleSheet(theme_qss(
                        "QPushButton { background: @finance_surface_alt; color: @finance_tertiary; border: 1px solid @border; "
                        "border-radius: 7px; padding: 5px 3px; font-size: 11px; } "
                        "QPushButton:checked { background: @accent; color: @selection_text; border-color: @accent; font-weight: 700; }"
                    ))
            self.search_input.setFixedSize(140, 42)
            self.filter_status.setFixedSize(190, 42)
            self.bank_filter.setFixedSize(200, 42)
            self.date_range.setFixedWidth(270)
            self.btn_clear_filters.setFixedSize(145, 42)
            self.date_start.setFixedWidth(116)
            self.date_end.setFixedWidth(116)
            self._metric_values["received"].setStyleSheet(theme_qss("color: @text; font: 17px Inter; border: none;"))
            self.page_title.setStyleSheet(theme_qss(
                "color: @text; background: transparent; font-size: 16px; font-weight: 700;"
            ))
            self.portfolio_badge.hide()
            self.page_subtitle.hide()
            self.btn_bulk_clearance.setFixedSize(190, 40)
            self.btn_bulk_clearance.setFont(QFont(DesignTokens.FONT_NAME, 10, QFont.Weight.DemiBold))
            self.btn_export.setFixedSize(110, 40)
            self.btn_add.setFixedSize(188, 40)
        else:
            header = self.table.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            self.reference_tabs_frame.setFixedWidth(836)
            self.currency_frame.setFixedWidth(288)
            desktop_tab_widths = {"all": 157, "checks": 158, "notes": 153, "own": 157, "endorsed": 201}
            for key, button in self.reference_filter_buttons.items():
                button.setFixedWidth(desktop_tab_widths[key])
                button.setStyleSheet(theme_qss(
                    "QPushButton { background: @finance_surface_alt; color: @text_muted; border: 1px solid @border; "
                    "border-radius: 7px; padding: 6px 11px; font-size: 14px; } "
                    "QPushButton:checked { background: @accent; color: @selection_text; border-color: @accent; font-weight: 700; }"
                ))
                if key == "endorsed":
                    button.setStyleSheet(theme_qss(
                        "QPushButton { background: @finance_surface_alt; color: @finance_tertiary; border: 1px solid @border; "
                        "border-radius: 7px; padding: 6px 8px; font-size: 13px; } "
                        "QPushButton:checked { background: @accent; color: @selection_text; border-color: @accent; font-weight: 700; }"
                    ))
            self.search_input.setFixedSize(232, 42)
            self.filter_status.setFixedSize(232, 42)
            self.bank_filter.setFixedSize(232, 42)
            self.date_range.setFixedSize(232, 42)
            self.btn_clear_filters.setFixedSize(232, 42)
            self.date_start.setFixedSize(112, 34)
            self.date_end.setFixedSize(104, 34)
            self._metric_values["received"].setStyleSheet(theme_qss("color: @text; font: 20px Inter; border: none;"))
            self.page_title.setStyleSheet(theme_qss(
                "color: @text; background: transparent; font-size: 18px; font-weight: 700;"
            ))
            self.portfolio_badge.show()
            self.page_subtitle.show()
            self.btn_bulk_clearance.setFixedSize(230, 44)
            self.btn_export.setFixedSize(128, 44)
            self.btn_add.setFixedSize(234, 44)
            self.btn_bulk_clearance.setFont(QFont(DesignTokens.FONT_NAME, 11, QFont.Weight.DemiBold))
        self._fit_table_columns()

    def _normalize_status_filter(self, current: str):
        mapping = {
            "T\u00fcm\u00fc": None,
            "Portf\u00f6yde (Kasada)": "__portfolio_group__",
            "Tahsil Edildi": "Tahsil Edildi",
            "Ciro Edildi": "Ciro Edildi",
            "\u00d6dendi": "\u00d6dendi",
            "Kar\u015f\u0131l\u0131ks\u0131z": "Kar\u015f\u0131l\u0131ks\u0131z",
            "\u0130ade": "\u0130ade",
        }
        return mapping.get(current)

    def _select_status_chip(self, value):
        aliases = {"Tumu": "T\u00fcm\u00fc", "Portfoyde": "Portf\u00f6yde (Kasada)", "Odendi": "\u00d6dendi"}
        self.filter_status.setCurrentText(aliases.get(value, value))

    def _toggle_table_selection(self, column):
        if column != 0:
            return
        should_check = any(
            not bool(self.table.item(row, 0).data(Qt.ItemDataRole.UserRole + 1))
            for row in range(self.table.rowCount()) if self.table.item(row, 0)
        )
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                item.setData(Qt.ItemDataRole.UserRole + 1, should_check)
                wrapper = self.table.cellWidget(row, 0)
                checkbox = wrapper.findChild(QPushButton) if wrapper is not None else None
                if checkbox is not None:
                    checkbox.setChecked(should_check)

    def _toggle_row_selection(self, row, column):
        if column != 0:
            return
        item = self.table.item(row, 0)
        if item:
            wrapper = self.table.cellWidget(row, 0)
            checkbox = wrapper.findChild(QPushButton) if wrapper is not None else None
            checked = not bool(item.data(Qt.ItemDataRole.UserRole + 1))
            item.setData(Qt.ItemDataRole.UserRole + 1, checked)
            if checkbox is not None:
                checkbox.setChecked(checked)

    def select_currency(self, currency_code):
        self.selected_currency = str(currency_code or self._display_currency()).upper()
        for code, button in self.currency_buttons.items():
            button.setChecked(code == self.selected_currency)
        self.load_data()

    def clear_filters(self):
        self.search_input.clear()
        self.filter_status.setCurrentText("Portf\u00f6yde (Kasada)")
        self.bank_filter.setCurrentIndex(0)
        range_start = QDate.currentDate().addDays(1 - QDate.currentDate().day())
        self.date_start.setDate(range_start)
        self.date_end.setDate(range_start.addMonths(12))
        self._select_reference_filter("all")

    def export_excel(self):
        path, _ = QFileDialog.getSaveFileName(self, "Excel \u00c7\u0131kt\u0131s\u0131", "cek_senet_portfoyu.csv", "CSV (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as output:
                writer = csv.writer(output, delimiter=";")
                writer.writerow([self.table.horizontalHeaderItem(column).text() for column in range(1, 10)])
                for row in range(self.table.rowCount()):
                    writer.writerow([self._cell_value(row, column) for column in range(1, 10)])
            show_success(self, "Excel uyumlu CSV dosyas\u0131 kaydedildi.")
        except Exception as exc:
            show_error(self, f"Dosya kaydedilemedi: {exc}")

    def bulk_bank_clearance(self):
        selected_ids = []
        for row in range(self.table.rowCount()):
            selection_item = self.table.item(row, 0)
            if selection_item and selection_item.data(Qt.ItemDataRole.UserRole + 1):
                selected_ids.append(selection_item.data(Qt.ItemDataRole.UserRole))
        if not selected_ids:
            show_error(self, "\u00d6nce takasa verilecek evraklar\u0131 se\u00e7in.")
            return
        for check_id in selected_ids:
            self.change_status(check_id, "Ciro Edildi")

    def _select_reference_filter(self, value):
        self.reference_filter = value
        for key, button in self.reference_filter_buttons.items():
            button.setChecked(key == value)
        self.load_data()

    def _set_rendered_cell(self, row, column, widget):
        item = self.table.item(row, column)
        if item is not None:
            item.setData(Qt.ItemDataRole.UserRole + 2, item.text())
            item.setText("")
        self.table.setCellWidget(row, column, widget)

    def _cell_value(self, row, column):
        item = self.table.item(row, column)
        if item is None:
            return ""
        value = item.data(Qt.ItemDataRole.UserRole + 2)
        return str(value if value is not None else item.text())

    def open_add_dialog(self):
        dlg = AddCheckDialog(self.db, self)
        if dlg.exec():
            self.load_data()

    def load_data(self):
        status = self._normalize_status_filter(self.filter_status.currentText())
        try:
            query_status = None if status == "__portfolio_group__" else status
            rows = self.db.get_checks_notes(status_filter=query_status) or []
            all_rows = self.db.get_checks_notes(status_filter=None) or []
        except Exception as e:
            show_error(self, f"Veri yüklenirken hata: {e}")
            rows = []
            all_rows = []

        def row_as_dict(value):
            try:
                return dict(value)
            except Exception:
                return value if isinstance(value, dict) else {}

        if status == "__portfolio_group__":
            rows = [
                row for row in rows
                if row_as_dict(row).get("status") in ("Portf\u00f6yde", "Ciro Edildi")
            ]

        all_dicts = [row_as_dict(row) for row in all_rows]
        selected_bank = self.bank_filter.currentText()
        banks = sorted({str(row.get("bank_name", "") or "").strip() for row in all_dicts if row.get("bank_name")})
        self.bank_filter.blockSignals(True)
        self.bank_filter.clear()
        self.bank_filter.addItem("Banka: T\u00fcm Bankalar")
        self.bank_filter.addItems(banks)
        if selected_bank in banks:
            self.bank_filter.setCurrentText(selected_bank)
        self.bank_filter.blockSignals(False)

        incoming_directions = ("Giri\u015f (Al\u0131nan)", "Al\u0131nan")
        tab_counts = {
            "all": len(all_dicts),
            "checks": sum(1 for row in all_dicts if row.get("type") == "\u00c7ek" and row.get("direction") in incoming_directions),
            "notes": sum(1 for row in all_dicts if row.get("type") == "Senet" and row.get("direction") in incoming_directions),
            "own": sum(1 for row in all_dicts if row.get("direction") in ("\u00c7\u0131k\u0131\u015f (Verilen)", "Verilen")),
            "endorsed": sum(1 for row in all_dicts if row.get("status") == "Ciro Edildi"),
        }
        for key, button in self.reference_filter_buttons.items():
            label = button.property("baseLabel") or button.text().split(" (")[0]
            button.setProperty("baseLabel", label)
            button.setText(f"{label} ({tab_counts[key]})" if key != "endorsed" else label)

        query = self.search_input.text().strip().casefold()
        bank_filter = self.bank_filter.currentText()
        start_date = self.date_start.date().toString("yyyy-MM-dd")
        end_date = self.date_end.date().toString("yyyy-MM-dd")
        filtered_rows = []
        for row in rows:
            row_values = row_as_dict(row)
            record_type = str(row_values.get("type", ""))
            direction = str(row_values.get("direction", ""))
            row_status = str(row_values.get("status", ""))
            if self.reference_filter == "checks" and not (record_type == "\u00c7ek" and direction in incoming_directions):
                continue
            if self.reference_filter == "notes" and not (record_type == "Senet" and direction in incoming_directions):
                continue
            if self.reference_filter == "own" and direction not in ("\u00c7\u0131k\u0131\u015f (Verilen)", "Verilen"):
                continue
            if self.reference_filter == "endorsed" and row_status != "Ciro Edildi":
                continue
            if bank_filter != "Banka: T\u00fcm Bankalar" and str(row_values.get("bank_name", "") or "") != bank_filter:
                continue
            due_value = str(row_values.get("due_date", "") or "")
            if due_value and due_value < start_date:
                continue
            if due_value and due_value > end_date:
                continue
            if query and not any(query in str(value or "").casefold() for value in row_values.values()):
                continue
            filtered_rows.append(row)
        rows = filtered_rows

        self.table.setRowCount(0)
        self._update_empty_state()
        portfolio_total = sum(float(row.get("amount", 0) or 0) for row in all_dicts if str(row.get("status", "")) == "Portf\u00f6yde")
        due_total = sum(float(row.get("amount", 0) or 0) for row in all_dicts if str(row.get("status", "")) not in ("Tahsil Edildi", "\u00d6dendi", "\u0130ade"))
        received_count = tab_counts["checks"] + tab_counts["notes"]
        own_count = tab_counts["own"]
        settled_total = sum(float(row.get("amount", 0) or 0) for row in all_dicts if str(row.get("status", "")) in ("Tahsil Edildi", "Ciro Edildi", "\u00d6dendi"))
        month_prefix = QDate.currentDate().toString("yyyy-MM")
        monthly_due = [row for row in all_dicts if str(row.get("due_date", "") or "").startswith(month_prefix)]
        if self._metric_values:
            self._metric_values["portfolio"].setText(self._format_display_money(portfolio_total))
            try_currency = CurrencyHelper.format_from_try(portfolio_total, db=self.db, currency_code="TRY")
            self.findChild(QLabel, "metric_detail_portfolio").setText(
                f"TL Kar\u015f\u0131l\u0131\u011f\u0131: {portfolio_total:,.0f} \u20ba"
            )
            self._metric_values["due"].setText(self._format_display_money(sum(float(row.get("amount", 0) or 0) for row in monthly_due)))
            primary = qc("text").name()
            muted = qc("text_muted").name()
            self._metric_values["received"].setText(
                f'<span style="color:{primary};font-weight:700">{received_count} Al\u0131nan</span> / '
                f'<span style="color:{muted}">{own_count} Kendi \u00c7ekimiz</span>'
            )
            self._metric_values["discounted"].setText(self._format_display_money(settled_total))
            due_soon_count = sum(
                1 for row in monthly_due
                if 0 <= QDate.currentDate().daysTo(QDate.fromString(str(row.get("due_date", "")), "yyyy-MM-dd")) <= 14
            )
            self.findChild(QLabel, "metric_detail_due").setText(
                f"Toplam: <b>{len(monthly_due)} Evrak</b>"
            )
            self.findChild(QLabel, "metric_badge_due").setText(
                f"{due_soon_count} \u00c7ek Yakla\u015ft\u0131"
            )
            incoming_total = sum(float(row.get("amount", 0) or 0) for row in all_dicts if row.get("direction") in incoming_directions)
            all_total = sum(float(row.get("amount", 0) or 0) for row in all_dicts) or 1.0
            coverage = incoming_total * 100 / all_total
            self.findChild(QLabel, "metric_detail_received").setText(
                f"Alacak G\u00fcvencesi: <b>%{coverage:.1f}</b>"
            )
            self.findChild(QLabel, "metric_badge_received").setText("Dengeli")
            self.findChild(QLabel, "metric_detail_discounted").setText(
                f"Takasta: <b>{sum(1 for row in all_dicts if row.get('status') == 'Ciro Edildi')} Bankada</b>"
            )
            self.findChild(QLabel, "metric_badge_discounted").setText("Akbank & Garanti")
        for idx_row, row in enumerate(rows):
            # Ensure row supports .get by converting to a dictionary type, handling sqlite3.Row specifically
            try:
                row_dict = dict(row)
            except Exception:
                row_dict = row if isinstance(row, dict) else {}
                
            rid = row["id"] if "id" not in row_dict else row_dict["id"]
            rtype = str(row_dict.get("type", ""))
            rdir = str(row_dict.get("direction", ""))
            bank = str(row_dict.get("bank_name", "") or "")
            branch = str(row_dict.get("branch_name", "") or "")
            bank_info = f"{bank}\n{branch}".strip()
            amount = float(row_dict.get("amount", 0) or 0)
            amount_str = self._format_display_money(amount)
            due = str(row_dict.get("due_date", "") or "")
            issuer = str(row_dict.get("issuer", "") or "")
            recipient = str(row_dict.get("recipient", "") or "")
            status_text = str(row_dict.get("status", "") or "")
            serial_number = str(row_dict.get("check_no", "") or row_dict.get("portfolio_no", "") or "-")

            r = self.table.rowCount()
            self.table.insertRow(r)
            select_item = QTableWidgetItem("")
            select_item.setData(Qt.ItemDataRole.UserRole, rid)
            select_item.setData(Qt.ItemDataRole.UserRole + 1, False)
            select_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 0, select_item)
            select_button = QPushButton()
            select_button.setCheckable(True)
            select_button.setFixedSize(16, 16)
            select_button.setStyleSheet(theme_qss(
                "QPushButton { background: @finance_surface_alt; border: 1px solid @border; "
                "border-radius: 4px; padding: 0; } QPushButton:checked { background: @accent; border-color: @accent; }"
            ))
            select_button.toggled.connect(
                lambda checked, item=select_item: item.setData(Qt.ItemDataRole.UserRole + 1, bool(checked))
            )
            select_wrapper = QWidget()
            select_layout = QHBoxLayout(select_wrapper)
            select_layout.setContentsMargins(0, 0, 0, 0)
            select_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            select_layout.addWidget(select_button)
            self.table.setCellWidget(r, 0, select_wrapper)
            self.table.setItem(r, 1, QTableWidgetItem(f"{idx_row + 1:02d}"))
            self.table.item(r, 1).setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            type_item = QTableWidgetItem(rtype)
            type_item.setForeground(qc("accent" if rtype == "\u00c7ek" else "finance_tertiary"))
            self.table.setItem(r, 2, type_item)
            type_badge = QLabel(rtype)
            type_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            type_badge.setStyleSheet(theme_qss(
                "QLabel { background: @finance_surface_alt; color: @accent; border: 1px solid @border; "
                "border-radius: 6px; padding: 3px 8px; font-size: 11px; font-weight: 700; }"
            ))
            type_wrapper = QWidget()
            type_layout = QHBoxLayout(type_wrapper)
            type_layout.setContentsMargins(0, 0, 0, 0)
            type_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            type_layout.addWidget(type_badge)
            self._set_rendered_cell(r, 2, type_wrapper)
            direction_item = QTableWidgetItem(
                "\u2199 Al\u0131nan" if rdir in incoming_directions else "\u2197 Verilen"
            )
            direction_item.setForeground(qc("success" if rdir in incoming_directions else "finance_tertiary"))
            self.table.setItem(r, 3, direction_item)
            direction_label = QLabel(direction_item.text())
            direction_label.setStyleSheet(theme_qss(
                f"color: @{'success' if rdir in incoming_directions else 'finance_tertiary'}; font-size: 12px;"
            ))
            direction_wrapper = QWidget()
            direction_layout = QHBoxLayout(direction_wrapper)
            direction_layout.setContentsMargins(5, 0, 0, 0)
            direction_layout.addWidget(direction_label)
            self._set_rendered_cell(r, 3, direction_wrapper)
            self.table.setItem(r, 4, QTableWidgetItem(f"{issuer}\n{recipient}".strip()))
            self.table.setItem(r, 5, QTableWidgetItem(bank_info))
            serial_display = serial_number
            if "-" in serial_number:
                prefix, separator, suffix = serial_number.partition("-")
                serial_display = f"{prefix}{separator}\n{suffix}"
            serial_item = QTableWidgetItem(serial_display)
            serial_item.setData(Qt.ItemDataRole.UserRole + 2, serial_number)
            serial_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 6, serial_item)
            self.table.setItem(r, 7, QTableWidgetItem(amount_str))
            self.table.setItem(r, 8, QTableWidgetItem(due))
            self.table.item(r, 1).setFont(QFont("JetBrains Mono", 11))
            self.table.item(r, 6).setFont(QFont("JetBrains Mono", 11))
            self.table.item(r, 7).setFont(QFont("JetBrains Mono", 13, QFont.Weight.Bold))
            self.table.item(r, 7).setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.item(r, 8).setFont(QFont("JetBrains Mono", 9))

            customer_cell = QWidget()
            customer_layout = QHBoxLayout(customer_cell)
            customer_layout.setContentsMargins(4, 2, 4, 2)
            customer_layout.setSpacing(13)
            initials = "".join(part[:1] for part in issuer.split()[:2]).upper() or "--"
            avatar = QLabel(initials)
            avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            avatar.setFixedSize(30, 30)
            avatar.setStyleSheet(theme_qss(
                "QLabel { background: @finance_surface_alt; color: @accent; border: 1px solid @border; "
                "border-radius: 6px; font-size: 10px; font-weight: 700; }"
            ))
            avatar_slot = QWidget()
            avatar_layout = QVBoxLayout(avatar_slot)
            avatar_layout.setContentsMargins(0, 0, 0, 0)
            avatar_layout.addStretch(1)
            avatar_layout.addWidget(avatar, 0, Qt.AlignmentFlag.AlignCenter)
            avatar_layout.addStretch(1)
            customer_text = QVBoxLayout()
            customer_text.setSpacing(10)
            customer_text.setContentsMargins(0, 5, 0, 0)
            customer_text.setAlignment(Qt.AlignmentFlag.AlignTop)
            customer_display = issuer.replace(" (", "\n(")
            customer_name = QLabel(customer_display)
            customer_name.setWordWrap(True)
            customer_name.setMinimumHeight(85 if len(customer_display) >= 30 else (68 if len(customer_display) >= 20 else 42))
            customer_name.setStyleSheet(theme_qss("color: @text; font-size: 14px; font-weight: 700;"))
            customer_meta = QLabel(recipient)
            customer_meta.setWordWrap(True)
            customer_meta.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px;"))
            customer_text.addWidget(customer_name)
            customer_text.addWidget(customer_meta)
            customer_text_widget = QWidget()
            customer_text_widget.setLayout(customer_text)
            customer_layout.addWidget(avatar_slot, 0, Qt.AlignmentFlag.AlignVCenter)
            customer_layout.addWidget(customer_text_widget, 1, Qt.AlignmentFlag.AlignTop)
            self._set_rendered_cell(r, 4, customer_cell)

            bank_cell = QWidget()
            bank_layout = QVBoxLayout(bank_cell)
            bank_layout.setContentsMargins(5, 26, 4, 2)
            bank_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
            bank_name = QLabel(bank)
            bank_name.setWordWrap(True)
            bank_name.setStyleSheet(theme_qss("color: @text; font-size: 14px; font-weight: 600;"))
            bank_branch = QLabel(branch)
            bank_branch.setWordWrap(True)
            bank_branch.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px;"))
            bank_layout.addWidget(bank_name)
            bank_layout.addWidget(bank_branch)
            self._set_rendered_cell(r, 5, bank_cell)

            amount_cell = QWidget()
            amount_layout = QVBoxLayout(amount_cell)
            amount_layout.setContentsMargins(4, 2, 0, 2)
            amount_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            amount_primary = QLabel(amount_str)
            amount_primary.setAlignment(Qt.AlignmentFlag.AlignCenter)
            amount_primary.setStyleSheet(theme_qss("color: @text; font: 700 16px 'JetBrains Mono';"))
            amount_try = CurrencyHelper.format_from_try(amount, db=self.db, currency_code="TRY")
            amount_secondary = QLabel(f"\u2248 {amount_try}")
            amount_secondary.setAlignment(Qt.AlignmentFlag.AlignCenter)
            amount_secondary.setStyleSheet(theme_qss("color: @text_muted; font: 10px 'JetBrains Mono';"))
            amount_layout.addWidget(amount_primary)
            amount_layout.addWidget(amount_secondary)
            self._set_rendered_cell(r, 7, amount_cell)

            due_cell = QWidget()
            due_layout = QVBoxLayout(due_cell)
            due_layout.setContentsMargins(5, 26, 4, 2)
            due_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
            due_label = QLabel(f"{due[:5]}\n{due[5:]}" if len(due) == 10 else due)
            due_label.setStyleSheet(theme_qss("color: @text; font: 10px 'JetBrains Mono';"))
            due_layout.addWidget(due_label)
            due_date = QDate.fromString(due, "yyyy-MM-dd")
            if due_date.isValid():
                days_left = QDate.currentDate().daysTo(due_date)
                due_detail = QLabel(f"{days_left} g\u00fcn kald\u0131")
                due_detail.setStyleSheet(theme_qss("color: @warning; font-size: 10px;"))
                due_layout.addWidget(due_detail)
            self._set_rendered_cell(r, 8, due_cell)

            status_item = QTableWidgetItem(status_text)
            if status_text in ("Tahsil Edildi", "Ödendi"):
                status_item.setForeground(qc("success"))
            elif status_text == "Karşılıksız":
                status_item.setForeground(qc("selection_text"))
                status_item.setBackground(qc("danger"))
            elif status_text == "Ciro Edildi":
                status_item.setForeground(qc("accent"))
            elif status_text == "Portföyde":
                status_item.setForeground(qc("warning"))
            elif status_text == "İade":
                status_item.setForeground(qc("text_muted"))
            status_item.setFont(QFont(DesignTokens.FONT_NAME, 10, QFont.Weight.Bold))

            self.table.setItem(r, 9, status_item)
            display_status = "Tahsilde\n(Takas)" if status_text == "Ciro Edildi" else status_text
            status_chip = QLabel(f"\u25cf {display_status}")
            status_chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
            status_token = "success" if status_text in ("Portf\u00f6yde", "Tahsil Edildi", "\u00d6dendi") else (
                "warning" if status_text == "Ciro Edildi" else "danger"
            )
            status_background = "finance_success_bg" if status_token == "success" else (
                "finance_warning_bg" if status_token == "warning" else "danger_bg"
            )
            status_chip.setMinimumWidth(96)
            status_chip.setFixedHeight(52 if status_text == "Ciro Edildi" else 36)
            status_chip.setStyleSheet(theme_qss(
                f"QLabel {{ background: @{status_background}; color: @{status_token}; "
                f"border: 1px solid @{status_token}; border-radius: 18px; padding: 5px 10px; "
                "font-size: 11px; font-weight: 700; }"
            ))
            status_wrapper = QWidget()
            status_layout = QHBoxLayout(status_wrapper)
            status_layout.setContentsMargins(0, 0, 0, 0)
            status_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            status_layout.addWidget(status_chip)
            self._set_rendered_cell(r, 9, status_wrapper)
            action_cell = QWidget()
            action_layout = QHBoxLayout(action_cell)
            action_layout.setContentsMargins(4, 2, 4, 2)
            action_layout.setSpacing(6)
            action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            detail_button = QPushButton("\u22ee")
            detail_button.setFixedSize(28, 38)
            detail_button.setToolTip("Se\u00e7ili evrak\u0131n ayr\u0131nt\u0131lar\u0131n\u0131 g\u00f6r\u00fcnt\u00fcle")
            detail_button.setStyleSheet(theme_qss(
                "QPushButton { background: @surface_alt; color: @text; border: 1px solid @border; "
                "border-radius: 6px; padding: 2px 3px; font-size: 18px; }"
            ))
            detail_button.clicked.connect(lambda _checked=False, check_id=rid: self.show_details(check_id))
            if status_text not in ("Tahsil Edildi", "Ciro Edildi", "\u00d6dendi"):
                collect_button = QPushButton("Tahsil\nEt")
                collect_button.setFixedSize(58, 52)
                collect_button.setToolTip("Evrak\u0131 tahsil edildi olarak i\u015faretle")
                collect_button.setStyleSheet(theme_qss(
                    "QPushButton { background: @finance_surface_alt; color: @text; border: 1px solid @border; "
                    "border-radius: 6px; padding: 2px 3px; font-size: 11px; }"
                ))
                collect_button.clicked.connect(
                    lambda _checked=False, check_id=rid: self.change_status(check_id, "Tahsil Edildi")
                )
                action_layout.addWidget(collect_button)
                clearance_button = QPushButton("Takasa\nVer")
                clearance_button.setFixedSize(66, 52)
                clearance_button.setToolTip("Bankaya takas i\u015flemi ba\u015flat")
                clearance_button.setStyleSheet(theme_qss(
                    "QPushButton { background: @surface; color: @text; border: 1px solid @border; "
                    "border-radius: 6px; padding: 2px 3px; font-size: 11px; }"
                ))
                clearance_button.clicked.connect(
                    lambda _checked=False, check_id=rid: self.change_status(check_id, "Ciro Edildi")
                )
                action_layout.addWidget(clearance_button)
            elif status_text == "Ciro Edildi":
                receipt_button = QPushButton("Banka\nDekontu")
                receipt_button.setFixedSize(72, 52)
                receipt_button.setToolTip("Banka ve takas bilgilerini g\u00f6r\u00fcnt\u00fcle")
                receipt_button.setStyleSheet(theme_qss(
                    "QPushButton { background: @surface_alt; color: @text; border: 1px solid @border; "
                    "border-radius: 6px; padding: 2px 3px; font-size: 11px; }"
                ))
                receipt_button.clicked.connect(lambda _checked=False, check_id=rid: self.show_details(check_id))
                action_layout.addWidget(receipt_button)
                refund_button = QPushButton("\u0130ade\nAl")
                refund_button.setFixedSize(60, 52)
                refund_button.setToolTip("Takas i\u015flemindeki evrak\u0131 iade al")
                refund_button.setStyleSheet(theme_qss(
                    "QPushButton { background: @surface_alt; color: @text; border: 1px solid @border; "
                    "border-radius: 6px; padding: 2px 3px; font-size: 11px; }"
                ))
                refund_button.clicked.connect(lambda _checked=False, check_id=rid: self.change_status(check_id, "\u0130ade"))
                action_layout.addWidget(refund_button)
            action_layout.addWidget(detail_button)
            self.table.setCellWidget(r, 10, action_cell)
            self.table.setRowHeight(r, 170 if idx_row == 0 else 132)
        self._update_empty_state()

    def open_context_menu(self, position):
        if not is_context_menu_enabled(self.db, page_id=106):
            return
        item = self.table.itemAt(position)
        if not item:
            return

        row = item.row()
        check_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        current_status = self._cell_value(row, 9)

        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QAction

        menu = QMenu()
        detail_action = QAction("Detay Görüntüle", self)
        detail_action.triggered.connect(lambda: self.show_details(check_id))
        menu.addAction(detail_action)
        menu.addSeparator()

        status_menu = menu.addMenu("Durum Değiştir")
        statuses = ["Portföyde", "Tahsil Edildi", "Ciro Edildi", "Ödendi", "Karşılıksız", "İade"]
        for st in statuses:
            if st == current_status:
                continue
            action = QAction(st, self)
            action.triggered.connect(lambda checked, new_status=st: self.change_status(check_id, new_status))
            status_menu.addAction(action)

        menu.exec(self.table.viewport().mapToGlobal(position))

    def change_status(self, check_id, new_status):
        if not self.db.update_check_status(check_id, new_status):
            show_error(self.main_window, "Durum güncellenemedi.")
            return

        if new_status in ["Tahsil Edildi", "Ödendi", "Ciro Edildi"]:
            try:
                self.db.cursor.execute(
                    "SELECT type, direction, amount, bank_name, issuer, recipient FROM checks_notes WHERE id=?",
                    (check_id,),
                )
                row = self.db.cursor.fetchone()
                if row:
                    c_type = str(row[0] or "")
                    direction = str(row[1] or "")
                    amount = float(row[2] or 0.0)
                    bank = str(row[3] or "")
                    issuer = str(row[4] or "")
                    recipient = str(row[5] or "")
                    
                    # 'Alınan' çek tahsil edilince Kasa ARTAR (Gelir), Çek/Senet AZALIR (Gider)
                    # 'Verilen' çek ödenince Kasa AZALIR (Gider), Çek/Senet ARTAR (Gelir - Borç kapanır)
                    if direction == "Giriş (Alınan)" and new_status == "Tahsil Edildi":
                        bank_txn_type = "Gelir"
                        rev_txn_type = "Gider"
                    elif direction == "Çıkış (Verilen)" and new_status == "Ödendi":
                        bank_txn_type = "Gider"
                        rev_txn_type = "Gelir"
                    elif new_status == "Ciro Edildi":
                        # Ciro: Alınan çek başkasına verilir. Çek/Senet AZALIR (Gider). Kasa etkilenmez (genelde).
                        bank_txn_type = None
                        rev_txn_type = "Gider"
                    else:
                        bank_txn_type = None
                        rev_txn_type = None
                    
                    bank_id = None
                    if bank_txn_type: # Only ask for bank selection if there's a bank transaction
                        try:
                            if hasattr(self.db, 'get_bank_accounts'):
                                banks = self.db.get_bank_accounts()
                                if banks:
                                    from PyQt6.QtWidgets import QDialog, QVBoxLayout, QComboBox, QPushButton, QLabel
                                    dlg = QDialog(self.main_window)
                                    dlg.setWindowTitle("Banka/Kasa Seçimi")
                                    dlg.setStyleSheet(theme_qss("background-color: @surface; border-radius: 8px;"))
                                    layout = QVBoxLayout(dlg)
                                    amount_text = self._format_display_money(amount)
                                    layout.addWidget(QLabel(f"Bu işlem banka/kasa bakiyenizi etkileyecektir ({amount_text} {bank_txn_type}).\nLütfen işlem yapılacak hesabı seçiniz:"))
                                    cmb = QComboBox(dlg)
                                    cmb.setStyleSheet(theme_qss(DesignTokens.get_combobox_qss()))
                                    cmb.addItem("Banka/Kasa Seçmeyin (Sadece Statü Değiştir)", -1)
                                    for b in banks:
                                        bid = b.get('id') if isinstance(b, dict) else b[0]
                                        bname = b.get('bank_name') if isinstance(b, dict) else b[1]
                                        cmb.addItem(bname, bid)
                                    layout.addWidget(cmb)
                                    b_ok = QPushButton("Onayla", dlg)
                                    b_ok.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="sm")))
                                    b_ok.clicked.connect(dlg.accept)
                                    layout.addWidget(b_ok)
                                    if dlg.exec():
                                        selected = cmb.currentData()
                                        if selected != -1:
                                            bank_id = selected
                        except Exception as e:
                            logger.error(f"Banka seçim dialogu hatası: {e}")

                    customer_name = issuer if direction == "Giriş (Alınan)" else recipient
                    desc_base = f"{c_type} {new_status} - {bank} - {issuer}/{recipient} (ID: {check_id})"

                    if rev_txn_type:
                        # 1. Ters Kayıt (Çek/Senet portföyden çıkışı)
                        self.db.add_transaction(
                            t_type=rev_txn_type,
                            category=f"{c_type} Portföy Çıkışı",
                            amount=amount,
                            description=f"{desc_base} - Portföy Çıkışı",
                            customer_name=customer_name,
                            payment_method="Çek/Senet"
                        )
                    
                    if bank_txn_type and bank_id is not None:
                        # 2. Banka/Kasa Kaydı (Gerçek para hareketi)
                        self.db.add_transaction(
                            t_type=bank_txn_type,
                            category=f"Banka/Kasa Hareketi ({c_type})",
                            amount=amount,
                            description=f"{desc_base} - Kasa İşlemi",
                            bank_account_id=bank_id,
                            customer_name=customer_name,
                            payment_method="Çek/Senet"
                        )
                        
                    if rev_txn_type or (bank_txn_type and bank_id is not None):
                        show_success(self.main_window, "Finans/Kasa kayıtları oluşturuldu.")
            except Exception as e:
                logger.error(f"Finans kaydı oluşturulurken hata: {e}")

        show_success(self.main_window, f"Durum güncellendi: {new_status}")
        self.load_data()

    def on_row_double_click(self, row, col):
        check_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self.show_details(check_id)

    def show_details(self, check_id):
        dlg = QDialog(self)
        dlg.setWindowTitle("Çek / Senet Detay")
        dlg.setFixedSize(420, 320)
        dlg.setStyleSheet(theme_qss("background: @surface;"))

        layout = QVBoxLayout(dlg)
        found_data = {}
        for r in range(self.table.rowCount()):
            if self.table.item(r, 0).data(Qt.ItemDataRole.UserRole) == check_id:
                found_data = {
                    'T\u00fcr': self._cell_value(r, 2),
                    'Y\u00f6n': self._cell_value(r, 3),
                    'Ke\u015fideci/Bor\u00e7lu': self._cell_value(r, 4),
                    'Banka': self._cell_value(r, 5),
                    'Evrak / Seri No': self._cell_value(r, 6),
                    'Tutar': self._cell_value(r, 7),
                    'Vade': self._cell_value(r, 8),
                    'Durum': self._cell_value(r, 9),
                }
                break

        if not found_data:
            return

        form = QFormLayout()
        for k, v in found_data.items():
            form.addRow(f"<b>{k}:</b>", QLabel(v))
        layout.addLayout(form)

        btn_close = QPushButton("Kapat")
        btn_close.clicked.connect(dlg.accept)
        btn_close.setStyleSheet(theme_qss("background-color: @surface_alt; color: @text; padding: 8px; border-radius: 4px;"))
        layout.addWidget(btn_close)
        dlg.exec()


class AddCheckDialog(BaseModernDialog):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)

    def __init__(self, db, parent=None):
        super().__init__(parent, title="Çek / Senet Girişi", width=450, height=580)
        self.db = db
        self.set_footer_visible(True, 68)
        self.setup_ui()

        self._wire_ui_signals()

    def setup_ui(self):
        form = QFormLayout()

        self.cmb_type = QComboBox()
        self.cmb_type.addItems(["Çek", "Senet"])
        form.addRow("Evrak Tipi:", self.cmb_type)

        self.cmb_dir = QComboBox()
        self.cmb_dir.addItems(["Giriş (Alınan)", "Çıkış (Verilen)"])
        form.addRow("Yön:", self.cmb_dir)

        self.txt_amount = QDoubleSpinBox()
        self.txt_amount.setRange(0, 100000000)
        self.txt_amount.setSuffix(f" {CurrencyHelper.get_label(db=self.db)}")
        self.txt_amount.setFixedHeight(38)
        self.txt_amount.setStyleSheet(theme_qss(
            "QDoubleSpinBox { background: @surface_alt; color: @text; border: 1px solid @border; border-radius: 6px; padding: 4px 8px; }"
            "QDoubleSpinBox::up-button, QDoubleSpinBox::down-button { width: 0; border: none; }"
        ))
        form.addRow("Tutar:", self.txt_amount)

        self.txt_bank = QLineEdit()
        form.addRow("Banka:", self.txt_bank)

        self.txt_branch = QLineEdit()
        form.addRow("Şube:", self.txt_branch)

        self.txt_issuer = QLineEdit()
        form.addRow("Keşideci/Borçlu:", self.txt_issuer)

        self.txt_recipient = QLineEdit()
        form.addRow("Alıcı:", self.txt_recipient)

        self.date_due = QDateEdit()
        self.date_due.setCalendarPopup(True)
        self.date_due.setDate(QDate.currentDate())
        form.addRow("Vade Tarihi:", self.date_due)

        self.cmb_status = QComboBox()
        self.cmb_status.addItems(["Portföyde", "Tahsil Edildi", "Ciro Edildi", "Ödendi", "Karşılıksız", "İade"])
        form.addRow("Durum:", self.cmb_status)

        self.content_layout.addLayout(form)
        self.clear_footer()
        self.add_cancel_button("Iptal")
        self.add_button("Kaydet", "success", self.save)

    def _wire_ui_signals(self):
        self.cmb_type.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_dir.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_status.currentIndexChanged.connect(self._on_ui_widget_changed)

    def save(self):
        data = {
            "type": self.cmb_type.currentText(),
            "direction": self.cmb_dir.currentText(),
            "amount": float(self.txt_amount.value()),
            "bank_name": self.txt_bank.text().strip(),
            "branch_name": self.txt_branch.text().strip(),
            "issuer": self.txt_issuer.text().strip(),
            "recipient": self.txt_recipient.text().strip(),
            "due_date": self.date_due.date().toString("yyyy-MM-dd"),
            "status": self.cmb_status.currentText(),
        }

        if data["amount"] <= 0:
            show_error(self, "Tutar 0'dan buyuk olmalidir.")
            return
        if not data["issuer"] and not data["recipient"]:
            show_error(self, "Kesideci/Borclu veya Alici alanlarindan en az biri doldurulmalidir.")
            return

        try:
            if self.db.add_check_note(data):
                # Türkiye Finans/Muhasebe Standartlarına Göre İlk Kayıt:
                # Çek/Senet alındığında "Alınan Çekler/Senetler" hesabına (Gelir yansıması/Varlık artışı)
                # Çek/Senet verildiğinde "Verilen Çekler/Senetler" hesabına (Gider yansıması/Yükümlülük artışı) kaydedilir.
                try:
                    c_type = data["type"]
                    direction = data["direction"]
                    amount = data["amount"]
                    issuer = data["issuer"]
                    recipient = data["recipient"]
                    
                    if direction == "Giriş (Alınan)":
                        txn_type = "Gelir"
                        category = f"Alınan {c_type}"
                        desc = f"{c_type} Alındı - Düzenleyen: {issuer} (Vade: {data['due_date']})"
                        customer_name = issuer if issuer else None
                    else:
                        txn_type = "Gider"
                        category = f"Verilen {c_type}"
                        desc = f"{c_type} Verildi - Alıcı: {recipient} (Vade: {data['due_date']})"
                        customer_name = recipient if recipient else None
                        
                    self.db.add_transaction(
                        t_type=txn_type,
                        category=category,
                        amount=amount,
                        description=desc,
                        customer_name=customer_name,
                        payment_method="Çek/Senet"
                    )
                except Exception as fin_err:
                    logger.error(f"Çek/Senet finans ilk kayıt hatası: {fin_err}")
                    
                show_success(self, "Kayıt eklendi ve finans modülüne işlendi.")
                self.accept()
            else:
                show_error(self, "Kayıt eklenemedi.")
        except Exception as e:
            show_error(self, f"Kaydetme hatası: {e}")
