"""
Yeni İşlem Sayfası (PyQt5)
BulutTech.py'deki İşlemView'ın PyQt5 versiyonu
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QFrame, QDoubleSpinBox,
                             QComboBox, QTextEdit, QDateEdit, QSpinBox, QGroupBox,
                             QFormLayout, QSplitter, QDialog, QRadioButton, QGridLayout,
                             QMenu, QListWidget, QListWidgetItem, QGraphicsDropShadowEffect, QStackedWidget,
                             QFileDialog, QInputDialog, QTreeWidget, QTreeWidgetItem)
from src.utils.toast_notification import show_success, show_error, show_warning, show_info
from src.utils.currency_helper import CurrencyHelper
from src.utils.exchange_rate_manager import ExchangeRateManager
from src.ui.pages.transaction_multi_select_dialog import MultiSelectServiceDialog
from src.ui.pages.transaction_page_behaviors import TransactionPageBehaviorMixin
from PyQt6.QtCore import Qt, QDate, pyqtSignal, QTimer
from PyQt6.QtGui import QAction, QFont, QColor, QIcon
from src.utils.logger import logger
from src.utils.theme_colors import theme_qss
from src.utils.design_system import DesignTokens
import uuid
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# Error handling ve validation
try:
    from src.utils.error_handler import handle_exceptions, validate_input, ValidationError
    ERROR_HANDLER_AVAILABLE = True
except ImportError:
    ERROR_HANDLER_AVAILABLE = False
    def handle_exceptions(func):
        return func


class TransactionPage(TransactionPageBehaviorMixin, QWidget):
    """Yeni Satış ve Servis İşlemi Sayfası"""
    
    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.cart_items = []  # Sepet
        self.current_exchange_rate = 1.0  # Varsayılan TRY
        self.init_ui()
        self._apply_global_currency_setting()
        # Sayfa geçişlerini bloklamamak için ilk veri yüklemeyi kademeli başlat.
        QTimer.singleShot(0, self._deferred_initial_load)

    def _apply_global_currency_setting(self):
        if not hasattr(self, 'cmb_currency'):
            return
        code = CurrencyHelper.get_code(self.db)
        index_map = {"TRY": 0, "USD": 1, "EUR": 2}
        self.cmb_currency.setCurrentIndex(index_map.get(code, 0))

    def _deferred_initial_load(self):
        QTimer.singleShot(0, self._deferred_load_customers)

    def _deferred_load_customers(self):
        self.load_customers()
        QTimer.singleShot(0, self._deferred_load_services)

    def _deferred_load_services(self):
        self.load_services()
        QTimer.singleShot(0, self._deferred_load_exchange_rates)

    def _deferred_load_exchange_rates(self):
        self.update_exchange_rates()  # Kurları güncelle

    def showEvent(self, event):
        super().showEvent(event)
        try:
            self.load_services()
        except Exception:
            pass
    
    def init_ui(self):
        self.services_data = {} # Initialize data first
        
        # Main Layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # --- PREMIUM TOP TABS ---
        tabs_container = QFrame()
        tabs_container.setObjectName("TabsContainer")
        tabs_container.setFixedHeight(70)
        tabs_container.setStyleSheet("""
            #TabsContainer {
                background-color: white;
                border-radius: 15px;
                border: 1px solid #e0e0e0;
            }
        """)
        # Shadow for tabs
        tab_shadow = QGraphicsDropShadowEffect()
        tab_shadow.setBlurRadius(15)
        tab_shadow.setOffset(0, 4)
        tab_shadow.setColor(QColor(0,0,0,10))
        tabs_container.setGraphicsEffect(tab_shadow)

        self.tab_layout = QHBoxLayout(tabs_container)
        self.tab_layout.setContentsMargins(10, 10, 10, 10)
        self.tab_layout.setSpacing(10)

        self.tab_buttons = []
        tab_info = [
            ("Müşteri Seçimi", "👤"),
            ("Hizmetler & Parçalar", "🛠️"),
            ("Satış Özeti & Onay", "💳")
        ]

        for i, (text, icon) in enumerate(tab_info):
            btn = QPushButton(f"{icon} {text}")
            btn.setCheckable(True)
            btn.setFixedHeight(50)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            from PyQt6.QtWidgets import QSizePolicy
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed) # Horizontal expand
            btn.setStyleSheet(self.get_tab_style(False))
            btn.clicked.connect(lambda checked, idx=i: self.switch_tab(idx))
            self.tab_layout.addWidget(btn, 1) # Equal stretch
            self.tab_buttons.append(btn)

        self.tab_buttons[0].setChecked(True)
        self.tab_buttons[0].setStyleSheet(self.get_tab_style(True))

        main_layout.addWidget(tabs_container)

        # --- STACKED CONTENT AREA ---
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)

        # Page 1: Customer Selection
        self.page_customer = self.create_customer_page()
        self.stack.addWidget(self.page_customer)

        # Page 2: Service Selection
        self.page_services = self.create_services_page()
        self.stack.addWidget(self.page_services)

        # Page 3: Summary & Payment
        self.page_summary = self.create_summary_page()
        self.stack.addWidget(self.page_summary)

        self.setLayout(main_layout)

    def get_tab_style(self, active):
        if active:
            return """
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3498db, stop:1 #2980b9);
                    color: white;
                    border-radius: 10px;
                    font-weight: bold;
                    font-size: 14px;
                    border: none;
                }
            """
        else:
            return """
                QPushButton {
                    background: #f8f9fa;
                    color: #7f8c8d;
                    border-radius: 10px;
                    font-weight: 500;
                    font-size: 14px;
                    border: 1px solid transparent;
                }
                QPushButton:hover {
                    background: #f1f2f6;
                    border: 1px solid #e0e0e0;
                }
            """

    def switch_tab(self, index):
        # Update summary labels if moving to summary tab
        if index == 2:
            cust_name = self.cmb_customer.currentText()
            if self.cmb_customer.currentIndex() == 0:
                cust_name = "Peşin / Genel Müşteri"
            self.lbl_summary_customer.setText(f"Müşteri: <b>{cust_name}</b>")
            self.lbl_summary_items.setText(f"Hizmet Sayısı: <b>{len(self.cart_items)}</b>")
            self.update_totals()

        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.tab_buttons):
            btn.setChecked(i == index)
            btn.setStyleSheet(self.get_tab_style(i == index))

    def create_customer_page(self):
        page = QFrame()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)

        # Centered Welcome 
        welcome_box = QVBoxLayout()
        welcome_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_icon = QLabel("👤")
        lbl_icon.setFont(QFont("Segoe UI Emoji", 48))
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_title = QLabel("Müşteri Seçimi")
        lbl_title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #2c3e50;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_sub = QLabel("İşlem yapılacak müşteriyi seçin veya yeni bir kayıt oluşturun.")
        lbl_sub.setFont(QFont("Segoe UI", 12))
        lbl_sub.setStyleSheet("color: #7f8c8d;")
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)

        welcome_box.addWidget(lbl_icon)
        welcome_box.addWidget(lbl_title)
        welcome_box.addWidget(lbl_sub)
        layout.addLayout(welcome_box)

        # Input Card
        card = QFrame()
        card.setObjectName("PageCard")
        card.setStyleSheet("#PageCard { background: white; border-radius: 20px; border: 1px solid #e0e0e0; }")
        card.setFixedWidth(600)
        card_shadow = QGraphicsDropShadowEffect()
        card_shadow.setBlurRadius(30)
        card_shadow.setColor(QColor(0,0,0,15))
        card.setGraphicsEffect(card_shadow)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(30, 30, 30, 30)
        card_layout.setSpacing(20)

        # Combo
        lbl_sel = QLabel("Müşteri Ara / Seç")
        lbl_sel.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_sel.setStyleSheet("color: #34495e;")
        
        # Combo + Search Button Row
        combo_box_layout = QHBoxLayout()
        combo_box_layout.setSpacing(10)

        self.cmb_customer = QComboBox()
        self.cmb_customer.setEditable(True)
        self.cmb_customer.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.cmb_customer.setMinimumHeight(50)
        self.cmb_customer.setStyleSheet("""
            QComboBox {
                padding: 10px 15px;
                border: 2px solid #ecf0f1;
                border-radius: 10px;
                background: #fdfdfd;
                font-size: 14px;
                color: #2c3e50;
            }
            QComboBox:focus { border-color: #3498db; background: white; }
        """)
        
        btn_search = QPushButton("🔍")
        btn_search.setFixedSize(50, 50)
        btn_search.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_search.setToolTip("Detaylı Müşteri Ara")
        btn_search.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border-radius: 10px;
                font-size: 20px;
                border: none;
            }
            QPushButton:hover { background-color: #2980b9; }
        """)
        btn_search.clicked.connect(self.open_customer_search)
        
        combo_box_layout.addWidget(self.cmb_customer, 1)
        combo_box_layout.addWidget(btn_search)
        
        card_layout.addWidget(lbl_sel)
        card_layout.addLayout(combo_box_layout)

        # Event filter to show popup on click (Requested by user)
        self.cmb_customer.lineEdit().installEventFilter(self)

        # Divider or info
        info_row = QHBoxLayout()
        info_row.addWidget(QLabel("📅 İşlem Tarihi:"))
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setMinimumHeight(40)
        self.date_edit.setStyleSheet("padding: 5px; border: 1px solid #ddd; border-radius: 8px;")
        info_row.addWidget(self.date_edit)
        card_layout.addLayout(info_row)

        # Next Button
        btn_next = QPushButton("Hizmetleri Seç →")
        btn_next.setFixedHeight(55)
        btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_next.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border-radius: 12px;
                font-weight: bold;
                font-size: 15px;
            }
            QPushButton:hover { background-color: #2ecc71; }
        """)
        btn_next.clicked.connect(lambda: self.switch_tab(1))
        card_layout.addWidget(btn_next)

        center_layout = QHBoxLayout()
        center_layout.addStretch()
        center_layout.addWidget(card)
        center_layout.addStretch()
        layout.addLayout(center_layout)
        layout.addStretch()

        return page
        
    def open_customer_search(self):
        """Open detailed customer search dialog."""
        try:
            from src.ui.dialogs.customer_select_dialog import CustomerSelectDialog
            dlg = CustomerSelectDialog(self.db, self)
            if dlg.exec():
                selected_id = dlg.selected_customer_id
                # Find in combo
                index = self.cmb_customer.findData(selected_id)
                if index >= 0:
                    self.cmb_customer.setCurrentIndex(index)
                else:
                    # Reload customers and try again
                    self.load_customers()
                    index = self.cmb_customer.findData(selected_id)
                    if index >= 0:
                        self.cmb_customer.setCurrentIndex(index)
        except ImportError:
            show_error(self, "Müşteri arama modülü bulunamadı.")
        except (AttributeError, TypeError, ValueError) as e:
            show_error(self, f"Arama hatası: {e}")

    def create_services_page(self):
        page = QFrame()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Left side: Selection
        left_panel = QFrame()
        left_panel.setObjectName("SelectionCard")
        left_panel.setStyleSheet("#SelectionCard { background: white; border-radius: 20px; border: 1px solid #e0e0e0; }")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(25, 25, 25, 25)
        left_layout.setSpacing(15)

        lbl_title = QLabel("Hizmet Ekle")
        lbl_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        left_layout.addWidget(lbl_title)

        # Service Combo
        from src.ui.widgets.checkable_combobox import CheckableComboBox
        self.cmb_service = CheckableComboBox()
        self.cmb_service.setPlaceholderText("Hizmet Ara / Seç...")
        self.cmb_service.setMinimumHeight(45)
        self.cmb_service.setMinimumWidth(300)
        self.cmb_service.lineEdit().textChanged.connect(self.on_service_selection_change)
        # Trigger on checkbox change
        self.cmb_service.model().dataChanged.connect(lambda: self.on_service_selection_change())
        self.cmb_service.setStyleSheet("border: 2px solid #ecf0f1; border-radius: 8px; padding: 5px;")
        left_layout.addWidget(QLabel("Hizmetler (Çoklu Seçilebilir)"))
        left_layout.addWidget(self.cmb_service)

        self.inp_desc = QLineEdit()
        self.inp_desc.setPlaceholderText("Geniş açıklama girin...")
        self.inp_desc.setMinimumHeight(45)
        self.inp_desc.setStyleSheet("border: 2px solid #ecf0f1; border-radius: 8px; padding: 10px;")
        left_layout.addWidget(QLabel("Notlar / Açıklama"))
        left_layout.addWidget(self.inp_desc)
        
        # Adet Input
        self.inp_qty = QSpinBox()
        self.inp_qty.setRange(1, 999)
        self.inp_qty.setValue(1)
        self.inp_qty.setMinimumHeight(45)
        self.inp_qty.setStyleSheet("font-size: 16px; font-weight: bold; border: 2px solid #ecf0f1; border-radius: 8px; padding: 5px;")
        left_layout.addWidget(QLabel("Adet"))
        left_layout.addWidget(self.inp_qty)

        self.inp_price = QDoubleSpinBox()
        self.inp_price.setRange(0, 999999)
        self.inp_price.setSuffix(f" {CurrencyHelper.get_symbol(self.db)}")
        self.inp_price.setMinimumHeight(45)
        self.inp_price.setStyleSheet("font-size: 16px; font-weight: bold; border: 2px solid #ecf0f1; border-radius: 8px; padding: 5px;")
        left_layout.addWidget(QLabel("Birim Fiyat"))
        left_layout.addWidget(self.inp_price)

        # Real-time Total Calculation
        cur_symbol = CurrencyHelper.get_symbol(self.db)
        self.lbl_line_total = QLabel(f"Satır Toplamı: 0.00 {cur_symbol}")
        self.lbl_line_total.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lbl_line_total.setStyleSheet("font-size: 14px; color: #27ae60; font-weight: bold; margin-top: 2px;")
        left_layout.addWidget(self.lbl_line_total)

        self.inp_qty.valueChanged.connect(self.update_calc_total)
        self.inp_price.valueChanged.connect(self.update_calc_total)
        


        btn_add = QPushButton("➕ SEPETE EKLE")
        btn_add.setFixedHeight(55)
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #16a085, stop:1 #1abc9c);
                color: white;
                border-radius: 12px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background: #1abc9c; }
        """)
        btn_add.clicked.connect(self.add_to_cart)
        left_layout.addWidget(btn_add)
        
        # Bulk Select Button
        btn_bulk = QPushButton("📝 TOPLU SEÇİM LİSTESİ")
        btn_bulk.setFixedHeight(45)
        btn_bulk.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_bulk.setStyleSheet("""
            QPushButton {
                background: white;
                color: #2c3e50;
                border: 2px solid #bdc3c7;
                border-radius: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background: #ecf0f1; border-color: #95a5a6; }
        """)
        btn_bulk.clicked.connect(self.open_multi_select)
        left_layout.addWidget(btn_bulk)

        left_layout.addStretch()

        # Right side: Basket list
        right_panel = QFrame()
        right_panel.setObjectName("BasketCard")
        right_panel.setStyleSheet("#BasketCard { background: #fdfdfd; border-radius: 20px; border: 1px solid #e0e0e0; }")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        cart_head = QFrame()
        cart_head.setFixedHeight(60)
        cart_head.setStyleSheet("background: #f8f9fa; border-top-left-radius: 20px; border-top-right-radius: 20px; border-bottom: 2px solid #eee;")
        ch_layout = QHBoxLayout(cart_head)
        ch_layout.addWidget(QLabel("🛒 İşlem Sepeti"))
        btn_clear = QPushButton("Sepeti Boşalt")
        btn_clear.setStyleSheet("color: #e74c3c; border: none; font-weight: bold;")
        btn_clear.clicked.connect(self.clear_cart)
        ch_layout.addStretch()
        ch_layout.addWidget(btn_clear)
        right_layout.addWidget(cart_head)

        # Cart Content Stack (Table or Empty)
        self.cart_content_stack = QStackedWidget()
        
        self.cart_table = QTreeWidget()
        self.cart_table.setColumnCount(5)
        self.cart_table.setHeaderLabels(["Tarih", "Hizmet", "Adet", "Açıklama", "Tutar"])
        
        # Sütun Ayarları
        header = self.cart_table.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # Tarih
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch) # Hizmet
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # Adet
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch) # Açıklama
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents) # Tutar
        
        self.cart_table.setAlternatingRowColors(True)
        self.cart_table.setRootIsDecorated(True)
        self.cart_table.setItemsExpandable(True)
        self.cart_table.setStyleSheet("""
            QTreeWidget {
                background-color: white;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
            }
            QTreeWidget::item { padding: 8px; height: 35px; color: #2c3e50; }
            QTreeWidget::item:hover { background-color: #dbeafe; color: #1e3a8a; }
            QTreeWidget::item:selected { background-color: #3b82f6; color: white; }
            QHeaderView::section {
                background-color: #f8fafc;
                padding: 10px;
                border: none;
                font-weight: bold;
                color: #64748b;
            }
        """)
        
        # Context Menu
        self.cart_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.cart_table.customContextMenuRequested.connect(self.show_cart_context_menu)
        self.cart_content_stack.addWidget(self.cart_table)

        from src.ui.widgets.empty_state import EmptyState
        self.cart_empty_state = EmptyState("🛒", "Henüz bir şey eklemediniz", "Soldaki panelden hizmet seçebilirsiniz.")
        self.cart_content_stack.addWidget(self.cart_empty_state)
        self.cart_content_stack.setCurrentWidget(self.cart_empty_state)
        
        right_layout.addWidget(self.cart_content_stack)

        # Bottom Finish Area
        finish_bar = QFrame()
        finish_bar.setFixedHeight(80)
        finish_bar.setStyleSheet("background: #f8f9fa; border-bottom-left-radius: 20px; border-bottom-right-radius: 20px; border-top: 1px solid #eee;")
        fb_layout = QHBoxLayout(finish_bar)
        fb_layout.setContentsMargins(20, 0, 20, 0)
        
        symbol = CurrencyHelper.get_symbol()
        self.lbl_subtotal = QLabel(
            f"Ara Toplam: {CurrencyHelper.format_try_for_display(0, db=self.db, include_try_reference=False)}"
        )
        self.lbl_subtotal.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        fb_layout.addWidget(self.lbl_subtotal)
        fb_layout.addStretch()
        
        btn_summary = QPushButton("Özet ve Onay →")
        btn_summary.setFixedSize(200, 50)
        btn_summary.setStyleSheet("""
            QPushButton {
                background: #3498db;
                color: white;
                border-radius: 10px;
                font-weight: bold;
            }
            QPushButton:hover { background: #2980b9; }
        """)
        btn_summary.clicked.connect(lambda: self.switch_tab(2))
        fb_layout.addWidget(btn_summary)
        right_layout.addWidget(finish_bar)

        layout.addWidget(left_panel, 2)
        layout.addWidget(right_panel, 3)

        return page
        
    def update_calc_total(self):
        """Update the total label based on qty * price."""
        try:
            qty = self.inp_qty.value()
            price = self.inp_price.value()
            total = qty * price
            currency_code = self._parse_currency_code(self.cmb_currency.currentText()) if hasattr(self, 'cmb_currency') else 'TRY'
            self.lbl_line_total.setText(
                f"Satır Toplamı: {CurrencyHelper.format_amount(total, db=self.db, currency_code=currency_code)}"
            )
        except (AttributeError, TypeError, ValueError) as e:
            logger.debug(f"TransactionPage update_calc_total skipped: {e}")

    def create_summary_page(self):
        page = QFrame()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 20, 30, 30)
        layout.setSpacing(25)

        # Title
        # title = QLabel("İşlem Özeti")
        # title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        # title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # layout.addWidget(title)

        # Content Splitter (Info vs Total)
        content = QHBoxLayout()
        content.setSpacing(30)

        # Left Column: Review & Options
        left = QVBoxLayout()
        left.setSpacing(20)

        # Info Card
        info_card = QFrame()
        info_card.setObjectName("InfoCard")
        info_card.setStyleSheet("""
            #InfoCard { 
                background: white; 
                border-radius: 20px; 
                border: 1px solid #e0e0e0;
            }
        """)
        shadow1 = QGraphicsDropShadowEffect()
        shadow1.setBlurRadius(20)
        shadow1.setColor(QColor(0,0,0,10))
        shadow1.setOffset(0, 4)
        info_card.setGraphicsEffect(shadow1)

        il = QVBoxLayout(info_card)
        il.setContentsMargins(25, 25, 25, 25)
        il.setSpacing(15)
        
        lbl_head_1 = QLabel("MÜŞTERİ VE HİZMET DETAYLARI")
        lbl_head_1.setStyleSheet("color: #95a5a6; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        il.addWidget(lbl_head_1)

        self.lbl_summary_customer = QLabel("Müşteri: Seçilmedi")
        self.lbl_summary_customer.setStyleSheet("font-size: 16px; color: #2c3e50;")
        il.addWidget(self.lbl_summary_customer)
        
        self.lbl_summary_items = QLabel("Hizmet Sayısı: 0")
        self.lbl_summary_items.setStyleSheet("font-size: 14px; color: #7f8c8d;")
        il.addWidget(self.lbl_summary_items)
        
        il.addSpacing(10)
        line = QFrame(frameShape=QFrame.Shape.HLine)
        line.setStyleSheet("color: #f1f2f6;")
        il.addWidget(line)
        il.addSpacing(10)

        # Settings Section
        lbl_head_2 = QLabel("FİNANSAL AYARLAR")
        lbl_head_2.setStyleSheet("color: #95a5a6; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        il.addWidget(lbl_head_2)
        
        # Discount Input
        row_disc = QHBoxLayout()
        lbl_disc = QLabel("İskonto Tutarı:")
        lbl_disc.setStyleSheet("font-size: 14px; font-weight: 500;")
        self.inp_discount = QDoubleSpinBox()
        self.inp_discount.setRange(0, 99999)
        self.inp_discount.setSuffix(f" {CurrencyHelper.get_symbol(self.db)}")
        self.inp_discount.valueChanged.connect(self.update_totals)
        self.inp_discount.setFixedHeight(40)
        self.inp_discount.setStyleSheet("""
            QDoubleSpinBox {
                border: 2px solid #ecf0f1; 
                border-radius: 8px; 
                padding: 5px; 
                font-size: 14px; font-weight: bold;
            }
            QDoubleSpinBox:focus { border-color: #3498db; }
        """)
        row_disc.addWidget(lbl_disc)
        row_disc.addWidget(self.inp_discount)
        il.addLayout(row_disc)

        # Transaction Date Input (Backdating)
        row_date = QHBoxLayout()
        lbl_date = QLabel("İşlem Tarihi:")
        lbl_date.setStyleSheet("font-size: 14px; font-weight: 500;")
        self.date_edit_transaction = QDateEdit(QDate.currentDate())
        self.date_edit_transaction.setCalendarPopup(True)
        self.date_edit_transaction.setDisplayFormat("dd.MM.yyyy")
        self.date_edit_transaction.setFixedHeight(40)
        self.date_edit_transaction.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        row_date.addWidget(lbl_date)
        row_date.addWidget(self.date_edit_transaction)
        il.addLayout(row_date)
        il.addLayout(row_disc)

        # VAT Input
        row_vat = QHBoxLayout()
        lbl_vat = QLabel("KDV Oranı:")
        lbl_vat.setStyleSheet("font-size: 14px; font-weight: 500;")
        self.cmb_vat = QComboBox()
        self.cmb_vat.addItems(["%0", "%1", "%10", "%20"])
        self.cmb_vat.setCurrentIndex(3)
        self.cmb_vat.currentTextChanged.connect(self.update_totals)
        self.cmb_vat.setFixedHeight(40)
        self.cmb_vat.setStyleSheet(theme_qss(DesignTokens.get_combobox_qss()))
        row_vat.addWidget(lbl_vat)
        row_vat.addWidget(self.cmb_vat)
        il.addLayout(row_vat)

        # Currency Selection
        row_cur = QHBoxLayout()
        lbl_cur = QLabel("İşlem Para Birimi:")
        lbl_cur.setStyleSheet("font-size: 14px; font-weight: 500;")
        self.cmb_currency = QComboBox()
        self.cmb_currency.addItems(["₺ TRY", "$ USD", "€ EUR"])
        self.cmb_currency.currentTextChanged.connect(self.on_currency_changed)
        self.cmb_currency.setFixedHeight(40)
        self.cmb_currency.setStyleSheet(theme_qss(DesignTokens.get_combobox_qss()))
        row_cur.addWidget(lbl_cur)
        row_cur.addWidget(self.cmb_currency)
        il.addLayout(row_cur)
        
        # Exchange Rate Display
        self.lbl_exchange_rate = QLabel("Güncel Kur: Yükleniyor...")
        self.lbl_exchange_rate.setStyleSheet("""
            font-size: 12px; 
            color: #16a34a; 
            font-weight: 600;
            padding: 8px;
            background: #f0fdf4;
            border-radius: 6px;
            border-left: 3px solid #16a34a;
        """)
        il.addWidget(self.lbl_exchange_rate)

        il.addStretch()
        left.addWidget(info_card)

        # Right Column: Big Total Payment Card
        right = QVBoxLayout()
        
        total_card = QFrame()
        total_card.setObjectName("TotalCard")
        # Gradient dark sleek background
        total_card.setStyleSheet("""
            #TotalCard { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1e293b, stop:1 #334155); 
                border-radius: 25px; 
            }
        """)
        shadow2 = QGraphicsDropShadowEffect()
        shadow2.setBlurRadius(30)
        shadow2.setColor(QColor(0,0,0,30))
        shadow2.setOffset(0, 8)
        total_card.setGraphicsEffect(shadow2)

        tl = QVBoxLayout(total_card)
        tl.setContentsMargins(40, 50, 40, 50)
        tl.setSpacing(15)

        lbl_total_title = QLabel("TOPLAM ÖDENECEK TUTAR")
        lbl_total_title.setStyleSheet("color: rgba(255,255,255,0.6); font-size: 12px; font-weight: 700; letter-spacing: 1.5px;")
        tl.addWidget(lbl_total_title)

        self.lbl_total = QLabel(CurrencyHelper.format_try_for_display(0, db=self.db, include_try_reference=False))
        self.lbl_total.setFont(QFont("Segoe UI", 56, QFont.Weight.Bold))
        self.lbl_total.setStyleSheet("color: #4ade80;") # Bright green text
        self.lbl_total.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tl.addWidget(self.lbl_total)
        
        tl.addSpacing(20)
        tl.addWidget(QFrame(frameShape=QFrame.Shape.HLine, styleSheet="color: rgba(255,255,255,0.2);"))
        tl.addSpacing(20)

        # Final Actions
        # Final Actions
        self.btn_save = QPushButton("⏳ Servis Kaydet (Borç)")
        self.btn_save.setFixedHeight(50)
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f39c12, stop:1 #d35400);
                color: white;
                border-radius: 12px;
                font-weight: 700;
                font-size: 15px;
                border: none;
            }
            QPushButton:hover { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #d35400, stop:1 #e67e22);
            }
        """)
        self.btn_save.clicked.connect(self.save_transaction)
        tl.addWidget(self.btn_save)

        self.btn_pay = QPushButton("✅ Ödeme Al (Nakit/Kart)")
        self.btn_pay.setFixedHeight(50)
        self.btn_pay.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pay.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #059669);
                color: white;
                border-radius: 12px;
                font-weight: 700;
                font-size: 15px;
                border: none;
            }
            QPushButton:hover { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #047857);
            }
        """)
        self.btn_pay.clicked.connect(self.save_and_pay)
        tl.addWidget(self.btn_pay)

        self.btn_proforma = QPushButton("📄 Teklif (Proforma) Oluştur")
        self.btn_proforma.setFixedHeight(50)
        self.btn_proforma.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_proforma.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.08); 
                border: 1px solid rgba(255,255,255,0.2); 
                color: #e2e8f0; 
                border-radius: 12px;
                font-weight: 600;
            }
            QPushButton:hover { background: rgba(255,255,255,0.15); }
        """)
        self.btn_proforma.clicked.connect(self.create_proforma)
        tl.addWidget(self.btn_proforma)
        
        tl.addStretch()

        right.addWidget(total_card)
        
        content.addLayout(left, 4) # 40%
        content.addLayout(right, 6) # 60%
        layout.addLayout(content)

        return page


    def open_multi_select(self):
        """Toplu hizmet seçim penceresini aç"""
        if not self.services_data:
            show_warning(self, "Henüz hizmet/ürün verisi yüklenmedi.")
            return
        dlg = MultiSelectServiceDialog(self, self.services_data)
        if dlg.exec():
            selected = dlg.get_selected()  # List of (name, price, description)
            for s_name, price, desc in selected:
                info = self.services_data.get(s_name, {})
                self.cart_items.append({
                    'service': s_name,
                    'qty': 1,
                    'price': price,
                    'type': info.get('type', 'service'),
                    'brand': info.get('brand', ''),
                    'description': f"Stoktan ürün: {s_name}" if info.get('type') == 'part' else s_name
                })
            self.refresh_cart()
            if selected:
                show_success(self, f"{len(selected)} kalem sepete eklendi.")
