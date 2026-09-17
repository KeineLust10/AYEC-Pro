# -*- coding: utf-8 -*-

from datetime import datetime
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtGui import QTextDocument
from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtGui import QPageSize
from src.utils.date_formatter import format_date
from src.utils.currency_helper import CurrencyHelper

def generate_service_html(db, tracking_no, customer_name, device_info, details, parts_list, labor_cost, total_cost, terms_text, technician_name):
    """HTML servis formu oluştur"""
    labor_text = CurrencyHelper.format_try_for_display(labor_cost, db=db, include_try_reference=False)
    
    html = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; }}
            h1 {{ color: #2c3e50; text-align: center; }}
            .box {{ border: 1px solid #ccc; padding: 10px; margin-bottom: 10px; }}
            .title {{ font-weight: bold; margin-bottom: 5px; background: #eee; padding: 5px; }}
        </style>
    </head>
    <body>
        <h1>TEKNİK SERVİS FORMU</h1>
        
        <div class="box">
            <div class="title">CİHAZ VE MÜŞTERİ BİLGİLERİ</div>
            <p><b>Takip No:</b> {tracking_no}</p>
            <p><b>Müşteri:</b> {customer_name}</p>
            <p><b>Cihaz:</b> {device_info}</p>
            <p><b>Tarih:</b> {format_date(datetime.now(), db, include_time=True)}</p>
        </div>
        
        <div class="box">
            <div class="title">YAPILAN İŞLEMLER</div>
            <p>{details.replace(chr(10), '<br>')}</p>
        </div>
        
        <div class="box">
            <div class="title">FİYATLANDIRMA</div>
            <p><b>Kullanılan Parçalar:</b><br>{parts_list.replace(chr(10), '<br>')}</p>
            <p><b>İşçilik:</b> {labor_text}</p>
            <h3 style="text-align: right; color: #c0392b;">TOPLAM: {total_cost}</h3>
        </div>
        
        <div class="box">
            <div class="title">TEKNİSYEN</div>
            <p>İşlemi Yapan: {technician_name}</p>
        </div>
        
        <div class="box">
            <div class="title">ŞARTLAR</div>
            <small>{terms_text.replace(chr(10), '<br>')}</small>
        </div>
        
        <br><br>
        <table width="100%">
            <tr>
                <td align="center"><b>TESLİM ALAN (Müşteri)</b><br><br><br>_________________</td>
                <td align="center"><b>TESLİM EDEN (Servis)</b><br><br><br>_________________</td>
            </tr>
        </table>
        
    </body>
    </html>
    """
    return html

def save_pdf(html_content, file_path):
    """HTML içeriğini PDF olarak kaydet"""
    try:
        doc = QTextDocument()
        doc.setHtml(html_content)
        
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(file_path)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        
        doc.print_(printer)
        return True
    except Exception as e:
        logger.error("PDF save error: %s", e)
        return False
import logging
logger = logging.getLogger("AYECProLogger")
