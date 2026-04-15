# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QLineEdit,
    QFrame,
    QMenu,
    QGraphicsDropShadowEffect,
    QApplication,
    QFileDialog,
    QMessageBox,
    QDoubleSpinBox,
    QGridLayout,
    QTabWidget,
)
from PyQt6.QtGui import QAction
from src.utils.theme_colors import theme_qss, qc, tc
from src.utils.toast_notification import (
    show_success,
    show_error,
    show_warning,
    show_info,
)
from src.utils.design_system import DesignTokens
from PyQt6.QtCore import Qt, QDate, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QIcon
from datetime import datetime
from src.ui.pages.customers.logic.export_manager import ExportManager
import csv
import webbrowser
import os

from src.ui.dialogs.customer_history_dialog import CustomerHistoryDialog
from src.ui.dialogs.add_customer_dialog import AddCustomerDialog
from src.ui.dialogs.customer_notes_dialog import CustomerNotesDialog
from src.ui.dialogs.service_invoice_dialog import ServiceInvoiceDialog
from src.ui.dialogs.customer_360_dialog import Customer360Dialog
from src.ui.dialogs.unified_documents_center_dialog import UnifiedDocumentsCenterDialog
from src.ui.dialogs.tahsilat_dialog import TahsilatDialog
from src.ui.pages.appointments_page import AddAppointmentDialog
from src.ui.pages.customers.logic.customer_manager import CustomerManager
from src.ui.widgets.modern_inputs import ModernComboBox
from src.ui.widgets.modern_dialog import ModernDialog
from src.ui.widgets.empty_state import EmptyState
from src.utils.logger import logger

from src.ui.pages.customers_page_parts import (
    CustomerWorker,
    PartnersPage,
    PartnerDialog,
)
from src.utils.date_formatter import format_date
from src.utils.currency_helper import CurrencyHelper
from src.utils.context_menu_settings import is_context_menu_enabled


class CustomersPage(QWidget):
    @staticmethod
    def _looks_like_partner_row(data):
        try:
            keys = data.keys() if hasattr(data, "keys") else []
            if "is_partner" in keys and int(data["is_partner"] or 0) == 1:
                return True
            row_type = (
                str(data["type"] or "").strip().casefold() if "type" in keys else ""
            )
            return row_type in {"bayi", "tedarikçi", "tedarikci"}
        except Exception:
            return False

    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.current_filter_type = None

        # Pagination State
        self.current_page = 0
        self.limit = 50
        self.total_count = 0
        self.search_query = None
        self.worker = None
        self._reload_pending = False
        self._pending_customers = []
        self._render_index = 0
        self._render_batch_size = 25
        self._multi_select = False

        # Arama optimizasyonu (Debounce)
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.execute_search)

        try:
            self.setup_ui()
            self._prepare_initial_view()
            # PartnersPage ile aynı yaklaşım: __init__ içinde veriyi yükle
            logger.debug(
                "CustomersPage init complete, scheduling refresh_data in 300ms"
            )
            QTimer.singleShot(300, self.refresh_data)
        except Exception as e:
            import traceback

            logger.error(f"CustomersPage Init Error: {e}\n{traceback.format_exc()}")
            QTimer.singleShot(
                500,
                lambda: self.notify(
                    f"Müşteri Listesi yüklenirken hata oluştu: {e}", "error"
                ),
            )

    def _prepare_initial_view(self):
        """Yükleniyor durumunu göster. Worker çalışıyorsa tabloyu sıfırlama."""
        self.lbl_total.setText("⏳ Yükleniyor...")
        self.btn_prev.setEnabled(False)
        self.btn_next.setEnabled(False)

    def notify(self, message, level="info"):
        if self.main_window and hasattr(self.main_window, "show_notification"):
            self.main_window.show_notification(message, level)
        else:
            if level == "error":
                show_error(self, message)
            elif level == "success":
                show_success(self, message)
            elif level == "warning":
                show_warning(self, message)
            else:
                show_info(self, message)

    def filter_by_type(self, type_name):
        self.current_filter_type = type_name
        title_map = {
            None: "M\u00fc\u015fteri Y\u00f6netimi",
            "DEBTORS": "Net Bor\u00e7lular",
            "OPEN_RECEIVABLES": "Tahsilat Bekleyenler",
        }
        subtitle_map = {
            None: "M\u00fc\u015fterileri, cari durumlar\u0131n\u0131 ve tahsilat aksiyonlar\u0131n\u0131 tek ekranda y\u00f6netin.",
            "DEBTORS": "Bor\u00e7 bakiyesi ta\u015f\u0131yan kay\u0131tlar\u0131 odak g\u00f6r\u00fcn\u00fcm\u00fcnde inceleyin.",
            "OPEN_RECEIVABLES": "Tahsilat bekleyen i\u015flemleri h\u0131zl\u0131ca filtreleyip aksiyon al\u0131n.",
        }
        badge_map = {
            None: "M\u00dc\u015eTER\u0130 HUB",
            "DEBTORS": "BOR\u00c7 ODA\u011eI",
            "OPEN_RECEIVABLES": "TAHS\u0130LAT",
        }
        self.header_title.setText(
            title_map.get(type_name, "M\u00fc\u015fteri Y\u00f6netimi")
        )
        if hasattr(self, "header_subtitle"):
            self.header_subtitle.setText(
                subtitle_map.get(type_name, subtitle_map[None])
            )
        if hasattr(self, "header_badge"):
            self.header_badge.setText(badge_map.get(type_name, badge_map[None]))
        self.current_page = 0
        self.request_reload()

    def request_reload(self, delay_ms=50):
        """Tekrarlı çağrılarda veri yüklemeyi kuyruklayarak UI donmasını azaltır."""
        QTimer.singleShot(delay_ms, self.refresh_data)

    def setup_ui(self):
        """Arayüz hiyerarşisini kurar"""
        self.setStyleSheet(theme_qss("background: @window;"))
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            theme_qss("""
            QTabWidget::pane { background: @window; border: none; }
            QTabBar::tab {
                background: @surface_alt;
                color: @text;
                padding: 9px 16px;
                border: 1px solid @border;
                border-bottom: none;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                margin-right: 4px;
                font-weight: 700;
            }
            QTabBar::tab:selected { background: @accent; color: @selection_text; }
        """)
        )
        self.tab_main = QWidget()
        self.tab_main.setStyleSheet(theme_qss("background: @window;"))
        self.tabs.addTab(self.tab_main, "👥 Müşteri Listesi")

        self.layout = QVBoxLayout(self.tab_main)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(12)

        # 1. Başlık Bölümü
        self._setup_header()
        # 2. Hızlı Erişim Kartları (Filtreleme)
        self._setup_banners()
        # 3. Araç Çubuğu (Dışa Aktarma & Arama)
        self._setup_toolbar()
        # 4. Veri Tablosu
        self._setup_table()
        # 5. Alt Bilgi (Footer)
        self._setup_footer()

    def _setup_header(self):
        hero = QFrame()
        hero.setStyleSheet(
            theme_qss("""
            QFrame {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 @surface,
                    stop:1 @surface_alt
                );
                border: 1px solid @border;
                border-radius: 18px;
            }
        """)
        )
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(22, 18, 22, 18)
        hero_layout.setSpacing(18)

        icon_badge = QLabel("👥")
        icon_badge.setFixedSize(54, 54)
        icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_badge.setStyleSheet(
            theme_qss("""
            QLabel {
                background: @accent;
                color: @selection_text;
                border-radius: 27px;
                font-size: 24px;
                font-weight: 700;
            }
        """)
        )
        hero_layout.addWidget(icon_badge, alignment=Qt.AlignmentFlag.AlignTop)

        title_box = QVBoxLayout()
        title_box.setSpacing(6)
        self.header_title = QLabel("Müşteri Yönetimi")
        self.header_title.setObjectName("DashboardWelcomeTitle")
        self.header_title.setStyleSheet(
            theme_qss("""
            color: @text;
            font-size: 28px;
            font-weight: 800;
            border: none;
            background: transparent;
        """)
        )
        self.header_subtitle = QLabel(
            "Müşterileri, cari durumlarını ve tahsilat aksiyonlarını tek ekranda yönetin."
        )
        self.header_subtitle.setWordWrap(True)
        self.header_subtitle.setStyleSheet(
            theme_qss("""
            color: @text_muted;
            font-size: 13px;
            border: none;
            background: transparent;
        """)
        )
        title_box.addWidget(self.header_title)
        title_box.addWidget(self.header_subtitle)
        hero_layout.addLayout(title_box, 1)

        self.header_badge = QLabel("MÜŞTERİ HUB")
        self.header_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.header_badge.setFixedHeight(34)
        self.header_badge.setMinimumWidth(140)
        self.header_badge.setStyleSheet(
            theme_qss("""
            QLabel {
                background: @surface_alt;
                color: @text;
                border: 1px solid @border;
                border-radius: 17px;
                font-size: 12px;
                font-weight: 700;
                padding: 0 14px;
            }
        """)
        )
        hero_layout.addWidget(self.header_badge, alignment=Qt.AlignmentFlag.AlignTop)

        self.layout.addWidget(hero)

    def _setup_banners(self):
        banner_card = QFrame()
        banner_card.setStyleSheet(
            theme_qss(
                "background: @surface; border: 1px solid @border; border-radius: 14px;"
            )
        )
        banner_layout = QHBoxLayout(banner_card)
        banner_layout.setContentsMargins(14, 14, 14, 14)
        banner_layout.setSpacing(15)

        # Not: İlk butonun arka planı beyaz olursa metin görünmez hale geliyordu.
        configs = [
            (
                "T\u00dcM M\u00dc\u015eTER\u0130LER",
                tc("accent"),
                lambda: self.filter_by_type(None),
                1,
            ),
            (
                "NET BOR\u00c7LULAR",
                tc("danger"),
                lambda: self.filter_by_type("DEBTORS"),
                1,
            ),
            (
                "TAHS\u0130LAT BEKLEYENLER",
                tc("warning"),
                lambda: self.filter_by_type("OPEN_RECEIVABLES"),
                1,
            ),
            (
                "+ YEN\u0130 M\u00dc\u015eTER\u0130 EKLE",
                tc("success"),
                self.add_customer,
                1,
            ),
        ]

        for text_value, color, cb, stretch in configs:
            btn = self._create_banner_btn(text_value, color)
            btn.clicked.connect(cb)
            banner_layout.addWidget(btn, stretch)

        self.layout.addWidget(banner_card)

    def _create_banner_btn(self, text, color):
        btn = QPushButton(text)
        btn.setFixedHeight(50)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        btn.setStyleSheet(
            theme_qss(f"""
            QPushButton {{ background-color: {color}; color: @selection_text; border-radius: 25px; border: none; }}
            QPushButton:hover {{ background-color: @surface; color: {color}; border: 2px solid {color}; }}
        """)
        )
        return btn

    def _setup_toolbar(self):
        toolbar_card = QFrame()
        toolbar_card.setStyleSheet(
            theme_qss(
                "background: @surface; border: 1px solid @border; border-radius: 12px;"
            )
        )
        toolbar = QHBoxLayout(toolbar_card)
        toolbar.setContentsMargins(14, 12, 14, 12)
        toolbar.setSpacing(10)
        tone_map = {
            "KOPYALA": "warning",
            "EXCEL": "success",
            "PDF": "secondary",
            "YAZDIR": "outline",
        }

        tools = [
            ("KOPYALA", "📄", tc("warning"), self.copy_list),
            ("EXCEL", "📊", tc("success"), self.export_excel),
            ("PDF", "📑", tc("text"), self.export_pdf),
            ("YAZDIR", "🖨️", tc("text_muted"), self.print_list),
        ]

        for text, icon, color, cb in tools:
            btn = QPushButton(f"{icon} {text}")
            btn.setFixedHeight(35)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                theme_qss(
                    DesignTokens.get_button_qss(
                        tone_map.get(text, "secondary"), size="sm"
                    )
                )
            )
            btn.clicked.connect(cb)
            toolbar.addWidget(btn)

        btn_docs = QPushButton("🗂 BELGE MERKEZI")
        btn_docs.setFixedHeight(35)
        btn_docs.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_docs.setStyleSheet(
            theme_qss(DesignTokens.get_button_qss("primary", size="sm"))
        )
        btn_docs.clicked.connect(self.open_documents_center)
        toolbar.addWidget(btn_docs)

        self.btn_multi = QPushButton("🔲 COKLU SEC")
        self.btn_multi.setCheckable(True)
        self.btn_multi.setFixedHeight(35)
        self.btn_multi.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_multi.setStyleSheet(
            theme_qss(DesignTokens.get_button_qss("outline", size="sm"))
        )
        self.btn_multi.clicked.connect(self.toggle_multiselect)
        toolbar.addWidget(self.btn_multi)

        toolbar.addStretch()
        lbl_search = QLabel("<b>Arama:</b>")
        lbl_search.setStyleSheet(
            theme_qss("color: @text_muted; font-weight: 700; padding-right: 6px;")
        )
        toolbar.addWidget(lbl_search)
        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("İsim, telefon veya e-posta...")
        self.inp_search.setFixedWidth(250)
        self.inp_search.setFixedHeight(35)
        self.inp_search.setStyleSheet(
            theme_qss(
                "border: 1px solid @border; border-radius: 8px; padding-left: 10px; background: @surface; color: @text;"
            )
        )
        self.inp_search.textChanged.connect(lambda: self.search_timer.start(500))
        toolbar.addWidget(self.inp_search)

        self.layout.addWidget(toolbar_card)

    def _setup_table(self):
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["MÜ.NO", "MÜŞTERİ", "FİRMA", "TELEFON", "E-POSTA", "BAKİYE", "İŞLEMLER"]
        )

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 76)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        self.table.setColumnWidth(1, 280)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 180)

        # Telefon ve E-posta biraz daha geniş
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 154)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 210)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 190)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(6, 190)
        self.table.verticalHeader().setVisible(False)
        self.table.setCornerButtonEnabled(False)

        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setMouseTracking(True)
        self.table.cellEntered.connect(self._on_table_cell_entered)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.cellDoubleClicked.connect(self.on_table_double_click)
        self.table.setAlternatingRowColors(False)
        self.table.setStyleSheet(
            theme_qss("""
            QTableWidget { border-radius: 12px; border: 1px solid @border; background: @surface; }
            QHeaderView::section { background-color: @surface_alt; color: @text; padding: 12px 10px; font-weight: bold; border: none; }
            QTableWidget::item { padding: 10px 12px; color: @text; border-bottom: 1px solid @surface_alt; background: @surface; }
            QTableWidget::item:selected { background-color: @selection_bg; color: @selection_text; font-weight: bold; }
            QTableWidget::item:focus { outline: none; }
        """)
        )
        self.layout.addWidget(self.table)
        self.empty_state = EmptyState(
            "Henüz müşteri yok",
            "Bu görünümde gösterilecek müşteri kaydı bulunamadı.",
            parent=self,
        )
        self.empty_state.setMinimumHeight(280)
        self.empty_state.hide()
        self.layout.addWidget(self.empty_state)

    def open_documents_center(self):
        UnifiedDocumentsCenterDialog(self.db, None, self).exec()

    def _on_table_cell_entered(self, row, _column):
        if row >= 0:
            self.table.selectRow(row)

    def _setup_footer(self):
        self.footer = QFrame()
        self.footer.setStyleSheet(
            theme_qss(
                "background: @surface_alt; border: 1px solid @border; border-radius: 10px;"
            )
        )
        f_layout = QHBoxLayout(self.footer)
        f_layout.setContentsMargins(12, 10, 12, 10)
        self.lbl_total = QLabel("📊 Toplam Kayıt: 0")
        self.lbl_total.setStyleSheet(theme_qss("color: @text;"))
        self.lbl_time = QLabel(
            f"🕒 Son Güncelleme: {format_date(datetime.now(), self.db, include_time=True)}"
        )
        self.lbl_time.setStyleSheet(theme_qss("color: @text_muted;"))
        f_layout.addWidget(self.lbl_total)
        f_layout.addStretch()
        f_layout.addWidget(self.lbl_time)
        f_layout.addStretch()

        # Pagination Controls in Footer
        self.btn_prev = QPushButton("\u25c0")
        self.btn_prev.setFixedSize(40, 30)
        self.btn_prev.clicked.connect(self.prev_page)
        self.btn_prev.setStyleSheet(
            theme_qss(
                "background: @surface; color: @text; border: 1px solid @border; border-radius: 8px;"
            )
        )

        self.lbl_page = QLabel("1 / 1")
        self.lbl_page.setStyleSheet(
            theme_qss("font-weight: bold; color: @text; margin: 0 10px;")
        )

        self.btn_next = QPushButton("\u25b6")
        self.btn_next.setFixedSize(40, 30)
        self.btn_next.clicked.connect(self.next_page)
        self.btn_next.setStyleSheet(
            theme_qss(
                "background: @surface; color: @text; border: 1px solid @border; border-radius: 8px;"
            )
        )

        f_layout.addWidget(self.btn_prev)
        f_layout.addWidget(self.lbl_page)
        f_layout.addWidget(self.btn_next)

        self.layout.addWidget(self.footer)

        # Tab 2: Nasıl Kullanılır? (Usage Guide)
        if self.db.get_internal_setting("feature_usage_guides_active", "1") == "1":
            self.tab_guide = QWidget()
            self.setup_usage_guide_tab()
            self.tabs.addTab(self.tab_guide, "❓ Nasıl Kullanılır?")

        self.main_layout.addWidget(self.tabs)
        # self.load_data() -> __init__ içine taşındı (Lazy Load)

    def refresh_data(self):
        """Müşteri verisini asenkron worker ile yükle"""
        logger.debug("CustomersPage.refresh_data called")
        try:
            self.table.setRowCount(0)
            self.lbl_total.setText("⏳ Yükleniyor...")
            self.btn_prev.setEnabled(False)
            self.btn_next.setEnabled(False)

            if self.worker is not None and self.worker.isRunning():
                self.worker.wait(100)
                self.worker.deleteLater()

            self.worker = CustomerWorker(
                self.db,
                self.limit,
                self.current_page * self.limit,
                self.search_query,
                self.current_filter_type,
            )
            self.worker.data_loaded.connect(self.on_data_loaded)
            self.worker.load_error.connect(
                lambda e: self.lbl_total.setText(f"Hata: {e}")
            )
            self.worker.start()

        except Exception as e:
            import traceback

            logger.error(f"Customer refresh_data error: {e}", exc_info=True)
            self.lbl_total.setText(f"Hata: {e}")
            show_error(self, f"Müşteri verisi yüklenemedi: {e}")

    def _try_run_pending_reload(self):
        if self._reload_pending:
            self._reload_pending = False
            QTimer.singleShot(100, self.refresh_data)

    def on_data_loaded(self, customers, total):
        logger.debug(
            "CustomersPage.on_data_loaded total=%s rows=%s",
            total,
            len(customers) if customers else 0,
        )
        customers_list = [
            row
            for row in list(customers or [])
            if not self._looks_like_partner_row(row)
        ]
        self.total_count = (
            len(customers_list)
            if self.current_filter_type in (None, "DEBTORS", "OPEN_RECEIVABLES")
            else int(total or 0)
        )
        self.table.setSortingEnabled(False)
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(0)
        success_count = 0
        for i, customer in enumerate(customers_list):
            try:
                self._add_row(i, customer)
                success_count += 1
            except Exception as e:
                import traceback

                logger.error(
                    f"CustomersPage _add_row failed at index {i}: {e}\n{traceback.format_exc()}"
                )
        self.table.setSortingEnabled(True)
        self.table.setUpdatesEnabled(True)
        self.table.viewport().update()
        logger.debug(
            "CustomersPage rendered %s/%s rows, table.rowCount=%s",
            success_count,
            len(customers_list),
            self.table.rowCount(),
        )
        self.lbl_total.setText(f"Toplam Kayıt: {self.total_count}")
        self.lbl_time.setText(
            f"Son Güncelleme: {format_date(datetime.now(), self.db, include_time=True)}"
        )
        has_rows = self.table.rowCount() > 0
        self.table.setVisible(has_rows)
        self.empty_state.setVisible(not has_rows)
        self._update_pagination_ui()
        self._try_run_pending_reload()

    def _render_rows_batch(self):
        # Legacy method kept for compatibility - rendering is now done directly in on_data_loaded
        pass

    def _update_pagination_ui(self):
        total_pages = (self.total_count + self.limit - 1) // self.limit
        if total_pages == 0:
            total_pages = 1

        self.lbl_page.setText(f"{self.current_page + 1} / {total_pages}")
        self.btn_prev.setEnabled(self.current_page > 0)
        self.btn_next.setEnabled(self.current_page < total_pages - 1)

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.request_reload()

    def next_page(self):
        total_pages = (self.total_count + self.limit - 1) // self.limit
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self.request_reload()

    def load_data(self, customers=None):
        """Legacy alias needed for some dialog callbacks"""
        # If customers arg is passed (e.g. from search), we ignore it and use refresh_data
        # unless strict legacy behavior is needed. But for search we optimized it.
        # Just call refresh_data()
        self.request_reload()

    def _add_row(self, row_idx, data):
        try:
            self.table.insertRow(row_idx)

            # Müşteri No (Vurgulu)
            # sqlite3.Row supports both index and name access
            customer_id = data["id"]
            item_id = QTableWidgetItem(str(customer_id))
            item_id.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_id.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            self.table.setItem(row_idx, 0, item_id)

            # İsim, Firma, Tel, Email
            name_display = str(data["name"])
            # Check row keys for 'type'
            keys = data.keys() if hasattr(data, "keys") else []
            cust_type = str(data["type"] or "").strip() if "type" in keys else ""

            if cust_type in ("Kurumsal", "Bayi", "Tedarikçi"):
                if cust_type == "Kurumsal":
                    badge_bg, badge_fg, badge_text = (
                        tc("selection_bg"),
                        tc("accent_pressed"),
                        "Kurumsal",
                    )
                elif cust_type == "Bayi":
                    badge_bg, badge_fg, badge_text = (
                        tc("surface_alt"),
                        tc("success"),
                        "Bayi",
                    )
                else:
                    badge_bg, badge_fg, badge_text = (
                        tc("surface_alt"),
                        tc("warning"),
                        "Tedarikçi",
                    )
                name_display = f"{name_display}  [{badge_text}]"
            name_item = QTableWidgetItem(name_display)
            name_item.setTextAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
            if cust_type in ("Kurumsal", "Bayi", "Tedarikçi"):
                name_item.setForeground(qc("selection_text"))
            self.table.setItem(row_idx, 1, name_item)

            # Kolon adı ile erişim - İndeks kayması riskini ortadan kaldırır
            company = (
                data["company_name"]
                if "company_name" in keys and data["company_name"]
                else "—"
            )
            comp_item = QTableWidgetItem(str(company))
            comp_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 2, comp_item)

            phone_item = QTableWidgetItem(str(data["phone"]) if data["phone"] else "—")
            phone_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            phone_item.setFont(QFont("Consolas", 9))
            self.table.setItem(row_idx, 3, phone_item)

            mail_item = QTableWidgetItem(str(data["email"]) if data["email"] else "—")
            mail_item.setTextAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
            mail_item.setFont(QFont("Segoe UI", 9))
            self.table.setItem(row_idx, 4, mail_item)

            # Bakiye Renklendirme (Çoklu Para Birimi)
            try:
                # get_customer_all_balances returns dict: {'TRY': 100, 'USD': 50}
                balances = {
                    "TRY": float(data["balance_try"]) if "balance_try" in keys else 0.0,
                    "USD": float(data["balance_usd"]) if "balance_usd" in keys else 0.0,
                    "EUR": float(data["balance_eur"]) if "balance_eur" in keys else 0.0,
                }
            except Exception:
                balances = {"TRY": 0.0}

            bal_item = self._create_balance_item_multi(balances)
            self.table.setItem(row_idx, 5, bal_item)

            # İşlem Yap Butonu
            self.table.setCellWidget(
                row_idx, 6, self._create_action_widget(row_idx, data)
            )

            # Safety checks for items
            it = self.table.item(row_idx, 0)
            if it:
                it.setData(Qt.ItemDataRole.UserRole, data)

            visible_currency_count = getattr(bal_item, "_visible_currency_count", 1)
            self.table.setRowHeight(
                row_idx,
                76
                if visible_currency_count <= 1
                else 92
                if visible_currency_count == 2
                else 108,
            )
        except Exception as e:
            logger.error(f"ADD_ROW ERROR at index {row_idx}: {e}", exc_info=True)

    def _create_balance_item_multi(self, balances):
        """Varsayilan para birimini her zaman, digerlerini sadece bakiye varsa goster."""
        default_currency = CurrencyHelper.get_code(self.db)
        lines = []
        has_debt = False
        has_credit = False
        visible_codes = []

        for currency_code in ("TRY", "USD", "EUR"):
            try:
                amount = float(balances.get(currency_code, 0.0) or 0.0)
            except Exception:
                amount = 0.0

            should_show = currency_code == default_currency or abs(amount) > 0.0001
            if not should_show:
                continue

            visible_codes.append(currency_code)

            if amount < 0:
                status = " (Borc)"
                has_debt = True
            elif amount > 0:
                status = " (Alacak)"
                has_credit = True
            else:
                status = ""

            formatted_amount = CurrencyHelper.format_amount(
                abs(amount),
                db=self.db,
                currency_code=currency_code,
            )
            lines.append(f"{currency_code}: {formatted_amount}{status}")

        if not lines:
            lines.append(
                f"{default_currency}: "
                + CurrencyHelper.format_amount(
                    0, db=self.db, currency_code=default_currency
                )
            )
            visible_codes.append(default_currency)

        if has_debt:
            color = tc("danger")
        elif has_credit:
            color = tc("success")
        else:
            color = tc("text_muted")

        text = "\n".join(lines)
        item = QTableWidgetItem(text)
        item.setForeground(QColor(color))
        item.setTextAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        item._visible_currency_count = len(visible_codes)
        return item

    def _create_balance_item(self, balance):
        # Legacy support just in case
        return self._create_balance_item_multi({"TRY": balance})

    def _create_action_widget(self, row, data):
        btn = QPushButton("İşlem Yap ▼")
        btn.setMinimumWidth(160)
        btn.setFixedHeight(34)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            theme_qss("""
            QPushButton { background: @accent; color: @selection_text; border-radius: 15px; font-weight: bold; font-size: 11px; border: 1px solid @accent; }
            QPushButton:hover { background: @accent_hover; color: @selection_text; border-color: @accent_hover; }
        """)
        )
        btn.clicked.connect(lambda checked, r=row: self.show_row_menu(r))

        container = QWidget()
        container.setStyleSheet(theme_qss("background: transparent; border: none;"))
        lay = QHBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(btn)
        return container

    def show_row_menu(self, row):
        # Ensure row is valid
        if row < 0 or row >= self.table.rowCount():
            return

        customer = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        # Use common menu function
        self.open_customer_menu(
            customer, self.table.cellWidget(row, 6).findChild(QPushButton)
        )

    def show_context_menu(self, position):
        if not is_context_menu_enabled(self.db, page_id=21):
            return
        item = self.table.itemAt(position)
        if not item:
            return

        row = item.row()
        if (
            self.table.selectionMode()
            == QAbstractItemView.SelectionMode.SingleSelection
        ):
            self.table.selectRow(row)
        customer = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)

        menu = QMenu(self)
        self.populate_customer_menu(menu, customer)
        menu.exec(self.table.viewport().mapToGlobal(position))

    def open_customer_menu(self, customer, source_widget):
        menu = QMenu(self)
        self.populate_customer_menu(menu, customer)

        # Adjust position
        pos = source_widget.mapToGlobal(source_widget.rect().bottomLeft())
        menu.exec(pos)

    def open_customer_360(self, customer):
        try:
            # Customer360Dialog expects: db, customer_id, customer_name, parent
            Customer360Dialog(self.db, customer["id"], customer["name"], self).exec()
        except Exception as e:
            show_error(self, f"Müşteri 360 açılamadı: {str(e)}")

    def on_table_double_click(self, row, column):
        if row < 0:
            return
        customer = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if not customer:
            return

        # Cari Hesap (Bakiye) sütununa (Index 6) çift tıklanırsa geçmişi aç
        if column == 5:
            self.show_history(customer)
        else:
            # Diğer sütunlarda 360'ı aç
            self.open_customer_360(customer)

    def populate_customer_menu(self, menu, customer):
        menu.addAction(
            "Musteri Notlari",
            lambda: CustomerNotesDialog(
                self.db, customer["id"], customer["name"], self
            ).exec(),
        )
        menu.addAction("Musteri 360", lambda: self.open_customer_360(customer))
        menu.addAction("Duzenle", lambda: self.edit_customer(customer))
        menu.addSeparator()
        menu.addAction("Yeni Servis Kaydi", lambda: self.create_service(customer))
        menu.addAction("Fatura Kes", lambda: self.create_invoice(customer))
        menu.addAction("Tahsilat / Odeme Al", lambda: self.record_payment(customer))
        menu.addSeparator()
        menu.addAction("WhatsApp Mesaj", lambda: self.send_whatsapp(customer))
        menu.addAction(
            "Bakiye Hatirlat (WA)", lambda: self.send_debt_reminder(customer)
        )
        menu.addSeparator()
        menu.addAction("Excel'e Aktar", self.export_excel)
        menu.addAction("PDF Olarak Kaydet", self.export_pdf)
        menu.addAction("Yazdir", self.print_list)
        if self._multi_select:
            menu.addSeparator()
            menu.addAction("Secilileri Excel Aktar", self.export_selected_csv)
        menu.addSeparator()
        menu.addAction("Musteriyi Sil", lambda: self.delete_customer(customer))

    def toggle_multiselect(self, checked: bool):
        self.table.clearSelection()
        self._multi_select = checked
        if checked:
            self.table.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
            self.btn_multi.setText("✅ COKLU SECIM")
        else:
            self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
            self.btn_multi.setText("🔲 COKLU SEC")

    def _selected_customer_rows(self):
        return sorted(
            set(index.row() for index in self.table.selectionModel().selectedRows())
        )

    def export_selected_csv(self):
        rows = self._selected_customer_rows()
        if not rows:
            show_warning(self, "Disa aktarmak icin en az bir musteri secin.")
            return
        customers = []
        for row in rows:
            item = self.table.item(row, 0)
            if item:
                customer = item.data(Qt.ItemDataRole.UserRole)
                if customer:
                    customers.append(customer)
        if not customers:
            show_warning(self, "Secili musteri kayitlari bulunamadi.")
            return
        success, msg = ExportManager.export_to_csv(customers, self)
        if success:
            show_success(self, msg)
        else:
            show_error(self, msg)

    def execute_search(self):
        self.search_query = self.inp_search.text().strip()
        self.current_page = 0
        self.request_reload()

    def add_customer(self):
        sector_manager = getattr(self.main_window, "sector_manager", None)
        if AddCustomerDialog(self.db, self, sector_manager=sector_manager).exec():
            self.request_reload()
            if self.main_window and hasattr(self.main_window, "refresh_loaded_page"):
                self.main_window.refresh_loaded_page(40)

    def send_whatsapp(self, c):
        phone = "".join(filter(str.isdigit, str(c["phone"])))
        if phone:
            if phone.startswith("0"):
                phone = "9" + phone
            webbrowser.open(f"https://wa.me/{phone}")

    def send_debt_reminder(self, c):
        balance = self.db.get_customer_balance(c["id"])
        if balance <= 0:
            show_info(self, "Müşterinin borcu bulunmamaktadır. ✅")
            return

        name = c["name"]
        phone = "".join(filter(str.isdigit, str(c["phone"])))
        if not phone:
            show_error(self, "Müşterinin telefon numarası kayıtlı değil. ❌")
            return

        if phone.startswith("0") and len(phone) == 11:
            phone = "9" + phone
        elif len(phone) == 10:
            phone = "90" + phone

        formatted_balance = CurrencyHelper.format_try_for_display(
            balance,
            db=self.db,
            include_try_reference=False,
        )
        message = (
            f"Sayın *{name}*,\n\nGüncel borç bakiyeniz: *{formatted_balance}*'dir.\n\n"
            "Ödemenizi rica eder, iyi çalışmalar dileriz. 🙏\n\n*AYEC Pro*"
        )
        import urllib.parse

        encoded_msg = urllib.parse.quote(message)
        webbrowser.open(f"https://wa.me/{phone}?text={encoded_msg}")

    def copy_list(self):

        text = ""
        for r in range(self.table.rowCount()):
            text += "\t".join([self.table.item(r, i).text() for i in range(7)]) + "\n"
        QApplication.clipboard().setText(text)
        show_info(self, "Liste panoya kopyalandı.")

    def export_csv(self):
        customers = self.db.get_customers()  # Get all customers for full export
        success, msg = ExportManager.export_to_csv(customers, self)
        if success:
            show_success(self, msg)
        else:
            show_error(self, msg)

    def show_history(self, c):
        try:
            dlg = Customer360Dialog(self.db, c["id"], c["name"], self)
            if hasattr(dlg, "tabs"):
                dlg.tabs.setCurrentIndex(1)
            dlg.exec()
        except Exception as e:
            show_error(self, f"Cari geçmiş açılamadı: {e}")

    def edit_customer(self, c):
        sector_manager = getattr(self.main_window, "sector_manager", None)
        if AddCustomerDialog(self.db, self, c, sector_manager=sector_manager).exec():
            self.request_reload()

    def record_payment(self, c):
        """Müşteriden ödeme/tahsilat al - Borç düşümü ve finans gelir akışı ile entegre"""
        dlg = TahsilatDialog(self, self.db, c)
        if dlg.exec():
            data = dlg.get_data()
            if data:
                items = data.get("selected_services") or []
                parts = []
                for it in items:
                    kind = it.get("kind")
                    if kind == "device":
                        tn = it.get("tracking_no") or ""
                        desc = it.get("description") or ""
                        label = f"Servis {tn}".strip()
                        if desc:
                            label = f"{label} - {desc}"
                        parts.append(label)
                    elif kind == "service":
                        sid = it.get("service_id")
                        desc = it.get("description") or ""
                        label = f"Hizmet #{sid}" if sid else "Hizmet"
                        if desc:
                            label = f"{label} - {desc}"
                        parts.append(label)
                    elif kind == "currency_txn":
                        tid = it.get("currency_txn_id")
                        label = f"Döviz İşlem #{tid}" if tid else "Döviz İşlem"
                        parts.append(label)
                    elif kind == "balance":
                        parts.append("Cari Borç Kapatma")
                jobs_text = ", ".join(parts[:5])
                base_desc = data["notes"].strip() if data.get("notes") else ""
                if jobs_text:
                    if base_desc:
                        full_desc = f"{base_desc} | {jobs_text}"
                    else:
                        full_desc = jobs_text
                else:
                    full_desc = base_desc or f"{data['method']} ile ödeme"

                # Get currency from dialog or default to TRY
                currency = data.get("currency", "TRY")
                exchange_rate = (
                    data.get("exchange_rate", 1.0) if currency != "TRY" else 1.0
                )
                bank_account_id = data.get("bank_account_id")
                payment_method = data.get("method")
                date_value = data.get("date")
                if date_value:
                    d = QDate.fromString(date_value, "dd.MM.yyyy")
                    if d.isValid():
                        date_value = d.toString("yyyy-MM-dd")

                reference_tracking = data.get("reference_tracking_no") or None
                reference_desc = (data.get("reference_desc") or "").strip()
                if (
                    reference_tracking
                    and reference_desc
                    and reference_desc not in full_desc
                ):
                    full_desc = f"{full_desc} | {reference_desc}"

                created_at = None
                if date_value:
                    parsed = QDate.fromString(str(data.get("date")), "dd.MM.yyyy")
                    if parsed.isValid():
                        accounting_date = parsed.toString("yyyy-MM-dd")
                        date_value = accounting_date
                        created_at = (
                            f"{accounting_date} {datetime.now().strftime('%H:%M:%S')}"
                        )

                # Önce ödeme-borç bağlantı tablosunun var olduğundan emin ol
                try:
                    self.db.create_payment_debt_links_table()
                except Exception:
                    pass

                # Use currency-aware transaction (updates customer_currency_balances)
                res = self.db.add_currency_transaction(
                    customer_id=c["id"],
                    amount=data["amount"],
                    currency=currency,
                    transaction_type="CREDIT",  # CREDIT = payment reduces debt
                    exchange_rate=exchange_rate,
                    description=full_desc,
                    tracking_no=reference_tracking,
                    created_at=created_at,
                )

                if res:
                    # Son eklenen işlemin ID'sini al (ödeme kaydı)
                    try:
                        payment_txn_id = self.db.get_last_currency_transaction_id()
                    except Exception:
                        payment_txn_id = None

                    # Seçili borç kalemlerine ödemeyi dağıt
                    selected_debt_ids = data.get("selected_debt_ids", [])
                    debt_allocation = {
                        "allocated": 0,
                        "remaining": data["amount"],
                        "linked_debts": [],
                    }

                    if payment_txn_id:
                        try:
                            debt_allocation = self.db.apply_payment_to_debts(
                                customer_id=c["id"],
                                payment_amount=data["amount"],
                                currency=currency,
                                payment_transaction_id=payment_txn_id,
                                selected_debt_ids=selected_debt_ids
                                if selected_debt_ids
                                else None,
                            )
                        except Exception as e:
                            print(f"Borç dağıtımı hatası: {e}")

                    # Finans gelir kaydı oluştur
                    try:
                        tl_amount = float(data["amount"]) * (
                            exchange_rate if currency != "TRY" else 1.0
                        )
                        self.db.add_transaction(
                            t_type="Gelir",
                            category="Tahsilat",
                            amount=tl_amount,
                            description=full_desc,
                            customer_name=c.get("name"),
                            customer_id=c["id"],
                            date=date_value,
                            payment_method=payment_method,
                            bank_account_id=bank_account_id,
                            tracking_no=reference_tracking,
                            ref_no=reference_tracking,
                            currency=currency,
                            original_amount=float(data["amount"]),
                        )
                    except Exception:
                        pass

                    # Başarı mesajı hazırla
                    success_msg = f"{CurrencyHelper.format_amount(data['amount'], currency_code=currency)} tahsilat kaydedildi."

                    if debt_allocation["linked_debts"]:
                        success_msg += f"\n{len(debt_allocation['linked_debts'])} borç kalemine dağıtıldı."

                    if debt_allocation["remaining"] > 0.01:
                        success_msg += f"\n{CurrencyHelper.format_amount(debt_allocation['remaining'], currency_code=currency)} cari hesaba işlendi."

                    success_msg += "\nMüşteri bakiyesi güncellendi."

                    show_success(self, success_msg)
                    self.request_reload()
                else:
                    show_error(self, "Ödeme kaydedilirken bir hata oluştu.")

    def create_service(self, c):
        from src.ui.dialogs.new_service_dialog import NewServiceDialog

        sector_manager = getattr(self.main_window, "sector_manager", None)
        NewServiceDialog(
            self.db, self, customer_name=c["name"], sector_manager=sector_manager
        ).exec()

    def create_invoice(self, c):
        dlg = ServiceInvoiceDialog(self.db, c["id"], self)
        if dlg.exec():
            show_success(self, "Fatura başarıyla oluşturuldu ve işlemler işaretlendi.")
            self.request_reload()

    def export_excel(self):
        customers = self.db.get_customers()
        success, msg = ExportManager.export_to_excel(customers, self)
        if success:
            show_success(self, msg)
        else:
            show_error(self, msg)

    def print_list(self):
        try:
            from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
            from PyQt6.QtGui import QTextDocument

            headers = [self.table.horizontalHeaderItem(i).text() for i in range(7)]
            rows = []
            for r in range(self.table.rowCount()):
                rows.append(
                    [
                        self.table.item(r, c).text() if self.table.item(r, c) else ""
                        for c in range(7)
                    ]
                )

            html = "<html><head><meta charset='utf-8'></head><body>"
            html += "<h2>Müşteri Listesi</h2>"
            html += "<table border='1' cellspacing='0' cellpadding='4' width='100%'>"
            html += (
                "<tr style='background:@text;color: @selection_text;font-weight:bold;'>"
            )
            for h in headers:
                html += f"<th>{h}</th>"
            html += "</tr>"
            for row in rows:
                html += "<tr>"
                for v in row:
                    html += f"<td>{v}</td>"
                html += "</tr>"
            html += "</table></body></html>"

            printer = QPrinter()
            dlg = QPrintDialog(printer, self)
            if dlg.exec() != QPrintDialog.DialogCode.Accepted:
                return

            doc = QTextDocument()
            doc.setHtml(html)
            doc.print(printer)
            show_success(self, "Yazdırma kuyruğuna gönderildi.")
        except Exception as e:
            show_error(self, f"Yazdırma hatası: {e}")

    def setup_usage_guide_tab(self):
        ly = QVBoxLayout(self.tab_guide)
        ly.setContentsMargins(0, 10, 0, 0)

        from PyQt6.QtWidgets import QTextBrowser

        guide_text = QTextBrowser()
        guide_text.setStyleSheet(
            theme_qss(
                "border: none; background: transparent; color: @text; padding: 20px;"
            )
        )

        html_content = f"""
        <div style="font-family: {DesignTokens.FONT_FAMILY}; color: @text;">
            <h1 style="color: @accent;">🤝 Müşteri & İlişki Yönetimi (CRM) Kullanım Kılavuzu</h1>
            <p>Bu modül, müşterilerinizin, bayilerinizin ve tedarikçilerinizin bilgilerini merkezi bir yerde toplar, bakiye ve işlem takibi yapmanızı sağlar.</p>
            
            <h2 style="color: @primary;">1. Müşteri Listesi ve Kartlar</h2>
            <ul>
                <li><b>Hızlı Filtre:</b> Üstteki renkli butonlar ile sadece Borçlu Müşterileri veya Bayileri listeleyebilirsiniz.</li>
                <li><b>Arama:</b> İsim, Telefon veya E-posta girerek anında arama yapabilirsiniz.</li>
                <li><b>Durum Rozetleri:</b> Kurumsal, Bayi veya Tedarikçi ayrımı isimlerin yanındaki renkli rozetlerle belirtilir.</li>
            </ul>
            
            <h2 style="color: @primary;">2. İşlemler ve Cari Takibi</h2>
            <ul>
                <li><b>İşlem Yap:</b> Tablonun en sağındaki buton veya sağ tık menüsü ile müşteriye Ödeme Alabilir, Fatura Kesebilir veya Servis Kaydı açabilirsiniz.</li>
                <li><b>Bakiye Renkleri:</b> Borçlu müşteriler <b>kırmızı</b>, alacaklı (ön ödeme yapmış) müşteriler <b>yeşil</b> görünür.</li>
                <li><b>Müşteri 360°:</b> Müşteriye çift tıklayarak tüm servis geçmişini, ödemelerini ve notlarını tek bir ekranda görebilirsiniz.</li>
            </ul>
            
            <h2 style="color: @primary;">3. İletişim Araçları</h2>
            <ul>
                <li><b>WhatsApp:</b> Tek tıkla müşteriye mesaj gönderebilir veya bakiye hatırlatması yapabilirsiniz.</li>
                <li><b>Dışa Aktar:</b> Listeyi Excel veya PDF olarak kaydedebilirsiniz.</li>
            </ul>
            
            <hr style="border: 0; border-top: 1px solid @border; margin: 20px 0;">
            <p style="color: @text_muted; font-style: italic;">AYEC Pro Teknik Servis Yönetimi - Müşteri Memnuniyeti</p>
        </div>
        """
        final_html = (
            html_content.replace("@text_muted", tc("text_muted"))
            .replace("@text", tc("text"))
            .replace("@accent", tc("accent"))
            .replace("@primary", tc("primary"))
            .replace("@border", tc("border"))
        )

        guide_text.setHtml(final_html)
        ly.addWidget(guide_text)

    def export_pdf(self):
        try:
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.platypus import (
                SimpleDocTemplate,
                Table,
                TableStyle,
                Paragraph,
                Spacer,
            )
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib import colors
            from datetime import datetime

            path, _ = QFileDialog.getSaveFileName(
                self,
                "PDF'e Aktar",
                f"musteri_listesi_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                "PDF (*.pdf)",
            )
            if not path:
                return

            headers = [self.table.horizontalHeaderItem(i).text() for i in range(7)]
            data = [headers]
            for r in range(self.table.rowCount()):
                data.append(
                    [
                        self.table.item(r, c).text() if self.table.item(r, c) else ""
                        for c in range(7)
                    ]
                )

            doc = SimpleDocTemplate(
                path,
                pagesize=landscape(A4),
                rightMargin=24,
                leftMargin=24,
                topMargin=24,
                bottomMargin=24,
            )
            styles = getSampleStyleSheet()
            story = []
            story.append(Paragraph("Müşteri Listesi", styles["Heading1"]))
            story.append(Spacer(1, 12))

            table = Table(data, repeatRows=1)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(tc("text"))),
                        (
                            "TEXTCOLOR",
                            (0, 0),
                            (-1, 0),
                            colors.HexColor(tc("selection_text")),
                        ),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 9),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [
                                colors.HexColor(tc("selection_text")),
                                colors.HexColor(tc("surface")),
                            ],
                        ),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            story.append(table)
            doc.build(story)

            show_success(self, "PDF dosyası oluşturuldu.")
            try:
                os.startfile(path)
            except Exception:
                pass
        except Exception as e:
            show_error(self, f"PDF aktarım hatası: {e}")

    def delete_customer(self, c):
        # c is tuple or dict
        # populate_customer_menu calls it with 'customer' which is a DICT from data(Qt.UserRole).
        # But wait, in show_row_menu it might be different. Let's check how it's used.
        # It's consistently used as a dict in show_context_menu/populate_customer_menu.

        # Accessing dict keys
        customer_id = c["id"]
        customer_name = c["name"]

        from PyQt6.QtWidgets import QDialog
        from src.ui.widgets.modern_confirm_dialog import ModernConfirmDialog

        dlg = ModernConfirmDialog(
            "Silme Onayı",
            f"'{customer_name}' isimli müşteriyi silmek istediğinize emin misiniz\n\nBu işlem geri alınamaz!",
            self,
            confirm_text="Evet, Sil",
            cancel_text="İptal",
            destructive=True,
        )

        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                success = self.db.delete_customer(customer_id)
                self.db.conn.commit()  # Ensure deletion is committed

                if success:
                    # Clear and reload
                    self.request_reload()
                    show_success(self, f"'{customer_name}' silindi.")
                else:
                    show_error(self, "Müşteri silinemedi.")
            except Exception as e:
                show_error(self, f"Silme hatası: {str(e)}")
