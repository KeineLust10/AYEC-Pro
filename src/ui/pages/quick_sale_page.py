# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, 
                             QLineEdit, QComboBox, QFrame, QGridLayout, QSpinBox,
                             QMessageBox, QGraphicsDropShadowEffect, QAbstractItemView,
                             QScrollArea)
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import show_success, show_error, show_warning, show_info
from src.utils.logger import logger
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QFont, QColor, QIcon, QAction, QKeySequence, QShortcut

class StartPOSWidget(QWidget):
    """Modern Başlangıç/POS Widget"""
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(QLabel("POS Yükleniyor..."))

class ProductCard(QFrame):
    def __init__(self, p_id, name, price, stock, category, currency, parent_page):
        super().__init__()
        self.p_id = p_id
        self.name = name
        self.price = price
        self.stock = stock
        self.category = category
        self.currency = currency
        self.parent_page = parent_page
        
        self.setFixedSize(160, 180)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(theme_qss("""
            QFrame {
                background-color: @surface;
                border: 1px solid @border;
                border-radius: 15px;
            }
            QFrame:hover {
                border: 2px solid @accent;
                background-color: @surface_alt;
            }
        """))
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 15, 10, 15)
        layout.setSpacing(5)
        
        # Icon/Image Placeholder
        icon_lbl = QLabel("📦")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(theme_qss("font-size: 40px; border: none; background: transparent;"))
        layout.addWidget(icon_lbl)
        
        # Name
        lbl_name = QLabel(name)
        lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_name.setWordWrap(True)
        lbl_name.setStyleSheet(theme_qss("font-weight: 700; color: @text; font-size: 13px; border: none; background: transparent;"))
        layout.addWidget(lbl_name)
        
        # Spacer
        layout.addStretch()
        
        # Price
        sym = "$" if currency=="USD" else "€" if currency=="EUR" else "₺"
        lbl_price = QLabel(f"{price:,.2f} {sym}")
        lbl_price.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_price.setStyleSheet(theme_qss("color: @success; font-weight: 800; font-size: 15px; border: none; background: transparent;"))
        layout.addWidget(lbl_price)
        
        # Stock Badge
        lbl_stock = QLabel(f"Stok: {stock}")
        lbl_stock.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if stock <= 0:
            lbl_stock.setStyleSheet(theme_qss("color: @danger; font-size: 10px; font-weight: bold; border:none; background:transparent;"))
            lbl_stock.setText("TÜKENDİ")
        else:
            lbl_stock.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px; border:none; background:transparent;"))
        layout.addWidget(lbl_stock)

    def mousePressEvent(self, event):
        if self.stock > 0:
            self.parent_page.add_to_cart_by_id(self.p_id)
        else:
            show_warning(self.parent_page.window(), "Ürün stokta yok!", 1000)

class QuickSalePage(QWidget):
    """
    Modern POS / Hızlı Satış Ekranı
    Sol: Kategori Filtreleri ve Ürün Izgarası
    Sağ: Sepet ve Ödeme
    """
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.cart_items = [] # (id, name, price, qty, total)
        self.all_products = [] 
        self.current_filtered_products = [] # Lazy loading source
        self.rendered_count = 0
        self.BATCH_SIZE = 20
        
        self.selected_category = "Tümü"
        self.selected_customer = None
        self.init_ui()
        self.load_products()
        
    def init_ui(self):
        # Ana Layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ================= SOL PANEL (ÜRÜNLER) =================
        left_panel = QWidget()
        left_panel.setStyleSheet(theme_qss("background-color: @surface_alt;"))
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(20, 20, 20, 20)
        left_layout.setSpacing(15)
        
        # 1. Üst Bar (Arama)
        search_frame = QFrame()
        search_frame.setFixedHeight(60)
        search_frame.setStyleSheet(theme_qss("""
            QFrame { background-color: @surface; border-radius: 12px; border: 1px solid @border; }
        """))
        sl = QHBoxLayout(search_frame)
        sl.setContentsMargins(15, 0, 15, 0)
        
        # Customer Select
        self.btn_customer = QPushButton("👤 Müşteri Seç")
        self.btn_customer.setFixedWidth(150)
        self.btn_customer.setStyleSheet(theme_qss("""
            QPushButton { 
                background-color: @surface_alt; 
                border: 1px solid @border; 
                border-radius: 8px; 
                padding: 8px;
                font-weight: bold;
            }
        """))
        self.btn_customer.clicked.connect(self.select_customer_dialog)
        sl.addWidget(self.btn_customer)
        
        icon_s = QLabel("🔍")
        icon_s.setStyleSheet(theme_qss("border:none; font-size: 18px; color: @text_muted;"))
        sl.addWidget(icon_s)
        
        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("Barkod okutun veya ürün adı arayın...")
        self.inp_search.setStyleSheet(theme_qss("border:none; font-size: 15px; font-weight: 500; background:transparent;"))
        self.inp_search.textChanged.connect(self.filter_products)
        self.inp_search.returnPressed.connect(self.process_barcode_enter)
        sl.addWidget(self.inp_search)
        
        btn_clear_s = QPushButton("✖")
        btn_clear_s.setFixedSize(30, 30)
        btn_clear_s.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear_s.setStyleSheet(theme_qss("border:none; color: @disabled_text; font-weight: bold; font-size: 14px;"))
        btn_clear_s.clicked.connect(self.inp_search.clear)
        sl.addWidget(btn_clear_s)
        
        left_layout.addWidget(search_frame)
        
        # 2. Kategoriler (Tab Bar benzeri)
        self.category_scroll = QScrollArea()
        self.category_scroll.setFixedHeight(50)
        self.category_scroll.setWidgetResizable(True)
        self.category_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.category_scroll.setStyleSheet(theme_qss("background: transparent;"))
        
        self.cat_container = QWidget()
        self.cat_layout = QHBoxLayout(self.cat_container)
        self.cat_layout.setContentsMargins(0, 0, 0, 0)
        self.cat_layout.setSpacing(10)
        self.cat_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self.category_scroll.setWidget(self.cat_container)
        left_layout.addWidget(self.category_scroll)
        
        # 3. Ürün Grid Alanı
        self.product_scroll = QScrollArea()
        self.product_scroll.setWidgetResizable(True)
        self.product_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.product_scroll.setStyleSheet(theme_qss("QScrollArea { border: none; background: transparent; }"))
        
        self.grid_container = QWidget()
        self.grid_container.setStyleSheet(theme_qss("background: transparent;"))
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(15)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        self.product_scroll.setWidget(self.grid_container)
        # Infinite Scroll Listener
        self.product_scroll.verticalScrollBar().valueChanged.connect(self.check_scroll_bottom)
        left_layout.addWidget(self.product_scroll)
        
        main_layout.addWidget(left_panel, 65) # %65 Genişlik
        
        # ================= SAĞ PANEL (SEPET) =================
        right_panel = QFrame()
        right_panel.setStyleSheet(theme_qss("background-color: @surface; border-left: 1px solid @border;"))
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        # Header
        r_header = QFrame()
        r_header.setFixedHeight(70)
        r_header.setStyleSheet(theme_qss("background-color: @surface_alt; border-bottom: 1px solid @border;"))
        rhl = QHBoxLayout(r_header)
        rhl.setContentsMargins(20, 0, 20, 0)
        lbl_cart_title = QLabel("🛒 Satış Sepeti")
        lbl_cart_title.setStyleSheet(theme_qss("font-size: 18px; font-weight: 800; color: @text; border:none;"))
        rhl.addWidget(lbl_cart_title)
        
        btn_trash = QPushButton("🗑️")
        btn_trash.setToolTip("Sepeti Temizle")
        btn_trash.setFixedSize(40, 40)
        btn_trash.setStyleSheet(theme_qss("background: @danger_bg; border-radius: 8px; color: @danger; font-size: 18px; border:none;"))
        btn_trash.clicked.connect(self.clear_cart)
        rhl.addStretch()
        rhl.addWidget(btn_trash)
        
        right_layout.addWidget(r_header)
        
        # Cart Table
        self.table = QTableWidget()
        self.table.setColumnCount(4) # Ad, Adet, Fiyat, Sil
        self.table.setHorizontalHeaderLabels(["Ürün", "Adet", "Tutar", ""])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 70)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 40)
        
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setStyleSheet(theme_qss("""
            QTableWidget { border: none; background: @surface; font-size: 14px; }
            QTableWidget::item { padding: 10px; border-bottom: 1px solid @surface_alt; }
            QHeaderView::section { background: @surface; color: @text_muted; font-weight: 700; border-bottom: 2px solid @surface_alt; padding: 10px; }
        """))
        right_layout.addWidget(self.table)
        
        # Summary Area (Dark)
        summary_box = QFrame()
        summary_box.setStyleSheet(theme_qss("background-color: @surface_alt; color: @text; border-top-left-radius: 20px; border-top-right-radius: 20px; border: 1px solid @border;"))
        s_lay = QVBoxLayout(summary_box)
        s_lay.setContentsMargins(25, 25, 25, 25)
        s_lay.setSpacing(15)
        
        # Total Row
        tl_row = QHBoxLayout()
        lbl_total_title = QLabel("TOPLAM TUTAR")
        lbl_total_title.setStyleSheet(theme_qss("color: @text_muted; font-size: 14px; font-weight: 600; border:none;"))
        tl_row.addWidget(lbl_total_title)
        self.lbl_total = QLabel("0.00 ₺")
        self.lbl_total.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lbl_total.setStyleSheet(theme_qss("color: @success; font-size: 32px; font-weight: 900; border:none;"))
        tl_row.addWidget(self.lbl_total)
        s_lay.addLayout(tl_row)
        
        s_lay.addSpacing(10)
        
        # Pay Buttons
        btn_cash = QPushButton("💵 NAKİT TAHSİLAT")
        btn_cash.setFixedHeight(55)
        btn_cash.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cash.setStyleSheet(theme_qss("""
            QPushButton { background-color: @success; color: @selection_text; font-weight: 800; font-size: 16px; border-radius: 12px; border:none; }
            QPushButton:hover { background-color: @success; }
        """))
        btn_cash.clicked.connect(lambda: self.finish_sale("Nakit"))
        
        btn_cc = QPushButton("💳 KREDİ KARTI")
        btn_cc.setFixedHeight(55)
        btn_cc.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cc.setStyleSheet(theme_qss("""
            QPushButton { background-color: @accent; color: @selection_text; font-weight: 800; font-size: 16px; border-radius: 12px; border:none; }
            QPushButton:hover { background-color: @accent_hover; }
        """))
        btn_cc.clicked.connect(lambda: self.finish_sale("Kredi Kartı"))
        
        s_lay.addWidget(btn_cash)
        s_lay.addWidget(btn_cc)
        
        right_layout.addWidget(summary_box)
        
        main_layout.addWidget(right_panel, 35) # %35 Genişlik
        
        # Shortcuts
        QShortcut(QKeySequence("F1"), self).activated.connect(lambda: self.finish_sale("Nakit"))
        QShortcut(QKeySequence("F2"), self).activated.connect(lambda: self.finish_sale("Kredi Kartı"))
        QShortcut(QKeySequence("Delete"), self).activated.connect(self.remove_selected)

    def load_products(self):
        """Ürünleri DB'den çek ve kategori/grid doldur"""
        try:
            # part: (id, code, name, category, stock, price, ...)
            self.db.cursor.execute("SELECT id, code, name, category, stock, price, currency FROM parts ORDER BY name")
            rows = self.db.cursor.fetchall()
            
            self.all_products = []
            categories = set(["Tümü"])
            
            for r in rows:
                p = {
                    "id": r[0],
                    "code": r[1] or "",
                    "name": r[2],
                    "category": r[3] or "Genel",
                    "stock": r[4] or 0,
                                        "price": float(r[5] or 0),
                    "currency": r[6] if len(r)>6 else "TRY" 
                }
                self.all_products.append(p)
                categories.add(p["category"])
                
            # Kategorileri oluştur
            self.setup_categories(sorted(list(categories)))
            
            # Grid'i doldur
            self.filter_products()
            
        except Exception as e:
            logger.error(f"POS Load Products Error: {e}")

    def setup_categories(self, categories):
        # Clear layout
        while self.cat_layout.count():
            item = self.cat_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        for cat in categories:
            btn = QPushButton(cat)
            btn.setCheckable(True)
            btn.setChecked(cat == self.selected_category)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda ch, c=cat: self.change_category(c))
            btn.setStyleSheet(theme_qss(self.get_cat_btn_style(cat == self.selected_category)))
            self.cat_layout.addWidget(btn)
        self.cat_layout.addStretch()

    def get_cat_btn_style(self, active=False):
        if active:
            return """
                QPushButton { background-color: @accent; color: @selection_text; border-radius: 20px; padding: 8px 20px; font-weight: bold; border: none; }
            """
        else:
            return """
                QPushButton { background-color: @surface; color: @text_muted; border-radius: 20px; padding: 8px 20px; font-weight: 600; border: 1px solid @border; }
                QPushButton:hover { background-color: @surface_alt; color: @text; }
            """
            
    def change_category(self, cat):
        self.selected_category = cat
        # Re-render buttons style
        for i in range(self.cat_layout.count()):
            w = self.cat_layout.itemAt(i).widget()
            if isinstance(w, QPushButton):
                w.setChecked(w.text() == cat)
                w.setStyleSheet(theme_qss(self.get_cat_btn_style(w.text() == cat)))
        
        self.filter_products()

    def filter_products(self):
        query = self.inp_search.text().lower().strip()
        
        # Clear Grid
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        
        self.current_filtered_products = []
        for p in self.all_products:
            # 1. Kategori Filtresi
            if self.selected_category != "Tümü" and p["category"] != self.selected_category:
                continue
            
            # 2. Arama Filtresi
            if query and (query not in p["name"].lower() and query not in p["code"].lower()):
                continue
            
            self.current_filtered_products.append(p)
            
        # Reset counters and render first batch
        self.rendered_count = 0
        self.render_batch()

    def render_batch(self):
        """Renders the next batch of products"""
        if self.rendered_count >= len(self.current_filtered_products):
             return
             
        limit = self.rendered_count + self.BATCH_SIZE
        batch = self.current_filtered_products[self.rendered_count : limit]
        
        # Grid positions
        # Calculate current row/col based on existing items
        # But since we remove all items on filter, we can calculate simply 
        # No, we append. So we need to track where we are.
        # Ideally, we can just keep adding. 
        
        # Let's count current widgets to decide row/col
        current_widget_count = self.rendered_count
        max_cols = 4 
        
        for p in batch:
            row = current_widget_count // max_cols
            col = current_widget_count % max_cols
            
            card = ProductCard(p["id"], p["name"], p["price"], p["stock"], p["category"], p.get("currency", "TRY"), self)
            self.grid_layout.addWidget(card, row, col)
            current_widget_count += 1
            
        self.rendered_count = current_widget_count
        
        # Empty hint check (only if total is 0)
        if not self.current_filtered_products:
             lbl = QLabel("Ürün bulunamadı.")
             lbl.setStyleSheet(theme_qss("color: @disabled_text; font-size: 16px; margin-top: 50px;"))
             self.grid_layout.addWidget(lbl, 0, 0)
             
    def check_scroll_bottom(self, value):
        """Checks if scrollbar is near bottom to trigger load"""
        bar = self.product_scroll.verticalScrollBar()
        if value > bar.maximum() - 200: # 200px threshold
            self.render_batch()

    def process_barcode_enter(self):
        """Barkod okutulduğunda enter'a basılırsa"""
        text = self.inp_search.text().strip()
        if not text: return
        
        # Tam eşleşen barkodu bul ve sepete ekle
        found = None
        for p in self.all_products:
            if p["code"] == text:
                found = p
                break
        
        if found:
            self.add_to_cart_by_id(found["id"])
            self.inp_search.clear()
            show_success(self.window(), f"Eklendi: {found['name']}", 500)
        else:
            # Eğer grid'de tek bir sonuç kaldıysa onu ekle (Hızlı arama mantığı)
            # Opsiyonel: Şimdilik sadece uyarı verelim
            pass

    def add_to_cart_by_id(self, p_id):
        product = next((p for p in self.all_products if p["id"] == p_id), None)
        if not product: return
        
        # Stok kontrol (Burada hafızadan yapıyoruz, satış anında DB kontrolü var)
        current_qty = sum(item['qty'] for item in self.cart_items if item['id'] == p_id)
        if product["stock"] <= current_qty:
            show_warning(self.window(), "Stok yetersiz!", 1000)
            return

        # Sepete ekle
        found = False
        for item in self.cart_items:
            if item['id'] == p_id:
                item['qty'] += 1
                item['total'] = item['qty'] * item['price']
                found = True
                break
        
        if not found:
            self.cart_items.append({
                'id': p_id,
                'name': product['name'],
                'price': product['price'],
                'currency': product.get('currency', 'TRY'),
                'qty': 1,
                'total': product['price']
            })
        
        self.update_cart_ui()
        
        # Ses
        try: import winsound; winsound.Beep(1000, 50)
        except ImportError: pass
        except RuntimeError: pass

    def update_cart_ui(self):
        self.table.setRowCount(0)
        grand_total = 0.0
        
        for i, item in enumerate(self.cart_items):
            self.table.insertRow(i)
            
            # Ürün Adı
            self.table.setItem(i, 0, QTableWidgetItem(item['name']))
            
            # Adet (Spinbox or simple label Let's use Label for speed, click to edit logic later)
            lbl_qty = QLabel(f"x {item['qty']}")
            lbl_qty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_qty.setStyleSheet(theme_qss("font-weight: bold; color: @accent; border:none;"))
            self.table.setCellWidget(i, 1, lbl_qty)
            
            # Tutar
            sym = "$" if item.get('currency')=="USD" else "€" if item.get('currency')=="EUR" else "₺"
            self.table.setItem(i, 2, QTableWidgetItem(f"{item['total']:,.2f} {sym}"))
            
            # Sil Btn
            btn_del = QPushButton("✖")
            btn_del.setFixedSize(24, 24)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setStyleSheet(theme_qss("background: transparent; color: @danger; font-weight: bold; border: none;"))
            btn_del.clicked.connect(lambda ch, idx=i: self.remove_item(idx))
            self.table.setCellWidget(i, 3, btn_del)
            
            grand_total += item['total']
        
        # Döviz bazlı toplam göster
        currencies_in_cart = set(item.get('currency', 'TRY') for item in self.cart_items)
        if len(currencies_in_cart) == 1 and self.cart_items:
            cart_currency = list(currencies_in_cart)[0]
            sym = "$" if cart_currency == "USD" else "€" if cart_currency == "EUR" else "₺"
            self.lbl_total.setText(f"{grand_total:,.2f} {sym}")
        else:
            self.lbl_total.setText(f"{grand_total:,.2f} ₺")
        if self.cart_items:
            self.table.scrollToBottom()

    def remove_item(self, index):
        if 0 <= index < len(self.cart_items):
            del self.cart_items[index]
            self.update_cart_ui()

    def remove_selected(self):
        r = self.table.currentRow()
        if r >= 0: self.remove_item(r)
        
    def select_customer_dialog(self):
        from src.ui.dialogs.customer_select_dialog import CustomerSelectDialog
        dlg = CustomerSelectDialog(self.db, self)
        if dlg.exec():
            self.selected_customer = dlg.selected_customer
            self.btn_customer.setText(f"👤 {self.selected_customer['name']}")
            self.btn_customer.setStyleSheet(theme_qss("background-color: @surface_alt; border: 1px solid @success; border-radius: 8px; padding: 8px; font-weight: bold; color: @success;"))

    def clear_cart(self):
        self.cart_items = []
        self.selected_customer = None
        self.btn_customer.setText("👤 Müşteri Seç")
        self.btn_customer.setStyleSheet(theme_qss("background-color: @surface_alt; border: 1px solid @border; border-radius: 8px; padding: 8px; font-weight: bold;"))
        self.update_cart_ui()

    def finish_sale(self, method):
        if not self.cart_items:
            return
            
        total = sum(item['total'] for item in self.cart_items)
        customer_id = self.selected_customer['id'] if self.selected_customer else None
        customer_name = self.selected_customer['name'] if self.selected_customer else None
        
        try:
            # 1. Stok Düşüm (Bulk)
            if self.cart_items:
                item_ids = [str(item['id']) for item in self.cart_items]
                placeholders = ','.join(['?'] * len(item_ids))
                self.db.cursor.execute(
                    "SELECT id, stock FROM parts WHERE id IN ({placeholders})".format(
                        placeholders=placeholders
                    ),
                    item_ids,
                )
                stocks = {row[0]: row[1] for row in self.db.cursor.fetchall()}
                
                update_data = []
                for item in self.cart_items:
                    curr = stocks.get(item['id'], 0)
                    new_s = max(0, curr - item['qty'])
                    update_data.append((new_s, item['id']))
                    self.db.add_stock_movement(item['id'], item['qty'], curr, "Satış", f"POS Satış: {method}")
                    
                if update_data:
                    self.db.cursor.executemany("UPDATE parts SET stock=? WHERE id=?", update_data)
            
            self.db.conn.commit()

            # Sepetteki döviz birimini belirle
            currencies_in_cart = set(item.get('currency', 'TRY') for item in self.cart_items)
            sale_currency = list(currencies_in_cart)[0] if len(currencies_in_cart) == 1 else 'TRY'
            sale_sym = "$" if sale_currency == "USD" else "€" if sale_currency == "EUR" else "₺"

            item_lines = []
            for idx, item in enumerate(self.cart_items, start=1):
                line_total = item['total']
                isym = "$" if item.get('currency') == "USD" else "€" if item.get('currency') == "EUR" else "₺"
                item_lines.append(f"{idx}. {item['name']} (x{item['qty']}) - {line_total:,.2f} {isym}")
            header_desc = f"POS Ürün Satışı ({len(self.cart_items)} kalem) - {method}"
            full_desc = header_desc
            if item_lines:
                full_desc = header_desc + "\n" + "\n".join(item_lines)

            self.db.add_transaction(
                "Gelir",
                "Satış",
                total,
                full_desc,
                customer_name=customer_name,
                customer_id=customer_id,
                currency=sale_currency,
                original_amount=total,
            )

            # --- GİDER KAYDI: Satılan Malın Maliyeti (COGS) ---
            try:
                total_material_cost = 0.0
                cost_parts = []
                if self.cart_items:
                    try:
                        item_ids = [str(item['id']) for item in self.cart_items]
                        placeholders = ','.join(['?'] * len(item_ids))
                        self.db.cursor.execute(
                            "SELECT id, purchase_price FROM parts WHERE id IN ({placeholders})".format(
                                placeholders=placeholders
                            ),
                            item_ids,
                        )
                        prices = {row[0]: float(row[1] or 0) for row in self.db.cursor.fetchall()}
                        
                        for item in self.cart_items:
                            pp = prices.get(item['id'], 0.0)
                            if pp > 0:
                                line_cost = pp * item['qty']
                                total_material_cost += line_cost
                                cost_parts.append(f"{item['name']}x{item['qty']}")
                    except Exception:
                        pass

                if total_material_cost > 0:
                    cost_desc = f"Satılan Malın Maliyeti - POS ({len(self.cart_items)} kalem)"
                    if cost_parts:
                        cost_desc += f" [{', '.join(cost_parts)}]"
                    self.db.add_transaction(
                        t_type="Gider",
                        category="Satılan Malın Maliyeti",
                        amount=total_material_cost,
                        description=cost_desc,
                        customer_name=customer_name,
                        customer_id=customer_id,
                    )
            except Exception as cogs_err:
                logger.error(f"POS COGS recording error: {cogs_err}")

            if customer_id:
                try:
                    header_desc_cur = f"POS Satış ({len(self.cart_items)} kalem) - {method}"
                    full_desc_cur = header_desc_cur
                    if item_lines:
                        full_desc_cur = header_desc_cur + "\n" + "\n".join(item_lines)

                    # 1. DEBIT: Müşteri borçlanır (satış)
                    self.db.add_currency_transaction(
                        customer_id=customer_id,
                        amount=total,
                        currency=sale_currency,
                        transaction_type="DEBIT",
                        description=full_desc_cur,
                        tracking_no=None,
                    )
                    # 2. CREDIT: Anında tahsilat (nakit/kart)
                    self.db.add_currency_transaction(
                        customer_id=customer_id,
                        amount=total,
                        currency=sale_currency,
                        transaction_type="CREDIT",
                        description=f"POS Tahsilat ({method}) - {len(self.cart_items)} kalem",
                        tracking_no=None,
                    )
                except Exception as ex:
                    logger.error(f"POS currency transaction error: {ex}")
            
            show_success(self.window(), f"Satış Başarılı! Toplam: {total:,.2f} {sale_sym}")
            
            # 3. YAZILIM SATIŞI İSE SUNUCUYA YEDEKLE (KULLANICI İSTEĞİ)
            is_software_sale = any("yazılım" in item['name'].lower() for item in self.cart_items)
            if is_software_sale:
                show_info(self.window(), "Yazılım satışı tespit edildi. Sunucuya özel yedek alınıyor...", 3000)
                try:
                    from src.utils.cloud_backup import get_cloud_backup_manager
                    from src.utils.path_helper import PathHelper
                    import threading
                    
                    def run_backup():
                        manager = get_cloud_backup_manager(PathHelper.get_db_path())
                        res = manager.sync_all(customer_name=customer_name or "Genel_Yazilim_Satisi")
                        if res.get('success'):
                            logger.info("Yazılım satışı yedeği başarıyla yüklendi.")
                        else:
                            logger.error(f"Yazılım satışı yedeği hatası: {res.get('error')}")

                    threading.Thread(target=run_backup, daemon=True).start()
                except Exception as ex:
                    logger.error(f"Auto Backup Trigger Error: {ex}")

            # Audit
            from src.utils.audit_logger import get_audit_logger
            audit = get_audit_logger(self.db)
            audit.log_action('sales', 'SELL', f"POS Satışı yapıldı: {total:.2f} TL ({method}) (Müşteri: {customer_name})")
            
            self.clear_cart()
            self.load_products() # Stokları güncelle
            main_window = self.window()
            if main_window and hasattr(main_window, "refresh_loaded_page"):
                try:
                    main_window.refresh_loaded_page(101)
                    main_window.refresh_loaded_page(40)
                except Exception as refresh_err:
                    logger.debug(f"POS live refresh skipped: {refresh_err}")
            
        except Exception as e:
            show_error(self, f"Satış hatası: {e}")



