from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["PYTHONIOENCODING"] = "utf-8"

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Admin_Konsol"))

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from admin_capture_fonts import load_system_fallback_fonts
from pages.error_logs import ErrorLogsPage


LOGS = [
    {
        "timestamp": "2026-10-14 09:20",
        "company": "ASLAN TIC",
        "machine": "WS-01",
        "level": "ERROR",
        "line": 42,
        "message": "Database is locked",
        "traceback": "sqlite3.OperationalError",
    },
    {
        "timestamp": "2026-10-14 09:21",
        "company": "Babali Servis",
        "machine": "WS-02",
        "level": "WARNING",
        "line": 18,
        "message": "Retry scheduled",
    },
]


def main() -> int:
    app = QApplication(sys.argv)
    available = load_system_fallback_fonts()
    if "segoe ui" not in available:
        QFont.insertSubstitution("Segoe UI", "Arial")
    app.setFont(QFont("Segoe UI", 9))
    ErrorLogsPage._load_companies = lambda _self: None
    ErrorLogsPage._load_logs = lambda _self: None
    page = ErrorLogsPage()
    page._populate(LOGS)
    page.show()
    artifacts = ROOT / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)

    page.resize(1440, 1000)
    app.processEvents()
    if page._metric_total.text() != "2" or len(page._metric_cards) != 4:
        return 2
    if not page.grab().save(str(artifacts / "admin_error_telemetry_pyqt_desktop.png"), "PNG"):
        return 3

    page.resize(390, 844)
    app.processEvents()
    if page._scroll.horizontalScrollBar().maximum() != 0:
        return 4
    if not page.grab().save(str(artifacts / "admin_error_telemetry_pyqt_mobile.png"), "PNG"):
        return 5
    if page.font().family().casefold() not in ("segoe ui", "arial"):
        return 6
    page.close()
    app.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
