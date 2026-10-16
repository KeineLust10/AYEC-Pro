"""Capture Admin quota limits on desktop and mobile with offscreen PyQt."""

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

from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication

from admin_capture_fonts import load_system_fallback_fonts

from pages.limits import LimitsPage


def main() -> int:
    app = QApplication(sys.argv)
    available = load_system_fallback_fonts()
    if "segoe ui" not in available:
        QFont.insertSubstitution("Segoe UI", "Arial")
    app.setFont(QFont("Segoe UI", 9))

    LimitsPage._load = lambda _self: None
    page = LimitsPage()
    page._populate(
        [
            {"tenant_id": "tenant-a", "company_name": "ASLAN TIC", "license_code": "AYEC-1001", "package_name": "Kurumsal Paket", "db_size_mb": 1.64, "db_limit_gb": 10, "users_count": 2, "users_limit": 10, "devices_count": 20, "devices_limit": 100, "services_count": 248, "services_limit": 1000},
            {"tenant_id": "tenant-b", "company_name": "Babali Servis", "license_code": "AYEC-1002", "package_name": "Pro Paket", "db_size_mb": 0.69, "db_limit_gb": 5, "users_count": 2, "users_limit": 10, "devices_count": 0, "devices_limit": 100, "services_count": 45, "services_limit": 1000},
            {"tenant_id": "tenant-c", "company_name": "Bulut Bilisim Ltd.", "license_code": "AYEC-1003", "package_name": "Standart Paket", "db_size_mb": 0.71, "db_limit_gb": 5, "users_count": 2, "users_limit": 10, "devices_count": 2, "devices_limit": 100, "services_count": 86, "services_limit": 1000},
            {"tenant_id": "tenant-d", "company_name": "Isiktas Oto Servis", "license_code": "AYEC-1004", "package_name": "Pro Paket", "db_size_mb": 0.73, "db_limit_gb": 5, "users_count": 2, "users_limit": 10, "devices_count": 2, "devices_limit": 100, "services_count": 33, "services_limit": 1000},
        ]
    )
    page.resize(1440, 950)
    page.show()
    app.processEvents()
    if page._metric_columns != 4:
        return 10
    if page._metric_tenants.text() != "4" or page._metric_critical.text() != "0":
        return 2
    if page._metric_db.text() != "3.77 MB / 100 GB" or page._metric_users.text() != "8" or page._metric_devices.text() != "24 / 400 Cihaz" or page._metric_services.text() != "412 / 4,000 Fis":
        return 8
    if len(page._policy_controls) != 3 or page._upgrade_total.text() != "$ 750 / Ay" or page._upgrade_tenant.count() != 4:
        return 9
    artifacts = ROOT / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    if not page.grab().save(str(artifacts / "admin_quota_limits_pyqt_desktop.png"), "PNG"):
        return 3

    page.resize(390, 844)
    app.processEvents()
    if page._data_stack.currentWidget() is not page._mobile_list:
        return 4
    if page._metric_columns != 1:
        return 11
    if page._scroll.horizontalScrollBar().maximum() != 0:
        return 5
    if not page.grab().save(str(artifacts / "admin_quota_limits_pyqt_mobile.png"), "PNG"):
        return 6
    page._search.setText("tenant-a")
    app.processEvents()
    if page._mobile_layout.itemAt(0).widget().isHidden():
        return 7
    page.close()
    app.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
