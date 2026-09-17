import re
import unicodedata


def clean_offer_line_description(
    description,
    *,
    service="",
    brand="",
    model="",
    category="",
):
    """Keep import provenance out of customer-facing offer descriptions."""
    text = str(description or "").strip()
    normalized = unicodedata.normalize("NFKD", text)
    normalized = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    normalized = normalized.replace("\u0131", "i").casefold().strip()
    if normalized in {
        "web akilli ice aktarma",
        "akilli ice aktarma",
        "web smart import",
        "smart import",
    }:
        text = ""
    if text:
        return text
    details = []
    for value in (brand, model, category):
        value = str(value or "").strip()
        if value and value.casefold() not in {
            item.casefold() for item in details
        }:
            details.append(value)
    if details:
        return " / ".join(details)
    return "Stok \u00fcr\u00fcn\u00fc" if service else "-"


def split_service_work_text(value):
    result = []
    for raw_line in str(value or "").replace("\r\n", "\n").split("\n"):
        line = raw_line.strip().lstrip("-\u2022").strip()
        if not line:
            continue
        lowered = line.casefold()
        if lowered.startswith("bakim notu:"):
            continue
        if lowered.startswith("bakim kalemleri:"):
            line = line.split(":", 1)[1].strip()
        line = re.sub(r"\s+ve\s+\d+\s+kalem\s+daha\s*$", "", line, flags=re.IGNORECASE)
        parts = [part.strip() for part in line.split(",") if part.strip()]
        for part in parts or [line]:
            clean = re.sub(r"^\d+[.)]\s*", "", part).strip()
            if clean and clean.casefold() not in {item.casefold() for item in result}:
                result.append(clean)
    return result


def load_service_work_lines(db, tracking_no, repair_details="", fault_description=""):
    tracking_no = str(tracking_no or "").strip()
    cursor = getattr(db, "cursor", None) or db.conn.cursor()
    if tracking_no:
        try:
            device_columns = {
                row[1] for row in cursor.execute("PRAGMA table_info(devices)").fetchall()
            }
            card_id = None
            if "vehicle_maintenance_card_id" in device_columns:
                row = cursor.execute(
                    "SELECT vehicle_maintenance_card_id FROM devices "
                    "WHERE tracking_no=? ORDER BY id DESC LIMIT 1",
                    (tracking_no,),
                ).fetchone()
                card_id = row[0] if row else None
            if not card_id:
                table_row = cursor.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' "
                    "AND name='vehicle_maintenance_cards'"
                ).fetchone()
                if table_row:
                    row = cursor.execute(
                        "SELECT id FROM vehicle_maintenance_cards "
                        "WHERE linked_device_tracking_no=? ORDER BY id DESC LIMIT 1",
                        (tracking_no,),
                    ).fetchone()
                    card_id = row[0] if row else None
            if card_id:
                rows = cursor.execute(
                    "SELECT item_label FROM vehicle_maintenance_items "
                    "WHERE card_id=? AND COALESCE(performed,1)=1 ORDER BY id ASC",
                    (card_id,),
                ).fetchall()
                labels = [str(row[0] or "").strip() for row in rows]
                labels = [label for label in labels if label]
                if labels:
                    return labels
        except Exception:
            pass

    return split_service_work_text(repair_details or fault_description)


def format_numbered_work_lines(lines):
    return "\n".join(
        f"{index}. {str(line).strip()}"
        for index, line in enumerate(lines or [], 1)
        if str(line).strip()
    )
