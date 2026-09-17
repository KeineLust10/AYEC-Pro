# -*- coding: utf-8 -*-

"""
Service Form PDF Generator
Creates professional service forms with Turkish character support.
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, Paragraph, Spacer, Image
from reportlab.lib import colors
from datetime import datetime
import os

from src.utils.pdf_helper import TurkishPDFHelper

class ServiceFormPDF:
    """Generate service form PDF with Turkish support."""
    
    def __init__(self, db):
        self.db = db
        TurkishPDFHelper.register_fonts()
    
    def generate(self, tracking_no, output_path=None):
        """
        Generate service form PDF for given tracking number.
        
        Args:
            tracking_no: Device tracking number
            output_path: Optional output path, defaults to desktop
            
        Returns:
            Path to generated PDF file
        """
        # Get device data
        try:
            self.db.cursor.execute(
                "SELECT * FROM devices WHERE tracking_no=? AND COALESCE(is_deleted, 0)=0",
                (tracking_no,),
            )
        except Exception:
            self.db.cursor.execute("SELECT * FROM devices WHERE tracking_no=?", (tracking_no,))
        device = self.db.cursor.fetchone()
        
        if not device:
            raise ValueError(f"Device not found: {tracking_no}")
        
        # Default output path
        if not output_path:
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            output_path = os.path.join(desktop, f"Servis_Formu_{tracking_no}.pdf")
        
        # Create PDF
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        story = []
        
        # Header
        story.append(self._create_header())
        story.append(Spacer(1, 0.5*cm))
        
        # Title
        title = Paragraph("SERVİS FORMU", TurkishPDFHelper.get_header_style())
        story.append(title)
        story.append(Spacer(1, 0.3*cm))
        
        # Tracking number
        tracking = Paragraph(
            f"<b>Takip No:</b> {tracking_no}",
            TurkishPDFHelper.get_subheader_style()
        )
        story.append(tracking)
        story.append(Spacer(1, 0.5*cm))
        
        # Customer Information
        story.append(self._create_customer_section(device))
        story.append(Spacer(1, 0.5*cm))
        
        # Device Information
        story.append(self._create_device_section(device))
        story.append(Spacer(1, 0.5*cm))
        
        # Fault Description
        story.append(self._create_fault_section(device))
        story.append(Spacer(1, 0.5*cm))
        
        # Cost Breakdown
        story.append(self._create_cost_section(device))
        story.append(Spacer(1, 1*cm))
        
        # Signature Area
        story.append(self._create_signature_section())
        
        # Build PDF
        doc.build(story, onFirstPage=TurkishPDFHelper.add_page_number, 
                 onLaterPages=TurkishPDFHelper.add_page_number)
        
        return output_path
    
    def _create_header(self):
        """Create company header with logo."""
        company_name = self.db.get_setting("company_name", "BULUT TECH")
        company_phone = self.db.get_setting("company_phone", "")
        company_address = self.db.get_setting("company_address", "")
        
        data = [
            [Paragraph(f"<b>{company_name}</b>", TurkishPDFHelper.get_subheader_style())],
            [Paragraph(company_phone, TurkishPDFHelper.get_body_style())],
            [Paragraph(company_address, TurkishPDFHelper.get_body_style())]
        ]
        
        table = Table(data, colWidths=[17*cm])
        table.setStyle(TurkishPDFHelper.create_table_style(header_bg='#ffffff', alternate_rows=False))
        
        return table
    
    def _create_customer_section(self, device):
        """Create customer information section."""
        section_title = Paragraph("<b>MÜŞTERİ BİLGİLERİ</b>", TurkishPDFHelper.get_subheader_style())
        
        # Get customer details
        customer_name = device[1]  # Assuming column 1 is customer
        
        data = [
            ["Müşteri Adı", customer_name],
            ["Teslim Tarihi", TurkishPDFHelper.format_date(device[2])],  # Assuming column 2 is date
            ["Durum", device[3]]  # Assuming column 3 is status
        ]
        
        table = Table(data, colWidths=[5*cm, 12*cm])
        table.setStyle(TurkishPDFHelper.create_table_style(header_bg='#3b82f6'))
        
        return Table([[section_title], [table]], colWidths=[17*cm])
    
    def _create_device_section(self, device):
        """Create device information section."""
        section_title = Paragraph("<b>CİHAZ BİLGİLERİ</b>", TurkishPDFHelper.get_subheader_style())
        
        data = [
            ["Cihaz Türü", device[4] if len(device) > 4 else ""],
            ["Marka/Model", device[5] if len(device) > 5 else ""],
            ["Seri No", device[6] if len(device) > 6 else ""]
        ]
        
        table = Table(data, colWidths=[5*cm, 12*cm])
        table.setStyle(TurkishPDFHelper.create_table_style(header_bg='#3b82f6'))
        
        return Table([[section_title], [table]], colWidths=[17*cm])
    
    def _create_fault_section(self, device):
        """Create fault description section."""
        section_title = Paragraph("<b>ARIZA TANIMI</b>", TurkishPDFHelper.get_subheader_style())
        
        fault_desc = device[7] if len(device) > 7 else "Belirtilmemiş"
        fault_para = Paragraph(fault_desc, TurkishPDFHelper.get_body_style())
        
        return Table([[section_title], [fault_para]], colWidths=[17*cm])
    
    def _create_cost_section(self, device):
        """Create cost breakdown section."""
        section_title = Paragraph("<b>MALİYET DÖKÜMÜ</b>", TurkishPDFHelper.get_subheader_style())
        
        # Sample cost data (adjust based on actual database schema)
        cost = device[8] if len(device) > 8 else 0
        
        data = [
            ["Açıklama", "Tutar"],
            ["Tamir Ücreti", TurkishPDFHelper.format_currency(cost)],
            ["<b>TOPLAM</b>", f"<b>{TurkishPDFHelper.format_currency(cost)}</b>"]
        ]
        
        table = Table(data, colWidths=[12*cm, 5*cm])
        table.setStyle(TurkishPDFHelper.create_table_style(header_bg='#3b82f6'))
        
        return Table([[section_title], [table]], colWidths=[17*cm])
    
    def _create_signature_section(self):
        """Create signature area."""
        data = [
            ["Teslim Eden", "Teslim Alan"],
            ["", ""],
            ["İmza: ______________", "İmza: ______________"]
        ]
        
        table = Table(data, colWidths=[8.5*cm, 8.5*cm], rowHeights=[0.8*cm, 2*cm, 0.8*cm])
        table.setStyle(TurkishPDFHelper.create_table_style(header_bg='#64748b', alternate_rows=False))
        
        return table
