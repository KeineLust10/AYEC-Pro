# -*- coding: utf-8 -*-

from collections import defaultdict
from datetime import datetime

from PyQt6.QtCore import QDate, Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QTextDocument, QAction
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog

from src.ui.pages.accounting_dialogs import (
    AddExpenseDialog,
    AddIncomeDialog,
    AddTransferDialog,
    TaxAnalysisDialog,
    TransactionDetailsDialog,
)
from src.ui.dialogs.customer_select_dialog import CustomerSelectDialog
from src.ui.dialogs.tahsilat_dialog import TahsilatDialog
from src.ui.widgets.empty_state import EmptyState
from src.utils.currency_helper import CurrencyHelper
from src.utils.context_menu_settings import is_context_menu_enabled
from src.utils.finance_manager import FinanceManager
from src.utils.theme_colors import qc, tc, theme_qss
from src.utils.date_formatter import format_date
from src.utils.message_helper import show_question
from src.utils.toast_notification import show_warning, show_info, show_success
from src.utils.logger import logger


class LedgerWorker(QThread):
    finished = pyqtSignal(list)

    def __init__(self, finance_manager, limit=1000):
        super().__init__()
        self.finance_manager = finance_manager
        self.limit = limit

    def run(self):
        try:
            data = self.finance_manager.get_unified_ledger(self.limit)
            self.finished.emit(data)
        except Exception as e:
            logger.error(f"LedgerWorker error: {e}")
            self.finished.emit([])


from src.ui.components.modern_dialog import ModernDialog
from src.ui.components.message_box import ModernMessage
from PyQt6.QtWidgets import QComboBox


class ArchiveSelectionDialog(ModernDialog):
    def __init__(self, parent, archives):
        super().__init__(
            parent,
            title="Geçmiş Yıl Arşivi Seçin",
            width=640,
            height=320,
            blur_background=True,
        )
        self.selected_archive = None
        self.archives = archives
        self.combo = QComboBox()
        for archive in self.archives:
            year = ""
            if archive.startswith("archive_") and archive.endswith(".db"):
                year = archive.replace("archive_", "").replace(".db", "")
            label = f"Mali Yil {year}" if year.isdigit() else archive
            self.combo.addItem(label, archive)
        self.combo.setStyleSheet(
            theme_qss("""
            QComboBox {
                padding: 10px;
                border: 1px solid @border;
                border-radius: 8px;
                background-color: @surface_alt;
                color: @text;
                font-size: 13px;
                font-weight: 600;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: @surface_alt;
                border: 1px solid @border;
                selection-background-color: @selection_bg;
                selection-color: @selection_text;
            }
        """)
        )
        msg = QLabel("İncelenecek Arşiv Veritabanı:")
        msg.setStyleSheet(
            theme_qss("color: @text_muted; font-size: 13px; font-weight: 600;")
        )
        self.content_layout.addWidget(msg)
        self.content_layout.addSpacing(10)
        self.content_layout.addWidget(self.combo)
        self.content_layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        btn_cancel = QPushButton("İptal")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet(
            theme_qss(
                "background: transparent; color: @text_muted; border-radius: 6px; padding: 8px 16px; font-weight: bold; border: 1px solid @border;"
            )
        )
        btn_cancel.clicked.connect(self.reject)

        btn_ok = QPushButton("İncele")
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.setStyleSheet(
            theme_qss(
                "background: @success; color: @selection_text; border-radius: 6px; padding: 8px 30px; font-weight: bold; border:none;"
            )
        )
        btn_ok.clicked.connect(self.accept_selection)

        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_ok)
        self.content_layout.addLayout(btn_layout)

    def accept_selection(self):
        self.selected_archive = self.combo.currentData() or self.combo.currentText()
        self.accept()


class FinanceCard(QFrame):
    clicked = pyqtSignal()

    def __init__(self, title, value, subtext="", color=None, icon="💰"):
        super().__init__()
        color = color or tc("accent")
        self.setMinimumSize(180, 112)
        self.setMaximumHeight(140)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(14)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(0, 0, 0, 40))
        self.setGraphicsEffect(shadow)

        self.setStyleSheet(
            theme_qss(
                f"""
                QFrame {{
                    background-color: @surface;
                    border: 1px solid @border;
                    border-top: 4px solid {color};
                    border-radius: 14px;
                }}
                """
            )
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)

        header = QHBoxLayout()
        lbl_title = QLabel(title)
        lbl_title.setWordWrap(True)
        lbl_title.setStyleSheet(
            theme_qss(
                "color: @text_muted; font-size: 12px; font-weight: 700; border:none;"
            )
        )
        lbl_icon = QLabel(icon)
        lbl_icon.setStyleSheet(
            theme_qss(
                f"font-size: 16px; background: {color}15; color: {color}; "
                "border:none; border-radius: 10px; padding: 6px;"
            )
        )
        header.addWidget(lbl_title)
        header.addStretch()
        header.addWidget(lbl_icon)
        layout.addLayout(header)

        self.lbl_value = QLabel(value)
        self.lbl_value.setWordWrap(True)
        self.lbl_value.setStyleSheet(
            theme_qss("color: @text; font-size: 18px; font-weight: 800; border:none;")
        )
        layout.addWidget(self.lbl_value)

        self.lbl_sub_value = QLabel("")
        self.lbl_sub_value.setWordWrap(True)
        self.lbl_sub_value.setVisible(False)
        self.lbl_sub_value.setStyleSheet(
            theme_qss(
                "color: @text_muted; font-size: 10px; font-weight: 600; border:none;"
            )
        )
        layout.addWidget(self.lbl_sub_value)

        self.lbl_subtext = QLabel(subtext)
        self.lbl_subtext.setWordWrap(True)
        self.lbl_subtext.setStyleSheet(
            theme_qss(
                f"color: {color}; font-size: 10px; font-weight: 700; border:none;"
            )
        )
        layout.addWidget(self.lbl_subtext)

    def set_sub_value(self, text):
        self.lbl_sub_value.setText(text)
        self.lbl_sub_value.setVisible(bool(text))

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


class AccountingPage(QWidget):
    def __init__(self, db, main_window):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.finance_manager = FinanceManager(db)
        self.ledger_data = []
        self.worker = None
        self._refresh_lock = False  # Prevent overlapping refreshes
        # Robustness: Initialize critical layout attributes early
        self.cards_layout = None
        self.cards_container = None
        self.quick_actions_layout = None
        self.quick_actions_container = None
        self.card_widgets = []
        self.quick_action_buttons = []
        self.setup_ui()

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        self.tab_main = QWidget()
        self.tabs.addTab(self.tab_main, "📊 Finansal Özet")
        root.addWidget(self.tabs)

        layout = QVBoxLayout(self.tab_main)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        header = QHBoxLayout()
        title = QLabel("Finansal Dashboard")
        title.setStyleSheet(
            theme_qss("font-size: 24px; font-weight: 800; color: @text;")
        )
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        self.btn_archive = QPushButton("📂 Arşiv (Geçmiş)")
        self.btn_archive.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_archive.clicked.connect(self.handle_archive_action)

        self.cmb_fiscal_year = QComboBox()
        self.cmb_fiscal_year.setMinimumWidth(180)
        self.cmb_fiscal_year.currentIndexChanged.connect(
            self.handle_fiscal_year_changed
        )
        self.cmb_fiscal_year.setStyleSheet(
            theme_qss(
                """
                QComboBox {
                    padding: 10px 12px;
                    border: 1px solid @border;
                    border-radius: 8px;
                    background: @surface_alt;
                    color: @text;
                    font-weight: 700;
                }
                QComboBox::drop-down { border: none; width: 24px; }
                """
            )
        )

        table_container = QFrame()
        table_container.setStyleSheet(
            theme_qss(
                "background: @surface; border-radius: 12px; border: 1px solid @border;"
            )
        )
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(0)

        lbl_table = QLabel("  Son Hareketler (Birleşik Defter)")
        lbl_table.setFixedHeight(40)
        lbl_table.setStyleSheet(
            theme_qss(
                "font-weight: 700; color: @text_muted; background: @surface_alt; "
                "border-bottom: 1px solid @border; padding-left: 10px;"
            )
        )
        table_layout.addWidget(lbl_table)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self._refresh_amount_headers()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setStyleSheet(
            theme_qss(
                """
                QTableWidget { border: none; font-size: 13px; selection-background-color: @border; selection-color: @selection_text; }
                QTableWidget::item { padding: 8px; border-bottom: 1px solid @surface_alt; }
                QTableWidget::item:selected { background-color: @border; color: @selection_text; }
                QHeaderView::section { background: @surface; padding: 10px; border-bottom: 2px solid @border; font-weight: 700; color: @text_muted; }
                """
            )
        )
        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        self.table.cellDoubleClicked.connect(self.on_table_double_click)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_table_context_menu)
        table_layout.addWidget(self.table)
        self.ledger_empty_state = EmptyState(
            "Henüz işlem yok",
            "Finansal harekete ait kayıt bulunamadı.",
            parent=self,
        )
        self.ledger_empty_state.hide()
        table_layout.addWidget(self.ledger_empty_state)

        self.footer_frame = QFrame()
        self.footer_frame.setFixedHeight(50)
        self.footer_frame.setStyleSheet(
            theme_qss(
                "background: @surface_alt; border-top: 1px solid @border; "
                "border-bottom-left-radius: 12px; border-bottom-right-radius: 12px;"
            )
        )
        self.footer_layout = QHBoxLayout(self.footer_frame)
        self.footer_layout.setContentsMargins(20, 0, 20, 0)
        table_layout.addWidget(self.footer_frame)

        right_panel = QFrame()
        right_panel.setMinimumWidth(390)
        right_panel.setMaximumWidth(720)
        right_panel.setStyleSheet(theme_qss("background: transparent; border: none;"))
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(14)

        fiscal_controls = QFrame()
        fiscal_controls.setStyleSheet(
            theme_qss(
                "background: @surface; border: 1px solid @border; border-radius: 12px;"
            )
        )
        fiscal_wrap = QVBoxLayout(fiscal_controls)
        fiscal_wrap.setContentsMargins(12, 12, 12, 12)
        fiscal_wrap.setSpacing(10)
        fiscal_title = QLabel("Mali Yil Kontrolleri")
        fiscal_title.setStyleSheet(
            theme_qss(
                "font-size: 12px; font-weight: 800; color: @text_muted; border:none;"
            )
        )
        fiscal_wrap.addWidget(fiscal_title)

        fiscal_grid = QGridLayout()
        fiscal_grid.setContentsMargins(0, 0, 0, 0)
        fiscal_grid.setHorizontalSpacing(10)
        fiscal_grid.setVerticalSpacing(10)
        fiscal_grid.addWidget(self.btn_archive, 0, 0)
        fiscal_grid.addWidget(self.cmb_fiscal_year, 0, 1)
        fiscal_buttons = [
            ("🔄 Yenile", tc("accent"), self.refresh_data),
            ("Yeni Mali Yila Gecis", tc("warning"), self.handle_fiscal_rollover),
            ("Acilis Fisleri", tc("warning"), lambda: self.apply_filter("OPENING")),
            ("Yilbasi Raporu", tc("accent"), self.show_fiscal_opening_report),
        ]
        for index, (label, color, slot) in enumerate(fiscal_buttons):
            row = (index // 2) + 1
            col = index % 2
            fiscal_grid.addWidget(
                self._build_toolbar_button(label, color, slot), row, col
            )
        fiscal_wrap.addLayout(fiscal_grid)
        right_layout.addWidget(fiscal_controls)

        self.quick_actions_container = QFrame()
        self.quick_actions_container.setStyleSheet(
            theme_qss(
                "background: @surface; border: 1px solid @border; border-radius: 12px;"
            )
        )
        quick_wrap = QVBoxLayout(self.quick_actions_container)
        quick_wrap.setContentsMargins(12, 12, 12, 12)
        quick_wrap.setSpacing(10)
        quick_title = QLabel("Hizli Islemler")
        quick_title.setStyleSheet(
            theme_qss(
                "font-size: 12px; font-weight: 800; color: @text_muted; border:none;"
            )
        )
        quick_wrap.addWidget(quick_title)
        self.quick_actions_layout = QGridLayout()
        self.quick_actions_layout.setContentsMargins(0, 0, 0, 0)
        self.quick_actions_layout.setHorizontalSpacing(10)
        self.quick_actions_layout.setVerticalSpacing(10)
        quick_wrap.addLayout(self.quick_actions_layout)
        right_layout.addWidget(self.quick_actions_container)

        self.cards_container = QFrame()
        self.cards_container.setStyleSheet(
            theme_qss("background: transparent; border: none;")
        )
        cards_wrap = QVBoxLayout(self.cards_container)
        cards_wrap.setContentsMargins(0, 0, 0, 0)
        cards_wrap.setSpacing(10)
        cards_title = QLabel("Finans Ozeti")
        cards_title.setStyleSheet(
            theme_qss(
                "font-size: 12px; font-weight: 800; color: @text_muted; border:none;"
            )
        )
        cards_wrap.addWidget(cards_title)
        self.cards_layout = QGridLayout()
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setHorizontalSpacing(10)
        self.cards_layout.setVerticalSpacing(10)
        cards_wrap.addLayout(self.cards_layout)
        right_layout.addWidget(self.cards_container)
        right_layout.addStretch(1)

        self._build_quick_actions()

        content_row = QHBoxLayout()
        content_row.setSpacing(16)
        content_row.addWidget(table_container, 1)
        content_row.addWidget(right_panel, 0)
        layout.addLayout(content_row, 1)

        self.update_archive_button()
        self.populate_fiscal_year_selector()
        QTimer.singleShot(100, self.refresh_data)

    def _build_toolbar_button(self, label, color, slot):
        btn = QPushButton(label)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            theme_qss(
                f"background: {color}; color: @selection_text; border-radius: 8px; "
                "padding: 10px 16px; font-weight: 700;"
            )
        )
        btn.clicked.connect(slot)
        return btn

    def _clear_layout(self, layout):
        if not layout:
            return
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if child_layout is not None:
                self._clear_layout(child_layout)
            if widget is not None:
                widget.setParent(None)

    def _build_quick_actions(self):
        self.quick_action_buttons = []
        actions = [
            ("📊 Excel", tc("accent"), self.export_to_excel),
            ("📄 PDF", tc("accent"), self.export_to_pdf),
            ("🖨️ Yazdır", tc("accent"), self.print_ledger),
            ("💰 Tahsilat Al", tc("success"), self.open_collection_dialog),
            ("➕ Gelir Ekle", tc("success"), self.open_income_dialog),
            ("➖ Gider Ekle", tc("danger"), self.open_expense_dialog),
            ("↔ Transfer", tc("accent"), self.open_transfer_dialog),
        ]
        for label, color, slot in actions:
            btn = self._build_toolbar_button(label, color, slot)
            btn.setMinimumHeight(40)
            self.quick_action_buttons.append(btn)
        self._relayout_quick_actions()

    def _relayout_quick_actions(self):
        self._clear_layout(self.quick_actions_layout)
        if not self.quick_action_buttons:
            return
        cols = 2
        for index, btn in enumerate(self.quick_action_buttons):
            row = index // cols
            col = index % cols
            self.quick_actions_layout.addWidget(btn, row, col)

    def _relayout_summary_cards(self):
        self._clear_layout(self.cards_layout)
        if not self.card_widgets:
            return

        width = 0
        try:
            width = int(self.cards_container.width() or 0)
        except Exception:
            width = 0
        cols = 3 if width >= 660 else 2
        for index, card in enumerate(self.card_widgets):
            row = index // cols
            col = index % cols
            self.cards_layout.addWidget(card, row, col)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        try:
            self._relayout_summary_cards()
            self._relayout_quick_actions()
        except Exception:
            pass

    def handle_fiscal_rollover(self):
        fiscal_service = getattr(self.main_window, "fiscal_service", None)
        if not fiscal_service:
            ModernMessage.show_error(
                self, "Mali yil servisi baslatilamadi.", "Servis Hatasi"
            )
            return

        snapshot = fiscal_service.get_status_snapshot()
        reply = show_question(
            self,
            "Yeni Mali Yila Gecis",
            "Manuel mali yil devir islemi baslatilsin mi?\n\n"
            f"Planli devir tarihi: {snapshot.get('rollover_date', '-')}\n"
            f"Planli reset tarihi: {snapshot.get('reset_date', '-')}\n"
            f"Son devir: {snapshot.get('last_rollover', '-')}\n"
            f"Son durum: {snapshot.get('last_status', '-')}\n\n"
            "Bu islem mevcut veritabanini arsivler ve sonraki dongu tarihlerini gunceller. "
            "Canli veri silme yapmaz.",
        )
        if int(reply) != 16384:
            return

        result = fiscal_service.trigger_manual_rollover()
        if not result.get("ok"):
            archive_name = result.get("archive_name") or "-"
            detail = result.get("error", "Bilinmeyen hata")
            if archive_name != "-":
                detail = f"{detail}\n\nOlusan arsiv: {archive_name}"
            ModernMessage.show_error(
                self,
                f"Manuel mali yil devri basarisiz: {detail}",
                "Mali Yil Hatasi",
            )
            self.populate_fiscal_year_selector()
            self.refresh_data()
            return

        snapshot = result.get("snapshot", {})
        archive_name = result.get("archive_name") or "olusturulamadi"
        title = "Mali Yil Devri"
        body = (
            "Manuel mali yil devir islemi tamamlandi.\n\n"
            f"Arsiv: {archive_name}\n"
            f"Bir sonraki planli devir: {snapshot.get('rollover_date', '-')}\n"
            f"Bir sonraki planli reset: {snapshot.get('reset_date', '-')}"
        )
        ModernMessage.show_info(
            self,
            body,
            title,
        )
        self.populate_fiscal_year_selector()
        self.refresh_data()

    def show_fiscal_opening_report(self):
        fiscal_service = getattr(self.main_window, "fiscal_service", None)
        report = fiscal_service.get_last_opening_report() if fiscal_service else {}
        if not report:
            ModernMessage.show_info(
                self,
                "Kayitli bir yilbasi acilis raporu bulunamadi.\n"
                "Önce manuel veya otomatik mali yil devri calismis olmali.",
                "Yilbasi Raporu",
            )
            return
        message = (
            f"Acilis Tarihi: {report.get('opening_date', '-')}\n"
            f"Arsiv: {report.get('archive_name', '-')}\n"
            f"Olusan Acilis Fisi: {report.get('opening_count', 0)}\n\n"
            f"Banka Devri: {report.get('bank_count', 0)} hesap | "
            f"{CurrencyHelper.format_try_for_display(report.get('bank_total_try', 0), db=self.db, include_try_reference=False)}\n"
            f"Cari Alacak Devri: {CurrencyHelper.format_try_for_display(report.get('receivable_total_try', 0), db=self.db, include_try_reference=False)}\n"
            f"Musteri Avans Devri: {CurrencyHelper.format_try_for_display(report.get('advance_total_try', 0), db=self.db, include_try_reference=False)}\n\n"
            f"Sonraki Planli Devir: {report.get('next_rollover_date', '-')}"
        )
        ModernMessage.show_info(self, message, "Yilbasi Baslangic Raporu")

    def populate_fiscal_year_selector(self):
        try:
            fiscal_start = str(
                self.db.get_internal_setting("fiscal_year_start", "") or ""
            ).strip()
            current_year = int((fiscal_start or str(datetime.now().year))[:4])
        except Exception:
            current_year = datetime.now().year
        current_archive = ""
        if getattr(self.main_window, "is_archive_mode", False):
            db_path = str(
                getattr(getattr(self.main_window, "db", None), "_db_path", "") or ""
            )
            if "archive_" in db_path.lower():
                current_archive = db_path.split("\\")[-1]

        self.cmb_fiscal_year.blockSignals(True)
        self.cmb_fiscal_year.clear()
        self.cmb_fiscal_year.addItem(
            f"Canli ({current_year})", ("live", current_year, "")
        )
        archives = []
        if hasattr(self.main_window, "get_available_archives"):
            try:
                archives = self.main_window.get_available_archives() or []
            except Exception:
                archives = []
        selected_index = 0
        for archive in archives:
            year_text = archive.replace("archive_", "").replace(".db", "")
            label = f"Mali Yil {year_text}" if year_text.isdigit() else archive
            self.cmb_fiscal_year.addItem(label, ("archive", year_text, archive))
            if archive == current_archive:
                selected_index = self.cmb_fiscal_year.count() - 1
        self.cmb_fiscal_year.setCurrentIndex(selected_index)
        self.cmb_fiscal_year.blockSignals(False)

    def handle_fiscal_year_changed(self, _index):
        payload = self.cmb_fiscal_year.currentData()
        if not payload:
            return
        mode, _year, archive_name = payload
        is_archive = getattr(self.main_window, "is_archive_mode", False)
        if mode == "live":
            if is_archive and hasattr(self.main_window, "return_to_active_database"):
                if self.main_window.return_to_active_database():
                    self.update_archive_button()
                    self.refresh_data()
            return
        if archive_name and hasattr(self.main_window, "load_archived_database"):
            current_db_path = str(
                getattr(getattr(self.main_window, "db", None), "_db_path", "") or ""
            )
            if archive_name.lower() in current_db_path.lower():
                return
            if self.main_window.load_archived_database(archive_name):
                self.update_archive_button()
                self.refresh_data()

    def update_archive_button(self):
        is_archive = getattr(self.main_window, "is_archive_mode", False)
        if is_archive:
            self.btn_archive.setText("🔙 Canlı Sisteme Dön")
            self.btn_archive.setStyleSheet(
                theme_qss(
                    "background: @danger; color: @selection_text; border-radius: 8px; padding: 10px 20px; font-weight: 700; border: 1px solid @danger;"
                )
            )
        else:
            self.btn_archive.setText("📂 Arşiv (Geçmiş)")
            self.btn_archive.setStyleSheet(
                theme_qss(
                    "background: @surface_alt; color: @text; border-radius: 8px; padding: 10px 20px; font-weight: 700; border: 1px solid @border;"
                )
            )
        self.populate_fiscal_year_selector()

    def handle_archive_action(self):
        is_archive = getattr(self.main_window, "is_archive_mode", False)
        if is_archive:
            if hasattr(self.main_window, "return_to_active_database"):
                if self.main_window.return_to_active_database():
                    self.update_archive_button()
                    self.refresh_data()
        else:
            if hasattr(self.main_window, "get_available_archives"):
                archives = self.main_window.get_available_archives()
                if not archives:
                    ModernMessage.show_warning(
                        self,
                        "Kayıtlı hiçbir geçmiş yıl arşivi bulunamadı.",
                        "Geçmiş Arşiv Bulunamadı",
                    )
                    return
                dlg = ArchiveSelectionDialog(self, archives)
                if dlg.exec():
                    if dlg.selected_archive and self.main_window.load_archived_database(
                        dlg.selected_archive
                    ):
                        self.update_archive_button()
                        self.refresh_data()

    def refresh_data(self):
        if self._refresh_lock:
            return
        self._refresh_lock = True

        try:
            if not hasattr(self, "cards_layout") or self.cards_layout is None:
                self._refresh_lock = False
                return

            display_code = CurrencyHelper.get_code(self.db)
            self._refresh_amount_headers()
            try:
                data = self.finance_manager.get_financial_summary("fiscal")
            except Exception:
                data = {}

            summary = {
                "gross_revenue": float(data.get("gross_revenue", 0) or 0),
                "net_revenue": float(data.get("net_revenue", 0) or 0),
                "expenses": float(data.get("expenses", 0) or 0),
                "pocket_net": float(data.get("pocket_net", 0) or 0),
                "hot_cash": float(data.get("hot_cash", 0) or 0),
            }

            # Clear existing cards
            self._clear_layout(self.cards_layout)
            self.card_widgets = []

            cards = [
                (
                    f"Toplam Ciro ({display_code})",
                    CurrencyHelper.format_try_for_display(
                        summary["gross_revenue"],
                        db=self.db,
                        include_try_reference=False,
                    ),
                    "Brüt Satış (KDV Dahil)",
                    tc("success"),
                    "📈",
                    "Net Ciro: "
                    f"{CurrencyHelper.format_try_for_display(summary['net_revenue'], db=self.db, include_try_reference=False)}",
                    "INCOME",
                ),
                (
                    f"Maliyet ve Gider ({display_code})",
                    CurrencyHelper.format_try_for_display(
                        summary["expenses"],
                        db=self.db,
                        include_try_reference=False,
                    ),
                    "Alış + Operasyonel",
                    tc("danger"),
                    "📉",
                    "",
                    "EXPENSE",
                ),
                (
                    f"Net Kâr ({display_code})",
                    CurrencyHelper.format_try_for_display(
                        summary["pocket_net"],
                        db=self.db,
                        include_try_reference=False,
                    ),
                    "Cepte Kalan (Vergi Sonrası)",
                    tc("warning"),
                    "💰",
                    "",
                    "ALL",
                ),
                (
                    f"Sıcak Nakit ({display_code})",
                    CurrencyHelper.format_try_for_display(
                        summary["hot_cash"],
                        db=self.db,
                        include_try_reference=False,
                    ),
                    "Kasa ve Banka Mevcudu",
                    tc("accent"),
                    "🏧",
                    "",
                    "ALL",
                ),
            ]

            for title, value, subtext, color, icon, sub_value, filter_key in cards:
                card = FinanceCard(title, value, subtext, color, icon)
                if sub_value:
                    card.set_sub_value(sub_value)
                card.clicked.connect(
                    lambda _=False, fk=filter_key: self.apply_filter(fk)
                )
                self.card_widgets.append(card)
            self._relayout_summary_cards()

            if self.worker and self.worker.isRunning():
                try:
                    self.worker.disconnect()
                    self.worker.terminate()
                    self.worker.wait()
                except Exception:
                    pass

            self.worker = LedgerWorker(self.finance_manager)
            self.worker.finished.connect(self.on_data_loaded)
            self.worker.start()
        except Exception as e:
            self._refresh_lock = False
            logger.error(f"Error in refresh_data: {e}")

    def on_data_loaded(self, data):
        self._refresh_lock = False
        try:
            self.ledger_data = data or []
            # Enrich rows with display-formatted fields
            for i, row in enumerate(self.ledger_data):
                date_str = row.get("date") or ""
                # Centralized date format: DD.MM.YYYY
                row["display_date"] = format_date(date_str, self.db, include_time=False)

                # Extract time portions
                if "T" in str(date_str):
                    parts = str(date_str).split("T")
                    row["time"] = parts[1][:5] if len(parts) > 1 else "--"
                elif " " in str(date_str):
                    parts = str(date_str).split(" ")
                    row["time"] = parts[1][:5] if len(parts) > 1 else "--"
                else:
                    row["time"] = "--"
                # Format original amount with currency symbol
                currency = (row.get("currency") or "TRY").upper()
                amount = row.get("amount") or 0
                rate = row.get("rate") or 1.0
                display_code = CurrencyHelper.get_code(self.db)
                if currency != display_code and float(amount or 0) != 0:
                    row["amount_original_str"] = CurrencyHelper.format_amount(
                        amount, db=self.db, currency_code=currency
                    )
                    row["exchange_rate_str"] = (
                        f"{float(rate):,.4f}" if float(rate) != 1.0 else "--"
                    )
                else:
                    row["amount_original_str"] = "--"
                    row["exchange_rate_str"] = "--"
                # Status text
                row["status_text"] = row.get("status") or ""
                # Balance value
                row["balance_value"] = row.get("balance")

            self.apply_filter("ALL")
        except Exception as e:
            logger.error(f"Error in on_data_loaded: {e}")

    def apply_filter(self, filter_key):
        with open("DEBUG_REFRESH.txt", "a", encoding="utf-8") as df:
            df.write(f"apply_filter starting (filter={filter_key})\n")
            try:
                grouped = defaultdict(list)
                self.table.setRowCount(0)

                for row in self.ledger_data:
                    type_label = str(row.get("type_label", ""))
                    if filter_key == "INCOME" and type_label not in {
                        "Satış",
                        "Gelir",
                        "Tahsilat",
                    }:
                        continue
                    if filter_key == "EXPENSE" and type_label not in {"Gider"}:
                        continue
                    if filter_key == "OPENING" and type_label not in {"Açılış"}:
                        continue
                    display_date = row.get("display_date") or row.get("date") or "-"
                    grouped[display_date].append(row)

                sorted_dates = sorted(grouped.keys(), reverse=True)
                for display_date in sorted_dates:
                    rows = grouped[display_date]
                    header_row = self.table.rowCount()
                    self.table.insertRow(header_row)

                    try:
                        date_total = sum(
                            float(t.get("amount_try") or 0)
                            for t in rows
                            if str(t.get("type_label", ""))
                            in {"Satış", "Gelir", "Tahsilat", "Açılış"}
                        )
                    except Exception as e:
                        df.write(f"date_total calc error: {e}\n")
                        date_total = 0

                    header_item = QTableWidgetItem(
                        f"📅 {display_date} ({len(rows)} işlem)"
                    )
                    header_item.setFlags(
                        Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
                    )
                    header_item.setForeground(qc("text"))
                    self.table.setItem(header_row, 0, header_item)

                    total_item = QTableWidgetItem(
                        CurrencyHelper.format_try_for_display(
                            date_total,
                            db=self.db,
                            include_try_reference=False,
                        )
                    )
                    total_item.setFlags(
                        Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
                    )
                    total_item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                    self.table.setItem(header_row, 5, total_item)

                    for row in rows:
                        data_row = self.table.rowCount()
                        self.table.insertRow(data_row)
                        type_label = str(row.get("type_label", "-"))
                        is_opening = type_label == "Açılış"
                        is_income = type_label in {
                            "Satış",
                            "Gelir",
                            "Tahsilat",
                            "Açılış",
                        }
                        icon = (
                            "🟣"
                            if is_opening
                            else (
                                "🔵"
                                if type_label == "Satış"
                                else ("🟢" if is_income else "🔴")
                            )
                        )

                        try:
                            amt_try_val = float(row.get("amount_try") or 0)
                            bal_val = row.get("balance_value")
                            bal_val_float = (
                                float(bal_val or 0) if bal_val is not None else None
                            )

                            values = [
                                row.get("time") or "--",
                                f"{icon} {type_label}",
                                row.get("description") or "-",
                                row.get("amount_original_str") or "--",
                                row.get("exchange_rate_str") or "--",
                                CurrencyHelper.format_try_for_display(
                                    amt_try_val,
                                    db=self.db,
                                    include_try_reference=False,
                                ),
                                row.get("status_text") or "-",
                                "--"
                                if bal_val is None
                                else CurrencyHelper.format_try_for_display(
                                    bal_val_float,
                                    db=self.db,
                                    include_try_reference=False,
                                ),
                            ]

                            for col, value in enumerate(values):
                                item = QTableWidgetItem(str(value))
                                item.setFlags(
                                    Qt.ItemFlag.ItemIsEnabled
                                    | Qt.ItemFlag.ItemIsSelectable
                                )
                                if col in (3, 4, 5, 7):
                                    item.setTextAlignment(
                                        Qt.AlignmentFlag.AlignRight
                                        | Qt.AlignmentFlag.AlignVCenter
                                    )
                                if col == 1:
                                    item.setForeground(
                                        qc("success") if is_income else qc("danger")
                                    )
                                elif col == 6:
                                    status = str(value).lower()
                                    if "bekliyor" in status:
                                        item.setForeground(qc("warning"))
                                    elif "tamam" in status:
                                        item.setForeground(qc("success"))
                                elif col in (5, 7):
                                    # Safe starts-with check for negative amounts
                                    if (
                                        str(value).startswith("-")
                                        or (col == 5 and amt_try_val < 0)
                                        or (
                                            col == 7
                                            and bal_val_float is not None
                                            and bal_val_float < 0
                                        )
                                    ):
                                        item.setForeground(qc("danger"))
                                    else:
                                        item.setForeground(qc("text"))
                                self.table.setItem(data_row, col, item)
                                self.table.item(data_row, col).setData(
                                    Qt.ItemDataRole.UserRole, row
                                )
                        except Exception as row_err:
                            df.write(f"Error drawing row: {row_err}\n")

                df.write("Step 6: Updating footer\n")
                has_rows = self.table.rowCount() > 0
                self.table.setVisible(has_rows)
                self.ledger_empty_state.setVisible(not has_rows)
                self.update_footer()
                df.write("apply_filter successful\n")
                self.table.resizeRowsToContents()
            except Exception as e:
                import traceback

                df.write(f"apply_filter CRASH: {e}\n{traceback.format_exc()}\n")

    def update_footer(self):
        try:
            while self.footer_layout.count():
                item = self.footer_layout.takeAt(0)
                if item and item.widget():
                    item.widget().deleteLater()

            try:
                data = self.finance_manager.get_financial_summary("fiscal")
            except Exception:
                data = {}

            cash = float(data.get("hot_cash") or 0)
            pending_try = float(data.get("pending") or 0)

            cash_lbl = QLabel(
                "<b>Kasa:</b> "
                + CurrencyHelper.format_try_for_display(
                    cash, db=self.db, include_try_reference=False
                )
            )
            rec_text = (
                "<b>Bekleyen Alacaklar:</b> "
                + CurrencyHelper.format_try_for_display(
                    pending_try,
                    db=self.db,
                    include_try_reference=False,
                )
            )
            rec_lbl = QLabel(rec_text)

            for lbl in (cash_lbl, rec_lbl):
                lbl.setStyleSheet(theme_qss("color: @text; font-weight: 700;"))
                self.footer_layout.addWidget(lbl)
            self.footer_layout.addStretch()
        except Exception as e:
            logger.error(f"Error in update_footer: {e}")

    def on_table_double_click(self, row, _column):
        item = self.table.item(row, 0)
        if not item:
            return
        entry = item.data(Qt.ItemDataRole.UserRole)
        if not entry:
            return
        TransactionDetailsDialog(self.db, entry, self).exec()

    def _refresh_amount_headers(self):
        display_code = CurrencyHelper.get_code(self.db)
        self.table.setHorizontalHeaderLabels(
            [
                "TARİH",
                "İŞLEM TÜRÜ",
                "AÇIKLAMA",
                "TUTAR (DÖVİZ)",
                "KUR",
                f"TUTAR ({display_code})",
                "DURUM",
                f"BAKİYE ({display_code})",
            ]
        )

    def show_table_context_menu(self, pos):
        if not is_context_menu_enabled(self.db, page_id=101):
            return
        idx = self.table.indexAt(pos)
        if not idx.isValid():
            return
        self.table.selectRow(idx.row())
        menu = QMenu(self)
        action_detail = QAction("🔍 Hareket Detayı", self)
        action_excel = QAction("📊 Excel'e Aktar", self)
        action_pdf = QAction("📄 PDF Olarak Kaydet", self)
        action_print = QAction("🖨️ Yazdır", self)
        action_detail.triggered.connect(
            lambda: self.on_table_double_click(idx.row(), idx.column())
        )
        action_excel.triggered.connect(self.export_to_excel)
        action_pdf.triggered.connect(self.export_to_pdf)
        action_print.triggered.connect(self.print_ledger)
        menu.addAction(action_detail)
        menu.addSeparator()
        menu.addAction(action_excel)
        menu.addAction(action_pdf)
        menu.addAction(action_print)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _collect_ledger_rows(self):
        headers = [
            self.table.horizontalHeaderItem(i).text()
            for i in range(self.table.columnCount())
        ]
        rows = []
        for row in range(self.table.rowCount()):
            payload = {}
            for col, header in enumerate(headers):
                item = self.table.item(row, col)
                payload[header] = item.text() if item else ""
            rows.append(payload)
        return rows

    def _build_ledger_html(self):
        rows = self._collect_ledger_rows()
        header_html = "".join(
            f"<th style='padding:8px;border:1px solid #d9d9d9;background:#f3f4f6;'>{header}</th>"
            for header in (
                rows[0].keys() if rows else ["Tarih", "İşlem Türü", "Açıklama", "Tutar"]
            )
        )
        body_html = []
        for row in rows:
            body_html.append(
                "<tr>"
                + "".join(
                    f"<td style='padding:6px;border:1px solid #d9d9d9;'>{value}</td>"
                    for value in row.values()
                )
                + "</tr>"
            )
        return f"""
        <html><head><meta charset='UTF-8'></head><body>
        <h2>AYEC Pro - Cari Hareketler / Finansal Defter</h2>
        <p>Tarih: {datetime.now().strftime("%d.%m.%Y %H:%M")}</p>
        <table cellspacing='0' cellpadding='0' style='width:100%;border-collapse:collapse;font-size:9pt;'>
        <thead><tr>{header_html}</tr></thead>
        <tbody>{"".join(body_html)}</tbody>
        </table></body></html>
        """

    def export_to_excel(self):
        rows = self._collect_ledger_rows()
        if not rows:
            show_warning(self, "Disa aktarilacak hareket bulunamadi.")
            return
        try:
            import pandas as pd

            path, _ = QFileDialog.getSaveFileName(
                self,
                "Cari Hareketleri Kaydet",
                "cari_hareketler.xlsx",
                "Excel Dosyası (*.xlsx)",
            )
            if not path:
                return
            df = pd.DataFrame(rows)
            df.to_excel(path, index=False)
            show_success(self, "Cari hareketler disa aktarildi.")
        except Exception as e:
            show_warning(self, f"Excel aktarim hatasi: {e}")

    def export_to_pdf(self):
        rows = self._collect_ledger_rows()
        if not rows:
            show_warning(self, "PDF icin hareket bulunamadi.")
            return
        try:
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Cari Hareketleri PDF Kaydet",
                "cari_hareketler.pdf",
                "PDF Dosyasi (*.pdf)",
            )
            if not path:
                return
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(path)
            doc = QTextDocument()
            doc.setHtml(self._build_ledger_html())
            doc.print(printer)
            show_success(self, "Cari hareket PDF'i olusturuldu.")
        except Exception as e:
            show_warning(self, f"PDF olusturma hatasi: {e}")

    def print_ledger(self):
        rows = self._collect_ledger_rows()
        if not rows:
            show_warning(self, "Yazdirilacak hareket bulunamadi.")
            return
        try:
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            dialog = QPrintDialog(printer, self)
            if dialog.exec() != QPrintDialog.DialogCode.Accepted:
                return
            doc = QTextDocument()
            doc.setHtml(self._build_ledger_html())
            doc.print(printer)
            show_info(self, "Cari hareketler yazdirmaya gonderildi.")
        except Exception as e:
            show_warning(self, f"Yazdirma hatasi: {e}")

    def open_tax_dialog(self):
        TaxAnalysisDialog(self.finance_manager, self).exec()

    def open_collection_dialog(self):
        picker = CustomerSelectDialog(self.db, self)
        if not picker.exec() or not picker.selected_customer:
            return
        selected = picker.selected_customer
        customer = {
            "id": selected[0],
            "name": selected[1],
            "phone": selected[2] if len(selected) > 2 else "",
        }
        if not customer.get("id"):
            show_warning(self, "Geçerli bir müşteri seçilemedi.")
            return
        dlg = TahsilatDialog(self, self.db, customer)
        if not dlg.exec():
            return

        data = dlg.get_data() or {}
        try:
            currency = str(
                data.get("currency") or CurrencyHelper.get_code(self.db) or "TRY"
            ).upper()
            exchange_rate = float(data.get("exchange_rate", 1.0) or 1.0)
            amount = float(data.get("amount", 0) or 0)
            if amount <= 0:
                show_warning(self, "Tahsilat tutarı geçersiz.")
                return

            accounting_date = None
            created_at = None
            if data.get("date"):
                parsed = QDate.fromString(str(data.get("date")), "dd.MM.yyyy")
                if parsed.isValid():
                    accounting_date = parsed.toString("yyyy-MM-dd")
                    created_at = (
                        f"{accounting_date} {datetime.now().strftime('%H:%M:%S')}"
                    )

            reference_tracking = data.get("reference_tracking_no") or None
            reference_desc = (data.get("reference_desc") or "").strip()
            full_desc = (
                data.get("notes") or ""
            ).strip() or "Cari borç kapatma tahsilatı"
            if reference_tracking:
                full_desc = f"Ref: {reference_tracking} | {full_desc}"
            if reference_desc and reference_desc not in full_desc:
                full_desc = f"{full_desc} | {reference_desc}"

            try:
                self.db.create_payment_debt_links_table()
            except Exception:
                pass

            saved = self.db.add_currency_transaction(
                customer_id=customer["id"],
                amount=amount,
                currency=currency,
                transaction_type="CREDIT",
                exchange_rate=exchange_rate,
                description=full_desc,
                tracking_no=reference_tracking,
                created_at=created_at,
            )
            if not saved:
                show_warning(self, "Tahsilat kaydedilirken bir hata oluştu.")
                return

            payment_txn_id = None
            try:
                payment_txn_id = self.db.get_last_currency_transaction_id()
            except Exception:
                payment_txn_id = None

            if payment_txn_id:
                try:
                    self.db.apply_payment_to_debts(
                        customer_id=customer["id"],
                        payment_amount=amount,
                        currency=currency,
                        payment_transaction_id=payment_txn_id,
                        selected_debt_ids=data.get("selected_debt_ids") or None,
                    )
                except Exception:
                    pass

            tl_amount = amount * (exchange_rate if currency != "TRY" else 1.0)
            try:
                self.db.add_transaction(
                    t_type="Gelir",
                    category="Tahsilat",
                    amount=tl_amount,
                    description=full_desc,
                    customer_name=customer.get("name"),
                    customer_id=customer["id"],
                    date=accounting_date,
                    payment_method=data.get("method"),
                    bank_account_id=data.get("bank_account_id"),
                    tracking_no=reference_tracking,
                    ref_no=reference_tracking,
                    currency=currency,
                    original_amount=amount,
                )
            except Exception:
                pass

            self.refresh_data()
        except Exception as exc:
            show_warning(self, f"Tahsilat kaydı sırasında hata oluştu: {exc}")

    def open_income_dialog(self):
        if AddIncomeDialog(self.db, self).exec():
            self.refresh_data()

    def open_expense_dialog(self):
        if AddExpenseDialog(self.db, self).exec():
            self.refresh_data()

    def open_transfer_dialog(self):
        if AddTransferDialog(self.db, self).exec():
            self.refresh_data()
