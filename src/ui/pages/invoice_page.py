# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
                             QComboBox, QLineEdit, QTableWidget, QTableWidgetItem, QPushButton,
                             QLabel, QFrame, QHeaderView, QSizePolicy)
from src.utils.theme_colors import theme_qss
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from src.finance.invoice_mapper import InvoiceMapper
from src.api.einvoice_client import EInvoiceClient
from src.utils.logger import logger
from src.utils.toast_notification import show_success, show_error, show_warning
from src.utils.currency_helper import CurrencyHelper
from src.utils.tax_settings import TaxSettings
from src.utils.secure_setting_store import SecureSettingStore
from datetime import datetime
import json


class InvoiceSenderThread(QThread):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
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
        self.client = self._build_einvoice_client()
        
        self.init_ui()
        self.load_customers()

    def _build_einvoice_client(self):
        environment = self.db.get_setting("einvoice_environment", "sandbox")
        return EInvoiceClient(
            api_key=SecureSettingStore.get(self.db, "einvoice_api_key"),
            is_sandbox=environment != "live",
            base_url=self.db.get_setting("einvoice_api_url", ""),
        )

    def init_ui(self):
        self.setWindowTitle("AYEC Pro | E-Fatura Oluştur")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 16, 20, 16)
        self.layout.setSpacing(10)

        page_title = QLabel("E-Fatura Olustur")
        self.page_title = page_title
        page_title.setStyleSheet(theme_qss("font-size: 24px; font-weight: 800; color: @text;"))
        title_row = QHBoxLayout()
        title_row.addWidget(page_title)
        title_row.addStretch(1)
        self.btn_integration = QPushButton("Entegrasyon Ayarlari")
        self.btn_integration.clicked.connect(self.open_integration_settings)
        title_row.addWidget(self.btn_integration)
        self.layout.addLayout(title_row)

        # 1. Müşteri Bilgileri Grubu
        self.client_group = QGroupBox("Müşteri Bilgileri")
        self.client_layout = QFormLayout(self.client_group)
        self.client_layout.setContentsMargins(12, 10, 12, 10)
        self.client_layout.setVerticalSpacing(8)
        
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
        self.items_table.setMinimumHeight(220)
        self.items_table.setMaximumHeight(290)
        self.items_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.items_table.verticalHeader().setDefaultSectionSize(34)
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
        self.total_layout.setContentsMargins(12, 10, 12, 10)
        self.total_layout.setVerticalSpacing(8)
        
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
        
        self.total_panel.setMinimumWidth(300)
        self.total_panel.setMaximumWidth(340)

        top_row = QHBoxLayout()
        top_row.setSpacing(16)
        top_row.addWidget(self.client_group, 1)
        top_row.addWidget(self.total_panel, 0, Qt.AlignmentFlag.AlignTop)
        self.layout.addLayout(top_row)

        self.layout.addWidget(self.items_table, 0)

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
        self.layout.addStretch(1)
        
        # Init with one row
        self.add_row()
        self._normalize_ui_texts()

    def _normalize_ui_texts(self):
        """Repair legacy mojibake strings after widget creation."""
        self.setWindowTitle("AYEC Pro | E-Fatura Olu\u015ftur")
        self.page_title.setText("E-Fatura Olu\u015ftur")
        self.client_group.setTitle("M\u00fc\u015fteri Bilgileri")
        self.cmb_customer.setPlaceholderText("M\u00fc\u015fteri Se\u00e7in...")
        customer_label = self.client_layout.labelForField(self.cmb_customer)
        if customer_label:
            customer_label.setText("M\u00fc\u015fteri Se\u00e7:")
        bank_label = self.total_layout.labelForField(self.cmb_bank)
        if bank_label:
            bank_label.setText("Tahsilat Kasas\u0131:")
        if self.cmb_bank.count() and self.cmb_bank.itemData(0) == -1:
            self.cmb_bank.setItemText(0, "Kasa/Banka Se\u00e7meyin")
        self.btn_add_item.setText("+ Yeni Sat\u0131r Ekle")
        self.btn_remove_item.setText("- Sat\u0131r Sil")
        self.btn_send.setText("\U0001f680 E-Faturay\u0131 Resmile\u015ftir ve G\u00f6nder")
        self.items_table.setHorizontalHeaderLabels(
            ["\u00dcr\u00fcn/Hizmet", "Miktar", "Birim", "Birim Fiyat", "KDV %", "Tutar"]
        )

    def open_integration_settings(self):
        from src.ui.dialogs.einvoice_integration_dialog import EInvoiceIntegrationDialog

        dialog = EInvoiceIntegrationDialog(self.db, self)
        if dialog.exec():
            self.client = self._build_einvoice_client()
            show_success(self, "Kaydedildi", "E-Fatura entegrasyon ayarlari kaydedildi.")

    def showEvent(self, event):
        super().showEvent(event)
        self.load_customers()

    def load_customers(self):
        try:
            cursor = self.db.cursor
            columns = {
                str(row[1]).lower()
                for row in cursor.execute("PRAGMA table_info(customers)").fetchall()
            }
            tax_column = next(
                (name for name in ("tax_number", "tax_no", "tax_id", "tc_no") if name in columns),
                None,
            )
            tax_expr = tax_column if tax_column else "''"
            address_expr = "address" if "address" in columns else "''"
            where_clause = " WHERE COALESCE(is_deleted, 0) = 0" if "is_deleted" in columns else ""
            query = (
                f"SELECT id, name, {tax_expr}, {address_expr} FROM customers"
                f"{where_clause} ORDER BY name COLLATE NOCASE"
            )
            customers = cursor.execute(query).fetchall()

            self.customers_data = {}
            self.cmb_customer.clear()

            for c in customers:
                c_id, name, tax, addr = c
                self.customers_data[c_id] = {'name': name, 'tax': tax, 'addr': addr}
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
        vat_percent = TaxSettings.get_percent(self.db)
        self.items_table.setItem(
            row,
            4,
            QTableWidgetItem(f"{vat_percent:g}"),
        )
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
        self.lbl_subtotal.setText(
            CurrencyHelper.format_try_for_display(subtotal, db=self.db)
        )
        self.lbl_vat.setText(
            CurrencyHelper.format_try_for_display(vat_total, db=self.db)
        )
        self.lbl_total.setText(
            CurrencyHelper.format_try_for_display(grand_total, db=self.db)
        )
        self.items_table.blockSignals(False)

    def refresh_financial_defaults(self):
        vat_percent = TaxSettings.get_percent(self.db)
        self.items_table.blockSignals(True)
        try:
            for row in range(self.items_table.rowCount()):
                self.items_table.setItem(
                    row,
                    4,
                    QTableWidgetItem(f"{vat_percent:g}"),
                )
        finally:
            self.items_table.blockSignals(False)
        self.calculate_totals()

    def send_invoice(self):
        # 1. Gather Data
        cust_name = self.cmb_customer.currentText()
        if not cust_name:
            show_warning(self, "Hata", "L\u00fctfen m\u00fc\u015fteri se\u00e7in.")
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
            show_error(self, "Veri Hatas\u0131", f"Fatura olu\u015fturulamad\u0131:\n{e}")

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

            if self.client.is_sandbox:
                show_success(
                    self,
                    "Test Basarili",
                    f"Sandbox e-fatura testi tamamlandi. Gercek belge gonderilmedi.\nETTN: {uuid}\nDurum: {status}",
                )
                return
                
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
            
            show_success(self, "Ba\u015far\u0131l\u0131", f"Fatura G\u0130B'e iletildi!\nETTN: {uuid}\nDurum: {status}")
        else:
            show_error(self, "Hata", f"G\u00f6nderim ba\u015far\u0131s\u0131z:\n{resp.get('detail', 'Bilinmeyen Hata')}")

    def _wire_ui_signals(self):
        self.cmb_bank.currentIndexChanged.connect(self._on_ui_widget_changed)


# Geriye d\u00f6n\u00fck uyumluluk alias
InvoicePage = InvoiceCreationPage
