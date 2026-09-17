"""Professional proforma PDF builder shared by desktop and synchronized offers."""

from __future__ import annotations

import os
from io import BytesIO
from datetime import date, datetime, timedelta
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


_TEXT = {
    "title": "F\u0130YAT TEKL\u0130F\u0130",
    "invoice": "FATURA",
    "issuer": "TEKL\u0130F\u0130 VEREN",
    "recipient": "TEKL\u0130F VER\u0130LEN",
    "customer": "M\u00fc\u015fteri / Firma",
    "contact": "Yetkili",
    "project": "Proje",
    "offer_no": "Teklif No",
    "date": "Tarih",
    "valid_until": "Ge\u00e7erlilik",
    "currency": "Para Birimi",
    "item": "H\u0130ZMET / \u00dcR\u00dcN",
    "description": "A\u00c7IKLAMA",
    "quantity": "ADET",
    "unit_price": "B\u0130R\u0130M F\u0130YAT",
    "amount": "TUTAR",
    "subtotal": "Ara Toplam",
    "discount": "\u0130skonto",
    "vat": "KDV",
    "grand_total": "GENEL TOPLAM",
    "terms": "T\u0130CAR\u0130 KO\u015eULLAR",
    "approval": "TEKL\u0130F ONAYI",
    "issuer_signature": "Teklifi Haz\u0131rlayan",
    "customer_signature": "M\u00fc\u015fteri Onay\u0131 / Ka\u015fe - \u0130mza",
    "page": "Sayfa",
    "unspecified": "Belirtilmedi",
}

_PDF_METADATA_TITLE = "FIYAT TEKLIFI"


def _safe(value) -> str:
    return escape(str(value or "").strip())


def _setting(manager, key: str, default="") -> str:
    try:
        return str(manager.db.get_setting(key, default) or default).strip()
    except Exception:
        return str(default or "").strip()


def _prepare_logo_source(logo_path):
    """Crop dark canvas logos and place them on a print-safe white background."""
    try:
        from PIL import Image as PilImage, ImageChops

        source = PilImage.open(logo_path).convert("RGB")
        width, height = source.size
        if width < 2 or height < 2:
            return logo_path
        corners = (
            source.getpixel((0, 0)),
            source.getpixel((width - 1, 0)),
            source.getpixel((0, height - 1)),
            source.getpixel((width - 1, height - 1)),
        )
        corner_level = sum(max(pixel) for pixel in corners) / len(corners)
        if corner_level >= 45:
            return logo_path

        red, green, blue = source.split()
        max_channel = ImageChops.lighter(red, ImageChops.lighter(green, blue))
        alpha = max_channel.point(lambda value: max(0, min(255, (value - 8) * 8)))
        bbox = alpha.point(lambda value: 255 if value > 20 else 0).getbbox()
        if not bbox:
            return logo_path

        pad_x = max(4, int(width * 0.015))
        pad_y = max(4, int(height * 0.015))
        left = max(0, bbox[0] - pad_x)
        top = max(0, bbox[1] - pad_y)
        right = min(width, bbox[2] + pad_x)
        bottom = min(height, bbox[3] + pad_y)
        source = source.crop((left, top, right, bottom))
        alpha = alpha.crop((left, top, right, bottom))

        rgba = source.convert("RGBA")
        rgba.putalpha(alpha)
        printable = PilImage.new("RGBA", rgba.size, (255, 255, 255, 255))
        printable.alpha_composite(rgba)
        stream = BytesIO()
        printable.convert("RGB").save(stream, format="PNG")
        stream.seek(0)
        return stream
    except Exception as exc:
        logger.debug("Proforma logo preparation skipped: %s", exc)
        return logo_path


def _parse_date(value) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    text = str(value or "").strip()
    if text:
        for candidate in (text, text.replace("Z", "+00:00")):
            try:
                return datetime.fromisoformat(candidate)
            except ValueError:
                pass
        for pattern in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(text[:10], pattern)
            except ValueError:
                pass
    return datetime.now()


def _date_text(value) -> str:
    return _parse_date(value).strftime("%d.%m.%Y")


def _number(value, decimals=2) -> str:
    raw = f"{float(value or 0):,.{decimals}f}"
    return raw.replace(",", "_").replace(".", ",").replace("_", ".")


def _quantity(value) -> str:
    number = float(value or 0)
    if abs(number - round(number)) < 0.000001:
        return str(int(round(number)))
    return _number(number, 2)


def _currency_code(currency, currency_code=None) -> str:
    code = str(currency_code or "").strip().upper()
    if code:
        return {"TL": "TRY"}.get(code, code)
    symbol = str(currency or "").strip()
    return {"$": "USD", "\u20ac": "EUR", "\u20ba": "TRY", "TL": "TRY"}.get(
        symbol,
        symbol.upper() or "TRY",
    )


def _currency_label(code: str) -> str:
    return {
        "TRY": "T\u00fcrk Liras\u0131 (TRY)",
        "USD": "Amerikan Dolar\u0131 (USD)",
        "EUR": "Euro (EUR)",
        "GBP": "\u0130ngiliz Sterlini (GBP)",
    }.get(code, code)


def _money(value, currency, code: str) -> str:
    symbol = str(currency or "").strip()
    if not symbol:
        symbol = {"TRY": "\u20ba", "USD": "$", "EUR": "\u20ac"}.get(code, code)
    amount = _number(value)
    return f"{symbol} {amount}" if symbol in {"$", "\u20ac", "\u00a3"} else f"{amount} {symbol}"


def _document_money(value, code: str) -> str:
    amount = f"{float(value or 0):,.2f}"
    amount = amount.replace(",", "_").replace(".", ",").replace("_", ".")
    label = "TL" if str(code or "TRY").upper() == "TRY" else str(code).upper()
    return f"{amount} {label}"


def _financial_summary_rows(totals, code: str, totals_try=None):
    subtotal, discount, vat_rate, vat_amount, grand_total = totals
    vat_rate = float(vat_rate or 0)
    if vat_rate > 1:
        vat_rate /= 100.0
    vat_label = f"Hesaplanan KDV(%{vat_rate * 100:.2f})"
    code = str(code or "TRY").upper()
    rows = [
        ("Mal Hizmet Toplam Tutar\u0131", _document_money(subtotal, code), False),
        ("Toplam \u0130skonto", _document_money(discount, code), False),
        (vat_label, _document_money(vat_amount, code), False),
        ("Vergiler Dahil Toplam Tutar", _document_money(grand_total, code), False),
        ("\u00d6denecek Tutar", _document_money(grand_total, code), True),
    ]
    if code == "TRY" or not totals_try:
        return rows

    subtotal_try, _discount_try, vat_rate_try, vat_amount_try, total_try = totals_try
    vat_rate_try = float(vat_rate_try or 0)
    if vat_rate_try > 1:
        vat_rate_try /= 100.0
    rows.extend(
        [
            (
                f"Hesaplanan KDV(%{vat_rate_try * 100:.2f}) (TL)",
                _document_money(vat_amount_try, "TRY"),
                False,
            ),
            (
                "Mal Hizmet Toplam Tutar\u0131 (TL)",
                _document_money(subtotal_try, "TRY"),
                False,
            ),
            (
                "Vergiler Dahil Toplam Tutar (TL)",
                _document_money(total_try, "TRY"),
                False,
            ),
            ("\u00d6denecek Tutar (TL)", _document_money(total_try, "TRY"), True),
        ]
    )
    return rows


def _default_terms(code: str, validity_days: int) -> str:
    currency_name = _currency_label(code)
    return "\n".join(
        [
            f"Fiyat : Teklif tutarlar\u0131 {currency_name} cinsindendir.",
            "\u00d6deme : Sipari\u015fte toplam tutar\u0131n %50'si, kalan bakiye i\u015f tesliminde \u00f6denir.",
            "Teslimat : Termin s\u00fcresi sipari\u015f, \u00f6n \u00f6deme ve stok onay\u0131ndan sonra kesinle\u015fir.",
            "Garanti : \u00dcr\u00fcn ve hizmetler, ilgili \u00fcretici ve hizmet garanti ko\u015fullar\u0131na tabidir.",
            f"Ge\u00e7erlilik : Bu teklif d\u00fczenleme tarihinden itibaren {validity_days} g\u00fcn ge\u00e7erlidir.",
        ]
    )


def _terms(manager, code: str, validity_days: int) -> str:
    custom = _setting(manager, "offer_contract")
    service = _setting(manager, "service_contract")
    text = custom or service
    if not text:
        return _default_terms(code, validity_days)

    currency_line = f"Fiyat : Teklif tutarlar\u0131 {_currency_label(code)} cinsindendir."
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip().casefold().startswith("fiyat"):
            lines[index] = currency_line
            break
    else:
        lines.insert(0, currency_line)
    # Correct the common legacy contract typo without mutating the saved setting.
    return "\n".join(lines).replace("%50'i", "%50'si")


def _palette(template_type: str):
    palettes = {
        "modern": ("#145A86", "#EAF3F9", "#0F766E"),
        "corporate": ("#243B53", "#EDF2F7", "#B7791F"),
        "minimal": ("#222222", "#F2F2F2", "#555555"),
        "bulut_deri": ("#145A86", "#EAF3F9", "#0F766E"),
    }
    primary, pale, accent = palettes.get(str(template_type or "modern").lower(), palettes["modern"])
    return colors.HexColor(primary), colors.HexColor(pale), colors.HexColor(accent)


def _company_lines(manager):
    phone = _setting(manager, "company_phone")
    gsm = _setting(manager, "company_gsm")
    email = _setting(manager, "company_email")
    website = _setting(manager, "company_website")
    address = _setting(manager, "company_address")
    lines = []
    if phone or gsm:
        lines.append(" / ".join(part for part in (phone, gsm) if part))
    if email or website:
        lines.append(" / ".join(part for part in (email, website) if part))
    lines.extend(line.strip() for line in address.splitlines() if line.strip())
    return lines


def _item_content(item):
    name = str(item.get("service") or item.get("name") or "Hizmet / Urun").strip()
    description = str(item.get("description") or "").strip()
    if description.casefold() == name.casefold():
        description = ""
    meta = []
    for label, key in (("Kod", "code"), ("Marka", "brand"), ("Model", "model")):
        value = str(item.get(key) or "").strip()
        if value:
            meta.append(f"{label}: {_safe(value)}")
    detail_parts = []
    if description:
        detail_parts.append(_safe(description).replace("\n", "<br/>"))
    if meta:
        detail_parts.append(f'<font color="#667085" size="7.5">{" | ".join(meta)}</font>')
    return _safe(name), "<br/>".join(detail_parts) or "-"


def build_professional_proforma(
    manager,
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
    """Build a consistent, print-ready A4 commercial offer."""
    try:
        issue_date = _parse_date(offer_date)
        validity_days = max(1, int(validity_days or 15))
        valid_until = issue_date + timedelta(days=validity_days)
        code = _currency_code(currency, currency_code)
        primary, pale, accent = _palette(template_type)
        issuer = str(company_name or _setting(manager, "company_name", "AYEC Pro")).strip()
        recipient = str(customer_company or customer_name or "Say\u0131n \u0130lgili").strip()
        contact = str(contact_name or customer_name or "").strip()
        project = str(project_name or "").strip()
        reference = str(reference_no or f"PRF-{issue_date.strftime('%Y%m%d-%H%M')}").strip()
        subtotal, discount, vat_rate, vat_amount, grand_total = totals
        vat_rate = float(vat_rate or 0)
        if vat_rate > 1:
            vat_rate /= 100.0
        if code != "TRY" and not totals_try:
            rate = float(exchange_rate or 0)
            if rate <= 0:
                try:
                    from src.utils.exchange_rate_manager import ExchangeRateManager

                    rate = float(
                        ExchangeRateManager.get_current_rate(manager.db, code)
                        or 1.0
                    )
                except Exception:
                    rate = 1.0
            totals_try = (
                float(subtotal or 0) * rate,
                float(discount or 0) * rate,
                vat_rate,
                float(vat_amount or 0) * rate,
                float(grand_total or 0) * rate,
            )

        if not save_path:
            directory = manager._get_save_path()
            safe_recipient = manager._safe_filename(recipient)
            save_path = os.path.join(directory, f"Teklif_{safe_recipient}_{issue_date.strftime('%Y%m%d')}.pdf")
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)

        font, font_bold = manager._register_fonts()
        normal = ParagraphStyle("ProformaBody", fontName=font, fontSize=8.5, leading=11, textColor=colors.HexColor("#273444"))
        small = ParagraphStyle("ProformaSmall", parent=normal, fontSize=7.5, leading=9.5, textColor=colors.HexColor("#667085"))
        bold = ParagraphStyle("ProformaBold", parent=normal, fontName=font_bold)
        title_style = ParagraphStyle("ProformaTitle", fontName=font_bold, fontSize=17, leading=20, textColor=primary, alignment=2)
        section_style = ParagraphStyle("ProformaSection", fontName=font_bold, fontSize=8, leading=10, textColor=primary)
        table_head = ParagraphStyle("ProformaTableHead", fontName=font_bold, fontSize=7.5, leading=9, textColor=colors.white, alignment=1)
        table_head_left = ParagraphStyle("ProformaTableHeadLeft", parent=table_head, alignment=0)
        cell = ParagraphStyle("ProformaCell", parent=normal, fontSize=8, leading=10)
        cell_center = ParagraphStyle("ProformaCellCenter", parent=cell, alignment=1)
        cell_right = ParagraphStyle("ProformaCellRight", parent=cell, alignment=2)
        total_label = ParagraphStyle("ProformaTotalLabel", parent=normal, alignment=2)
        total_bold = ParagraphStyle("ProformaTotalBold", parent=bold, fontSize=10, leading=12, alignment=2, textColor=accent)

        story = []
        logo_path = _setting(manager, "logo_path")
        logo = ""
        if logo_path and os.path.exists(logo_path):
            logo = Image(_prepare_logo_source(logo_path), mask="auto")
            logo._restrictSize(48 * mm, 17 * mm)
            logo.hAlign = "LEFT"
        company_subtitle = _setting(manager, "site_title")
        brand_text = _safe(issuer)
        if company_subtitle and company_subtitle.casefold() != issuer.casefold():
            brand_text += f'<br/><font size="8" color="#667085">{_safe(company_subtitle)}</font>'
        brand = Paragraph(brand_text, ParagraphStyle("ProformaBrand", parent=bold, fontSize=13, leading=16, textColor=primary))
        heading = Paragraph(
            f"{_TEXT['invoice'] if is_invoice else _TEXT['title']}<br/>"
            f'<font size="8" color="#667085">{_safe(reference)}</font>',
            title_style,
        )
        # A configured logo commonly already contains the company wordmark.
        # Avoid printing the issuer name a second time beside that logo.
        header = Table([[logo or brand, "", heading]], colWidths=[50 * mm, 78 * mm, 62 * mm])
        header.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LINEBELOW", (0, 0), (-1, -1), 1.2, primary),
        ]))
        story.extend([header, Spacer(1, 5 * mm)])

        issuer_lines = [f"<b>{_safe(issuer)}</b>"] + [_safe(line) for line in _company_lines(manager)]
        offer_meta = [
            f"<b>{_TEXT['offer_no']}:</b> {_safe(reference)}",
            f"<b>{_TEXT['date']}:</b> {_date_text(issue_date)}",
            f"<b>{_TEXT['valid_until']}:</b> {_date_text(valid_until)}",
            f"<b>{_TEXT['currency']}:</b> {_safe(_currency_label(code))}",
        ]
        info = Table([
            [Paragraph(_TEXT["issuer"], section_style), Paragraph("TEKL\u0130F B\u0130LG\u0130LER\u0130", section_style)],
            [Paragraph("<br/>".join(issuer_lines), normal), Paragraph("<br/>".join(offer_meta), normal)],
        ], colWidths=[110 * mm, 80 * mm])
        info.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), pale),
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#CDD5DF")),
            ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D8DEE7")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.extend([info, Spacer(1, 4 * mm)])

        recipient_lines = [f"<b>{_TEXT['customer']}:</b> {_safe(recipient)}"]
        if contact and contact.casefold() != recipient.casefold():
            recipient_lines.append(f"<b>{_TEXT['contact']}:</b> {_safe(contact)}")
        if project:
            recipient_lines.append(f"<b>{_TEXT['project']}:</b> {_safe(project)}")
        recipient_box = Table([
            [Paragraph(_TEXT["recipient"], section_style)],
            [Paragraph("<br/>".join(recipient_lines), normal)],
        ], colWidths=[190 * mm])
        recipient_box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), pale),
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#CDD5DF")),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.extend([recipient_box, Spacer(1, 5 * mm)])

        rows = [[
            Paragraph("#", table_head),
            Paragraph(_TEXT["item"], table_head_left),
            Paragraph(_TEXT["description"], table_head_left),
            Paragraph(_TEXT["quantity"], table_head),
            Paragraph(_TEXT["unit_price"], table_head),
            Paragraph(_TEXT["amount"], table_head),
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
        items_table = Table(rows, colWidths=[9 * mm, 43 * mm, 60 * mm, 14 * mm, 30 * mm, 34 * mm], repeatRows=1)
        items_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), primary),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, pale]),
            ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#CBD3DD")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("VALIGN", (2, 1), (2, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.extend([items_table, Spacer(1, 3 * mm)])

        total_rows = []
        for label, value, emphasized in _financial_summary_rows(
            totals,
            code,
            totals_try=totals_try,
        ):
            style = total_bold if emphasized else total_label
            value_style = total_bold if emphasized else cell_right
            total_rows.append(
                ["", Paragraph(label, style), Paragraph(value, value_style)]
            )
        totals_table = Table(total_rows, colWidths=[105 * mm, 45 * mm, 40 * mm])
        totals_table.setStyle(TableStyle([
            ("BACKGROUND", (1, 0), (-1, -2), pale),
            ("BACKGROUND", (1, -1), (-1, -1), colors.HexColor("#E7F4EF")),
            ("LINEABOVE", (1, -1), (-1, -1), 1, accent),
            ("BOX", (1, 0), (-1, -1), 0.5, colors.HexColor("#CBD3DD")),
            ("INNERGRID", (1, 0), (-1, -1), 0.35, colors.HexColor("#D8DEE7")),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.extend([totals_table, Spacer(1, 5 * mm)])

        term_rows = [[Paragraph(_TEXT["terms"], section_style)]]
        for line in _terms(manager, code, validity_days).splitlines():
            line = line.strip()
            if not line:
                continue
            if ":" in line:
                label, value = line.split(":", 1)
                line = f"<b>{_safe(label.strip())}:</b> {_safe(value.strip())}"
            else:
                line = _safe(line)
            term_rows.append([Paragraph(line, small)])
        terms_table = Table(term_rows, colWidths=[190 * mm])
        terms_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), pale),
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#CDD5DF")),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))

        signatures = Table([
            [Paragraph(_TEXT["issuer_signature"], section_style), Paragraph(_TEXT["customer_signature"], section_style)],
            [Paragraph(f"{_safe(issuer)}<br/><br/><br/>\u0130mza: ____________________", small), Paragraph("Ad Soyad: ____________________<br/><br/>Tarih: ________________________<br/>\u0130mza: ____________________", small)],
        ], colWidths=[95 * mm, 95 * mm], rowHeights=[8 * mm, 25 * mm])
        signatures.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), pale),
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#CDD5DF")),
            ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D8DEE7")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(terms_table)
        if include_approval:
            story.extend([
                Spacer(1, 5 * mm),
                KeepTogether([
                    Paragraph(_TEXT["approval"], section_style),
                    Spacer(1, 2 * mm),
                    signatures,
                ]),
            ])

        footer_contact = " | ".join(_company_lines(manager)[:2])

        def draw_page(canvas_obj, document):
            canvas_obj.saveState()
            canvas_obj.setTitle(f"{_PDF_METADATA_TITLE} - {reference}")
            canvas_obj.setAuthor(issuer)
            canvas_obj.setSubject(project or recipient)
            width, _height = A4
            if document.page > 1:
                canvas_obj.setFont(font_bold, 8)
                canvas_obj.setFillColor(primary)
                canvas_obj.drawString(10 * mm, _height - 9 * mm, _TEXT["title"])
                canvas_obj.setFont(font, 7)
                canvas_obj.setFillColor(colors.HexColor("#667085"))
                canvas_obj.drawRightString(width - 10 * mm, _height - 9 * mm, reference)
                canvas_obj.setStrokeColor(colors.HexColor("#D4DAE2"))
                canvas_obj.line(10 * mm, _height - 11 * mm, width - 10 * mm, _height - 11 * mm)
            canvas_obj.setStrokeColor(colors.HexColor("#D4DAE2"))
            canvas_obj.line(10 * mm, 11 * mm, width - 10 * mm, 11 * mm)
            canvas_obj.setFont(font, 7)
            canvas_obj.setFillColor(colors.HexColor("#667085"))
            canvas_obj.drawString(10 * mm, 7 * mm, footer_contact[:105] or issuer)
            canvas_obj.drawRightString(width - 10 * mm, 7 * mm, f"{_TEXT['page']} {document.page} | {reference}")
            canvas_obj.restoreState()

        doc = SimpleDocTemplate(
            save_path,
            pagesize=A4,
            rightMargin=10 * mm,
            leftMargin=10 * mm,
            topMargin=14 * mm,
            bottomMargin=16 * mm,
            title=f"{_PDF_METADATA_TITLE} - {reference}",
            author=issuer,
            subject=project or recipient,
        )
        doc.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
        manager._open_file(save_path)
        return True, save_path
    except Exception as exc:
        logger.error("Professional proforma PDF error: %s", exc)
        return False, str(exc)
