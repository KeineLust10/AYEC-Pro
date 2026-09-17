# -*- coding: utf-8 -*-

"""
PDF Manager for PyQt5 Application
Proforma ve Servis Formu PDF oluşturma
Kurumsal Şablonlar
Mix-in yapısı ile modüler hale getirilmiştir.
"""

from src.utils._pdf_base_mixin import PDFBaseMixin
from src.utils._pdf_invoice_mixin import PDFInvoiceMixin
from src.utils._pdf_service_mixin import PDFServiceMixin
from src.utils._pdf_smart_home_mixin import PDFSmartHomeMixin

class PDFManagerQt(PDFBaseMixin, PDFSmartHomeMixin, PDFInvoiceMixin, PDFServiceMixin):
    """PyQt5 için PDF Manager - Kurumsal (Mix-in destekli)"""
    
    def __init__(self, db):
        self.db = db
