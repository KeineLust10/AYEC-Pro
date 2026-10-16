"""Capture the Admin SQL diagnostic screen with offscreen PyQt rendering."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["PYTHONIOENCODING"] = "utf-8"

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Admin_Konsol"))

from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication, QScrollArea

from admin_capture_fonts import load_system_fallback_fonts

import api_client
from pages.database_manager import DatabaseManagerPage


def main() -> int:
    app = QApplication(sys.argv)
    available_fonts = load_system_fallback_fonts()
    mono_font_path = ROOT / "assets" / "fonts" / "JetBrainsMono-Regular.ttf"
    if mono_font_path.is_file():
        QFontDatabase.addApplicationFont(str(mono_font_path))
    if "segoe ui" not in available_fonts:
        QFont.insertSubstitution("Segoe UI", "Arial")
    loaded_fonts = {family.casefold() for family in QFontDatabase.families()}
    if "jetbrains mono" not in loaded_fonts:
        QFont.insertSubstitution("JetBrains Mono", "Arial")
    app.setFont(QFont("Segoe UI", 10))

    api_client.companies = lambda: [{"id": "tenant-1", "company_name": "ASLAN TIC"}]
    api_client.server_status = lambda: {
        "cpu_percent": 23, "ram_percent": 51, "disk_percent": 30, "tenant_count": 1,
        "db_path": "C:/data/admin.db", "uptime": "4 days"
    }
    api_client.audit_logs = lambda tenant_id="", limit=200: [
        {"timestamp": "2026-10-14 08:00", "action": "BACKUP_CREATED", "company_name": "ASLAN TIC", "status": "OK"}
    ]
    api_client.backups = lambda tenant_id: [
        {"filename": "ASLAN_TIC_full_backup.db", "size_bytes": 2048}
    ]
    api_client.readonly_query = lambda _tenant, _sql: {
        "columns": ["id", "username", "role", "last_login", "disk_usage_mb"],
        "rows": [[101, "enginmamu22", "Super Admin", "2026-10-14 08:11", 0.82], [102, "aslan_teknik", "Teknisyen", "2026-10-14 07:45", 0.64], [104, "babali_operator", "Operator", "2026-10-13 18:20", 0.18]],
        "truncated": False,
    }
    page = DatabaseManagerPage()
    page.resize(1440, 1080)
    page.show()
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        app.processEvents()
        if not page._thread or not page._thread.isRunning():
            break
        page._thread.wait(50)
    app.processEvents()
    page._sql_input.setPlainText("SELECT id, username, role, last_login, disk_usage_mb\nFROM users\nWHERE status = 'active'\nORDER BY id ASC\nLIMIT 50;")
    page._run_btn.click()
    if page._thread:
        page._thread.wait(1000)
    app.processEvents()
    if page._table.rowCount() != 3 or page._table.columnCount() != 5:
        return 2
    if page._telemetry_table.rowCount() != 1 or page._platform_values[2].text() != "200 OK":
        return 6
    desktop = ROOT / "artifacts" / "admin_database_manager_desktop_offscreen.png"
    desktop.parent.mkdir(parents=True, exist_ok=True)
    if not page.grab().save(str(desktop), "PNG"):
        return 3

    page.resize(390, 844)
    app.processEvents()
    scroll = page.findChild(QScrollArea, "sqlScroll")
    if scroll.horizontalScrollBar().maximum() != 0:
        details = [(child.objectName(), child.width(), child.minimumSizeHint().width()) for child in scroll.widget().children() if hasattr(child, "minimumSizeHint")]
        raise AssertionError((scroll.horizontalScrollBar().maximum(), scroll.widget().width(), scroll.viewport().width(), page.width(), details))
    mobile = ROOT / "artifacts" / "admin_database_manager_mobile_offscreen.png"
    if not page.grab().save(str(mobile), "PNG"):
        return 5
    page.close()
    app.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
