"""Capture the Admin Console customer 360 page at desktop and mobile sizes."""

import os
import sys
from pathlib import Path

os.environ["PYTHONIOENCODING"] = "utf-8"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from PyQt6.QtWidgets import QBoxLayout, QWidget
from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[2]
ADMIN_ROOT = ROOT / "Admin_Konsol"
sys.path.insert(0, str(ADMIN_ROOT))
sys.path.insert(0, str(ROOT / "tools" / "quality"))

from admin_capture_fonts import load_system_fallback_fonts
from pages.customer_360 import Customer360Page, _Customer360Thread
import api_client


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    available = {family.casefold() for family in load_system_fallback_fonts()}
    if "segoe ui" not in available:
        QFont.insertSubstitution("Segoe UI", "Arial")
    if "arial" not in available:
        QFont.insertSubstitution("Arial", "Segoe UI")
    loaded = {family.casefold() for family in QFontDatabase.families()}
    if "jetbrains mono" not in loaded:
        QFont.insertSubstitution("JetBrains Mono", "Arial")
    app.setFont(QFont("Segoe UI", 10))

    companies = [
        {"id": "tenant-1", "company_name": "ASLAN TIC", "active": 1, "online": True, "contact_name": "Engin ASLAN", "phone": "0534 878 10 47", "email": "enginmamu22@gmail.com", "sector": "teknik_servis", "license_type": "3 Yillik Kurumsal", "license_end": "2029-10-07", "last_login": "2026-10-14"},
        {"id": "tenant-2", "company_name": "Babali", "active": 1, "online": True, "contact_name": "Emirhan BABALI", "phone": "0535 535 35 35", "email": "babalieemirhan048@gmail.com", "sector": "Otomotiv", "license_type": "Lifetime Pro"},
        {"id": "tenant-3", "company_name": "Bulut Bilisim", "active": 1, "online": True, "contact_name": "Engin MAMU", "phone": "0534 878 10 47", "email": "enginmamu1@gmail.com", "sector": "IT & Servis", "license_type": "Lifetime Core"},
        {"id": "tenant-4", "company_name": "Isiktas Oto Servis", "active": 1, "online": True, "contact_name": "Hasan ISIKTAS", "phone": "0534 123 45 67", "email": "hasanisiktas@icloud.com", "sector": "Mekanik Oto", "license_type": "Lifetime Pro"},
    ]
    payload = {
        "company": companies[0],
        "summary": {"user_count": 2, "backup_count": 1, "error_count": 0, "audit_count": 8, "online": True},
        "licenses": [{"license_type": "3 Yillik Kurumsal", "status": "active"}],
        "backups": [{"filename": "ASLAN_TIC.db"}],
        "live_status": {"hardware_id": "WS-02", "ping_ms": 11},
        "error_logs": [],
        "audit_logs": [{"action": "AUTH_OK"}],
        "users": [
            {"id": 1, "full_name": "Engin ASLAN", "username": "enginmamu22", "email": "enginmamu22@gmail.com", "phone": "05348781047", "role": "user", "active": 1},
            {"id": 2, "full_name": "AYEC Platform Owner", "username": "ayepro", "email": "ayepro@gmail.com", "role": "admin", "active": 1, "last_login": "2026-10-14 05:09:33"},
        ],
    }
    api_client.companies = lambda: companies
    api_client.customer_360 = lambda _tenant_id: payload
    _Customer360Thread.run = lambda worker: worker.loaded.emit(api_client.customer_360(worker._tenant_id))

    page = Customer360Page()
    if page._thread:
        page._thread.wait(3000)
    app.processEvents()
    page.resize(1440, 1000)
    page.show()
    app.processEvents()
    artifacts = ROOT / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    desktop_path = artifacts / "admin_customer_360_desktop_offscreen.png"
    if not page.grab().save(str(desktop_path), "PNG"):
        return 1
    if page._page_scroll.horizontalScrollBar().maximum() != 0:
        return 2

    page.resize(390, 844)
    app.processEvents()
    mobile_path = artifacts / "admin_customer_360_mobile_offscreen.png"
    if not page.grab().save(str(mobile_path), "PNG"):
        return 3
    if page._workspace_layout.direction() != QBoxLayout.Direction.TopToBottom:
        return 4
    if page._page_scroll.horizontalScrollBar().maximum() != 0:
        content = page._page_scroll.widget()
        overflow = []
        for widget in content.findChildren(QWidget):
            position = widget.mapTo(content, widget.rect().topLeft())
            if position.x() + widget.width() > content.width():
                overflow.append((widget.objectName(), type(widget).__name__, position.x(), widget.width()))
        print({"content_width": content.width(), "content_min": content.minimumSizeHint().width(), "content_hint": content.sizeHint().width(), "viewport_width": page._page_scroll.viewport().width(), "scroll": page._page_scroll.horizontalScrollBar().maximum(), "root_min": page._root_layout.minimumSize().width(), "root_hint": page._root_layout.sizeHint().width(), "root_items": [(page._root_layout.itemAt(index).layout().minimumSize().width() if page._root_layout.itemAt(index).layout() else -1, page._root_layout.itemAt(index).layout().sizeHint().width() if page._root_layout.itemAt(index).layout() else -1) for index in range(page._root_layout.count())], "detail_min": page._detail_scroll.minimumSizeHint().width(), "list_min": page._list_column.minimumSizeHint().width(), "overflow": overflow[:8]})
        return 5
    if page._page_scroll.verticalScrollBar().maximum() <= 0:
        return 6
    page.close()
    app.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
