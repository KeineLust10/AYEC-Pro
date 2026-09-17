# -*- coding: utf-8 -*-
import os
import sys
import tempfile
import webbrowser
import subprocess
from datetime import datetime
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import Frame
from src.utils.logger import logger

class PDFBaseMixin:
    def _register_fonts(self):
        try:
            if sys.platform == "win32":
                font_dir = os.environ.get('WINDIR', 'C:\\Windows') + "\\Fonts"
                arial_files = ["arial.ttf", "Arial.ttf"]
                arial_bold_files = ["arialbd.ttf", "Arial_Bold.ttf"]
                found_arial = found_bold = None
                for f in arial_files:
                    path = os.path.join(font_dir, f)
                    if os.path.exists(path): found_arial = path; break
                for f in arial_bold_files:
                    path = os.path.join(font_dir, f)
                    if os.path.exists(path): found_bold = path; break
                if found_arial and found_bold:
                    pdfmetrics.registerFont(TTFont('Arial', found_arial))
                    pdfmetrics.registerFont(TTFont('Arial-Bold', found_bold))
                    return 'Arial', 'Arial-Bold'
            try:
                pdfmetrics.registerFont(TTFont('Arial', 'Arial.ttf'))
                pdfmetrics.registerFont(TTFont('Arial-Bold', 'arialbd.ttf'))
                return 'Arial', 'Arial-Bold'
            except Exception: pass
            return 'Helvetica', 'Helvetica-Bold'
        except Exception as e:
            logger.error("Font Reg Error: %s", e); return 'Helvetica', 'Helvetica-Bold'

    def _open_file(self, filename):
        try:
            if sys.platform == "win32":
                try: os.startfile(filename)
                except Exception: webbrowser.open(filename)
            elif sys.platform == "darwin": subprocess.call(["open", filename])
            else: subprocess.call(["xdg-open", filename])
        except Exception as e:
            logger.error("Error opening file: %s", e)
            try: webbrowser.open(filename)
            except Exception: pass

    def _get_save_path(self):
        paths = [os.path.join(os.path.expanduser("~"), "Documents"), os.path.join(os.path.expanduser("~"), "Desktop"), os.getcwd()]
        for p in paths:
            try:
                if not os.path.exists(p): os.makedirs(p, exist_ok=True)
                if os.path.exists(p) and os.access(p, os.W_OK): return p
            except Exception: continue
        return "."

    def _safe_filename(self, text):
        return "".join(ch for ch in str(text or "") if ch.isalnum() or ch in (" ", "_", "-")).strip() or "Genel_Evrak"

    def _currency_symbol(self, currency_code):
        m = {"TRY": "TL", "TL": "TL", "USD": "$", "EUR": "€", "GBP": "£", "AED": "AED", "SAR": "SAR", "CHF": "CHF"}
        return m.get(str(currency_code or "USD").upper(), str(currency_code).upper())

    def _format_money(self, amount, currency_code):
        return f"{float(amount or 0):,.2f} {self._currency_symbol(currency_code)}"

    def _get_styles(self):
        return getSampleStyleSheet()

    def _group_currency_totals(self, items):
        totals = {}
        for item in items or []:
            code = str(item.get("currency") or "USD").upper()
            totals[code] = totals.get(code, 0.0) + (float(item.get("unit_price") or 0) * int(item.get("qty") or 0))
        return totals

    def _is_placeholder_customer(self, text):
        normalized = str(text or "").strip().lower()
        return normalized in {"", "müşteri seçin...", "musteri secin...", "peşin / genel müşteri", "pesin / genel musteri", "genel müşteri", "genel musteri"}

    def _fresh_template_page(self, template_pdf, page_index):
        reader = PdfReader(template_pdf)
        if not reader.pages: raise ValueError("Template PDF is empty")
        safe_index = max(0, min(int(page_index or 0), len(reader.pages) - 1))
        return reader.pages[safe_index]

    def _merge_overlay_on_template_page(self, writer, template_pdf, page_index, draw_callback):
        page = self._fresh_template_page(template_pdf, page_index)
        pw, ph = float(page.mediabox.width), float(page.mediabox.height)
        fd, op = tempfile.mkstemp(suffix=".pdf"); os.close(fd)
        try:
            cv = rl_canvas.Canvas(op, pagesize=(pw, ph)); draw_callback(cv, pw, ph); cv.save()
            or_ = PdfReader(op)
            if or_.pages: page.merge_page(or_.pages[0])
            writer.add_page(page)
        finally:
            try: os.remove(op)
            except Exception: pass
