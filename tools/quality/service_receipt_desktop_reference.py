"""Create an offscreen desktop service-receipt reference PDF for parity audits."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from datetime import datetime as _datetime

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils.pdf_manager import PDFManagerQt
import src.utils._pdf_service_mixin as _pdf_service_mixin


OUTPUT_DIR = Path(os.environ.get("AYEC_AUDIT_OUTPUT", ROOT / "output" / "playwright")).resolve()


class _ReceiptAuditDateTime(_datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 10, 17, 22, 55, 0, tzinfo=tz)


_pdf_service_mixin.datetime = _ReceiptAuditDateTime


class ReceiptSettings:
    values = {
        "company_name": "QA SERVICE CENTER",
        "company_address": "Workshop Road 10",
        "company_phone": "5551234567",
        "company_email": "qa@example.test",
        "company_website": "https://example.test",
        "service_terms": "Retain the signed service receipt for warranty claims.",
    }

    def get_setting(self, key, default=""):
        return self.values.get(key, default)


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manager = PDFManagerQt(ReceiptSettings())
    manager._get_save_path = lambda: str(OUTPUT_DIR)
    manager._open_file = lambda _path: None
    device = {
        "tracking_no": "SRV-QA-204",
        "customer_name": "Aylin Example",
        "customer_contact": "5551002000",
        "device_brand": "Acme",
        "device_model": "Z",
        "serial_no": "SN-204",
        "reported_fault": "Screen flickers",
        "repair_notes": "Replaced display cable",
        "status": "Tamirde",
        "delivery_method": "Elden",
        "delivered_by_name": "QA Handover",
        "delivered_by_phone": "5553004000",
    }
    parts = [
        {"part_name": "Display cable", "quantity": 2, "line_total": 50},
        {"part_name": "Connector", "quantity": 1, "unit_price": 50},
    ]
    success, result = manager.create_detailed_service_receipt(
        device,
        parts,
        25,
        page_size="A5",
        orientation="landscape",
    )
    source = Path(result)
    target = OUTPUT_DIR / "service-detailed-receipt-desktop.pdf"
    if not success or not source.is_file():
        raise RuntimeError(f"Desktop service receipt generation failed: {result}")
    if source.resolve() != target.resolve():
        target.write_bytes(source.read_bytes())
        source.unlink(missing_ok=True)
    print(json.dumps({"pdf": str(target), "bytes": target.stat().st_size}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
