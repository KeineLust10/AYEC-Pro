"""Read OFX and MT940 transactions for a local statement preview."""

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from html import unescape


def _amount(value):
    try:
        return Decimal(str(value).strip().replace(",", "."))
    except InvalidOperation as exc:
        raise ValueError("Invalid statement amount") from exc


def _ofx_value(block, tag):
    match = re.search(rf"<{re.escape(tag)}>\s*([^<\r\n]+)", block, re.I)
    return unescape(match.group(1).strip()) if match else ""


def _parse_ofx(text):
    rows = []
    for block in re.split(r"<STMTTRN>", text, flags=re.I)[1:]:
        date_text = _ofx_value(block, "DTPOSTED")[:8]
        amount_text = _ofx_value(block, "TRNAMT")
        if not re.fullmatch(r"\d{8}", date_text) or not amount_text:
            continue
        date = datetime.strptime(date_text, "%Y%m%d").date().isoformat()
        rows.append({
            "date": date,
            "amount": _amount(amount_text),
            "reference": _ofx_value(block, "FITID") or _ofx_value(block, "CHECKNUM"),
            "description": _ofx_value(block, "MEMO") or _ofx_value(block, "NAME"),
        })
    return rows


def _parse_mt940(text):
    rows = []
    current = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = re.match(r"^:61:(\d{6})(?:\d{4})?([CD])([A-Z])?([0-9,]+)", line)
        if match:
            date = datetime.strptime(match.group(1), "%y%m%d").date().isoformat()
            amount = _amount(match.group(4))
            if match.group(2) == "D":
                amount = -amount
            current = {
                "date": date,
                "amount": amount,
                "reference": line[match.end():].strip(),
                "description": "",
            }
            rows.append(current)
        elif line.startswith(":86:") and current:
            current["description"] = line[4:].strip()
        elif current and line and not line.startswith(":"):
            current["description"] = (
                current["description"] + " " + line
            ).strip()
    return rows


def parse_bank_statement(text, suffix):
    """Return validated statement rows without changing the ledger."""
    suffix = str(suffix or "").lower()
    if suffix == ".ofx":
        rows = _parse_ofx(text)
    elif suffix in {".mt940", ".sta", ".txt"}:
        rows = _parse_mt940(text)
    else:
        raise ValueError("Unsupported statement format")
    if not rows:
        raise ValueError("No statement transactions found")
    if len(rows) > 5000:
        raise ValueError("Statement contains too many transactions")
    return rows
