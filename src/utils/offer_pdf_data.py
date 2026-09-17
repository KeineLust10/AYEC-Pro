import json

from src.utils.service_work_details import (
    clean_offer_line_description,
    format_numbered_work_lines,
    load_service_work_lines,
)


def _row_as_dict(cursor, row):
    if row is None:
        return {}
    if hasattr(row, "keys"):
        return dict(row)
    return {
        column[0]: value
        for column, value in zip(cursor.description or (), row)
    }


def load_offer_pdf_data(db, offer_id):
    cursor = db.conn.cursor()
    cursor.execute("SELECT * FROM offers WHERE id=?", (int(offer_id),))
    offer = _row_as_dict(cursor, cursor.fetchone())
    if not offer:
        raise LookupError("Teklif kaydi bulunamadi.")

    customer_company = ""
    customer_id = offer.get("customer_id")
    if customer_id:
        try:
            cursor.execute(
                "SELECT COALESCE(company_name, '') FROM customers WHERE id=?",
                (int(customer_id),),
            )
            company_row = cursor.fetchone()
            if company_row:
                customer_company = str(company_row[0] or "").strip()
        except Exception:
            customer_company = ""

    cursor.execute(
        "SELECT * FROM offer_items WHERE offer_id=? ORDER BY id",
        (int(offer_id),),
    )
    item_rows = [_row_as_dict(cursor, row) for row in cursor.fetchall()]
    cart_items = []
    for item in item_rows:
        try:
            payload = json.loads(item.get("payload_json") or "{}")
        except (TypeError, ValueError):
            payload = {}
        service_name = item.get("service") or payload.get("name") or "Urun / Hizmet"
        description = clean_offer_line_description(
            item.get("description") or payload.get("description"),
            service=service_name,
            brand=item.get("brand") or payload.get("brand") or "",
            model=payload.get("model") or "",
            category=payload.get("category") or "",
        )
        tracking_no = str(payload.get("tracking_no") or "").strip()
        if not tracking_no and str(service_name).casefold().startswith("servis iscilik"):
            candidate = str(offer.get("project_name") or "").strip()
            try:
                row = cursor.execute(
                    "SELECT tracking_no, repair_details, fault_description FROM devices "
                    "WHERE tracking_no=? ORDER BY id DESC LIMIT 1",
                    (candidate,),
                ).fetchone()
            except Exception:
                row = None
            if row:
                tracking_no = str(row[0] or "").strip()
                lines = load_service_work_lines(
                    db,
                    tracking_no,
                    repair_details=row[1],
                    fault_description=row[2],
                )
                description = format_numbered_work_lines(lines) or description
        cart_items.append(
            {
                "service": service_name,
                "name": service_name,
                "description": description,
                "brand": item.get("brand") or payload.get("brand") or "",
                "model": payload.get("model") or "",
                "code": payload.get("code") or "",
                "qty": float(item.get("qty") or payload.get("qty") or 1),
                "price": float(item.get("unit_price") or payload.get("price") or 0),
            }
        )

    if not cart_items:
        try:
            payload = json.loads(offer.get("payload_json") or "{}")
            cart_items = list(payload.get("items") or [])
        except (TypeError, ValueError):
            cart_items = []
    if not cart_items:
        raise ValueError("Teklif kalemleri bulunamadi.")

    vat_rate = float(offer.get("vat_rate") or 0)
    if vat_rate > 1:
        vat_rate /= 100.0
    currency_code = str(offer.get("currency_code") or "TRY").upper()
    currency_symbol = str(offer.get("currency_symbol") or "").strip()
    allowed_symbols = ("$", "EUR", "USD", "TRY", "TL", "\u20ba", "\u20ac")
    if not currency_symbol or currency_symbol not in allowed_symbols:
        currency_symbol = {"TRY": "\u20ba", "USD": "$", "EUR": "\u20ac"}.get(
            currency_code,
            currency_code,
        )

    return {
        "offer": offer,
        "items": cart_items,
        "totals": (
            float(offer.get("subtotal") or 0),
            float(offer.get("discount") or 0),
            vat_rate,
            float(offer.get("vat_amount") or 0),
            float(offer.get("total") or 0),
        ),
        "currency_symbol": currency_symbol,
        "currency_code": currency_code,
        "customer_company": customer_company,
    }
