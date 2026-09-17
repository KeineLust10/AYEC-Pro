"""
Turkish PDF Helper
Provides utilities for generating PDFs with full Turkish character support.
Uses DejaVu Sans TrueType fonts for proper rendering of Turkish characters.
"""

import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from src.utils.currency_helper import CurrencyHelper
from src.utils.logger import logger


class TurkishPDFHelper:
    """Helper class for generating PDFs with Turkish character support."""

    _fonts_registered = False

    @staticmethod
    def register_fonts():
        """
        Register TrueType fonts for Turkish characters.
        Call this once before generating any PDFs.
        """
        if TurkishPDFHelper._fonts_registered:
            return

        font_dir = os.path.join(os.path.dirname(__file__), "..", "..", "fonts")

        try:
            # 1. Try bundled DejaVu fonts.
            if os.path.exists(os.path.join(font_dir, "DejaVuSans.ttf")):
                pdfmetrics.registerFont(TTFont("DejaVu", os.path.join(font_dir, "DejaVuSans.ttf")))
                pdfmetrics.registerFont(TTFont("DejaVu-Bold", os.path.join(font_dir, "DejaVuSans-Bold.ttf")))
                pdfmetrics.registerFont(TTFont("DejaVu-Italic", os.path.join(font_dir, "DejaVuSans-Oblique.ttf")))
                pdfmetrics.registerFont(TTFont("DejaVu-BoldItalic", os.path.join(font_dir, "DejaVuSans-BoldOblique.ttf")))
                logger.info("Bundled DejaVu fonts registered")
            # 2. Fallback to Windows system fonts.
            elif os.name == "nt" and os.path.exists("C:\\Windows\\Fonts\\arial.ttf"):
                pdfmetrics.registerFont(TTFont("DejaVu", "C:\\Windows\\Fonts\\arial.ttf"))
                pdfmetrics.registerFont(TTFont("DejaVu-Bold", "C:\\Windows\\Fonts\\arialbd.ttf"))
                pdfmetrics.registerFont(TTFont("DejaVu-Italic", "C:\\Windows\\Fonts\\ariali.ttf"))
                pdfmetrics.registerFont(TTFont("DejaVu-BoldItalic", "C:\\Windows\\Fonts\\arialbi.ttf"))
                logger.info("System Arial fonts registered as fallback")
            else:
                logger.warning(
                    "No compatible PDF font found. Falling back to standard fonts; Turkish characters may render poorly."
                )

            TurkishPDFHelper._fonts_registered = True
        except Exception as e:
            logger.warning("Font registration warning: %s", e)
            # Let ReportLab continue with default fonts as a last resort.

    @staticmethod
    def get_style(name="Normal", font_size=10, bold=False, italic=False, alignment=TA_LEFT, text_color=colors.black):
        """Get paragraph style with Turkish font support."""
        if bold and italic:
            font_name = "DejaVu-BoldItalic"
        elif bold:
            font_name = "DejaVu-Bold"
        elif italic:
            font_name = "DejaVu-Italic"
        else:
            font_name = "DejaVu"

        return ParagraphStyle(
            name=name,
            fontName=font_name,
            fontSize=font_size,
            leading=font_size * 1.2,
            alignment=alignment,
            textColor=text_color,
            spaceAfter=6,
        )

    @staticmethod
    def get_header_style():
        return TurkishPDFHelper.get_style(
            name="Header",
            font_size=18,
            bold=True,
            alignment=TA_CENTER,
            text_color=colors.black,
        )

    @staticmethod
    def get_subheader_style():
        return TurkishPDFHelper.get_style(
            name="SubHeader",
            font_size=14,
            bold=True,
            text_color=colors.darkgrey,
        )

    @staticmethod
    def get_body_style():
        return TurkishPDFHelper.get_style(name="Body", font_size=10, alignment=TA_JUSTIFY)

    @staticmethod
    def get_table_header_style():
        return TurkishPDFHelper.get_style(
            name="TableHeader",
            font_size=9,
            bold=True,
            alignment=TA_CENTER,
            text_color=colors.white,
        )

    @staticmethod
    def get_table_cell_style():
        return TurkishPDFHelper.get_style(name="TableCell", font_size=9, alignment=TA_LEFT)

    @staticmethod
    def create_table_style(header_bg="dodgerblue", alternate_rows=True):
        """Create a standard table style with Turkish font support."""
        from reportlab.platypus import TableStyle

        style = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_bg)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "DejaVu-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
            ("FONTNAME", (0, 1), (-1, -1), "DejaVu"),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("ALIGN", (0, 1), (-1, -1), "LEFT"),
            ("VALIGN", (0, 1), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 1), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
            ("LEFTPADDING", (0, 1), (-1, -1), 8),
            ("RIGHTPADDING", (0, 1), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("BOX", (0, 0), (-1, -1), 1, colors.lightgrey),
        ]

        if alternate_rows:
            style.append(("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.whitesmoke]))

        return TableStyle(style)

    @staticmethod
    def format_currency(amount):
        return CurrencyHelper.format_try_for_display(
            amount,
            include_try_reference=False,
        )

    @staticmethod
    def format_date(date_str):
        from src.utils.date_utils import format_datetime_turkish

        return format_datetime_turkish(date_str)

    @staticmethod
    def add_page_number(canvas, doc):
        """
        Add page number footer to PDF.
        Use as callback: doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
        """
        canvas.saveState()
        canvas.setFont("DejaVu", 8)
        canvas.setFillColor(colors.darkgrey)
        page_num = f"Sayfa {canvas.getPageNumber()}"
        canvas.drawRightString(A4[0] - 2 * cm, 1.5 * cm, page_num)
        canvas.restoreState()
