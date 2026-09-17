# -*- coding: utf-8 -*-
# _stock_export.py
# Dışa aktarma işlemleri

import csv
from datetime import datetime
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from PyQt6.QtGui import QTextDocument
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
import pandas as pd
from src.utils.currency_helper import CurrencyHelper
from src.utils.toast_notification import (
    show_success,
    show_warning,
    show_error,
)


class StockExportMixin:
    """Dışa aktarma işlemleri için mixin."""

    def export_to_excel(self):
        try:
            default_name = (
                f"yedek_parca_listesi_{datetime.now().strftime('%Y%m%d')}.xlsx"
                if self.is_automotive
                else f"stok_listesi_{datetime.now().strftime('%Y%m%d')}.xlsx"
            )
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Excel Olarak Kaydet",
                default_name,
                "Excel Dosyası (*.xlsx)",
            )
            if not path:
                return

            parts, _ = self.db.get_parts_paginated(limit=100000)
            if not parts:
                show_warning(self, "Dışa aktarılacak veri bulunamadı.")
                return

            dict_parts = self._build_stock_export_rows(parts)
            df = pd.DataFrame(dict_parts)

            if self.is_automotive:
                rename_map = {
                    "id": "ID",
                    "code": "Stok Kodu",
                    "name": "Parça Adı",
                    "brand": "Marka",
                    "category": "Kategori",
                    "oem_code": "OEM Kodu",
                    "equivalent_code": "Muadil Kodu",
                    "compatible_models": "Uyumlu Araç / Motor",
                    "shelf_number": "Raf / Konum",
                    "stock": "Stok",
                    "purchase_price": "Alış Fiyatı",
                    "price": "Satış Fiyatı",
                    "currency": "Para Birimi",
                    "export_exchange_rate": "D\u00f6viz Kuru",
                    "purchase_price_try": "Al\u0131\u015f Fiyat\u0131 (TRY)",
                    "sale_price_try": "Sat\u0131\u015f Fiyat\u0131 (TRY)",
                    "stock_value_original": "Stok De\u011feri (Orijinal)",
                    "stock_value_try": "Stok De\u011feri (TRY)",
                    "min_stock": "Kritik Limit",
                    "description": "Açıklama",
                }
            else:
                rename_map = {
                    "id": "ID",
                    "code": "Barkod",
                    "name": "Ürün Adı",
                    "brand": "Marka",
                    "category": "Kategori",
                    "stock": "Stok",
                    "purchase_price": "Alış Fiyatı",
                    "price": "Satış Fiyatı",
                    "currency": "Birim",
                    "export_exchange_rate": "D\u00f6viz Kuru",
                    "purchase_price_try": "Al\u0131\u015f Fiyat\u0131 (TRY)",
                    "sale_price_try": "Sat\u0131\u015f Fiyat\u0131 (TRY)",
                    "stock_value_original": "Stok De\u011feri (Orijinal)",
                    "stock_value_try": "Stok De\u011feri (TRY)",
                    "shelf_number": "Raf",
                    "description": "Açıklama",
                }
            df = df.rename(columns=rename_map)

            keep_cols = [
                rename_map[k] for k in rename_map if rename_map[k] in df.columns
            ]
            df = df[keep_cols]

            df.to_excel(path, index=False)
            show_success(self, "Veriler başarıyla aktarıldı.")
        except Exception as e:
            from src.utils.logger import logger
            logger.error(f"Excel export failed: {e}")
            show_error(self, f"Dışa aktarma hatası: {e}")

    def _build_stock_export_rows(self, parts):
        export_rows = []
        for part in parts:
            row = dict(part)
            currency = str(row.get("currency") or "TRY").upper()
            rate = float(CurrencyHelper.require_rate(self.db, currency) or 1.0)
            purchase_price = float(row.get("purchase_price") or 0)
            sale_price = float(row.get("price") or 0)
            stock = float(row.get("stock") or 0)
            row["currency"] = currency
            row["export_exchange_rate"] = rate
            row["purchase_price_try"] = round(purchase_price * rate, 2)
            row["sale_price_try"] = round(sale_price * rate, 2)
            row["stock_value_original"] = round(purchase_price * stock, 2)
            row["stock_value_try"] = round(purchase_price * stock * rate, 2)
            export_rows.append(row)
        return export_rows

    def export_selected_stock_to_excel(self):
        rows = sorted({index.row() for index in self.table_stock.selectedIndexes()})
        if not rows:
            show_warning(self, "Dışa aktarmak için en az bir stok kaydı seçin.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Seçili Stokları Excel Olarak Kaydet",
            f"secili_stoklar_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            "Excel Dosyası (*.xlsx)",
        )
        if not path:
            return
        selected_ids = {
            self.table_stock.item(row, 0).data(Qt.ItemDataRole.UserRole)
            for row in rows
            if self.table_stock.item(row, 0) is not None
        }
        parts, _ = self.db.get_parts_paginated(limit=100000)
        selected_parts = [
            part for part in parts if dict(part).get("id") in selected_ids
        ]
        pd.DataFrame(self._build_stock_export_rows(selected_parts)).to_excel(
            path, index=False
        )
        show_success(self, f"{len(rows)} stok kaydı Excel olarak dışa aktarıldı.")

    def _build_stock_html(self):
        headers = []
        for col in range(self.table_stock.columnCount()):
            item = self.table_stock.horizontalHeaderItem(col)
            headers.append(item.text() if item else f"Kolon {col + 1}")
        body_rows = []
        for row in range(self.table_stock.rowCount()):
            cells = []
            for col in range(self.table_stock.columnCount()):
                item = self.table_stock.item(row, col)
                cells.append(item.text() if item else "")
            body_rows.append(
                "<tr>"
                + "".join(
                    f"<td style='padding:6px;border:1px solid #d9d9d9;'>{cell}</td>"
                    for cell in cells
                )
                + "</tr>"
            )
        header_html = "".join(
            f"<th style='padding:8px;border:1px solid #d9d9d9;background:#f3f4f6;'>{header}</th>"
            for header in headers
        )
        return f"""
        <html><head><meta charset='UTF-8'></head><body>
        <h2>AYEC Pro - Stok Listesi</h2>
        <p>Tarih: {datetime.now().strftime("%d.%m.%Y %H:%M")}</p>
        <table cellspacing='0' cellpadding='0' style='width:100%;border-collapse:collapse;font-size:9pt;'>
        <thead><tr>{header_html}</tr></thead>
        <tbody>{"".join(body_rows)}</tbody>
        </table></body></html>
        """

    def export_stock_to_pdf(self):
        try:
            if self.table_stock.rowCount() == 0:
                show_warning(self, "PDF için stok verisi bulunamadı.")
                return
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Stok PDF Kaydet",
                f"stok_listesi_{datetime.now().strftime('%Y%m%d')}.pdf",
                "PDF Dosyası (*.pdf)",
            )
            if not path:
                return
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(path)
            doc = QTextDocument()
            doc.setHtml(self._build_stock_html())
            doc.print(printer)
            show_success(self, "Stok PDF oluşturuldu.")
        except Exception as e:
            show_error(self, f"Stok PDF hatası: {e}")

    def print_stock_table(self):
        try:
            if self.table_stock.rowCount() == 0:
                show_warning(self, "Yazdırılacak stok verisi bulunamadı.")
                return
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            dialog = QPrintDialog(printer, self)
            if dialog.exec() != QPrintDialog.DialogCode.Accepted:
                return
            doc = QTextDocument()
            doc.setHtml(self._build_stock_html())
            doc.print(printer)
            show_success(self, "Stok listesi yazdırmaya gönderildi.")
        except Exception as e:
            show_error(self, f"Stok yazdırma hatası: {e}")

    def _collect_history_rows(self):
        rows = []
        headers = []
        for col in range(self.table_hist.columnCount()):
            item = self.table_hist.horizontalHeaderItem(col)
            headers.append(item.text() if item else f"Kolon {col + 1}")
        for row in range(self.table_hist.rowCount()):
            payload = {}
            for col, header in enumerate(headers):
                item = self.table_hist.item(row, col)
                payload[header] = item.text() if item else ""
            rows.append(payload)
        return rows

    def _build_history_html(self):
        rows = self._collect_history_rows()
        body_rows = []
        for row in rows:
            body_rows.append(
                "<tr>"
                + "".join(
                    f"<td style='padding:6px;border:1px solid #d9d9d9;'>{row[key]}</td>"
                    for key in row.keys()
                )
                + "</tr>"
            )
        header_html = "".join(
            f"<th style='padding:8px;border:1px solid #d9d9d9;background:#f3f4f6;'>{header}</th>"
            for header in (rows[0].keys() if rows else [])
        )
        return f"""
        <html><head><meta charset='UTF-8'></head><body>
        <h2>AYEC Pro - Stok Hareketleri</h2>
        <p>Tarih: {datetime.now().strftime("%d.%m.%Y %H:%M")}</p>
        <table cellspacing='0' cellpadding='0' style='width:100%;border-collapse:collapse;font-size:9pt;'>
        <thead><tr>{header_html}</tr></thead>
        <tbody>{"".join(body_rows)}</tbody>
        </table></body></html>
        """

    def export_history_to_excel(self):
        try:
            rows = self._collect_history_rows()
            if not rows:
                show_warning(self, "Dışa aktarılacak stok hareketi bulunamadı.")
                return
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Hareket Geçmişini Kaydet",
                f"stok_hareketleri_{datetime.now().strftime('%Y%m%d')}.xlsx",
                "Excel Dosyası (*.xlsx)",
            )
            if not path:
                return
            df = pd.DataFrame(rows)
            df.to_excel(path, index=False)
            show_success(self, "Stok hareketleri dışa aktarıldı.")
        except Exception as e:
            show_error(self, f"Hareket geçmişi Excel hatası: {e}")

    def export_history_to_pdf(self):
        try:
            if self.table_hist.rowCount() == 0:
                show_warning(self, "PDF için stok hareketi bulunamadı.")
                return
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Hareket Geçmişi PDF Kaydet",
                f"stok_hareketleri_{datetime.now().strftime('%Y%m%d')}.pdf",
                "PDF Dosyası (*.pdf)",
            )
            if not path:
                return
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(path)
            doc = QTextDocument()
            doc.setHtml(self._build_history_html())
            doc.print(printer)
            show_success(self, "Stok hareketleri PDF olarak kaydedildi.")
        except Exception as e:
            show_error(self, f"Hareket geçmişi PDF hatası: {e}")

    def print_history_table(self):
        try:
            if self.table_hist.rowCount() == 0:
                show_warning(self, "Yazdırılacak stok hareketi bulunamadı.")
                return
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            dialog = QPrintDialog(printer, self)
            if dialog.exec() != QPrintDialog.DialogCode.Accepted:
                return
            doc = QTextDocument()
            doc.setHtml(self._build_history_html())
            doc.print(printer)
            show_success(self, "Stok hareketleri yazdırmaya gönderildi.")
        except Exception as e:
            show_error(self, f"Hareket geçmişi yazdırma hatası: {e}")

    def export_active_tab_to_pdf(self):
        if self.tabs.currentWidget() == self.tab_history:
            self.export_history_to_pdf()
            return
        self.export_stock_to_pdf()

    def print_active_tab(self):
        if self.tabs.currentWidget() == self.tab_history:
            self.print_history_table()
            return
        self.print_stock_table()
