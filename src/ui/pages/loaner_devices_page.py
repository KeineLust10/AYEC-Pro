# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLayout, QFrame, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
                             QTabWidget, QLineEdit, QFormLayout, QComboBox, QMessageBox,
                             QDateTimeEdit, QMenu, QAbstractItemView, QFileDialog, QButtonGroup)
from PyQt6.QtCore import Qt, QDateTime, QTimer
from PyQt6.QtGui import QFont, QFontDatabase, QFontMetrics, QColor, QCursor, QShortcut, QKeySequence
from PyQt6.QtCore import QThread, pyqtSignal
import sqlite3
import csv
import unicodedata

from src.utils.theme_colors import tc, theme_qss
from src.utils.currency_helper import CurrencyHelper
from src.ui.widgets.modern_dialog import ModernDialog
from src.ui.widgets.loaner_summary_visuals import LoanerCategoryRing, LoanerMetricIcon
from src.ui.widgets.navigation_glyph import NavigationGlyph
from src.utils.design_system import DesignTokens
from src.utils.path_helper import PathHelper
from src.utils.logger import logger
from src.utils.message_helper import show_error, show_question, show_warning
from src.utils.system_config import SystemConfig


class LoanerDataWorker(QThread):
    loaded = pyqtSignal(list, list)
    error = pyqtSignal(str)

    def __init__(self, db_name="ayecpro.db"):
        super().__init__()
        self.db_name = db_name

    def run(self):
        try:
            db_path = PathHelper.get_db_path(self.db_name)
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            inventory = cur.execute("SELECT * FROM loaner_devices ORDER BY id DESC").fetchall()
            active = cur.execute(
                """
                SELECT t.*, d.brand_model, d.daily_penalty_fee, d.serial_mac, d.device_type
                FROM loaner_transactions t
                JOIN loaner_devices d ON t.device_id = d.id
                WHERE t.status = 'Aktif'
                """
            ).fetchall()
            conn.close()
            self.loaded.emit(list(inventory), list(active))
        except (sqlite3.Error, OSError, RuntimeError) as e:
            self.error.emit(str(e))

class LoanerDevicesPage(QWidget):
    """
    Emanet (Konsinye) Cihaz Takip Modülü Ana Sayfası
    """
    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.right_click_setting_key = "rc_loaner"
        self.active_page = 0
        self.active_page_size = 5
        self._loaner_type_filter = "all"
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        self.setup_ui()
        self._worker = None
        self._refresh_pending = False
        self._pending_inventory_rows = []
        self._pending_active_rows = []
        QTimer.singleShot(0, self._prepare_initial_view)
        QTimer.singleShot(140, self.request_refresh)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        table = getattr(self, "table_active", None)
        if table is not None:
            self._configure_active_columns(table)

    def _prepare_initial_view(self):
        if hasattr(self, "table_inventory"):
            self.table_inventory.setRowCount(0)
        if hasattr(self, "table_active"):
            self.table_active.setRowCount(0)

    def setup_ui(self):
        # Header
        header_widget = QWidget()
        header_widget.setFixedHeight(80)
        header_widget.setStyleSheet(theme_qss("background-color: @finance_surface_alt; border-bottom: 1px solid @finance_outline;"))
        
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(16, 0, 16, 0)
        
        title_vbox = QVBoxLayout()
        title_vbox.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        title_vbox.setSpacing(2)
        title = QLabel("Emanet (Konsinye) Cihazlar")
        title_font = QFont(self.font())
        if "Inter" in QFontDatabase.families():
            title_font.setFamily("Inter")
        title_font.setPointSize(16)
        title_font.setWeight(QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet(theme_qss("color: @finance_text; background: transparent; border: none;"))
        
        subtitle = QLabel("Müşterilere verilen geçici (ikame) cihazların depo ve durum takibi.")
        subtitle.setFont(QFont("Segoe UI", 11))
        subtitle.setStyleSheet(theme_qss("color: @finance_text_muted; background: transparent; border: none;"))
        
        title_vbox.addWidget(title)
        title_vbox.addWidget(subtitle)
        title_vbox.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        header_layout.addLayout(title_vbox)
        header_layout.addStretch()

        self.btn_refresh = QPushButton('')
        self.btn_refresh.setAccessibleName('RefreshLoanerDevices')
        self.btn_refresh.setFixedSize(34, 34)
        self.btn_refresh.setToolTip("Yenile")
        self.btn_refresh.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_refresh.setStyleSheet(theme_qss(
            DesignTokens.get_button_qss("secondary", size="sm")
        ))
        refresh_layout = QHBoxLayout(self.btn_refresh)
        refresh_layout.setContentsMargins(0, 0, 0, 0)
        self.refresh_glyph = NavigationGlyph('\U0001f504', title='RefreshLoanerDevices')
        self.refresh_glyph.setFixedSize(18, 18)
        self.refresh_glyph.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        refresh_layout.addWidget(self.refresh_glyph, alignment=Qt.AlignmentFlag.AlignCenter)
        self.btn_refresh.clicked.connect(self.request_refresh)
        header_layout.addWidget(self.btn_refresh)

        btn_add_device = QPushButton("+ Yeni Emanet Ver")
        btn_add_device.setFixedSize(126, 32)
        btn_add_device.setToolTip("Depodaki cihazi teslim et")
        btn_add_device.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_add_device.setStyleSheet(theme_qss(
            DesignTokens.get_button_qss("primary", size="sm")
        ))
        action_font = QFont(title_font)
        action_font.setPointSize(10)
        btn_add_device.setFont(action_font)
        btn_add_device.clicked.connect(self._start_new_loan)
        header_layout.addWidget(btn_add_device)

        for label, callback, variant in [
            ("Iade Al & Test Et", self._return_selected_active, "secondary"),
            ("Sozlesme", self._open_commitments_tab, "secondary"),
            ("Excel", self._show_export_notice, "secondary"),
        ]:
            action = QPushButton(label)
            action.setMinimumWidth(88)
            action.setMinimumHeight(34)
            action.setStyleSheet(theme_qss(DesignTokens.get_button_qss(variant, size="sm")))
            action.clicked.connect(callback)
            header_layout.addWidget(action)
        
        self.layout.addWidget(header_widget)

        metric_row = QHBoxLayout()
        metric_row.setContentsMargins(20, 10, 20, 10)
        metric_row.setSpacing(10)
        self.loaner_metric_values = []
        for index, (title_text, value_text, accent) in enumerate([
            ("Musterideki Ikameler", "0 Cihaz", "@finance_primary"),
            ("Musait Konsinye Stok", "0 Cihaz", "@finance_secondary"),
            ("Iadesi Gecikenler", "0 Acil", "@finance_tertiary"),
            ("Sahadaki Cihaz Degeri", "0 TRY", "@finance_text"),
        ]):
            card = QFrame()
            card.setObjectName("LoanerMetricCard")
            card.setMinimumHeight(84)
            card.setStyleSheet(theme_qss("QFrame#LoanerMetricCard { background: @finance_surface; border: 1px solid @finance_outline; border-radius: 6px; } QLabel { background: transparent; border: none; }"))
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 8, 12, 8)
            title_label = QLabel(title_text)
            title_label.setStyleSheet(theme_qss("color: @finance_text_muted; font-size: 10px; font-weight: 800; border: none;"))
            value_label = QLabel(value_text)
            value_label.setStyleSheet(theme_qss(f"color: {accent}; font-size: 18px; font-weight: 900; border: none;"))
            title_row = QHBoxLayout()
            title_label.setWordWrap(True)
            title_row.addWidget(title_label, 1)
            title_row.addWidget(LoanerMetricIcon(("computer", "warehouse", "warning", "shield")[index], accent.lstrip("@")))
            card_layout.addLayout(title_row)
            card_layout.addWidget(value_label)
            self.loaner_metric_values.append(value_label)
            metric_row.addWidget(card, 1)
        self.layout.addLayout(metric_row)
        
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: none; border-top: 1px solid {tc('border')}; }}
            QTabBar::tab {{ 
                background: {tc('surface')}; 
                color: {tc('text_muted')}; 
                padding: 8px 14px;
                font-size: 12px;
                font-weight: 600;
                border: 1px solid {tc('border')};
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{ 
                background: {tc('surface_alt')};
                color: {tc('primary')}; 
                border-bottom: 3px solid {tc('primary')};
            }}
            QTabBar::tab:hover {{ color: {tc('text')}; }}
        """)
        
        # Tab 1: Aktif Emanetler (Müşteride Olanlar)
        self.tab_active = QWidget()
        self.setup_active_tab()
        
        # Tab 2: Depo Envanteri (Tüm Cihazlar)
        self.tab_inventory = QWidget()
        self.setup_inventory_tab()
        
        self.tabs.addTab(self.tab_active, "Müşterideki Cihazlar (Aktif)")
        self.tabs.addTab(self.tab_inventory, "Emanet Cihaz Deposu")
        
        # Tab 3: Nasıl Kullanılır? (Usage Guide)
        if SystemConfig.is_feature_active(self.db, "usage_guides"):
            self.tab_guide = QWidget()
            self.setup_usage_guide_tab()
            self.tabs.addTab(self.tab_guide, "❓ Nasıl Kullanılır?")

        self.tab_return_history = QWidget()
        history_layout = QVBoxLayout(self.tab_return_history)
        history_layout.setContentsMargins(0, 10, 0, 0)
        self.table_return_history = QTableWidget(0, 9)
        self.table_return_history.setHorizontalHeaderLabels([
            "\u0130\u015flem ID", "Cihaz / Seri No", "M\u00fc\u015fteri", "Verili\u015f", "Beklenen \u0130ade",
            "\u0130ade Tarihi", "Gecikme Cezas\u0131", "Teslim Durumu", "Durum",
        ])
        self._configure_table(self.table_return_history)
        self.table_return_history.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table_return_history.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_return_history.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        history_layout.addWidget(self.table_return_history)
        self.loaner_history_count = QLabel("0 kayit")
        history_layout.addWidget(self.loaner_history_count)
        self.tabs.addTab(self.tab_return_history, "Iade Gecmisi & Arsiv")

        self.tab_commitments = QWidget()
        commitments_layout = QVBoxLayout(self.tab_commitments)
        commitments_layout.addWidget(QLabel("Iade Taahhut Sozlesmesi"))
        commitments_layout.addWidget(QLabel("Musteriye verilen cihazlar icin e-imza ve teslim taahhutlerini yonetin."))
        commitments_layout.addStretch()
        self.tabs.addTab(self.tab_commitments, "Iade Taahhutleri")
        
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(12, 8, 12, 12)
        self.tabs.tabBar().hide()
        navigation = QHBoxLayout()
        navigation.setSpacing(4)
        self.loaner_navigation_group = QButtonGroup(self)
        self.loaner_navigation_group.setExclusive(True)
        self._loaner_nav_buttons = []
        destinations = [
            ("M\u00fc\u015fterideki Cihazlar (Aktif)", self.tab_active, "Tum Durumlar"),
            ("Emanet Cihaz Deposu", self.tab_inventory, "Tum Durumlar"),
            ("Gecikmi\u015f \u0130adeler", self.tab_active, "Geciken"),
            ("\u0130ade Ge\u00e7mi\u015fi & Ar\u015fiv", self.tab_return_history, "Tum Durumlar"),
            ("Taahh\u00fctler", self.tab_commitments, "Tum Durumlar"),
        ]
        if hasattr(self, "tab_guide"):
            destinations.append(("Nas\u0131l Kullan\u0131l\u0131r?", self.tab_guide, "Tum Durumlar"))
        for label, destination, status in destinations:
            button = QPushButton(label)
            button.setCheckable(True)
            button.setMinimumHeight(32)
            button.setStyleSheet(theme_qss(
                "QPushButton { background: transparent; color: @finance_text_muted; border: none; padding: 6px 8px; font-size: 12px; font-weight: 600; } "
                "QPushButton:checked { background: @finance_surface_alt; color: @finance_primary; border-bottom: 2px solid @primary; }"
            ))
            self.loaner_navigation_group.addButton(button)
            self._loaner_nav_buttons.append((destination, status, button))
            button.clicked.connect(lambda _checked=False, target=destination, mode=status: self._select_loaner_view(target, mode))
            navigation.addWidget(button)
        navigation.addStretch()
        self._loaner_nav_buttons[0][2].setChecked(True)
        self.tabs.currentChanged.connect(self._sync_loaner_navigation)
        content_layout.addLayout(navigation)
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(8)
        self.loaner_search = QLineEdit()
        self.loaner_search.setPlaceholderText("Cihaz, musteri veya seri no ara...")
        self.loaner_search.setClearButtonEnabled(True)
        self.loaner_search.textChanged.connect(self._loaner_filter_changed)
        self.loaner_search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self.loaner_search_shortcut.activated.connect(self._focus_loaner_search)
        self.loaner_status = QComboBox()
        self.loaner_status.addItems(["Tum Durumlar", "Aktif", "Geciken", "Musait"])
        self.loaner_status.currentTextChanged.connect(self._loaner_filter_changed)
        filter_bar.addWidget(self.loaner_search, 1)
        self.loaner_type_group = QButtonGroup(self)
        self.loaner_type_group.setExclusive(True)
        self.loaner_type_buttons = {}
        for label, category in [("T\u00fcm\u00fc", "all"), ("Laptop / PC", "pc"),
                                ("Switch & A\u011f", "network"), ("NVR / Kamera", "video")]:
            button = QPushButton(label)
            button.setCheckable(True)
            button.setChecked(category == "all")
            button.setStyleSheet(theme_qss(
                "QPushButton { background: transparent; color: @finance_text_muted; border: none; padding: 5px 7px; font-size: 11px; } "
                "QPushButton:checked { background: @finance_surface_alt; color: @finance_text; border-radius: 4px; }"
            ))
            self.loaner_type_group.addButton(button)
            self.loaner_type_buttons[category] = button
            button.clicked.connect(lambda _checked=False, value=category: self._set_loaner_type(value))
            filter_bar.addWidget(button)
        filter_bar.addWidget(self.loaner_status)
        content_layout.addLayout(filter_bar)
        content_layout.addWidget(self.tabs)
        self.layout.addWidget(content_container)
        self.layout.addWidget(self._build_bottom_summary())

    def _build_bottom_summary(self):
        wrapper = QFrame()
        wrapper.setObjectName("LoanerSummaryWrapper")
        wrapper.setFixedHeight(180)
        wrapper.setStyleSheet(theme_qss(
            "QFrame#LoanerSummaryWrapper { background: @finance_surface_alt; border: 1px solid @finance_outline; border-radius: 6px; }"
        ))
        row = QHBoxLayout(wrapper)
        row.setContentsMargins(20, 10, 20, 10)
        row.setSpacing(10)
        cards = [
            ("Konsinye Cihaz Kategorileri", "-"),
            ("Iade Taahhut Sozlesmesi", "Teslim ve iade taahhut kayitlari"),
            ("Hizli Rezerve Edilebilir Stok", "-"),
        ]
        self.loaner_summary_details = []
        for index, (title, body) in enumerate(cards):
            card = QFrame()
            card.setObjectName("LoanerSummaryCard")
            card.setStyleSheet(theme_qss(
                "QFrame#LoanerSummaryCard { background: @finance_surface; border: 1px solid @finance_outline; border-radius: 6px; } QLabel { background: transparent; border: none; }"
            ))
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 8, 12, 8)
            heading = QLabel(title)
            heading.setStyleSheet(theme_qss("color: @finance_text; font-weight: 800;"))
            detail = QLabel(body)
            detail.setWordWrap(True)
            detail.setStyleSheet(theme_qss("color: @finance_text_muted; font-size: 10px; line-height: 1.3;"))
            card_layout.addWidget(heading, 0, Qt.AlignmentFlag.AlignTop)
            if index == 0:
                distribution = QHBoxLayout()
                self.loaner_category_ring = LoanerCategoryRing()
                distribution.addWidget(self.loaner_category_ring, 0, Qt.AlignmentFlag.AlignVCenter)
                distribution.addWidget(detail, 1, Qt.AlignmentFlag.AlignTop)
                card_layout.addLayout(distribution, 1)
            else:
                card_layout.addWidget(detail, 1, Qt.AlignmentFlag.AlignTop)
            self.loaner_summary_details.append(detail)
            if index == 1:
                commitments = QPushButton("Taahh\u00fct Kay\u0131tlar\u0131 >")
                commitments.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
                commitments.clicked.connect(self._open_commitments_tab)
                card_layout.addWidget(commitments)
            elif index == 2:
                detail.setMaximumHeight(20)
                self.loaner_reserve_layout = QVBoxLayout()
                self.loaner_reserve_layout.setSpacing(3)
                card_layout.addLayout(self.loaner_reserve_layout)
                depot_link = QPushButton("T\u00fcm Depoyu G\u00f6r\u00fcnt\u00fcle >")
                depot_link.setStyleSheet(theme_qss("QPushButton { color: @finance_secondary; background: transparent; border: none; padding: 4px; font-size: 10px; font-weight: 600; }"))
                depot_link.clicked.connect(lambda: self._select_loaner_view(self.tab_inventory, "Tum Durumlar"))
                card_layout.addWidget(depot_link)
            row.addWidget(card, 1)
        return wrapper

    def setup_active_tab(self):
        ly = QVBoxLayout(self.tab_active)
        ly.setContentsMargins(0, 10, 0, 0)
        
        self.table_active = QTableWidget(0, 10)
        self.table_active.setHorizontalHeaderLabels([
            "\u0130\u015flem\nID", "Cihaz / Model\n(Seri No)", "M\u00fc\u015fteri", "Verili\u015f\nTarihi", "\u0130ade\nTarihi", "Durum /\nUyar\u0131", "Teminat /\nKo\u015ful", "\u0130\u015flemler", "Servis\nEmri", "Ge\u00e7en\nS\u00fcre"
        ])
        for table in [self.table_active]:
            self._configure_table(table)
            self._configure_active_columns(table)
        self.table_active.customContextMenuRequested.connect(self.open_active_context_menu)
        self.table_active.setShowGrid(False)
        self.table_active.setAlternatingRowColors(False)
        active_header = self.table_active.horizontalHeader()
        active_header.moveSection(active_header.visualIndex(8), 3)
        active_header.moveSection(active_header.visualIndex(9), 6)
        active_header.moveSection(active_header.visualIndex(7), 9)
        ly.addWidget(self.table_active)
        pager = QHBoxLayout()
        self.active_result_label = QLabel()
        self.active_result_label.setStyleSheet(theme_qss("color: @text_muted; background: transparent; border: none;"))
        pager.addWidget(self.active_result_label, 1)
        self.active_previous = QPushButton("<")
        self.active_page_label = QLabel("1 / 1")
        self.active_next = QPushButton(">")
        for button in (self.active_previous, self.active_next):
            button.setFixedSize(32, 28)
            button.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm") + "QPushButton { padding: 0; min-height: 0; }"))
        self.active_previous.clicked.connect(lambda: self._change_active_page(-1))
        self.active_next.clicked.connect(lambda: self._change_active_page(1))
        pager.addWidget(self.active_previous)
        pager.addWidget(self.active_page_label)
        pager.addWidget(self.active_next)
        ly.addLayout(pager)

    def _loaner_filter_changed(self, *_args):
        self.active_page = 0
        self._apply_filters()
        self._sync_loaner_navigation()

    def _focus_loaner_search(self):
        self.loaner_search.setFocus()
        self.loaner_search.selectAll()

    def _set_loaner_type(self, category):
        self._loaner_type_filter = category
        self.active_page = 0
        self._apply_filters()

    @staticmethod
    def _loaner_type_group(device_type):
        normalized = unicodedata.normalize("NFKD", str(device_type or '').lower().replace("\u0131", "i"))
        normalized = normalized.encode("ascii", "ignore").decode("ascii")
        words = set(normalized.replace("/", " ").replace("&", " ").replace("-", " ").split())
        if words.intersection(("laptop", "notebook", "pc", "masaustu", "dizustu", "istasyonu", "sunucu")):
            return "pc"
        if words.intersection(("switch", "router", "network", "ag", "agi")):
            return "network"
        if words.intersection(("nvr", "kamera", "camera")):
            return "video"
        return "other"

    def _select_loaner_view(self, destination, status):
        self.tabs.setCurrentWidget(destination)
        self.loaner_status.setCurrentText(status)
        if destination is self.tab_return_history:
            self.load_return_history()
        self._sync_loaner_navigation()

    def _sync_loaner_navigation(self, *_args):
        if not hasattr(self, "loaner_status"):
            return
        current = self.tabs.currentWidget()
        mode = "Geciken" if current is self.tab_active and self.loaner_status.currentText() == "Geciken" else "Tum Durumlar"
        for destination, status, button in self._loaner_nav_buttons:
            if destination is current and status == mode:
                button.setChecked(True)
                break

    def _change_active_page(self, delta):
        self.active_page += int(delta)
        self._apply_filters()

    def _apply_filters(self):
        query = self.loaner_search.text().strip().lower() if hasattr(self, "loaner_search") else ""
        status = self.loaner_status.currentText() if hasattr(self, "loaner_status") else "Tum Durumlar"
        for table in (getattr(self, "table_active", None), getattr(self, "table_inventory", None)):
            if table is None:
                continue
            matching_rows = []
            for row in range(table.rowCount()):
                values = []
                for column in range(table.columnCount()):
                    item = table.item(row, column)
                    if item:
                        values.append(item.text().lower())
                haystack = " ".join(values)
                matches_query = not query or query in haystack
                matches_status = status == "Tum Durumlar"
                if status == "Aktif":
                    matches_status = table is self.table_active
                elif status == "Geciken":
                    matches_status = table is self.table_active and "gecikti" in haystack
                elif status == "Musait":
                    matches_status = table is self.table_inventory and "depoda" in haystack
                type_item = table.item(row, 0)
                device_type = type_item.data(Qt.ItemDataRole.UserRole + 1) if type_item else ''
                matches_type = self._loaner_type_filter == "all" or self._loaner_type_group(device_type) == self._loaner_type_filter
                if matches_query and matches_status and matches_type:
                    matching_rows.append(row)
            if table is self.table_active:
                self._active_export_rows = list(matching_rows)
            else:
                self._inventory_export_rows = list(matching_rows)
            if table is self.table_active:
                pages = max(1, (len(matching_rows) + self.active_page_size - 1) // self.active_page_size)
                self.active_page = max(0, min(self.active_page, pages - 1))
                start = self.active_page * self.active_page_size
                page_rows = matching_rows[start:start + self.active_page_size]
                shown_start = start + 1 if page_rows else 0
                self.active_result_label.setText("Toplam {} aktif kay\u0131ttan {}-{} aras\u0131 g\u00f6steriliyor.".format(len(matching_rows), shown_start, start + len(page_rows)))
                self.active_page_label.setText("{} / {}".format(self.active_page + 1, pages))
                self.active_previous.setEnabled(self.active_page > 0)
                self.active_next.setEnabled(self.active_page + 1 < pages)
                visible_rows = set(page_rows)
            else:
                visible_rows = set(matching_rows)
            for row in range(table.rowCount()):
                table.setRowHidden(row, row not in visible_rows)
        if hasattr(self, "table_return_history"):
            visible = 0
            for row in range(self.table_return_history.rowCount()):
                values = [self.table_return_history.item(row, column).text().lower()
                          for column in range(self.table_return_history.columnCount())
                          if self.table_return_history.item(row, column)]
                hidden = bool(query and query not in " ".join(values))
                type_item = self.table_return_history.item(row, 0)
                device_type = type_item.data(Qt.ItemDataRole.UserRole + 1) if type_item else ''
                if self._loaner_type_filter != "all" and self._loaner_type_group(device_type) != self._loaner_type_filter:
                    hidden = True
                self.table_return_history.setRowHidden(row, hidden)
                visible += not hidden
            self.loaner_history_count.setText("{} / {} kayit".format(visible, self.table_return_history.rowCount()))

    def _return_selected_active(self):
        row = self.table_active.currentRow()
        if row < 0:
            self.tabs.setCurrentWidget(self.tab_active)
            self.table_active.setFocus()
            return
        trans_item = self.table_active.item(row, 0)
        if trans_item is None:
            return
        record = self.db.cursor.execute(
            "SELECT device_id FROM loaner_transactions WHERE id = ?", (trans_item.text(),)
        ).fetchone()
        if record:
            self.return_device(trans_item.text(), record[0])

    def _open_commitments_tab(self):
        self.tabs.setCurrentWidget(self.tab_commitments)

    def _show_export_notice(self):
        if self.tabs.currentWidget() is self.tab_return_history:
            table = self.table_return_history
            rows = [row for row in range(table.rowCount()) if not table.isRowHidden(row)]
        else:
            table = self.table_inventory if self.tabs.currentWidget() is self.tab_inventory else self.table_active
            rows = getattr(self, "_inventory_export_rows" if table is self.table_inventory else "_active_export_rows", list(range(table.rowCount())))
        path, _ = QFileDialog.getSaveFileName(self, "Excel uyumlu rapor", "emanet_raporu.csv", "CSV (*.csv)")
        if not path:
            return
        header = table.horizontalHeader()
        columns = [header.logicalIndex(index) for index in range(table.columnCount())
                   if table is self.table_return_history or header.logicalIndex(index) != 7]
        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.writer(stream, delimiter=";")
                active_headers = {
                    0: "\u0130\u015flem ID", 1: "Cihaz Marka/Model", 2: "Teslim Alan",
                    3: "Verili\u015f Tarihi", 4: "Beklenen \u0130ade", 5: "Durum / Uyar\u0131",
                    6: "Gecikme Cezas\u0131", 7: "\u0130\u015flemler", 8: "\u0130lgili Kay\u0131t",
                    9: "Ge\u00e7en S\u00fcre",
                }
                writer.writerow([
                    active_headers.get(column, table.horizontalHeaderItem(column).text())
                    if table is self.table_active else table.horizontalHeaderItem(column).text()
                    for column in columns
                ])
                for row in rows:
                    writer.writerow([table.item(row, column).text() if table.item(row, column) else ""
                                     for column in columns])
        except OSError as error:
            show_error(self, "Rapor", "Rapor kaydedilemedi: {}".format(error))

    def load_return_history(self, records=None):
        try:
            if records is None:
                records = self.db.cursor.execute(
                    "SELECT t.*, d.brand_model, d.serial_mac, d.device_type FROM loaner_transactions t "
                    "JOIN loaner_devices d ON d.id=t.device_id "
                    "WHERE t.status <> 'Aktif' ORDER BY t.date_returned DESC, t.id DESC"
                ).fetchall()
            self.table_return_history.setRowCount(0)
            query = self.loaner_search.text().strip().lower()
            visible_count = 0
            for record in records:
                row = self.table_return_history.rowCount()
                self.table_return_history.insertRow(row)
                brand = "{}\nSN: {}".format(record['brand_model'], record['serial_mac'] or '-')
                values = [str(record['id']), brand, str(record['customer_name'] or '-'),
                          str(record['date_given'] or '-'), str(record['expected_return'] or '-'),
                          str(record['date_returned'] or '-'),
                          CurrencyHelper.format_try_for_display(record['penalty_applied'] or 0, db=self.db, include_try_reference=False),
                          str(record['condition_in'] or '-'), str(record['status'] or '-')]
                for column, value in enumerate(values):
                    self.table_return_history.setItem(row, column, QTableWidgetItem(value))
                self.table_return_history.item(row, 0).setData(Qt.ItemDataRole.UserRole + 1, str(record['device_type'] or ''))
                self.table_return_history.setRowHeight(row, 62)
                hidden = bool(query and query not in " ".join(values).lower())
                self.table_return_history.setRowHidden(row, hidden)
                visible_count += not hidden
            self.loaner_history_count.setText("{} / {} kayit".format(visible_count, self.table_return_history.rowCount()))
            self._apply_filters()
        except (sqlite3.Error, RuntimeError, TypeError, ValueError) as error:
            logger.error("Loaner return history loading failed: %s", error)

    def setup_inventory_tab(self):
        ly = QVBoxLayout(self.tab_inventory)
        ly.setContentsMargins(0, 10, 0, 0)
        inventory_commands = QHBoxLayout()
        add_device = QPushButton("+ Yeni Cihaz Ekle")
        add_device.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        add_device.clicked.connect(self.add_new_device)
        inventory_commands.addWidget(add_device)
        inventory_commands.addStretch()
        ly.addLayout(inventory_commands)
        
        self.table_inventory = QTableWidget(0, 8)
        self.table_inventory.setHorizontalHeaderLabels([
            "ID", "Cihaz Tipi", "Marka/Model", "Seri/MAC", "Raf No", "Durum", "Günlük Ceza", "İşlemler"
        ])
        for table in [self.table_inventory]:
            self._configure_table(table)
            self._configure_inventory_columns(table)
        self.table_inventory.customContextMenuRequested.connect(self.open_inventory_context_menu)
        self.table_inventory.cellDoubleClicked.connect(self._handle_inventory_double_click)
        ly.addWidget(self.table_inventory)

    def _configure_table(self, table):
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.setAlternatingRowColors(True)
        table.setWordWrap(True)
        table.setTextElideMode(Qt.TextElideMode.ElideRight)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(62)
        table.verticalHeader().setMinimumSectionSize(56)
        table.setStyleSheet(theme_qss("""
            QTableWidget {
                background-color: @surface;
                color: @text;
                border: 1px solid @border;
                border-radius: 8px;
                gridline-color: @border;
                outline: none;
            }
            QTableWidget::item {
                padding: 8px 10px;
                border: none;
                outline: none;
            }
            QTableWidget::item:selected {
                background-color: @selection_bg;
                color: @selection_text;
                border: none;
                outline: none;
            }
            QHeaderView::section {
                background-color: @surface_alt;
                color: @text;
                font-weight: bold;
                border: none;
                border-bottom: 1px solid @border;
                padding: 9px;
            }
            QPushButton {
                min-height: 30px;
                border-radius: 5px;
                padding: 5px 9px;
                font-weight: 700;
            }
        """))

    def _configure_active_columns(self, table):
        header = table.horizontalHeader()
        wide = self.width() > 980
        widths = (
            (80, 180, 144, 112, 112, 136, 130, 110, 140, 108)
            if not wide
            else (56, 190, 165, 108, 108, 120, 138, 180, 128, 92)
        )
        for column, width in enumerate(widths):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
            table.setColumnWidth(column, width)
        if wide:
            for column in (1, 2, 3, 4, 8):
                header.setSectionResizeMode(column, QHeaderView.ResizeMode.Stretch)
        else:
            header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)

    def _configure_inventory_columns(self, table):
        header = table.horizontalHeader()
        for col in range(table.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(7, 270)

    def _is_context_menu_enabled(self):
        if self.db.get_setting("enable_right_click", "1") == "0":
            return False
        return self.db.get_setting(self.right_click_setting_key, "1") == "1"

    def open_inventory_context_menu(self, position):
        if not self._is_context_menu_enabled():
            show_warning(self, "Hata", "Marka/Model ve Seri No alanları zorunludur.")
            return

        row = self.table_inventory.rowAt(position.y())
        menu = QMenu(self)
        menu.addAction("➕ Yeni Cihaz Ekle", self.add_new_device)
        menu.addAction("🔄 Yenile", self.refresh_data)

        if row >= 0:
            self.table_inventory.selectRow(row)
            dev_id_item = self.table_inventory.item(row, 0)
            status_item = self.table_inventory.item(row, 5)
            if dev_id_item:
                dev_id = dev_id_item.text().strip()
                status_text = status_item.text().strip() if status_item else ""
                menu.addSeparator()
                if status_text == "Depoda":
                    menu.addAction("📤 Cihazı Zimmetle", lambda did=dev_id: self.assign_device(did))
                menu.addAction("Düzenle", lambda did=dev_id: self.edit_device(did))
                menu.addAction("🗑️ Cihazı Sil", lambda did=dev_id: self.delete_device(did))

        menu.exec(self.table_inventory.viewport().mapToGlobal(position))

    def open_active_context_menu(self, position):
        if not self._is_context_menu_enabled():
            return

        row = self.table_active.rowAt(position.y())
        menu = QMenu(self)
        menu.addAction("🔄 Yenile", self.refresh_data)

        if row >= 0:
            self.table_active.selectRow(row)
            trans_id_item = self.table_active.item(row, 0)
            if trans_id_item:
                trans_id = trans_id_item.text().strip()
                try:
                    rec = self.db.cursor.execute(
                        "SELECT device_id FROM loaner_transactions WHERE id = ?",
                        (trans_id,)
                    ).fetchone()
                    if rec:
                        menu.addSeparator()
                        menu.addAction(
                            "📥 Cihazı İade Al",
                            lambda tid=trans_id, did=rec["device_id"]: self.return_device(tid, did)
                        )
                except (TypeError, ValueError, sqlite3.Error):
                    pass

        menu.exec(self.table_active.viewport().mapToGlobal(position))

    def _handle_inventory_double_click(self, row, column):
        if column == 7:
            return
        dev_id = self._inventory_device_id(row)
        if dev_id:
            self.edit_device(dev_id)

    def _inventory_device_id(self, row):
        if row < 0:
            return None
        item = self.table_inventory.item(row, 0)
        return item.text().strip() if item else None

    def request_refresh(self, delay_ms=0):
        if self._worker and self._worker.isRunning():
            self._refresh_pending = True
            return
        QTimer.singleShot(delay_ms, self.refresh_data)

    def refresh_data(self):
        if self._worker and self._worker.isRunning():
            self._refresh_pending = True
            return
        self.btn_refresh.setEnabled(False)
        self._worker = LoanerDataWorker(getattr(self.db, "_db_name", "ayecpro.db"))
        self._worker.loaded.connect(self._on_data_loaded)
        self._worker.error.connect(self._on_worker_error)
        self._worker.finished.connect(lambda: self.btn_refresh.setEnabled(True))
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.start()

    def _on_worker_error(self, err_msg):
        try:
            if self.main_window and hasattr(self.main_window, "show_notification"):
                self.main_window.show_notification(f"Emanet veri yükleme hatası: {err_msg}", "error")
        except (AttributeError, RuntimeError):
            pass

    def _on_worker_finished(self):
        self._worker = None
        if self._refresh_pending:
            self._refresh_pending = False
            QTimer.singleShot(0, self.refresh_data)

    def _on_data_loaded(self, inventory_rows, active_rows):
        self._pending_inventory_rows = list(inventory_rows or [])
        self._pending_active_rows = list(active_rows or [])
        self._update_loaner_metrics(self._pending_inventory_rows, self._pending_active_rows)
        QTimer.singleShot(0, self._load_inventory_deferred)
        QTimer.singleShot(0, self._load_active_deferred)

    def _update_loaner_metrics(self, inventory_rows, active_rows):
        active_count = len(active_rows)
        occupied_ids = {str(row['device_id']) for row in active_rows}
        available = [row for row in inventory_rows
                     if str(row['status'] or '') == 'Depoda'
                     and str(row['id']) not in occupied_ids]
        available_count = len(available)
        now = QDateTime.currentDateTime()
        overdue_count = sum(
            1 for row in active_rows
            if (deadline := QDateTime.fromString(str(row['expected_return'] or '')[:19],
                                                "yyyy-MM-dd HH:mm:ss")).isValid()
            and deadline < now
        )
        if len(self.loaner_metric_values) == 4:
            self.loaner_metric_values[0].setText(f"{active_count} Cihaz")
            self.loaner_metric_values[1].setText(f"{available_count} Cihaz")
            self.loaner_metric_values[2].setText(f"{overdue_count} Acil")
            self.loaner_metric_values[3].setText("-")
            self.loaner_metric_values[3].setToolTip("Cihaz degeri kaydedilmedigi icin hesaplanamiyor.")
        categories = {}
        for row in inventory_rows:
            category = str(row['device_type'] or 'Diger')
            categories[category] = categories.get(category, 0) + 1
        self.loaner_summary_details[0].setText("\n".join(
            "{}    {} Adet".format(name, count) for name, count in sorted(categories.items())
        ) or "Kayit yok")
        self.loaner_category_ring.set_categories(categories)
        self.loaner_summary_details[2].setText("{} Hazir".format(available_count))
        while self.loaner_reserve_layout.count():
            item = self.loaner_reserve_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for record in available[:3]:
            reserve = QPushButton("{}    Hemen Ata".format(record['brand_model']))
            reserve.setObjectName("LoanerReserve{}".format(record['id']))
            reserve.setStyleSheet(theme_qss("QPushButton { text-align: left; background: @finance_surface_alt; color: @finance_text; border: none; padding: 4px 6px; border-radius: 4px; font-size: 10px; } QPushButton:hover { color: @finance_primary; }"))
            reserve.clicked.connect(lambda _checked=False, device_id=record['id']: self.assign_device(device_id))
            self.loaner_reserve_layout.addWidget(reserve)

    def _load_inventory_deferred(self):
        self.load_inventory(self._pending_inventory_rows)

    def _load_active_deferred(self):
        self.load_active_loans(self._pending_active_rows)

    def load_inventory(self, records=None):
        self.table_inventory.setRowCount(0)
        try:
            if records is None:
                records = self.db.cursor.execute("SELECT * FROM loaner_devices ORDER BY id DESC").fetchall()
            for r in records:
                row = self.table_inventory.rowCount()
                self.table_inventory.insertRow(row)
                d_id = str(r['id'])
                dev_type = str(r['device_type'] or '')
                brand_model = str(r['brand_model'] or '')
                serial_mac = str(r['serial_mac'] or '')
                shelf_no = str(r['shelf_no'] or '')
                status = str(r['status'] or 'Depoda')
                penalty = float(r['daily_penalty_fee'] or 0.0)

                id_item = QTableWidgetItem(d_id)
                id_item.setData(Qt.ItemDataRole.UserRole + 1, dev_type)
                self.table_inventory.setItem(row, 0, id_item)
                self.table_inventory.setItem(row, 1, QTableWidgetItem(dev_type))
                self.table_inventory.setItem(row, 2, QTableWidgetItem(brand_model))
                self.table_inventory.setItem(row, 3, QTableWidgetItem(serial_mac))
                self.table_inventory.setItem(row, 4, QTableWidgetItem(shelf_no))
                
                status_item = QTableWidgetItem(status)
                if status == 'Depoda':
                    status_item.setForeground(QColor("#10B981"))
                elif status == 'Müşteride':
                    status_item.setForeground(QColor("#F59E0B"))
                else:
                    status_item.setForeground(QColor("#EF4444"))
                    
                self.table_inventory.setItem(row, 5, status_item)
                self.table_inventory.setItem(row, 6, QTableWidgetItem(f"{CurrencyHelper.format_try_for_display(penalty, db=self.db, include_try_reference=False)} / Gün"))

                actions_container = QWidget()
                actions_layout = QHBoxLayout(actions_container)
                actions_layout.setContentsMargins(4, 2, 4, 2)
                actions_layout.setSpacing(6)
                
                if status == 'Depoda':
                    btn_assign = QPushButton("Zimmet")
                    btn_assign.setMinimumWidth(72)
                    btn_assign.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                    btn_assign.setStyleSheet(f"background: {tc('success')}; color: white; border:none; padding: 6px; border-radius:4px; font-weight: bold;")
                    btn_assign.clicked.connect(lambda checked, did=d_id: self.assign_device(did))
                    actions_layout.addWidget(btn_assign)

                btn_edit = QPushButton("Düzenle")
                btn_edit.setMinimumWidth(78)
                btn_edit.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                btn_edit.setStyleSheet(f"background: {tc('primary')}; color: white; border:none; padding: 6px; border-radius:4px; font-weight: bold;")
                btn_edit.clicked.connect(lambda checked, did=d_id: self.edit_device(did))
                actions_layout.addWidget(btn_edit)
                
                btn_del = QPushButton("Sil")
                btn_del.setMinimumWidth(52)
                btn_del.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                btn_del.setStyleSheet(f"background: {tc('danger')}; color: white; border:none; padding: 6px; border-radius:4px; font-weight: bold;")
                btn_del.clicked.connect(lambda checked, did=d_id: self.delete_device(did))
                actions_layout.addWidget(btn_del)
                
                self.table_inventory.setCellWidget(row, 7, actions_container)
                self.table_inventory.setRowHeight(row, 62)
        except (sqlite3.Error, RuntimeError, TypeError, ValueError) as e:
            logger.error(f"Envanter yükleme hatası: {e}")
        self._apply_filters()

    def load_active_loans(self, records=None):
        self.table_active.setRowCount(0)
        try:
            if records is None:
                records = self.db.cursor.execute('''
                    SELECT t.*, d.brand_model, d.daily_penalty_fee, d.serial_mac, d.device_type
                    FROM loaner_transactions t
                    JOIN loaner_devices d ON t.device_id = d.id
                    WHERE t.status = 'Aktif'
                ''').fetchall()
            
            for r in records:
                row = self.table_active.rowCount()
                self.table_active.insertRow(row)
                t_id = str(r['id'])
                brand = str(r['brand_model'])
                if 'serial_mac' in r.keys() and r['serial_mac']:
                    brand += "\nSN: " + str(r['serial_mac'])
                customer = f"{r['customer_name']}\n{r['customer_phone']}"
                expected = r['expected_return']
                given = r['date_given']
                
                # Check delay
                penalty_calc = CurrencyHelper.format_try_for_display(0, db=self.db, include_try_reference=False)
                delay_str = "S\u00fcre Devam Ediyor"
                is_delayed = False
                if expected:
                    dt_exp = QDateTime.fromString(expected[:19], "yyyy-MM-dd HH:mm:ss")
                    dt_now = QDateTime.currentDateTime()
                    if dt_exp.isValid() and dt_now > dt_exp:
                        days_late = dt_exp.daysTo(dt_now)
                        if days_late >= 0:
                            is_delayed = True
                            delay_str = f"{days_late} G\u00fcn Gecikti"
                            fee = float(r['daily_penalty_fee'] or 0)
                            penalty_calc = CurrencyHelper.format_try_for_display(fee * days_late, db=self.db, include_try_reference=False)

                id_item = QTableWidgetItem(t_id)
                id_item.setData(Qt.ItemDataRole.UserRole + 1, str(r['device_type'] or '') if 'device_type' in r.keys() else '')
                self.table_active.setItem(row, 0, id_item)
                self.table_active.setItem(row, 1, QTableWidgetItem(brand))
                self.table_active.setItem(row, 2, QTableWidgetItem(customer))
                given_date = QDateTime.fromString(str(given or '')[:19], "yyyy-MM-dd HH:mm:ss")
                given_item = QTableWidgetItem(given_date.toString("dd.MM.yyyy") if given_date.isValid() else "-")
                given_item.setToolTip(str(given or ''))
                self.table_active.setItem(row, 3, given_item)
                tracking = str(r['tracking_no'] or '-') if 'tracking_no' in r.keys() else '-'
                self.table_active.setItem(row, 8, QTableWidgetItem(tracking))
                elapsed = max(0, given_date.daysTo(QDateTime.currentDateTime())) if given_date.isValid() else None
                self.table_active.setItem(row, 9, QTableWidgetItem("{} G\u00fcn".format(elapsed) if elapsed is not None else "-"))
                
                expected_date = QDateTime.fromString(str(expected or '')[:19], "yyyy-MM-dd HH:mm:ss")
                exp_item = QTableWidgetItem(expected_date.toString("dd.MM.yyyy") if expected_date.isValid() else "Belirsiz")
                exp_item.setToolTip(str(expected or ''))
                if is_delayed:
                    exp_item.setForeground(QColor(tc('danger')))
                self.table_active.setItem(row, 4, exp_item)
                
                delay_item = QTableWidgetItem(delay_str)
                if is_delayed:
                    delay_item.setForeground(QColor(tc('danger')))
                self.table_active.setItem(row, 5, delay_item)
                status_cell = QWidget()
                status_cell.setObjectName("LoanerStatusCell")
                status_cell.setStyleSheet(theme_qss("QWidget#LoanerStatusCell { background: @surface; }"))
                status_layout = QHBoxLayout(status_cell)
                status_layout.setContentsMargins(4, 0, 4, 0)
                badge = QLabel(delay_str if is_delayed else "AKTIF /\nSURESINDE")
                badge.setWordWrap(True)
                badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                badge.setMaximumHeight(40)
                badge.setStyleSheet(theme_qss(
                    "QLabel { background: @finance_surface_alt; color: "
                    + ("@danger" if is_delayed else "@finance_primary")
                    + "; border: none; border-radius: 6px; padding: 4px; font-size: 10px; font-weight: 700; }"
                ))
                status_layout.addWidget(badge)
                self.table_active.setCellWidget(row, 5, status_cell)
                
                self.table_active.setItem(row, 6, QTableWidgetItem(penalty_calc))

                btn_return = QPushButton("\u0130ade Al")
                btn_return.setFixedSize(92, 32)
                btn_return.setStyleSheet(theme_qss("QPushButton { background: @finance_surface_alt; color: @finance_text; border: 1px solid @finance_outline; padding: 0; min-height: 26px; border-radius: 4px; } QPushButton:hover { border-color: @primary; }"))
                btn_return.clicked.connect(lambda checked, tid=t_id, did=r['device_id']: self.return_device(tid, did))
                action_cell = QWidget()
                action_layout = QHBoxLayout(action_cell)
                action_layout.setContentsMargins(6, 0, 6, 0)
                action_layout.addWidget(btn_return, 0, Qt.AlignmentFlag.AlignCenter)
                self.table_active.setCellWidget(row, 7, action_cell)
                self.table_active.setRowHeight(row, 76)
                for column in (0, 3, 4, 6, 8, 9):
                    item = self.table_active.item(row, column)
                    if item is None:
                        continue
                    font = QFont(DesignTokens.MONO_FONT_NAME)
                    font.setPixelSize(11)
                    font.setBold(column in (0, 6, 8))
                    item.setFont(font)
                    if column not in (3, 4):
                        item.setToolTip(item.text())

        except (sqlite3.Error, RuntimeError, TypeError, ValueError) as e:
            logger.error(f"Aktif konsinye yükleme hatası: {e}")
        self._apply_filters()

    def add_new_device(self):
        dialog = ModernDialog("Yeni İkame Cihaz Ekle", self, width=540, height=580)
        form = QFormLayout()
        form.setSpacing(15)
        form.setVerticalSpacing(15)

        type_w = QComboBox()
        type_w.addItems(["Akıllı Telefon", "Dizüstü Bilgisayar", "Tablet", "Router/Modem", "Yedek Parça", "Diğer"])

        brand_w = QLineEdit()
        brand_w.setPlaceholderText("Örn: Apple iPhone 15")
        
        serial_w = QLineEdit()
        serial_w.setPlaceholderText("Seri No veya MAC Adresi")
        
        shelf_w = QLineEdit()
        shelf_w.setPlaceholderText("Örn: A-12, Raf 3")
        
        penalty_w = QLineEdit("50.0")
        penalty_w.setPlaceholderText("Günlük gecikme bedeli")
        
        from PyQt6.QtWidgets import QTextEdit
        notes_w = QTextEdit()
        notes_w.setPlaceholderText("Cihaz kondisyonu, aksesuarlar ve diğer notlar...")
        notes_w.setMinimumHeight(100)

        form.addRow("Cihaz Tipi:", type_w)
        form.addRow("Marka & Model:", brand_w)
        form.addRow("Seri / MAC No:", serial_w)
        form.addRow("Raf No:", shelf_w)
        form.addRow(f"Günlük Ceza ({CurrencyHelper.get_label(db=self.db)}):", penalty_w)
        form.addRow("Demirbaş Notu:", notes_w)
        
        dialog.add_layout(form)

        dialog.add_cancel_button("Vazgeç")
        dialog.add_button("Envantere Kaydet", "primary", lambda: self._save_device(
            dialog, 
            type_w.currentText(), 
            brand_w.text(), 
            serial_w.text(), 
            shelf_w.text(),
            penalty_w.text(), 
            notes_w.toPlainText()
        ))
        dialog.exec()

    
    def _save_device(self, dialog, c_type, brand, serial, shelf, penalty, notes):
        if not brand or not serial:
            show_warning(self, "Hata", "Marka/Model ve Seri No alanları zorunludur.")
            return
        try:
            p_val = float(penalty)
        except (TypeError, ValueError) as e:
            logger.debug(f"Loaner device penalty parse fallback: {e}")
            p_val = 0.0
            
        try:
            self.db.cursor.execute(
                "INSERT INTO loaner_devices (device_type, brand_model, serial_mac, shelf_no, daily_penalty_fee, notes) VALUES (?, ?, ?, ?, ?, ?)",
                (c_type, brand, serial, shelf, p_val, notes)
            )
            self.db.conn.commit()
            if self.main_window and hasattr(self.main_window, "show_notification"):
                self.main_window.show_notification("Yeni emanet cihazı depoya başarıyla eklendi.", "success")
            dialog.accept()
            self.request_refresh()
        except (sqlite3.Error, ValueError, TypeError) as e:
            show_error(self, "Hata", f"Kayıt eklenemedi: {e}")

    def edit_device(self, dev_id):
        try:
            record = self.db.cursor.execute(
                "SELECT * FROM loaner_devices WHERE id=?",
                (dev_id,),
            ).fetchone()
        except (sqlite3.Error, RuntimeError) as e:
            show_error(self, "Hata", f"Emanet cihaz bilgisi okunamadı: {e}")
            return

        if not record:
            show_warning(self, "Hata", "Düzenlenecek emanet cihaz bulunamadı.")
            return

        dialog = ModernDialog("Emanet Cihazı Düzenle", self, width=540, height=580)
        form = QFormLayout()
        form.setSpacing(15)
        form.setVerticalSpacing(15)

        type_w = QComboBox()
        type_w.addItems(["Akıllı Telefon", "Dizüstü Bilgisayar", "Tablet", "Router/Modem", "Yedek Parça", "Diğer"])
        current_type = str(record["device_type"] or "")
        type_idx = type_w.findText(current_type)
        if type_idx >= 0:
            type_w.setCurrentIndex(type_idx)
        elif current_type:
            type_w.addItem(current_type)
            type_w.setCurrentText(current_type)

        brand_w = QLineEdit(str(record["brand_model"] or ""))
        serial_w = QLineEdit(str(record["serial_mac"] or ""))
        shelf_w = QLineEdit(str(record["shelf_no"] or ""))
        penalty_w = QLineEdit(str(record["daily_penalty_fee"] or "0.0"))

        from PyQt6.QtWidgets import QTextEdit
        notes_w = QTextEdit()
        notes_w.setPlainText(str(record["notes"] or ""))
        notes_w.setMinimumHeight(100)

        form.addRow("Cihaz Tipi:", type_w)
        form.addRow("Marka & Model:", brand_w)
        form.addRow("Seri / MAC No:", serial_w)
        form.addRow("Raf No:", shelf_w)
        form.addRow(f"Günlük Ceza ({CurrencyHelper.get_label(db=self.db)}):", penalty_w)
        form.addRow("Demirbaş Notu:", notes_w)
        dialog.add_layout(form)

        dialog.add_cancel_button("Vazgeç")
        dialog.add_button("Değişiklikleri Kaydet", "primary", lambda: self._update_device(
            dialog,
            dev_id,
            type_w.currentText(),
            brand_w.text(),
            serial_w.text(),
            shelf_w.text(),
            penalty_w.text(),
            notes_w.toPlainText(),
        ))
        dialog.exec()

    def _update_device(self, dialog, dev_id, c_type, brand, serial, shelf, penalty, notes):
        if not brand or not serial:
            show_warning(self, "Hata", "Marka/Model ve Seri No alanları zorunludur.")
            return
        try:
            p_val = float(penalty)
        except (TypeError, ValueError) as e:
            logger.debug(f"Loaner device penalty parse fallback: {e}")
            p_val = 0.0

        try:
            self.db.cursor.execute(
                """
                UPDATE loaner_devices
                SET device_type=?, brand_model=?, serial_mac=?, shelf_no=?, daily_penalty_fee=?, notes=?
                WHERE id=?
                """,
                (c_type, brand, serial, shelf, p_val, notes, dev_id),
            )
            self.db.conn.commit()
            if self.main_window and hasattr(self.main_window, "show_notification"):
                self.main_window.show_notification("Emanet cihaz bilgileri güncellendi.", "success")
            dialog.accept()
            self.request_refresh()
        except (sqlite3.Error, ValueError, TypeError) as e:
            show_error(self, "Hata", f"Kayıt güncellenemedi: {e}")

    def delete_device(self, dev_id):
        reply = show_question(
            self,
            "Onay",
            "Bu emanet cihazını envanterden tamamen silmek istediğinize emin misiniz",
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db.cursor.execute("DELETE FROM loaner_devices WHERE id=?", (dev_id,))
                self.db.conn.commit()
                self.request_refresh()
            except (sqlite3.Error, RuntimeError) as e:
                show_error(self, "Hata", f"Silme başarısız: {e}")

    def _start_new_loan(self):
        try:
            available = self.db.cursor.execute(
                "SELECT d.id, d.brand_model, d.serial_mac FROM loaner_devices d "
                "WHERE d.status='Depoda' AND NOT EXISTS "
                "(SELECT 1 FROM loaner_transactions t WHERE t.device_id=d.id AND t.status='Aktif') "
                "ORDER BY d.brand_model, d.id"
            ).fetchall()
        except sqlite3.Error as error:
            show_error(self, "Emanet", "Depo listesi okunamadi: {}".format(error))
            return
        if not available:
            self._select_loaner_view(self.tab_inventory, "Tum Durumlar")
            show_warning(self, "Emanet", "Teslim edilebilecek musait cihaz yok. Depoya yeni cihaz ekleyin.")
            return
        dialog = ModernDialog("Yeni Emanet Ver", self, width=520, height=240)
        choice = QComboBox()
        for record in available:
            choice.addItem("{} / {}".format(record['brand_model'], record['serial_mac'] or '-'), record['id'])
        form = QFormLayout()
        form.addRow("Musait cihaz:", choice)
        dialog.add_layout(form)
        dialog.add_cancel_button("Vazgec")
        dialog.add_button("Teslim Bilgileri", "primary", dialog.accept)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self.assign_device(choice.currentData())

    def assign_device(self, dev_id):
        dialog = ModernDialog("Müşteriye Tesis Et (Zimmetle)", self, width=560, height=520)
        form = QFormLayout()
        form.setSpacing(15)
        form.setVerticalSpacing(15)

        f_name = QLineEdit()
        f_name.setPlaceholderText("Müşteri Adı Soyadı")
        
        f_phone = QLineEdit()
        f_phone.setPlaceholderText("Telefon Numarası")
        
        f_track = QLineEdit()
        f_track.setPlaceholderText("Servis Takip Numarası (Opsiyonel)")
        
        from PyQt6.QtWidgets import QTextEdit
        f_cond = QTextEdit()
        f_cond.setPlaceholderText("Örn: Ekranda çizik yok, şarj aletiyle verildi")
        f_cond.setMinimumHeight(80)

        f_date = QDateTimeEdit(QDateTime.currentDateTime().addDays(3))
        f_date.setCalendarPopup(True)
        f_date.setMinimumHeight(40)

        form.addRow("Müşteri Adı:", f_name)
        form.addRow("Telefon:", f_phone)
        form.addRow("Servis Kaydı (Fiş):", f_track)
        form.addRow("Veriliş Durumu (Not):", f_cond)
        form.addRow("Beklenen İade Tarihi:", f_date)
        dialog.add_layout(form)

        dialog.add_cancel_button("Vazgeç")
        dialog.add_button("Zimmetle ve Teslim Et", "success", lambda: self._save_assignment(
            dialog, dev_id, f_name.text(), f_phone.text(), f_track.text(), f_cond.toPlainText(), 
            f_date.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        ))
        dialog.exec()

    
    def _save_assignment(self, dialog, dev_id, name, phone, track, cond, target_date):
        if not name:
            show_warning(self, "Hata", "Müşteri adı zorunludur.")
            return
        
        try:
            self.db.cursor.execute("""
                INSERT INTO loaner_transactions (device_id, customer_name, customer_phone, tracking_no, condition_out, expected_return)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (dev_id, name, phone, track, cond, target_date))
             
            self.db.cursor.execute("UPDATE loaner_devices SET status='Müşteride' WHERE id=?", (dev_id,))
            self.db.conn.commit()
            
            if self.main_window and hasattr(self.main_window, "show_notification"):
                self.main_window.show_notification("Cihaz müşteriye başarıyla zimmetlendi.", "success")
            
            dialog.accept()
            self.request_refresh()
        except (sqlite3.Error, RuntimeError, TypeError, ValueError) as e:
            show_error(self, "Hata", f"Kayıt işlemi başarısız: {e}")

    def return_device(self, trans_id, dev_id):
        dialog = ModernDialog("Cihazı İade Al", self, width=540, height=400)
        form = QFormLayout()
        form.setSpacing(15)
        form.setVerticalSpacing(15)

        f_cond = QLineEdit()
        f_cond.setPlaceholderText("İade alınırkenki cihaz durumu (Örn: Sağlam / Kamera Kırık)")

        f_penalty = QLineEdit("0")
        f_penalty.setPlaceholderText(f"Ek ceza / hasar ücreti ({CurrencyHelper.get_label(db=self.db)})")

        form.addRow("İade Durumu:", f_cond)
        form.addRow("Kesilecek Hasar/Ceza Ücreti:", f_penalty)
        dialog.add_layout(form)

        lbl_info = QLabel("ℹ️ Bu işlem sonrası cihaz tekrar 'Depoda' statüsüne geçer.")
        lbl_info.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; margin-top: 5px;"))
        dialog.add_widget(lbl_info)

        dialog.add_cancel_button("Vazgeç")
        dialog.add_button("İşlemi Tamamla & İade Al", "warning", lambda: self._save_return(
            dialog, trans_id, dev_id, f_cond.text(), f_penalty.text()
        ))
        dialog.exec()

    
    def _save_return(self, dialog, trans_id, dev_id, cond, penalty):
        try:
            p_val = float(penalty) if penalty else 0.0
        except (TypeError, ValueError) as e:
            logger.debug(f"Loaner return penalty parse fallback: {e}")
            p_val = 0.0
            
        try:
            now_str = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss")
            self.db.cursor.execute("""
                UPDATE loaner_transactions 
                SET date_returned=?, condition_in=?, penalty_applied=?, status='Tamamlandı'
                WHERE id=?
            """, (now_str, cond, p_val, trans_id))
             
            self.db.cursor.execute("UPDATE loaner_devices SET status='Depoda' WHERE id=?", (dev_id,))
            self.db.conn.commit()
            
            if self.main_window and hasattr(self.main_window, "show_notification"):
                if p_val > 0:
                    self.main_window.show_notification(
                        "Cihaz iade alındı. Tahakkuk eden ceza: "
                        f"{CurrencyHelper.format_try_for_display(p_val, db=self.db, include_try_reference=False)}",
                        "warning",
                    )
                else:
                    self.main_window.show_notification("Cihaz sorunsuz şekilde iade alındı ve depoya döndü.", "success")
                    
            dialog.accept()
            self.request_refresh()
        except (sqlite3.Error, RuntimeError, TypeError, ValueError) as e:
            show_error(self, "Hata", f"İade işlemi sırasında hata: {e}")

    def setup_usage_guide_tab(self):
        ly = QVBoxLayout(self.tab_guide)
        ly.setContentsMargins(0, 10, 0, 0)
        
        from PyQt6.QtWidgets import QTextBrowser
        guide_text = QTextBrowser()
        guide_text.setOpenExternalLinks(True)
        guide_text.setStyleSheet(theme_qss("border: none; background: transparent; color: @text; padding: 20px;"))
        
        html_content = f"""
        <div style="font-family: {DesignTokens.FONT_FAMILY}; color: @text;">
            <h1 style="color: @accent;">📖 Emanet (Konsinye) Cihaz Takip Modülü Kullanım Kılavuzu</h1>
            <p>Bu modül, teknik servis sürecinde müşterilere verilen geçici cihazların stok ve durum takibini yapmak için tasarlanmıştır.</p>
            
            <h2 style="color: @primary;">1. Müşterideki Cihazlar (Aktif) Sekmesi</h2>
            <ul>
                <li><b>Takip:</b> Şu an müşterilerde olan tüm cihazları listeler.</li>
                <li><b>Gecikme:</b> İade tarihi geçen cihazlar otomatik olarak <b>kırmızı</b> ile işaretlenir.</li>
                <li><b>İade Al:</b> Müşteri cihazı getirdiğinde bu butonu kullanarak cihazı depoya geri alabilirsiniz.</li>
            </ul>
            
            <h2 style="color: @primary;">2. Emanet Cihaz Deposu Sekmesi</h2>
            <ul>
                <li><b>Envanter:</b> Elinizdeki tüm emanet cihazları ve raf numaralarını görebilirsiniz.</li>
                <li><b>Yeni Cihaz:</b> Üstteki <b>"+ Yeni Cihaz Ekle"</b> butonu ile depoya yeni ikame cihazlar girebilirsiniz.</li>
                <li><b>Zimmetle:</b> Bir cihazı müşteriye vereceğiniz zaman bu butona basarak müşteri bilgilerini girmeniz yeterlidir.</li>
            </ul>
            
            <h2 style="color: @primary;">3. İpuçları ve Kısayollar</h2>
            <p>💡 Cihazları eklerken <b>"Raf No"</b> bilgisini girmek, yoğun zamanlarda cihazı hızlıca bulmanızı sağlar.</p>
            <p>💡 <b>Gecikme Cezası:</b> Cihazı tanımlarken günlük gecikme bedeli belirlerseniz, sistem otomatik olarak borç hesaplaması yapar.</p>
            
            <hr style="border: 0; border-top: 1px solid @border; margin: 20px 0;">
            <p style="color: @text_muted; font-style: italic;">AYEC Pro Teknik Servis Yönetimi - Akıllı İkame Çözümleri</p>
        </div>
        """
        # theme_qss doesn't process HTML, we should replace tokens manually or use theme_manager helper if exists.
        # But for now, we'll use literal colors or basic CSS.
        # Let's fix tokens in HTML:
        final_html = html_content.replace("@text_muted", tc("text_muted")).replace("@text", tc("text")).replace("@accent", tc("accent")).replace("@primary", tc("primary")).replace("@border", tc("border"))
        
        guide_text.setHtml(final_html)
        ly.addWidget(guide_text)
