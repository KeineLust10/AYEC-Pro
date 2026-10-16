from __future__ import annotations

import os
import sys
from pathlib import Path

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["PYTHONIOENCODING"] = "utf-8"

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Admin_Konsol"))

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication, QScrollArea

from admin_capture_fonts import load_system_fallback_fonts

import api_client
from pages.license_requests import LicenseRequestsPage


def main() -> int:
    app = QApplication(sys.argv)
    fonts = load_system_fallback_fonts()
    if "segoe ui" not in fonts:
        QFont.insertSubstitution("Segoe UI", "Arial")
    QFont.insertSubstitution("Plus Jakarta Sans", "Segoe UI")
    QFont.insertSubstitution("JetBrains Mono", "Arial")
    app.setFont(QFont("Segoe UI", 10))
    api_client.license_orders = lambda status="", product_code="": []
    api_client.licenses = lambda product_code="": []
    api_client.provision_invites = lambda: {
        "invites": [
            {
                "id": index,
                "expires_at": "2028-10-14T00:00:00+00:00",
                "max_uses": 1,
                "use_count": 0 if index <= 12 or index > 46 else 1,
                "revoked_at": "2026-10-14T00:00:00+00:00" if index > 46 else None,
            }
            for index in range(1, 49)
        ]
    }
    page = LicenseRequestsPage()
    if page.worker:
        page.worker.wait(3000)
    if page.license_worker:
        page.license_worker.wait(3000)
    if page.invite_worker:
        page.invite_worker.wait(3000)
    app.processEvents()
    page.populate(
        [
            {
                "id": 1,
                "request_no": "REQ-9921",
                "company_name": "ASLAN TIC LTD STI",
                "requester_name": "Engin",
                "requester_email": "admin@aslan.example",
                "plan_label": "3 Year Corporate",
                "amount_try": 15990,
                "payment_reference": "PAY-1001",
                "status": "payment_reported",
                "created_at": "2026-10-14 09:42",
                "description": "ASLAN TIC icin lisans uzatma ve ilave 10 koltuk terminal paketi siparisi. Mali muhur ve dekont kontrolu yapildi, derleme emri bekleniyor.",
            },
            {
                "id": 2,
                "request_no": "REQ-9922",
                "company_name": "Babali Servis Teknoloji",
                "requester_name": "Bora",
                "plan_label": "Lifetime Core",
                "amount_try": 4500,
                "payment_reference": "PAY-1002",
                "status": "active",
                "created_at": "2026-10-14 09:38",
                "description": "Teknik Servis ana modulune ilave Otomotiv Teslis ve Barkod yazici terminal lisansi aktivasyonu. Odeme provizyonu tamamlandi.",
            },
        ]
    )
    page.populate_inventory(
        [
            {
                "company_name": "ASLAN TIC",
                "product_code": "teknik_servis",
                "license_code": "AYEC-TS-8841-K992-SEC",
                "license_type": "3 Year Corporate",
                "license_end": "2028-10-14",
                "license_updated_at": "2026-10-14",
                "status": "Aktif",
                "online": True,
                "active_users": 2,
            },
            {
                "company_name": "Babali Servis",
                "product_code": "otomotiv",
                "license_code": "AYEC-TS-3310-M104-SEC",
                "license_type": "Lifetime",
                "status": "Aktif",
                "online": True,
                "active_users": 1,
            },
            {
                "company_name": "Bulut Bilisim & Donanim",
                "product_code": "teknik_servis",
                "license_code": "AYEC-TS-9923-P008-SEC",
                "license_type": "1 Year Pro",
                "license_end": "2027-10-14",
                "status": "Aktif",
                "online": True,
                "active_users": 5,
            },
            {
                "company_name": "Isiktas Oto Elektronik Servis Terminali",
                "product_code": "otomotiv",
                "license_code": "AYEC-TS-1200-Z441-SEC",
                "license_type": "15 Gunluk Pilot",
                "license_end": "2026-10-29",
                "status": "Aktif",
                "online": True,
                "active_users": 3,
            },
        ]
    )
    page.resize(1152, 1000)
    page.show()
    app.processEvents()
    scroll = page.findChild(QScrollArea, "licenseScroll")
    if scroll is None or scroll.horizontalScrollBar().maximum() != 0:
        return 2
    desktop_path = ROOT / "artifacts" / "admin_license_requests_pyqt_desktop_offscreen.png"
    if not page.grab().save(str(desktop_path), "PNG"):
        return 3
    page.resize(390, 844)
    app.processEvents()
    if scroll.horizontalScrollBar().maximum() != 0:
        return 4
    image_path = ROOT / "artifacts" / "admin_license_requests_mobile_offscreen.png"
    if not page.grab().save(str(image_path), "PNG"):
        return 5
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
