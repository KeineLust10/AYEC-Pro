# -*- coding: utf-8 -*-
"""Custom editor based proforma PDF renderer.

Settings contract (single source of truth):
- ``proforma_editor_html``       : rich-text template body saved from the editor (HTML)
- ``proforma_use_custom_editor`` : "1" when the custom editor template is the
                                   active proforma template, otherwise the
                                   embedded professional builder is used.

Placeholders supported inside the template (Word-like field codes):
- {{firma_adi}}, {{musteri_adi}}, {{yetkili}}, {{proje}}, {{teklif_no}},
  {{tarih}}, {{gecerlilik}}, {{para_birimi}}
- {{logo}}           : company logo image (from ``logo_path`` setting)
- {{urun_tablosu}}   : dynamic items table (flows across pages)
- {{toplamlar}}      : totals block (subtotal / discount / VAT / grand total)
- {{ticari_kosullar}}: terms text from settings
- {{imza_alani}}     : signature block

Text placeholders may appear inline in any paragraph. Block placeholders
({{logo}}, {{urun_tablosu}}, {{toplamlar}}, {{ticari_kosullar}},
{{imza_alani}}) are rendered as dedicated flowables at the paragraph position
where they occur. Missing block placeholders fall back to a sane default
order appended after the template body so the produced document always
contains the commercial data.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timedelta
from html.parser import HTMLParser
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.utils.logger import logger
from src.utils.professional_proforma import (
    _PDF_METADATA_TITLE,
    _company_lines,
    _currency_code,
    _currency_label,
    _date_text,
    _financial_summary_rows,
    _item_content,
    _money,
    _parse_date,
    _prepare_logo_source,
    _quantity,
    _safe,
    _setting,
    _terms,
)

# Settings keys (keep reader and writer on the same keys - hygiene rule)
SETTING_TEMPLATE_HTML = "proforma_editor_html"
SETTING_USE_CUSTOM = "proforma_use_custom_editor"

BLOCK_PLACEHOLDERS = (
    "logo",
    "urun_tablosu",
    "toplamlar",
    "ticari_kosullar",
    "imza_alani",
)

_PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-z_]+)\s*\}\}")

_PRIMARY = colors.HexColor("#145A86")
_PALE = colors.HexColor("#EAF3F9")
_ACCENT = colors.HexColor("#0F766E")
_GRID = colors.HexColor("#CBD3DD")


def is_custom_editor_active(db) -> bool:
    """Return True when the custom editor template should drive PDF output."""
    try:
        flag = str(db.get_setting(SETTING_USE_CUSTOM, "0") or "0").strip()
        html = str(db.get_setting(SETTING_TEMPLATE_HTML, "") or "").strip()
        return flag in {"1", "true", "True"} and bool(html)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Minimal QTextDocument-HTML -> ReportLab converter
# ---------------------------------------------------------------------------

_ALLOWED_INLINE = {"b", "strong", "i", "em", "u", "br", "font", "span", "a", "s"}
_HEADING_SIZES = {"h1": 16, "h2": 14, "h3": 12, "h4": 11}


def _css_color(style: str):
    m = re.search(r"color\s*:\s*(#[0-9a-fA-F]{6}|rgb\([^)]*\))", style or "")
    if not m:
        return None
    value = m.group(1)
    if value.startswith("rgb"):
        nums = re.findall(r"\d+", value)
        if len(nums) >= 3:
            return "#%02x%02x%02x" % (int(nums[0]), int(nums[1]), int(nums[2]))
        return None
    return value


def _css_size(style: str):
    m = re.search(r"font-size\s*:\s*(\d+(?:\.\d+)?)(pt|px)", style or "")
    if not m:
        return None
    size = float(m.group(1))
    if m.group(2) == "px":
        size *= 0.75
    return max(6.0, min(28.0, size))


def _css_align(style: str):
    m = re.search(r"text-align\s*:\s*(left|right|center|justify)", style or "")
    if not m:
        return None
    return {"left": 0, "center": 1, "right": 2, "justify": 4}[m.group(1)]


class _HtmlToBlocks(HTMLParser):
    """Parse QTextDocument HTML into a list of logical blocks.

    Produces items of shape:
      ("para", inline_markup, {align, size, color, bold})
      ("list_item", inline_markup, {...})
      ("image", src, {})
      ("hr", "", {})
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks = []
        self._buf = []
        self._meta = {}
        self._inline_stack = []
        self._in_body_block = False
        self._list_depth = 0
        self._skip_depth = 0

    # -- helpers ---------------------------------------------------------
    def _flush(self, kind="para"):
        text = "".join(self._buf).strip()
        # Close any dangling inline tags defensively
        if text:
            self.blocks.append((kind, text, dict(self._meta)))
        self._buf = []

    # -- parser events ---------------------------------------------------
    def handle_starttag(self, tag, attrs):
        if self._skip_depth:
            self._skip_depth += 1
            return
        attrs = dict(attrs)
        style = attrs.get("style", "")
        if tag in ("script", "style", "head", "title", "meta"):
            self._skip_depth = 1
            return
        if tag in ("p", "div", "li") or tag in _HEADING_SIZES:
            if self._in_body_block:
                self._flush("list_item" if self._list_depth else "para")
            self._in_body_block = True
            self._meta = {}
            align = _css_align(style)
            if align is not None:
                self._meta["align"] = align
            size = _css_size(style)
            if size:
                self._meta["size"] = size
            color = _css_color(style)
            if color:
                self._meta["color"] = color
            if tag in _HEADING_SIZES:
                self._meta["size"] = _HEADING_SIZES[tag]
                self._meta["bold"] = True
            if tag == "li":
                self._meta["list"] = True
            return
        if tag in ("ul", "ol"):
            self._list_depth += 1
            return
        if tag == "img":
            self._flush("list_item" if self._list_depth else "para")
            src = attrs.get("src", "")
            if src:
                self.blocks.append(("image", src, {}))
            return
        if tag == "hr":
            self._flush("list_item" if self._list_depth else "para")
            self.blocks.append(("hr", "", {}))
            return
        if tag == "br":
            self._buf.append("<br/>")
            return
        if tag in _ALLOWED_INLINE:
            markup = None
            if tag in ("b", "strong"):
                markup = "b"
            elif tag in ("i", "em"):
                markup = "i"
            elif tag == "u":
                markup = "u"
            elif tag == "s":
                markup = "strike"
            elif tag in ("font", "span", "a"):
                color = attrs.get("color") or _css_color(style)
                size = _css_size(style)
                parts = []
                if color:
                    parts.append(f'color="{color}"')
                if size:
                    parts.append(f'size="{size:g}"')
                # span may also carry bold/italic via css
                extra = []
                if "font-weight" in style and re.search(r"font-weight\s*:\s*(bold|[6-9]00)", style):
                    extra.append("b")
                if re.search(r"font-style\s*:\s*italic", style):
                    extra.append("i")
                if re.search(r"text-decoration\s*:\s*underline", style):
                    extra.append("u")
                if parts:
                    markup = ("font", " ".join(parts), extra)
                elif extra:
                    markup = ("plain", "", extra)
                else:
                    markup = ("plain", "", [])
            if isinstance(markup, str):
                self._buf.append(f"<{markup}>")
                self._inline_stack.append(markup)
            else:
                kind, attr_text, extra = markup
                opened = []
                if kind == "font":
                    self._buf.append(f"<font {attr_text}>")
                    opened.append("font")
                for tag_name in extra:
                    self._buf.append(f"<{tag_name}>")
                    opened.append(tag_name)
                self._inline_stack.append(tuple(opened))
            return
        # Unknown tags are ignored (content kept)

    def handle_endtag(self, tag):
        if self._skip_depth:
            self._skip_depth -= 1
            return
        if tag in ("p", "div", "li") or tag in _HEADING_SIZES:
            self._flush("list_item" if (self._list_depth and self._meta.get("list")) else "para")
            self._in_body_block = False
            return
        if tag in ("ul", "ol"):
            self._list_depth = max(0, self._list_depth - 1)
            return
        if tag in _ALLOWED_INLINE and tag != "br" and self._inline_stack:
            top = self._inline_stack.pop()
            if isinstance(top, str):
                self._buf.append(f"</{top}>")
            else:
                for tag_name in reversed(top):
                    self._buf.append(f"</{tag_name}>")

    def handle_data(self, data):
        if self._skip_depth:
            return
        if data:
            self._buf.append(escape(data))

    def close(self):
        super().close()
        self._flush("para")


def _split_placeholder_blocks(blocks):
    """Split parsed blocks so block-level placeholders become own entries."""
    result = []
    for kind, text, meta in blocks:
        if kind != "para" and kind != "list_item":
            result.append((kind, text, meta))
            continue
        plain = re.sub(r"<[^>]+>", "", text)
        stripped = plain.strip()
        m = _PLACEHOLDER_RE.fullmatch(stripped)
        if m and m.group(1) in BLOCK_PLACEHOLDERS:
            result.append(("block_field", m.group(1), meta))
            continue
        # Paragraph that contains a block placeholder among other text:
        # extract each block placeholder into its own entry, keep the rest.
        segments = _PLACEHOLDER_RE.split(text)
        if len(segments) > 1 and any(seg in BLOCK_PLACEHOLDERS for seg in segments[1::2]):
            buf = ""
            for idx, seg in enumerate(segments):
                if idx % 2 == 1 and seg in BLOCK_PLACEHOLDERS:
                    if buf.strip():
                        result.append((kind, buf, meta))
                    buf = ""
                    result.append(("block_field", seg, meta))
                elif idx % 2 == 1:
                    buf += "{{" + seg + "}}"
                else:
                    buf += seg
            if buf.strip():
                result.append((kind, buf, meta))
            continue
        result.append((kind, text, meta))
    return result


# ---------------------------------------------------------------------------
# Flowable builders shared with the professional layout
# ---------------------------------------------------------------------------

def _build_items_table(cart_items, currency, code, font, font_bold):
    head = ParagraphStyle("CeTblHead", fontName=font_bold, fontSize=7.5, leading=9, textColor=colors.white, alignment=1)
    head_left = ParagraphStyle("CeTblHeadL", parent=head, alignment=0)
    cell = ParagraphStyle("CeCell", fontName=font, fontSize=8, leading=10, textColor=colors.HexColor("#273444"))
    cell_center = ParagraphStyle("CeCellC", parent=cell, alignment=1)
    cell_right = ParagraphStyle("CeCellR", parent=cell, alignment=2)
    rows = [[
        Paragraph("#", head),
        Paragraph("H\u0130ZMET / \u00dcR\u00dcN", head_left),
        Paragraph("A\u00c7IKLAMA", head_left),
        Paragraph("ADET", head),
        Paragraph("B\u0130R\u0130M F\u0130YAT", head),
        Paragraph("TUTAR", head),
    ]]
    for index, item in enumerate(cart_items or [], 1):
        quantity = float(item.get("qty", item.get("count", 1)) or 0)
        price = float(item.get("price", item.get("unit_price", 0)) or 0)
        name, details = _item_content(item)
        rows.append([
            Paragraph(str(index), cell_center),
            Paragraph(name, cell),
            Paragraph(details, cell),
            Paragraph(_quantity(quantity), cell_center),
            Paragraph(_money(price, currency, code), cell_right),
            Paragraph(_money(quantity * price, currency, code), cell_right),
        ])
    table = Table(rows, colWidths=[9 * mm, 43 * mm, 60 * mm, 14 * mm, 30 * mm, 34 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _PRIMARY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _PALE]),
        ("GRID", (0, 0), (-1, -1), 0.45, _GRID),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("VALIGN", (2, 1), (2, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def _build_totals_table(
    totals,
    currency,
    code,
    font,
    font_bold,
    totals_try=None,
):
    normal = ParagraphStyle("CeTotN", fontName=font, fontSize=8.5, leading=11, textColor=colors.HexColor("#273444"), alignment=2)
    strong = ParagraphStyle("CeTotB", fontName=font_bold, fontSize=10, leading=12, alignment=2, textColor=_ACCENT)
    right = ParagraphStyle("CeTotR", parent=normal)
    rows = []
    for label, value, emphasized in _financial_summary_rows(
        totals,
        code,
        totals_try=totals_try,
    ):
        style = strong if emphasized else normal
        value_style = strong if emphasized else right
        rows.append(["", Paragraph(label, style), Paragraph(value, value_style)])
    table = Table(rows, colWidths=[105 * mm, 45 * mm, 40 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (1, 0), (-1, -2), _PALE),
        ("BACKGROUND", (1, -1), (-1, -1), colors.HexColor("#E7F4EF")),
        ("LINEABOVE", (1, -1), (-1, -1), 1, _ACCENT),
        ("BOX", (1, 0), (-1, -1), 0.5, _GRID),
        ("INNERGRID", (1, 0), (-1, -1), 0.35, colors.HexColor("#D8DEE7")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def _build_terms_table(manager, code, validity_days, font, font_bold):
    section = ParagraphStyle("CeSec", fontName=font_bold, fontSize=8, leading=10, textColor=_PRIMARY)
    small = ParagraphStyle("CeSmall", fontName=font, fontSize=7.5, leading=9.5, textColor=colors.HexColor("#667085"))
    rows = [[Paragraph("T\u0130CAR\u0130 KO\u015eULLAR", section)]]
    for line in _terms(manager, code, validity_days).splitlines():
        line = line.strip()
        if not line:
            continue
        if ":" in line:
            label, value = line.split(":", 1)
            line = f"<b>{_safe(label.strip())}:</b> {_safe(value.strip())}"
        else:
            line = _safe(line)
        rows.append([Paragraph(line, small)])
    table = Table(rows, colWidths=[190 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _PALE),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#CDD5DF")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def _build_signatures(issuer, font, font_bold):
    section = ParagraphStyle("CeSigSec", fontName=font_bold, fontSize=8, leading=10, textColor=_PRIMARY)
    small = ParagraphStyle("CeSigSmall", fontName=font, fontSize=7.5, leading=9.5, textColor=colors.HexColor("#667085"))
    table = Table([
        [Paragraph("Teklifi Haz\u0131rlayan", section), Paragraph("M\u00fc\u015fteri Onay\u0131 / Ka\u015fe - \u0130mza", section)],
        [
            Paragraph(f"{_safe(issuer)}<br/><br/><br/>\u0130mza: ____________________", small),
            Paragraph("Ad Soyad: ____________________<br/><br/>Tarih: ________________________<br/>\u0130mza: ____________________", small),
        ],
    ], colWidths=[95 * mm, 95 * mm], rowHeights=[8 * mm, 25 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _PALE),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#CDD5DF")),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D8DEE7")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return KeepTogether([table])


def _build_logo(manager):
    logo_path = _setting(manager, "logo_path")
    if logo_path and os.path.exists(logo_path):
        try:
            logo = Image(_prepare_logo_source(logo_path), mask="auto")
            logo._restrictSize(48 * mm, 17 * mm)
            logo.hAlign = "LEFT"
            return logo
        except Exception as exc:
            logger.warning("Custom proforma logo load failed: %s", exc)
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def default_template_html() -> str:
    """Starter template shown when the editor is opened for the first time."""
    return (
        "<p>{{logo}}</p>"
        "<h2 style=\"color:#145A86;\">F\u0130YAT TEKL\u0130F\u0130</h2>"
        "<p><b>Teklif No:</b> {{teklif_no}} &nbsp;&nbsp; <b>Tarih:</b> {{tarih}} "
        "&nbsp;&nbsp; <b>Ge\u00e7erlilik:</b> {{gecerlilik}}</p>"
        "<p><b>Firma:</b> {{firma_adi}}<br/><b>Say\u0131n:</b> {{musteri_adi}}"
        "<br/><b>Yetkili:</b> {{yetkili}}<br/><b>Proje:</b> {{proje}}</p>"
        "<p>{{urun_tablosu}}</p>"
        "<p>{{toplamlar}}</p>"
        "<p>{{ticari_kosullar}}</p>"
        "<p>{{imza_alani}}</p>"
    )


def build_custom_editor_proforma(
    manager,
    cart_items,
    totals,
    company_name=None,
    customer_name=None,
    save_path=None,
    currency="TL",
    project_name=None,
    contact_name=None,
    reference_no=None,
    offer_date=None,
    customer_company=None,
    currency_code=None,
    validity_days=15,
    template_html=None,
    is_invoice=False,
    totals_try=None,
    include_approval=True,
):
    """Render the saved rich-text template with live offer data into a PDF."""
    try:
        html = template_html
        if html is None:
            html = str(manager.db.get_setting(SETTING_TEMPLATE_HTML, "") or "")
        if not html.strip():
            html = default_template_html()

        issue_date = _parse_date(offer_date)
        validity_days = max(1, int(validity_days or 15))
        valid_until = issue_date + timedelta(days=validity_days)
        code = _currency_code(currency, currency_code)
        issuer = str(company_name or _setting(manager, "company_name", "AYEC Pro")).strip()
        recipient = str(customer_company or customer_name or "Say\u0131n \u0130lgili").strip()
        contact = str(contact_name or customer_name or "").strip()
        project = str(project_name or "").strip()
        reference = str(reference_no or f"PRF-{issue_date.strftime('%Y%m%d-%H%M')}").strip()

        if not save_path:
            directory = manager._get_save_path()
            safe_recipient = manager._safe_filename(recipient)
            save_path = os.path.join(directory, f"Teklif_{safe_recipient}_{issue_date.strftime('%Y%m%d')}.pdf")
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)

        font, font_bold = manager._register_fonts()

        text_values = {
            "firma_adi": _safe(issuer),
            "musteri_adi": _safe(recipient),
            "yetkili": _safe(contact or recipient),
            "proje": _safe(project or "Belirtilmedi"),
            "teklif_no": _safe(reference),
            "tarih": _date_text(issue_date),
            "gecerlilik": _date_text(valid_until),
            "para_birimi": _safe(_currency_label(code)),
        }

        def _sub_text(markup: str) -> str:
            def repl(match):
                key = match.group(1)
                if key in BLOCK_PLACEHOLDERS:
                    return match.group(0)
                return text_values.get(key, match.group(0))
            return _PLACEHOLDER_RE.sub(repl, markup)

        parser = _HtmlToBlocks()
        parser.feed(html)
        parser.close()
        blocks = _split_placeholder_blocks(parser.blocks)

        block_builders = {
            "logo": lambda: _build_logo(manager),
            "urun_tablosu": lambda: _build_items_table(cart_items, currency, code, font, font_bold),
            "toplamlar": lambda: _build_totals_table(
                totals,
                currency,
                code,
                font,
                font_bold,
                totals_try=totals_try,
            ),
            "ticari_kosullar": lambda: _build_terms_table(manager, code, validity_days, font, font_bold),
            "imza_alani": lambda: (
                _build_signatures(issuer, font, font_bold)
                if include_approval
                else None
            ),
        }
        used_blocks = set()

        story = []
        base = ParagraphStyle("CeBody", fontName=font, fontSize=9.5, leading=13, textColor=colors.HexColor("#273444"))
        for kind, text, meta in blocks:
            if kind == "block_field":
                builder = block_builders.get(text)
                if not builder:
                    continue
                flow = builder()
                used_blocks.add(text)
                if flow is not None:
                    story.extend([flow, Spacer(1, 3 * mm)])
                continue
            if kind == "image":
                src = text
                if src.startswith("file:///"):
                    src = src[8:]
                if os.path.exists(src):
                    try:
                        img = Image(src)
                        img._restrictSize(120 * mm, 60 * mm)
                        img.hAlign = "LEFT"
                        story.extend([img, Spacer(1, 2 * mm)])
                    except Exception as exc:
                        logger.warning("Custom proforma image skipped: %s", exc)
                continue
            if kind == "hr":
                line = Table([[""]], colWidths=[190 * mm], rowHeights=[1])
                line.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.7, _GRID)]))
                story.extend([Spacer(1, 1.5 * mm), line, Spacer(1, 1.5 * mm)])
                continue
            markup = _sub_text(text)
            if not re.sub(r"<[^>]+>", "", markup).strip():
                continue
            style = base
            overrides = {}
            if meta.get("align") is not None:
                overrides["alignment"] = meta["align"]
            if meta.get("size"):
                overrides["fontSize"] = meta["size"]
                overrides["leading"] = meta["size"] * 1.35
            if meta.get("color"):
                overrides["textColor"] = colors.HexColor(meta["color"])
            if meta.get("bold"):
                overrides["fontName"] = font_bold
            if overrides:
                style = ParagraphStyle(f"CeBlk{len(story)}", parent=base, **overrides)
            if kind == "list_item":
                markup = f"\u2022 {markup}"
                style = ParagraphStyle(f"CeLi{len(story)}", parent=style, leftIndent=6 * mm)
            story.extend([Paragraph(markup, style), Spacer(1, 1.5 * mm)])

        # Guarantee commercial data even if placeholders were deleted
        fallback_order = ("urun_tablosu", "toplamlar", "ticari_kosullar", "imza_alani")
        for key in fallback_order:
            if key not in used_blocks:
                flow = block_builders[key]()
                if flow is not None:
                    story.extend([Spacer(1, 3 * mm), flow])

        footer_contact = " | ".join(_company_lines(manager)[:2])
        doc_title = ("FATURA" if is_invoice else _PDF_METADATA_TITLE) + f" - {reference}"

        def draw_page(canvas_obj, document):
            canvas_obj.saveState()
            canvas_obj.setTitle(doc_title)
            canvas_obj.setAuthor(issuer)
            canvas_obj.setSubject(project or recipient)
            width, height = A4
            if document.page > 1:
                canvas_obj.setFont(font_bold, 8)
                canvas_obj.setFillColor(_PRIMARY)
                canvas_obj.drawString(10 * mm, height - 9 * mm, "F\u0130YAT TEKL\u0130F\u0130")
                canvas_obj.setFont(font, 7)
                canvas_obj.setFillColor(colors.HexColor("#667085"))
                canvas_obj.drawRightString(width - 10 * mm, height - 9 * mm, reference)
                canvas_obj.setStrokeColor(colors.HexColor("#D4DAE2"))
                canvas_obj.line(10 * mm, height - 11 * mm, width - 10 * mm, height - 11 * mm)
            canvas_obj.setStrokeColor(colors.HexColor("#D4DAE2"))
            canvas_obj.line(10 * mm, 11 * mm, width - 10 * mm, 11 * mm)
            canvas_obj.setFont(font, 7)
            canvas_obj.setFillColor(colors.HexColor("#667085"))
            canvas_obj.drawString(10 * mm, 7 * mm, footer_contact[:105] or issuer)
            canvas_obj.drawRightString(width - 10 * mm, 7 * mm, f"Sayfa {document.page} | {reference}")
            canvas_obj.restoreState()

        doc = SimpleDocTemplate(
            save_path,
            pagesize=A4,
            rightMargin=10 * mm,
            leftMargin=10 * mm,
            topMargin=14 * mm,
            bottomMargin=16 * mm,
            title=doc_title,
            author=issuer,
            subject=project or recipient,
        )
        doc.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
        return True, save_path
    except Exception as exc:
        logger.error("Custom editor proforma PDF error: %s", exc)
        return False, str(exc)
