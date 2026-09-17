# -*- coding: utf-8 -*-

from PyQt6.QtCore import Qt, QTimer, QEvent, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import (
    QAbstractItemView, QComboBox, QFrame, QGridLayout, QHBoxLayout,
    QHeaderView, QLabel, QPushButton, QTableWidget, QTabWidget, QVBoxLayout, QWidget
)
from src.ui.components.modern_dialog import ModernDialog
from src.ui.widgets.empty_state import EmptyState
from src.utils.finance_manager import FinanceManager
from src.utils.theme_colors import theme_qss

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
        self._current_filter_key = "ALL"
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

        layout = QVBoxLayout(self.tab_main); layout.setContentsMargins(20, 12, 20, 20); layout.setSpacing(12)

        self.header_frame = QFrame()
        self.header_frame.setStyleSheet(theme_qss(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #0f172a, stop:0.55 #1e293b, stop:1 #334155); border-radius: 18px; border: 1px solid @border;"
        ))
        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(22, 18, 22, 18)
        lbl_title = QLabel("Finansal Dashboard")
        lbl_title.setStyleSheet(theme_qss("font-size: 20px; font-weight: 800; color: @text; border: none; background: transparent;"))
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        layout.addWidget(self.header_frame)

        self.btn_archive = QPushButton("Ar\u015fiv (Ge\u00e7mi\u015f)")
        self.btn_archive.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_archive.clicked.connect(self.handle_archive_action)

        self.cmb_fiscal_year = QComboBox()
        self.cmb_fiscal_year.setMinimumWidth(180)
        self.cmb_fiscal_year.currentIndexChanged.connect(self.handle_fiscal_year_changed)
        self.cmb_fiscal_year.setStyleSheet(theme_qss("QComboBox { padding: 10px 12px; border: 1px solid @border; border-radius: 8px; background: @surface_alt; color: @text; font-weight: 700; } QComboBox::drop-down { border: none; width: 24px; }"))

        self.table_container = QFrame()
        self.table_container.setStyleSheet(theme_qss("background: @surface; border-radius: 12px; border: 1px solid @border;"))
        table_layout = QVBoxLayout(self.table_container); table_layout.setContentsMargins(0, 0, 0, 0); table_layout.setSpacing(0)

        lbl_table = QLabel("  Son Hareketler (Birleşik Defter)")
        lbl_table.setFixedHeight(40)
        lbl_table.setStyleSheet(theme_qss("font-weight: 700; color: @text_muted; background: @surface_alt; border-bottom: 1px solid @border; padding-left: 10px;"))
        table_layout.addWidget(lbl_table)

        self.table = QTableWidget(); self.table.setColumnCount(8)
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
        ledger_pager_layout.setContentsMargins(12, 6, 12, 6)
        ledger_pager_layout.addStretch()
        self.ledger_prev_button = QPushButton("< \u00d6nceki")
        self.ledger_page_label = QLabel("Sayfa 1")
        self.ledger_next_button = QPushButton("Sonraki >")
        self.ledger_prev_button.clicked.connect(self._ledger_prev_page)
        self.ledger_next_button.clicked.connect(self._ledger_next_page)
        ledger_pager_layout.addWidget(self.ledger_prev_button)
        ledger_pager_layout.addWidget(self.ledger_page_label)
        ledger_pager_layout.addWidget(self.ledger_next_button)
        ledger_pager_layout.addStretch()
        table_layout.addWidget(self.ledger_pager_frame)
        self._update_ledger_pagination()

        self.footer_frame = QFrame(); self.footer_frame.setFixedHeight(50)
        self.footer_frame.setStyleSheet(theme_qss("background: @surface_alt; border-top: 1px solid @border; border-bottom-left-radius: 12px; border-bottom-right-radius: 12px;"))
        self.footer_layout = QHBoxLayout(self.footer_frame); self.footer_layout.setContentsMargins(20, 0, 20, 0)
        table_layout.addWidget(self.footer_frame)

        self.right_panel = QFrame()
        self.right_panel.setMinimumWidth(280)
        self.right_panel.setMaximumWidth(320)
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
        self.btn_pin.setFont(QFont("Segoe UI Emoji", 14))
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
        self.quick_actions_container = QFrame(); self.quick_actions_container.setStyleSheet(theme_qss("background: @surface; border: 1px solid @border; border-radius: 12px;"))
        q_wrap = QVBoxLayout(self.quick_actions_container); q_wrap.setContentsMargins(12, 12, 12, 12); q_wrap.setSpacing(10)
        q_title = QLabel("H\u0131zl\u0131 \u0130\u015flemler"); q_title.setStyleSheet(theme_qss("font-size: 12px; font-weight: 800; color: @text_muted; border:none;"))
        q_wrap.addWidget(q_title); self.quick_actions_layout = QGridLayout(); self.quick_actions_layout.setSpacing(10); q_wrap.addLayout(self.quick_actions_layout)
        right_layout.addWidget(self.quick_actions_container)

        fiscal_controls = QFrame()
        fiscal_controls.setStyleSheet(
            theme_qss(
                "background: @surface; border: 1px solid @border; border-radius: 12px;"
            )
        )
        f_wrap = QHBoxLayout(fiscal_controls)
        f_wrap.setContentsMargins(12, 10, 12, 10)
        self.btn_fiscal_controls = QPushButton("Mali Y\u0131l Kontrolleri")
        self.btn_fiscal_controls.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_fiscal_controls.clicked.connect(self.open_fiscal_controls)
        self.btn_fiscal_controls.setStyleSheet(
            theme_qss(
                "background: @accent; color: @selection_text; border-radius: 8px; padding: 11px 14px; font-weight: 700;"
            )
        )
        f_wrap.addWidget(self.btn_fiscal_controls, 1)
        f_wrap.addWidget(self.btn_pin)
        right_layout.addWidget(fiscal_controls)

        self.cards_container = QFrame(); self.cards_container.setStyleSheet(theme_qss("background: transparent; border: none;"))
        ca_wrap = QVBoxLayout(self.cards_container); ca_wrap.setContentsMargins(0, 0, 0, 0); ca_wrap.setSpacing(10)
        ca_title = QLabel("Finans \u00d6zeti"); ca_title.setStyleSheet(theme_qss("font-size: 12px; font-weight: 800; color: @text_muted; border:none;"))
        ca_wrap.addWidget(ca_title); self.cards_layout = QGridLayout(); self.cards_layout.setSpacing(10); ca_wrap.addLayout(self.cards_layout)
        right_layout.addWidget(self.cards_container); right_layout.addStretch(1)

        self._build_quick_actions()
        content_row = QHBoxLayout(); content_row.setSpacing(16); content_row.addWidget(self.table_container, 1); content_row.addWidget(self.right_panel, 0); layout.addLayout(content_row, 1)

        self.update_archive_button(); self.populate_fiscal_year_selector()
        QTimer.singleShot(100, self.refresh_data); self.apply_theme_styles()

    def _build_toolbar_button(self, label, color, slot, parent=None):
        btn = QPushButton(label)
        if parent:
            btn.setParent(parent)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(theme_qss(f"background: {color}; color: @selection_text; border-radius: 8px; padding: 10px 16px; font-weight: 700;"))
        btn.clicked.connect(slot); return btn

    def open_fiscal_controls(self):
        FiscalControlsDialog(self).exec()

    def _build_quick_actions(self):
        self.quick_action_buttons = []
        acts = [("Excel", "#0284c7", self.export_to_excel), ("PDF", "#0284c7", self.export_to_pdf), ("Yazd\u0131r", "#0284c7", self.print_ledger), ("Tahsilat Al", "#10b981", self.open_collection_dialog), ("Gelir Ekle", "#10b981", self.open_income_dialog), ("Gider Ekle", "#ef4444", self.open_expense_dialog), ("Transfer", "#0284c7", self.open_transfer_dialog)]
        for l, c, s in acts:
            b = self._build_toolbar_button(l, c, s, parent=self.quick_actions_container); b.setMinimumHeight(40); self.quick_action_buttons.append(b)
        tax_button = self._build_toolbar_button(
            "Vergi Dilimi Hesaplama",
            "#7c3aed",
            self.open_tax_dialog,
            parent=self.quick_actions_container,
        )
        tax_button.setMinimumHeight(40)
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
        self.anim.setEndValue(310)
        self.anim.setEasingCurve(QEasingCurve.Type.OutQuad)

        self.anim_max = QPropertyAnimation(self.right_panel, b"maximumWidth")
        self.anim_max.setDuration(200)
        self.anim_max.setStartValue(self.right_panel.width())
        self.anim_max.setEndValue(310)
        self.anim_max.setEasingCurve(QEasingCurve.Type.OutQuad)


        self.anim.start()
        self.anim_max.start()

        QTimer.singleShot(200, lambda: self._set_right_panel_content_visible(True))

    def _set_right_panel_content_visible(self, visible: bool):
        if hasattr(self, "right_panel") and self.right_panel.layout():
            layout = self.right_panel.layout()
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item and item.widget():
                    w = item.widget()
                    if w != self.collapsed_handle:
                        w.setVisible(visible)

    def toggle_shortcuts_hover(self):
        pass

    def request_reload(self, delay_ms=50):
        self._refresh_timer.stop()
        self._refresh_timer.start(max(0, int(delay_ms)))

    def _contrast_on(self, bg): return "#ffffff" # Basic fallback
    def _hover_on(self, bg): return bg # Basic fallback
