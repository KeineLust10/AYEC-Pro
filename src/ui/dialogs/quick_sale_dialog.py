# -*- coding: utf-8 -*-


from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit, 
                             QComboBox, QFrame, QGridLayout, QSpinBox, QWidget, QAbstractItemView)

from src.ui.dialogs.simple_confirm import SimpleConfirmDialog
from src.utils.toast_notification import show_success, show_error, show_warning, show_info
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor
from datetime import datetime
from src.utils.logger import logger
from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.design_system import DesignTokens


class QuickSaleDialog(ModernDialog):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    """
    Hızlı Satış (Sepet) Sistemi
    Barkod okutarak veya listeden seçerek hızlı ürün satışı yapmayı sağlar.
    """
    def __init__(self, db, parent=None):
        super().__init__(title="Hızlı Satış Terminali", parent=parent, width=1000, height=700)
        self.db = db
        self.cart = [] # List of dicts: {'id', 'name', 'price', 'qty', 'stock'}
        self.set_footer_visible(False)
        self.resize(1000, 700)
        self.setStyleSheet("""
            QDialog { 
                background-color: #F8FAFC; 
                border-radius: 15px;
                border: 2px solid #64748B;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 2px solid #F59E0B;
                background-color: #FFFBEB;
            }
            QLineEdit:hover, QComboBox:hover {
                border-color: #FCD34D;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                color: #333;
                selection-background-color: #F59E0B;
                selection-color: white;
                outline: none;
            }
        """)
        self.setup_ui()
        
        self._wire_ui_signals()
    def setup_ui(self):
        main_layout = self.content_layout
        
        # Left Panel: Product List & Search
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Search Box
        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("🔍 Ürün Ara veya Barkod Okut")
        self.inp_search.setClearButtonEnabled(True)
        self.inp_search.setFixedHeight(45)
        self.inp_search.setFont(QFont("Segoe UI", 11))
        self.inp_search.textChanged.connect(self.filter_products)
        self.inp_search.returnPressed.connect(self.add_by_barcode)
        
        left_layout.addWidget(QLabel("<b>Ürün Listesi</b>"))
        left_layout.addWidget(self.inp_search)
        
        # Product Table
        self.table_products = QTableWidget()
        self.table_products.setColumnCount(4)
        self.table_products.setHorizontalHeaderLabels(["ID", "Ürün Adı", "Stok", "Fiyat"])
        self.table_products.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_products.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_products.cellDoubleClicked.connect(self.add_selected_to_cart)
        left_layout.addWidget(self.table_products)
        
        self.lbl_product_count = QLabel("0 ürün listelendi")
        left_layout.addWidget(self.lbl_product_count)
        
        # Right Panel: Cart & Checkout
        right_panel = QFrame()
        right_panel.setStyleSheet("background-color: #f8f9fa; border-left: 1px solid #ddd;")
        right_layout = QVBoxLayout(right_panel)
        
        right_layout.addWidget(QLabel("<b>🛒 Sepet</b>"))
        
        # Cart Table
        self.table_cart = QTableWidget()
        self.table_cart.setColumnCount(5)
        self.table_cart.setHorizontalHeaderLabels(["Ürün", "Birim", "Adet", "Tutar", "Sil"])
        self.table_cart.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table_cart.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_cart.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self.table_cart.horizontalHeader() # Assuming 'header' was meant to be defined here
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_cart.setStyleSheet("background-color: white;")
        right_layout.addWidget(self.table_cart)
        
        # Totals Section
        totals_frame = QFrame()
        totals_frame.setStyleSheet("background-color: white; border-radius: 8px; border: 1px solid #eee;")
        t_layout = QGridLayout(totals_frame)
        
        t_layout.addWidget(QLabel("Ara Toplam:"), 0, 0)
        self.lbl_subtotal = QLabel("0.00 TL")
        self.lbl_subtotal.setAlignment(Qt.AlignmentFlag.AlignRight)
        t_layout.addWidget(self.lbl_subtotal, 0, 1)
        
        # Discount Input
        t_layout.addWidget(QLabel("İskonto (TL):"), 1, 0)
        self.inp_discount = QSpinBox()
        self.inp_discount.setRange(0, 10000)
        self.inp_discount.setSuffix(" TL")
        DesignTokens.apply_spinbox_styles(self.inp_discount)
        self.inp_discount.valueChanged.connect(self.calculate_total)
        t_layout.addWidget(self.inp_discount, 1, 1)
        
        # Grand Total
        lbl_total_txt = QLabel("GENEL TOPLAM")
        lbl_total_txt.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        t_layout.addWidget(lbl_total_txt, 2, 0)
        
        self.lbl_total = QLabel("0.00 TL")
        self.lbl_total.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.lbl_total.setStyleSheet("color: #27ae60;")
        self.lbl_total.setAlignment(Qt.AlignmentFlag.AlignRight)
        t_layout.addWidget(self.lbl_total, 2, 1)
        
        right_layout.addWidget(totals_frame)
        
        # Payment Method & Bank Selection (Row)
        pay_bank_layout = QHBoxLayout()
        
        v_pay = QVBoxLayout()
        v_pay.addWidget(QLabel("Ödeme Yöntemi:"))
        self.cmb_payment = QComboBox()
        self.cmb_payment.addItems(["Nakit", "Kredi Kartı", "Havale/EFT"])
        self.cmb_payment.setFixedHeight(40)
        v_pay.addWidget(self.cmb_payment)
        
        v_bank = QVBoxLayout()
        v_bank.addWidget(QLabel("Kasa/Banka Seçimi:"))
        self.cmb_bank = QComboBox()
        self.cmb_bank.setFixedHeight(40)
        self.cmb_bank.addItem("Seçiniz...", -1)
        try:
            if hasattr(self.db, 'get_bank_accounts'):
                for b in self.db.get_bank_accounts():
                    name = b.get('bank_name') if isinstance(b, dict) else b[1]
                    bid = b.get('id') if isinstance(b, dict) else b[0]
                    self.cmb_bank.addItem(name, bid)
        except Exception:
            pass
        v_bank.addWidget(self.cmb_bank)
        
        pay_bank_layout.addLayout(v_pay)
        pay_bank_layout.addLayout(v_bank)
        right_layout.addLayout(pay_bank_layout)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("İPTAL")
        btn_cancel.setFixedHeight(50)
        btn_cancel.setStyleSheet("background-color: #e74c3c; color: white;")
        btn_cancel.clicked.connect(self.reject)
        
        btn_checkout = QPushButton("✅ SATIŞI TAMAMLA")
        btn_checkout.setFixedHeight(50)
        btn_checkout.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        btn_checkout.setStyleSheet("background-color: #F59E0B; color: white; border-radius: 8px;")
        btn_checkout.clicked.connect(self.checkout)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_checkout)
        
        right_layout.addLayout(btn_layout)
        
        # Layouts Weight
        main_layout.addWidget(left_panel, 60)
        main_layout.addWidget(right_panel, 40)
        
        self.load_products()

    def _wire_ui_signals(self):
        self.cmb_payment.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_bank.currentIndexChanged.connect(self._on_ui_widget_changed)

    def load_products(self):
        # Cache detailed parts
        # Parts: id, name, category, stock, price, ...
        try:
            self.products = self.db.get_all_parts() 
            self.filter_products()
        except Exception as e:
            logger.error(f"Quick sale product load error: {e}")
            self.products = []
            
    def filter_products(self):
        query = self.inp_search.text().lower()
        
        filtered = []
        for p in self.products:
            # p[1] name, p[0] id
            if query in str(p[1]).lower() or query in str(p[0]).lower():
                filtered.append(p)
                
        self.table_products.setRowCount(0)
        self.lbl_product_count.setText(f"{len(filtered)} ürün listelendi")
        
        for i, p in enumerate(filtered):
            self.table_products.insertRow(i)
            # 0: ID, 1: Name, 2: Stock, 3: Price
            self.table_products.setItem(i, 0, QTableWidgetItem(str(p[0])))
            self.table_products.setItem(i, 1, QTableWidgetItem(str(p[1])))
            
            stk_item = QTableWidgetItem(str(p[3]))
            if p[3] <= 0: stk_item.setBackground(QColor("#ffcdd2"))
            self.table_products.setItem(i, 2, stk_item)
            
            self.table_products.setItem(i, 3, QTableWidgetItem(f"{p[4]:.2f}"))


    
    def add_selected_to_cart(self, row, col):
        p_id = int(self.table_products.item(row, 0).text())
        p_name = self.table_products.item(row, 1).text()
        p_stock = int(self.table_products.item(row, 2).text())
        p_price = float(self.table_products.item(row, 3).text().replace(" TL", ""))
        
        if p_stock <= 0:
            show_warning(self, "Bu üründen stokta kalmamış!")
            return
            
        self.add_to_cart(p_id, p_name, p_price, p_stock)
        
    def add_by_barcode(self):
        # Exact match logic or first hit
        # Currently we don't have barcode col reliably on table, let's use search result if unique
        txt = self.inp_search.text().strip()
        if not txt: return
        
        # Logic: find exact match in self.products ID or Name (or barcode if added)
        found = None
        for p in self.products:
            # If we had barcode column, check it. Assume p[6] is barcode if using latest schema or p[7]
            # Since p length varies based on schema, safest is by name or ID
            if str(p[0]) == txt:
                found = p
                break
        
        if found:
            # Add it
            p_id = found[0]
            p_name = found[1]
            p_stock = found[3]
            p_price = found[4]
            if p_stock > 0:
                self.add_to_cart(p_id, p_name, p_price, p_stock)
                self.inp_search.clear()
            else:
                show_warning(self, "Stok yok.")
                
    def add_to_cart(self, p_id, name, price, max_stock):
        # Check if already in cart
        for item in self.cart:
            if item['id'] == p_id:
                if item['qty'] < max_stock:
                    item['qty'] += 1
                else:
                    show_warning(self, "Stoktaki maksimum adede ulaşıldı.")
                self.refresh_cart()
                return

        # Add new
        self.cart.append({
            'id': p_id,
            'name': name,
            'price': price,
            'qty': 1,
            'stock': max_stock
        })
        self.refresh_cart()

    def refresh_cart(self):
        self.table_cart.setRowCount(0)
        total = 0.0
        
        for i, item in enumerate(self.cart):
            self.table_cart.insertRow(i)
            
            row_total = item['price'] * item['qty']
            total += row_total
            
            self.table_cart.setItem(i, 0, QTableWidgetItem(item['name']))
            self.table_cart.setItem(i, 1, QTableWidgetItem(f"{item['price']:.2f}"))
            
            # Qty (Editable would be nice, but simple label for now)
            self.table_cart.setItem(i, 2, QTableWidgetItem(str(item['qty'])))
            
            self.table_cart.setItem(i, 3, QTableWidgetItem(f"{row_total:.2f}"))
            
            # Remove Btn
            btn_del = QPushButton("✖")
            btn_del.setFixedWidth(30)
            btn_del.clicked.connect(lambda ch, idx=i: self.remove_item(idx))
            self.table_cart.setCellWidget(i, 4, btn_del)
            
        self.subtotal_val = total
        self.calculate_total()
        
    def remove_item(self, idx):
        if 0 <= idx < len(self.cart):
            self.cart.pop(idx)
            self.refresh_cart()

    def calculate_total(self):
        discount = self.inp_discount.value()
        total = max(0, self.subtotal_val - discount)
        
        self.lbl_subtotal.setText(f"{self.subtotal_val:.2f} TL")
        self.lbl_total.setText(f"{total:.2f} TL")
        
    def checkout(self):
        if not self.cart:
            show_warning(self, "Lütfen ürün ekleyin.")
            return

        dlg = SimpleConfirmDialog(self, "Satış Onayı", f"Toplam {self.lbl_total.text()} tutarında satışı onaylıyor musunuz")
        if not dlg.exec():
            return

        try:
            total_amount = float(self.lbl_total.text().split(" ")[0])
            payment_method = self.cmb_payment.currentText()
            desc = f"Hızlı Satış ({payment_method})"
            detail_lines = []
            for index, item in enumerate(self.cart, start=1):
                line_total = float(item["price"] or 0) * int(item["qty"] or 1)
                detail_lines.append(f"{index}. {item['name']} (x{item['qty']}) - {line_total:,.2f} TL")
            sale_description = f"{desc} - {len(self.cart)} kalem ürün"
            if detail_lines:
                sale_description += "\n" + "\n".join(detail_lines)

            if self.cart:
                update_data = [(item['qty'], item['id']) for item in self.cart]
                self.db.cursor.executemany("UPDATE parts SET stock = stock - ? WHERE id=?", update_data)
                created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                insert_data = [("DIRECT_SALE", f"{item['qty']}x {item['name']}", item['price'] * item['qty'], created_at) for item in self.cart]
                self.db.cursor.executemany("INSERT INTO used_parts (tracking_no, part_name, price, created_at) VALUES (?, ?, ?, ?)", insert_data)

            cat = "Satis"
            bank_id = self.cmb_bank.currentData()
            if bank_id == -1:
                bank_id = None

            try:
                self.db.add_transaction_extended(
                    type="Gelir",
                    category=cat,
                    amount=total_amount,
                    description=sale_description,
                    date=datetime.now().strftime("%Y-%m-%d"),
                    payment_method=payment_method,
                    bank_account_id=bank_id,
                )
            except Exception:
                self.db.add_transaction("Gelir", cat, total_amount, sale_description)

            try:
                total_material_cost = 0.0
                cost_parts = []
                if self.cart:
                    try:
                        item_ids = [str(item['id']) for item in self.cart]
                        placeholders = ','.join('?' * len(item_ids))
                        self.db.cursor.execute(
                            "SELECT id, purchase_price FROM parts WHERE id IN ({placeholders})".format(
                                placeholders=placeholders
                            ),
                            item_ids,
                        )
                        prices = {row[0]: float(row[1] or 0) for row in self.db.cursor.fetchall()}
                        for item in self.cart:
                            pp = prices.get(item['id'], 0.0)
                            if pp > 0:
                                line_cost = pp * item['qty']
                                total_material_cost += line_cost
                                cost_parts.append(f"{item['name']}x{item['qty']}")
                    except Exception:
                        pass

                if total_material_cost > 0:
                    cost_desc = f"Satilan Malin Maliyeti - Hızlı Satış ({len(self.cart)} kalem)"
                    if cost_parts:
                        cost_desc += f" [{', '.join(cost_parts)}]"
                    self.db.add_transaction(
                        t_type="Gider",
                        category="Satilan Malin Maliyeti",
                        amount=total_material_cost,
                        description=cost_desc,
                    )
            except Exception:
                pass

            self.db.conn.commit()
            show_info(self, "Satis islemi tamamlandi.")
            self.accept()
        except Exception as e:
            show_error(self, f"Satis hatasi: {e}")
