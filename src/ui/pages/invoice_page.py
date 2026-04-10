from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout, 
                             QComboBox, QLineEdit, QTableWidget, QTableWidgetItem, QPushButton, 
                             QLabel, QFrame, QMessageBox, QHeaderView, QSizePolicy)
from src.utils.theme_colors import theme_qss
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from src.finance.invoice_mapper import InvoiceMapper
from src.api.einvoice_client import EInvoiceClient
from src.utils.logger import logger
from src.utils.toast_notification import show_success, show_error, show_warning
from src.utils.currency_helper import CurrencyHelper
from datetime import datetime
import json

class InvoiceSenderThread(QThread):
    finished = pyqtSignal(bool, dict)

    def __init__(self, client, data):
        super().__init__()
        self.client = client
        self.data = data

    def run(self):
        success, resp = self.client.send_invoice(self.data)
        self.finished.emit(success, resp)

class InvoiceCreationPage(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.mapper = InvoiceMapper()
        self.current_currency_code = CurrencyHelper.get_code(self.db)
        self.current_total_try = 0.0
        # Initialize Client (Fetch key from DB settings)
        api_key = self.db.get_setting("einvoice_api_key", "SANDBOX_KEY_123")
        self.client = EInvoiceClient(api_key=api_key, is_sandbox=True)
        
        self.init_ui()
        self.load_customers()

    def init_ui(self):
        self.setWindowTitle("AYEC Pro | E-Fatura Oluştur")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(24, 20, 24, 20)
        self.layout.setSpacing(16)

        page_title = QLabel("E-Fatura Olustur")
        page_title.setStyleSheet(theme_qss("font-size: 28px; font-weight: 800; color: @text;"))
        self.layout.addWidget(page_title)

        # 1. Müşteri Bilgileri Grubu
        self.client_group = QGroupBox("Müşteri Bilgileri")
        self.client_layout = QFormLayout(self.client_group)
        
        self.cmb_customer = QComboBox()
        self.cmb_customer.setPlaceholderText("Müşteri Seçin...")
        self.cmb_customer.currentIndexChanged.connect(self.on_customer_change)
        
        self.inp_vkn = QLineEdit()
        self.inp_vkn.setReadOnly(True)
        self.inp_addr = QLineEdit()
        self.inp_addr.setReadOnly(True)
        
        self.client_layout.addRow("Müşteri Seç:", self.cmb_customer)
        self.client_layout.addRow("Vergi/TC No:", self.inp_vkn)
        self.client_layout.addRow("Adres:", self.inp_addr)
        

        # 2. Fatura Kalemleri (Ürün/Hizmet)
        self.items_table = QTableWidget(0, 6)
        headers = ["Ürün/Hizmet", "Miktar", "Birim", "Birim Fiyat", "KDV %", "Tutar"]
        self.items_table.setHorizontalHeaderLabels(headers)
        self.items_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.items_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.items_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.items_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.items_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.items_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.items_table.setMinimumHeight(420)
        self.items_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.items_table.cellChanged.connect(self.calculate_totals)
        
        btn_layout = QHBoxLayout()
        self.btn_add_item = QPushButton("+ Yeni Satır Ekle")
        self.btn_add_item.clicked.connect(self.add_row)
        self.btn_remove_item = QPushButton("- Satır Sil")
        self.btn_remove_item.clicked.connect(self.remove_row)
        
        btn_layout.addWidget(self.btn_add_item)
        btn_layout.addWidget(self.btn_remove_item)
        btn_layout.addStretch()
        self.layout.addLayout(btn_layout)

        # 3. Toplamlar Paneli
        self.total_panel = QFrame()
        self.total_panel.setStyleSheet(theme_qss("background-color: @surface_alt; border-radius: 8px; padding: 10px;"))
        self.total_layout = QFormLayout(self.total_panel)
        
        self.lbl_subtotal = QLabel(CurrencyHelper.format_try_for_display(0, db=self.db))
        self.lbl_vat = QLabel(CurrencyHelper.format_try_for_display(0, db=self.db))
        self.lbl_total = QLabel(CurrencyHelper.format_try_for_display(0, db=self.db))
        self.lbl_total.setStyleSheet(theme_qss("font-weight: bold; font-size: 16px; color: @accent_hover;"))
        
        self.total_layout.addRow("Ara Toplam:", self.lbl_subtotal)
        self.total_layout.addRow("Toplam KDV:", self.lbl_vat)
        self.total_layout.addRow("GENEL TOPLAM:", self.lbl_total)
        
        # Banka / Kasa Seçimi Ekleniyor
        self.cmb_bank = QComboBox()
        self.cmb_bank.addItem("Kasa/Banka Seçmeyin", -1)
        try:
            if hasattr(self.db, 'get_bank_accounts'):
                for b in self.db.get_bank_accounts():
                    b_name = b.get('bank_name') if isinstance(b, dict) else b[1]
                    b_id = b.get('id') if isinstance(b, dict) else b[0]
                    self.cmb_bank.addItem(b_name, b_id)
        except Exception:
            pass
        self.total_layout.addRow("Tahsilat Kasası:", self.cmb_bank)
        
        self.total_panel.setMinimumWidth(320)
        self.total_panel.setMaximumWidth(360)

        top_row = QHBoxLayout()
        top_row.setSpacing(16)
        top_row.addWidget(self.client_group, 1)
        top_row.addWidget(self.total_panel, 0, Qt.AlignmentFlag.AlignTop)
        self.layout.addLayout(top_row)

        self.layout.addWidget(self.items_table, 1)

        # 4. Gönder Butonu
        self.btn_send = QPushButton("🚀 E-Faturayı Resmileştir ve Gönder")
        self.btn_send.setStyleSheet(theme_qss("""
            QPushButton { 
                height: 50px; background-color: @accent_hover; color: @selection_text; border-radius: 8px; font-weight: bold; font-size: 14px;
            }
            QPushButton:hover { background-color: @accent; }
        """))
        self.btn_send.clicked.connect(self.send_invoice)
        self.layout.addWidget(self.btn_send)
        
        # Init with one row
        self.add_row()

    def load_customers(self):
        try:
            # Assuming DB has customers table
            cursor = self.db.cursor
            # Select essential columns
            customers = cursor.execute("SELECT id, name, tax_number, address FROM customers").fetchall()
            
            self.customers_data = {} 
            self.cmb_customer.clear()

            for c in customers:
                c_id, name, tax, addr = c
                # Store full data object mapped by ID
                self.customers_data[c_id] = {'name': name, 'tax': tax, 'addr': addr}
                # Add to combo with ID as UserData
                self.cmb_customer.addItem(name, c_id)
            self.cmb_customer.setCurrentIndex(-1)
                
        except Exception as e:
            logger.error(f"InvoiceCreationPage customer load error: {e}")

    def on_customer_change(self):
        # Get ID from UserData
        c_id = self.cmb_customer.currentData()
        if c_id and c_id in self.customers_data:
            c = self.customers_data[c_id]
            self.inp_vkn.setText(str(c.get('tax') or "")) # Tax No
            self.inp_addr.setText(str(c.get('addr') or "")) # Address
        else:
            self.inp_vkn.clear()
            self.inp_addr.clear()

    def add_row(self):
        row = self.items_table.rowCount()
        self.items_table.insertRow(row)
        self.items_table.setItem(row, 0, QTableWidgetItem("Hizmet"))
        self.items_table.setItem(row, 1, QTableWidgetItem("1"))
        self.items_table.setItem(row, 2, QTableWidgetItem("Adet"))
        self.items_table.setItem(row, 3, QTableWidgetItem("0.00"))
        self.items_table.setItem(row, 4, QTableWidgetItem("20")) # VAT
        self.items_table.setItem(row, 5, QTableWidgetItem("0.00")) # Total
        
    def remove_row(self):
        row = self.items_table.currentRow()
        if row >= 0:
            self.items_table.removeRow(row)
            self.calculate_totals()

    def get_float(self, row, col):
        try:
            item = self.items_table.item(row, col)
            return float(item.text().replace(',', '.')) if item else 0.0
        except Exception:
            return 0.0

    def calculate_totals(self):
        subtotal = 0.0
        vat_total = 0.0
        
        self.items_table.blockSignals(True)
        for i in range(self.items_table.rowCount()):
            qty = self.get_float(i, 1)
            price = self.get_float(i, 3)
            vat_rate = self.get_float(i, 4)
            
            amount = qty * price
            vat = amount * (vat_rate / 100.0)
            
            self.items_table.setItem(i, 5, QTableWidgetItem(f"{amount:.2f}"))
            
            subtotal += amount
            vat_total += vat
            
        grand_total = subtotal + vat_total
        self.current_total_try = grand_total

        self.lbl_subtotal.setText(CurrencyHelper.format_try_for_display(subtotal, db=self.db))
        self.lbl_vat.setText(CurrencyHelper.format_try_for_display(vat_total, db=self.db))
        self.lbl_total.setText(CurrencyHelper.format_try_for_display(grand_total, db=self.db))
        self.items_table.blockSignals(False)

    def send_invoice(self):
        # 1. Gather Data
        cust_name = self.cmb_customer.currentText()
        if not cust_name:
            QMessageBox.warning(self, "Hata", "Lütfen müşteri seçin.")
            return

        items = []
        for i in range(self.items_table.rowCount()):
            items.append({
                "name": self.items_table.item(i, 0).text(),
                "quantity": self.get_float(i, 1),
                "unit": self.items_table.item(i, 2).text(),
                "unit_price": self.get_float(i, 3),
                "vat_rate": self.get_float(i, 4)
            })
            
        # Prepare Data for Mapper
        raw_data = {
            "receiver": {
                "name": cust_name,
                "tax_id": self.inp_vkn.text(),
                "address": self.inp_addr.text(),
                "email": "" # Could add field
            },
            "items": items,
            "currency": self.current_currency_code
        }
        
        try:
            # 2. Map to JSON (Official Format)
            json_payload = self.mapper.to_json(raw_data)
            
            # 3. Send Async
            self.btn_send.setEnabled(False)
            self.btn_send.setText("Gönderiliyor... ⏳")
            
            self.worker = InvoiceSenderThread(self.client, json_payload)
            self.worker.finished.connect(self.on_send_finished)
            self.worker.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Veri Hatası", f"Fatura oluşturulamadı:\n{e}")

    def on_send_finished(self, success, resp):
        self.btn_send.setEnabled(True)
        self.btn_send.setText("🚀 E-Faturayı Resmileştir ve Gönder")
        
        if success:
            uuid = resp.get('uuid', '---')
            status = resp.get('status', 'SENT')
            msg = resp.get('message', '')
            
            # Save to DB (Log)
            try:
                self.db.cursor.execute(
                    "INSERT INTO e_invoices (uuid, status, receiver_name, json_data) VALUES (?, ?, ?, ?)",
                    (
                        uuid,
                        status,
                        self.cmb_customer.currentText(),
                        json.dumps({"message": msg, "response": resp}, ensure_ascii=False),
                    ),
                )
                self.db.conn.commit()
            except Exception as e:
                logger.error(f"InvoiceCreationPage e-invoice insert error: {e}")
                
            try:
                # --- FINANSAL TETİKLEYİCİ (TRIGGER) ---
                # Resmi Fatura Kesildi -> Kasaya İşle
                if hasattr(self.db, "add_transaction"):
                    total_amount = float(self.current_total_try or 0.0)
                    desc = f"E-Fatura Geliri ({uuid})"
                    bank_id = self.cmb_bank.currentData()
                    if bank_id == -1: bank_id = None
                    
                    try:
                        self.db.add_transaction_extended(
                            type="Gelir",
                            category="Resmi Fatura",
                            amount=total_amount,
                            description=desc,
                            date=datetime.now().strftime("%Y-%m-%d"),
                            customer_name=self.cmb_customer.currentText(),
                            bank_account_id=bank_id
                        )
                    except Exception:
                        self.db.add_transaction(
                            t_type="Gelir",
                            category="Resmi Fatura",
                            amount=total_amount,
                            description=desc,
                            customer_name=self.cmb_customer.currentText()
                        )
            except Exception as e: 
                logger.error(f"InvoiceCreationPage finance trigger error: {e}")
            
            QMessageBox.information(self, "Başarılı", f"Fatura GİB'e iletildi!\nETTN: {uuid}\nDurum: {status}")
        else:
            QMessageBox.critical(self, "Hata", f"Gönderim Başarısız:\n{resp.get('detail', 'Bilinmeyen Hata')}")

