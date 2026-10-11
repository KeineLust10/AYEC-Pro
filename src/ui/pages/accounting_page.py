# -*- coding: utf-8 -*-

from PyQt6.QtCore import Qt, QTimer, QEvent, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import (
    QAbstractItemView, QComboBox, QFrame, QGridLayout, QHBoxLayout,
    QHeaderView, QLabel, QPushButton, QTableWidget, QTabWidget, QVBoxLayout, QWidget, QButtonGroup, QLineEdit
)
from src.ui.components.modern_dialog import ModernDialog
from src.ui.widgets.empty_state import EmptyState
from src.utils.finance_manager import FinanceManager
from src.utils.currency_helper import CurrencyHelper
from src.utils.theme_colors import theme_qss
from src.ui.widgets.financial_flow_sparkline import FinancialFlowSparkline
from src.ui.widgets.financial_reference_controls import FinancialMetricGlyph, FinancialReferenceActionButton, FinancialReferenceLedgerDelegate, FinancialReferenceIconButton, ReferenceMetricValueLabel
from src.ui.widgets.modern_inputs import ModernComboBox
from src.utils.design_system import DesignTokens

# Mixin Imports
from src.ui.pages._accounting_base_mixin import AccountingBaseMixin
from src.ui.pages._accounting_fiscal_mixin import AccountingFiscalMixin
from src.ui.pages._accounting_data_mixin import AccountingDataMixin, LedgerWorker, FinanceCard
from src.ui.pages._accounting_table_mixin import AccountingTableMixin
from src.ui.pages._accounting_func_mixin import AccountingFuncMixin



class ArchiveSelectionDialog(ModernDialog):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    def __init__(self, parent, archives):
        super().__init__(parent, title="Ge\u00e7mi\u015f Y\u0131l Ar\u015fivi Se\u00e7in", width=640, height=320, blur_background=True)
        self.selected_archive = None
        self.archives = archives
        self.combo = QComboBox()
        for archive in self.archives:
            year = archive.replace("archive_", "").replace(".db", "") if archive.startswith("archive_") else archive
            label = f"Mali Y\u0131l {year}" if year.isdigit() else archive
            self.combo.addItem(label, archive)
        self.combo.setStyleSheet(theme_qss("QComboBox { padding: 10px; border: 1px solid @border; border-radius: 8px; background-color: @surface_alt; color: @text; font-size: 13px; font-weight: 600; } QComboBox::drop-down { border: none; } QComboBox QAbstractItemView { background-color: @surface_alt; border: 1px solid @border; selection-background-color: @selection_bg; selection-color: @selection_text; }"))
        msg = QLabel("İncelenecek Arşiv Veritabanı:")
        msg.setStyleSheet(theme_qss("color: @text_muted; font-size: 13px; font-weight: 600;"))
        self.content_layout.addWidget(msg); self.content_layout.addSpacing(10); self.content_layout.addWidget(self.combo); self.content_layout.addStretch()

        btn_layout = QHBoxLayout(); btn_layout.setSpacing(10); btn_layout.addStretch()
        btn_cancel = QPushButton("İptal")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet(theme_qss("background: transparent; color: @text_muted; border-radius: 6px; padding: 8px 16px; font-weight: bold; border: 1px solid @border;"))
        btn_cancel.clicked.connect(self.reject)

        btn_ok = QPushButton("İncele")
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.setStyleSheet(theme_qss("background: @success; color: @selection_text; border-radius: 6px; padding: 8px 30px; font-weight: bold; border:none;"))
        btn_ok.clicked.connect(self.accept_selection)

        btn_layout.addWidget(btn_cancel); btn_layout.addWidget(btn_ok); self.content_layout.addLayout(btn_layout)
        self._wire_ui_signals()

    def _wire_ui_signals(self):
        self.combo.currentIndexChanged.connect(self._on_ui_widget_changed)

    def accept_selection(self):
        self.selected_archive = self.combo.currentData() or self.combo.currentText(); self.accept()


class FiscalControlsDialog(ModernDialog):
    """Keep fiscal-year actions in one focused, shared-footer dialog."""

    def __init__(self, page):
        super().__init__(
            page,
            title="Mali Y\u0131l Kontrolleri",
            width=900,
            height=300,
            blur_background=True,
        )
        self.page = page
        message = QLabel(
            "Aktif mali y\u0131l\u0131 se\u00e7in veya d\u00f6nem i\u015flemlerinden birini \u00e7al\u0131\u015ft\u0131r\u0131n."
        )
        message.setWordWrap(True)
        message.setStyleSheet(
            theme_qss("color: @text_muted; font-size: 13px; border: none;")
        )
        self.content_layout.addWidget(message)
        self.year_combo = QComboBox()
        for index in range(page.cmb_fiscal_year.count()):
            self.year_combo.addItem(
                page.cmb_fiscal_year.itemText(index),
                page.cmb_fiscal_year.itemData(index),
            )
        self.year_combo.setCurrentIndex(page.cmb_fiscal_year.currentIndex())
        self.year_combo.currentIndexChanged.connect(self._select_year)
        self.content_layout.addWidget(self.year_combo)
        self.content_layout.addStretch()

        self.add_button(
            "Ar\u015fiv",
            "secondary",
            lambda: self._run(page.handle_archive_action),
        )
        self.add_button(
            "Yenile",
            "secondary",
            lambda: self._run(page.refresh_data),
        )
        self.add_button(
            "Yeni Mali Y\u0131la Ge\u00e7i\u015f",
            "warning",
            lambda: self._run(page.handle_fiscal_rollover),
        )
        self.add_button(
            "A\u00e7\u0131l\u0131\u015f Fi\u015fleri",
            "secondary",
            lambda: self._run(lambda: page.apply_filter("OPENING")),
        )
        self.add_button(
            "Y\u0131lba\u015f\u0131 Raporu",
            "primary",
            lambda: self._run(page.show_fiscal_opening_report),
        )
        self.add_button("Kapat", "ghost", self.reject)

    def _select_year(self, index):
        if index >= 0:
            self.page.cmb_fiscal_year.setCurrentIndex(index)

    def _run(self, callback):
        callback()


class AccountingPage(
    QWidget,
    AccountingBaseMixin,
    AccountingFiscalMixin,
    AccountingDataMixin,
    AccountingTableMixin,
    AccountingFuncMixin,
):
    def __init__(self, db, main_window):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.finance_manager = FinanceManager(db)
        self.ledger_data = []
        self._expanded_ledger_dates = set()
        self._ledger_groups_initialized = False
        self._current_filter_key = "ALL"
        self._ledger_period = "fiscal"
        self._ledger_search = ""
        self._ledger_search_timer = QTimer(self)
        self._ledger_search_timer.setSingleShot(True)
        self._ledger_search_timer.timeout.connect(self.refresh_data)
        self.worker = None
        self._refresh_lock = False
        self._pending_refresh = False
        self.ledger_current_page = 0
        self.ledger_page_limit = 100
        self.ledger_has_more = False
        self.card_widgets = []
        self.quick_action_buttons = []
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.timeout.connect(self.refresh_data)
        self.setup_ui()
        if self.main_window and hasattr(self.main_window, "financial_data_changed"):
            self.main_window.financial_data_changed.connect(self.refresh_data)
    def setup_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()
        self.tab_main = QWidget(); self.tabs.addTab(self.tab_main, "Finansal \u00d6zet"); root.addWidget(self.tabs)
        self.tabs.tabBar().hide()

        layout = QVBoxLayout(self.tab_main)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.header_frame = QFrame()
        self.header_frame.setStyleSheet(theme_qss(
            "background: @finance_surface; border-radius: 4px; border: 1px solid @finance_outline;"
        ))
        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(8, 4, 8, 4)
        lbl_title = QLabel("Finansal Dashboard & Defter Takibi")
        header_layout.addWidget(FinancialMetricGlyph("bank", "finance_action_collection"))
        lbl_title.setStyleSheet(theme_qss("font-size:13px;font-weight:700;color:@finance_text;border:none;background:transparent;"))
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        layout.addWidget(self.header_frame)

        summary_grid = QGridLayout()
        summary_grid.setSpacing(8)
        self.reference_metric_values = {}
        for column, (key, title, detail, color, glyph) in enumerate((
            ("gross_revenue", "TOPLAM C\u0130RO", "Br\u00fct Sat\u0131\u015f (KDV Dahil)", "@finance_text", "trend_up"),
            ("expenses", "MAL\u0130YET VE G\u0130DER", "Al\u0131\u015f + Operasyonel", "@finance_tertiary", "trend_down"),
            ("pocket_net", "NET K\u00c2R", "Gelir - Gider Net", "@finance_secondary", "wallet"),
            ("hot_cash", "SICAK NAK\u0130T & BANKA", "Kasa ve banka mevcudu", "@finance_text", "bank"),
            ("pending", "BEKLEYEN ALACAKLAR", "Tahsil edilmemi\u015f bakiye", "@finance_tertiary", "pending"),
        )):
            metric = QFrame()
            metric.setObjectName("financialReferenceMetric")
            metric.setMinimumHeight(100)
            metric.setMaximumHeight(112)
            metric.setStyleSheet(theme_qss(f"""
                QFrame#financialReferenceMetric {{ background: @finance_surface; border: none; border-right: 3px solid {color}; border-radius: 4px; }}
                QLabel {{ border: none; }}
            """))
            metric_layout = QVBoxLayout(metric)
            metric_layout.setContentsMargins(10, 8, 10, 8)
            metric_layout.setSpacing(2)
            title_row = QHBoxLayout()
            title_row.setContentsMargins(0, 0, 0, 0)
            title_row.setSpacing(4)
            title_label = QLabel(title + " (" + CurrencyHelper.get_code(self.db) + ")")
            title_label.setStyleSheet(theme_qss("color: @finance_text_muted; font-size: 10px; font-weight: 700;"))
            title_row.addWidget(title_label, 1)
            title_row.addWidget(FinancialMetricGlyph(glyph, color.lstrip("@")))
            value_label = ReferenceMetricValueLabel(primary_token=color.lstrip("@"))
            self.reference_metric_values[key] = value_label
            value_label.setStyleSheet(theme_qss(f"color: {color}; font-size: 23px; font-weight: 800;"))
            detail_label = QLabel(detail)
            detail_label.setStyleSheet(theme_qss("color: @finance_text_muted; font-size: 10px;"))
            metric_layout.addLayout(title_row); metric_layout.addWidget(value_label); metric_layout.addWidget(detail_label)
            summary_grid.addWidget(metric, 0, column)

        self.btn_archive = QPushButton("Ar\u015fiv (Ge\u00e7mi\u015f)")
        self.btn_archive.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_archive.clicked.connect(self.handle_archive_action)

        self.cmb_fiscal_year = ModernComboBox()
        self.cmb_fiscal_year.setMinimumWidth(120)
        self.cmb_fiscal_year.currentIndexChanged.connect(self.handle_fiscal_year_changed)
        self.cmb_fiscal_year.setStyleSheet(theme_qss("QComboBox{padding:2px 6px;border:1px solid @finance_outline;border-radius:4px;background:@finance_surface_alt;color:@finance_text;font-weight:700;}QComboBox::drop-down{border:none;width:20px;}"))
        self.cmb_fiscal_year.set_reference_chevron()

        command_frame = QFrame()
        command_frame.setStyleSheet(theme_qss(
            "background: @finance_canvas; border: none; border-radius: 4px;"
        ))
        command_layout = QHBoxLayout(command_frame)
        command_layout.setContentsMargins(0, 0, 0, 0)
        command_layout.setSpacing(4)
        period_bar = QFrame()
        period_bar.setObjectName("financialReferencePeriodBar")
        period_bar.setStyleSheet(theme_qss("QFrame#financialReferencePeriodBar { background: @finance_canvas; border: 1px solid @finance_outline; border-radius: 4px; }"))
        period_layout = QHBoxLayout(period_bar)
        period_layout.setContentsMargins(2, 2, 2, 2)
        period_layout.setSpacing(0)
        self.reference_period_buttons = {}
        self.reference_period_group = QButtonGroup(self)
        for period, label in (("today", "Bug\u00fcn"), ("last7", "Son 7 G\u00fcn"), ("month", "Bu Ay"), ("fiscal", "Y\u0131ll\u0131k")):
            button = QPushButton(label)
            button.setCheckable(True)
            button.setChecked(period == self._ledger_period)
            button.setFixedHeight(26)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(theme_qss("QPushButton { background: transparent; color: @finance_text_muted; border: none; border-radius: 4px; padding: 2px 8px; font-size: 10px; font-weight: 700; } QPushButton:checked { background: @finance_primary; color: @finance_primary_text; }"))
            button.clicked.connect(lambda checked=False, key=period: self._set_reference_period(key))
            self.reference_period_group.addButton(button)
            self.reference_period_buttons[period] = button
            period_layout.addWidget(button)
        command_layout.addWidget(period_bar)
        self.btn_archive.setFixedHeight(28)
        self.btn_archive.setStyleSheet(theme_qss("background: @finance_surface_alt; color: @finance_text; border: 1px solid @finance_outline; border-radius: 4px; padding: 2px 6px; font-size: 10px;"))
        self.cmb_fiscal_year.setFixedHeight(28)
        self.reference_command_actions = []
        for label, color, slot, glyph in (("Gelir Ekle", "@finance_action_income", self.open_income_dialog, "income"), ("Gider Ekle", "@finance_action_expense", self.open_expense_dialog, "expense"), ("Tahsilat Al", "@finance_action_collection", self.open_collection_dialog, "collection")):
            button = self._build_toolbar_button(label, color, slot, glyph=glyph, stacked=False)
            self.reference_command_actions.append(button)
            command_layout.addWidget(button)
        command_layout.addStretch()
        command_layout.addWidget(self.btn_archive)
        command_layout.addWidget(self.cmb_fiscal_year)
        layout.addWidget(command_frame)
        # Keep the reference order: period/actions first, then the KPI cards.
        layout.addLayout(summary_grid)

        self.table_container = QFrame()
        self.table_container.setStyleSheet(theme_qss("background: @finance_surface; border-radius: 6px; border: 1px solid @finance_outline;"))
        table_layout = QVBoxLayout(self.table_container); table_layout.setContentsMargins(0, 0, 0, 0); table_layout.setSpacing(0)

        self.reference_ledger_header = QFrame()
        self.reference_ledger_header.setObjectName("financialReferenceLedgerHeader")
        self.reference_ledger_header.setFixedHeight(34)
        self.reference_ledger_header.setStyleSheet(theme_qss("QFrame#financialReferenceLedgerHeader { background: @finance_surface; border: none; border-bottom: 1px solid @finance_outline; }"))
        ledger_header_layout = QHBoxLayout(self.reference_ledger_header)
        ledger_header_layout.setContentsMargins(8, 2, 6, 2)
        ledger_header_layout.setSpacing(6)
        lbl_table = QLabel("Son Hareketler (Birle\u015fik Defter)")
        lbl_table.setStyleSheet(theme_qss("font-size: 13px; font-weight: 800; color: @finance_text; border: none; background: transparent; letter-spacing: 0px;"))
        ledger_header_layout.addWidget(lbl_table)
        self.reference_record_count = QLabel("0 Kay\u0131t Y\u00fckl\u00fc")
        self.reference_record_count.setStyleSheet(theme_qss("color: @finance_text_muted; font-size: 10px; font-weight: 700; border: none; background: transparent;"))
        ledger_header_layout.addWidget(self.reference_record_count)
        ledger_header_layout.addStretch()
        self.reference_ledger_search = QLineEdit()
        self.reference_ledger_search.setPlaceholderText("Fi\u015f, Ref, M\u00fc\u015fteri ara...")
        self.reference_ledger_search.setAccessibleName("Defterde ara")
        self.reference_ledger_search.setMaxLength(200)
        self.reference_ledger_search.setClearButtonEnabled(True)
        self.reference_ledger_search.setFixedHeight(26)
        self.reference_ledger_search.setMinimumWidth(160)
        self.reference_ledger_search.setMaximumWidth(230)
        self.reference_ledger_search.setStyleSheet(theme_qss("QLineEdit { background: @finance_canvas; color: @finance_text; border: 1px solid @finance_outline; border-radius: 4px; padding: 3px 6px; font-size: 10px; }"))
        self.reference_ledger_search.textChanged.connect(self._on_reference_search_changed)
        ledger_header_layout.addWidget(self.reference_ledger_search)
        self.reference_header_actions = []
        for label, glyph, callback in (("Excel \u0130ndir", "excel", self.export_to_excel), ("PDF Rapor", "pdf", self.export_to_pdf), ("Fi\u015f Yazd\u0131r", "print", self.print_ledger)):
            button = FinancialReferenceIconButton(label, glyph, self.reference_ledger_header)
            button.setStyleSheet(theme_qss("QPushButton { background: transparent; color: @finance_text_muted; border: none; border-radius: 4px; padding: 0; } QPushButton:hover { background: @finance_surface_alt; color: @finance_text; }"))
            button.clicked.connect(callback)
            self.reference_header_actions.append(button)
            ledger_header_layout.addWidget(button)
        table_layout.addWidget(self.reference_ledger_header)

        self.table = QTableWidget(); self.table.setColumnCount(8)
        self.table.setItemDelegate(FinancialReferenceLedgerDelegate(self.table))
        self._refresh_amount_headers()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True); self.table.setShowGrid(False); self.table.verticalHeader().setVisible(False)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus); self.table.setStyleSheet(self._modern_table_qss())

        h = self.table.horizontalHeader()
        for i in range(8): h.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents if i != 2 else QHeaderView.ResizeMode.Stretch)

        self.table.cellDoubleClicked.connect(self.on_table_double_click)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_table_context_menu)
        table_layout.addWidget(self.table)

        self.ledger_empty_state = EmptyState("Hen\u00fcz i\u015flem yok", "Finansal harekete ait kay\u0131t bulunamad\u0131.", parent=self); self.ledger_empty_state.hide()
        table_layout.addWidget(self.ledger_empty_state)

        self.ledger_pager_frame = QFrame()
        ledger_pager_layout = QHBoxLayout(self.ledger_pager_frame)
        ledger_pager_layout.setContentsMargins(6, 2, 8, 2)
        ledger_pager_layout.setSpacing(4)
        ledger_pager_layout.addStretch()
        self.ledger_prev_button = QPushButton("< \u00d6nceki")
        self.ledger_page_label = QLabel("Sayfa 1")
        self.ledger_next_button = QPushButton("Sonraki >")
        for button in (self.ledger_prev_button, self.ledger_next_button):
            button.setFixedHeight(24)
            button.setStyleSheet(theme_qss("QPushButton { background: @finance_surface_alt; color: @finance_text; border: 1px solid @finance_outline; border-radius: 4px; padding: 2px 6px; font-size: 10px; } QPushButton:disabled { color: @disabled_text; }"))
        self.ledger_page_label.setStyleSheet(theme_qss("color: @finance_text; border: none; background: transparent; font-size: 10px;"))
        self.ledger_prev_button.clicked.connect(self._ledger_prev_page)
        self.ledger_next_button.clicked.connect(self._ledger_next_page)
        ledger_pager_layout.addWidget(self.ledger_prev_button)
        ledger_pager_layout.addWidget(self.ledger_page_label)
        ledger_pager_layout.addWidget(self.ledger_next_button)
        ledger_pager_layout.addStretch()
        self._update_ledger_pagination()

        self.footer_frame = QFrame(); self.footer_frame.setFixedHeight(30)
        self.footer_frame.setObjectName("financialReferenceBalances")
        self.footer_frame.setStyleSheet(theme_qss("QFrame#financialReferenceBalances { background: transparent; border: none; }"))
        self.footer_layout = QHBoxLayout(self.footer_frame); self.footer_layout.setContentsMargins(8, 0, 8, 0)
        self.reference_ledger_footer = QFrame()
        self.reference_ledger_footer.setObjectName("financialReferenceFooter")
        self.reference_ledger_footer.setFixedHeight(32)
        self.reference_ledger_footer.setStyleSheet(theme_qss("QFrame#financialReferenceFooter { background: @finance_surface; border: none; border-top: 1px solid @finance_outline; border-bottom-left-radius: 6px; border-bottom-right-radius: 6px; }"))
        combined_footer = QHBoxLayout(self.reference_ledger_footer)
        combined_footer.setContentsMargins(0, 0, 0, 0)
        combined_footer.setSpacing(0)
        combined_footer.addWidget(self.footer_frame, 1)
        combined_footer.addWidget(self.ledger_pager_frame)
        table_layout.addWidget(self.reference_ledger_footer)

        self.right_panel = QFrame()
        self.right_panel.setMinimumWidth(262)
        self.right_panel.setMaximumWidth(262)
        self.right_panel.setStyleSheet(theme_qss("background: transparent; border: none;"))
        self.right_panel.installEventFilter(self)
        right_layout = QVBoxLayout(self.right_panel); right_layout.setContentsMargins(8, 0, 0, 0); right_layout.setSpacing(10)


        self.collapsed_handle = QFrame(self.right_panel)
        self.collapsed_handle.setStyleSheet(theme_qss("background: @surface; border-left: 1px solid @border; border-radius: 12px;"))
        ch_layout = QVBoxLayout(self.collapsed_handle)
        ch_layout.setContentsMargins(0, 10, 0, 0)
        ch_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        self.btn_expand = QPushButton("\u25c0")
        self.btn_expand.setFixedSize(24, 24)
        self.btn_expand.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_expand.setStyleSheet(theme_qss("background: transparent; border: none; font-size: 12px; color: @text;"))
        self.btn_expand.clicked.connect(self._expand_right_panel)
        ch_layout.addWidget(self.btn_expand)

        self.btn_pin_collapsed = QPushButton("\U0001f4ce")
        self.btn_pin_collapsed.setFixedSize(24, 24)
        self.btn_pin_collapsed.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pin_collapsed.setStyleSheet(theme_qss("background: transparent; border: none; font-size: 14px; color: @text_muted;"))
        self.btn_pin_collapsed.clicked.connect(self.pin_from_collapsed)
        ch_layout.addWidget(self.btn_pin_collapsed)

        right_layout.addWidget(self.collapsed_handle)
        self.collapsed_handle.hide()

        self.btn_pin = QPushButton("\U0001f4cc")
        self.btn_pin.setCheckable(True)
        self.btn_pin.setChecked(True) # Pinned by default
        self.btn_pin.setFixedSize(28, 28)
        self.btn_pin.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pin.setToolTip("Paneli Sabitle / Gizle (Ata\u00e7)")
        from PyQt6.QtGui import QFont
        self.btn_pin.setText("")
        self.btn_pin.setProperty("referenceGlyph", "pin")
        self.btn_pin.setFont(QFont(DesignTokens.FONT_NAME, 14))
        self.btn_pin.setStyleSheet(theme_qss("""
            QPushButton {
                background: transparent;
                border: none;
                font-size: 16px;
                color: @text_muted;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover {
                color: @accent;
            }
            QPushButton:checked {
                color: @accent;
            }
        """))
        self.btn_pin.clicked.connect(self.handle_pin_toggled)
        self.quick_actions_container = QFrame(); self.quick_actions_container.setStyleSheet(theme_qss("background: @finance_surface; border: 1px solid @finance_outline; border-radius: 6px;"))
        q_wrap = QVBoxLayout(self.quick_actions_container); q_wrap.setContentsMargins(8, 8, 8, 8); q_wrap.setSpacing(6)
        q_title = QLabel("H\u0131zl\u0131 \u0130\u015flemler"); q_title.setStyleSheet(theme_qss("font-size: 12px; font-weight: 800; color: @text_muted; border:none;"))
        q_wrap.addWidget(q_title); self.quick_actions_layout = QGridLayout(); self.quick_actions_layout.setSpacing(4); q_wrap.addLayout(self.quick_actions_layout)
        right_layout.addWidget(self.quick_actions_container)

        fiscal_controls = QFrame()
        fiscal_controls.setStyleSheet(
            theme_qss(
                "background: @finance_surface; border: 1px solid @finance_outline; border-radius: 6px;"
            )
        )
        f_wrap = QHBoxLayout(fiscal_controls)
        f_wrap.setContentsMargins(8, 6, 8, 6)
        self.btn_fiscal_controls = QPushButton("Mali Y\u0131l Kontrolleri")
        self.btn_fiscal_controls.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_fiscal_controls.clicked.connect(self.open_fiscal_controls)
        self.btn_fiscal_controls.setStyleSheet(
            theme_qss(
                "background: @finance_primary; color: @finance_primary_text; border-radius: 4px; padding: 6px 8px; font-weight: 700;"
            )
        )
        f_wrap.addWidget(self.btn_fiscal_controls, 1)
        f_wrap.addWidget(self.btn_pin)
        right_layout.addWidget(fiscal_controls)

        self.reference_side_cards = QVBoxLayout()
        self.reference_side_cards.setSpacing(10)
        right_layout.addLayout(self.reference_side_cards)
        self._build_reference_side_cards()

        self.cards_container = QFrame(); self.cards_container.setStyleSheet(theme_qss("background: transparent; border: none;"))
        ca_wrap = QVBoxLayout(self.cards_container); ca_wrap.setContentsMargins(0, 0, 0, 0); ca_wrap.setSpacing(10)
        ca_title = QLabel("Finans \u00d6zeti"); ca_title.setStyleSheet(theme_qss("font-size: 12px; font-weight: 800; color: @text_muted; border:none;"))
        ca_wrap.addWidget(ca_title); self.cards_layout = QGridLayout(); self.cards_layout.setSpacing(10); ca_wrap.addLayout(self.cards_layout)
        right_layout.addStretch(1)

        self.cards_container.hide()
        self._build_quick_actions()
        content_row = QHBoxLayout()
        content_row.setSpacing(8)
        ledger_column = QVBoxLayout()
        ledger_column.setSpacing(8)
        ledger_column.addWidget(self.table_container, 1)
        content_row.addLayout(ledger_column, 1)
        content_row.addWidget(self.right_panel, 0)
        layout.addLayout(content_row, 1)
        flow_card = QFrame()
        flow_card.setObjectName("financialReferenceFlow")
        flow_card.setStyleSheet(theme_qss("QFrame#financialReferenceFlow { background: @finance_surface; border: none; border-radius: 6px; }"))
        flow_layout = QHBoxLayout(flow_card)
        flow_layout.setContentsMargins(12, 8, 12, 8)
        flow_layout.addWidget(FinancialMetricGlyph("trend_up", "finance_action_collection"))
        flow_text = QVBoxLayout()
        flow_text.setSpacing(2)
        flow_title = QLabel("Haftal\u0131k Nakit Ak\u0131\u015f Dengesi")
        flow_title.setStyleSheet(theme_qss("color: @finance_text; font-size: 12px; font-weight: 800; border: none;"))
        flow_detail = QLabel("Tahsilat ak\u0131\u015f\u0131 ve cari bor\u00e7 tahsilatlar\u0131 son 14 g\u00fcn i\u00e7inde izleniyor.")
        flow_detail.setWordWrap(True)
        flow_detail.setStyleSheet(theme_qss("color: @finance_text_muted; font-size: 10px; border: none;"))
        flow_text.addWidget(flow_title)
        flow_text.addWidget(flow_detail)
        flow_layout.addLayout(flow_text, 1)
        flow_detail.setText("Son 14 g\u00fcn: y\u00fcklenmi\u015f hareketlerin net dengesi.")
        self.reference_flow_chart = FinancialFlowSparkline()
        self.reference_flow_chart.setFixedWidth(160)
        self.reference_flow_volume = QLabel("-")
        self.reference_flow_volume.setWordWrap(True)
        self.reference_flow_volume.setMaximumWidth(150)
        self.reference_flow_volume.setStyleSheet(theme_qss("font-size:11px;font-weight:700;color:@finance_secondary;border:none;background:transparent;"))
        flow_row = QHBoxLayout()
        flow_row.addWidget(self.reference_flow_chart, 1)
        flow_row.addWidget(self.reference_flow_volume)
        flow_layout.addLayout(flow_row)
        ledger_column.addWidget(flow_card)

        self.update_archive_button(); self.populate_fiscal_year_selector()
        QTimer.singleShot(100, self.refresh_data); self.apply_theme_styles()

    def _build_reference_side_cards(self):
        """Build the compact reference panels without changing finance actions."""
        self.reference_side_values = {}
        panels = [
            ("rates", "Kayitli Doviz Kurlari", "@finance_secondary"),
            ("vat", "KDV & Stopaj Durumu", "@finance_primary"),
            ("cash", "Kasa ve Banka Bakiyeleri", "@finance_secondary"),
        ]
        for key, title, accent in panels:
            frame = QFrame()
            frame.setStyleSheet(theme_qss(
                f"background: @finance_surface; border: 1px solid @finance_outline; "
                f"border-top: 3px solid {accent}; border-radius: 8px;"
            ))
            wrap = QVBoxLayout(frame)
            wrap.setContentsMargins(12, 10, 12, 10)
            heading = QLabel(title)
            heading.setStyleSheet(theme_qss("color: @finance_text; font-size: 12px; font-weight: 800; border: none;"))
            value = QLabel("Veri y\u00fckleniyor...")
            value.setWordWrap(True)
            self.reference_side_values[key] = value
            value.setStyleSheet(theme_qss("color: @finance_text_muted; font-size: 11px; line-height: 1.4; border: none;"))
            wrap.addWidget(heading)
            wrap.addWidget(value)
            self.reference_side_cards.addWidget(frame)

    def _update_reference_side_panels(self):
        from src.utils.currency_helper import CurrencyHelper
        from src.ui.pages.finance.bank_accounts_widget import _account_fields

        rates = []
        for currency in ("EUR", "USD"):
            try:
                row = self.db.conn.execute("SELECT selling_rate,effective_date FROM exchange_rates WHERE currency=? ORDER BY created_at DESC LIMIT 1", (currency,)).fetchone()
                value = f"{float(row[0]):.4f}" if row and row[0] is not None else "-"
                timestamp = str(row[1] or "-") if row else "-"
                rates.append(f"{currency} / TRY  {value}  ({timestamp})")
            except Exception:
                rates.append(f"{currency} / TRY  -")
        self.reference_side_values["rates"].setText("\n".join(rates))
        self.reference_side_values["vat"].setText("Islem bazli KDV / stopaj verisi yok.\nSabit bir oranla vergi hesaplanmadi.")
        try:
            columns = list(self.db._get_table_columns("bank_accounts"))
            where = " WHERE COALESCE(is_deleted,0)=0" if "is_deleted" in columns else ""
            rows = self.db.conn.execute("SELECT * FROM bank_accounts" + where).fetchall()
            cash, bank = 0.0, 0.0
            display_currency = CurrencyHelper.get_code(self.db)
            for row in rows:
                account, _, name, number, _ = _account_fields(row, columns)
                amount = float(row[columns.index("current_balance")] or 0)
                currency = str(row[columns.index("currency")] or "TRY")
                amount = CurrencyHelper.convert_amount(self.db, amount, currency, display_currency)
                identity = f"{account} {name} {number}".casefold()
                if "kasa" in identity or "cash" in identity:
                    cash += amount
                else:
                    bank += amount
            cash_text = CurrencyHelper.format_amount(cash, db=self.db, currency_code=display_currency)
            bank_text = CurrencyHelper.format_amount(bank, db=self.db, currency_code=display_currency)
            self.reference_side_values["cash"].setText(f"Fiziki Nakit: {cash_text}\nPOS / BANKA: {bank_text}")
        except Exception:
            self.reference_side_values["cash"].setText("Hesap bakiyesi verisi yok.")

    def _on_reference_search_changed(self, value):
        search = value.strip()
        if search == self._ledger_search:
            return
        self._ledger_search = search
        self.ledger_current_page = 0
        self._ledger_groups_initialized = False
        self._expanded_ledger_dates.clear()
        self._ledger_search_timer.start(250)

    def _set_reference_period(self, period):
        if period not in self.reference_period_buttons or period == self._ledger_period:
            return
        self._ledger_period = period
        self.ledger_current_page = 0
        self._ledger_groups_initialized = False
        self._expanded_ledger_dates.clear()
        self.refresh_data()

    def _build_toolbar_button(self, label, color, slot, parent=None, glyph=None, stacked=True):
        btn = FinancialReferenceActionButton(label, glyph, stacked=stacked) if glyph else QPushButton(label)
        if parent:
            btn.setParent(parent)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        foreground = {"@finance_secondary": "@finance_secondary_text", "@finance_primary": "@finance_primary_text", "@danger": "@danger_foreground", "@finance_action_income": "@finance_action_income_text", "@finance_action_expense": "@finance_action_expense_text", "@finance_action_collection": "@finance_action_collection_text"}.get(color, "@finance_text")
        btn.setStyleSheet(theme_qss(f"background:{color};color:{foreground};border:none;border-radius:4px;padding:3px 6px;font-size:10px;font-weight:700;"))
        if glyph and not stacked:
            btn.setFixedHeight(24)
            btn.setMinimumWidth(btn.fontMetrics().horizontalAdvance(label) + 34)
        btn.clicked.connect(slot); return btn

    def open_fiscal_controls(self):
        FiscalControlsDialog(self).exec()

    def _build_quick_actions(self):
        self.quick_action_buttons = []
        acts = [("Excel \u0130ndir", "@finance_surface_high", self.export_to_excel, "excel"), ("PDF Rapor", "@finance_surface_high", self.export_to_pdf, "pdf"), ("Fi\u015f Yazd\u0131r", "@finance_surface_high", self.print_ledger, "print"), ("Tahsilat Al", "@finance_success_bg", self.open_collection_dialog, "collection"), ("Gelir Ekle", "@finance_success_bg", self.open_income_dialog, "income"), ("Gider Ekle", "@finance_warning_bg", self.open_expense_dialog, "expense"), ("Virman / Transfer", "@finance_surface_high", self.open_transfer_dialog, "transfer")]
        for l, c, s, glyph in acts:
            b = self._build_toolbar_button(l, c, s, parent=self.quick_actions_container, glyph=glyph)
            b.setFixedHeight(48)
            foreground = "@finance_secondary" if glyph in ("collection", "income") else ("@finance_tertiary" if glyph == "expense" else "@finance_text")
            b.setStyleSheet(theme_qss(f"background:{c};color:{foreground};border:none;border-radius:4px;padding:2px;font-size:10px;font-weight:700;"))
            self.quick_action_buttons.append(b)
        tax_button = self._build_toolbar_button(
            "Vergi Hesab\u0131",
            "@finance_surface_high",
            self.open_tax_dialog,
            parent=self.quick_actions_container,
            glyph="tax",
        )
        tax_button.setToolTip("Vergi Dilimi Hesaplama")
        tax_button.setFixedHeight(48)
        tax_button.setStyleSheet(theme_qss("background:@finance_surface_high;color:@finance_text;border:none;border-radius:4px;padding:2px;font-size:11px;font-weight:700;"))
        self.quick_action_buttons.append(tax_button)
        self._relayout_quick_actions()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        try: self._relayout_summary_cards(); self._relayout_quick_actions()
        except: pass

    def eventFilter(self, obj, event):
        if obj == self.right_panel:
            if event.type() == QEvent.Type.Enter:
                if hasattr(self, "btn_pin") and not self.btn_pin.isChecked():
                    self._expand_right_panel()
            elif event.type() == QEvent.Type.Leave:
                if hasattr(self, "btn_pin") and not self.btn_pin.isChecked():
                    self._collapse_right_panel()
        return super().eventFilter(obj, event)

    def handle_pin_toggled(self):
        pinned = self.btn_pin.isChecked()
        self.btn_pin.setText("\U0001f4cc" if pinned else "\U0001f4ce")
        if not pinned:
            self._collapse_right_panel()

    def pin_from_collapsed(self):
        self.btn_pin.setChecked(True)
        self.btn_pin.setText("\U0001f4cc")
        self._expand_right_panel()

    def _collapse_right_panel(self):
        self._set_right_panel_content_visible(False)
        self.collapsed_handle.show()

        self.anim = QPropertyAnimation(self.right_panel, b"minimumWidth")
        self.anim.setDuration(200)
        self.anim.setStartValue(self.right_panel.width())
        self.anim.setEndValue(35)
        self.anim.setEasingCurve(QEasingCurve.Type.OutQuad)

        self.anim_max = QPropertyAnimation(self.right_panel, b"maximumWidth")
        self.anim_max.setDuration(200)
        self.anim_max.setStartValue(self.right_panel.width())
        self.anim_max.setEndValue(35)
        self.anim_max.setEasingCurve(QEasingCurve.Type.OutQuad)

        self.anim.start()
        self.anim_max.start()

    def _expand_right_panel(self):
        self.collapsed_handle.hide()

        self.anim = QPropertyAnimation(self.right_panel, b"minimumWidth")
        self.anim.setDuration(200)
        self.anim.setStartValue(self.right_panel.width())
        self.anim.setEndValue(262)
        self.anim.setEasingCurve(QEasingCurve.Type.OutQuad)

        self.anim_max = QPropertyAnimation(self.right_panel, b"maximumWidth")
        self.anim_max.setDuration(200)
        self.anim_max.setStartValue(self.right_panel.width())
        self.anim_max.setEndValue(262)
        self.anim_max.setEasingCurve(QEasingCurve.Type.OutQuad)


        self.anim.start()
        self.anim_max.start()

        QTimer.singleShot(200, lambda: self._set_right_panel_content_visible(True))

    def _set_right_panel_content_visible(self, visible: bool):
        if hasattr(self, "right_panel") and self.right_panel.layout():
            def update_layout(layout):
                for index in range(layout.count()):
                    item = layout.itemAt(index)
                    widget = item.widget()
                    if widget is not None and widget != self.collapsed_handle:
                        widget.setVisible(visible)
                    elif item.layout() is not None:
                        update_layout(item.layout())

            update_layout(self.right_panel.layout())

    def toggle_shortcuts_hover(self):
        pass

    def request_reload(self, delay_ms=50):
        self._refresh_timer.stop()
        self._refresh_timer.start(max(0, int(delay_ms)))

    def _contrast_on(self, bg): return "#ffffff" # Basic fallback
    def _hover_on(self, bg): return bg # Basic fallback
