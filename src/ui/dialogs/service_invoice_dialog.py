# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, 
                             QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator, 
                             QFrame, QPushButton, QCheckBox, QAbstractItemView,
                             QGridLayout, QComboBox, QWidget, QHeaderView, QRadioButton, QDialog)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QAction
from datetime import datetime
from src.utils.theme_colors import theme_qss, tc, qc
from src.utils.design_system import DesignTokens
from src.utils.pdf_manager import PDFManagerQt
from src.utils.exchange_rate_manager import ExchangeRateManager
from src.utils.logger import logger
from src.ui.dialogs.base_modern_dialog import BaseModernDialog
from src.ui.dialogs.simple_confirm import SimpleConfirmDialog
from src.utils.currency_helper import CurrencyHelper
from src.utils.date_formatter import format_date
from src.utils.toast_notification import show_error, show_warning


class ServiceInvoiceDialog(BaseModernDialog):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    def __init__(self, db, customer_id, parent=None):
        self.db = db
        self.customer_id = customer_id
        self.customer_name = ""
        self.transactions = []
        self.active_currency = CurrencyHelper.get_code(db)
        
        # Resolve Customer Name
        try:
            self.db.cursor.execute("SELECT name FROM customers WHERE id=?", (customer_id,))
            row = self.db.cursor.fetchone()
            if row:
                self.customer_name = row[0]
        except Exception as e:
            logger.debug(f"Service invoice customer resolve fallback: {e}")

        super().__init__(parent, title=f"Servis Faturası Düzenle - {self.customer_name}", width=1180, height=820)
        self.set_wheel_scroll_enabled(True)
        
        self.setup_ui()
        self._wire_ui_signals()
        self.load_transactions()

    def get_customer_balance(self, customer_id):
        """Müşteri bakiyesini hesapla (Döviz dahil toplam TL)"""
        try:
            # Database class inherits from CurrencyMixin, which has get_customer_total_balance_in_try
            # If called via self.db or if self is Database
            if hasattr(self.db, 'get_customer_total_balance_in_try'): # Changed self to self.db
                return self.db.get_customer_total_balance_in_try(customer_id) # Changed self to self.db
            
            # Fallback if mixed into something else
            return 0.0
        except Exception as e:
            logger.error(f"Customer balance error: {e}")
            return 0.0

    def setup_ui(self):
        # Base layout is self.content_layout from BaseModernDialog
        
        # 1. Top Section (Template selection & Info)
        top_bar = QHBoxLayout()
        
        lbl_info = QLabel("Hizmet Faturası Oluştur")
        lbl_info.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl_info.setStyleSheet(theme_qss("color: @text;"))
        
        self.lbl_cust_balance = QLabel(f"Cari Bakiye: {CurrencyHelper.format_from_try(0, db=self.db, currency_code=self.active_currency)}")
        self.lbl_cust_balance.setStyleSheet(theme_qss("""
            QLabel {
                color: @danger; 
                font-weight: bold; 
                background: @danger_bg; 
                padding: 5px 15px; 
                border: 1px solid @danger;
                border-radius: 10px;
                font-size: 11pt;
            }
        """))

        
        temp_layout = QHBoxLayout()
        temp_layout.setSpacing(15)
        self.lbl_active_currency = QLabel(f"Aktif Para Birimi: {self.active_currency}")
        self.lbl_active_currency.setStyleSheet(theme_qss("color: @text; font-weight: bold;"))
        
        # Para Birimi Seçimi
        self.rb_try = QRadioButton("₺")
        self.rb_usd = QRadioButton("$")
        self.rb_eur = QRadioButton("€")
        self.rb_try.setVisible(False)
        self.rb_usd.setVisible(False)
        self.rb_eur.setVisible(False)
        
        lbl_temp = QLabel("Şablon:")
        lbl_temp.setStyleSheet(theme_qss("color: @text_muted; font-weight: bold;"))
        self.cmb_template = QComboBox()
        self.cmb_template.addItems(["modern", "corporate", "minimal"])
        self.cmb_template.setFixedWidth(120)
        self.cmb_template.setStyleSheet(theme_qss("""
            QComboBox { padding: 5px; border: 1px solid @border; border-radius: 5px; color: @text; background: @surface; }
            QRadioButton { color: @text; font-weight: bold; font-size: 14px; }
        """))
        
        temp_layout.addWidget(self.lbl_active_currency)
        temp_layout.addWidget(lbl_temp)
        temp_layout.addWidget(self.cmb_template)
        
        top_bar.addWidget(lbl_info)
        top_bar.addWidget(self.lbl_cust_balance)
        top_bar.addStretch()

        top_bar.addLayout(temp_layout)
        
        self.content_layout.addLayout(top_bar)
        
        # 2. Table
        table_container = QFrame()
        table_container.setStyleSheet(theme_qss("background: @surface; border: 1px solid @border; border-radius: 8px;"))
        t_layout = QVBoxLayout(table_container)
        t_layout.setContentsMargins(0,0,0,0)
        
        lbl_t = QLabel("  Faturalanmamış İşlemler")
        lbl_t.setStyleSheet(theme_qss("background: @surface_alt; padding: 10px; font-weight: bold; color: @text; border-bottom: 1px solid @border; border-top-left-radius: 8px; border-top-right-radius: 8px;"))
        t_layout.addWidget(lbl_t)

        self.table = QTreeWidget()
        self.table.setColumnCount(5)
        self.table.setHeaderLabels(["Seç", "Tarih", "Açıklama", "Kategori", "Tutar"])
        self.table.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setMinimumHeight(420)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table.setAlternatingRowColors(True)
        self.table.setRootIsDecorated(True)
        self.table.setItemsExpandable(True)
        # Connect item changed for calculation
        self.table.itemChanged.connect(self.on_item_changed)
        self.table.itemClicked.connect(self.on_item_clicked)
        
        self.table.setStyleSheet(theme_qss("""
            QTreeWidget {
                border: none;
                gridline-color: @surface_alt;
            }
            QHeaderView::section {
                background-color: @surface;
                padding: 10px;
                border: none;
                border-bottom: 2px solid @surface_alt;
                font-weight: bold;
                color: @text_muted;
            }
            QTreeWidget::item { padding: 5px; height: 30px; color: @text; }
            QTreeWidget::item:hover { background-color: @selection_bg; color: @accent_pressed; }
            QTreeWidget::item:selected { background-color: @accent; color: @selection_text; }
            QTreeWidget::item:selected:active { background-color: @accent; color: @selection_text; }
            QTreeWidget::indicator { width: 18px; height: 18px; }
            QTreeWidget::indicator:checked { image: url(assets/icons/checked.png); background-color: @success; border: 1px solid @success; border-radius: 4px; }
            QTreeWidget::indicator:unchecked { background-color: @surface; border: 2px solid @border; border-radius: 4px; }
            QTreeWidget::indicator:hover { border-color: @accent; }
            QScrollBar:vertical {
                width: 10px;
                background: transparent;
                margin: 4px;
            }
            QScrollBar::handle:vertical {
                background: @border;
                border-radius: 5px;
                min-height: 24px;
            }
            QScrollBar::handle:vertical:hover { background: @text_muted; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """))
        t_layout.addWidget(self.table)
        
        self.content_layout.addWidget(table_container)

        # 3. Summary & Actions
        bottom_layout = QHBoxLayout()
        
        # Left side: Notes
        info_lbl = QLabel("ⓘ Seçilen işlemler PDF faturaya eklenecektir.")
        info_lbl.setStyleSheet(theme_qss("color: @disabled_text; font-style: italic;"))
        bottom_layout.addWidget(info_lbl)
        
        bottom_layout.addStretch()

        # Right side: Totals
        summary_frame = QFrame()
        summary_frame.setStyleSheet(theme_qss("""
            background: @surface; 
            border-radius: 8px; 
            border: 1px solid @border; 
            padding: 15px;
        """))
        summary_layout = QHBoxLayout(summary_frame)
        
        lbl_total_txt = QLabel("Toplam:")
        lbl_total_txt.setStyleSheet(theme_qss("border: none; font-weight: bold; font-size: 14px; color: @text;"))
        self.lbl_total_val = QLabel(CurrencyHelper.format_try_for_display(0, db=self.db))
        self.lbl_total_val.setStyleSheet(theme_qss("border: none; font-size: 18px; font-weight: bold; color: @success; margin-left: 10px;"))
        
        summary_layout.addWidget(lbl_total_txt)
        summary_layout.addWidget(self.lbl_total_val)
        
        bottom_layout.addWidget(summary_frame)
        
        self.content_layout.addLayout(bottom_layout)

        # 4. Final Actions
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_cancel = QPushButton("İptal")
        self.btn_cancel.setFixedSize(100, 45)
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_cancel.setStyleSheet(theme_qss("""
            QPushButton {
                background: @surface;
                border: 1px solid @border;
                border-radius: 8px;
                color: @text_muted;
                font-weight: bold;
            }
            QPushButton:hover { background: @surface_alt; color: @text; }
        """))
        
        self.btn_generate = QPushButton("📄 Fatura Kes (PDF)")
        self.btn_generate.setFixedSize(180, 45)
        self.btn_generate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_generate.clicked.connect(self.generate_invoice)
        self.btn_generate.setEnabled(False)
        self.btn_generate.setStyleSheet(theme_qss("""
            QPushButton {{
                background-color: @warning;
                color: @selection_text;
                font-weight: bold;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover { background-color: @warning; }
            QPushButton:disabled { background-color: @border; color: @border; }
        """))
        
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_generate)
        
        self.content_layout.addLayout(btn_layout)

    def _wire_ui_signals(self):
        self.rb_try.toggled.connect(self._on_ui_widget_changed)
        self.rb_usd.toggled.connect(self._on_ui_widget_changed)
        self.rb_eur.toggled.connect(self._on_ui_widget_changed)
        self.cmb_template.currentIndexChanged.connect(self._on_ui_widget_changed)

    def load_transactions(self):
        try:
            self.transactions = self.db.get_uninvoiced_transactions(self.customer_id)
            self.table.clear()
            self.table.blockSignals(True)
            
            # Group by date
            grouped = {}
            for t in self.transactions:
                # t: {'id': 1, 'date': '...', 'description': '...', 'amount': 100, 'currency': 'TRY', 'source': 'accounting'}
                d_str = t['date']
                if d_str not in grouped: grouped[d_str] = []
                grouped[d_str].append(t)
                
            def date_sorter(d):
                try:
                    # Try various formats commonly used in the app
                    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M", "%d/%m/%Y", "%d.%m.%Y"):
                        try: return datetime.strptime(d, fmt)
                        except ValueError: continue
                    return datetime.min
                except Exception: return datetime.min
                
            sorted_dates = sorted(list(grouped.keys()), key=date_sorter, reverse=True)
            
            for d in sorted_dates:
                items = grouped[d]
                total_daily_try = sum(float(x.get('try_equivalent', x['amount'])) for x in items)
                
                # Parent Node
                root = QTreeWidgetItem(self.table)
                root.setFlags(root.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                root.setCheckState(0, Qt.CheckState.Unchecked)
                root.setText(1, f"📅 {format_date(d, self.db)}")
                root.setText(2, f"{len(items)} İşlem")
                root.setText(4, CurrencyHelper.format_try_for_display(total_daily_try, db=self.db))
                
                # Style Parent
                for c in range(5):
                    root.setBackground(c, qc("surface_alt"))
                    f = root.font(c); f.setBold(True); root.setFont(c, f)
                
                # Children
                for t in items:
                    child = QTreeWidgetItem(root)
                    child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    child.setCheckState(0, Qt.CheckState.Unchecked)
                    # Use role to store the whole dict for easy retrieval
                    child.setData(0, Qt.ItemDataRole.UserRole, t)
                    
                    child.setText(1, format_date(t['date'], self.db))
                    child.setText(2, t['description'])
                    child.setText(3, t.get('category', 'Satış'))
                    
                    # Display original amount and currency
                    amt = float(t['amount'])
                    curr = t['currency']
                    child.setText(4, f"{amt:,.2f} {curr}")
                    child.setTextAlignment(4, Qt.AlignmentFlag.AlignRight)
                    
                    # Store raw TRY value for summation
                    try_val = float(t.get('try_equivalent', t['amount']))
                    child.setData(4, Qt.ItemDataRole.UserRole, try_val)
                    
                root.setExpanded(False)
                
            if self.table.topLevelItemCount() > 0:
                self.table.topLevelItem(0).setExpanded(True)
                
            self.table.blockSignals(False)
            
        except Exception as e:
            logger.error(f"Error loading transactions: {e}")
            import traceback
            logger.error(traceback.format_exc())

        # Cari bakiye bilgisini güncelle (Çoklu Para Birimi)
        try:
            # Try to get multi-currency balance if method exists
            if hasattr(self.db, 'get_customer_all_balances'):
                balances = self.db.get_customer_all_balances(self.customer_id)
            else:
                # Fallback to single currency
                balances = {'TRY': self.db.get_customer_balance(self.customer_id)}

            total_try = 0.0
            for curr, amount in balances.items():
                total_try += CurrencyHelper.convert_amount(
                    self.db,
                    float(amount or 0),
                    from_currency=curr,
                    to_currency="TRY",
                )
            has_debt = total_try > 0
            text = f"Cari Bakiye: {CurrencyHelper.format_from_try(total_try, db=self.db, currency_code=self.active_currency)}"
            self.lbl_cust_balance.setText(text)
            
            # Adjust styling based on debt status
            if not has_debt:
                 self.lbl_cust_balance.setStyleSheet(theme_qss("""
                    QLabel {
                        color: @success; 
                        font-weight: bold; 
                        background: @success_bg; 
                        padding: 5px 15px; 
                        border: 1px solid @success;
                        border-radius: 10px;
                        font-size: 11pt;
                    }
                """))
            else:
                 self.lbl_cust_balance.setStyleSheet(theme_qss("""
                    QLabel {
                        color: @danger; 
                        font-weight: bold; 
                        background: @danger_bg; 
                        padding: 8px 15px; 
                        border: 1px solid @danger;
                        border-radius: 10px;
                        font-size: 11pt;
                    }
                """))
        except Exception as e:
            logger.error(f"Balance display error: {e}")
            self.lbl_cust_balance.setText("Bakiye Yüklenemedi")


    def on_item_changed(self, item, column):
        """Called when checkbox state changes"""
        # Manual Parent/Child sync
        # Prevent recursion by blocking signals creates issues sometimes, handle carefully
        self.table.blockSignals(True)
        
        # If item is parent (has children)
        if item.childCount() > 0:
            state = item.checkState(0)
            if state == Qt.CheckState.Checked:
                item.setExpanded(True) # Expand to show selected children
            for i in range(item.childCount()):
                item.child(i).setCheckState(0, state)
                
        self.table.blockSignals(False)
        self.calculate_totals()

    def on_item_clicked(self, item, column):
        # Allow checking box by clicking anywhere on the row (except the checkbox itself which is handled by Qt)
        if column > 0:
            current = item.checkState(0)
            new_state = Qt.CheckState.Unchecked if current == Qt.CheckState.Checked else Qt.CheckState.Checked
            item.setCheckState(0, new_state)

    def calculate_totals(self):
        total_tl = 0.0
        selected_count = 0
        
        iterator = QTreeWidgetItemIterator(self.table)
        while iterator.value():
            item = iterator.value()
            if item.checkState(0) == Qt.CheckState.Checked:
                if item.data(0, Qt.ItemDataRole.UserRole): # Transaction item
                    val = item.data(4, Qt.ItemDataRole.UserRole)
                    if val is not None:
                        total_tl += float(val)
                        selected_count += 1
            iterator += 1

        converted_total = CurrencyHelper.convert_amount(
            self.db,
            total_tl,
            from_currency="TRY",
            to_currency=self.active_currency,
        )
        self.lbl_total_val.setText(CurrencyHelper.format_amount(converted_total, db=self.db, currency_code=self.active_currency))
        self.btn_generate.setEnabled(selected_count > 0)

    def generate_invoice(self):
        selected_items = []
        selected_ids = []
        subtotal_tl = 0.0
        
        iterator = QTreeWidgetItemIterator(self.table, QTreeWidgetItemIterator.IteratorFlag.Checked)
        while iterator.value():
            item = iterator.value()
            t_data = item.data(0, Qt.ItemDataRole.UserRole)
            
            if t_data and isinstance(t_data, dict): # It's a transaction item
                price_tl = float(item.data(4, Qt.ItemDataRole.UserRole) or 0)
                
                item_data = {
                    'service': item.text(3), # Category
                    'description': item.text(2),
                    'price': price_tl,
                    'date': item.text(1)
                }
                selected_items.append(item_data)
                selected_ids.append({'id': t_data['id'], 'source': t_data['source']})
                subtotal_tl += price_tl
            
            iterator += 1
            
        if not selected_items:
            return

        currency_code = self.active_currency
        currency_symbol = CurrencyHelper.get_symbol(self.db, currency_code)
        converted_subtotal = CurrencyHelper.convert_amount(
            self.db,
            subtotal_tl,
            from_currency="TRY",
            to_currency=currency_code,
        )
        conv_totals = (
            converted_subtotal,
            0.0, # discount
            0.0, # vat_rate
            0.0, # vat_amount
            converted_subtotal # total
        )

        # Convert items
        conv_items = []
        for it in selected_items:
            c_it = it.copy()
            c_it['price'] = CurrencyHelper.convert_amount(
                self.db,
                it['price'],
                from_currency="TRY",
                to_currency=currency_code,
            )
            conv_items.append(c_it)

        from src.ui.utils.background_task import run_cancellable_task

        template_type = self.cmb_template.currentText()
        customer_name = self.customer_name
        self.btn_generate.setEnabled(False)

        def produce_pdf(is_cancelled):
            if is_cancelled():
                return None
            pdf = PDFManagerQt(self.db)
            return pdf.create_invoice(
                template_type=template_type,
                cart_items=conv_items,
                totals=conv_totals,
                customer_name=customer_name,
                currency=currency_symbol,
            )

        def pdf_ready(pdf_result):
            if not pdf_result:
                return
            success, result = pdf_result
            if not success:
                logger.error("Invoice generation failed: %s", result)
                show_warning(
                    self,
                    f"Fatura PDF dosyas\u0131 olu\u015fturulamad\u0131: {result}",
                )
                return
            confirm = SimpleConfirmDialog(
                parent=self,
                title="Fatura \u0130\u015flemini Onayla",
                text=(
                    "PDF faturas\u0131 ba\u015far\u0131yla olu\u015fturuldu.\n\n"
                    f"Se\u00e7ili {len(selected_ids)} adet i\u015flemi "
                    "'Faturaland\u0131' olarak i\u015faretlemek istiyor musunuz"
                ),
                ok_text="Onayla & Kapat",
                btn_color=tc("success"),
            )
            if confirm.exec():
                try:
                    self.db.mark_transactions_as_invoiced(selected_ids)
                    self.accept()
                except Exception as e:
                    logger.error("Error marking as invoiced: %s", e)
                    self.accept()

        run_cancellable_task(
            owner=self,
            title="Fatura PDF olusturuluyor",
            target=produce_pdf,
            on_success=pdf_ready,
            on_error=lambda message: show_error(
                self,
                f"Fatura PDF dosyas\u0131 olu\u015fturulamad\u0131: {message}",
            ),
            on_done=self.calculate_totals,
        )
