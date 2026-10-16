"""Render the Admin_Konsol dashboard offscreen with stable UTF-8 font settings."""

from __future__ import annotations

import os
import sys
import time
import json
from pathlib import Path

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ.setdefault(
    "QTWEBENGINE_CHROMIUM_FLAGS",
    "--disable-gpu --disable-gpu-compositing --disable-features=VizDisplayCompositor",
)
os.environ.setdefault("QT_OPENGL", "software")

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "Admin_Konsol") not in sys.path:
    sys.path.insert(0, str(ROOT / "Admin_Konsol"))

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QFontDatabase, QFontInfo
from PyQt6.QtWidgets import QApplication, QLabel, QWidget

from admin_capture_fonts import load_system_fallback_fonts
from src.ui.components.modern_dialog import ModernDialog

import api_client
from main_window import MainWindow
from pages.dashboard import DashboardPage
from pages.live_status import LiveStatusPage
from pages.audit_logs import AuditLogsPage, _FetchAudit
from pages.companies import _FetchUsers
from pages.customer_360 import _Customer360Thread
from pages.database_manager import _RunSqlThread
from pages.limits import _FetchLimits


def main() -> int:
    app = QApplication(sys.argv)
    available_fonts = load_system_fallback_fonts()
    if "segoe ui" not in available_fonts:
        QFont.insertSubstitution("Segoe UI", "Arial")
    mono_font_path = ROOT / "assets" / "fonts" / "JetBrainsMono-Regular.ttf"
    if mono_font_path.is_file():
        QFontDatabase.addApplicationFont(str(mono_font_path))
    loaded_fonts = {family.casefold() for family in QFontDatabase.families()}
    if "plus jakarta sans" not in loaded_fonts:
        QFont.insertSubstitution("Plus Jakarta Sans", "Segoe UI")
    if "jetbrains mono" not in loaded_fonts:
        QFont.insertSubstitution("JetBrains Mono", "Arial")
    app.setFont(QFont("Segoe UI", 10))
    fixture = {
            "total_companies": 4,
            "active_companies": 4,
            "inactive_companies": 0,
            "online_users": 4,
            "logins_today": 18,
            "disk_usage": "30.3%",
            "backup_coverage": 4,
            "pending_commands": 0,
            "failed_commands": 0,
            "expiring_licenses": 0,
            "recent_logs": [
                {"time": "2026-10-14 08:08:12", "action": "License Order Approved", "company": "ASLAN T\u0130C", "status": "Tamamland\u0131", "operator": "Root Admin"},
                {"time": "2026-10-14 07:45:00", "action": "Otomatik Bulut Yedekleme", "company": "Babal\u0131 Servis", "status": "42.8 MB OK", "operator": "CRON / Daemon"},
                {"time": "2026-10-14 06:12:30", "action": "Lisans G\u00fcncellendi (PRO v2.0)", "company": "Bulut Bili\u015fim Ltd.", "status": "+365 G\u00fcn", "operator": "Root Admin"},
                {"time": "2026-10-13 22:15:19", "action": "Firmware Patch Sync #104", "company": "I\u015f\u0131kta\u015f Oto Servis", "status": "E\u015fitlendi", "operator": "Auto-Deploy"},
                {"time": "2026-10-13 19:40:02", "action": "License Order Created", "company": "ASLAN T\u0130C", "status": "Beklemede", "operator": "Bayi Portal\u0131"},
                {"time": "2026-10-13 14:10:44", "action": "SQL \u0130ndeksleme & Optimize", "company": "T\u00fcm Veritabanlar\u0131", "status": "0.42 ms", "operator": "PostgreSQL Worker"},
            ],
        }
    api_client.dashboard = lambda: fixture
    api_client.live_status = lambda: [
        {"id": "tenant-1", "display_id": "AYEC-TR-1001", "company_name": "ASLAN T\u0130C", "sector": "teknik_servis", "location": "G\u00f6nen/Bal\u0131kesir", "db_filename": "aslan.db", "db_path": "C:\\Web_Arayuzu\\data\\ayecpro.db", "db_size_mb": 1.07, "wal_frames": 48, "user_id": 7, "session_username": "Engin ASLAN", "session_role": "SuperAdmin", "ip_address": "192.168.1.108", "user_agent": "AYEC Pro Desktop", "dashboard_version": "v2.0.1 (Pilot)", "uptime_text": "146G 06S 22D", "socket_port": 52410, "ssl_enabled": True, "ping_ms": 11, "average_ping_ms": 16, "data_rate": 1.4, "unsynced_queue": 0, "online": True, "active_users": 2, "last_seen": "2 sn \u00f6nce", "is_platform_root": True},
        {"id": "tenant-2", "display_id": "AYEC-TR-1002", "company_name": "Babal\u0131 Servis", "sector": "otomotiv", "location": "Bal\u0131kesir Merkez", "db_filename": "babali.db", "db_size_mb": 0.69, "user_id": 8, "session_username": "Emirhan BABALI", "session_role": "Y\u00f6netici", "session_port": 49112, "socket_ip": "88.241.12.65", "sync_status": "Bulut E\u015fitlendi", "client_version": "v2.0.0 (Stabil)", "ping_ms": 14, "unsynced_queue": 0, "online": True, "active_users": 1, "last_seen": "5 sn \u00f6nce"},
        {"id": "tenant-3", "display_id": "AYEC-TR-1003", "company_name": "Bulut Bili\u015fim Ltd.", "sector": "bilisim", "location": "Band\u0131rma", "db_filename": "bulut.db", "db_size_mb": 0.71, "user_id": 9, "session_username": "Engin MAMU", "session_role": "Teknisyen", "session_port": 38120, "socket_ip": "176.220.14.99", "client_version": "v1.9 (Eski)", "ping_ms": 92, "unsynced_queue": 0, "pending_orders": 2, "sync_status": "Senkronizasyon Bekliyor", "online": True, "active_users": 1, "last_seen": "8 sn \u00f6nce"},
        {"id": "tenant-4", "display_id": "AYEC-TR-1004", "company_name": "I\u015f\u0131kta\u015f Oto Servis", "sector": "otomotiv", "location": "Band\u0131rma", "db_filename": "isiktas.db", "db_size_mb": 0.73, "user_id": 10, "session_username": "Hasan I\u015eIKTA\u015e", "session_role": "Firma Sahibi", "session_port": 50114, "socket_ip": "78.135.20.14", "client_version": "v2.0.0 (Stabil)", "uptime_text": "26G 11S 45D", "ping_ms": 18, "unsynced_queue": 0, "online": True, "active_users": 1, "last_seen": "Simdi"},
    ]
    api_client.license_orders = lambda status="", product_code="": [
        {"id": 1, "request_no": "REQ-001", "company_name": "ASLAN TIC", "requester_name": "Engin", "plan_label": "3 Yillik", "amount_try": 15990, "payment_reference": "PAY-1001", "license_code": "AYEC-CORE-001", "status": "payment_reported", "created_at": "2026-10-14 09:42"},
        {"id": 2, "request_no": "REQ-002", "company_name": "Babali Servis", "requester_name": "Bora", "plan_label": "Lifetime", "amount_try": 4500, "payment_reference": "PAY-1002", "license_code": "AYEC-CORE-002", "status": "active", "created_at": "2026-10-14 09:38"},
    ]
    api_client.licenses = lambda product_code="": [
        {"tenant_id": "tenant-1", "company_name": "ASLAN TIC LTD. STI.", "product_code": "teknik_servis", "license_type": "three_years", "license_code": "AYEC-TS-8841-K992-SEC", "license_start": "2026-10-14", "license_end": "2029-10-14", "license_updated_at": "2026-10-14", "status": "Aktif", "branch_name": "Ana Bayi", "city": "Istanbul"},
        {"tenant_id": "tenant-2", "company_name": "Babali Servis Teknoloji", "product_code": "otomotiv", "license_type": "Lifetime", "license_code": "AYEC-TS-3310-M104-SEC", "license_start": "2026-10-14", "license_end": "", "license_updated_at": "2026-10-14", "status": "Aktif", "branch_name": "Sube #1", "city": "Ankara"},
        {"tenant_id": "tenant-3", "company_name": "Bulut Bilisim & Donanim", "product_code": "teknik_servis", "license_type": "one_year_pro", "license_code": "AYEC-TS-9923-P008-SEC", "license_start": "2026-02-14", "license_end": "2027-02-14", "license_updated_at": "2026-10-14", "status": "Aktif", "branch_name": "Merkez Servis", "city": "Izmir"},
        {"tenant_id": "tenant-4", "company_name": "Isiktas Oto Elektronik Servis", "product_code": "teknik_servis", "license_type": "pilot", "license_code": "AYEC-TS-1200-Z441-SEC", "license_start": "2026-10-01", "license_end": "2026-10-30", "license_updated_at": "2026-10-14", "status": "Aktif", "branch_name": "Servis Terminali", "city": "Bursa"},
    ]
    api_client.provision_invites = lambda: {
        "invites": [
            {
                "id": index,
                "invite_code": f"AYEC-DEMO-{index:03d}",
                "expires_at": "2028-10-14T00:00:00+00:00",
                "max_uses": 1,
                "use_count": 0 if index <= 12 or index > 46 else 1,
                "revoked_at": "2026-10-14T00:00:00+00:00" if index > 46 else None,
            }
            for index in range(1, 49)
        ]
    }
    companies = [
        {"id": "tenant-1", "company_name": "ASLAN TIC", "active": 1, "online": True, "contact_name": "Engin ASLAN", "phone": "0534 878 10 47", "email": "enginmamu22@gmail.com", "sector": "teknik_servis", "license_type": "3 Yillik Kurumsal", "license_end": "2029-10-07", "last_login": "2026-10-14", "created_at": "2024-05-01"},
        {"id": "tenant-2", "company_name": "Babali", "active": 1, "online": True, "contact_name": "Emirhan BABALI", "phone": "0535 535 35 35", "email": "babalieemirhan048@gmail.com", "sector": "Otomotiv", "license_type": "Lifetime Pro"},
        {"id": "tenant-3", "company_name": "Bulut Bilisim", "active": 1, "online": True, "contact_name": "Engin MAMU", "phone": "0534 878 10 47", "email": "enginmamu1@gmail.com", "sector": "IT & Servis", "license_type": "Lifetime Core"},
        {"id": "tenant-4", "company_name": "Isiktas Oto Servis", "active": 1, "online": True, "contact_name": "Hasan ISIKTAS", "phone": "0534 123 45 67", "email": "hasanisiktas@icloud.com", "sector": "Mekanik Oto", "license_type": "Lifetime Pro"},
    ]
    api_client.companies = lambda *args, **kwargs: companies
    api_client.error_logs = lambda tenant_id="", limit=200: [
        {"timestamp": "2026-10-14 08:05:12", "company": "ASLAN TIC", "machine": "DESKTOP-ENGIN-PC", "level": "ERROR", "line": 142, "file": "db_worker.py", "message": "database is locked (5000ms)", "traceback": "sqlite3.OperationalError: database is locked", "os": "Windows 11 Pro 64-bit", "python_version": "Python 3.11.4 / SQLite 3.45.1 WAL", "memory": "4.1 GB / 8.0 GB", "worker": "WorkerThread-04", "diagnosis": "Concurrent service writes collided with the WAL checkpoint; retry completed after 142ms."},
        {"timestamp": "2026-10-14 07:58:39", "company": "Bulut Bilisim", "machine": "TERMINAL-02-ATOLYE", "level": "WARNING", "line": 88, "file": "wa_client.py", "message": "Meta Cloud API response timeout", "traceback": "WhatsAppApiTimeout: request exceeded 20 seconds"},
        {"timestamp": "2026-10-14 07:31:04", "company": "Babali Teknik", "machine": "KASA-DESK-01", "level": "INFO", "line": 214, "file": "thermal_escpos.py", "message": "Windows Spooler RPC endpoint recovered", "traceback": "PrinterSpoolerError: transient retry recovered"},
        {"timestamp": "2026-10-14 06:45:11", "company": "Isiktas Elektronik", "machine": "LAB-ANALYST-PC", "level": "INFO", "line": 53, "file": "heartbeat.py", "message": "Roundtrip latency degraded", "traceback": "TelemetryHeartbeatSlow: ping 142ms"},
        {"timestamp": "2026-10-14 05:19:00", "company": "ASLAN TIC", "machine": "DESKTOP-ENGIN-PC", "level": "ERROR", "line": 391, "file": "gib_signer.py", "message": "SmartCard token removed", "traceback": "EFaturaCryptoSignFail: certificate token unavailable"},
        {"timestamp": "2026-10-14 04:48:22", "company": "Babali Servis", "machine": "WS-02", "level": "WARNING", "line": 61, "file": "update_agent.py", "message": "OTA package retry scheduled", "traceback": "UpdateDeliverySlow: retry count 1"},
    ]
    api_client.server_status = lambda: {
        "cpu_percent": 23,
        "ram_percent": 51,
        "disk_percent": 30,
        "disk_usage": "30%",
        "version": "2.4.0",
        "uptime": "4 days",
        "db_path": "C:/data/admin.db",
        "tenant_count": 2,
    }
    api_client.backups = lambda tenant_id: [
        {"filename": "ASLAN_TIC_full_backup.db", "source": "client", "modified": "2026-10-14 08:00", "size_bytes": 2048, "hardware_id": "WS-01", "product_code": "teknik_servis", "sha256": "a2c4e6f80123456789abcdef01234567"},
        {"filename": "ASLAN_TIC_daily_snapshot.db", "source": "server", "modified": "2026-10-14 06:00", "size_bytes": 1150, "hardware_id": "WS-02", "product_code": "teknik_servis", "sha256": "b3d5f709123456789abcdef012345678"},
        {"filename": "BABALI_TEK_daily_cron_snapshot.db", "source": "server", "modified": "2026-10-14 04:00", "size_bytes": 706560, "hardware_id": "WS-03", "product_code": "teknik_servis", "sha256": "88c1a932bb12ca340989f554011cc098"},
        {"filename": "BULUT_BILISIM_full_backup.db", "source": "server", "modified": "2026-10-14 03:00", "size_bytes": 765460, "hardware_id": "WS-04", "product_code": "teknik_servis", "sha256": "e3b0c44298fc1c149afbf4c8996fb924"},
        {"filename": "ISIKTAS_OTO_nightly_backup.db", "source": "server", "modified": "2026-10-14 02:00", "size_bytes": 765460, "hardware_id": "WS-05", "product_code": "teknik_servis", "sha256": "1109bc43a0889fce224a56c7104b901a"},
    ]
    api_client.audit_logs = lambda tenant_id="", limit=200: [
        {"timestamp": "2026-10-14 08:11:02", "action": "AUTH_OK", "company_name": "ASLAN TIC", "severity": "INFO", "description": "Administrator sign-in accepted.", "status": "OK"},
        {"timestamp": "2026-10-14 08:10:43", "action": "BACKUP_CREATED", "company_name": "SYSTEM_CORE", "severity": "AUDIT", "description": "Automatic backup created.", "status": "OK"},
        {"timestamp": "2026-10-14 08:09:51", "action": "SYNC_OK", "company_name": "Babali Servis", "severity": "TELEMETRY", "description": "Offline queue synchronized.", "status": "OK"},
        {"timestamp": "2026-10-14 08:05:12", "action": "QUOTA_CHECK", "company_name": "Isiktas Oto Servis", "severity": "METRIC", "description": "Usage is within limits.", "status": "OK"},
    ]
    api_client.readonly_query = lambda tenant_id, sql: {
        "columns": ["ID", "USERNAME", "ROLE", "LAST_LOGIN", "DISK_USAGE_MB"],
        "rows": [
            [101, "enginmamu22", "Super Admin", "2026-10-14 08:11", "0.82"],
            [102, "aslan_teknik", "Teknisyen", "2026-10-14 07:45", "0.64"],
            [104, "babali_operator", "Operator", "2026-10-13 18:20", "0.18"],
        ],
        "truncated": False,
    }
    _RunSqlThread.run = lambda worker: worker.done.emit(api_client.readonly_query(worker._tid, worker._sql))
    api_client.customer_360 = lambda tenant_id: {
        "company": {"id": tenant_id, "company_name": "ASLAN TIC", "contact_name": "Engin ASLAN", "phone": "05348781047", "email": "engimmamu22@gmail.com", "sector": "teknik_servis", "license_type": "3 Yillik Kurumsal", "company_address": "Gonen / Balikesir", "license_end": "2029-10-07", "last_login": "2026-10-14 05:09:33"},
        "summary": {"user_count": 2, "user_limit": "Sinirsiz", "backup_count": 1, "error_count": 0, "audit_count": 8, "online": True},
        "licenses": [{"license_type": "3 Yillik Kurumsal", "status": "active", "license_key": "AYEC-591309724851525554DE017E33B0DA6D42EC98B7E58DDC910"}],
        "backups": [{"filename": "latest.db"}],
        "live_status": {"hardware_id": "WS-01", "ping_ms": 18},
        "error_logs": [],
        "audit_logs": [{"action": "admin_license_updated"}],
        "users": [
            {"id": 1, "full_name": "Engin ASLAN", "username": "engimmamu22", "email": "engimmamu22@gmail.com", "phone": "05348781047", "role": "user", "active": 1, "last_login": "-"},
            {"id": 2, "full_name": "AYEC Platform Owner", "username": "ayecpro", "email": "ayecpro@gmail.com", "phone": "-", "role": "admin", "active": 1, "last_login": "2026-10-14 05:09:33"},
        ],
    }
    _Customer360Thread.run = lambda worker: worker.loaded.emit(api_client.customer_360(worker._tenant_id))
    _FetchLimits.run = lambda worker: worker.done.emit([
        {"tenant_id": "ASLAN-1001", "company_name": "ASLAN TIC", "license_code": "AYEC-1001", "package_name": "Kurumsal Paket", "db_size_mb": 1.64, "db_limit_gb": 10, "users_count": 2, "users_limit": 10, "devices_count": 20, "devices_limit": 100, "services_count": 248, "services_limit": 1000},
        {"tenant_id": "BABALI-1002", "company_name": "Babali Servis", "license_code": "AYEC-1002", "package_name": "Pro Paket", "db_size_mb": 0.69, "db_limit_gb": 5, "users_count": 2, "users_limit": 10, "devices_count": 0, "devices_limit": 100, "services_count": 45, "services_limit": 1000},
        {"tenant_id": "BULUT-1003", "company_name": "Bulut Bilisim Ltd.", "license_code": "AYEC-1003", "package_name": "Standart Paket", "db_size_mb": 0.71, "db_limit_gb": 5, "users_count": 2, "users_limit": 10, "devices_count": 2, "devices_limit": 100, "services_count": 86, "services_limit": 1000},
        {"tenant_id": "ISIKTAS-1004", "company_name": "Isiktas Oto Servis", "license_code": "AYEC-1004", "package_name": "Pro Paket", "db_size_mb": 0.73, "db_limit_gb": 5, "users_count": 2, "users_limit": 10, "devices_count": 2, "devices_limit": 100, "services_count": 33, "services_limit": 1000},
    ])
    _FetchAudit.run = lambda worker: worker.done.emit([
        {"id": "AUD-9942", "created_at": "2026-10-14 08:11:02", "action": "admin_password_reset_link", "company_name": "ASLAN TIC", "actor_username": "enginy", "ip_address": "192.168.1.108", "record_hash": "e3b0c44298fc1c149afbf4c8996fb924", "previous_hash": "9a7b1402", "detail": {"description": "A temporary password reset link was created for ASLAN TIC.", "before": {"user.password_hash": "[redacted]"}, "after": {"user.password_hash": "[temporary hash]"}, "user_agent": "AYEC Pro Desktop v2.0.1", "encryption": "TLS 1.3 / AES-GCM-256"}},
        {"id": "AUD-9941", "created_at": "2026-10-14 08:10:43", "action": "admin_backup_created", "company_name": "System (Master)", "actor_username": "AYEC Core Root", "ip_address": "127.0.0.1", "record_hash": "9a7b1402", "detail": {"description": "Automated database backup completed.", "reason": "Scheduled backup"}},
        {"id": "AUD-9940", "created_at": "2026-10-14 08:08:12", "action": "admin_license_updated", "company_name": "ASLAN TIC", "actor_username": "Root Admin", "ip_address": "192.168.1.108", "record_hash": "4f3a8b91", "detail": {"description": "License request approved for the three-year plan.", "before": {"plan": "standard"}, "after": {"plan": "three_year"}, "amount": 15990}},
        {"id": "AUD-9939", "created_at": "2026-10-14 07:45:00", "action": "admin_backup_sync", "company_name": "Babali Servis", "actor_username": "CRON Daemon", "ip_address": "10.0.4.12", "record_hash": "88c1a932", "detail": {"description": "Cloud backup synchronized to the S3 bucket.", "source": "AWS Direct Connect"}},
        {"id": "AUD-9938", "created_at": "2026-10-13 22:15:19", "action": "admin_update_deployed", "company_name": "Isiktas Oto Servis", "actor_username": "Auto-Deploy", "ip_address": "176.240.11.90", "record_hash": "1109bc43", "detail": {"description": "OTA firmware deployment completed for 12 devices."}},
        {"id": "AUD-9937", "created_at": "2026-10-13 14:10:44", "action": "admin_readonly_query", "company_name": "Tum Firmalar", "actor_username": "Root Admin", "ip_address": "192.168.1.108", "record_hash": "77a0029c", "detail": {"description": "Read-only SQL query completed.", "query": "SELECT users", "row_count": 24}},
    ])
    _FetchUsers.run = lambda worker: worker.done.emit(worker._tid, [
        {"id": 7, "username": "enginy", "full_name": "Engin Yilmaz", "email": "admin@aslan.example", "phone": "555-0101", "role": "tenant_admin", "active": 1, "last_login": "2026-10-14"},
    ])
    window = MainWindow()
    if any(QFontInfo(page.font()).family() != "Plus Jakarta Sans" for page in window._pages.values()):
        return 111
    window.resize(1440, 1000)
    window.show()
    app.processEvents()
    page = window._pages["dashboard"]
    if window._top_bar.height() != 56 or window._top_bar.property("referenceStyle") != "standard":
        return 113
    if QFontInfo(page.font()).family() != "Plus Jakarta Sans":
        return 110
    if page._thread:
        page._thread.wait(3000)
    if window._header_status_thread:
        window._header_status_thread.wait(3000)
    app.processEvents()
    if [value.text() for _bar, value in window._header_metric_widgets.values()] != ["23%", "51%", "30%"]:
        return 9
    # Seed deterministic latency history for the visual reference capture.
    captured_at = time.time()
    latency_values = (8.0, 11.0, 10.0, 15.0, 13.0, 14.0, 12.0, 16.0, 13.0, 12.0)
    page._latency_samples = [
        (captured_at - (len(latency_values) - index - 1) * 330, value)
        for index, value in enumerate(latency_values)
    ]
    page._latency_chart.set_samples(page._latency_samples)
    page._latency_average.setText("Ortalama: 12.4 ms")
    output = ROOT / "artifacts" / "admin_dashboard_offscreen.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    saved = window.grab().save(str(output), "PNG")
    if not saved:
        return 101
    if page._log_table.rowCount() != 6:
        return 102
    mobile_page = DashboardPage()
    if mobile_page._thread:
        mobile_page._thread.wait(3000)
    app.processEvents()
    mobile_page.resize(390, 844)
    mobile_page.show()
    app.processEvents()
    mobile_path = ROOT / "artifacts" / "admin_dashboard_mobile_offscreen.png"
    if mobile_page._primary_count != 1 or mobile_page._secondary_count != 1:
        return 103
    for group in (mobile_page._metric_cards[:4], mobile_page._metric_cards[4:]):
        for previous, current in zip(group, group[1:]):
            if previous.geometry().bottom() >= current.geometry().top():
                return 109
    if mobile_page._log_table.horizontalScrollBar().maximum() <= 0:
        return 104
    if mobile_page._log_table.verticalScrollBar().maximum() != 0:
        return 108
    if mobile_page._dashboard_scroll.horizontalScrollBar().maximum() != 0:
        return 105
    if not mobile_page.grab().save(str(mobile_path), "PNG"):
        return 106
    mobile_page._dashboard_scroll.ensureWidgetVisible(mobile_page._log_panel, 0, 0)
    app.processEvents()
    mobile_logs_path = ROOT / "artifacts" / "admin_dashboard_mobile_logs_offscreen.png"
    if not mobile_page.grab().save(str(mobile_logs_path), "PNG"):
        return 107
    mobile_page.close()
    app.processEvents()
    page._search.setText("ASLAN")
    app.processEvents()
    visible = sum(not page._log_table.isRowHidden(row) for row in range(page._log_table.rowCount()))
    if visible != 2:
        return 2
    page.navigate_requested.emit("companies")
    app.processEvents()
    if window._current_page != "companies":
        return 3
    company_page = window._pages["companies"]
    if company_page._thread:
        company_page._thread.wait(3000)
    app.processEvents()
    overview_deadline = time.monotonic() + 10
    while company_page._overview_workers and time.monotonic() < overview_deadline:
        for worker in tuple(company_page._overview_workers):
            worker.wait(1000)
        app.processEvents()
    if company_page._company_group.buttons():
        company_page._company_group.buttons()[0].click()
    if company_page._thread:
        company_page._thread.wait(3000)
    app.processEvents()
    company_image = ROOT / "artifacts" / "admin_company_management_offscreen.png"
    if not window.grab().save(str(company_image)) or company_page._user_table.rowCount() != 1:
        return 19
    window._navigate("audit_logs")
    app.processEvents()
    audit_page = window._pages["audit_logs"]
    audit_deadline = time.monotonic() + 10
    while audit_page._workers and time.monotonic() < audit_deadline:
        for worker in tuple(audit_page._workers):
            worker.wait(1000)
        app.processEvents()
    audit_image = ROOT / "artifacts" / "admin_audit_monitoring_offscreen.png"
    window.resize(1440, 1000)
    app.processEvents()
    if not window.grab().save(str(audit_image), "PNG") or audit_page._table.rowCount() != 6:
        return 20
    load_companies = AuditLogsPage._load_companies
    AuditLogsPage._load_companies = lambda _self: None
    audit_mobile = AuditLogsPage()
    AuditLogsPage._load_companies = load_companies
    audit_mobile.setStyleSheet(window.styleSheet() + audit_mobile.styleSheet())
    audit_mobile._populate_logs(audit_page._logs)
    audit_mobile._company.blockSignals(True)
    audit_mobile._company.addItem("T\u00fcm firmalar", "")
    audit_mobile._company.blockSignals(False)
    audit_mobile.resize(390, 844)
    audit_mobile.show()
    app.processEvents()
    audit_mobile_image = ROOT / "artifacts" / "admin_audit_mobile_offscreen.png"
    audit_mobile_saved = audit_mobile.grab().save(str(audit_mobile_image), "PNG")
    audit_mobile_checks = {
        "vertical_split": audit_mobile._audit_splitter.orientation() == Qt.Orientation.Vertical,
        "no_horizontal_overflow": audit_mobile._page_scroll.horizontalScrollBar().maximum() == 0,
        "two_metric_columns": audit_mobile._metrics_grid.itemAtPosition(0, 2) is None,
        "capture_saved": audit_mobile_saved,
    }
    if not all(audit_mobile_checks.values()):
        scroll = audit_mobile._page_scroll
        page_content = scroll.widget()
        overflowing = []
        for child in page_content.findChildren(QWidget):
            position = child.mapTo(page_content, child.rect().topLeft())
            if position.x() + child.width() > page_content.width():
                overflowing.append({"name": child.objectName(), "type": type(child).__name__, "x": position.x(), "width": child.width(), "minimum": child.minimumWidth(), "minimum_hint": child.minimumSizeHint().width(), "size_hint": child.sizeHint().width()})
        print(json.dumps({"screen": "audit_mobile", "checks": audit_mobile_checks, "viewport": scroll.viewport().width(), "content": page_content.width(), "scroll_max": scroll.horizontalScrollBar().maximum(), "overflowing": overflowing[:8]}))
        return 22
    audit_mobile.close()
    window.resize(1440, 1000)
    app.processEvents()
    audit_page._search.setText("ASLAN")
    if audit_page._table.isRowHidden(0) or not audit_page._table.isRowHidden(1):
        return 21
    window._navigate("live_status")
    app.processEvents()
    status_page = window._pages["live_status"]
    if status_page._thread:
        status_page._thread.wait(3000)
    app.processEvents()
    status_image = ROOT / "artifacts" / "admin_live_status_offscreen.png"
    if not window.grab().save(str(status_image), "PNG"):
        return 4
    status_page._search.setText("ASLAN")
    app.processEvents()
    visible_cards = sum(card.isVisible() for _, card in status_page._company_widgets)
    if visible_cards != 1:
        return 5
    mobile_status = LiveStatusPage()
    mobile_status._timer.stop()
    if mobile_status._thread and mobile_status._thread.isRunning():
        mobile_status._thread.wait(3000)
    mobile_status._populate(api_client.live_status())
    mobile_status.resize(390, 844)
    mobile_status.show()
    app.processEvents()
    mobile_status_image = ROOT / "artifacts" / "admin_live_status_mobile_offscreen.png"
    if mobile_status._page_scroll.horizontalScrollBar().maximum() != 0:
        content = mobile_status._page_scroll.widget()
        overflow = []
        for child in content.findChildren(QWidget):
            position = child.mapTo(content, child.rect().topLeft())
            if position.x() + child.width() > content.width():
                overflow.append({"name": child.objectName(), "type": type(child).__name__, "x": position.x(), "width": child.width(), "minimum": child.minimumSizeHint().width()})
        card = mobile_status._company_widgets[0][1] if mobile_status._company_widgets else None
        telemetry = getattr(card, "_telemetry_layout", None)
        print(json.dumps({"screen": "live_status_mobile", "content": content.width(), "viewport": mobile_status._page_scroll.viewport().width(), "inner": mobile_status._inner.width(), "inner_hint": mobile_status._inner.sizeHint().width(), "grid_hint": mobile_status._grid_lay.sizeHint().width(), "scroll_max": mobile_status._page_scroll.horizontalScrollBar().maximum(), "card": {"width": card.width(), "hint": card.sizeHint().width(), "min_hint": card.minimumSizeHint().width(), "telemetry_hint": telemetry.sizeHint().width() if telemetry else None, "telemetry_min": telemetry.minimumSize().width() if telemetry else None, "columns": [telemetry.columnMinimumWidth(c) for c in range(4)] if telemetry else []} if card else None, "overflow": overflow[:8]}))
        return 25
    if any(card.width() > mobile_status._page_scroll.viewport().width() for _, card in mobile_status._company_widgets):
        return 26
    if not mobile_status.grab().save(str(mobile_status_image), "PNG"):
        return 27
    app.processEvents()
    mobile_status._page_scroll.verticalScrollBar().setValue(700)
    app.processEvents()
    mobile_cards_image = ROOT / "artifacts" / "admin_live_status_mobile_cards_offscreen.png"
    if not mobile_status.grab().save(str(mobile_cards_image), "PNG"):
        return 28
    mobile_status.close()
    app.processEvents()
    window._navigate("license_requests")
    app.processEvents()
    if window._top_bar.height() != 48 or window._top_bar.property("referenceStyle") != "license":
        return 114
    license_page = window._pages["license_requests"]
    if license_page.worker:
        license_page.worker.wait(3000)
    if license_page.license_worker:
        license_page.license_worker.wait(3000)
    if license_page.invite_worker:
        license_page.invite_worker.wait(3000)
    app.processEvents()
    inventory_width = sum(
        license_page.inventory_table.columnWidth(column)
        for column in range(license_page.inventory_table.columnCount())
    )
    if abs(inventory_width - license_page.inventory_table.viewport().width()) > 2:
        return 24
    license_image = ROOT / "artifacts" / "admin_license_requests_offscreen.png"
    if not window.grab().save(str(license_image), "PNG") or license_page.table.rowCount() != 2 or license_page.inventory_table.rowCount() != 4:
        return 6
    license_page.search_field.setText("ASLAN")
    app.processEvents()
    if sum(not license_page.table.isRowHidden(row) for row in range(license_page.table.rowCount())) != 1:
        return 7
    window._navigate("updates")
    app.processEvents()
    update_page = window._pages["updates"]
    for worker in tuple(update_page._workers):
        worker.wait(3000)
    app.processEvents()
    update_image = ROOT / "artifacts" / "admin_updates_offscreen.png"
    if not window.grab().save(str(update_image), "PNG") or update_page._companies.rowCount() != 4:
        return 8
    update_page._company_search.setText("ASLAN")
    update_page._set_all_checks(Qt.CheckState.Checked)
    if update_page._selected_targets() != ["tenant-1"]:
        return 9
    mobile_update = type(update_page)()
    mobile_update.resize(390, 844)
    mobile_update.show()
    for worker in tuple(mobile_update._workers):
        worker.wait(3000)
    app.processEvents()
    if mobile_update._content_grid.columnCount() != 1 or mobile_update._company_search.width() > mobile_update.width():
        return 107
    if mobile_update._companies.horizontalScrollBar().maximum() > 0:
        return 108
    mobile_update_image = ROOT / "artifacts" / "admin_updates_mobile_offscreen.png"
    if not mobile_update.grab().save(str(mobile_update_image), "PNG"):
        return 109
    mobile_update.close()
    app.processEvents()
    window._navigate("error_logs")
    app.processEvents()
    error_page = window._pages["error_logs"]
    for worker in tuple(error_page._threads):
        worker.wait(3000)
    app.processEvents()
    if error_page._splitter.orientation() != Qt.Orientation.Vertical:
        return 28
    error_page._show_detail(0, 0)
    error_image = ROOT / "artifacts" / "admin_error_telemetry_offscreen.png"
    if not window.grab().save(str(error_image), "PNG") or error_page._table.rowCount() != 6:
        return 10
    error_content_image = ROOT / "artifacts" / "admin_error_telemetry_content_offscreen.png"
    if not error_page._content.grab().save(str(error_content_image), "PNG"):
        return 29
    error_page._search.setText("ASLAN")
    if sum(not error_page._table.isRowHidden(row) for row in range(6)) != 2:
        return 11
    mobile_error = type(error_page)()
    for worker in tuple(mobile_error._threads):
        worker.wait(3000)
    app.processEvents()
    for worker in tuple(mobile_error._threads):
        worker.wait(3000)
    app.processEvents()
    mobile_error._set_detail(mobile_error._logs[0])
    mobile_error.setStyleSheet(window.styleSheet() + mobile_error.styleSheet())
    mobile_error.resize(390, 844)
    mobile_error.show()
    app.processEvents()
    mobile_error_image = ROOT / "artifacts" / "admin_error_telemetry_mobile_offscreen.png"
    if (
        not mobile_error.grab().save(str(mobile_error_image), "PNG")
        or mobile_error._result_stack.currentWidget() is not mobile_error._mobile_logs
        or mobile_error._splitter.orientation() != Qt.Orientation.Vertical
        or mobile_error._scroll.horizontalScrollBar().maximum() != 0
        or len(mobile_error._log_cards) != 6
        or mobile_error._root_layout.contentsMargins().left() != 12
    ):
        return 27
    mobile_error.close()
    app.processEvents()
    window._navigate("notifications")
    notification_page = window._pages["notifications"]
    deadline = time.monotonic() + 20
    while not notification_page._ready and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.02)
    if not notification_page._ready:
        return 12
    if notification_page._company_thread:
        notification_page._company_thread.wait(3000)
    app.processEvents()
    bridge_ready = []
    notification_page._view.page().runJavaScript("window.notifyReady===true", bridge_ready.append)
    deadline = time.monotonic() + 8
    while (not bridge_ready or not bridge_ready[0]) and time.monotonic() < deadline:
        bridge_ready.clear()
        app.processEvents()
        notification_page._view.page().runJavaScript("window.notifyReady===true", bridge_ready.append)
        time.sleep(0.05)
    notification_dom = []
    notification_page._view.page().runJavaScript(
        "JSON.stringify({text:document.body?.innerText||'',bridge:window.notifyReady===true,firms:document.querySelectorAll('.firm-checkbox').length,companyIds:Array.from(document.querySelectorAll('.firm-checkbox')).map(x=>x.dataset.id),icons:Array.from(document.querySelectorAll('.material-symbols-outlined')).map(x=>x.textContent.trim())})",
        notification_dom.append,
    )
    deadline = time.monotonic() + 3
    while not notification_dom and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    if not notification_dom:
        return 16
    notification_state = json.loads(notification_dom[0])
    (ROOT / "artifacts" / "admin_notification_dom_state.json").write_text(
        json.dumps(notification_state, ensure_ascii=True, indent=2), encoding="utf-8"
    )
    if "Merkezi Bildirim" not in notification_state["text"]:
        return 16
    if not notification_state["bridge"]:
        return 18
    if notification_state["firms"] != 4 or notification_state["companyIds"] != ["tenant-1", "tenant-2", "tenant-3", "tenant-4"]:
        return 17
    time.sleep(0.15)
    app.processEvents()
    notification_image = ROOT / "artifacts" / "admin_notifications_offscreen.png"
    if not window.grab().save(str(notification_image), "PNG"):
        return 12
    notification_page._view.grab().save(
        str(ROOT / "artifacts" / "admin_notifications_webview_offscreen.png"), "PNG"
    )
    preview_result = []
    notification_page._view.page().runJavaScript(
        "document.getElementById('push-title').value='Maintenance window';"
        "document.getElementById('push-title').dispatchEvent(new Event('input'));"
        "document.getElementById('push-body').value='Update the service before 18:00.';"
        "document.getElementById('push-body').dispatchEvent(new Event('input'));"
        "document.getElementById('preview-title-text').textContent",
        preview_result.append,
    )
    deadline = time.monotonic() + 3
    while not preview_result and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    if not preview_result or preview_result[0] != "Maintenance window":
        return 13
    window._navigate("server_settings")
    app.processEvents()
    server_page = window._pages["server_settings"]
    if server_page._thread:
        server_page._thread.wait(3000)
    app.processEvents()
    server_image = ROOT / "artifacts" / "admin_server_settings_offscreen.png"
    if not window.grab().save(str(server_image), "PNG"):
        return 14
    if server_page._cpu_bar.value() != 23 or server_page._srv_version.text() != "2.4.0":
        return 15
    window._navigate("backups")
    app.processEvents()
    backup_page = window._pages["backups"]
    backup_deadline = time.monotonic() + 10
    while backup_page._workers and time.monotonic() < backup_deadline:
        for worker in tuple(backup_page._workers):
            worker.wait(1000)
        app.processEvents()
    backup_image = ROOT / "artifacts" / "admin_backups_offscreen.png"
    if not window.grab().save(str(backup_image), "PNG") or backup_page._table.rowCount() != 5:
        return 16
    backup_page._search.setText("BULUT_BILISIM")
    if sum(not backup_page._table.isRowHidden(row) for row in range(5)) != 1:
        return 17
    window._navigate("limits")
    app.processEvents()
    limit_page = window._pages["limits"]
    if limit_page._thread:
        limit_page._thread.wait(3000)
    app.processEvents()
    limit_image = ROOT / "artifacts" / "admin_limits_offscreen.png"
    if not window.grab().save(str(limit_image), "PNG") or limit_page._table.rowCount() != 4:
        return 18
    window._navigate("database_manager")
    app.processEvents()
    sql_page = window._pages["database_manager"]
    if sql_page._thread:
        sql_page._thread.wait(3000)
    app.processEvents()
    sql_page._sql_input.setPlainText("SELECT id, username, role, last_login, disk_usage_mb\nFROM users\nWHERE status = 'active'\nORDER BY id ASC\nLIMIT 50;")
    sql_page._run_query()
    if sql_page._thread:
        sql_page._thread.wait(3000)
    app.processEvents()
    sql_image = ROOT / "artifacts" / "admin_sql_diagnostics_offscreen.png"
    sql_grab = window.grab()
    sql_saved = sql_grab.save(str(sql_image), "PNG")
    if not sql_saved:
        print(json.dumps({"capture": "database_manager", "pixmap_null": sql_grab.isNull(), "pixmap_size": [sql_grab.width(), sql_grab.height()]}))
        return 22
    if sql_page._table.rowCount() != 3 or sql_page._table.columnCount() != 5:
        raise AssertionError(f"SQL rows={sql_page._table.rowCount()} columns={sql_page._table.columnCount()}")
    if sql_page._table.item(0, 0).text() != "101" or sql_page._table.isRowHidden(0):
        raise AssertionError(
            f"SQL first result={sql_page._table.item(0, 0).text()} hidden={sql_page._table.isRowHidden(0)}"
        )
    rendered_results = [
        [sql_page._table.item(row, column).text() if sql_page._table.item(row, column) else None
         for column in range(sql_page._table.columnCount())]
        for row in range(sql_page._table.rowCount())
    ]
    if any(not all(row) for row in rendered_results) or [row[0] for row in rendered_results] != ["101", "102", "104"]:
        raise AssertionError(f"SQL result rows are incomplete: {rendered_results}")
    if sql_page._table.verticalScrollBar().value() != 0:
        raise AssertionError(f"SQL result scroll={sql_page._table.verticalScrollBar().value()}")
    if not sql_page._table.grab().save(str(ROOT / "artifacts" / "admin_sql_results_table_offscreen.png"), "PNG"):
        raise AssertionError("SQL result table offscreen capture failed")
    if sql_page._telemetry_table.rowCount() != 4 or sql_page._backup_table.rowCount() != 2:
        raise AssertionError(
            f"SQL telemetry={sql_page._telemetry_table.rowCount()} backups={sql_page._backup_table.rowCount()}"
        )
    mobile_sql = type(sql_page)()
    if mobile_sql._thread:
        mobile_sql._thread.wait(3000)
    mobile_sql.resize(390, 844)
    mobile_sql.show()
    mobile_sql._sql_input.setPlainText("SELECT id, username, role, last_login, disk_usage_mb\nFROM users\nWHERE status = 'active'\nORDER BY id ASC\nLIMIT 50;")
    mobile_sql._show_results(api_client.readonly_query("tenant-1", mobile_sql._sql_input.toPlainText()))
    app.processEvents()
    if any(mobile_sql._status_lbl.geometry().intersects(button.geometry()) for button in mobile_sql._action_buttons):
        return 25
    if mobile_sql._query_panel.geometry().intersects(mobile_sql._result_stack.parentWidget().geometry()):
        return 26
    mobile_sql_image = ROOT / "artifacts" / "admin_sql_diagnostics_mobile_offscreen.png"
    if (
        not mobile_sql.grab().save(str(mobile_sql_image), "PNG")
        or mobile_sql._scroll.horizontalScrollBar().maximum() != 0
        or mobile_sql._result_stack.currentWidget() is not mobile_sql._mobile_results
        or len(mobile_sql._mobile_results.findChildren(QLabel, "sqlResultValue")) != 15
    ):
        return 24
    mobile_sql.close()
    app.processEvents()
    window._navigate("customer_360")
    app.processEvents()
    customer_page = window._pages["customer_360"]
    if customer_page._thread:
        customer_page._thread.wait(3000)
    app.processEvents()
    customer_image = ROOT / "artifacts" / "admin_customer_360_offscreen.png"
    if not window.grab().save(str(customer_image), "PNG") or "8" not in customer_page._audit_total.text() or "AYEC-591309724851525554DE017E33B0DA6D42EC98B7E58DDC910" not in customer_page._license_code.text() or customer_page._users_table.height() != 150:
        return 23
    window._navigate("invite_codes")
    app.processEvents()
    invite_page = window._pages["invite_codes"]
    for worker in tuple(invite_page._workers):
        worker.wait(3000)
    app.processEvents()
    dialog_path = ROOT / "artifacts" / "admin_invite_create_dialog_offscreen.png"
    dialog_saved = []
    dialog_state = []
    original_exec = ModernDialog.exec

    def capture_invite_dialog(dialog):
        dialog.show()
        app.processEvents()
        dialog_saved.append(dialog.grab().save(str(dialog_path), "PNG"))
        dialog_state.append({
            "footer_actions": dialog.footer_layout.count(),
            "expiry_hours": invite_page.hours.currentData(),
            "max_uses": invite_page.max_uses.value(),
            "font_family": QFontInfo(dialog.font()).family(),
            "title_font_family": QFontInfo(dialog.lbl_title.font()).family(),
        })
        dialog.reject()
        return 0

    ModernDialog.exec = capture_invite_dialog
    invite_page._open_create_dialog()
    ModernDialog.exec = original_exec
    if not dialog_saved or not dialog_saved[0]:
        return 30
    if dialog_state[0]["footer_actions"] != 2:
        return 31
    if dialog_state[0]["expiry_hours"] != 72:
        return 32
    if dialog_state[0]["max_uses"] != 1:
        return 33
    if dialog_state[0]["font_family"] not in ("Segoe UI", "Arial"):
        return 34
    if dialog_state[0]["title_font_family"] not in ("Segoe UI", "Arial"):
        return 35
    for page in window._pages.values():
        timer = getattr(page, "_timer", None)
        if timer is not None:
            timer.stop()
        for worker_name in ("worker", "license_worker", "_thread"):
            worker = getattr(page, worker_name, None)
            if worker is not None and hasattr(worker, "isRunning") and worker.isRunning():
                worker.wait(5000)
        for workers_name in ("_workers", "_threads"):
            workers = getattr(page, workers_name, ())
            for worker in tuple(workers):
                if hasattr(worker, "isRunning") and worker.isRunning():
                    worker.wait(5000)
    window.close()
    app.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
