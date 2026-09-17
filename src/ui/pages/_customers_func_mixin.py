# -*- coding: utf-8 -*-

import os
import csv
import webbrowser
import logging
from datetime import datetime
from PyQt6.QtWidgets import QFileDialog, QApplication, QWidget, QVBoxLayout, QTextBrowser
from PyQt6.QtCore import Qt, QTimer, QDate

from src.utils.logger import logger
from src.utils.toast_notification import show_success, show_error, show_warning, show_info
from src.utils.currency_helper import CurrencyHelper
from src.utils.date_formatter import format_date
from src.utils.system_config import SystemConfig
from src.utils.design_system import DesignTokens
from src.utils.performance_monitor import perf_span
from src.utils.theme_colors import theme_qss, tc
from src.ui.dialogs.customer_360_dialog import Customer360Dialog
from src.ui.dialogs.service_invoice_dialog import ServiceInvoiceDialog
from src.ui.dialogs.tahsilat_dialog import TahsilatDialog
from src.ui.dialogs.unified_documents_center_dialog import UnifiedDocumentsCenterDialog
from src.ui.pages.customers.logic.export_manager import ExportManager
from src.ui.widgets.modern_confirm_dialog import ModernConfirmDialog

class CustomersFuncMixin:
    """Core functional actions for CustomersPage (CRUD, Payments, Communication, Export)."""

    def _emit_financial_data_changed(self):
        main_window = getattr(self, "main_window", None) or self.window()
        if main_window and hasattr(main_window, "financial_data_changed"):
            try:
                main_window.financial_data_changed.emit()
            except Exception:
                pass

    def open_customer_360(self, customer):
        try:
            def _open():
                with perf_span("dialog.open.Customer360Dialog"):
                    dlg = Customer360Dialog(self.db, customer["id"], customer["name"], self)
                dlg.exec()
            QTimer.singleShot(0, _open)
        except Exception as e:
            show_error(self, f"Müşteri 360 açılamadı: {str(e)}")

    def on_table_double_click(self, row, column):
        if row < 0: return
        customer = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if not customer: return
        if column == 5:
            self.show_history(customer)
        else:
            self.open_customer_360(customer)

    def open_documents_center(self):
        UnifiedDocumentsCenterDialog(self.db, None, self).exec()

    def import_customers(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "M\u00fc\u015fteri I\u00e7e Aktar",
            "",
            "Excel ve CSV (*.xlsx *.xlsm *.csv);;T\u00fcm Dosyalar (*.*)",
        )
        if not file_path:
            return
        from src.ui.dialogs.customer_import_dialog import CustomerImportDialog

        dialog = CustomerImportDialog(self.db, file_path, self)
        if dialog.exec():
            self.request_reload()
            self._emit_financial_data_changed()

    def add_customer(self):
        sector_manager = getattr(self.main_window, "sector_manager", None)
        if self._is_automotive():
            from src.ui.dialogs.automotive_customer_dialog import AutomotiveCustomerDialog as dialog_cls
        else:
            from src.ui.dialogs.technical_service_customer_dialog import TechnicalServiceCustomerDialog as dialog_cls
        if dialog_cls(self.db, self, sector_manager=sector_manager).exec():
            self.request_reload()
            if self.main_window and hasattr(self.main_window, "refresh_loaded_page"):
                self.main_window.refresh_loaded_page(40)

    def edit_customer(self, c):
        sector_manager = getattr(self.main_window, "sector_manager", None)
        if self._is_automotive():
            from src.ui.dialogs.automotive_customer_dialog import AutomotiveCustomerDialog as dialog_cls
        else:
            from src.ui.dialogs.technical_service_customer_dialog import TechnicalServiceCustomerDialog as dialog_cls
        if dialog_cls(self.db, self, c, sector_manager=sector_manager).exec():
            self.request_reload()

    def send_whatsapp(self, c):
        phone = "".join(filter(str.isdigit, str(c["phone"])))
        if phone:
            if phone.startswith("0"): phone = "9" + phone
            webbrowser.open(f"https://wa.me/{phone}")

    def send_debt_reminder(self, c):
        balance = self.db.get_customer_balance(c["id"])
        if balance <= 0:
            show_info(self, "Müşterinin borcu bulunmamaktadır. ✅")
            return
        phone = "".join(filter(str.isdigit, str(c["phone"])))
        if not phone:
            show_error(self, "Müşterinin telefon numarası kayıtlı değil. ❌")
            return
        if phone.startswith("0") and len(phone) == 11: phone = "9" + phone
        elif len(phone) == 10: phone = "90" + phone
        formatted_balance = CurrencyHelper.format_try_for_display(balance, db=self.db, include_try_reference=False)
        message = (f"Sayın *{c['name']}*,\n\nGüncel borç bakiyeniz: *{formatted_balance}*'dir.\n\n"
                   "Ödemenizi rica eder, iyi çalışmalar dileriz. 🙏\n\n*AYEC Pro*")
        import urllib.parse
        webbrowser.open(f"https://wa.me/{phone}?text={urllib.parse.quote(message)}")

    def copy_list(self):
        text = ""
        for r in range(self.table.rowCount()):
            text += "\t".join([self.table.item(r, i).text() for i in range(7)]) + "\n"
        QApplication.clipboard().setText(text)
        show_info(self, "Liste panoya kopyalandı.")

    def export_csv(self):
        customers = self.db.get_customers()
        success, msg = ExportManager.export_to_csv(customers, self)
        if success: show_success(self, msg)
        else: show_error(self, msg)

    def show_history(self, c):
        try:
            dlg = Customer360Dialog(self.db, c["id"], c["name"], self)
            if hasattr(dlg, "tabs"): dlg.tabs.setCurrentIndex(1)
            dlg.exec()
        except Exception as e:
            show_error(self, f"Cari geçmiş açılamadı: {e}")

    def record_payment(self, c):
        dlg = TahsilatDialog(self, self.db, c)
        if dlg.exec():
            data = dlg.get_data()
            if data:
                items = data.get("selected_services") or []
                parts = []
                for it in items:
                    kind = it.get("kind")
                    if kind == "device":
                        tn = it.get("tracking_no") or ""; desc = it.get("description") or ""
                        label = f"Servis {tn}".strip()
                        if desc: label = f"{label} - {desc}"
                        parts.append(label)
                    elif kind == "service":
                        sid = it.get("service_id"); desc = it.get("description") or ""
                        label = f"Hizmet #{sid}" if sid else "Hizmet"
                        if desc: label = f"{label} - {desc}"
                        parts.append(label)
                    elif kind == "currency_txn":
                        tid = it.get("currency_txn_id")
                        label = f"Döviz İşlem #{tid}" if tid else "Döviz İşlem"
                        parts.append(label)
                    elif kind == "balance":
                        parts.append("Cari Borç Kapatma")

                jobs_text = ", ".join(parts[:5])
                base_desc = data["notes"].strip() if data.get("notes") else ""
                full_desc = f"{base_desc} | {jobs_text}" if jobs_text and base_desc else jobs_text or base_desc or f"{data['method']} ile ödeme"

                currency = data.get("currency", "TRY")
                exchange_rate = data.get("exchange_rate", 1.0) if currency != "TRY" else 1.0
                bank_account_id = data.get("bank_account_id")
                payment_method = data.get("method")
                date_value = data.get("date")
                if date_value:
                    d = QDate.fromString(date_value, "dd.MM.yyyy")
                    if d.isValid(): date_value = d.toString("yyyy-MM-dd")

                reference_tracking = data.get("reference_tracking_no")
                reference_desc = (data.get("reference_desc") or "").strip()
                if reference_tracking and reference_desc and reference_desc not in full_desc:
                    full_desc = f"{full_desc} | {reference_desc}"

                try:
                    self.db.create_payment_debt_links_table()
                except Exception: pass

                res = self.db.add_currency_transaction(
                    customer_id=c["id"], amount=data["amount"], currency=currency,
                    transaction_type="CREDIT", exchange_rate=exchange_rate, description=full_desc,
                    tracking_no=reference_tracking, created_at=None
                )

                if res:
                    payment_txn_id = self.db.get_last_currency_transaction_id()
                    selected_debt_ids = data.get("selected_debt_ids", [])
                    debt_allocation = {"linked_debts": [], "remaining": data["amount"]}
                    if payment_txn_id:
                        debt_allocation = self.db.apply_payment_to_debts(
                            customer_id=c["id"], payment_amount=data["amount"], currency=currency,
                            payment_transaction_id=payment_txn_id, selected_debt_ids=selected_debt_ids or None
                        )
                    try:
                        self.db.add_transaction(
                            t_type="Gelir", category="Tahsilat", amount=float(data["amount"]) * exchange_rate,
                            description=full_desc, customer_name=c.get("name"), customer_id=c["id"],
                            date=date_value, payment_method=payment_method, bank_account_id=bank_account_id,
                            tracking_no=reference_tracking, ref_no=reference_tracking, currency=currency,
                            original_amount=float(data["amount"])
                        )
                    except Exception: pass

                    success_msg = f"{CurrencyHelper.format_amount(data['amount'], currency_code=currency)} tahsilat kaydedildi."
                    if debt_allocation["linked_debts"]:
                        success_msg += f"\n{len(debt_allocation['linked_debts'])} borç kalemine dağıtıldı."
                    if debt_allocation["remaining"] > 0.01:
                        success_msg += f"\n{CurrencyHelper.format_amount(debt_allocation['remaining'], currency_code=currency)} cari hesaba işlendi."
                    show_success(self, success_msg + "\nM\u00fc\u015fteri bakiyesi g\u00fcncellendi.")
                    try:
                        from src.utils.asistan_motoru import sesli_cevap_ver_async
                        sesli_cevap_ver_async("\u00d6deme al\u0131nd\u0131.")
                    except Exception:
                        pass
                    self._emit_financial_data_changed()
                    self.request_reload()
                    if self.main_window and hasattr(self.main_window, "refresh_loaded_page"):
                        for pid in (101, 105, 106): self.main_window.refresh_loaded_page(pid)
                else:
                    show_error(self, "Ödeme kaydedilirken bir hata oluştu.")

    def create_service(self, c):
        sector_manager = getattr(self.main_window, "sector_manager", None)
        if self._is_automotive():
            from src.ui.dialogs.automotive_new_service_dialog import AutomotiveNewServiceDialog as dialog_cls
            dialog_cls(self.db, self, customer_name=c["name"], sector_manager=sector_manager).exec()
        else:
            from src.ui.dialogs.add_device_dialog import AddDeviceDialog
            AddDeviceDialog(self.db, self, customer_name=c["name"]).exec()

    def create_invoice(self, c):
        if ServiceInvoiceDialog(self.db, c["id"], self).exec():
            show_success(self, "Fatura başarıyla oluşturuldu ve işlemler işaretlendi.")
            self.request_reload()

    def export_excel(self):
        customers = self.db.get_customers()
        success, msg = ExportManager.export_to_excel(customers, self)
        if success: show_success(self, msg)
        else: show_error(self, msg)

    def print_list(self):
        try:
            from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
            from PyQt6.QtGui import QTextDocument
            headers = [self.table.horizontalHeaderItem(i).text() for i in range(7)]
            html = "<html><head><meta charset='utf-8'></head><body><h2>Müşteri Listesi</h2><table border='1' cellspacing='0' cellpadding='4' width='100%'><tr>"
            for h in headers: html += f"<th>{h}</th>"
            html += "</tr>"
            for r in range(self.table.rowCount()):
                html += "<tr>"
                for c in range(7): html += f"<td>{self.table.item(r, c).text() if self.table.item(r, c) else ''}</td>"
                html += "</tr>"
            html += "</table></body></html>"
            printer = QPrinter(); dlg = QPrintDialog(printer, self)
            if dlg.exec() == QPrintDialog.DialogCode.Accepted:
                doc = QTextDocument(); doc.setHtml(html); doc.print(printer)
                show_success(self, "Yazdırma kuyruğuna gönderildi.")
        except Exception as e: show_error(self, f"Yazdırma hatası: {e}")

    def setup_usage_guide_tab(self):
        ly = QVBoxLayout(self.tab_guide); ly.setContentsMargins(0, 10, 0, 0)
        guide_text = QTextBrowser()
        guide_text.setStyleSheet(theme_qss("border: none; background: transparent; color: @text; padding: 20px;"))
        html_content = f"""
        <div style="font-family: {DesignTokens.FONT_FAMILY}; color: {tc('text')};">
            <h1 style="color: {tc('accent')};">🤝 Müşteri & İlişki Yönetimi (CRM) Kullanım Kılavuzu</h1>
            <p>Bu modül, müşterilerinizin, bayilerinizin ve tedarikçilerinizin bilgilerini merkezi bir yerde toplar, bakiye ve işlem takibi yapmanızı sağlar.</p>
            <h2 style="color: {tc('primary')};">1. Müşteri Listesi ve Kartlar</h2>
            <ul><li><b>Hızlı Filtre:</b> Üstteki renkli butonlar ile sadece Borçlu Müşterileri veya Bayileri listeleyebilirsiniz.</li><li><b>Arama:</b> İsim, Telefon veya E-posta girerek anında arama yapabilirsiniz.</li></ul>
            <h2 style="color: {tc('primary')};">2. İşlemler ve Cari Takibi</h2>
            <ul><li><b>İşlem Yap:</b> Tablonun en sağındaki buton veya sağ tık menüsü ile müşteriye Ödeme Alabilir, Fatura Kesebilir veya Servis Kaydı açabilirsiniz.</li><li><b>Müşteri 360°:</b> Müşteriye çift tıklayarak tüm servis geçmişini, ödemelerini ve notlarını görebilirsiniz.</li></ul>
            <h2 style="color: {tc('primary')};">3. İletişim Araçları</h2>
            <ul><li><b>WhatsApp:</b> Tek tıkla mesaj gönderebilir veya bakiye hatırlatması yapabilirsiniz.</li></ul>
        </div>
        """
        guide_text.setHtml(html_content); ly.addWidget(guide_text)

    def export_pdf(self):
        try:
            from src.ui.utils.background_task import run_cancellable_task

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
                        self.table.item(r, c).text()
                        if self.table.item(r, c)
                        else ""
                        for c in range(7)
                    ]
                )
            text_color = tc("text")
            selection_text = tc("selection_text")

            def produce_pdf(is_cancelled):
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

                if is_cancelled():
                    return None
                doc = SimpleDocTemplate(path, pagesize=landscape(A4))
                styles = getSampleStyleSheet()
                story = [
                    Paragraph("M\u00fc\u015fteri Listesi", styles["Heading1"]),
                    Spacer(1, 12),
                ]
                table = Table(data, repeatRows=1)
                table.setStyle(
                    TableStyle(
                        [
                            (
                                "BACKGROUND",
                                (0, 0),
                                (-1, 0),
                                colors.HexColor(text_color),
                            ),
                            (
                                "TEXTCOLOR",
                                (0, 0),
                                (-1, 0),
                                colors.HexColor(selection_text),
                            ),
                            (
                                "GRID",
                                (0, 0),
                                (-1, -1),
                                0.25,
                                colors.lightgrey,
                            ),
                        ]
                    )
                )
                story.append(table)
                doc.build(story)
                return path

            def pdf_ready(result_path):
                if not result_path:
                    return
                show_success(self, "PDF dosyas\u0131 olu\u015fturuldu.")
                try:
                    os.startfile(result_path)
                except OSError:
                    pass

            run_cancellable_task(
                owner=self,
                title="Musteri listesi PDF olusturuluyor",
                target=produce_pdf,
                on_success=pdf_ready,
                on_error=lambda message: show_error(
                    self,
                    f"PDF aktar\u0131m hatas\u0131: {message}",
                ),
                output_path=path,
            )
        except Exception as e:
            show_error(self, f"PDF aktar\u0131m hatas\u0131: {e}")

    def delete_customer(self, c):
        dlg = ModernConfirmDialog("Silme Onayı", f"'{c['name']}' isimli müşteriyi silmek istediğinize emin misiniz\n\nBu işlem geri alınamaz!", self, confirm_text="Evet, Sil", destructive=True)
        if dlg.exec() == ModernConfirmDialog.DialogCode.Accepted if hasattr(ModernConfirmDialog, "DialogCode") else 1:
            try:
                if self.db.delete_customer(c["id"]):
                    self.db.conn.commit(); self.request_reload(); show_success(self, f"'{c['name']}' silindi.")
                else: show_error(self, "Müşteri silinemedi.")
            except Exception as e: show_error(self, f"Silme hatası: {str(e)}")

    def export_selected_csv(self):
        rows = self._selected_customer_rows()
        if not rows: show_warning(self, "Dışa aktarmak için en az bir müşteri seçin."); return
        customers = []
        for row in rows:
            item = self.table.item(row, 0)
            if item:
                customer = item.data(Qt.ItemDataRole.UserRole)
                if customer: customers.append(customer)
        if not customers: show_warning(self, "Seçili müşteri kayıtları bulunamadı."); return
        success, msg = ExportManager.export_to_csv(customers, self)
        if success: show_success(self, msg)
        else: show_error(self, msg)
