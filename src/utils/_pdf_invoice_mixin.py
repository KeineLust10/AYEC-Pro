# -*- coding: utf-8 -*-
import os
import json
import tempfile
from datetime import datetime
from xml.sax.saxutils import escape
from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, Frame
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas as rl_canvas
from src.utils.logger import logger
from src.utils.date_utils import format_turkish_date

class PDFInvoiceMixin:
    def create_invoice(self, template_type, cart_items, totals, company_name=None, customer_name=None, save_path=None, currency="TL", project_name=None, contact_name=None):
        return self.create_proforma(template_type, cart_items, totals, company_name, customer_name, is_invoice=True, save_path=save_path, currency=currency, project_name=project_name, contact_name=contact_name)

    def _default_offer_terms_text(self):
        return "\n".join(
            [
                "Fiyat      : Amerikan Dolar\u0131 cinsinden verilmi\u015f olup, fatura tarihindeki TCMB d\u00f6viz sat\u0131\u015f kuru ge\u00e7erlidir.",
                "\u00d6deme     : Sipari\u015fte toplam tutar\u0131n %50'i, i\u015f bitiminde kalan bakiye nakit \u00f6denecektir.",
                "Teslimat  : Sipari\u015f ve \u00f6n \u00f6demeyi takiben, stok durumuna g\u00f6re 6 (Alt\u0131) haftad\u0131r.",
                "Garanti   : \u00dcretim hatalar\u0131na kar\u015f\u0131 2 (iki) y\u0131ld\u0131r.",
                "Opsiyon   : Fiyat teklifimiz, ta\u015f\u0131d\u0131\u011f\u0131 tarih itibariyle 15 g\u00fcn s\u00fcre ile ge\u00e7erlidir.",
            ]
        )

    def _get_offer_terms_text(self):
        t = str(self.db.get_setting("offer_contract", "") or "").strip()
        if t:
            return t
        service_terms = str(self.db.get_setting("service_contract", "") or "").strip()
        return service_terms if service_terms else self._default_offer_terms_text()

    def create_proforma(
        self,
        template_type,
        cart_items,
        totals,
        company_name=None,
        customer_name=None,
        is_invoice=False,
        save_path=None,
        currency="TL",
        project_name=None,
        contact_name=None,
        reference_no=None,
        offer_date=None,
        customer_company=None,
        currency_code=None,
        validity_days=15,
        totals_try=None,
        exchange_rate=None,
        include_approval=True,
    ):
        from src.utils.custom_editor_proforma import (
            build_custom_editor_proforma,
            is_custom_editor_active,
        )
        from src.utils.professional_proforma import build_professional_proforma

        if is_custom_editor_active(self.db):
            ok, result = build_custom_editor_proforma(
                self,
                cart_items=cart_items,
                totals=totals,
                company_name=company_name,
                customer_name=customer_name,
                save_path=save_path,
                currency=currency,
                project_name=project_name,
                contact_name=contact_name,
                reference_no=reference_no,
                offer_date=offer_date,
                customer_company=customer_company,
                currency_code=currency_code,
                validity_days=validity_days,
                is_invoice=is_invoice,
                totals_try=totals_try,
                include_approval=include_approval,
            )
            if ok:
                self._open_file(result)
                return ok, result
            logger.error("Custom editor proforma failed, falling back: %s", result)

        return build_professional_proforma(
            self,
            template_type=template_type,
            cart_items=cart_items,
            totals=totals,
            company_name=company_name,
            customer_name=customer_name,
            is_invoice=is_invoice,
            save_path=save_path,
            currency=currency,
            project_name=project_name,
            contact_name=contact_name,
            reference_no=reference_no,
            offer_date=offer_date,
            customer_company=customer_company,
            currency_code=currency_code,
            validity_days=validity_days,
            totals_try=totals_try,
            exchange_rate=exchange_rate,
            include_approval=include_approval,
        )

    def _create_proforma_legacy(self, template_type, cart_items, totals, company_name=None, customer_name=None, is_invoice=False, save_path=None, currency="TL", project_name=None, contact_name=None, reference_no=None):
        def _fmt_desc(rd):
            txt = str(rd or "-").strip(); lines = [l.strip() for l in txt.replace("\r\n", "\n").split("\n") if l.strip()]
            if not lines: return "-"
            intro = lines[0] if ("|" in lines[0] or lines[0].lower().startswith("ref:")) else None
            bullets = [l.lstrip("-").strip() for l in (lines[1:] if intro else lines) if l.lstrip("-").strip()]
            parts = ([intro] if intro else []) + ([""] if intro and bullets else []) + [f"&bull; {b}" for b in bullets]
            return "<br/>".join(parts) if parts else (lines[0] if len(lines)==1 else txt)

        is_plh = lambda t: str(t or "").strip().lower() in {"", "müşteri seçin...", "musteri secin...", "peşin / genel müşteri", "pesin / genel musteri", "genel müşteri", "genel musteri"}
        cust = customer_name if customer_name and not is_plh(customer_name) else "Sayın İlgili"
        contact = str(contact_name or customer_name or "").strip(); contact = "" if is_plh(contact) else contact
        project = str(project_name or "").strip(); company = company_name or self.db.get_setting('company_name', 'AYEC Pro')
        st, disc, vat_r, vat_a, total = totals

        def _safe_text(value):
            return escape(str(value or "").strip())

        def _company_info_lines():
            rows = []
            phone = str(self.db.get_setting("company_phone", "") or "").strip()
            gsm = str(self.db.get_setting("company_gsm", "") or "").strip()
            email = str(self.db.get_setting("company_email", "") or "").strip()
            website = str(self.db.get_setting("company_website", "") or "").strip()
            address = str(self.db.get_setting("company_address", "") or "").strip()
            if phone or gsm:
                rows.append(" / ".join(x for x in [phone, gsm] if x))
            if email or website:
                rows.append(" / ".join(x for x in [email, website] if x))
            if address:
                rows.extend(line.strip() for line in address.splitlines() if line.strip())
            return rows
        
        if not save_path:
            sd = self._get_save_path(); sc = "".join([c for c in cust if c.isalnum() or c in (' ', '_', '-')]).strip() or "Genel_Evrak"
            save_path = os.path.join(sd, f"{('Teklif' if not is_invoice else 'Fatura')}_{template_type}_{sc}_{datetime.now().strftime('%H%M%S')}.pdf")
        
        try:
            fn, fb = self._register_fonts(); elements = []; styles = self._get_styles(); offer_terms = self._get_offer_terms_text()
            sn, sb = ParagraphStyle('N', parent=styles['Normal'], fontName=fn, fontSize=10, leading=12), ParagraphStyle('B', parent=styles['Normal'], fontName=fb, fontSize=10, leading=12)
            
            logo_path = self.db.get_setting('logo_path', '')
            clean_c = "" if is_plh(customer_name) else str(customer_name or "").strip()
            p_con, p_prj, ref_l = contact or clean_c or "Belirtilmedi", project or "Belirtilmedi", str(reference_no or f"REF-{datetime.now().strftime('%Y%m%d-%H%M')}").strip()

            def append_header(title, accent, t_back=None, s_color=colors.HexColor("#94A3B8")):
                if logo_path and os.path.exists(logo_path): img = Image(logo_path, width=58*mm, height=26*mm, kind='proportional'); img.hAlign = 'CENTER'; elements.extend([img, Spacer(1, 4)])
                ml = ParagraphStyle('ML', parent=sn, alignment=0, leading=14)
                mr = ParagraphStyle('MR', parent=sn, alignment=0, leading=14)
                brand_style = ParagraphStyle('Brand', parent=sb, fontSize=15, leading=18, alignment=1, textColor=accent, spaceAfter=10)
                company_lines = [_safe_text(line) for line in _company_info_lines()]
                info_block = "<br/>".join(line for line in company_lines if line)
                company_block = f"<b>Firma :</b> {_safe_text(company)}"
                if info_block:
                    company_block += f"<br/>{info_block}"
                suffix = "Bili\u015fim ve G\u00fcvenlik Sistemleri"
                configured_title = str(self.db.get_setting("site_title", "") or "").strip()
                if configured_title:
                    subtitle = configured_title
                else:
                    clean_company = str(company or "").strip() or "AYEC Pro"
                    if suffix.lower() in clean_company.lower():
                        subtitle = clean_company
                    else:
                        subtitle = f"{clean_company} {suffix}"
                details = (
                    f"<b>Tarih :</b> {format_turkish_date(datetime.now(), 'short')}<br/>"
                    f"<b>Ref.# :</b> {_safe_text(ref_l)}<br/>"
                    f"<b>Yetkili :</b> {_safe_text(p_con)}<br/>"
                    f"<b>Proje :</b> {_safe_text(p_prj)}"
                )
                tm = Table(
                    [[Paragraph(company_block, ml), Paragraph(details, mr)]],
                    colWidths=[118*mm, 72*mm],
                )
                tm.setStyle(TableStyle([
                    ('VALIGN',(0,0),(-1,-1),'TOP'),
                    ('LEFTPADDING',(0,0),(-1,-1),8),
                    ('RIGHTPADDING',(0,0),(-1,-1),8),
                    ('TOPPADDING',(0,0),(-1,-1),8),
                    ('BOTTOMPADDING',(0,0),(-1,-1),8),
                    ('BOX',(0,0),(-1,-1),0.6,colors.HexColor("#CBD5E1")),
                    ('LINEBEFORE',(1,0),(1,0),0.6,colors.HexColor("#CBD5E1")),
                    ('BACKGROUND',(0,0),(-1,-1),colors.HexColor("#F8FAFC")),
                ]))
                elements.extend([Paragraph(_safe_text(subtitle), brand_style), tm, Spacer(1, 12)])

            if template_type == "modern": append_header("MODERN FİYAT TEKLİFİ", colors.HexColor("#0F4C81"), colors.HexColor("#0F4C81"), colors.HexColor("#64748B")); h_bg, h_tx, r_bg, r_al = colors.HexColor("#0F4C81"), colors.white, colors.white, colors.HexColor("#EFF6FF")
            elif template_type == "corporate": append_header("KURUMSAL FİYAT TEKLİFİ", colors.HexColor("#1E3A5F"), s_color=colors.HexColor("#6B7280")); h_bg, h_tx, r_bg, r_al = colors.HexColor("#1E3A5F"), colors.white, colors.white, colors.HexColor("#F8FAFC")
            elif template_type == "minimal": append_header("ZEBRA FİYAT TEKLİFİ", colors.HexColor("#111827"), s_color=colors.HexColor("#6B7280")); h_bg, h_tx, r_bg, r_al = colors.HexColor("#111827"), colors.white, colors.white, colors.HexColor("#F3F4F6")
            else: append_header("FİYAT TEKLİFİ", colors.HexColor("#0F4C81"), s_color=colors.HexColor("#9CA3AF")); h_bg, h_tx, r_bg, r_al = colors.HexColor("#0F4C81"), colors.white, colors.white, colors.HexColor("#F7FAFC")

            cw = [12*mm, 23*mm, 39*mm, 58*mm, 13*mm, 22*mm, 23*mm] if template_type=="bulut_deri" else [10*mm, 45*mm, 55*mm, 15*mm, 30*mm, 35*mm]
            sth, stho, sthr = ParagraphStyle('TH', fontName=fb, fontSize=9, textColor=h_tx, alignment=1), ParagraphStyle('THL', fontName=fb, fontSize=9, textColor=h_tx, alignment=0), ParagraphStyle('THR', fontName=fb, fontSize=9, textColor=h_tx, alignment=2)
            std, stdc, stdr = ParagraphStyle('TD', fontName=fn, fontSize=9, textColor=colors.black, leading=10), ParagraphStyle('TDC', fontName=fn, fontSize=9, textColor=colors.black, alignment=1), ParagraphStyle('TDR', fontName=fn, fontSize=9, textColor=colors.black, alignment=2)

            if template_type == "bulut_deri": hdrs = [Paragraph("Sıra", sth), Paragraph("Marka", stho), Paragraph("Model", stho), Paragraph("Açıklama", stho), Paragraph("Adet", sth), Paragraph(f"Net Ft.{currency}", sth), Paragraph(f"Toplam {currency}", sth)]
            else: hdrs = [Paragraph("#", sth), Paragraph("HİZMET / ÜRÜN", stho), Paragraph("AÇIKLAMA", stho), Paragraph("ADET", sth), Paragraph("BİRİM FİYAT", sth), Paragraph("TUTAR", sth)]
            
            data = [hdrs]
            for i, it in enumerate(cart_items, 1):
                srv, dsc, q, p = it.get('service', 'Hizmet'), _fmt_desc(it.get('description', '-')), it.get('qty', 1), it.get('price', 0.0); lt = q * p
                pf, ltf = (f"{currency} {p:,.2f}" if currency in ["$", "€"] else f"{p:,.2f} {currency}"), (f"{currency} {lt:,.2f}" if currency in ["$", "€"] else f"{lt:,.2f} {currency}")
                if template_type == "bulut_deri":
                    rn, rc, rb, rm = str(it.get('name') or srv or "").strip(), str(it.get('code') or "").strip(), str(it.get('brand') or "").strip(), str(it.get('model') or "").strip()
                    cd = str(it.get('description') or "").replace("Stok ürün:", "").replace("Stok urun:", "").strip(" -")
                    if not rb and rc: pfx = "".join(ch for ch in rc if ch.isalpha()); rb = pfx[:12].upper() if pfx else "-"
                    if not rb: rb = "-"
                    if not rm: rm = rn or rc
                    if cd in {"", "-", rn, rm}: cd = dsc if dsc and dsc != "-" else rn
                    data.append([Paragraph(str(i), stdc), Paragraph(rb, std), Paragraph(rm, std), Paragraph(cd or rn or "-", std), Paragraph(str(q), stdc), Paragraph(f"{p:,.2f} {currency}", stdc), Paragraph(f"{lt:,.2f} {currency}", stdc)])
                else: data.append([Paragraph(str(i), stdc), Paragraph(srv, std), Paragraph(dsc, std), Paragraph(str(q), stdc), Paragraph(pf, stdc), Paragraph(ltf, stdc)])

            ti = Table(data, colWidths=cw, repeatRows=1)
            ts = [('VALIGN',(0,0),(-1,-1),'TOP'),('ALIGN',(0,0),(0,-1),'CENTER'),('ALIGN',(1,0),(2,-1),'LEFT'),('ALIGN',(3,0),(3,-1),'LEFT'),('ALIGN',(4,0),(-1,-1),'CENTER'),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),('BACKGROUND',(0,0),(-1,0),h_bg),('ROWBACKGROUNDS',(0,1),(-1,-1),[r_bg,r_al]),('GRID',(0,0),(-1,-1),0.5,colors.HexColor("#CBD5E1")),('TEXTCOLOR',(0,0),(-1,0),colors.white)]
            ti.setStyle(TableStyle(ts))
            elements.extend([ti, Spacer(1, 10)])
            
            f_curr = lambda v, s: f"{s} {v:,.2f}" if s in ["$", "€"] else f"{v:,.2f} {s}"
            t_data = [["Ara Toplam:", f_curr(st, currency)]]
            if disc > 0: t_data.append(["İskonto:", f"-{f_curr(disc, currency)}"])
            if vat_a > 0: t_data.append([f"KDV (%{int(vat_r*100)}):", f_curr(vat_a, currency)])
            t_data.append([Paragraph("GENEL TOPLAM:", ParagraphStyle('GT', fontName=fb, fontSize=11, alignment=2, leading=12)), Paragraph(f_curr(total, currency), ParagraphStyle('GTV', fontName=fb, fontSize=12, textColor=colors.red if template_type!='minimal' else colors.black, alignment=2, leading=12))])

            ftd, tcol = [], [125*mm, 30*mm, 35*mm] if template_type!="modern" else [108*mm, 39*mm, 43*mm]
            sl, sv = ParagraphStyle('SL', fontName=fn, fontSize=9, alignment=2, leading=11), ParagraphStyle('SV', fontName=fn, fontSize=9, alignment=2, leading=11)
            for r in t_data: ftd.append(["", r[0], r[1]] if isinstance(r[0], Paragraph) else ["", Paragraph(r[0], sl), Paragraph(r[1], sv)])
            tt = Table(ftd, colWidths=tcol); tbc = colors.HexColor("#DBEAFE") if template_type=="modern" else colors.HexColor("#E2E8F0")
            tt.setStyle(TableStyle([('ALIGN',(1,0),(-1,-1),'RIGHT'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LINEABOVE',(1,-1),(-1,-1),1,colors.black),('TOPPADDING',(0,-1),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),4),('BACKGROUND',(1,0),(-1,-1),tbc),('BOX',(1,0),(-1,-1),0.6,tbc)]))
            elements.extend([tt, Spacer(1, 24), Paragraph("<b>Genel Koşullar :</b>", sb)])
            for t in str(offer_terms).splitlines():
                if t.strip(): elements.extend([Paragraph(t.strip(), sn), Spacer(1, 2)])
            
            doc = SimpleDocTemplate(save_path, pagesize=A4, rightMargin=10*mm, leftMargin=10*mm, topMargin=15*mm, bottomMargin=15*mm)
            doc.build(elements); self._open_file(save_path); return True, save_path
        except Exception as e: logger.error("PDF error: %s", e); return False, str(e)

    def create_proforma_overlay(self, cart_items, totals, company_name, customer_name, save_path, currency="₺"):
        try:
            tp = self.db.get_setting('proforma_template_path', '')
            if not tp or not os.path.exists(tp): return False, "Şablon PDF dosyası bulunamadı."
            ly = self._get_proforma_layout(tp)
            if ly: return self._create_proforma_overlay_with_layout(cart_items, totals, company_name, customer_name, save_path, currency, tp, ly)
            fd, tdp = tempfile.mkstemp(suffix=".pdf"); os.close(fd); fn, fb = self._register_fonts(); styles = self._get_styles()
            sn, sb, st = ParagraphStyle('N', parent=styles['Normal'], fontName=fn, fontSize=10, leading=12), ParagraphStyle('B', parent=styles['Normal'], fontName=fb, fontSize=10, leading=12), ParagraphStyle('T', parent=styles['Normal'], fontName=fb, fontSize=18, leading=22, alignment=1)
            elements = [Spacer(1, 40*mm), Paragraph("PROFORMA TEKLİF FORMU", st), Spacer(1, 10*mm)]
            elements.append(Table([[Paragraph(f"<b>SAYIN:</b><br/>{customer_name}", sn), Paragraph(f"<b>TARİH:</b> {format_turkish_date(datetime.now(), 'short')}<br/><b>TEKLİF NO:</b> PRF-{datetime.now().strftime('%y%m%s')}", sn)]], colWidths=[100*mm, 80*mm]))
            td = [["Açıklama / Ürün", "Adet", "Birim Fiyat", "Toplam"]]
            for it in cart_items:
                q, p = it.get('count', 1), it.get('price', 0.0)
                td.append([Paragraph(it.get('name', 'Ürün'), sn), str(q), f"{p:,.2f} {currency}", f"{q*p:,.2f} {currency}"])
            itb = Table(td, colWidths=[100*mm, 20*mm, 35*mm, 35*mm]); itb.setStyle(TableStyle([('FONTNAME',(0,0),(-1,0),fb),('BACKGROUND',(0,0),(-1,0),colors.whitesmoke),('ALIGN',(1,0),(-1,-1),'CENTER'),('GRID',(0,0),(-1,-1),0.5,colors.grey)]))
            elements.extend([Spacer(1, 10*mm), itb, Spacer(1, 10)])
            stot, disc, vr, va, tf = totals
            tr = [["", "ARA TOPLAM:", f"{stot:,.2f} {currency}"], ["", f"KDV (%{vr}):", f"{va:,.2f} {currency}"], ["", "GENEL TOPLAM:", f"{tf:,.2f} {currency}"]]
            tt = Table(tr, colWidths=[100*mm, 45*mm, 45*mm]); tt.setStyle(TableStyle([('FONTNAME',(1,2),(2,2),fb),('ALIGN',(1,0),(2,-1),'RIGHT')]))
            elements.append(tt); doc = SimpleDocTemplate(tdp, pagesize=A4, rightMargin=10*mm, leftMargin=10*mm, topMargin=10*mm, bottomMargin=10*mm); doc.build(elements)
            wr, tr, dr = PdfWriter(), PdfReader(tp), PdfReader(tdp); tpge = tr.pages[0]; tpge.merge_page(dr.pages[0]); wr.add_page(tpge)
            for i in range(1, len(dr.pages)): wr.add_page(dr.pages[i])
            with open(save_path, "wb") as f: wr.write(f)
            if os.path.exists(tdp): os.remove(tdp)
            self._open_file(save_path); return True, save_path
        except Exception as e: logger.error(f"Overlay PDF error: {e}"); return False, str(e)

    def _get_proforma_layout(self, tp):
        lj = self.db.get_setting("proforma_template_layout", "")
        if not lj:
            return None
        try:
            d = json.loads(lj)
        except:
            return None
        tpl = d.get("templates", {}).get(os.path.abspath(tp))
        if not tpl:
            return None
        if "pages" in tpl:
            pi = int(tpl.get("default_page", 0))
            pgs = tpl.get("pages", {})
            pd = pgs.get(str(pi))
            if not pd and pgs:
                fk = sorted(pgs.keys(), key=lambda x: int(x) if str(x).isdigit() else x)[0]
                pd, pi = pgs.get(fk, {}), int(fk) if str(fk).isdigit() else 0
            return {"page_index": pi, "fields": (pd or {}).get("fields", {})}
        return {"page_index": 0, "fields": tpl.get("fields", {})}

    def _create_proforma_overlay_with_layout(self, cart_items, totals, company_name, customer_name, save_path, currency, tp, ly):
        try:
            fd, tdp = tempfile.mkstemp(suffix=".pdf")
            os.close(fd)
            tr = PdfReader(tp)
            pi = int(ly.get("page_index", 0))
            pge = tr.pages[pi] if 0 <= pi < len(tr.pages) else tr.pages[0]
            pw, ph = float(pge.mediabox.width), float(pge.mediabox.height)
            fn, fb = self._register_fonts()
            styles = self._get_styles()
            sn = ParagraphStyle('N', parent=styles['Normal'], fontName=fn, fontSize=10, leading=12)
            sb = ParagraphStyle('B', parent=styles['Normal'], fontName=fb, fontSize=10, leading=12)
            st = ParagraphStyle('T', parent=styles['Normal'], fontName=fn, fontSize=9, leading=11)
            cv = rl_canvas.Canvas(tdp, pagesize=(pw, ph))
            flds = ly.get("fields", {})

            def dp(txt, r, s):
                if not r:
                    return
                x, y, w, h = r
                frame = Frame(x, ph - (y + h), w, h, 0, 0, 0, 0, 0)
                frame.addFromList([Paragraph(txt, s)], cv)

            def rf(k):
                if k in flds:
                    f = flds[k]
                    return float(f["x"]), float(f["y"]), float(f["w"]), float(f["h"])
                return None

            dp(company_name, rf("company_name"), sb)
            dp(customer_name, rf("customer_name"), sn)
            dp(format_turkish_date(datetime.now(), 'short'), rf("date"), sn)
            trc = rf("table")
            if trc:
                x, y, w, h = trc
                td = [[Paragraph("Açıklama / Ürün", sb), Paragraph("Adet", sb), Paragraph("Birim Fiyat", sb), Paragraph("Toplam", sb)]]
                for it in cart_items:
                    q = it.get('qty', it.get('count', 1))
                    p = float(it.get('price', 0.0) or 0.0)
                    td.append([
                        Paragraph(str(it.get('service') or it.get('name') or "Ürün"), st),
                        Paragraph(str(q), st),
                        Paragraph(f"{p:,.2f} {currency}", st),
                        Paragraph(f"{q * p:,.2f} {currency}", st)
                    ])
                tt = Table(td, colWidths=[w * 0.48, w * 0.12, w * 0.2, w * 0.2], repeatRows=1)
                tt.setStyle(TableStyle([
                    ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.whitesmoke)
                ]))
                Frame(x, ph - (y + h), w, h, 0, 0, 0, 0, 0).addFromList([tt], cv)

            tc = rf("totals")
            if tc:
                x, y, w, h = tc
                stot, disc, vr, va, tf = totals
                rs = [["Ara Toplam:", f"{stot:,.2f} {currency}"]]
                if disc:
                    rs.append(["İskonto:", f"{disc:,.2f} {currency}"])
                if va:
                    rs.append([f"KDV (%{int(vr * 100)}):", f"{va:,.2f} {currency}"])
                rs.append(["Genel Toplam:", f"{tf:,.2f} {currency}"])
                ttt = Table(rs, colWidths=[w * 0.6, w * 0.4])
                ttt.setStyle(TableStyle([
                    ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                    ('FONTNAME', (0, -1), (1, -1), fb)
                ]))
                Frame(x, ph - (y + h), w, h, 0, 0, 0, 0, 0).addFromList([ttt], cv)

            cv.save()
            wr, dr = PdfWriter(), PdfReader(tdp)
            dpge = dr.pages[0]
            for i, p in enumerate(tr.pages):
                if i == pi:
                    p.merge_page(dpge)
                wr.add_page(p)
            for i in range(1, len(dr.pages)):
                wr.add_page(dr.pages[i])
            with open(save_path, "wb") as f:
                wr.write(f)
            if os.path.exists(tdp):
                os.remove(tdp)
            self._open_file(save_path)
            return True, save_path
        except Exception as e:
            logger.error(f"Overlay PDF layout error: {e}")
            return False, str(e)
