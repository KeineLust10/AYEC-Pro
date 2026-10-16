from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["PYTHONIOENCODING"] = "utf-8"

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Admin_Konsol"))

from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication

from admin_capture_fonts import load_system_fallback_fonts
from pages.live_status import LiveStatusPage


COMPANIES = [
    {"id": "AYEC-TR-1001", "company_name": "ASLAN TIC", "sector": "ANA DUGUM (ROOT)", "location": "Gonen/Balikesir", "db_filename": "ayec_aslan.db", "user_id": 7, "ip_address": "192.168.1.108", "user_agent": "SuperAdmin +1 Operator", "last_seen": "Heartbeat: 1 sn once", "online": True, "active_users": 2, "ping_ms": 11, "display_ping_ms": 11, "version": "v2.0.1 (Pilot)", "uptime": "146 06S 22D", "socket_port": 52410, "db_size_mb": 1.07, "wal_frames": 48, "data_rate": 1.4, "unsynced_queue": 0},
    {"id": "AYEC-TR-1002", "company_name": "Babali Servis", "sector": "OTOMOTIV", "location": "Balikesir Merkez", "db_filename": "ayec_babali.db", "user_id": 8, "ip_address": "192.168.1.109", "user_agent": "Yoneticisi", "last_seen": "Heartbeat: 3 sn once", "online": True, "active_users": 1, "ping_ms": 14, "display_ping_ms": 14, "version": "v2.0.0 Stabil", "uptime": "v2.0.0", "socket_port": 49112, "db_size_mb": 0.69, "data_rate": 1.4, "unsynced_queue": 0},
    {"id": "AYEC-TR-1003", "company_name": "Bulut Bilisim Ltd.", "sector": "BILISIM", "location": "Bandirma", "db_filename": "ayec_bulut.db", "user_id": 9, "ip_address": "176.220.14.99", "user_agent": "Teknisyen", "last_seen": "Heartbeat: 8 sn once", "online": True, "active_users": 1, "ping_ms": 22, "display_ping_ms": 92, "version": "v1.9 (Eski)", "uptime": "v1.9", "socket_port": 38120, "db_size_mb": 0.71, "data_rate": 1.4, "unsynced_queue": 0},
    {"id": "AYEC-TR-1004", "company_name": "Isiktas Oto Servis", "sector": "SERVIS", "location": "Bandirma", "db_filename": "ayec_isiktas.db", "user_id": 10, "ip_address": "78.135.20.14", "user_agent": "Firma Sahibi", "last_seen": "Heartbeat: 2 sn once", "online": True, "active_users": 0, "ping_ms": 18, "display_ping_ms": 18, "version": "v2.0.0 Stabil", "uptime": "26 11S 45D", "socket_port": 50114, "db_size_mb": 0.73, "data_rate": 1.4, "unsynced_queue": 0},
]


def main() -> int:
    app = QApplication(sys.argv)
    available = load_system_fallback_fonts()
    if "segoe ui" not in available:
        QFont.insertSubstitution("Segoe UI", "Arial")
    app.setFont(QFont("Segoe UI", 9))
    LiveStatusPage._refresh = lambda _self: None
    page = LiveStatusPage()
    page._populate(COMPANIES)
    page.resize(1440, 1000)
    page.show()
    app.processEvents()
    if [widget.text() for widget in page._metric_widgets] != ["4 / 4 Online", "16 ms", "1.4 MB/s", "0 Paket"]:
        return 2
    if len(page._company_widgets) != 4 or page._latency_chart.values[-1] != 16:
        return 3
    artifacts = ROOT / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    if not page.grab().save(str(artifacts / "admin_live_status_pyqt_desktop.png"), "PNG"):
        return 4
    page.resize(390, 844)
    app.processEvents()
    if page._page_scroll.horizontalScrollBar().maximum() != 0:
        return 5
    if not page.grab().save(str(artifacts / "admin_live_status_pyqt_mobile.png"), "PNG"):
        return 6
    page.close()
    app.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
