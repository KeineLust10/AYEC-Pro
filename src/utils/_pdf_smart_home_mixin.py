# -*- coding: utf-8 -*-
import os
import random
import tempfile
from datetime import datetime
from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import ParagraphStyle
from src.utils.logger import logger

class PDFSmartHomeMixin:
    def _default_smart_home_reference_pdf(self):
        c = os.path.join(os.path.expanduser("~"), "Downloads", "Wiihom - WiiT-2155-20260309.pdf")
        return c if os.path.exists(c) else ""

    def _extract_reference_pdf_image(self, pdf_path, page_index, image_index, output_name):
        if not pdf_path or not os.path.exists(pdf_path):
            return ""
        try:
            reader = PdfReader(pdf_path)
            if page_index >= len(reader.pages):
                return ""
            images = list(reader.pages[page_index].images)
            if image_index >= len(images):
                return ""
            asset_dir = os.path.join(tempfile.gettempdir(), "ayec_reference_assets")
            os.makedirs(asset_dir, exist_ok=True)
            out_path = os.path.join(asset_dir, output_name)
            with open(out_path, "wb") as f:
                f.write(images[image_index].data)
            return out_path
        except Exception as e:
            logger.warning("Reference image extraction failed: %s", e)
            return ""

    def _append_reference_pages(self, source_pdf_path, output_pdf_path, reference_pdf_path, page_indexes):
        if not reference_pdf_path or not os.path.exists(reference_pdf_path):
            if source_pdf_path != output_pdf_path:
                with open(source_pdf_path, "rb") as src:
                    with open(output_pdf_path, "wb") as dst:
                        dst.write(src.read())
            return
        writer = PdfWriter()
        source_reader = PdfReader(source_pdf_path)
        for page in source_reader.pages:
            writer.add_page(page)
        ref_reader = PdfReader(reference_pdf_path)
        for idx in page_indexes:
            if 0 <= idx < len(ref_reader.pages):
                p = ref_reader.pages[idx]
                if (p.extract_text() or "").strip():
                    writer.add_page(p)
        with open(output_pdf_path, "wb") as f:
            writer.write(f)

    def create_smart_home_offer_letter(self, offer_data, items, template_pdf=None, save_path=None):
        try:
            from src.utils.design_system import DesignTokens
            offer_no = str(offer_data.get("offer_no") or f"WiiT-{random.randint(1000,9999)}-{datetime.now().strftime('%Y%m%d')}")
            company_name = str(offer_data.get("company_name") or "").strip()
            customer_name = str(offer_data.get("customer_name") or "").strip()
            project_name = str(offer_data.get("project_name") or company_name or "").strip()
            offer_date = str(offer_data.get("date") or datetime.now().strftime("%Y-%m-%d")).strip()
            phone = str(offer_data.get("phone") or "").strip()
            email = str(offer_data.get("email") or "").strip()
            block_count = int(offer_data.get("block_count") or 0)
            flat_count = int(offer_data.get("flat_count") or 0)
            notes = str(offer_data.get("notes") or "").strip()
            vat_rate = float(offer_data.get("vat_rate") or 20.0)
            reference_pdf = template_pdf or self._default_smart_home_reference_pdf()
            wiihom_logo_path = self._extract_reference_pdf_image(reference_pdf, 1, 1, "wiihom_logo.jpg")

            if not save_path:
                save_dir = os.path.join(os.path.join(os.path.expanduser("~"), "Downloads"), "AYECPro_Belgeler", self._safe_filename(company_name or customer_name))
                os.makedirs(save_dir, exist_ok=True)
                save_path = os.path.join(save_dir, f"AkilliEv_TeklifMektubu_{self._safe_filename(offer_no)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")

            f_norm, f_bold = self._register_fonts()
            styles = self._get_styles()
            title_style = ParagraphStyle("SmartTitle", parent=styles["Normal"], fontName=f_bold, fontSize=20, textColor=colors.HexColor("#0F4C81"), leading=24, alignment=1)
            heading_style = ParagraphStyle("SmartHeading", parent=styles["Normal"], fontName=f_bold, fontSize=14, textColor=colors.HexColor("#0F4C81"), leading=18, spaceAfter=6)
            body_style = ParagraphStyle("SmartBody", parent=styles["Normal"], fontName=f_norm, fontSize=10, textColor=colors.HexColor("#1F2937"), leading=14)
            body_bold = ParagraphStyle("SmartBodyBold", parent=styles["Normal"], fontName=f_bold, fontSize=10, textColor=colors.HexColor("#1F2937"), leading=14)
            center_style = ParagraphStyle("SmartCenter", parent=body_style, alignment=1)
            right_style = ParagraphStyle("SmartRight", parent=body_style, alignment=2)
            small_style = ParagraphStyle("SmartSmall", parent=styles["Normal"], fontName=f_norm, fontSize=8.5, textColor=colors.HexColor("#4B5563"), leading=11)
            body_tight = ParagraphStyle("SmartBodyTight", parent=body_style, leading=12)
            contact_title = ParagraphStyle("SmartContactTitle", parent=styles["Normal"], fontName=f_bold, fontSize=9.2, textColor=colors.HexColor("#0F4C81"), leading=11)

            currency_totals = self._group_currency_totals(items)
            vat_totals = {c: a * (vat_rate / 100.0) for c, a in currency_totals.items()}
            grand_totals = {c: currency_totals[c] + vat_totals[c] for c in currency_totals}
            single_currency = len(currency_totals) == 1
            temp_path = save_path + ".tmp"
            doc = SimpleDocTemplate(temp_path, pagesize=A4, rightMargin=14*mm, leftMargin=14*mm, topMargin=14*mm, bottomMargin=14*mm)
            elements = []

            brand_left = []
            if wiihom_logo_path and os.path.exists(wiihom_logo_path): brand_left.append(Image(wiihom_logo_path, width=76*mm, height=18*mm, kind="proportional"))
            else: brand_left.append(Paragraph("WiiHOM Akıllı Ev Sistemleri", ParagraphStyle("BrandFallback", parent=styles["Normal"], fontName=f_bold, fontSize=18, textColor=colors.HexColor("#1D79B7"), leading=22)))
            brand_left.append(Spacer(1, 2*mm))
            brand_left.append(Paragraph("Akıllı Ev Sistemleri", ParagraphStyle("WiihomSub", parent=small_style, textColor=colors.HexColor("#5B6472"))))
            brand_right = [Paragraph('<font color="#1d79b7"><b>bulut</b></font><font color="#f0a500"><b>teknoloji</b></font>', ParagraphStyle("BulutTitle", parent=styles["Normal"], fontName=f_bold, fontSize=21, alignment=2, leading=24)), Paragraph("Bilişim ve Güvenlik Sistemleri", ParagraphStyle("BulutSub", parent=small_style, alignment=2))]

            header_table = Table([[brand_left, brand_right]], colWidths=[94*mm, 86*mm])
            header_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
            elements.extend([header_table, Spacer(1, 3*mm)])

            contact_table = Table([[ [Paragraph("MERKEZ", contact_title), Paragraph("Atatürk Mh. Kalkım Cd. No:144/2A<br/>Edremit / BALIKESİR", body_tight)], [Paragraph("AKDENİZ BÖLGE MÜDÜRLÜĞÜ", contact_title), Paragraph("Arapsuyu Mh. 626. Sk. No:10/1 Feyzi Apartmanı<br/>Konyaaltı / ANTALYA", body_tight)], [Paragraph("İLETİŞİM", contact_title), Paragraph("M: +90 542 425 87 20<br/>T: +90 850 305 32 63<br/>kyuksel@wiihom.com<br/>www.wiihom.com", body_tight)] ]], colWidths=[60*mm, 60*mm, 60*mm])
            contact_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FAFC")), ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#D8E2EC")), ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E3EBF3")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
            elements.extend([contact_table, Spacer(1, 6*mm)])

            hero_box = Table([[Paragraph("Akıllı Ev Sistemleri Teklif Dosyası", ParagraphStyle("HeroTitle", parent=styles["Normal"], fontName=f_bold, fontSize=16, textColor=colors.white, alignment=1, leading=20))]], colWidths=[180*mm])
            hero_box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0F4C81")), ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12), ("TOPPADDING", (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 10)]))
            elements.extend([hero_box, Spacer(1, 5*mm), Paragraph("Akıllı Ev Sistemleri", title_style), Paragraph("Teklif Bilgisi ve Proje Özeti", ParagraphStyle("SmartSub", parent=styles["Normal"], fontName=f_norm, fontSize=12, textColor=colors.HexColor("#54708B"), alignment=1)), Spacer(1, 8*mm)])

            top_box = Table([[Paragraph(f"<b>Firma</b><br/>{company_name}", body_style), Paragraph(f"<b>Teklif No</b><br/>{offer_no}", right_style)]], colWidths=[90*mm, 90*mm])
            top_box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F5FAFE")), ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#C9D7E6")), ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12), ("TOPPADDING", (0, 0), (-1, -1), 12), ("BOTTOMPADDING", (0, 0), (-1, -1), 12), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
            elements.extend([top_box, Spacer(1, 6*mm)])

            info_rows = [[Paragraph("<b>Yetkili</b>", body_bold), Paragraph(customer_name or "-", body_style), Paragraph("<b>Tarih</b>", body_bold), Paragraph(offer_date, body_style)], [Paragraph("<b>Telefon</b>", body_bold), Paragraph(phone or "-", body_style), Paragraph("<b>E-Posta</b>", body_bold), Paragraph(email or "-", body_style)], [Paragraph("<b>Proje Adı</b>", body_bold), Paragraph(project_name or "-", body_style), Paragraph("<b>Blok / Daire</b>", body_bold), Paragraph(f"{block_count} / {flat_count}", body_style)]]
            info_table = Table(info_rows, colWidths=[26 * mm, 64 * mm, 26 * mm, 64 * mm])
            info_table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D6E0EA")), ("BACKGROUND", (0, 0), (-1, -1), colors.white), ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F8FBFD")), ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#F8FBFD")), ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
            elements.extend([info_table, Spacer(1, 8*mm)])

            intro_lines = [f"Sayın {customer_name or company_name or 'Yetkili'},", "Projeniz için tasarlanmış akıllı ev sistemi teklifini ekte bilgilerinize sunariz.", "Teklif içeriği, ürün kalemleri ve detay açıklamalar ile ilgili sorularınızı memnuniyetle yanıtlamaya hazırız.", "Teklifimizi değerlendirerek projenizde birlikte çalışabilmemiz için geri dönüşlerinizi bekleriz."]
            if notes: intro_lines.append(f"Özel Not: {notes}")
            intro_table = Table([[Paragraph("<br/>".join(intro_lines), body_style)]], colWidths=[180 * mm])
            intro_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FBFD")), ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#D6E0EA")), ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12), ("TOPPADDING", (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 10)]))
            elements.extend([intro_table, Spacer(1, 6*mm)])

            if single_currency:
                sc = next(iter(currency_totals))
                stat_rows = [[Paragraph(f"<b>Ürün Kalemi</b><br/>{len(items)}", center_style), Paragraph(f"<b>Ara Toplam</b><br/>{self._format_money(currency_totals[sc], sc)}", center_style), Paragraph(f"<b>KDV</b><br/>{self._format_money(vat_totals[sc], sc)}", center_style), Paragraph(f"<b>Genel Toplam</b><br/>{self._format_money(grand_totals[sc], sc)}", center_style)]]
            else:
                stat_rows = [[Paragraph(f"<b>Ürün Kalemi</b><br/>{len(items)}", center_style), Paragraph(f"<b>Para Birimi</b><br/>{len(currency_totals)} farkli PB", center_style), Paragraph(f"<b>Ara Toplam</b><br/>Satir bazli hesap", center_style), Paragraph("<b>Genel Toplam</b><br/>Icmal sayfasina bakiniz", center_style)]]
            stat_cards = Table(stat_rows, colWidths=[45 * mm, 45 * mm, 45 * mm, 45 * mm])
            stat_cards.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0F4C81")), ("TEXTCOLOR", (0, 0), (-1, -1), colors.white), ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#0F4C81")), ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 12), ("BOTTOMPADDING", (0, 0), (-1, -1), 12), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
            elements.extend([stat_cards, Spacer(1, 8*mm)])

            sig_table = Table([[Paragraph("Saygılarımızla,<br/><br/><b>AYEC Pro Akıllı Ev Satış Modülü</b>", body_style), Paragraph("<b>Kaan YÜKSEL</b><br/>Proje Yöneticisi<br/>WiiHOM Akıllı Ev Sistemleri<br/>Akdeniz Bölge Müdürlüğü<br/>Arapsuyu Mh. 626. Sk. No:10 D:1<br/>Konyaaltı / ANTALYA / TÜRKİYE", right_style)]], colWidths=[90 * mm, 90 * mm])
            sig_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.white), ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D6E0EA")), ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12), ("TOPPADDING", (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 10), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
            elements.extend([sig_table, PageBreak()])

            chunks = [items[i:i + 8] for i in range(0, len(items), 8)] or [[]]
            for page_no, chunk in enumerate(chunks, start=1):
                elements.append(Paragraph(f"Ürün Detayları - Sayfa {page_no}", heading_style))
                product_rows = [[Paragraph("Ürün / Kod", body_bold), Paragraph("Açıklama", body_bold), Paragraph("Adet", body_bold), Paragraph("Birim", body_bold), Paragraph("Tutar", body_bold)]]
                for it in chunk:
                    qty = int(it.get("qty") or 0); up = float(it.get("unit_price") or 0); lt = qty * up; ic = str(it.get("currency") or "USD").upper()
                    product_rows.append([Paragraph(f"{it.get('name', '-')}" + (f"<br/>{it.get('code')}" if it.get("code") else ""), body_style), Paragraph(str(it.get("description") or it.get("category") or "-"), body_style), Paragraph(str(qty), center_style), Paragraph(self._format_money(up, ic), center_style), Paragraph(self._format_money(lt, ic), center_style)])
                pt = Table(product_rows, colWidths=[58 * mm, 66 * mm, 16 * mm, 24 * mm, 26 * mm], repeatRows=1)
                pt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#103D60")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#C8D6E2")), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FBFD")]), ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (2, 1), (-1, -1), "CENTER")]))
                elements.append(pt)
                if page_no != len(chunks): elements.append(PageBreak())

            elements.append(PageBreak()); elements.append(Paragraph("Teklif İcmali", heading_style))
            sum_rows = [[Paragraph("Sıra", body_bold), Paragraph("Kalem", body_bold), Paragraph("Miktar", body_bold), Paragraph("Birim Fiyat", body_bold), Paragraph("Toplam", body_bold)]]
            for idx, it in enumerate(items, start=1):
                qty = int(it.get("qty") or 0); up = float(it.get("unit_price") or 0); ic = str(it.get("currency") or "USD").upper()
                sum_rows.append([Paragraph(str(idx), center_style), Paragraph(str(it.get("name") or "-"), body_style), Paragraph(str(qty), center_style), Paragraph(self._format_money(up, ic), center_style), Paragraph(self._format_money(qty * up, ic), center_style)])
            for c, a in currency_totals.items():
                sum_rows.extend([ ["", "", "", Paragraph(f"Ara Toplam ({c})", body_bold), Paragraph(self._format_money(a, c), body_bold)], ["", "", "", Paragraph(f"KDV (%{vat_rate:.0f}) ({c})", body_bold), Paragraph(self._format_money(vat_totals[c], c), body_bold)], ["", "", "", Paragraph(f"Genel Toplam ({c})", body_bold), Paragraph(self._format_money(grand_totals[c], c), body_bold)] ])
            st = Table(sum_rows, colWidths=[14 * mm, 90 * mm, 20 * mm, 30 * mm, 30 * mm], repeatRows=1)
            st.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F4C81")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#C8D6E2")), ("ROWBACKGROUNDS", (0, 1), (-1, -(len(currency_totals) * 3 + 1)), [colors.white, colors.HexColor("#F8FBFD")]), ("BACKGROUND", (0, -(len(currency_totals) * 3)), (-1, -1), colors.HexColor("#EEF5FA")), ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7), ("ALIGN", (0, 1), (0, -1), "CENTER"), ("ALIGN", (2, 1), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
            elements.extend([st, Spacer(1, 8 * mm), Paragraph("Bilgilendirme", heading_style)])
            for term in [f"1. Teklif fiyatlarina %{vat_rate:.0f} Katma Deger Vergisi (KDV) dahildir.", "2. Teklifin gecerlilik suresi teklifin iletildigi gunden itibaren 15 gundur.", "3. Fiyatlar secilen para birimi uzerinden hazirlanmistir.", "4. Bu teklif ilgili proje icin ozel hazirlanmistir."]:
                elements.append(Paragraph(term, body_style)); elements.append(Spacer(1, 1.5 * mm))

            def draw_page(canvas_obj, doc_obj):
                canvas_obj.saveState(); pw, ph = A4; canvas_obj.setFillColor(colors.HexColor("#0F4C81")); canvas_obj.rect(14 * mm, ph - 18 * mm, pw - 28 * mm, 8 * mm, stroke=0, fill=1)
                canvas_obj.setFillColor(colors.white); canvas_obj.setFont(f_bold, 9); canvas_obj.drawString(18 * mm, ph - 13.2 * mm, "AYEC Pro | Akıllı Ev Teklif Formu")
                canvas_obj.setFillColor(colors.HexColor("#6B7280")); canvas_obj.setFont(f_norm, 8); canvas_obj.drawRightString(pw - 16 * mm, 10 * mm, f"Sayfa {doc_obj.page}"); canvas_obj.restoreState()

            doc.build(elements, onFirstPage=draw_page, onLaterPages=draw_page)
            r_reader = PdfReader(reference_pdf) if reference_pdf and os.path.exists(reference_pdf) else None
            ai = [len(r_reader.pages) - 2] if r_reader and len(r_reader.pages) >= 2 else []
            self._append_reference_pages(temp_path, save_path, reference_pdf, ai)
            try: os.remove(temp_path)
            except Exception: pass
            self._open_file(save_path); return True, save_path
        except Exception as e: logger.error("Smart home offer letter error: %s", e); return False, str(e)

    def create_smart_home_offer_excel(self, offer_data, items, save_path=None):
        try:
            from openpyxl import Workbook; from openpyxl.styles import Alignment, Border, Font, PatternFill, Side; from openpyxl.drawing.image import Image as XLImage
            offer_no = str(offer_data.get("offer_no") or f"WiiT-{random.randint(1000,9999)}-{datetime.now().strftime('%Y%m%d')}")
            cn = str(offer_data.get("company_name") or "").strip(); c_name = str(offer_data.get("customer_name") or "").strip()
            pn = str(offer_data.get("project_name") or cn or "").strip(); od = str(offer_data.get("date") or datetime.now().strftime("%Y-%m-%d")).strip()
            ph = str(offer_data.get("phone") or "").strip(); em = str(offer_data.get("email") or "").strip()
            bc = int(offer_data.get("block_count") or 0); fc = int(offer_data.get("flat_count") or 0); nt = str(offer_data.get("notes") or "").strip(); vr = float(offer_data.get("vat_rate") or 20.0)
            r_pdf = self._default_smart_home_reference_pdf(); w_logo = self._extract_reference_pdf_image(r_pdf, 1, 1, "excel_wiihom_logo.jpg"); c_img = self._extract_reference_pdf_image(r_pdf, 0, 0, "excel_cover_image.jpg")
            r_terms = ""
            try:
                if r_pdf and os.path.exists(r_pdf):
                    rd = PdfReader(r_pdf)
                    if len(rd.pages) >= 2: r_terms = (rd.pages[-2].extract_text() or "").strip()
            except Exception: pass

            if not save_path:
                sd = os.path.join(os.path.join(os.path.expanduser("~"), "Downloads"), "AYECPro_Belgeler", self._safe_filename(cn or c_name)); os.makedirs(sd, exist_ok=True)
                save_path = os.path.join(sd, f"AkilliEv_TeklifExcel_{self._safe_filename(offer_no)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")

            wb = Workbook(); ws = wb.active; ws.title = "Teklif Formu"; info_ws = wb.create_sheet("Bilgilendirme"); docs_ws = wb.create_sheet("Referans Belgeler")
            hf = PatternFill("solid", fgColor="0F4C81"); sf = PatternFill("solid", fgColor="EAF4FB"); tf = PatternFill("solid", fgColor="DFF3EA"); tg = Side(style="thin", color="D6E0EA"); brd = Border(left=tg, right=tg, top=tg, bottom=tg)
            for col, width in {"A": 8, "B": 18, "C": 28, "D": 22, "E": 46, "F": 10, "G": 14, "H": 14, "I": 16}.items(): ws.column_dimensions[col].width = width
            ws.row_dimensions[1].height = 30
            ws.row_dimensions[2].height = 55
            ws.row_dimensions[4].height = 52
            if w_logo and os.path.exists(w_logo):
                img = XLImage(w_logo)
                img.width = 320
                img.height = 72
                ws.add_image(img, "A1")
            ws.merge_cells("F1:I2")
            ws["F1"] = "bulutteknoloji\nBilişim ve Güvenlik Sistemleri"
            ws["F1"].font = Font(size=16, bold=True, color="1D79B7")
            ws["F1"].alignment = Alignment(horizontal="right", vertical="center", wrap_text=True)
            ws.merge_cells("A4:I4")
            ws["A4"] = "AKILLI EV TEKLIF DOSYASI"
            ws["A4"].font = Font(size=16, bold=True, color="FFFFFF")
            ws["A4"].fill = hf
            ws["A4"].alignment = Alignment(horizontal="center", vertical="center")
            
            cr = 6; ws.merge_cells(f"A{cr}:C{cr}"); ws.merge_cells(f"D{cr}:F{cr}"); ws.merge_cells(f"G{cr}:I{cr}")
            ws[f"A{cr}"], ws[f"D{cr}"], ws[f"G{cr}"] = "MERKEZ", "AKDENIZ BOLGE MUDURLUGU", "ILETISIM"
            for c_ref in (f"A{cr}", f"D{cr}", f"G{cr}"): ws[c_ref].font = Font(size=10, bold=True, color="0F4C81"); ws[c_ref].fill = sf; ws[c_ref].alignment = Alignment(horizontal="center", vertical="center"); ws[c_ref].border = brd
            ws.merge_cells(f"A{cr+1}:C{cr+3}")
            ws.merge_cells(f"D{cr+1}:F{cr+3}")
            ws.merge_cells(f"G{cr+1}:I{cr+3}")
            ws[f"A{cr+1}"] = "Atatürk Mh. Kalkım Cd. No:144/2A\nEdremit / BALIKESIR"
            ws[f"D{cr+1}"] = "Arapsuyu Mh. 626. Sk. No:10/1 Feyzi Apartmani\nKonyaalti / ANTALYA"
            ws[f"G{cr+1}"] = "M: +90 542 425 87 20\nT: +90 850 305 32 63\nkyuksel@wiihom.com\nwww.wiihom.com"
            for c_ref in (f"A{cr+1}", f"D{cr+1}", f"G{cr+1}"):
                ws[c_ref].alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                ws[c_ref].border = brd

            sr = 11; ws.merge_cells(f"A{sr}:E{sr}"); ws[f"A{sr}"] = "Musteri ve Proje Bilgileri"; ws[f"A{sr}"].font = Font(size=12, bold=True, color="0F4C81"); ws[f"A{sr}"].fill = sf; ws[f"A{sr}"].alignment = Alignment(horizontal="left", vertical="center")
            ws.merge_cells(f"F{sr}:I{sr}"); ws[f"F{sr}"] = "Teklif Bilgileri"; ws[f"F{sr}"].font = Font(size=12, bold=True, color="0F4C81"); ws[f"F{sr}"].fill = sf; ws[f"F{sr}"].alignment = Alignment(horizontal="left", vertical="center")
            info_pairs = [("Musteri / Yetkili", c_name or "-"), ("Firma / Kurum", cn or "-"), ("Telefon", ph or "-"), ("E-Posta", em or "-"), ("Proje Adi", pn or "-"), ("Blok Sayisi", bc), ("Daire Sayisi", fc), ("Teklif No", offer_no), ("Tarih", od), ("KDV Orani", f"%{vr:.0f}")]
            lr, rr = info_pairs[:7], info_pairs[7:]; start_row = sr + 1
            for i, (l, v) in enumerate(lr, start=start_row):
                ws[f"A{i}"] = l; ws[f"A{i}"].font = Font(bold=True, color="4B5563"); ws[f"A{i}"].fill = sf; ws[f"A{i}"].border = brd; ws.merge_cells(f"B{i}:E{i}"); ws[f"B{i}"] = v; ws[f"B{i}"].border = brd
            for i, (l, v) in enumerate(rr, start=start_row):
                ws[f"F{i}"] = l; ws[f"F{i}"].font = Font(bold=True, color="4B5563"); ws[f"F{i}"].fill = sf; ws[f"F{i}"].border = brd; ws.merge_cells(f"G{i}:I{i}"); ws[f"G{i}"] = v; ws[f"G{i}"].border = brd

            nr = start_row + max(len(lr), len(rr)) + 1; ws.merge_cells(f"A{nr}:I{nr}"); ws[f"A{nr}"] = "Duzenleme Alani: Istenmeyen satirlari silebilir, metinleri degistirebilir ve yeni satir ekleyebilirsiniz."; ws[f"A{nr}"].font = Font(italic=True, color="0F4C81"); ws[f"A{nr}"].fill = PatternFill("solid", fgColor="FFF7D6")
            ir = nr + 2; ws.merge_cells(f"A{ir}:I{ir+2}"); i_text = f"Sayin {c_name or cn or 'Yetkili'},\nProjeniz icin hazirlanan akilli ev sistemi teklifini bilgilerinize sunariz.\nUrun kalemleri, miktarlar ve fiyatlar asagidaki tabloda duzenlenebilir sekilde yer almaktadir."
            if nt: i_text += f"\nOzel Not: {nt}"
            ws[f"A{ir}"] = i_text; ws[f"A{ir}"].alignment = Alignment(wrap_text=True, vertical="top"); ws[f"A{ir}"].border = brd
            if c_img and os.path.exists(c_img): ci = XLImage(c_img); ci.width = 185; ci.height = 260; ws.add_image(ci, f"H{ir}")

            tr = ir + 4; headers = ["Sira", "Kod", "Urun", "Kategori", "Aciklama", "Adet", "Birim Fiyat", "PB", "Toplam"]
            for ci, h in enumerate(headers, start=1): cell = ws.cell(row=tr, column=ci, value=h); cell.font = Font(bold=True, color="FFFFFF"); cell.fill = hf; cell.alignment = Alignment(horizontal="center", vertical="center"); cell.border = brd
            cur_r = tr + 1
            for idx, it in enumerate(items, start=1):
                q = int(it.get("qty") or 0); up = float(it.get("unit_price") or 0); cur = str(it.get("currency") or "USD").upper()
                vals = [idx, str(it.get("code") or ""), str(it.get("name") or ""), str(it.get("category") or ""), str(it.get("description") or ""), q, up, cur, q * up]
                for ci, v in enumerate(vals, start=1):
                    cell = ws.cell(row=cur_r, column=ci, value=v)
                    cell.border = brd
                    cell.alignment = Alignment(vertical="top", wrap_text=ci in (3, 4, 5))
                    if ci in (7, 9):
                        cell.number_format = '#,##0.00'
                cur_r += 1

            ct = self._group_currency_totals(items); vt = {c: a * (vr / 100.0) for c, a in ct.items()}; gt = {c: ct[c] + vt[c] for c in ct}
            t_s = cur_r + 1; ws.merge_cells(f"A{t_s}:F{t_s}"); ws[f"A{t_s}"] = "Toplamlar"; ws[f"A{t_s}"].font = Font(size=12, bold=True, color="0F4C81"); ws[f"A{t_s}"].fill = sf
            r = t_s + 1
            for c, st in ct.items():
                ws[f"F{r}"], ws[f"G{r}"], ws[f"H{r}"], ws[f"I{r}"] = f"Ara Toplam ({c})", st, f"KDV %{vr:.0f}", vt[c]
                for cl in "FGHI":
                    ws[f"{cl}{r}"].border = brd
                    if cl in "GI":
                        ws[f"{cl}{r}"].number_format = '#,##0.00'
                    ws[f"F{r}"].font = Font(bold=True)
                r += 1
                ws[f"F{r}"], ws[f"G{r}"], ws[f"H{r}"], ws[f"I{r}"] = f"Genel Toplam ({c})", gt[c], c, ""
                for cl in "FGHI":
                    ws[f"{cl}{r}"].border = brd
                    ws[f"{cl}{r}"].fill = tf
                    if cl == "G":
                        ws[f"{cl}{r}"].number_format = '#,##0.00'
                    ws[f"F{r}"].font = Font(bold=True, color="0F5132")
                    ws[f"G{r}"].font = Font(bold=True, color="0F5132")
                r += 1
            ws.freeze_panes = f"A{tr+1}"

            info_ws.column_dimensions["A"].width = 8; info_ws.column_dimensions["B"].width = 120
            info_ws["A1"] = "Bilgilendirme ve Duzenleme Notlari"; info_ws["A1"].font = Font(size=14, bold=True, color="FFFFFF"); info_ws["A1"].fill = hf; info_ws.merge_cells("A1:B1")
            lns = ["Bu excel dosyasi teklif uzerinde manuel duzenleme yapabilmeniz icin olusturulmustur.", "Istenmeyen urun satirlarini silebilir veya yeni satir ekleyebilirsiniz.", "Fiyat, adet ve aciklama hucreleri manuel olarak degistirilebilir.", "Son hali kontrol ettikten sonra Excel olarak saklayabilir veya PDF'ye yazdirabilirsiniz.", f"KDV orani varsayilan olarak %{vr:.0f} uygulanmistir."]
            for idx, ln in enumerate(lns, start=3): info_ws[f"A{idx}"], info_ws[f"B{idx}"] = idx - 2, ln; info_ws[f"A{idx}"].border = info_ws[f"B{idx}"].border = brd; info_ws[f"B{idx}"].alignment = Alignment(wrap_text=True)

            docs_ws.column_dimensions["A"].width = 6; docs_ws.column_dimensions["B"].width = 120
            docs_ws["A1"] = "Referans Belgeler ve Bilgilendirme"; docs_ws["A1"].font = Font(size=14, bold=True, color="FFFFFF"); docs_ws["A1"].fill = hf; docs_ws.merge_cells("A1:B1")
            docs_ws["B3"] = "Bu sayfa referans PDF'nin sonundaki bilgilendirme belgelerini içerir."; docs_ws["B3"].font = Font(italic=True, color="0F4C81"); docs_ws["B3"].alignment = Alignment(wrap_text=True)
            if r_terms:
                trl = [l.strip() for l in r_terms.splitlines() if l.strip()]; r_cur = 5
                for idx, ln in enumerate(trl, start=1): docs_ws[f"A{r_cur}"], docs_ws[f"B{r_cur}"] = idx, ln; docs_ws[f"A{r_cur}"].border = docs_ws[f"B{r_cur}"].border = brd; docs_ws[f"B{r_cur}"].alignment = Alignment(wrap_text=True, vertical="top"); r_cur += 1
            else: docs_ws["B5"] = "Referans PDF bilgilendirme metni bulunamadi."
            wb.save(save_path); self._open_file(save_path); return True, save_path
        except Exception as e: logger.error("Smart home offer excel error: %s", e); return False, str(e)
