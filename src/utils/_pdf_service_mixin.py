# -*- coding: utf-8 -*-
import os
import html
import json
import base64
import hashlib
import hmac
from urllib.parse import quote
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A3, A4, A5, landscape, portrait
from reportlab.platypus import KeepInFrame, SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.graphics.barcode import createBarcodeDrawing
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF
from reportlab.pdfgen import canvas
from src.utils.logger import logger
from src.utils.date_utils import format_turkish_date, format_datetime_turkish

class PDFServiceMixin:
    @staticmethod
    def _service_tracking_token(tracking_no):
        value = str(tracking_no or '').strip()
        encoded = base64.urlsafe_b64encode(value.encode('utf-8')).decode('ascii').rstrip('=')
        secret = os.environ.get('AYEC_TRACKING_SECRET') or os.environ.get('AYEC_SECRET_KEY') or 'ayecpro-development-tracking-secret'
        signature = hmac.new(secret.encode('utf-8'), value.encode('utf-8'), hashlib.sha256).hexdigest()[:32]
        return f'{encoded}.{signature}'

    @classmethod
    def _service_tracking_url(cls, tracking_no):
        base_url = os.environ.get('AYEC_SERVICE_TRACKING_URL', 'https://ayecpro.com/servis/takip').strip().rstrip('/')
        return f'{base_url}/{quote(cls._service_tracking_token(tracking_no), safe=".")}'

    def create_device_label(self, device_data, width_mm=None, height_mm=None):
        try:
            fn, fb = self._register_fonts()
            tno = device_data[1]
            cnm = device_data[2][:15]
            mdl = f"{device_data[3]} {device_data[4]}"[:18]
            dstr = format_turkish_date(datetime.now(), "short")
            lw, lh = 50 * mm, 30 * mm
            sd = self._get_save_path()
            filename = os.path.join(sd, f"Label_{tno}.pdf")
            doc = SimpleDocTemplate(filename, pagesize=(lw, lh), rightMargin=1 * mm, leftMargin=1 * mm, topMargin=1 * mm, bottomMargin=1 * mm)
            elms = []
            st = getSampleStyleSheet()
            elms.append(Paragraph(self.db.get_setting('company_name', 'AYEC Pro').upper()[:15], ParagraphStyle('T', fontName=fn, fontSize=6, alignment=1, spaceAfter=1)))
            elms.append(Paragraph(f"<b>{mdl}</b>", ParagraphStyle('SB', fontName=fb, fontSize=7, alignment=1)))
            elms.append(Paragraph(cnm, ParagraphStyle('S', fontName=fn, fontSize=6, alignment=1, spaceAfter=2)))
            d = createBarcodeDrawing('Code128', value=tno, barHeight=7 * mm, barWidth=0.8, humanReadable=False)
            d.hAlign = 'CENTER'
            elms.append(d)
            elms.append(Paragraph(f"<b>{tno}</b>  |  {dstr}", ParagraphStyle('TC', fontName=fn, fontSize=6, alignment=1, spaceBefore=1)))
            doc.build(elms); self._open_file(filename); return True, filename
        except Exception as e: logger.error("Label error: %s", e); return False, str(e)

    def create_zpl_label(self, device_data):
        try:
            tno = device_data[1]
            cnm = device_data[2][:20]
            b = device_data[3] or ""
            m = device_data[4] or ""
            mdl = f"{b} {m}"[:20]
            dstr = format_turkish_date(datetime.now(), "short")
            cmp = self.db.get_setting('company_name', 'AYEC Pro').upper()
            zpl = f"^XA\n^PW400\n^LL240\n^MD15\n^FO10,10^A0N,20,20^FD{cmp}^FS\n^FO10,35^A0N,25,25^FD{mdl}^FS\n^FO10,65^A0N,20,20^FD{cnm}^FS\n^FO20,95^BCN,50,Y,N,N\n^FD{tno}^FS\n^FO10,180^A0N,18,18^FDTarih: {dstr}^FS\n^XZ"
            sd = self._get_save_path()
            fn = os.path.join(sd, f"Label_{tno}.zpl")
            with open(fn, "w", encoding="utf-8") as f: f.write(zpl)
            return True, fn
        except Exception as e: logger.error("ZPL Error: %s", e); return False, str(e)

    def create_service_receipt(self, device_data, used_parts, labor_cost):
        try:
            fn, fb = self._register_fonts()
            tno = str(device_data[1])
            cust = str(device_data[2])
            dinfo = f"{device_data[3]} {device_data[4]}"
            dstr = format_datetime_turkish(datetime.now())
            cn = self.db.get_setting('company_name', 'AYEC Pro')
            cp = self.db.get_setting('company_phone', '')
            ca = self.db.get_setting('company_address', '')
            sd = self._get_save_path()
            fnm = os.path.join(sd, f"Servis_Fisi_{tno}.pdf")
            doc = SimpleDocTemplate(fnm, pagesize=A4, rightMargin=15 * mm, leftMargin=15 * mm, topMargin=15 * mm, bottomMargin=15 * mm)
            elms = []
            st = getSampleStyleSheet()
            elms.append(Paragraph(cn.upper(), ParagraphStyle('H1', fontName=fb, fontSize=18, alignment=1)))
            elms.append(Paragraph(f"{ca} | Tel: {cp}", ParagraphStyle('C', alignment=1, fontSize=8)))
            elms.append(Spacer(1, 10 * mm))
            elms.append(Table([[Paragraph("TEKNİK SERVİS FORMU", ParagraphStyle('T', fontName=fb, fontSize=14)), Paragraph(f"Tarih: {dstr}", ParagraphStyle('R', alignment=2))]], colWidths=[120*mm, 60*mm]))
            it = Table([[Paragraph(f"<b>Müşteri:</b> {cust}", ParagraphStyle('I', fontName=fn, fontSize=10, leading=14)), Paragraph(f"<b>Takip No:</b> {tno}", ParagraphStyle('I', fontName=fn, fontSize=10, leading=14))], [Paragraph(f"<b>Cihaz:</b> {dinfo}", ParagraphStyle('I', fontName=fn, fontSize=10, leading=14)), Paragraph(f"<b>Seri No:</b> {device_data[5] or '-'}", ParagraphStyle('I', fontName=fn, fontSize=10, leading=14))]], colWidths=[90*mm, 90*mm])
            it.setStyle(TableStyle([('BOX',(0,0),(-1,-1),0.5,colors.grey),('PADDING',(0,0),(-1,-1),8)])); elms.extend([Spacer(1, 5*mm), it, Spacer(1, 10*mm), Paragraph("YAPILAN İŞLEMLER VE KULLANILAN PARÇALAR", ParagraphStyle('ST', fontName=fb, fontSize=11)), Spacer(1, 3*mm)])
            pd = [[Paragraph("Sıra", ParagraphStyle('TH', fontName=fb, alignment=1)), Paragraph("İşlem / Parça", ParagraphStyle('TH', fontName=fb)), Paragraph("Tutar", ParagraphStyle('TH', fontName=fb, alignment=2))]]
            tp = 0
            for i, (n, p) in enumerate(used_parts, 1): pd.append([str(i), n, f"{p:.2f} ₺"]); tp += p
            pd.append([str(len(used_parts)+1), "Teknik Servis İşçilik Ücreti", f"{labor_cost:.2f} ₺"])
            tpbt = Table(pd, colWidths=[15*mm, 135*mm, 30*mm]); tpbt.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.lightgrey),('GRID',(0,0),(-1,-1),0.5,colors.grey),('ALIGN',(-1,0),(-1,-1),'RIGHT')]))
            elms.extend([tpbt, Table([["", "TOPLAM TUTAR:", f"<b>{tp+labor_cost:.2f} ₺</b>"]], colWidths=[120*mm, 30*mm, 30*mm])])
            nts = self.db.get_setting('service_terms', "Cihaz tesliminden itibaren 3 ay servis garantisi altındadır."); elms.extend([Spacer(1, 20*mm), Paragraph("<b>Servis Şartları:</b>", ParagraphStyle('NT', fontName=fb, fontSize=9)), Paragraph(nts, ParagraphStyle('N', fontSize=8, leading=10)), Spacer(1, 20*mm), Table([[Paragraph("<b>Müşteri İmzası</b>", ParagraphStyle('Sig', alignment=1)), Paragraph("<b>Servis Yetkilisi</b>", ParagraphStyle('Sig', alignment=1))]], colWidths=[90*mm, 90*mm])])
            doc.build(elms); self._open_file(fnm); return True, fnm
        except Exception as e: logger.error("Service Receipt Error: %s", e); return False, str(e)

    def create_automotive_service_form_pdf(self, device_data, service_form, used_parts, labor_cost):
        try:
            fn, fb = self._register_fonts(); st = getSampleStyleSheet(); ts, hs = ParagraphStyle("AT", fontName=fb, fontSize=16, alignment=1, leading=20), ParagraphStyle("AH", fontName=fb, fontSize=11, leading=14, textColor=colors.HexColor("#1f3b5b"))
            bs, ss = ParagraphStyle("AB", fontName=fn, fontSize=9, leading=12), ParagraphStyle("AS", fontName=fn, fontSize=8, leading=10)
            tno, cn, vb, vm = str(device_data.get("tracking_no") or "SERVIS"), str(device_data.get("customer_name") or "-"), str(device_data.get("device_brand") or ""), str(device_data.get("device_model") or "")
            vp, vv, ec = str(service_form.get("vehicle_plate") or "-"), str(service_form.get("vehicle_vin") or "-"), str(service_form.get("engine_code") or "-")
            eo, exo, fe, fex = str(service_form.get("entry_odometer") or "-"), str(service_form.get("exit_odometer") or "-"), str(service_form.get("fuel_level_entry") or "-"), str(service_form.get("fuel_level_exit") or "-")
            an, at, kt, ca = str(service_form.get("acceptance_notes") or ""), str(service_form.get("customer_approval_text") or "Onayliyorum."), str(service_form.get("kvkk_text") or "Veriler islenir."), str(service_form.get("created_at") or datetime.now().strftime("%Y-%m-%d"))
            cli, dpl = [], {"items": [], "general_note": ""}
            try: cli = json.loads(service_form.get("checklist_json") or "[]")
            except: pass
            try: dpl = json.loads(service_form.get("damage_marks_json") or "{}")
            except: pass
            comp, cph, cadr = self.db.get_setting("company_name", "AYEC Pro"), self.db.get_setting("company_phone", ""), self.db.get_setting("company_address", "")
            sd = self._get_save_path(); fnm = os.path.join(sd, f"Otomotiv_Servis_Formu_{tno}.pdf")
            doc = SimpleDocTemplate(fnm, pagesize=A4, rightMargin=12*mm, leftMargin=12*mm, topMargin=12*mm, bottomMargin=12*mm); elms = []
            elms.extend([Paragraph(comp.upper(), ts), Paragraph(f"{cadr} | Tel: {cph}", ParagraphStyle("AC", parent=ss, alignment=1)), Spacer(1, 4*mm), Paragraph("OTOMOTIV SERVIS BAKIM VE KONTROL FORMU", ts), Spacer(1, 4*mm)])
            ir = [[Paragraph("<b>Musteri</b>", bs), Paragraph(cn, bs), Paragraph("<b>Takip No</b>", bs), Paragraph(tno, bs)], [Paragraph("<b>Arac</b>", bs), Paragraph(f"{vb} {vm}".strip() or "-", bs), Paragraph("<b>Plaka</b>", bs), Paragraph(vp, bs)], [Paragraph("<b>VIN / Sasi</b>", bs), Paragraph(vv, bs), Paragraph("<b>Motor Kodu</b>", bs), Paragraph(ec, bs)], [Paragraph("<b>Giris KM</b>", bs), Paragraph(eo, bs), Paragraph("<b>Cikis KM</b>", bs), Paragraph(exo, bs)], [Paragraph("<b>Giris Yakit</b>", bs), Paragraph(fe, bs), Paragraph("<b>Cikis Yakit</b>", bs), Paragraph(fex, bs)]]
            it = Table(ir, colWidths=[28*mm, 62*mm, 28*mm, 62*mm]); it.setStyle(TableStyle([("BOX",(0,0),(-1,-1),0.5,colors.HexColor("#aab7c4")),("INNERGRID",(0,0),(-1,-1),0.35,colors.HexColor("#d9e1e8")),("BACKGROUND",(0,0),(-1,0),colors.HexColor("#f5f8fb"))])); elms.extend([it, Spacer(1, 4*mm)])
            if an: elms.extend([Paragraph("Servis Kabul Notu", hs), Paragraph(an.replace("\n", "<br/>"), bs), Spacer(1, 3*mm)])
            clr = [[Paragraph("<b>Grup</b>", bs), Paragraph("<b>Madde</b>", bs), Paragraph("<b>Durum</b>", bs), Paragraph("<b>Not</b>", bs)]]
            for itm in cli: clr.append([Paragraph(str(itm.get("group") or "-"), ss), Paragraph(str(itm.get("label") or "-"), ss), Paragraph(str(itm.get("status") or "-"), ss), Paragraph(str(itm.get("note") or "-"), ss)])
            clt = Table(clr if len(clr)>1 else (clr+[["-","Kontrol yok","-","-"]]), colWidths=[32*mm, 72*mm, 28*mm, 48*mm], repeatRows=1); clt.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#e9f1f8")),("GRID",(0,0),(-1,-1),0.35,colors.HexColor("#c7d3dd"))])); elms.extend([Paragraph("Hizli Kontrol Listesi", hs), clt, Spacer(1, 4*mm)])
            drr = [[Paragraph("<b>Yon</b>", bs), Paragraph("<b>Bolge</b>", bs), Paragraph("<b>Durum</b>", bs)]]
            for itm in dpl.get("items", []): drr.append([Paragraph(str(itm.get("side") or "-"), ss), Paragraph(str(itm.get("zone") or "-"), ss), Paragraph(str(itm.get("status") or "-"), ss)])
            dt = Table(drr if len(drr)>1 else (drr+[["-","Kayit yok","-"]]), colWidths=[36*mm, 90*mm, 54*mm], repeatRows=1); dt.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#fff2e8")),("GRID",(0,0),(-1,-1),0.35,colors.HexColor("#d8c4b2"))])); elms.extend([Paragraph("Hasar Tespit Kayitlari", hs), dt, Spacer(1, 4*mm)])
            tp = 0.0; pr = [[Paragraph("<b>Kalem</b>", bs), Paragraph("<b>Tutar</b>", bs)]]
            for p in used_parts or []: pn = p[0] if not isinstance(p, dict) else p.get("part_name", "Parca"); prc = float((p[1] if not isinstance(p, dict) else p.get("price", 0)) or 0); tp += prc; pr.append([Paragraph(str(pn), ss), Paragraph(f"{prc:.2f} TL", ss)])
            pr.extend([[Paragraph("Iscilik", bs), Paragraph(f"{float(labor_cost or 0):.2f} TL", bs)], [Paragraph("<b>Genel Toplam</b>", bs), Paragraph(f"<b>{(tp+float(labor_cost or 0)):.2f} TL</b>", bs)]]); pt = Table(pr, colWidths=[130*mm, 50 * mm]); pt.setStyle(TableStyle([("GRID",(0,0),(-1,-1),0.35,colors.HexColor("#c7d3dd")),("BACKGROUND",(0,0),(-1,0),colors.HexColor("#edf6ed")),("ALIGN",(1,0),(1,-1),"RIGHT")])); elms.extend([Paragraph("Parca / Iscilik Ozeti", hs), pt, Spacer(1, 5*mm)])
            as_, ks = ("Onaylandi" if int(service_form.get("customer_approval") or 0) else "Bekliyor"), ("Onaylandi" if int(service_form.get("kvkk_approval") or 0) else "Bekliyor")
            letr = [[Paragraph("<b>Musteri Onayi</b>", bs), Paragraph(at, ss), Paragraph(as_, ss)], [Paragraph("<b>KVKK</b>", bs), Paragraph(kt, ss), Paragraph(ks, ss)]]; let = Table(letr, colWidths=[30*mm, 120*mm, 30*mm]); let.setStyle(TableStyle([("GRID",(0,0),(-1,-1),0.35,colors.HexColor("#c7d3dd"))])); elms.extend([Paragraph("Onay ve Yasal Metin", hs), let, Spacer(1, 4*mm), Paragraph(f"Olusturulma: {ca}", ss)])
            doc.build(elms); self._open_file(fnm); return True, fnm
        except Exception as e: logger.error("Automotive Service Form PDF Error: %s", e); return False, str(e)

    def _service_value(self, data, key, index=None, default=""):
        if data is None:
            return default
        if isinstance(data, dict):
            value = data.get(key, default)
        elif hasattr(data, "keys"):
            try:
                value = data[key]
            except (KeyError, IndexError):
                value = default
        elif index is not None:
            try:
                value = data[index]
            except (IndexError, TypeError):
                value = default
        else:
            value = default
        return default if value is None else value

    def _service_text(self, value, default="-"):
        text = str(value or "").strip()
        return text or default

    def _safe_html(self, value):
        return html.escape(self._service_text(value), quote=True).replace("\n", "<br/>")

    def _service_part_values(self, part):
        name = self._service_value(part, "part_name", 0)
        for key in ("name", "product_name", "description"):
            if not name:
                name = self._service_value(part, key, 0)
        quantity = self._service_value(part, "quantity")
        if quantity in ("", None):
            quantity = self._service_value(part, "qty")
        if quantity in ("", None):
            quantity = self._service_value(part, "amount")
        if quantity in ("", None):
            quantity = self._service_value(part, "quantity", 2, 1)
        try:
            quantity = float(quantity or 1)
        except (TypeError, ValueError):
            quantity = 1.0
        total = self._service_value(part, "line_total")
        for key in ("total", "total_price", "price"):
            if total in ("", None):
                total = self._service_value(part, key)
        if total in ("", None):
            total = self._service_value(part, "price", 1)
        if total in ("", None):
            unit_price = self._service_value(part, "unit_price")
            try:
                total = float(unit_price or 0) * quantity
            except (TypeError, ValueError):
                total = 0.0
        try:
            total = float(total or 0)
        except (TypeError, ValueError):
            total = 0.0
        return self._service_text(name), quantity, total

    def _service_print_context(self, device_data, used_parts, labor_cost):
        tracking = self._service_text(self._service_value(device_data, "tracking_no", 1, "SERVIS"))
        customer = self._service_text(self._service_value(device_data, "customer_name", 2))
        brand = self._service_text(self._service_value(device_data, "device_brand", 3))
        model = self._service_text(self._service_value(device_data, "device_model", 4))
        serial = self._service_text(self._service_value(device_data, "serial_no", 5))
        fault = self._service_value(device_data, "reported_fault")
        if not fault:
            fault = self._service_value(device_data, "fault_description")
        notes = self._service_value(device_data, "repair_notes")
        if not notes:
            notes = self._service_value(device_data, "technician_notes")
        if not notes:
            notes = self._service_value(device_data, "description")
        parts = [self._service_part_values(part) for part in (used_parts or [])]
        try:
            labor = float(labor_cost or 0)
        except (TypeError, ValueError):
            labor = 0.0
        return {
            "tracking": tracking,
            "customer": customer,
            "brand": brand,
            "model": model,
            "serial": serial,
            "fault": self._service_text(fault),
            "notes": self._service_text(notes),
            "status": self._service_text(self._service_value(device_data, "status")),
            "delivery": self._service_text(
                self._service_value(device_data, "delivery_method")
                or self._service_value(device_data, "delivery_type")
            ),
            "delivered_by": self._service_text(
                self._service_value(device_data, "delivered_by_name")
            ),
            "delivered_phone": self._service_text(
                self._service_value(device_data, "delivered_by_phone")
            ),
            "parts": parts,
            "labor": labor,
            "total": sum(row[2] for row in parts) + labor,
        }

    def _service_company_context(self):
        get = self.db.get_setting
        return {
            "name": self._service_text(get("company_name", "AYEC Pro"), "AYEC Pro"),
            "phone": self._service_text(get("company_phone", ""), ""),
            "gsm": self._service_text(get("company_gsm", ""), ""),
            "email": self._service_text(get("company_email", ""), ""),
            "website": self._service_text(get("company_website", ""), ""),
            "address": self._service_text(get("company_address", ""), ""),
            "cargo": self._service_text(get("cargo_company", ""), ""),
            "cargo_no": self._service_text(get("cargo_deal_no", ""), ""),
            "logo": str(get("logo_path", "") or "").strip(),
        }

    def _service_customer_context(self, device_data):
        if isinstance(device_data, dict):
            data = device_data
        elif hasattr(device_data, "keys"):
            data = {key: device_data[key] for key in device_data.keys()}
        else:
            data = {}
        result = {
            "name": self._service_text(data.get("customer_name")),
            "phone": self._service_text(data.get("customer_contact"), ""),
            "phone2": "",
            "email": "",
            "address": self._service_text(data.get("customer_address"), ""),
            "company": "",
        }
        customer_id = data.get("customer_id")
        if not customer_id:
            return result
        try:
            row = self.db.cursor.execute(
                "SELECT * FROM customers WHERE id=?", (customer_id,)
            ).fetchone()
            if row and hasattr(row, "keys"):
                customer = {key: row[key] for key in row.keys()}
                result.update({
                    "name": self._service_text(customer.get("name"), result["name"]),
                    "phone": self._service_text(customer.get("phone"), result["phone"]),
                    "phone2": self._service_text(customer.get("phone2"), ""),
                    "email": self._service_text(customer.get("email"), ""),
                    "address": self._service_text(customer.get("address"), result["address"]),
                    "company": self._service_text(customer.get("company_name"), ""),
                })
        except Exception as exc:
            logger.warning("Customer print context lookup failed: %s", exc)
        return result

    def _service_logo_flowable(self, max_width, max_height):
        path = self._service_company_context()["logo"]
        if not path or not os.path.exists(path):
            return None
        try:
            image = RLImage(path)
            scale = min(max_width / image.imageWidth, max_height / image.imageHeight)
            image.drawWidth = image.imageWidth * scale
            image.drawHeight = image.imageHeight * scale
            return image
        except Exception as exc:
            logger.warning("Company logo could not be loaded: %s", exc)
            return None

    def _service_pdf_styles(self, normal_font, bold_font, toner_friendly=False):
        accent = colors.black if toner_friendly else colors.HexColor("#12395d")
        return {
            "title": ParagraphStyle("ServiceTitle", fontName=bold_font, fontSize=17, leading=21, alignment=1, textColor=accent),
            "subtitle": ParagraphStyle("ServiceSubtitle", fontName=normal_font, fontSize=8, leading=10, alignment=1, textColor=accent),
            "section": ParagraphStyle("ServiceSection", fontName=bold_font, fontSize=10, leading=13, textColor=accent),
            "body": ParagraphStyle("ServiceBody", fontName=normal_font, fontSize=9, leading=12),
            "small": ParagraphStyle("ServiceSmall", fontName=normal_font, fontSize=8, leading=10),
            "header": ParagraphStyle("ServiceHeader", fontName=bold_font, fontSize=8, leading=10, textColor=colors.black if toner_friendly else colors.white, alignment=1),
            "right": ParagraphStyle("ServiceRight", fontName=normal_font, fontSize=9, leading=12, alignment=2),
        }

    def _build_service_info_table(self, ctx, styles, width=180 * mm, toner_friendly=False):
        rows = [
            [Paragraph("MUSTERI", styles["section"]), Paragraph(self._safe_html(ctx["customer"]), styles["body"]), Paragraph("TAKIP NO", styles["section"]), Paragraph(self._safe_html(ctx["tracking"]), styles["body"])],
            [Paragraph("CIHAZ", styles["section"]), Paragraph(self._safe_html(f"{ctx['brand']} {ctx['model']}"), styles["body"]), Paragraph("SERI NO", styles["section"]), Paragraph(self._safe_html(ctx["serial"]), styles["body"])],
            [Paragraph("DURUM", styles["section"]), Paragraph(self._safe_html(ctx["status"]), styles["body"]), Paragraph("TESLIM SEKLI", styles["section"]), Paragraph(self._safe_html(ctx["delivery"]), styles["body"])],
        ]
        table = Table(
            rows,
            colWidths=[width * 0.15, width * 0.35, width * 0.15, width * 0.35],
        )
        table_style = [
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#a9bac8")),
            ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d5dfe7")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("PADDING", (0, 0), (-1, -1), 3 if toner_friendly else 6),
        ]
        if not toner_friendly:
            table_style.extend([
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#edf4f9")),
                ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#edf4f9")),
            ])
        table.setStyle(TableStyle(table_style))
        return table

    def _build_service_parts_table(self, ctx, styles, width=180 * mm, toner_friendly=False):
        rows = [[Paragraph("SIRA", styles["header"]), Paragraph("URUN / ISLEM", styles["header"]), Paragraph("ADET", styles["header"]), Paragraph("TUTAR", styles["header"])]]
        for number, (name, quantity, total) in enumerate(ctx["parts"], 1):
            rows.append([str(number), Paragraph(self._safe_html(name), styles["body"]), f"{quantity:g}", Paragraph(f"{total:,.2f} TL", styles["right"])])
        if ctx["labor"] > 0:
            rows.append([str(len(ctx["parts"]) + 1), Paragraph("SERVIS ISCILIK", styles["body"]), "1", Paragraph(f"{ctx['labor']:,.2f} TL", styles["right"])])
        if len(rows) == 1:
            rows.append(["1", Paragraph("KAYITLI PARCA YOK", styles["body"]), "-", Paragraph("0.00 TL", styles["right"])])
        table = Table(
            rows,
            colWidths=[width * 0.08, width * 0.58, width * 0.12, width * 0.22],
            repeatRows=1,
        )
        table_style = [
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#b6c8d6")),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (2, 0), (2, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("PADDING", (0, 0), (-1, -1), 3 if toner_friendly else 5),
        ]
        if toner_friendly:
            table_style.extend([
                ("LINEABOVE", (0, 0), (-1, 0), 0.8, colors.black),
                ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.black),
            ])
        else:
            table_style.extend([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#155c88")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f6fa")]),
            ])
        table.setStyle(TableStyle(table_style))
        return table

    @staticmethod
    def _service_qr_drawing(tracking_no, size=24 * mm):
        payload = PDFServiceMixin._service_tracking_url(tracking_no)
        qr_code = QrCodeWidget(payload)
        x1, y1, x2, y2 = qr_code.getBounds()
        width = max(x2 - x1, 1)
        height = max(y2 - y1, 1)
        scale = min(size / width, size / height)
        drawing = Drawing(
            size,
            size,
            transform=[
                scale,
                0,
                0,
                scale,
                -x1 * scale,
                -y1 * scale,
            ],
        )
        drawing.add(qr_code)
        return drawing

    def _resolve_service_pagesize(self, page_size=None, orientation=None):
        page_name = str(
            page_size
            or self.db.get_setting("print_document_page_size", "A4")
            or "A4"
        ).upper()
        orientation_name = str(
            orientation
            or self.db.get_setting("print_document_orientation", "portrait")
            or "portrait"
        ).lower()
        base = {"A3": A3, "A4": A4, "A5": A5}.get(page_name, A4)
        return landscape(base) if orientation_name == "landscape" else portrait(base)

    def _finish_service_output(self, filename):
        if not getattr(self, "_suppress_service_open", False):
            self._open_file(filename)

    def _create_service_pdf(
        self,
        device_data,
        used_parts,
        labor_cost,
        pagesize=None,
        prefix="Servis_Fisi",
        compact=False,
        orientation=None,
        toner_friendly=False,
    ):
        normal_font, bold_font = self._register_fonts()
        ctx = self._service_print_context(device_data, used_parts, labor_cost)
        company_info = self._service_company_context()
        company = company_info["name"]
        phone = company_info["phone"] or company_info["gsm"]
        address = company_info["address"]
        save_dir = self._get_save_path()
        filename = os.path.join(save_dir, f"{prefix}_{self._safe_filename(ctx['tracking'])}.pdf")
        margin = 6 if toner_friendly else (9 if compact else 14)
        resolved_pagesize = (
            pagesize
            if isinstance(pagesize, (tuple, list))
            else self._resolve_service_pagesize(pagesize, orientation)
        )
        doc = SimpleDocTemplate(filename, pagesize=resolved_pagesize, rightMargin=margin * mm, leftMargin=margin * mm, topMargin=margin * mm, bottomMargin=margin * mm)
        styles = self._service_pdf_styles(normal_font, bold_font, toner_friendly=toner_friendly)
        if toner_friendly:
            styles["title"].fontSize = 13
            styles["title"].leading = 15
            styles["section"].fontSize = 8.5
            styles["section"].leading = 10
            styles["body"].fontSize = 8
            styles["body"].leading = 9.5
            styles["right"].fontSize = 8
            styles["right"].leading = 9.5
            styles["small"].fontSize = 7
            styles["small"].leading = 8.5
            styles["header"].fontSize = 7.5
            styles["header"].leading = 9
        if doc.width < 150 * mm:
            for key in ("body", "right"):
                styles[key].fontSize = 7.5
                styles[key].leading = 9
            styles["section"].fontSize = 8.5
            styles["section"].leading = 10
        logo = None if toner_friendly else self._service_logo_flowable(42 * mm, 16 * mm)
        brand_cell = logo or Paragraph(self._safe_html(company).upper(), styles["title"])
        company_lines = [] if toner_friendly else [company]
        if address:
            company_lines.append(address)
        if phone:
            company_lines.append(f"Tel: {phone}")
        if company_info["email"]:
            company_lines.append(company_info["email"])
        section_gap = 2 * mm if toner_friendly else 5 * mm
        small_gap = 1.5 * mm if toner_friendly else 3 * mm
        header_line = colors.black if toner_friendly else colors.HexColor("#12395d")
        story = [
            Table(
                [[brand_cell, Paragraph("<br/>".join(self._safe_html(line) for line in company_lines if line), styles["small"]) ]],
                colWidths=[doc.width * (0.34 if toner_friendly else 0.28), doc.width * (0.66 if toner_friendly else 0.72)],
                style=TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.8, header_line),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3 if toner_friendly else 5),
                ]),
            ),
            Spacer(1, section_gap),
            Table([[Paragraph("DETAYLI SERVIS FISI", styles["section"]), Paragraph(datetime.now().strftime("%Y-%m-%d %H:%M"), styles["right"])]], colWidths=[doc.width * 0.66, doc.width * 0.34]),
            Spacer(1, small_gap),
            self._build_service_info_table(ctx, styles, doc.width, toner_friendly=toner_friendly),
            Spacer(1, small_gap),
            Table(
                [[
                    Paragraph("CIHAZ SAHIBI", styles["section"]),
                    Paragraph(self._safe_html(ctx["customer"]), styles["body"]),
                    Paragraph("TESLIM EDEN", styles["section"]),
                    Paragraph(self._safe_html(ctx["delivered_by"]), styles["body"]),
                ], [
                    Paragraph("ILETISIM", styles["section"]),
                    Paragraph(self._safe_html(self._service_value(device_data, "customer_contact")), styles["body"]),
                    Paragraph("TESLIM EDEN TEL", styles["section"]),
                    Paragraph(self._safe_html(ctx["delivered_phone"]), styles["body"]),
                ]],
                colWidths=[doc.width * 0.18, doc.width * 0.32, doc.width * 0.18, doc.width * 0.32],
                style=TableStyle([
                    ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#a9bac8")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d5dfe7")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("PADDING", (0, 0), (-1, -1), 3 if toner_friendly else 5),
                ] + ([] if toner_friendly else [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#edf4f9")),
                    ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#edf4f9")),
                ])),
            ),
            Spacer(1, section_gap),
            Table(
                [[
                    self._service_qr_drawing(
                        ctx["tracking"],
                        size=16 * mm if toner_friendly else (20 * mm if compact else 24 * mm),
                    ),
                    Paragraph(
                        "Takip QR<br/><b>"
                        + self._safe_html(ctx["tracking"])
                        + "</b><br/>Servis kaydini hizli acmak icin okutun.",
                        styles["small"],
                    ),
                ]],
                colWidths=[
                    20 * mm if toner_friendly else 26 * mm,
                    doc.width - (20 * mm if toner_friendly else 26 * mm),
                ],
                style=TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOX", (0, 0), (-1, -1), 0.4, colors.black if toner_friendly else colors.HexColor("#d5dfe7")),
                    ("PADDING", (0, 0), (-1, -1), 2 if toner_friendly else 4),
                ]),
            ),
            Spacer(1, section_gap),
        ]
        if ctx["fault"] != "-":
            story.extend([Paragraph("BILDIRILEN ARIZA", styles["section"]), Paragraph(self._safe_html(ctx["fault"]), styles["body"]), Spacer(1, small_gap)])
        if ctx["notes"] != "-":
            story.extend([Paragraph("YAPILAN ISLEMLER / TEKNISYEN NOTU", styles["section"]), Paragraph(self._safe_html(ctx["notes"]), styles["body"]), Spacer(1, small_gap)])
        story.extend([
            Paragraph("PARCA VE ISCLIK DETAYI", styles["section"]),
            self._build_service_parts_table(ctx, styles, doc.width, toner_friendly=toner_friendly),
            Spacer(1, small_gap),
            Table([["", Paragraph("GENEL TOPLAM", styles["section"]), Paragraph(f"{ctx['total']:,.2f} TL", styles["right"])]], colWidths=[doc.width * 0.55, doc.width * 0.23, doc.width * 0.22], style=TableStyle([
                ("BOX", (1, 0), (-1, 0), 0.5, colors.black if toner_friendly else colors.HexColor("#78a995")),
                ("PADDING", (0, 0), (-1, -1), 3 if toner_friendly else 6),
            ] + ([] if toner_friendly else [
                ("BACKGROUND", (1, 0), (-1, 0), colors.HexColor("#e3f2ec")),
            ]))),
        ])
        terms = self.db.get_setting("service_terms", "Cihaz tesliminden itibaren servis garantisi uygulanir.")
        if not compact:
            story.extend([
                Spacer(1, 3 * mm if toner_friendly else 7 * mm),
                Paragraph("SERVIS SARTLARI", styles["section"]),
                Paragraph(self._safe_html(terms), styles["small"]),
                Spacer(1, 6 * mm if toner_friendly else 12 * mm),
                Table([[Paragraph("TESLIM EDEN IMZASI", styles["section"]), Paragraph("SERVIS YETKILISI", styles["section"])]], colWidths=[doc.width * 0.5, doc.width * 0.5]),
            ])
        if toner_friendly:
            doc.build([KeepInFrame(doc.width, doc.height, story, mode="shrink")])
        else:
            doc.build(story)
        self._finish_service_output(filename)
        return True, filename

    def create_device_label(self, device_data, width_mm=None, height_mm=None):
        try:
            normal_font, bold_font = self._register_fonts()
            ctx = self._service_print_context(device_data, [], 0)
            width = float(
                width_mm
                or self.db.get_setting("print_label_a_width_mm", "100")
                or 100
            ) * mm
            height = float(
                height_mm
                or self.db.get_setting("print_label_a_height_mm", "28")
                or 28
            ) * mm
            filename = os.path.join(self._get_save_path(), f"Label_{self._safe_filename(ctx['tracking'])}.pdf")
            pdf = canvas.Canvas(filename, pagesize=(width, height))
            cells = [
                ("MUSTERI", ctx["customer"]),
                ("MARKA / MODEL", f"{ctx['brand']} {ctx['model']}".strip()),
                ("TAKIP NO", ctx["tracking"]),
                ("TARIH", datetime.now().strftime("%d.%m.%Y")),
            ]
            cell_width = width / 2
            cell_height = height / 2
            for index, (title, value) in enumerate(cells):
                column = index % 2
                row = 1 - (index // 2)
                x = column * cell_width
                y = row * cell_height
                pdf.rect(x + 0.8 * mm, y + 0.8 * mm, cell_width - 1.6 * mm, cell_height - 1.6 * mm)
                pdf.setFillColor(colors.black)
                pdf.rect(x + 1.3 * mm, y + cell_height - 5.5 * mm, cell_width - 2.6 * mm, 4 * mm, fill=1)
                pdf.setFillColor(colors.white)
                pdf.setFont(bold_font, 6)
                pdf.drawString(x + 2 * mm, y + cell_height - 4.4 * mm, title)
                pdf.setFillColor(colors.black)
                pdf.setFont(normal_font, 7)
                pdf.drawString(x + 2 * mm, y + 3 * mm, self._service_text(value)[:36])
            pdf.showPage()
            pdf.save()
            self._finish_service_output(filename)
            return True, filename
        except Exception as exc:
            logger.error("Label error: %s", exc)
            return False, str(exc)

    def create_device_label_b(self, device_data, width_mm=None, height_mm=None):
        try:
            normal_font, bold_font = self._register_fonts()
            ctx = self._service_print_context(device_data, [], 0)
            company = self._service_company_context()
            customer = self._service_customer_context(device_data)
            width = float(
                width_mm
                or self.db.get_setting("print_label_width_mm", "70")
                or 70
            ) * mm
            height = float(
                height_mm
                or self.db.get_setting("print_label_height_mm", "45")
                or 45
            ) * mm
            filename = os.path.join(self._get_save_path(), f"Label_B_{self._safe_filename(ctx['tracking'])}.pdf")
            pdf = canvas.Canvas(filename, pagesize=(width, height))
            logo_path = company["logo"]
            if logo_path and os.path.exists(logo_path):
                try:
                    pdf.drawImage(ImageReader(logo_path), 3 * mm, height - 15 * mm, 38 * mm, 11 * mm, preserveAspectRatio=True, anchor="w", mask="auto")
                except Exception as exc:
                    logger.warning("Label logo could not be drawn: %s", exc)
            else:
                pdf.setFont(bold_font, 12)
                pdf.drawString(3 * mm, height - 10 * mm, company["name"][:28])
            qr = self._service_qr_drawing(ctx["tracking"], size=16 * mm)
            renderPDF.draw(qr, pdf, width - 19 * mm, height - 19 * mm)
            lines = [
                company["phone"] or company["gsm"],
                datetime.now().strftime("%d.%m.%Y %H:%M"),
                customer["name"] or ctx["customer"],
                customer["phone"],
                f"{ctx['brand']} {ctx['model']}".strip(),
                ctx["fault"],
            ]
            pdf.setFont(bold_font, 6.8)
            y = height - 20 * mm
            for line in lines:
                if line:
                    pdf.drawString(3 * mm, y, self._service_text(line)[:42])
                    y -= 4.2 * mm
            pdf.showPage()
            pdf.save()
            self._finish_service_output(filename)
            return True, filename
        except Exception as exc:
            logger.error("Label B error: %s", exc)
            return False, str(exc)

    def create_zpl_label(self, device_data):
        try:
            ctx = self._service_print_context(device_data, [], 0)
            company = self._service_text(self.db.get_setting("company_name", "AYEC Pro"), "AYEC Pro")
            date_text = datetime.now().strftime("%Y-%m-%d")
            zpl = f"^XA\n^PW400\n^LL240\n^FO10,10^A0N,20,20^FD{company[:24]}^FS\n^FO10,38^A0N,25,25^FD{ctx['brand']} {ctx['model']}^FS\n^FO10,68^A0N,20,20^FD{ctx['customer'][:24]}^FS\n^FO20,95^BCN,50,Y,N,N\n^FD{ctx['tracking']}^FS\n^FO10,180^A0N,18,18^FD{date_text}^FS\n^XZ"
            filename = os.path.join(self._get_save_path(), f"Label_{self._safe_filename(ctx['tracking'])}.zpl")
            with open(filename, "w", encoding="utf-8") as handle:
                handle.write(zpl)
            return True, filename
        except Exception as exc:
            logger.error("ZPL error: %s", exc)
            return False, str(exc)

    def _receipt_styles(self, normal_font, bold_font):
        return {
            "title": ParagraphStyle("ReceiptTitle", fontName=bold_font, fontSize=10, leading=12, alignment=1),
            "body": ParagraphStyle("ReceiptBody", fontName=normal_font, fontSize=7, leading=9),
            "bold": ParagraphStyle("ReceiptBold", fontName=bold_font, fontSize=7, leading=9),
            "section": ParagraphStyle("ReceiptSection", fontName=bold_font, fontSize=7.5, leading=9, textColor=colors.white),
            "right": ParagraphStyle("ReceiptRight", fontName=normal_font, fontSize=7, leading=9, alignment=2),
        }

    def _receipt_section(self, title, width, styles):
        return Table(
            [[Paragraph(title, styles["section"])]],
            colWidths=[width],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.black),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]),
        )

    def _receipt_rows(self, rows, width, styles):
        data = []
        for label, value in rows:
            data.append([
                Paragraph(self._safe_html(label), styles["bold"]),
                Paragraph(self._safe_html(self._service_text(value)), styles["right"]),
            ])
        return Table(
            data,
            colWidths=[width * 0.38, width * 0.62],
            style=TableStyle([
                ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
                ("LINEBELOW", (0, 0), (-1, -2), 0.25, colors.black),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]),
        )

    def create_detailed_service_receipt(self, device_data, used_parts, labor_cost):
        try:
            normal_font, bold_font = self._register_fonts()
            styles = self._receipt_styles(normal_font, bold_font)
            ctx = self._service_print_context(device_data, used_parts, labor_cost)
            company = self._service_company_context()
            customer = self._service_customer_context(device_data)
            width, height = 80 * mm, 210 * mm
            content_width = width - 6 * mm
            filename = os.path.join(self._get_save_path(), f"Detayli_Fis_{self._safe_filename(ctx['tracking'])}.pdf")
            doc = SimpleDocTemplate(filename, pagesize=(width, height), rightMargin=3 * mm, leftMargin=3 * mm, topMargin=3 * mm, bottomMargin=3 * mm)
            logo = self._service_logo_flowable(48 * mm, 18 * mm)
            header = logo or Paragraph(self._safe_html(company["name"]), styles["title"])
            contact_parts = [company["website"], company["phone"] or company["gsm"]]
            story = [
                header,
                Paragraph(self._safe_html(" - ".join(part for part in contact_parts if part)), styles["title"]),
                Spacer(1, 2 * mm),
                Paragraph(datetime.now().strftime("%d.%m.%Y %H:%M"), styles["right"]),
                Spacer(1, 1 * mm),
                self._receipt_section("MUSTERI BILGILERI", content_width, styles),
                self._receipt_rows([
                    ("MUSTERI:", customer["name"] or ctx["customer"]),
                    ("TELEFON:", customer["phone"]),
                    ("TELEFON 2:", customer["phone2"]),
                    ("ADRES:", customer["address"]),
                ], content_width, styles),
                Spacer(1, 2 * mm),
                self._receipt_section("URUN BILGILERI", content_width, styles),
                self._receipt_rows([
                    ("FIS NO:", ctx["tracking"]),
                    ("TARIH:", datetime.now().strftime("%d.%m.%Y")),
                    ("MARKA/MODEL:", f"{ctx['brand']} {ctx['model']}".strip()),
                    ("SERI NO:", ctx["serial"]),
                ], content_width, styles),
                Spacer(1, 2 * mm),
                self._receipt_section("BILDIRILEN ARIZA", content_width, styles),
                Table([[Paragraph(self._safe_html(ctx["fault"]), styles["body"])]], colWidths=[content_width], style=TableStyle([("BOX", (0, 0), (-1, -1), 0.5, colors.black), ("PADDING", (0, 0), (-1, -1), 6)])),
                Spacer(1, 2 * mm),
                self._receipt_section("PERSONEL BILGILERI", content_width, styles),
                self._receipt_rows([
                    ("KAYIT ACAN:", self._service_value(device_data, "created_by") or "-"),
                    ("TAMIR EDEN:", self._service_value(device_data, "assigned_person") or "-"),
                    ("TESLIM EDEN:", self._service_value(device_data, "delivered_by") or "-"),
                ], content_width, styles),
                Spacer(1, 3 * mm),
                Table([[self._service_qr_drawing(ctx["tracking"], 22 * mm)]], colWidths=[content_width], style=TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")])),
            ]
            doc.build(story)
            self._finish_service_output(filename)
            return True, filename
        except Exception as exc:
            logger.error("Detailed receipt error: %s", exc)
            return False, str(exc)

    def create_service_receipt(self, device_data, used_parts, labor_cost):
        try:
            return self._create_service_pdf(device_data, used_parts, labor_cost, A4, "Servis_Fisi")
        except Exception as exc:
            logger.error("Service receipt error: %s", exc)
            return False, str(exc)

    def create_short_service_receipt(self, device_data, used_parts, labor_cost):
        try:
            normal_font, bold_font = self._register_fonts()
            styles = self._receipt_styles(normal_font, bold_font)
            ctx = self._service_print_context(device_data, used_parts, labor_cost)
            customer = self._service_customer_context(device_data)
            width, height = 80 * mm, 125 * mm
            content_width = width - 4 * mm
            filename = os.path.join(self._get_save_path(), f"Kisa_Fis_{self._safe_filename(ctx['tracking'])}.pdf")
            doc = SimpleDocTemplate(filename, pagesize=(width, height), rightMargin=2 * mm, leftMargin=2 * mm, topMargin=2 * mm, bottomMargin=2 * mm)
            story = [
                Paragraph("TEKNIK SERVIS BILGI FISI", styles["title"]),
                Paragraph(datetime.now().strftime("%d.%m.%Y %H:%M"), styles["right"]),
                self._receipt_section("MUSTERI BILGILERI", content_width, styles),
                self._receipt_rows([
                    ("MUSTERI:", customer["name"] or ctx["customer"]),
                    ("TELEFON:", customer["phone"]),
                ], content_width, styles),
                Spacer(1, 1.5 * mm),
                self._receipt_section("URUN BILGILERI", content_width, styles),
                self._receipt_rows([
                    ("MARKA/MODEL:", f"{ctx['brand']} {ctx['model']}".strip()),
                    ("SERI NO:", ctx["serial"]),
                    ("TAKIP NO:", ctx["tracking"]),
                ], content_width, styles),
                Spacer(1, 1.5 * mm),
                self._receipt_section("BILDIRILEN ARIZA", content_width, styles),
                Table([[Paragraph(self._safe_html(ctx["fault"]), styles["body"])]], colWidths=[content_width], style=TableStyle([("BOX", (0, 0), (-1, -1), 0.5, colors.black), ("PADDING", (0, 0), (-1, -1), 5)])),
            ]
            doc.build(story)
            self._finish_service_output(filename)
            return True, filename
        except Exception as exc:
            logger.error("Short receipt error: %s", exc)
            return False, str(exc)

    def create_cargo_receipt(self, device_data, used_parts, labor_cost):
        try:
            normal_font, bold_font = self._register_fonts()
            styles = self._receipt_styles(normal_font, bold_font)
            ctx = self._service_print_context(device_data, [], 0)
            company = self._service_company_context()
            customer = self._service_customer_context(device_data)
            width, height = 105 * mm, 150 * mm
            content_width = width - 6 * mm
            filename = os.path.join(self._get_save_path(), f"Kargo_Fisi_{self._safe_filename(ctx['tracking'])}.pdf")
            doc = SimpleDocTemplate(filename, pagesize=(width, height), rightMargin=3 * mm, leftMargin=3 * mm, topMargin=3 * mm, bottomMargin=3 * mm)
            story = [
                Paragraph("KARGO BILGILERI", styles["title"]),
                Paragraph(datetime.now().strftime("%d.%m.%Y %H:%M"), styles["right"]),
                Spacer(1, 2 * mm),
                self._receipt_section("GONDEREN BILGILERI", content_width, styles),
                self._receipt_rows([
                    ("FIRMA:", company["name"]),
                    ("KARGO:", company["cargo"]),
                    ("ANLASMA:", company["cargo_no"]),
                    ("ADRES:", company["address"]),
                    ("TELEFON:", company["phone"] or company["gsm"]),
                ], content_width, styles),
                Spacer(1, 4 * mm),
                self._receipt_section("ALICI BILGILERI", content_width, styles),
                self._receipt_rows([
                    ("AD SOYAD:", customer["name"] or ctx["customer"]),
                    ("FIRMA:", customer["company"]),
                    ("TELEFON:", customer["phone"]),
                    ("TELEFON 2:", customer["phone2"]),
                    ("CIHAZ:", f"{ctx['brand']} {ctx['model']}".strip()),
                    ("SERI NO:", ctx["serial"]),
                    ("ADRES:", customer["address"]),
                ], content_width, styles),
            ]
            doc.build(story)
            self._finish_service_output(filename)
            return True, filename
        except Exception as exc:
            logger.error("Cargo receipt error: %s", exc)
            return False, str(exc)

    def create_detailed_service_receipt(
        self,
        device_data,
        used_parts,
        labor_cost,
        page_size=None,
        orientation=None,
    ):
        try:
            return self._create_service_pdf(
                device_data,
                used_parts,
                labor_cost,
                pagesize=page_size,
                prefix="Detayli_Servis_Fisi",
                orientation=orientation,
                toner_friendly=True,
            )
        except Exception as exc:
            logger.error("Detailed receipt error: %s", exc)
            return False, str(exc)

    def create_service_receipt(
        self,
        device_data,
        used_parts,
        labor_cost,
        page_size=None,
        orientation=None,
    ):
        try:
            return self._create_service_pdf(
                device_data,
                used_parts,
                labor_cost,
                pagesize=page_size,
                prefix="Servis_Fisi",
                orientation=orientation,
            )
        except Exception as exc:
            logger.error("Service receipt error: %s", exc)
            return False, str(exc)
