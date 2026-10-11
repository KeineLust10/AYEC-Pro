# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
                             QComboBox, QLineEdit, QTableWidget, QTableWidgetItem, QPushButton,
                             QLabel, QFrame, QHeaderView, QSizePolicy, QFileDialog, QDialog,
                             QInputDialog, QMessageBox, QTextBrowser)
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
import uuid
from html import escape as html_escape


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
        self.setWindowTitle("AYEC Pro | E-Fatura Olu\u015ftur")
        from src.ui.pages.invoice_composer_ui import build_invoice_composer

        build_invoice_composer(self)
        self.on_currency_change()
        self.add_row()
        self.calculate_totals()

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
        self.items_table.blockSignals(True)
        self.items_table.insertRow(row)
        values = (
            f"{row + 1:02d}", "Hizmet", "", "1", "Adet", "0.00", "0.0",
            f"{TaxSettings.get_percent(self.db):g}", "0.00", "0.00",
        )
        for column, value in enumerate(values):
            item = QTableWidgetItem(value)
            if column in (0, 8, 9):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.items_table.setItem(row, column, item)
        remove_button = QPushButton("\u00d7")
        remove_button.setToolTip("Sat\u0131r\u0131 sil")
        remove_button.setProperty("invoice_row", row)
        remove_button.clicked.connect(
            lambda _checked=False, button=remove_button: self.remove_row(button.property("invoice_row"))
        )
        remove_button.setStyleSheet(theme_qss(
            "QPushButton { color: @danger; background: transparent; border: none; font-size: 16px; }"
        ))
        self.items_table.setCellWidget(row, 10, remove_button)
        self.items_table.blockSignals(False)
        self.calculate_totals()

    def remove_row(self, row=None):
        row_index = self.items_table.currentRow() if row is None else int(row)
        if 0 <= row_index < self.items_table.rowCount():
            self.items_table.removeRow(row_index)
            for index in range(self.items_table.rowCount()):
                self.items_table.item(index, 0).setText(f"{index + 1:02d}")
                button = self.items_table.cellWidget(index, 10)
                if button is not None:
                    button.setProperty("invoice_row", index)
            self.calculate_totals()

    def get_float(self, row, col):
        try:
            item = self.items_table.item(row, col)
            return float(item.text().replace(",", ".")) if item else 0.0
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def get_float_from_text(value):
        try:
            return float(str(value or "").replace(",", ".").strip())
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _format_invoice_amount(amount, db, currency):
        code = str(currency or "TRY").upper()
        value = float(amount or 0)
        formatted = CurrencyHelper.format_amount(abs(value), db=db, currency_code=code)
        symbol = CurrencyHelper.get_symbol(db, code)
        suffix = " " + symbol
        number = formatted[:-len(suffix)] if formatted.endswith(suffix) else formatted
        if code in {"USD", "EUR"}:
            sign = "-" if value < 0 else ""
            return f"{sign}{symbol}{number}"
        return ("-" if value < 0 else "") + formatted

    def calculate_totals(self):
        if not hasattr(self, "items_table"):
            return
        subtotal = 0.0
        discount_total = 0.0
        vat_total = 0.0
        units_total = 0.0
        discounted_rows = 0
        self.items_table.blockSignals(True)
        for row in range(self.items_table.rowCount()):
            quantity = self.get_float(row, 3)
            unit_price = self.get_float(row, 5)
            discount_rate = min(max(self.get_float(row, 6), 0.0), 100.0)
            vat_rate = max(self.get_float(row, 7), 0.0)
            gross = quantity * unit_price
            discount = gross * discount_rate / 100.0
            taxable = gross - discount
            vat = taxable * vat_rate / 100.0
            total = taxable + vat
            self.items_table.setItem(row, 8, QTableWidgetItem(f"{vat:.2f}"))
            self.items_table.setItem(row, 9, QTableWidgetItem(f"{total:.2f}"))
            for column in (8, 9):
                item = self.items_table.item(row, column)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            subtotal += taxable
            discount_total += discount
            vat_total += vat
            units_total += quantity
            discounted_rows += int(discount_rate > 0)
        self.items_table.blockSignals(False)

        grand_total = subtotal + vat_total
        currency = str(getattr(self, "current_currency_code", "TRY") or "TRY").upper()
        rate = 1.0 if currency == "TRY" else self.get_float_from_text(self.exchange_rate.text())
        if currency != "TRY" and rate <= 0:
            rate = CurrencyHelper._get_rate(self.db, currency)
        self.current_total_try = grand_total * (rate or 0.0)
        self.lbl_subtotal.setText(self._format_invoice_amount(subtotal + discount_total, self.db, currency))
        self.lbl_discount.setText(self._format_invoice_amount(-discount_total, self.db, currency))
        self.lbl_taxable.setText(self._format_invoice_amount(subtotal, self.db, currency))
        self.lbl_vat.setText(self._format_invoice_amount(vat_total, self.db, currency))
        total_text = self._format_invoice_amount(grand_total, self.db, currency)
        if currency in {"USD", "EUR"}:
            total_text += " " + currency
        self.lbl_total.setText(total_text)
        self.lbl_total_try.setText(CurrencyHelper.format_amount(self.current_total_try, db=self.db, currency_code="TRY"))
        self.item_count_label.setText(f"{self.items_table.rowCount()} Kalem Listelendi")
        self.total_units_label.setText(f"Toplam Miktar: {units_total:g} Birim")
        self.discounted_rows_label.setText(f"\u0130skonto Yap\u0131lan Sat\u0131r: {discounted_rows}")
        self.rate_footer_label.setText(f"Para Birimi Kuru: {rate:.4f} {currency}")
        self.summary_currency_badge.setText(f"{currency} / TRY")

    def refresh_financial_defaults(self):
        vat_percent = TaxSettings.get_percent(self.db)
        self.items_table.blockSignals(True)
        try:
            for row in range(self.items_table.rowCount()):
                self.items_table.setItem(row, 7, QTableWidgetItem(f"{vat_percent:g}"))
        finally:
            self.items_table.blockSignals(False)
        self.calculate_totals()

    def on_currency_change(self, *_args):
        code = str(self.currency_select.currentData() or "TRY").upper()
        self.current_currency_code = code
        rate = 1.0 if code == "TRY" else CurrencyHelper._get_rate(self.db, code)
        self.exchange_rate.setText(f"{rate:.4f}" if rate > 0 else "0.0000")
        self.summary_currency_badge.setText(f"{code} / TRY")
        if hasattr(self, "items_table"):
            self.calculate_totals()

    def send_invoice(self):
        cust_name = self.cmb_customer.currentText()
        if not cust_name:
            show_warning(self, "Hata", "L\u00fctfen m\u00fc\u015fteri se\u00e7in.")
            return
        try:
            json_payload = self.mapper.to_json(self.build_invoice_data())
            self.btn_send.setEnabled(False)
            self.btn_send.setText("G\u00f6nderiliyor...")
            self.worker = InvoiceSenderThread(self.client, json_payload)
            self.worker.finished.connect(self.on_send_finished)
            self.worker.start()
        except Exception as e:
            show_error(self, "Veri Hatas\u0131", f"Fatura olu\u015fturulamad\u0131:\n{e}")

    def build_invoice_data(self):
        items = []
        for row in range(self.items_table.rowCount()):
            name_item = self.items_table.item(row, 1)
            name = name_item.text().strip() if name_item else ""
            if not name:
                continue
            items.append({
                "name": name,
                "stock_code": self.items_table.item(row, 2).text() if self.items_table.item(row, 2) else "",
                "quantity": self.get_float(row, 3),
                "unit": self.items_table.item(row, 4).text() if self.items_table.item(row, 4) else "Adet",
                "unit_price": self.get_float(row, 5),
                "discount_rate": self.get_float(row, 6),
                "vat_rate": self.get_float(row, 7),
            })
        return {
            "receiver": {
                "name": self.cmb_customer.currentText(),
                "tax_id": self.inp_vkn.text(),
                "tax_office": self.tax_office.text(),
                "address": self.inp_addr.text(),
                "email": "",
            },
            "items": items,
            "currency": self.current_currency_code,
            "currency_rate": self.get_float_from_text(self.exchange_rate.text()),
            "invoice_date": self.invoice_date.date().toString("yyyy-MM-dd"),
            "invoice_time": self.invoice_time.time().toString("HH:mm"),
            "scenario": self.invoice_scenario.currentText(),
            "type": self.invoice_type.currentText().split(" ")[0],
            "dispatch_reference": self.inp_delivery_reference.text(),
            "notes": self.invoice_notes.toPlainText(),
            "order_reference": self.inp_order_reference.text(),
            "due_date": self.due_date.date().toString("yyyy-MM-dd"),
            "payment_channel": self.payment_channel.currentText(),
            "bank_account_id": self.cmb_bank.currentData(),
            "auto_reconcile": self.chk_auto_reconcile.isChecked(),
        }

    def open_linked_order_picker(self):
        value, accepted = QInputDialog.getText(
            self,
            "\u0130rsaliye / Sipari\u015f Referans\u0131",
            "Ba\u011fl\u0131 belge numaras\u0131n\u0131 girin:",
            text=self.inp_delivery_reference.text(),
        )
        if accepted:
            self.inp_delivery_reference.setText(value.strip())

    def _invoice_preview_text(self):
        data = self.build_invoice_data()
        lines = [
            "E-FATURA TASLAK \u00d6N\u0130ZLEMES\u0130",
            f"M\u00fc\u015fteri: {data['receiver']['name']}",
            f"VKN/TCKN: {data['receiver']['tax_id']}",
            f"Tarih: {data['invoice_date']} {data['invoice_time']}",
            f"Senaryo / Tip: {data['scenario']} / {data['type']}",
            "",
        ]
        for index, item in enumerate(data["items"], 1):
            lines.append(
                f"{index:02d}. {item['name']} | {item['quantity']:g} {item['unit']} | "
                f"{item['unit_price']:.2f} {data['currency']} | KDV %{item['vat_rate']:g}"
            )
        lines.extend(["", f"Toplam: {self.lbl_total.text()}", f"Not: {data['notes']}"])
        return "\n".join(lines)

    def preview_invoice(self):
        QMessageBox.information(self, "PDF G\u00f6r", self._invoice_preview_text())

    def save_draft(self):
        try:
            payload = self.mapper.to_json(self.build_invoice_data())
            draft_id = f"DRAFT-{uuid.uuid4()}"
            self.db.cursor.execute(
                "INSERT INTO e_invoices (uuid, status, receiver_name, json_data) VALUES (?, ?, ?, ?)",
                (draft_id, "DRAFT", self.cmb_customer.currentText(), json.dumps(payload, ensure_ascii=True)),
            )
            self.db.conn.commit()
            show_success(self, "Taslak Kaydedildi", f"Taslak belge: {draft_id}")
        except Exception as exc:
            show_error(self, "Taslak Kaydedilemedi", str(exc))

    def export_proforma(self):
        path, _selected = QFileDialog.getSaveFileName(
            self, "Proforma PDF Kaydet", "proforma.pdf", "PDF Files (*.pdf)"
        )
        if not path:
            return
        try:
            from PyQt6.QtPrintSupport import QPrinter
            from PyQt6.QtGui import QTextDocument

            document = QTextDocument()
            body = "<br>".join(html_escape(line) for line in self._invoice_preview_text().splitlines())
            document.setHtml(f"<h2>Proforma Fatura</h2><p>{body}</p>")
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(path)
            document.print(printer)
            show_success(self, "Proforma Haz\u0131r", f"PDF kaydedildi: {path}")
        except Exception as exc:
            show_error(self, "PDF Olu\u015fturulamad\u0131", str(exc))

    def on_send_finished(self, success, resp):
        self.btn_send.setEnabled(True)
        self.btn_send.setText("E-Faturay\u0131 Resmile\u015ftir ve G\u00f6nder (F12)")
        
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
                if self.chk_auto_reconcile.isChecked() and hasattr(self.db, "add_transaction"):
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
