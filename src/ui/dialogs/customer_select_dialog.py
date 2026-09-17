# -*- coding: utf-8 -*-


from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QListWidget, QListWidgetItem, QFrame,
                             QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView, QMenu)
from src.ui.dialogs.simple_confirm import SimpleConfirmDialog
from src.utils.toast_notification import show_success, show_error, show_warning, show_info
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QIcon, QAction
from src.ui.dialogs.customer_360_dialog import Customer360Dialog
from src.ui.widgets.premium_dialog import PremiumDialog
from src.utils.currency_helper import CurrencyHelper
from src.utils.context_menu_settings import is_context_menu_enabled

class CustomerSelectDialog(PremiumDialog):
    def __init__(self, db, parent=None):
        super().__init__("Müşteri Seçim Paneli", parent)
        self.db = db
        self.selected_customer = None
        self.resize(1000, 700)
        self.setup_ui()
        
    def setup_ui(self):
        layout = self.body_layout
        
        # Search area
        search_container = QFrame()
        search_container.setStyleSheet("""
            QFrame {
                background-color: #F1F5F9;
                border-radius: 12px;
                border: 1px solid #E2E8F0;
            }
        """)
        sl = QHBoxLayout(search_container)
        sl.setContentsMargins(15, 0, 15, 0)
        
        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("İsim, telefon veya e-posta ile hızlı ara...")
        self.inp_search.setFixedHeight(45)
        self.inp_search.setStyleSheet("border: none; background: transparent; font-size: 14px; font-weight: 500;")
        self.inp_search.textChanged.connect(self.search)
        
        sl.addWidget(QLabel("🔍"))
        sl.addWidget(self.inp_search)
        layout.addWidget(search_container)
        
        # Table
        self.list_widget = QTableWidget()
        self.list_widget.setColumnCount(4)
        self.list_widget.setHorizontalHeaderLabels(["MÜŞTERİ ADI", "TELEFON", "MÜŞTERİ TİPİ", "BAKİYE"])
        self.list_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.list_widget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list_widget.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.list_widget.doubleClicked.connect(self.select_and_close)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.open_context_menu)
        self.list_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.list_widget.setMouseTracking(True)
        self.list_widget.setShowGrid(False)
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setStyleSheet("""
            QTableWidget {
                border: 1px solid #E2E8F0;
                border-radius: 12px;
                background-color: white;
                alternate-background-color: #F8FAFC;
                font-size: 13px;
                selection-background-color: #DBEAFE;
                selection-color: #1E40AF;
                outline: 0;
            }
            QTableWidget::item { padding: 12px; border-bottom: 1px solid #F1F5F9; }
            QTableWidget::item:hover { background-color: #EFF6FF; color: #1D4ED8; }
            QTableWidget::item:selected { background-color: #DBEAFE; color: #1E40AF; font-weight: bold; border: none; }
            QHeaderView::section {
                background-color: #F8FAFC; color: #64748B; font-weight: 800; font-size: 11px; border: none; padding: 12px;
            }
        """)
        layout.addWidget(self.list_widget)
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        # Left side buttons
        btn_add = QPushButton("+ Yeni Müşteri")
        btn_add.setFixedSize(160, 45)
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setStyleSheet("""
            QPushButton { background: #F59E0B; color: white; border-radius: 10px; font-weight: 700; border: none; }
            QPushButton:hover { background: #D97706; }
        """)
        btn_add.clicked.connect(self.add_customer)
        btn_layout.addWidget(btn_add)
        
        btn_history = QPushButton("📋 İşlem Geçmişi")
        btn_history.setFixedSize(160, 45)
        btn_history.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_history.setStyleSheet("""
            QPushButton { background: #F1F5F9; color: #475569; border-radius: 10px; font-weight: 700; border: 1px solid #E2E8F0; }
            QPushButton:hover { background: #E2E8F0; }
        """)
        btn_history.clicked.connect(self.show_history)
        btn_layout.addWidget(btn_history)
        
        btn_layout.addStretch()
        
        # Right side (Select)
        btn_select = QPushButton("Müşteriyi Seç ve İlerle")
        btn_select.setFixedSize(220, 45)
        btn_select.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_select.setStyleSheet("""
            QPushButton { background: #F59E0B; color: white; border-radius: 10px; font-weight: 800; border: none; }
            QPushButton:hover { background: #D97706; }
        """)
        btn_select.clicked.connect(self.select_and_close)
        btn_layout.addWidget(btn_select)
        
        layout.addLayout(btn_layout)
        self.load_data()

    def open_context_menu(self, position):
        if not is_context_menu_enabled(self.db, page_id=21):
            return
        row = self.list_widget.rowAt(position.y())
        if row >= 0:
            self.list_widget.selectRow(row)
            menu = QMenu()
            menu.setStyleSheet("padding: 5px; background: white; border-radius: 8px; border: 1px solid #E2E8F0;")
            
            action_select = QAction("✅ Bu Müşteriyi Seç", self)
            action_select.triggered.connect(self.select_and_close)
            menu.addAction(action_select)
            
            action_history = QAction("📋 İşlem Geçmişi", self)
            action_history.triggered.connect(self.show_history)
            menu.addAction(action_history)
            
            menu.addSeparator()
            
            action_delete = QAction("❌ Müşteri Kaydını Sil", self)
            action_delete.triggered.connect(self.delete_customer)
            menu.addAction(action_delete)
            
            menu.exec(self.list_widget.viewport().mapToGlobal(position))
        
    def load_data(self, customers=None):
        if customers is None:
            customers = self.db.get_customers()
        
        self.list_widget.setRowCount(0)
        for i, c in enumerate(customers):
            # c: id, name, phone, email, type...
            self.list_widget.insertRow(i)
            self.list_widget.setItem(i, 0, QTableWidgetItem(str(c[1])))
            self.list_widget.setItem(i, 1, QTableWidgetItem(str(c[2])))
            self.list_widget.setItem(i, 2, QTableWidgetItem(str(c[4])))
            
            # Balance
            balance = self.db.get_customer_balance(c[0])
            b_item = QTableWidgetItem(
                CurrencyHelper.format_try_for_display(balance, db=self.db, include_try_reference=False)
            )
            if balance < 0:
                b_item.setForeground(QColor("#DC2626"))
            self.list_widget.setItem(i, 3, b_item)
            
            self.list_widget.item(i, 0).setData(Qt.ItemDataRole.UserRole, c)
            
    def search(self):
        query = self.inp_search.text()
        if not query:
            self.load_data()
        else:
            results = self.db.search_customers(query)
            self.load_data(results)
            
    def select_and_close(self):
        row = self.list_widget.currentRow()
        if row >= 0:
            self.selected_customer = self.list_widget.item(row, 0).data(Qt.ItemDataRole.UserRole)
            self.accept()

    def show_history(self):
        row = self.list_widget.currentRow()
        if row >= 0:
            customer = self.list_widget.item(row, 0).data(Qt.ItemDataRole.UserRole)
            history = self.db.get_customer_history(customer[1])
            dialog = Customer360Dialog(self.db, int(customer[0]), customer[1], self)
            dialog.exec()
        else:
            show_warning(self, "Lütfen bir müşteri seçin!")

    def delete_customer(self):
        row = self.list_widget.currentRow()
        if row >= 0:
            customer = self.list_widget.item(row, 0).data(Qt.ItemDataRole.UserRole)
            confirm = SimpleConfirmDialog("Kayıt Silme Onayı", f"{customer[1]} adlı müşteriyi ve tüm kayıtlarını silmek istediğinize emin misiniz")
            if confirm.exec() == QDialog.DialogCode.Accepted:
                if self.db.delete_customer(customer[0]):
                    show_success(self, "Müşteri kaydı silindi.")
                    self.load_data()
                else:
                    show_error(self, "Silme işlemi başarısız!")
        else:
            show_warning(self, "Lütfen silinecek müşteriyi seçin!")

    def add_customer(self):
        sector_manager = getattr(self.parent(), "sector_manager", None)
        try:
            is_automotive = (
                sector_manager
                and sector_manager.get_current_plugin().sector_id == "otomotiv"
            )
        except Exception:
            is_automotive = False
        if is_automotive:
            from src.ui.dialogs.automotive_customer_dialog import (
                AutomotiveCustomerDialog as dialog_cls,
            )
        else:
            from src.ui.dialogs.technical_service_customer_dialog import (
                TechnicalServiceCustomerDialog as dialog_cls,
            )
        dialog = dialog_cls(self.db, self, sector_manager=sector_manager)
        if dialog.exec():
            self.load_data()
