"""Capture desktop and mobile Admin server settings with offscreen PyQt."""

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

import api_client
from pages.server_settings import ServerSettingsPage


def main() -> int:
    app = QApplication(sys.argv)
    fonts = load_system_fallback_fonts()
    if "segoe ui" not in fonts:
        QFont.insertSubstitution("Segoe UI", "Arial")
    QFont.insertSubstitution("JetBrains Mono", "Arial")
    app.setFont(QFont("Segoe UI", 9))

    api_client.server_status = lambda: {
        "cpu_percent": 38,
        "ram_percent": 64,
        "disk_percent": 30,
        "disk_usage": "30%",
        "version": "2.0.4",
        "uptime": "Veri yok",
        "db_path": "C:/ayec/data/tenant_registry.db",
        "tenant_count": 12,
        "server_time": "2026-10-14T08:15:00+00:00",
        "database_size_bytes": 1121976,
        "network_mbps": 9.6,
    }
    page = ServerSettingsPage()
    page.resize(1440, 1000)
    page.show()
    if not page._thread.wait(5000):
        return 2
    app.processEvents()
    if page._cpu_bar.value() != 38 or page._ram_bar.value() != 64 or page._disk_bar.value() != 30:
        return 3
    if page._cpu_lbl.text() != "38%" or page._ram_lbl.text() != "64%" or page._disk_lbl.text() != "30%":
        return 3
    if page._database_lbl.text() != "1.07 MB" or page._network_lbl.text() != "1.20 MB/s":
        return 3
    if page._cpu_state.text() != "Normal" or page._ram_state.text() != "Normal" or page._disk_state.text() != "Normal":
        return 3
    artifacts = ROOT / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    if not page.grab().save(str(artifacts / "admin_server_settings_pyqt_desktop.png"), "PNG"):
        return 4

    page.resize(390, 844)
    app.processEvents()
    if page._main_row.direction() != page._main_row.Direction.TopToBottom:
        return 5
    if page._scroll.horizontalScrollBar().maximum() != 0:
        return 6
    if not page.grab().save(str(artifacts / "admin_server_settings_pyqt_mobile.png"), "PNG"):
        return 7
    page.close()
    app.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
