# -*- coding: utf-8 -*-

import html

import pandas as pd
from datetime import datetime
from PyQt6.QtCore import QDate
from PyQt6.QtGui import QPageLayout, QTextDocument
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
from PyQt6.QtWidgets import QFileDialog
from src.ui.dialogs.customer_select_dialog import CustomerSelectDialog
from src.ui.dialogs.tahsilat_dialog import TahsilatDialog
from src.ui.pages.accounting_dialogs import AddExpenseDialog, AddIncomeDialog, AddTransferDialog, TaxAnalysisDialog
from src.utils.currency_helper import CurrencyHelper
from src.utils.toast_notification import show_warning, show_info, show_success

class AccountingFuncMixin:
    def _emit_financial_data_changed(self):
        main_window = getattr(self, "main_window", None) or self.window()
        if main_window and hasattr(main_window, "financial_data_changed"):
            try:
                main_window.financial_data_changed.emit()
            except Exception:
                pass

    def open_tax_dialog(self):
        TaxAnalysisDialog(self.finance_manager, self).exec()

    def open_collection_dialog(self):
        picker = CustomerSelectDialog(self.db, self)
        if not picker.exec() or not picker.selected_customer: return
        sel = picker.selected_customer
        customer = {"id": sel[0], "name": sel[1], "phone": sel[2] if len(sel) > 2 else ""}
        if not customer.get("id"): show_warning(self, "Geçerli bir müşteri seçilemedi."); return
        dlg = TahsilatDialog(self, self.db, customer)
        if not dlg.exec(): return
        data = dlg.get_data() or {}
        try:
            curr = str(data.get("currency") or CurrencyHelper.get_code(self.db) or "TRY").upper()
            rate, amt = float(data.get("exchange_rate", 1.0) or 1.0), float(data.get("amount", 0) or 0)
            if amt <= 0: show_warning(self, "Tahsilat tutarı geçersiz."); return
            acc_date, c_at = None, None
            if data.get("date"):
                p = QDate.fromString(str(data.get("date")), "dd.MM.yyyy")
                if p.isValid(): acc_date = p.toString("yyyy-MM-dd"); c_at = f"{acc_date} {datetime.now().strftime('%H:%M:%S')}"
            ref_tr, ref_ds = data.get("reference_tracking_no") or None, (data.get("reference_desc") or "").strip()
            full_ds = (data.get("notes") or "").strip() or "Cari borç kapatma tahsilatı"
            if ref_tr: full_ds = f"Ref: {ref_tr} | {full_ds}"
            if ref_ds and ref_ds not in full_ds: full_ds = f"{full_ds} | {ref_ds}"
            try: self.db.create_payment_debt_links_table()
            except: pass
            saved = self.db.add_currency_transaction(customer_id=customer["id"], amount=amt, currency=curr, transaction_type="CREDIT", exchange_rate=rate, description=full_ds, tracking_no=ref_tr, created_at=c_at, commit=False)
            if not saved: show_warning(self, "Tahsilat kaydedilirken bir hata oluştu."); return
            try:
                pid = self.db.get_last_currency_transaction_id()
                if pid: self.db.apply_payment_to_debts(customer_id=customer["id"], payment_amount=amt, currency=curr, payment_transaction_id=pid, selected_debt_ids=data.get("selected_debt_ids") or None, commit=False)
            except Exception:
                self.db.conn.rollback()
                raise
            tl_amt = amt * (rate if curr != "TRY" else 1.0)
            accounting_id = self.db.add_transaction(t_type="Gelir", category="Tahsilat", amount=tl_amt, description=full_ds, customer_name=customer.get("name"), customer_id=customer["id"], date=acc_date, payment_method=data.get("method"), bank_account_id=data.get("bank_account_id"), tracking_no=ref_tr, ref_no=ref_tr, currency=curr, original_amount=amt, commit=False)
            if not accounting_id:
                raise RuntimeError("Muhasebe kaydi olusturulamadi")
            self.db.conn.commit()
            show_success(self, "Tahsilat ba\u015far\u0131yla kaydedildi.")
            try:
                from src.utils.asistan_motoru import sesli_cevap_ver_async
                sesli_cevap_ver_async("\u00d6deme al\u0131nd\u0131.")
            except Exception:
                pass
            self._emit_financial_data_changed()
            self.refresh_data()
        except Exception as exc: show_warning(self, f"Tahsilat kaydı sırasında hata oluştu: {exc}")

    def open_income_dialog(self):
        if AddIncomeDialog(self.db, self).exec(): self.refresh_data()

    def open_expense_dialog(self):
        if AddExpenseDialog(self.db, self).exec(): self.refresh_data()

    def open_transfer_dialog(self):
        if AddTransferDialog(self.db, self).exec(): self.refresh_data()

    def export_to_excel(self):
        rows = self._collect_ledger_export_rows()
        if not rows: show_warning(self, "Dışa aktarılacak hareket bulunamadı."); return
        try:
            path, _ = QFileDialog.getSaveFileName(self, "Cari Hareketleri Kaydet", "cari_hareketler.xlsx", "Excel Dosyası (*.xlsx)")
            if not path: return
            pd.DataFrame(rows).to_excel(path, index=False); show_success(self, "Cari hareketler dışa aktarıldı.")
        except Exception as e: show_warning(self, f"Excel aktarım hatası: {e}")

    def _collect_ledger_export_rows(self):
        manager = getattr(self, "finance_manager", None)
        if manager is not None and hasattr(manager, "get_unified_ledger"):
            source_rows = manager.get_unified_ledger(limit=100000)
        else:
            source_rows = list(getattr(self, "ledger_data", []) or [])

        export_rows = []
        for row in source_rows:
            currency = str(row.get("currency") or "TRY").upper()
            original_amount = row.get("amount")
            amount_try = row.get("amount_try")
            export_rows.append(
                {
                    "Kayit ID": row.get("id") or "",
                    "Kaynak": row.get("source") or "",
                    "Tarih": row.get("date") or "",
                    "Islem Turu": row.get("type_label") or "",
                    "Aciklama": row.get("description") or "",
                    "Musteri": row.get("customer_name") or "",
                    "Orijinal Tutar": float(original_amount or 0),
                    "Para Birimi": currency,
                    "Doviz Kuru": float(row.get("rate") or 1),
                    "TRY Karsiligi": float(amount_try or 0),
                    "Odeme Yontemi": row.get("payment_method") or "",
                    "Takip No": row.get("tracking_no") or "",
                    "Referans": row.get("ref_no") or "",
                    "Urun Hizmet ID": row.get("product_service_id") or "",
                    "Urun Hizmet Turu": row.get("product_service_type") or "",
                    "Durum": row.get("status") or "",
                }
            )
        return export_rows

    def export_to_pdf(self):
        rows = self._collect_ledger_export_rows()
        if not rows: show_warning(self, "PDF için hareket bulunamadı."); return
        try:
            path, _ = QFileDialog.getSaveFileName(self, "Cari Hareketleri PDF Kaydet", "cari_hareketler.pdf", "PDF Dosyası (*.pdf)")
            if not path: return
            printer = QPrinter(QPrinter.PrinterMode.HighResolution); printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat); printer.setOutputFileName(path)
            printer.setPageOrientation(QPageLayout.Orientation.Landscape)
            doc = QTextDocument(); doc.setHtml(self._build_ledger_html()); doc.print(printer); show_success(self, "Cari hareket PDF'i oluşturuldu.")
        except Exception as e: show_warning(self, f"PDF oluşturma hatası: {e}")

    def print_ledger(self):
        rows = self._collect_ledger_export_rows()
        if not rows: show_warning(self, "Yazdırılacak hareket bulunamadı."); return
        try:
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setPageOrientation(QPageLayout.Orientation.Landscape)
            if QPrintDialog(printer, self).exec() != QPrintDialog.DialogCode.Accepted: return
            doc = QTextDocument(); doc.setHtml(self._build_ledger_html()); doc.print(printer); show_info(self, "Cari hareketler yazdırmaya gönderildi.")
        except Exception as e: show_warning(self, f"Yazdırma hatası: {e}")

    def _collect_ledger_rows(self):
        headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
        rows = []
        for row in range(self.table.rowCount()):
            payload = {}
            for col, header in enumerate(headers):
                item = self.table.item(row, col); payload[header] = item.text() if item else ""
            rows.append(payload)
        return rows

    def _build_ledger_html(self):
        rows = self._collect_ledger_export_rows()
        headers = [
            "Tarih",
            "Islem Turu",
            "Aciklama",
            "Musteri",
            "Orijinal Tutar",
            "Para Birimi",
            "Doviz Kuru",
            "TRY Karsiligi",
            "Odeme Yontemi",
            "Referans",
            "Durum",
        ]
        header_html = "".join(
            "<th>{}</th>".format(html.escape(str(header))) for header in headers
        )
        body_html = []
        for row in rows:
            cells = "".join(
                "<td>{}</td>".format(html.escape(str(row.get(header, ""))))
                for header in headers
            )
            body_html.append("<tr>{}</tr>".format(cells))
        return (
            "<html><head><meta charset='UTF-8'><style>"
            "body{{font-family:'Segoe UI',Arial,sans-serif;color:#172033;}}"
            "h2{{margin:0 0 5px 0;}}p{{margin:0 0 12px 0;}}"
            "table{{width:100%;border-collapse:collapse;font-size:7pt;}}"
            "th{{padding:5px 3px;border:1px solid #cbd5e1;background:#e8eef6;text-align:left;}}"
            "td{{padding:4px 3px;border:1px solid #d9d9d9;vertical-align:top;}}"
            "tr{{page-break-inside:avoid;}}"
            "</style></head><body>"
            "<h2>AYEC Pro - Cari Hareketler / Finansal Defter</h2>"
            "<p>Tarih: {}</p><table><thead><tr>{}</tr></thead><tbody>{}</tbody></table>"
            "</body></html>"
        ).format(
            datetime.now().strftime("%d.%m.%Y %H:%M"),
            header_html,
            "".join(body_html),
        )
