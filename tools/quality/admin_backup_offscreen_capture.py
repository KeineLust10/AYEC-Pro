"""Capture the Admin backup page with offscreen PyQt and system fonts."""

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
from pages.backups import BackupsPage


def main() -> int:
    app = QApplication(sys.argv)
    available_fonts = load_system_fallback_fonts()
    if "segoe ui" not in available_fonts:
        QFont.insertSubstitution("Segoe UI", "Arial")
    QFont.insertSubstitution("Plus Jakarta Sans", "Segoe UI")
    QFont.insertSubstitution("JetBrains Mono", "Arial")
    app.setFont(QFont("Segoe UI", 10))

    api_client.companies = lambda: [
        {"id": "tenant-1", "company_name": "ASLAN TIC"},
    ]
    api_client.backups = lambda _tenant: [
        {"backup_id": 101, "index": 101, "filename": "ASLAN_TIC_auto_snapshot_20261014_0810.db", "source": "Server WAL Daemon", "created_at": "2026-10-14 08:10:14", "size_bytes": 1720320, "product_code": "teknik_servis", "hardware_id": "ASLAN-TERM-01", "sha256": "9a7b1402f631a65e"},
        {"backup_id": 102, "index": 102, "filename": "ASLAN_TIC_pre_update_backup_v2.0.0.db", "source": "Upgrade safety snapshot", "created_at": "2026-10-13 22:15:00", "size_bytes": 1679360, "product_code": "teknik_servis", "hardware_id": "ASLAN-TERM-01", "sha256": "4f3a8b91d29ca2e1"},
        {"backup_id": 103, "index": 103, "filename": "BABALI_TEK_daily_cron_snapshot.db", "source": "AWS S3 deep archive", "created_at": "2026-10-14 04:00:12", "size_bytes": 723456, "product_code": "otomotiv", "hardware_id": "BABALI-TERM-01", "sha256": "88c1a93270bbf008"},
        {"backup_id": 104, "index": 104, "filename": "BULUT_BILISIM_full_backup.db", "source": "Manual technician push", "created_at": "2026-10-12 18:30:45", "size_bytes": 743424, "product_code": "teknik_servis", "hardware_id": "BULUT-TERM-01"},
        {"backup_id": 105, "index": 105, "filename": "ISIKTAS_OTO_nightly_backup.db", "source": "Auto nightly cycle", "created_at": "2026-10-14 02:00:00", "size_bytes": 765432, "product_code": "otomotiv", "hardware_id": "ISIKTAS-TERM-01", "sha256": "1109bc43f0b7cd21"},
    ]

    page = BackupsPage()
    page.resize(1440, 1500)
    page.show()
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        app.processEvents()
        if not page._workers and page._table.rowCount() == 5:
            break
        for worker in tuple(page._workers):
            worker.wait(100)
        app.processEvents()
    app.processEvents()
    if page._table.rowCount() != 5 or page._metric_count.text() != "5":
        raise AssertionError(f"Backup rows or metric mismatch: {page._table.rowCount()}, {page._metric_count.text()}")
    if page._metric_size.text() != "4 / 5":
        return 7
    if page._restore_button.isEnabled():
        return 2
    page._restore_selected()
    if "onayi" not in page._status.text().casefold():
        return 8
    page._select_backup_row(0)
    page._restore_ack.setChecked(True)
    app.processEvents()
    if not page._restore_button.isEnabled():
        return 3
    page._restore_ack.setChecked(False)
    page._table.clearSelection()
    page._table.setCurrentCell(-1, -1)
    page._update_restore_selection()
    page.resize(1440, 1080)
    app.processEvents()
    desktop_path = ROOT / "artifacts" / "admin_backups_reference_desktop_offscreen.png"
    desktop_path.parent.mkdir(parents=True, exist_ok=True)
    if not page.grab().save(str(desktop_path), "PNG"):
        return 4

    page.resize(390, 844)
    app.processEvents()
    scroll = page.findChild(QScrollArea, "backupScroll")
    if scroll.horizontalScrollBar().maximum() != 0:
        return 9
    mobile_path = ROOT / "artifacts" / "admin_backups_reference_mobile_offscreen.png"
    if not page.grab().save(str(mobile_path), "PNG"):
        return 5
    page._search.setText("ASLAN-TERM-01")
    app.processEvents()
    visible = sum(not page._table.isRowHidden(row) for row in range(page._table.rowCount()))
    if visible != 2:
        return 6

    page.close()
    app.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
