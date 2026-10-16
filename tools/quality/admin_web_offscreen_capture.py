import argparse
import json
import os
import re
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu --disable-gpu-compositing --disable-features=VizDisplayCompositor")
os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")
os.environ.setdefault("QT_OPENGL", "software")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from PyQt6.QtCore import QTimer, QUrl
from PyQt6.QtWebEngineCore import QWebEngineScript
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QApplication


ROOT = Path(__file__).resolve().parents[2]
DESIGN_REFERENCE_ROOT = Path("C:/Users/yedek/Desktop/Y\u00f6netim Konsolu Tasar\u0131m")
DESIGN_REFERENCE_FILES = {
    "dashboard": "DASHBOAD",
    "audit": "DENET\u0130M \u0130ZLEME",
    "live-status": "Canl\u0131 Firma Durumu",
    "license-requests": "Lisans Talepleri",
    "server-settings": "SUNUCU AYARI",
    "notifications": "Merkezi bildirim",
    "tenants": "Firma 360",
    "error-telemetry": "HaTA TELEMETR\u0130 G\u00d6NDERME",
    "backup-restore": "YEDEKLEME VER\u0130 KURTARMA",
    "quota-limits": "KOTA L\u0130M\u0130T",
    "staged-update": "G\u00dcNCELLEME OTA DA\u011eITIM",
    "database-query": "Kota Limit Sorgu",
}
LOGS = [
    {
        "id": 9942,
        "created_at": "2026-10-14T08:11:02Z",
        "action": "admin_password_reset",
        "actor_user_id": 7,
        "target_tenant_id": "tenant-aslan",
        "target_user_id": 11,
        "company_name": "ASLAN TIC",
        "ip_address": "192.168.1.108",
        "record_hash": "e3b0c44298fc1c149afbf4c8996fb924",
        "previous_hash": "cbf43926bbd5a919bafc4c2f9ce0d2a1",
        "detail": {
            "description": "Support verified password reset.",
            "changes": {
                "user.password_hash": {"before": "old-hash", "after": "new-hash"},
                "user.must_change_pwd": {"before": False, "after": True},
            },
        },
    },
    {
        "id": 9941,
        "created_at": "2026-10-14T08:08:12Z",
        "action": "admin_license_updated",
        "actor_user_id": 7,
        "target_tenant_id": "tenant-babali",
        "company_name": "Babali Servis",
        "record_hash": "cbf43926bbd5a919bafc4c2f9ce0d2a1",
        "previous_hash": "a54d88e06612d820bc3be72877c74f257b561b19",
        "detail": {"plan": "pro"},
    },
    {
        "id": 9940,
        "created_at": "2026-10-14T08:03:01Z",
        "action": "admin_readonly_query",
        "actor_user_id": 7,
        "target_tenant_id": "tenant-aslan",
        "company_name": "ASLAN TIC",
        "record_hash": "a54d88e06612d820bc3be72877c74f257b561b19",
        "previous_hash": "88c1a932bb12ca340989f554011cc098",
        "detail": {"table": "users"},
    },
]
AUDIT_LOGS = LOGS + [
    {
        "id": 9939,
        "created_at": "2026-10-14T07:45:00Z",
        "action": "admin_restore_queued",
        "actor_user_id": 8,
        "actor_username": "rootadmin",
        "target_tenant_id": "tenant-bulut",
        "company_name": "Bulut Bilisim Ltd.",
        "ip_address": "10.0.4.12",
        "record_hash": "88c1a932bb12ca340989f554011cc098",
        "previous_hash": "1109bc43a0889fce224a56c7104b901a",
        "detail": {"description": "A verified backup restore was queued."},
    },
    {
        "id": 9938,
        "created_at": "2026-10-13T22:15:19Z",
        "action": "admin_update_deployed",
        "actor_user_id": 8,
        "actor_username": "rootadmin",
        "target_tenant_id": "tenant-isiktas",
        "company_name": "Isiktas Oto Servis",
        "ip_address": "176.240.11.90",
        "record_hash": "1109bc43a0889fce224a56c7104b901a",
        "previous_hash": "e3b0c44298fc1c149afbf4c8996fb924",
        "detail": {"description": "OTA firmware deployment was queued."},
    },
    {
        "id": 9937,
        "created_at": "2026-10-13T14:10:02Z",
        "action": "admin_notification_sent",
        "actor_user_id": 7,
        "actor_username": "enginy",
        "target_tenant_id": "tenant-aslan",
        "company_name": "ASLAN TIC",
        "ip_address": "192.168.1.108",
        "record_hash": "e3b0c44298fc1c149afbf4c8996fb924",
        "previous_hash": "0f343b0931126a20f133d67c2b018a3b",
        "detail": {"description": "A platform notification was sent."},
    },
]
QUERY_AUDIT_LOGS = [
    {"id": 9942, "created_at": "2026-10-14T08:11:02.412Z", "action": "AUTH_OK", "company_name": "ASLAN T\u0130C", "severity": "INFO", "detail": {"description": "Kullan\u0131c\u0131 enginmamu22 istemci \u00fczerinden ba\u015far\u0131l\u0131 oturum a\u00e7t\u0131 (IP: 192.168.1.108).", "code": "enginmamu22", "code_tone": "success"}},
    {"id": 9941, "created_at": "2026-10-14T08:10:43.109Z", "action": "BACKUP_CREATED", "company_name": "SYSTEM_CORE", "severity": "AUDIT", "detail": {"description": "Otomatik anl\u0131k yedekleme olu\u015fturuldu: aslan-tic.db (1.6 MB, MD5: 9a7b...c3).", "code": "aslan-tic.db", "code_tone": "primary"}},
    {"id": 9940, "created_at": "2026-10-14T08:09:51.890Z", "action": "SYNC_OK", "company_name": "Babal\u0131", "severity": "TELEMETRY", "detail": {"description": "\u00c7evrimd\u0131\u015f\u0131 i\u015flem kuyru\u011fu ana lisans d\u00fc\u011f\u00fcm\u00fcyle e\u015fitlendi (2 servis formu senkronize)."}},
    {"id": 9939, "created_at": "2026-10-14T08:05:12.003Z", "action": "QUOTA_CHECK", "company_name": "I\u015f\u0131kta\u015f Oto Servis", "severity": "METRIC", "detail": {"description": "Kullan\u0131c\u0131 say\u0131s\u0131: 2/10, Kay\u0131tl\u0131 cihaz: 2/100, Disk: 0.73 MB. Limit a\u015f\u0131m\u0131 yok."}},
    {"id": 9938, "created_at": "2026-10-14T08:03:01Z", "action": "admin_password_reset", "company_name": "ASLAN T\u0130C", "severity": "SECURITY", "detail": {"description": "Support verified password reset."}},
    {"id": 9937, "created_at": "2026-10-14T08:00:00Z", "action": "quota_warning", "company_name": "Babal\u0131", "severity": "WARN", "detail": {"description": "Tenant approaching its storage limit."}},
]
NOTIFICATION_LOGS = [
    {"id": 9831, "created_at": "2026-10-14T05:00:00Z", "action": "control_notification_sent", "actor_user_id": 7, "target_tenant_id": "tenant-1", "company_name": "ASLAN TIC", "detail": {"title": "v2.0.1 Pilot G\u00fcncelleme Da\u011f\u0131t\u0131m\u0131"}},
    {"id": 9824, "created_at": "2026-10-13T20:30:00Z", "action": "control_notification_sent", "actor_user_id": 7, "target_tenant_id": "All", "company_name": "T\u00fcm Kay\u0131tl\u0131 Firmalar", "detail": {"title": "Mali M\u00fch\u00fcr & E-Fatura Planl\u0131 Bak\u0131m"}},
    {"id": 9812, "created_at": "2026-10-12T11:15:00Z", "action": "control_notification_sent", "actor_user_id": 7, "target_tenant_id": "tenant-2", "company_name": "Babali Servis", "detail": {"title": "Sunucu Yedekleme Bildirimi"}},
]
ERROR_LOGS = [
    {"id": 301, "level": "ERROR", "tenant_id": "tenant-1", "company_name": "ASLAN TIC", "license_code": "ILC-9940", "device_name": "DESKTOP-ENGIN-PC", "version": "2.4.0", "os_info": "Windows 11 Pro 64-bit (Build 22631)", "error_type": "SQLiteBusyException", "summary": "database is locked (5000 ms)", "error_message": "sqlite3.OperationalError: database is locked", "stack_trace": "db_worker.py:142 -> wal_checkpoint()\nsqlite3.OperationalError: database is locked", "created_at": "2026-10-14T08:05:12Z"},
    {"id": 300, "level": "WARNING", "tenant_id": "tenant-3", "company_name": "Bulut Bili\u015fim", "license_code": "ILC-4811", "device_name": "TERMINAL-02-AT\u00d6LYE", "version": "2.3.8", "os_info": "Windows 10 Pro", "error_type": "WhatsAppApiTimeout", "summary": "Meta Cloud API response 429", "error_message": "WhatsApp template send request timed out", "stack_trace": "wa_client.py:88 -> send_template_msg()\nWhatsAppApiTimeout: Meta Cloud API response 429", "created_at": "2026-10-14T07:58:39Z"},
    {"id": 299, "level": "WARNING", "tenant_id": "tenant-2", "company_name": "Babali Teknik", "license_code": "ILC-1029", "device_name": "KASA-DESK-01", "version": "2.0.4", "os_info": "Windows 10 Pro", "error_type": "PrinterSpoolerError", "summary": "Windows SpoolerRPC endpoint unavailable", "error_message": "Printer spooler endpoint unavailable", "stack_trace": "thermal_escpos.py:214 -> raw_print()\nPrinterSpoolerError: SpoolerRPC endpoint unavailable", "created_at": "2026-10-14T07:31:04Z"},
    {"id": 298, "level": "ERROR", "tenant_id": "tenant-4", "company_name": "I\u015f\u0131kta\u015f Elektronik", "license_code": "ILC-3320", "device_name": "LAB-ANALYST-PC", "version": "1.9.8", "os_info": "Windows 11 Pro", "error_type": "TelemetryHeartbeatSlow", "summary": "Roundtrip latency degraded", "error_message": "Telemetry heartbeat exceeded target latency", "stack_trace": "heartbeat.py:53 -> ping_cloud()\nTelemetryHeartbeatSlow: roundtrip latency degraded", "created_at": "2026-10-14T06:45:11Z"},
    {"id": 297, "level": "ERROR", "tenant_id": "tenant-1", "company_name": "ASLAN TIC", "license_code": "ILC-9940", "device_name": "DESKTOP-ENGIN-PC", "version": "2.4.0", "os_info": "Windows 11 Pro 64-bit (Build 22631)", "error_type": "EFaturaCryptoSignFail", "summary": "SmartCard token removed during certificate validation", "error_message": "e-Fatura crypto signature validation failed", "stack_trace": "gib_signer.py:391 -> parse_cert()\nSmartCard token removed", "created_at": "2026-10-14T05:19:00Z"},
]
DASHBOARD_LOGS = [
    {"id": 9942, "created_at": "2026-10-14T08:08:12Z", "action": "License Order Approved", "company_name": "ASLAN T\u0130C", "status": "Tamamland\u0131", "operator": "Root Admin"},
    {"id": 9941, "created_at": "2026-10-14T07:45:00Z", "action": "Otomatik Bulut Yedekleme", "company_name": "Babal\u0131 Servis", "status": "42.8 MB OK", "operator": "CRON / Daemon"},
    {"id": 9940, "created_at": "2026-10-14T06:12:30Z", "action": "Lisans G\u00fcncellendi (PRO v2.0)", "company_name": "Bulut Bili\u015fim Ltd.", "status": "+365 G\u00fcn", "operator": "Root Admin"},
    {"id": 9939, "created_at": "2026-10-13T22:15:19Z", "action": "Firmware Patch Sync #104", "company_name": "I\u015f\u0131kta\u015f Oto Servis", "status": "E\u015fitlendi", "operator": "Auto-Deploy"},
    {"id": 9938, "created_at": "2026-10-13T19:40:02Z", "action": "License Order Created", "company_name": "ASLAN T\u0130C", "status": "Beklemede", "operator": "Bayi Portal\u0131"},
    {"id": 9937, "created_at": "2026-10-13T14:10:44Z", "action": "SQL \u0130ndeksleme & Optimize", "company_name": "T\u00fcm Veritabanlar\u0131", "status": "0.42 ms", "operator": "PostgreSQL Worker"},
]
TENANTS = [
    {
        "id": f"tenant-{index}",
        "company_name": name,
        "current_version": ("v2.0.1 Pilot", "v2.0.0", "v1.9.0", "v2.0.0")[index - 1],
        "active": active,
        "users": [{"active": 1} for _ in range(users)],
        "backups": [{}] if backups else [],
        "commands": commands,
    }
    for index, (name, active, users, backups, commands) in enumerate(
        [
            ("ASLAN TIC", 1, 2, True, [{"command_type": "deploy_update", "status": "completed", "version": "v2.0.1-rc3", "created_at": "2026-10-14T10:42:15Z"}]),
            ("Babali Servis", 1, 1, True, [{"command_type": "deploy_update", "status": "pending", "version": "v2.0.1-rc3", "created_at": "2026-10-14T10:42:01Z"}]),
            ("Bulut Bilisim Ltd.", 1, 1, True, [{"command_type": "deploy_update", "status": "failed", "version": "v2.0.1-rc3", "created_at": "2026-10-14T10:41:38Z"}]),
            ("Isiktas Oto Servis", 1, 0, True, [{"command_type": "deploy_update", "status": "pending", "version": "v2.0.1-rc3", "created_at": "2026-10-14T10:40:22Z"}]),
        ],
        1,
    )
]
LIVE_DETAILS = [
    {"user_id": 7, "user_name": "Engin ASLAN", "user_role": "SuperAdmin", "location": "Gonen/Balikesir", "sector": "ANA DUGUM (ROOT)", "tenant_code": "AYEC-TR-1001", "heartbeat": "1 sn once", "socket_port": 52410, "uptime_text": "146 06S 22D", "ip_address": "192.168.1.108", "db_filename": "ayec_aslan.db", "db_size_mb": 1.07, "wal_frames": 48, "user_agent": "1 Operator", "dashboard_version": "v2.0.1 (Pilot)", "dashboard_latency_ms": 11, "display_ping_ms": 11, "dashboard_seen_text": "2 sn \u00f6nce"},
    {"user_id": 8, "user_name": "Emirhan BABALI", "user_role": "Yoneticisi", "location": "Balikesir Merkez", "sector": "OTOMOTIV", "tenant_code": "AYEC-TR-1002", "heartbeat": "3 sn once", "socket_port": 49112, "uptime_text": "v2.0.0 Stabil", "ip_address": "192.168.1.109", "db_filename": "ayec_babali.db", "db_size_mb": 0.69, "queue_count": 0, "user_agent": "AYEC Pro Desktop", "dashboard_version": "v2.0.0 (Stabil)", "dashboard_latency_ms": 14, "display_ping_ms": 14, "dashboard_seen_text": "5 sn \u00f6nce"},
    {"user_id": 9, "user_name": "Engin MAMU", "user_role": "Teknisyen", "location": "Bandirma", "sector": "BILISIM", "tenant_code": "AYEC-TR-1003", "heartbeat": "8 sn once", "socket_port": 38120, "uptime_text": "v1.9 (Eski)", "ip_address": "176.220.14.99", "db_filename": "ayec_bulut.db", "db_size_mb": 0.71, "sync_state": "Senkronizasyon Bekliyor", "user_agent": "AYEC Pro Desktop", "dashboard_version": "v1.9 (Eski)", "dashboard_latency_ms": 22, "display_ping_ms": 92, "dashboard_seen_text": "1 sn \u00f6nce"},
    {"user_id": 10, "user_name": "Hasan ISIKTAS", "user_role": "Firma Sahibi", "location": "Bandirma", "sector": "SERVIS", "tenant_code": "AYEC-TR-1004", "heartbeat": "2 sn once", "socket_port": 50114, "uptime_text": "26 11S 45D", "ip_address": "78.135.20.14", "db_filename": "ayec_isiktas.db", "db_size_mb": 0.73, "sync_state": "Senkronize", "user_agent": "AYEC Pro Desktop", "dashboard_version": "v2.0.0 (Stabil)", "dashboard_latency_ms": 18, "display_ping_ms": 18, "dashboard_seen_text": "Simdi"},
]
LIVE_COMPANIES = [
    {"id": row["id"], "company_name": row["company_name"], "online": True, "active_users": len(row["users"]), "active_terminals": (3, 3, 5, 7)[index], **details}
    for index, (row, details) in enumerate(zip(TENANTS, LIVE_DETAILS))
]
COMPANY_PROFILES = [
    {"id": row["id"], "company_name": row["company_name"], "active": row["active"], "sector": "otomotiv" if index == 4 else "teknik_servis", "license_type": "3 Yillik Kurumsal", "license_code": "AYEC-591309724851525554DE017E33B0DA6D42EC98B7E58DDC910", "license_end": "2029-10-07", "contact_name": "Engin ASLAN", "phone": "0534 878 10 47", "email": "enginmamu22@gmail.com", "company_address": "Gonen / Balikesir", "users": [{"id": 11, "full_name": "Engin ASLAN", "username": "enginmamu22", "email": "enginmamu22@gmail.com", "phone": "05348781047", "role": "User", "active": 1}, {"id": 12, "full_name": "AYEC Platform Owner", "username": "ayecpro", "email": "ayecpro@gmail.com", "role": "Admin", "active": 1}], "backups": [{}] if index == 1 else []}
    for index, row in enumerate(TENANTS, 1)
]
COMPANY_DETAILS = {
    profile["id"]: {"company": profile, "users": profile["users"], "licenses": [{"license_code": profile["license_code"], "license_type": profile["license_type"], "license_end": profile["license_end"]}], "backups": profile["backups"], "error_logs": [], "live_status": {"online": True, "active_users": len(profile["users"]), "ping_ms": 18, "last_seen": "2026-10-14 05:09:33"}, "summary": {"user_count": len(profile["users"]), "backup_count": len(profile["backups"]), "error_count": 0, "online": True}}
    for profile in COMPANY_PROFILES
}
FIXTURES = {
    "/api/control/overview": {
        "vendor": {"name": "AYEC Pro", "server": "lisans.ayecpro.com"},
        "tenants": TENANTS,
    },
    "/api/admin/server-status": {"version": "2.0.0", "db_path": "C:/Web_Arayuzu/data/ayecpro.db", "cpu_percent": 3, "ram_percent": 52, "disk_percent": 30, "cpu_cores": "8 \u00c7ekirdek", "cpu_model": "Xeon Gold 3.4GHz", "cpu_load": "Yuk: 0.12, 0.08, 0.05", "ram_type": "DDR4 ECC", "ram_used_gb": 8.4, "ram_total_gb": 16.0, "swap_used_gb": 0, "swap_total_gb": 4.0, "disk_type": "Gen4 RAID 1", "disk_used_gb": 30.0, "disk_total_gb": 99.0, "disk_free_gb": 69.0, "disk_health_percent": 99, "database_size_bytes": 1121976, "database_wal_state": "WAL AKT\u0130F", "database_wal_kb": 42, "database_table_count": "Tablolar: 42 adet", "database_sync_state": "Cloud Mirror Cift Yonlu", "network_tls": "TLS 1.3", "network_mbps": 1.4, "network_ping_ms": 14, "network_active_state": "WebSocket Aktif (9280)", "network_packet_state": "Kayipsiz Paket"},
    "/api/admin/dashboard": {
        "online_users": 4,
        "logins_today": 18,
        "disk_usage": "30.0 / 99.0 GB",
        "backup_coverage": 4,
        "pending_commands": 0,
        "expiring_licenses": 0,
            "recent_logs": [
            {"id": row["id"], "created_at": row["created_at"], "action": row["action"], "company": row["company_name"], "status": row["status"], "operator": row["operator"]}
            for row in DASHBOARD_LOGS
        ],
    },
    "/api/admin/live-status": {"companies": LIVE_COMPANIES, "throughput_mbps": 1.4, "pending_command_count": 0},
    "/api/admin/companies": {"companies": COMPANY_PROFILES},
    **{f"/api/admin/customer-360/{tenant_id}": detail for tenant_id, detail in COMPANY_DETAILS.items()},
    "/api/admin/audit-logs?limit=20": {"logs": DASHBOARD_LOGS},
    "/api/admin/audit-logs?limit=100": {"logs": NOTIFICATION_LOGS},
    "/api/admin/audit-logs?limit=200": {"logs": AUDIT_LOGS},
    "/api/control/telemetry/errors": {"logs": ERROR_LOGS, "stability_percent": 98.5, "handled_count": 14},
    "/api/admin/backups/tenant-1": {"backups": [
        {"index": 8, "backup_id": 8, "filename": "ASLAN_TIC_auto_snapshot_20261014_0810.db", "size_bytes": 1677721, "modified": "2026-10-14T08:10:14", "source": "Server WAL Daemon", "kind": "support", "hardware_id": "ASLAN-TERM-01", "product_code": "teknik_servis", "sha256": "9a7b1402f631a65e"},
        {"index": 7, "backup_id": 7, "filename": "ASLAN_TIC_pre_update_backup_v2.0.0.db", "size_bytes": 1677721, "modified": "2026-10-13T22:15:00", "source": "G\u00fcncelleme Oncesi Otomatik", "kind": "support", "hardware_id": "ASLAN-TERM-01", "product_code": "teknik_servis", "sha256": "4f3a8b91d29ca2e1"},
        {"index": 6, "backup_id": 6, "filename": "BABALI_TEK_daily_cron_snapshot.db", "size_bytes": 723518, "modified": "2026-10-14T04:00:12", "source": "Otomatik Cron (AWS S3)", "kind": "support", "hardware_id": "BABALI-TERM-01", "product_code": "otomotiv", "sha256": "88c1a93270bbf008"},
        {"index": 5, "backup_id": 5, "filename": "BULUT_BILISIM_full_backup.db", "size_bytes": 744488, "modified": "2026-10-12T18:30:45", "source": "Manuel Istemci Talebi", "kind": "support", "hardware_id": "BULUT-TERM-01", "product_code": "teknik_servis", "sha256": ""},
        {"index": 4, "backup_id": 4, "filename": "ISIKTAS_OTO_nightly_backup.db", "size_bytes": 765460, "modified": "2026-10-14T02:00:12", "source": "Gece Yedekleme Otomasyonu", "kind": "support", "hardware_id": "ISIKTAS-TERM-01", "product_code": "otomotiv", "sha256": "1109bc43f0b7cd21"},
    ]},
    "/api/admin/licenses/usage": {"usages": [
        {"tenant_id": "tenant-1", "company_name": "ASLAN TIC", "license_code": "AYEC-1001", "package_name": "Kurumsal Paket", "db_size_mb": 1.64, "db_limit_gb": 10, "users_count": 2, "active_users": 2, "users_limit": 10, "devices_count": 20, "devices_limit": 100, "services_count": 248, "services_limit": 1000},
        {"tenant_id": "tenant-2", "company_name": "Babali Servis", "license_code": "AYEC-1002", "package_name": "Pro Paket", "db_size_mb": 0.69, "db_limit_gb": 5, "users_count": 2, "active_users": 2, "users_limit": 10, "devices_count": 0, "devices_limit": 100, "services_count": 45, "services_limit": 1000},
        {"tenant_id": "tenant-3", "company_name": "Bulut Bilisim Ltd.", "license_code": "AYEC-1003", "package_name": "Standart Paket", "db_size_mb": 0.71, "db_limit_gb": 5, "users_count": 2, "active_users": 2, "users_limit": 10, "devices_count": 2, "devices_limit": 100, "services_count": 86, "services_limit": 1000},
        {"tenant_id": "tenant-4", "company_name": "Isiktas Oto Servis", "license_code": "AYEC-1004", "package_name": "Pro Paket", "db_size_mb": 0.73, "db_limit_gb": 5, "users_count": 2, "active_users": 2, "users_limit": 10, "devices_count": 2, "devices_limit": 100, "services_count": 33, "services_limit": 1000},
    ]},
    "/api/admin/companies/tenant-1/query": {"columns": ["id", "username", "role", "last_login", "disk_usage_mb"], "rows": [[101, "enginmamu22", "Super Admin", "2026-10-14 08:11", 0.82], [102, "aslan_teknik", "Teknisyen", "2026-10-14 07:45", 0.64], [104, "babali_operator", "Operator", "2026-10-13 18:20", 0.18]], "truncated": False},
    "/api/control/staged-update": {"ok": True, "updates": [
        {"id": 3, "version": "v2.0.1-rc3", "target_scope": "Pilot", "file_path": "https://updates.ayecpro.com/v2.0.1-rc3.zip", "notes": "Hotfix: SQLite WAL checkpoint optimizasyonu, seri fatura kuyru\u011fu ve yaz\u0131c\u0131 s\u00fcr\u00fcc\u00fcs\u00fc uyumlu", "created_at": "2026-10-14T10:42:00Z"},
        {"id": 2, "version": "v2.0.0", "target_scope": "Stable", "file_path": "https://updates.ayecpro.com/v2.0.0.zip", "notes": "Stable release", "created_at": "2026-10-01T09:00:00Z"},
    ]},
    "/api/admin/license-orders": {
        "orders": [
            {"id": 101, "request_no": "REQ-9921", "company_name": "ASLAN TIC LTD. STI.", "requester_name": "Engin Aslan", "plan_label": "3 Yillik Kurumsal", "amount_try": 15990, "payment_reference": "PAY-101", "status": "payment_reported", "description": "ASLAN TIC icin lisans uzatma ve ilave 10 koltuk terminal paketi siparisi. Mali muhür ve dekont kontrolu yapildi, derleme emri bekleniyor.", "created_at": "2026-10-14 09:42"},
            {"id": 102, "request_no": "REQ-9922", "company_name": "Babali Servis Teknoloji", "requester_name": "Bora Yilmaz", "plan_label": "Lifetime Core Eklenti", "amount_try": 4500, "payment_reference": "PAY-102", "status": "payment_pending", "description": "Teknik Servis ana modulune ilave Otomotiv Teshis ve Barkod yazici terminal lisansi aktivasyonu. Odeme provizyonu tamamlandi.", "created_at": "2026-10-14 09:38"},
        ]
    },
    "/api/admin/licenses": {
        "licenses": [
            {"tenant_id": "tenant-1", "company_name": "ASLAN TIC", "branch_name": "Ana Bayi - Kadikoy", "product_code": "teknik_servis", "license_code": "AYEC-TS-8841-K992-SEC", "license_type": "3 Yillik Kurumsal", "license_start": "2026-10-14", "license_end": "2028-10-24", "status": "Active", "display_ping_ms": 11},
            {"tenant_id": "tenant-2", "company_name": "Babali Servis", "branch_name": "Sube #1 - Altindag", "product_code": "teknik_servis", "license_code": "AYEC-TS-3310-M104-SEC", "license_type": "Lifetime Sinirsiz", "status": "Active", "display_ping_ms": 14},
            {"tenant_id": "tenant-3", "company_name": "Bulut Bilisim & Donanim", "branch_name": "Merkez Servis - Izmir", "product_code": "saha", "license_code": "AYEC-TS-9923-P008-SEC", "license_type": "1 Yillik Pro", "license_start": "2026-09-15", "license_end": "2026-11-26", "status": "Active", "display_ping_ms": 19},
            {"tenant_id": "tenant-4", "company_name": "Isiktas Oto Elektronik", "branch_name": "Servis Terminali - Bursa", "product_code": "otomotiv", "license_code": "AYEC-TS-1200-Z441-SEC", "license_type": "15 Gunluk Pilot", "license_start": "2026-10-11", "license_end": "2026-10-18", "status": "Active", "display_ping_ms": 88},
        ]
    },
    "/api/control/provision-invites": {
        "invites": [
            {
                "id": index,
                "created_at": "2026-10-14T09:00:00+00:00" if index > 42 else "2026-10-01T09:00:00+00:00",
                "expires_at": "2028-10-14T00:00:00+00:00",
                "max_uses": 1,
                "use_count": 0 if index <= 12 or index > 46 else 1,
                "revoked_at": "2026-10-14T00:00:00+00:00" if index > 46 else None,
            }
            for index in range(1, 49)
        ]
    },
}


def add_api_fixtures(page, screen):
    script = QWebEngineScript()
    script.setName("admin-web-offscreen-fixtures")
    script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
    script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
    script.setRunsOnSubFrames(False)
    fixture_data = dict(FIXTURES)
    if screen == "database-query":
        query_status = dict(fixture_data["/api/admin/server-status"])
        query_status.update({"cpu_percent": 3.2, "ram_percent": 52.4, "disk_percent": 30.3, "cpu_cores": "4 \u00c7ekirdek", "cpu_model": "2.40 GHz", "ram_used_gb": 4.1, "ram_total_gb": 8.0, "disk_type": "NVMe SSD"})
        fixture_data["/api/admin/server-status"] = query_status
        fixture_data["/api/admin/audit-logs?limit=200"] = {"logs": QUERY_AUDIT_LOGS, "total_count": 324, "category_counts": {"error": 0, "warn": 2, "audit": 48, "security": 12}}
    if screen == "notifications":
        company_names = ["ASLAN T\u0130C. LTD.", "Babali Motor Servis", "Bulut Bili\u015fim Teknoloji", "I\u015f\u0131kta\u015f Oto Servis & Yedek Par\u00e7a"]
        overview = dict(fixture_data["/api/control/overview"])
        overview["tenants"] = [{**tenant, "company_name": company_names[index]} for index, tenant in enumerate(overview["tenants"])]
        fixture_data["/api/control/overview"] = overview
        for endpoint in ("/api/admin/companies", "/api/admin/live-status"):
            response = dict(fixture_data[endpoint])
            response["companies"] = [{**company, "company_name": company_names[index]} for index, company in enumerate(response["companies"])]
            fixture_data[endpoint] = response
    fixture_json = json.dumps(fixture_data, ensure_ascii=True, separators=(",", ":"))
    script.setSourceCode(
        "(()=>{const fixtures="
        + fixture_json
        + ";window.__adminFixtureWrites=[];window.fetch=async (input,init={})=>{const options=init||{};const url=new URL(typeof input===\"string\"?input:input.url,location.href);"
        + "const path=url.pathname.replace(/^\\/[A-Za-z]:/i,\"\");const body=fixtures[path+url.search]||fixtures[path]||{};"
        + "const method=String(options.method||input.method||\"GET\").toUpperCase();if(method!==\"GET\")window.__adminFixtureWrites.push({path,method,body:options.body||\"\"});"
        + "return new Response(JSON.stringify(body),{status:200,headers:{\"Content-Type\":\"application/json; charset=utf-8\"}})}})()"
    )
    page.scripts().insert(script)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--screen", choices=("dashboard", "audit", "live-status", "license-requests", "server-settings", "notifications", "tenants", "error-telemetry", "backup-restore", "quota-limits", "staged-update", "database-query"), default="dashboard")
    parser.add_argument("--width", type=int, default=1440)
    parser.add_argument("--height", type=int, default=1000)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    reference_source = (DESIGN_REFERENCE_ROOT / f"{DESIGN_REFERENCE_FILES[args.screen]}.html").read_text(encoding="utf-8")
    header_match = re.search(r'<header\b[^>]*class="([^"]*)"', reference_source, re.IGNORECASE)
    reference_header_height = None
    if header_match:
        reference_header_height = next(
            (int(token[2:]) * 4 for token in header_match.group(1).split() if token.startswith("h-") and token[2:].isdigit()),
            None,
        )
    reference_search_height = None
    if header_match:
        header_end = reference_source.lower().find("</header>", header_match.start())
        header_source = reference_source[header_match.start():header_end] if header_end >= 0 else reference_source[header_match.start():]
        search_match = re.search(r'<input\b[^>]*class="([^"]*)"', header_source, re.IGNORECASE)
        if search_match:
            search_classes = search_match.group(1).split()
            reference_search_height = next(
                (int(token[2:]) * 4 for token in search_classes if token.startswith("h-") and token[2:].isdigit()),
                None,
            )
            if reference_search_height is None and "py-1" in search_classes and "text-body-sm" in search_classes:
                reference_search_height = 26
    output = args.output or ROOT / "artifacts" / f"admin_{args.screen}_web_{args.width}x{args.height}.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    app = QApplication(sys.argv)
    view = QWebEngineView()
    view.resize(args.width, args.height)
    page = view.page()
    page.settings().setDefaultTextEncoding("UTF-8")
    add_api_fixtures(page, args.screen)

    setup = "window.__captureSetupDone=false;(async()=>{document.querySelector('#authRoot')?.remove();document.body.classList.remove('auth-active');const fontFallback=document.createElement('style');fontFallback.textContent='html,body{font-family:\"Plus Jakarta Sans\",\"Segoe UI\",Arial,sans-serif!important}';document.head.appendChild(fontFallback);"
    setup += f"activeAdminTab={json.dumps("telemetry" if args.screen == "error-telemetry" else args.screen)};page='control-center';render();"
    if args.screen == "dashboard":
        setup += "window.__adminDashboardSamples=[5.2,7.2,6.2,10.2,8.2,12.2,17.2,13.2,21.2,16.2,20.2,12].map((ms,index)=>({at:Date.now()-(11-index)*5*60*1000,ms}));"
    setup += "await loadControlCenter();document.querySelectorAll('dialog[open]').forEach(dialog=>dialog.close());"
    if args.screen == "live-status":
        setup += (
            "window.__liveActionBehavior={};"
            "document.querySelector('[data-live-action=diagnostics]')?.click();"
            "window.__liveActionBehavior.diagnosticsOpened=!!document.querySelector('#appDialog')?.open;"
            "document.querySelector('#dialogCancel')?.click();"
            "const messageButton=document.querySelector('[data-live-action=message]');window.__liveActionBehavior.messageTenant=messageButton?.dataset.liveTenant||'';messageButton?.click();"
            "for(let attempt=0;attempt<120;attempt++){const selected=[...document.querySelectorAll('[data-notify-tenant]:checked')].map(input=>input.dataset.notifyTenant);if(document.querySelector('#adminNotificationForm')&&selected.length===1&&selected[0]==='tenant-1')break;await new Promise(resolve=>setTimeout(resolve,25))}"
            "window.__liveActionBehavior.notificationTab=activeAdminTab;window.__liveActionBehavior.notificationTargets=[...document.querySelectorAll('[data-notify-tenant]:checked')].map(input=>input.dataset.notifyTenant);"
            "activeAdminTab='live-status';await loadControlCenter();"
        )
    if args.screen == "tenants":
        setup += (
            "try{"
            "for(let attempt=0;attempt<20&&!document.querySelector('#company360Sector');attempt++)await new Promise(resolve=>setTimeout(resolve,50));"
            "const companySearch=document.querySelector('#company360Search');companySearch.value='Babali';"
            "companySearch.dispatchEvent(new Event('input'));const searchMatches=[...document.querySelectorAll('[data-company360-id]')].filter(row=>!row.hidden).length;"
            "companySearch.value='';companySearch.dispatchEvent(new Event('input'));"
            "document.querySelector('[data-company-filter=inactive]').click();const inactiveRows=[...document.querySelectorAll('[data-company360-id]')].filter(row=>!row.hidden).length;"
            "document.querySelector('[data-company-filter=all]').click();"
            "const sectorForm=document.querySelector('#company360Sector');sectorForm.querySelector('[name=sector]').value='otomotiv';"
            "sectorForm.requestSubmit();await new Promise(resolve=>setTimeout(resolve,450));"
            "const sectorWrite=window.__adminFixtureWrites.find(write=>write.path==='/api/control/tenant');"
            "window.__company360Behavior={searchMatches,inactiveRows,sectorWrite:sectorWrite?{path:sectorWrite.path,method:sectorWrite.method,body:JSON.parse(sectorWrite.body)}:null};"
            "}catch(error){window.__company360Behavior={error:String(error)}}"
        )
    if args.screen == "database-query":
        setup += (
            "try{"
            "for(let attempt=0;attempt<20&&!document.querySelector('[data-query-audit-filter=security]');attempt++)await new Promise(resolve=>setTimeout(resolve,50));"
            "const search=document.querySelector('#adminQueryAuditSearch'),allRows=document.querySelectorAll('.admin-query-telemetry-table tbody tr').length;"
            "document.querySelector('[data-query-audit-filter=security]').click();const securityRows=document.querySelectorAll('.admin-query-telemetry-table tbody tr').length;"
            "search.value='password';search.dispatchEvent(new Event('input'));const passwordRows=document.querySelectorAll('.admin-query-telemetry-table tbody tr').length;"
            "search.value='';search.dispatchEvent(new Event('input'));document.querySelector('[data-query-audit-filter=all]').click();"
            "window.__queryAuditBehavior={allRows,securityRows,passwordRows};"
            "}catch(error){window.__queryAuditBehavior={error:String(error)}}"
        )
    setup += "document.body.dataset.page='control-center';document.querySelectorAll('#toastRoot .toast').forEach(node=>node.remove());"
    setup += "await document.fonts.ready;await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));return true})().then(()=>window.__captureSetupDone=true)"
    capture_ok = []
    capture_retries = [0]
    render_waited = [False]

    def finish_capture():
        saved = [False]
        query = "(()=>{const integrityButton=document.querySelector('[data-audit-integrity]');integrityButton?.click();const integrityToast=document.querySelector('#toastRoot')?.innerText||'';document.querySelectorAll('#toastRoot .toast').forEach(node=>node.remove());const adminContent=document.querySelector('#adminTabContent'),adminStyle=adminContent?getComputedStyle(adminContent):null,shellStyle=document.querySelector('.topbar')?getComputedStyle(document.querySelector('.topbar')):null;return JSON.stringify({encoding:document.characterSet,openDialogs:[...document.querySelectorAll('dialog[open]')].map(dialog=>dialog.id),shortcutOverlayOpen:!!document.querySelector('.dashboard-shortcut-overlay'),fontFamily:shellStyle?.fontFamily||'',topbarBackground:shellStyle?.backgroundColor||'',topbarShadow:shellStyle?.boxShadow||'',topbarBorderWidth:shellStyle?.borderBottomWidth||'',topbarBackdropFilter:shellStyle?.backdropFilter||'',adminFontFamily:adminStyle?.fontFamily||'',adminFontLoaded:document.fonts.check('400 14px \"Plus Jakarta Sans\"'),adminTokens:adminStyle?{surface:adminStyle.getPropertyValue('--surface').trim(),surface2:adminStyle.getPropertyValue('--surface-2').trim(),text:adminStyle.getPropertyValue('--text').trim(),muted:adminStyle.getPropertyValue('--muted').trim(),line:adminStyle.getPropertyValue('--line').trim(),primary:adminStyle.getPropertyValue('--primary').trim()}:null,viewport:document.documentElement.clientWidth,document:document.documentElement.scrollWidth,overflowElements:[...document.querySelectorAll('body *')].map(node=>({tag:node.tagName,id:node.id,cls:String(node.className?.baseVal||node.className||'').slice(0,80),text:String(node.innerText||node.getAttribute('aria-label')||node.title||'').trim().slice(0,48),left:Math.round(node.getBoundingClientRect().left),right:Math.round(node.getBoundingClientRect().right),width:Math.round(node.getBoundingClientRect().width)})).filter(node=>node.right>document.documentElement.clientWidth+1).sort((a,b)=>b.right-a.right).slice(0,8),"
        query += "auditRects:['.audit-page-toolbar','.audit-compliance-badges','.audit-category-tabs','.audit-metrics','.audit-filter-panel','.audit-workspace','.audit-stream-panel','.audit-inspector-panel','#auditEventList','#auditInspector'].map(sel=>{const n=document.querySelector(sel);if(!n)return {sel,missing:true};const r=n.getBoundingClientRect();return {sel,left:Math.round(r.left),top:Math.round(r.top),width:Math.round(r.width),height:Math.round(r.height),children:[...n.children].slice(0,5).map(c=>{const q=c.getBoundingClientRect();return {cls:String(c.className||'').slice(0,60),left:Math.round(q.left),top:Math.round(q.top),width:Math.round(q.width),height:Math.round(q.height)}})}}),dashboardRects:['.control-dashboard-toolbar','.control-kpi-primary','.control-kpi-secondary','.control-dashboard-grid','.control-dashboard-primary-column','.control-audit-panel','.control-performance-panel','.control-dashboard-aside','.control-dashboard-aside > section','.control-dashboard-aside > section:nth-child(2)','.control-dashboard-aside > section:nth-child(2) > *','.control-security-note','.control-health-list'].map(sel=>{const n=document.querySelector(sel);if(!n)return {sel,missing:true};const r=n.getBoundingClientRect();return {sel,left:Math.round(r.left),top:Math.round(r.top),width:Math.round(r.width),height:Math.round(r.height),children:[...n.children].slice(0,5).map(c=>{const q=c.getBoundingClientRect();return {cls:String(c.className||'').slice(0,65),left:Math.round(q.left),top:Math.round(q.top),width:Math.round(q.width),height:Math.round(q.height)}})}}),activeTab:activeAdminTab,adminTabAttribute:document.body.dataset.adminTab||'',adminTabMatches:document.body.matches('body[data-page=\"control-center\"][data-admin-tab=\"license-requests\"]'),crumbDisplay:getComputedStyle(document.querySelector('.topbar > div:first-of-type')).display,crumbText:document.querySelector('#breadcrumb')?.innerText||'',rows:document.querySelectorAll('[data-audit-select]').length,"
        query += "companyRows:document.querySelectorAll('.control-health-row').length,auditRows:document.querySelectorAll('.control-audit-table tbody tr').length,controlActionDisabledCount:document.querySelectorAll('.control-quick-actions button:disabled').length,controlActionRoutes:[...document.querySelectorAll('.control-quick-actions button[data-control-action]')].map(button=>button.dataset.controlAction),"
        query += "liveActionCount:document.querySelectorAll('.admin-live-company [data-live-action]').length,liveActionDisabledCount:document.querySelectorAll('.admin-live-company [data-live-action]:disabled').length,liveActionRoutes:[...new Set([...document.querySelectorAll('.admin-live-company [data-live-action]')].map(button=>button.dataset.liveAction))].sort(),"
        query += "liveActionBehavior:window.__liveActionBehavior||{},"
        query += "auditTitleRects:['.audit-page-intro','.audit-page-title-row','.audit-page-title-row h2','.audit-compliance-icon','.audit-compliance-tags','.audit-compliance-tags span','.audit-compliance-actions'].map(sel=>{const n=document.querySelector(sel);if(!n)return {sel,missing:true};const r=n.getBoundingClientRect();return {sel,left:Math.round(r.left),width:Math.round(r.width),height:Math.round(r.height),font:getComputedStyle(n).fontSize}}),"
        query += "metricValues:[...document.querySelectorAll('.control-kpi b,.license-metric b,.admin-error-metrics strong,.admin-backup-metrics strong,.admin-quota-metrics strong,.admin-ota-metrics strong')].map(node=>node.textContent),"
        query += "licenseMetricDetails:[...document.querySelectorAll('.license-metric small')].map(node=>node.textContent.trim()),"
        query += "quotaBehavior:(()=>{const search=document.querySelector('#quotaSearch'),filter=document.querySelector('#quotaPackage');if(!search||!filter)return null;search.value='Babali';search.dispatchEvent(new Event('input',{bubbles:true}));const searchCount=document.querySelectorAll('#quotaRows tr[data-quota-row]:not([hidden])').length;search.value='';search.dispatchEvent(new Event('input',{bubbles:true}));filter.value='Pro Paket';filter.dispatchEvent(new Event('change',{bubbles:true}));const packageCount=document.querySelectorAll('#quotaRows tr[data-quota-row]:not([hidden])').length;filter.value='';filter.dispatchEvent(new Event('change',{bubbles:true}));return {searchCount,packageCount}})(),"
        query += "quotaCopy:{title:document.querySelector('.admin-quota-title h2')?.textContent.trim()||'',subtitle:document.querySelector('.admin-quota-title p')?.textContent.trim()||'',tableTitle:document.querySelector('.admin-quota-table-card h3')?.textContent.trim()||'',policyTitle:document.querySelector('.admin-quota-policy h3')?.textContent.trim()||'',upgradeTitle:document.querySelector('.admin-quota-upgrade h3')?.textContent.trim()||'',upgradeAmount:document.querySelector('.admin-quota-upgrade > footer button')?.textContent.trim()||'',policyFooter:document.querySelector('.admin-quota-policy-footer')?.innerText.trim()||'',policyInputs:[...document.querySelectorAll('.admin-quota-policy input[type=checkbox]')].map(node=>node.checked),upgradePrices:[...document.querySelectorAll('.admin-quota-upgrade-options strong')].map(node=>node.textContent.trim()),tableHeaders:[...document.querySelectorAll('.admin-quota-table-wrap th')].map(node=>node.textContent.trim()),tableHeaderTransform:getComputedStyle(document.querySelector('.admin-quota-table-wrap th')||document.body).textTransform},quotaPolicyToggle:(()=>{const n=document.querySelector('.admin-quota-policy input[type=checkbox]');if(!n)return false;const before=n.checked;n.click();const changed=n.checked!==before;n.click();return changed&&n.checked===before})(),"
        query += "liveFilterBehavior:(()=>{const slow=document.querySelector('[data-live-filter=slow]');if(!slow)return null;slow.click();const slowCount=document.querySelectorAll('[data-live-company]:not([hidden])').length;document.querySelector('[data-live-filter=all]')?.click();return {slowCount,restoredCount:document.querySelectorAll('[data-live-company]:not([hidden])').length}})(),"
        query += "metricBadges:[...document.querySelectorAll('.control-kpi-badge')].map(node=>node.textContent),diskProgress:document.querySelector('.control-kpi-progress > span')?.style.width||'',"
        query += "chartLine:document.querySelector('.control-performance-line')?.getAttribute('d')||'',"
        query += "auditFooter:document.querySelector('.control-audit-panel > footer')?.innerText||'',performanceBackground:(()=>{const node=document.querySelector('.control-performance-panel');return node?getComputedStyle(node).backgroundColor:''})(),performanceAverage:document.querySelector('.control-performance-average')?.innerText||'',performanceCurrent:document.querySelector('.control-performance-axis b')?.innerText||'',"
        query += "licenseRects:['.license-requests-toolbar','.license-request-metrics','.license-requests-section','.license-request-grid','.license-inventory-section','.license-inventory-table','.license-requests-context','.license-active-product','.license-active-product > div','.license-requests-title','.license-invite-open'].map(sel=>{const n=document.querySelector(sel);if(!n)return {sel,missing:true};const r=n.getBoundingClientRect();return {sel,left:Math.round(r.left),top:Math.round(r.top),width:Math.round(r.width),height:Math.round(r.height)}}),licenseRequestCards:document.querySelectorAll('.license-request-card').length,licenseInventoryRows:document.querySelectorAll('.license-inventory-table tbody tr').length,licenseTableMetrics:(()=>{const t=document.querySelector('.license-inventory-table'),r=e=>{const q=e?.getBoundingClientRect();return q?[Math.round(q.left),Math.round(q.top),Math.round(q.width),Math.round(q.height)]:null};return {table:r(t),head:r(t?.tHead),cells:Array.from(t?.tHead?.rows[0]?.cells||[]).map(r),row1:Array.from(t?.tBodies[0]?.rows[0]?.cells||[]).map(r),rows:Array.from(t?.tBodies[0]?.rows||[]).map(r)}})(),licenseTableText:[...document.querySelectorAll('.license-inventory-table tbody tr')].map(row=>[...row.cells].map(cell=>cell.textContent.trim().replace(/\\s+/g,' ').slice(0,90))),licenseTelemetry:[...document.querySelectorAll('.license-telemetry')].map(node=>node.textContent.trim()),licenseTitle:document.querySelector('.license-requests-title h2')?.textContent||'',licenseHsmBadge:document.querySelector('.license-hsm-badge')?.textContent||'',licenseInviteButton:!!document.querySelector('.license-invite-open'),licenseInviteNavigates:(()=>{const button=document.querySelector('.license-invite-open');if(!button)return false;const before=activeAdminTab;button.click();const changed=activeAdminTab==='provision-invites';document.querySelector('[data-admin-tab='+JSON.stringify(before)+']')?.click();activeAdminTab=before;return changed})(),licenseQueueTitle:document.querySelector('.license-queue-title h3')?.textContent||'',"
        query += "licenseRemoteActionCount:document.querySelectorAll('.license-remote-actions button').length,licenseTableHorizontalOverflow:(()=>{const n=document.querySelector('.license-inventory-wrap');return n?n.scrollWidth>n.clientWidth:false})(),"
        query += "queryTenantOptions:document.querySelectorAll('#adminQueryTenant option').length,queryButtons:document.querySelectorAll('.admin-query-workbench footer button').length,queryRunHandler:typeof document.querySelector('#adminQueryRun')?.onclick,queryColumns:document.querySelectorAll('#adminQueryHead th').length,queryRows:document.querySelectorAll('#adminQueryRows tr').length,queryHeaders:[...document.querySelectorAll('#adminQueryHead th')].map(node=>node.textContent.trim()),queryResultText:document.querySelector('#adminQueryRows')?.innerText||'',queryResultCount:document.querySelector('#adminQueryResultCount')?.textContent||'',queryStatus:document.querySelector('#adminQueryStatus')?.textContent||'',queryTenantValue:document.querySelector('#adminQueryTenant')?.value||'',queryTitle:document.querySelector('.admin-query-hero h2')?.textContent||'',querySubtitle:document.querySelector('.admin-query-hero p')?.textContent.trim()||'',"
        query += "queryModuleNav:document.querySelectorAll('[data-query-nav]').length,queryActiveModule:document.querySelector('.admin-query-nav button.active')?.dataset.queryNav||'',queryPlatformCards:document.querySelectorAll('.admin-query-platform-status > article,.admin-query-hardware').length,queryHardwareMetrics:document.querySelectorAll('.admin-query-hardware > div > div').length,queryDatabasePath:document.querySelector('.admin-query-platform-status article.database strong')?.textContent||'',queryGatewayState:document.querySelector('.admin-query-platform-status article.gateway strong')?.textContent||'',"
        query += "querySidePanels:document.querySelectorAll('.admin-query-aside > section').length,queryBackupRows:document.querySelectorAll('.admin-query-backup-table tbody tr').length,queryTelemetryRows:document.querySelectorAll('.admin-query-telemetry-table tbody tr').length,queryTelemetryColumns:document.querySelectorAll('.admin-query-telemetry-table thead th').length,queryTelemetryFirstRows:[...document.querySelectorAll('.admin-query-telemetry-table tbody tr')].slice(0,4).map(row=>[...row.cells].map(cell=>cell.textContent.trim())),queryAuditFilterCounts:[...document.querySelectorAll('.admin-query-audit-filters button')].map(button=>button.textContent.trim()),queryFiltersInHeader:document.querySelector('.admin-query-audit-filters')?.parentElement?.tagName==='DIV'&&document.querySelector('.admin-query-audit-filters')?.closest('header')!==null,queryReleaseOptions:document.querySelectorAll('#adminQueryRelease option').length,queryAuditBehavior:window.__queryAuditBehavior||{},"
        query += "backupRows:document.querySelectorAll('#backupRows tr[data-backup-row]').length,backupMetrics:document.querySelectorAll('.admin-backup-metrics article').length,backupColumns:document.querySelectorAll('.admin-backup-table-wrap thead th').length,backupRowActionButtons:[...document.querySelectorAll('#backupRows tr[data-backup-row]')].every(row=>row.querySelectorAll('button').length===1),backupMetadata:document.querySelector('.admin-backup-table-card > header > span')?.textContent||'',backupDateFilter:document.querySelector('#backupDateFilter')?.value||'',backupSearchPlaceholder:document.querySelector('#backupSearch')?.placeholder||'',backupToolbarCountDisplay:(()=>{const node=document.querySelector('#backupResultCount');return node?getComputedStyle(node).display:'missing'})(),backupTableSubtitleVisible:!!document.querySelector('.admin-backup-table-card > header p')&&getComputedStyle(document.querySelector('.admin-backup-table-card > header p')).display!=='none',backupTableWidth:(()=>{const wrap=document.querySelector('.admin-backup-table-wrap'),table=wrap?.querySelector('table');return wrap&&table?{client:wrap.clientWidth,scroll:wrap.scrollWidth,table:table.scrollWidth}:null})(),backupBehavior:(()=>{const input=document.querySelector('#backupSearch'),confirm=document.querySelector('#backupRestoreConfirm'),queue=document.querySelector('#backupRestoreQueue'),select=document.querySelector('[data-backup-select]:not([disabled])');if(!input||!confirm||!queue||!select)return null;input.value='ISIKTAS';input.dispatchEvent(new Event('input',{bubbles:true}));const filtered=document.querySelectorAll('#backupRows tr[data-backup-row]:not([hidden])').length;input.value='';input.dispatchEvent(new Event('input',{bubbles:true}));const restored=document.querySelectorAll('#backupRows tr[data-backup-row]:not([hidden])').length;const initiallyDisabled=queue.disabled;select.click();const selectedDownloadVisible=!!document.querySelector('#backupSelectedDownload')&&!document.querySelector('#backupSelectedDownload').hidden;confirm.checked=true;confirm.dispatchEvent(new Event('change',{bubbles:true}));const enabledAfterConsent=!queue.disabled;confirm.checked=false;confirm.dispatchEvent(new Event('change',{bubbles:true}));const disabledAfterConsentRemoved=queue.disabled;return {filtered,restored,initiallyDisabled,enabledAfterConsent,disabledAfterConsentRemoved,selectedDownloadVisible}})(),quotaMetricColumns:document.querySelector('.admin-quota-metrics')?getComputedStyle(document.querySelector('.admin-quota-metrics')).gridTemplateColumns.split(' ').length:0,quotaRows:document.querySelectorAll('#quotaRows tr').length,quotaMetrics:document.querySelectorAll('.admin-quota-metrics article').length,updateMetricColumns:document.querySelector('.admin-ota-metrics')?getComputedStyle(document.querySelector('.admin-ota-metrics')).gridTemplateColumns.split(' ').length:0,updateRows:document.querySelectorAll('.admin-ota-telemetry li').length,updateMetrics:document.querySelectorAll('.admin-ota-metrics article').length,updateMetricLabels:[...document.querySelectorAll('.admin-ota-metrics article small')].map(node=>node.textContent.trim()),updateMetricValues:[...document.querySelectorAll('.admin-ota-metrics article strong')].map(node=>node.textContent.trim()),otaHeroStatusCount:document.querySelectorAll('.admin-ota-hero-status article').length,otaHeroStatusValues:[...document.querySelectorAll('.admin-ota-hero-status article strong')].map(node=>node.textContent.trim()),updateTargetVersions:[...document.querySelectorAll('#otaTargetList .admin-ota-target-row code')].map(node=>node.textContent.trim()),updateTargetStates:[...document.querySelectorAll('#otaTargetList .admin-ota-target-row b')].map(node=>node.textContent.trim()),updateTargetRows:document.querySelectorAll('#otaTargetList .admin-ota-target-row').length,"
        query += "serverMetrics:document.querySelector('.admin-server-metrics')?.children.length||0,serverMetricValues:[...document.querySelectorAll('.admin-server-metric-value strong')].map(node=>node.textContent.trim()),serverMetricBadgeCount:document.querySelectorAll('.admin-server-metric header b').length,serverFields:document.querySelectorAll('.admin-server-fields label').length,serverMaintenance:document.querySelectorAll('.admin-server-maintenance button').length,errorTableMetrics:(()=>{const wrap=document.querySelector('.admin-error-table-wrap'),table=wrap?.querySelector('table'),s=table?getComputedStyle(table):null;return {wrap:wrap?.clientWidth,scroll:wrap?.scrollWidth,table:table?.getBoundingClientRect().width,minWidth:s?.minWidth,layout:s?.tableLayout}})(),errorRects:['.admin-error-hero','.admin-error-metrics','.admin-error-metrics article','.admin-error-toolbar','.admin-error-table-card','.admin-error-table-card > header','.admin-error-table-wrap','.admin-error-detail'].map(sel=>{const n=document.querySelector(sel);if(!n)return {sel,missing:true};const r=n.getBoundingClientRect();return {sel,left:Math.round(r.left),top:Math.round(r.top),width:Math.round(r.width),height:Math.round(r.height),minHeight:getComputedStyle(n).minHeight,margin:getComputedStyle(n).margin}}),errorRowSelection:(()=>{const rows=[...document.querySelectorAll('#adminTelemetryRows tr[data-telemetry-row]')];if(rows.length<2)return false;rows[1].click();const selected=document.querySelector('#adminTelemetryRows tr.selected'),ok=selected?.dataset.telemetryRow===rows[1].dataset.telemetryRow&&document.querySelector('#adminTelemetryDetail h3')?.textContent.includes('WhatsApp');document.querySelector('#adminTelemetryRows tr[data-telemetry-row]')?.click();return Boolean(ok)})(),errorRows:document.querySelectorAll('#adminTelemetryRows tr[data-telemetry-row]').length,errorDetail:document.querySelector('#adminTelemetryDetail')?.innerText||'',errorTableHeaders:[...document.querySelectorAll('.admin-error-table-wrap thead th')].map(node=>node.textContent.trim()),errorPauseLabel:document.querySelector('#adminTelemetryPause')?.textContent||'',"
        query += "selectedInspector:document.querySelector('#auditInspector')?.innerText||'',selectedAuditId:document.querySelector('#auditSelectedId')?.textContent||'',auditMetricValues:[...document.querySelectorAll('.audit-metrics article b')].map(node=>node.textContent),firstAuditRisk:document.querySelector('.audit-event .audit-risk')?.textContent||'',auditIntegrityButton:!!document.querySelector('[data-audit-integrity]'),auditIntegrityToast:integrityToast,"
        query += "topbarBottom:document.querySelector('.topbar').getBoundingClientRect().bottom,contentTop:document.querySelector('#content').getBoundingClientRect().top,contentLayout:(()=>{const n=document.querySelector('#content'),s=getComputedStyle(n),p=n.parentElement,ps=getComputedStyle(p);return {marginTop:s.marginTop,paddingTop:s.paddingTop,position:s.position,parentTag:p.tagName,parentClass:String(p.className||''),parentTop:p.getBoundingClientRect().top,parentMarginTop:ps.marginTop,parentPaddingTop:ps.paddingTop,firstChildren:[...n.children].slice(0,5).map(c=>({cls:String(c.className||'').slice(0,70),top:Math.round(c.getBoundingClientRect().top),marginTop:getComputedStyle(c).marginTop}))}})(),"
        query += "topbarRect:(()=>{const r=document.querySelector('.topbar').getBoundingClientRect(),s=getComputedStyle(document.querySelector('.topbar')),f=getComputedStyle(document.querySelector('.topbar').children[1]);return {left:Math.round(r.left),right:Math.round(r.right),width:Math.round(r.width),gap:s.gap,padding:s.padding,firstMarginLeft:f.marginLeft}})(),shellRect:(()=>{const r=document.querySelector('.app-shell').getBoundingClientRect();return {left:Math.round(r.left),right:Math.round(r.right),width:Math.round(r.width)}})(),topActions:(()=>{const box=document.querySelector('.topbar .top-actions').getBoundingClientRect();return {left:box.left,right:box.right,width:box.width,display:getComputedStyle(document.querySelector('.topbar .top-actions')).display}})(),topbarItems:[...document.querySelector('.topbar').children].map(node=>({id:node.id,cls:String(node.className||''),text:(node.innerText||'').slice(0,100),display:getComputedStyle(node).display,left:Math.round(node.getBoundingClientRect().left),right:Math.round(node.getBoundingClientRect().right),width:Math.round(node.getBoundingClientRect().width),flex:getComputedStyle(node).flex})),topActionItems:[...document.querySelector('.topbar .top-actions').children].map(node=>({id:node.id,cls:String(node.className||''),left:Math.round(node.getBoundingClientRect().left),right:Math.round(node.getBoundingClientRect().right),width:Math.round(node.getBoundingClientRect().width),flex:getComputedStyle(node).flex})),"
        query += "searchDisplay:getComputedStyle(document.querySelector('#globalSearch').closest('.global-search')).display,quickActionDisplay:getComputedStyle(document.querySelector('[data-action=quick-add]')).display,preLicenseHeader:{tab:document.body.dataset.adminTab,display:getComputedStyle(document.querySelector('.topbar > div:first-of-type')).display},headerRects:['.topbar','.topbar > div:first-of-type','#breadcrumb','.top-actions','.global-search','#notificationBtn','[data-action=quick-add]','#adminSystemMetrics','#adminServerContext','#adminProductContext','#adminHeaderUser'].map(sel=>{const node=document.querySelector(sel),rect=node?.getBoundingClientRect();return {sel,display:node?getComputedStyle(node).display:'missing',left:Math.round(rect?.left||0),top:Math.round(rect?.top||0),width:Math.round(rect?.width||0),height:Math.round(rect?.height||0),parent:node?.parentElement?.className||''}}),"
        query += "headerUserWidth:document.querySelector('#adminHeaderUser').getBoundingClientRect().width,"
        query += "toolbarTop:document.querySelector('.control-dashboard-toolbar,.audit-page-toolbar,.admin-live-hero,.license-requests-toolbar,.admin-server-hero,.admin-notification-hero,.admin-error-hero,.admin-backup-hero,.admin-quota-hero,.admin-ota-hero,.admin-query-hero,.admin-notification-layout,.admin-company-360')?.getBoundingClientRect().top,"
        query += "quotaRects:['.admin-quota-page','.admin-quota-hero','.admin-quota-metrics','.admin-quota-metrics article','.admin-quota-table-card','.admin-quota-table-card > header','.admin-quota-table-wrap','.admin-quota-bottom','.admin-quota-policy','.admin-quota-upgrade'].map(sel=>{const n=document.querySelector(sel);if(!n)return {sel,missing:true};const r=n.getBoundingClientRect(),s=getComputedStyle(n);return {sel,left:Math.round(r.left),top:Math.round(r.top),width:Math.round(r.width),height:Math.round(r.height),parent:n.parentElement?.className||'',display:s.display,flex:s.flex,direction:s.flexDirection,gap:s.gap,padding:s.padding,minHeight:s.minHeight,children:[...n.children].slice(0,6).map(c=>{const q=c.getBoundingClientRect();return {cls:String(c.className||'').slice(0,80),top:Math.round(q.top),height:Math.round(q.height),width:Math.round(q.width),scroll:c.scrollHeight}})}}),quotaPageChildren:[...document.querySelector('.admin-quota-page')?.children||[]].map(n=>{const r=n.getBoundingClientRect();return {cls:String(n.className||'').slice(0,80),top:Math.round(r.top),height:Math.round(r.height),width:Math.round(r.width),parent:n.parentElement?.className||''}}),"
        query += "queryTraceText:document.querySelector('.admin-query-trace')?.innerText||'',queryTraceLines:document.querySelectorAll('.admin-query-trace-lines p').length,queryRects:['.admin-query-page','.admin-query-nav','.admin-query-platform-status','.admin-query-platform-status > article.database','.admin-query-hardware','.admin-query-platform-status > article.gateway','.admin-query-hero','.admin-query-workspace','.admin-query-primary','.admin-query-workbench','.admin-query-results','.admin-query-aside','.admin-query-update','.admin-query-backups','.admin-query-telemetry','.admin-query-telemetry > header','.admin-query-audit-heading','.admin-query-audit-filters','.admin-query-audit-tools','.admin-query-telemetry-table','.admin-query-telemetry-table table','.admin-query-trace'].map(sel=>{const n=document.querySelector(sel);if(!n)return {sel,missing:true};const r=n.getBoundingClientRect();return {sel,left:Math.round(r.left),top:Math.round(r.top),width:Math.round(r.width),height:Math.round(r.height)}}),"
        query += "queryHardwareDetails:[...document.querySelectorAll('.admin-query-hardware > div > div > small')].map(node=>node.textContent.trim()),queryHardwareValues:[...document.querySelectorAll('.admin-query-hardware > div > div > b')].map(node=>node.textContent.trim()),queryNavScrollbar:(()=>{const n=document.querySelector('.admin-query-nav');return n?getComputedStyle(n).scrollbarWidth:''})(),"
        query += "metricsColumns:getComputedStyle(document.querySelector('.audit-metrics')||document.querySelector('.control-kpi-primary')||document.querySelector('.admin-live-metrics')||document.querySelector('.license-request-metrics')||document.querySelector('.admin-server-metrics')||document.querySelector('.admin-error-metrics')||document.querySelector('.admin-backup-metrics')||document.querySelector('.admin-quota-metrics')||document.querySelector('.admin-ota-metrics')||document.querySelector('.admin-query-page')||document.querySelector('.admin-notification-layout')||document.querySelector('.admin-company-kpis')).gridTemplateColumns,"
        query += "liveRows:document.querySelectorAll('.admin-live-company').length,"
        query += "liveSessionRows:document.querySelectorAll('.admin-live-session').length,liveDatabaseRows:document.querySelectorAll('.admin-live-database').length,"
        query += "liveSessionText:document.querySelector('.admin-live-session')?.innerText||'',liveUserIds:[...document.querySelectorAll('.admin-live-session')].map(node=>node.dataset.userId),liveDatabaseText:document.querySelector('.admin-live-database')?.innerText||'',livePingValues:[...document.querySelectorAll('.admin-live-facts > div:first-child strong')].map(node=>node.textContent),liveAveragePing:document.querySelector('.admin-live-metrics article:nth-child(2) strong')?.textContent||'',liveLatencyRows:document.querySelectorAll('.admin-live-latency-row').length,duplicateGateway:document.querySelectorAll('.admin-live-reference-subtitle').length,"
        query += "liveHeroRects:['.admin-live-hero','.admin-live-hero-actions','.admin-live-stream','.admin-live-hero-actions button'].map(sel=>{const n=document.querySelector(sel);if(!n)return {sel,missing:true};const r=n.getBoundingClientRect(),s=getComputedStyle(n);return {sel,left:Math.round(r.left),top:Math.round(r.top),width:Math.round(r.width),height:Math.round(r.height),display:s.display,columns:s.gridTemplateColumns,gridColumn:s.gridColumn,widthStyle:s.width}}),"
        query += "notificationRects:['.admin-notification-layout','.admin-notification-hero','.admin-notification-hero-badges','.admin-notification-hero-badges article:first-child','.admin-notification-hero-actions','.admin-notification-composer','.admin-notification-head','.admin-notification-form','.admin-notify-section','.admin-notify-section-heading','.admin-notify-section-heading > label','#notifyTargetSummary','.admin-notify-audience','.admin-notify-audience button','.admin-notify-firm-pool','#notifyFirmList','.admin-notify-firm','.admin-notify-types','.admin-notify-type','#notifyTitle','#notifyBody','.admin-notification-side','.admin-notify-preview-card','.admin-notify-history-card'].map(sel=>{const n=document.querySelector(sel);if(!n)return {sel,missing:true};const r=n.getBoundingClientRect(),s=getComputedStyle(n);return {sel,left:Math.round(r.left),top:Math.round(r.top),width:Math.round(r.width),height:Math.round(r.height),minHeight:s.minHeight,padding:s.padding,gap:s.gap,margin:s.margin,gridAutoRows:s.gridAutoRows,lineHeight:s.lineHeight}}),"
        query += "notificationHeroActions:(()=>{const title=document.querySelector('#notifyTitle'),body=document.querySelector('#notifyBody'),template=document.querySelector('#notifyTemplateBtn'),logs=document.querySelector('#notifyLogsBtn'),history=document.querySelector('.admin-notify-history-card');if(!title||!body||!template||!logs||!history)return {};title.value='Temporary draft';body.value='Temporary body';template.click();const templateRestored=title.value.startsWith('Acil Sistem G')&&body.value.startsWith('De\u011ferli AYEC Pro')&&document.querySelector('.admin-notify-preview')?.dataset.previewType==='danger';let historyOpened=false;const original=history.scrollIntoView;history.scrollIntoView=()=>{historyOpened=true};logs.click();if(original)history.scrollIntoView=original;else delete history.scrollIntoView;return {templateRestored,historyOpened}})(),"
        query += "notificationTitle:document.querySelector('#notifyTitle')?.value||'',notificationDraftBody:document.querySelector('#notifyBody')?.value||'',notificationDraftType:document.querySelector('.admin-notify-preview')?.dataset.previewType||'',notificationBody:!!document.querySelector('#notifyBody'),notificationTypes:document.querySelectorAll('.admin-notify-type').length,notificationHistory:!!document.querySelector('#notifyHistoryList'),notificationHistoryRows:document.querySelectorAll('.admin-notify-history-row').length,notificationLatestTitle:document.querySelector('.admin-notification-hero-badges article:nth-child(2) strong')?.textContent||'',notificationLatestTime:document.querySelector('.admin-notification-hero-badges article:nth-child(2) small')?.textContent||'',notificationPreviewHeading:document.querySelector('.admin-notify-preview-card > header h3')?.textContent||'',notificationPreviewScale:document.querySelector('.admin-notify-preview-card > header small')?.textContent||'',notificationHeroTitle:document.querySelector('.admin-notification-hero h1')?.textContent||'',notificationHeroBadges:document.querySelectorAll('.admin-notification-hero-badges article').length,notificationOnlineSummary:document.querySelector('.admin-notification-hero-badges article:first-child strong')?.textContent||'',notificationTenantLabels:[...document.querySelectorAll('.admin-notify-firm-copy small')].map(node=>node.textContent.trim()),notificationTargetSummary:document.querySelector('#notifyTargetSummary')?.textContent||'', notificationBehavior:(()=>{const title=document.querySelector('#notifyTitle'),body=document.querySelector('#notifyBody');if(!title||!body)return {};title.value='Planned Window';title.dispatchEvent(new Event('input',{bubbles:true}));body.value='Restart after saving active work.';body.dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('[data-notify-type=warning]')?.click();document.querySelector('[data-notify-audience=selected]')?.click();const firm=document.querySelector('[data-notify-tenant]');if(firm){firm.checked=true;firm.dispatchEvent(new Event('change',{bubbles:true}))}const result={title:document.querySelector('#notifyPreviewTitle')?.textContent||'',body:document.querySelector('#notifyPreviewBody')?.textContent||'',type:document.querySelector('.admin-notify-preview')?.dataset.previewType||'',titleCount:document.querySelector('#notifyTitleCount')?.textContent||'',targetSummary:document.querySelector('#notifyTargetSummary')?.textContent||''};document.querySelector('[data-notify-audience=all]')?.click();return result})(),"
        query += "serverTlsBadge:document.querySelector('.admin-server-tls')?.textContent.trim()||'',"
        query += "notificationFirmRects:[...document.querySelectorAll('.admin-notify-firm')].map(node=>{const r=node.getBoundingClientRect(),s=getComputedStyle(node);return [Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height),s.flex,s.width]}),"
        query += "companyListRows:document.querySelectorAll('[data-company360-id]').length,companyUserRows:document.querySelectorAll('.admin-company-table-wrap tbody tr').length,companyTitle:document.querySelector('#company360Detail h1')?.textContent||'',companyFieldCount:document.querySelectorAll('.admin-company-info-grid article').length,"
        query += "companyStateActions:window.__company360Behavior||{},"
        query += "workspaceColumns:getComputedStyle(document.querySelector('.audit-workspace')||document.querySelector('.control-dashboard-grid')||document.querySelector('.admin-live-lower')||document.querySelector('.license-request-grid')||document.querySelector('.admin-server-layout')||document.querySelector('.admin-notification-layout')||document.querySelector('.admin-company-360-grid')||document.querySelector('.admin-error-page')||document.querySelector('.admin-backup-page')||document.querySelector('.admin-quota-page')||document.querySelector('.admin-ota-page')||document.querySelector('.admin-query-page')).gridTemplateColumns,"
        expected_screen_selectors = {
            "dashboard": ".control-dashboard-toolbar",
            "audit": ".audit-page-toolbar",
            "live-status": ".admin-live-hero",
            "license-requests": ".license-requests-title",
            "server-settings": ".admin-server-hero",
            "notifications": ".admin-notification-hero",
            "tenants": ".admin-company-360-head",
            "error-telemetry": ".admin-error-hero",
            "backup-restore": ".admin-backup-hero",
            "quota-limits": ".admin-quota-hero",
            "staged-update": ".admin-ota-page",
            "database-query": ".admin-query-hero",
        }
        expected_selector = json.dumps(expected_screen_selectors[args.screen])
        query += "expectedScreenVisible:(()=>{const node=document.querySelector(%s),rect=node?.getBoundingClientRect();if(!node||!node.closest('#adminTabContent')||!rect||rect.width<=0||rect.height<=0)return false;for(let current=node;current&&current!==document.body;current=current.parentElement){const style=getComputedStyle(current);if(style.display==='none'||style.visibility==='hidden'||Number(style.opacity)===0)return false}return rect.right>0&&rect.bottom>0&&rect.left<innerWidth&&rect.top<innerHeight})(),otaGeometry:(()=>[document.querySelector('.admin-ota-hero'),document.querySelector('.admin-ota-metrics'),document.querySelector('.admin-ota-metrics article'),document.querySelector('.admin-ota-grid')].map(node=>{const rect=node?.getBoundingClientRect();return rect?{top:Math.round(rect.top),height:Math.round(rect.height)}:null}))()})})()" % expected_selector
        query = "(()=>{try{return " + query + "}catch(error){return JSON.stringify({captureError:String(error),stack:error.stack,activeAdminTab:window.activeAdminTab,adminContentText:document.querySelector('#adminTabContent')?.innerText.slice(0,600)||''})}})()"

        def report(value):
            if args.screen == "database-query":
                saved[0] = view.grab().save(str(output))
            try:
                state = json.loads(value or "{}")
            except json.JSONDecodeError:
                state = {"state": value}
            if state.get("expectedScreenVisible") is False and capture_retries[0] < 6:
                capture_retries[0] += 1
                QTimer.singleShot(350, finish_capture)
                return
            if not render_waited[0]:
                render_waited[0] = True
                QTimer.singleShot(250, lambda: report(value))
                return
            view.update()
            view.repaint()
            app.processEvents()
            saved[0] = view.grab().save(str(output))
            state.update({"saved": bool(saved[0]), "output": str(output)})
            expected_metric_columns = 1 if args.screen == "server-settings" and args.width <= 760 else 2 if args.screen in ("server-settings", "tenants") and args.width <= (1150 if args.screen == "server-settings" else 1080) else (1 if args.screen in ("license-requests", "notifications") else 2) if args.width <= 760 else 2 if args.screen == "notifications" else 5 if args.screen == "server-settings" else 4
            if args.screen == "dashboard":
                expected_metric_columns = 1 if args.width <= 639 else 2 if args.width <= 1023 else 4
            if args.screen == "live-status":
                expected_metric_columns = 1 if args.width <= 639 else 2 if args.width <= 1279 else 4
            if args.screen == "server-settings":
                expected_metric_columns = 1 if args.width <= 767 else 2 if args.width <= 1279 else 5
            if args.screen == "notifications":
                expected_metric_columns = 1 if args.width <= 1023 else 2
            if args.screen == "tenants":
                expected_metric_columns = 2 if args.width <= 767 else 4
            if args.screen == "error-telemetry":
                expected_metric_columns = 1 if args.width <= 767 else 2 if args.width <= 1023 else 4
            if args.screen == "backup-restore":
                expected_metric_columns = 1 if args.width <= 639 else 2 if args.width <= 1023 else 4
            if args.screen == "backup-restore" and args.width <= 639:
                expected_metric_columns = 1
            if args.screen in ("database-query", "error-telemetry") and args.width <= 760:
                expected_metric_columns = 1
            if args.screen == "database-query":
                expected_metric_columns = 1
            if args.screen == "staged-update":
                expected_metric_columns = 1 if args.width <= 767 else 2 if args.width <= 1023 else 4
            if args.screen == "quota-limits":
                expected_metric_columns = 1 if args.width <= 767 else 2 if args.width <= 1279 else 4
            if args.screen == "audit":
                expected_metric_columns = 1 if args.width <= 639 else 2 if args.width <= 1023 else 4
            if args.screen == "license-requests":
                expected_metric_columns = 1 if args.width <= 760 else 2 if args.width <= 1100 else 4
            metric_columns = str(state.get("metricsColumns", "")).split()
            checks = {
                "encoding": state.get("encoding") == "UTF-8",
                "system_font_fallbacks": "Segoe UI" in state.get("fontFamily", "") and "Arial" in state.get("fontFamily", ""),
                "reference_typography": "Plus Jakarta Sans" in state.get("adminFontFamily", "") and state.get("adminFontLoaded") is True,
                "reference_color_tokens": state.get("adminTokens") == {"surface": "#161b2a", "surface2": "#1a1f2e", "text": "#dee2f6", "muted": "#c2c6d6", "line": "#424754", "primary": "#adc6ff"},
                "no_horizontal_overflow": state.get("document") == state.get("viewport"),
                "content_below_header": state.get("toolbarTop", 0) >= state.get("topbarBottom", 0),
                "reference_header_height": reference_header_height is not None and state.get("topbarBottom") == reference_header_height,
                "reference_header_surface": state.get("topbarBackground", "").replace(" ", "") == ("rgba(22,27,42,0.95)" if args.screen == "license-requests" else "rgba(9,14,28,0.9)"),
                "reference_header_effects": state.get("topbarBackdropFilter", "").replace(" ", "") == "blur(24px)" and state.get("topbarBorderWidth") == ("0px" if args.screen == "license-requests" else "1px") and state.get("topbarShadow", "").replace(" ", "") == ("rgba(0,0,0,0.25)0px1px8px0px" if args.screen == "license-requests" else "rgba(0,0,0,0.04)0px1px8px0px" if args.screen in ("staged-update", "quota-limits", "server-settings", "backup-restore") else "rgba(0,0,0,0.25)0px4px16px0px"),
                "reference_header_search_height": reference_search_height is None or next((rect.get("height") for rect in state.get("headerRects", []) if rect.get("sel") == ".global-search"), None) == reference_search_height,
                "header_user_width": state.get("headerUserWidth", 0) <= (132 if args.width >= 761 else 32),
                "metric_columns": len(metric_columns) == expected_metric_columns,
                "screen": state.get("activeTab") == ("telemetry" if args.screen == "error-telemetry" else args.screen),
                "screen_content_visible": state.get("expectedScreenVisible") is True,
                "no_capture_dialogs": state.get("openDialogs") == [],
                "no_dashboard_shortcut_overlay": state.get("shortcutOverlayOpen") is False,
                "capture_saved": bool(saved[0]),
                "single_source_reference": (DESIGN_REFERENCE_ROOT / f"{DESIGN_REFERENCE_FILES[args.screen]}.html").is_file() and (DESIGN_REFERENCE_ROOT / f"{DESIGN_REFERENCE_FILES[args.screen]}.md").is_file(),
            }
            if args.width <= 760:
                checks["mobile_header_actions"] = state.get("searchDisplay") == "flex" and state.get("quickActionDisplay") == "none" and state.get("headerRects", [{}])[3].get("width", 0) > 0
                checks["mobile_reference_breadcrumb"] = all(part in state.get("crumbText", "") for part in ("Sistem", "Y\u00f6netim", "Konsolu"))
            if args.screen == "notifications":
                checks["notification_form_and_reference_panels"] = state.get("notificationTitle") == "Acil Sistem G\u00fcncellemesi v2.0.2: L\u00fctfen A\u00e7\u0131k Fi\u015flerinizi Kaydediniz!" and state.get("notificationDraftBody") == "De\u011ferli AYEC Pro kullan\u0131c\u0131s\u0131, SQLite WAL motorunda y\u00fcksek h\u0131zl\u0131 optimizasyon ve entegre WhatsApp fi\u015f bildirim \u015fablonlar\u0131n\u0131 i\u00e7eren v2.0.2 kritik yama haz\u0131rland\u0131. Veri g\u00fcvenli\u011finiz i\u00e7in l\u00fctfen \u00e7al\u0131\u015fma formlar\u0131n\u0131z\u0131 kaydedip program\u0131 yeniden ba\u015flat\u0131n." and state.get("notificationDraftType") == "danger" and state.get("notificationBody") and state.get("notificationTypes") == 5 and state.get("notificationHistory") and state.get("notificationHistoryRows") == 3
                checks["notification_terminal_counts"] = state.get("notificationOnlineSummary") == "4 Firma / 18 Terminal \u00c7evrimi\u00e7i" and state.get("notificationTenantLabels") == ["3 Uc Nokta", "3 Uc Nokta", "5 Uc Nokta", "7 Uc Nokta"] and state.get("notificationTargetSummary") == "2 Firma (6 Uc Nokta) Secili"
                checks["notification_reference_hero"] = state.get("notificationHeroTitle") == "Merkezi Bildirim & Anl\u0131k Mesaj G\u00f6nderimi" and state.get("notificationHeroBadges") == 2
                checks["notification_reference_activity"] = state.get("notificationLatestTitle") == "v2.0.1 Pilot G\u00fcncelleme Da\u011f\u0131t\u0131m\u0131" and state.get("notificationLatestTime") == "14/10 08:00" and state.get("notificationHistoryRows") == 3
                checks["notification_preview_header"] = state.get("notificationPreviewHeading") == "\u0130stemci Masa\u00fcst\u00fc \u00d6nizlemesi" and state.get("notificationPreviewScale") == "1920x1080 \u00d6L\u00c7EK"
                checks["notification_hero_actions"] = state.get("notificationHeroActions", {}).get("templateRestored") and state.get("notificationHeroActions", {}).get("historyOpened")
                behavior = state.get("notificationBehavior", {})
                checks["notification_preview_bindings"] = behavior.get("title") == "Planned Window" and behavior.get("body") == "Restart after saving active work." and behavior.get("type") == "warning" and behavior.get("titleCount") == "14/120 Karakter" and behavior.get("targetSummary", "").startswith("2 Firma (") and "Uc Nokta" in behavior.get("targetSummary", "")
                checks["notification_layout_columns"] = len(str(state.get("workspaceColumns", "")).split()) == (1 if args.width <= 1023 else 2)
                firms = state.get("notificationFirmRects", [])
                if args.width >= 1400:
                    checks["notification_firm_chip_flow"] = len(firms) == 4 and firms[0][1] == firms[1][1] and firms[2][1] > firms[1][1] and firms[0][0] == firms[2][0] == firms[3][0]
                elif args.width <= 760:
                    checks["notification_mobile_firm_stack"] = len(firms) == 4 and len({rect[1] for rect in firms}) == 4
                if args.width == 390:
                    rects = {rect.get("sel"): rect for rect in state.get("notificationRects", [])}
                    checks["notification_mobile_reference_geometry"] = rects.get(".admin-notification-hero", {}).get("top") == 60 and rects.get(".admin-notification-hero", {}).get("height") == 274 and rects.get(".admin-notification-hero-badges article:first-child", {}).get("top") == 243 and rects.get(".admin-notification-hero-badges article:first-child", {}).get("width") == 270 and rects.get(".admin-notification-hero-actions", {}).get("top") == 300 and rects.get(".admin-notification-hero-actions", {}).get("height") == 34 and rects.get(".admin-notification-composer", {}).get("top") == 350 and rects.get(".admin-notification-head", {}).get("height") == 130 and rects.get(".admin-notify-audience", {}).get("top") == 525 and rects.get(".admin-notify-audience", {}).get("height") == 60 and rects.get(".admin-notify-firm-pool", {}).get("top") == 602 and rects.get(".admin-notify-firm-pool", {}).get("height") == 214 and rects.get("#notifyFirmList", {}).get("top") == 637 and rects.get("#notifyFirmList", {}).get("height") == 167
                if args.width >= 1400:
                    rects = {rect.get("sel"): rect for rect in state.get("notificationRects", [])}
                    checks["notification_reference_geometry"] = rects.get(".admin-notification-layout", {}).get("top") == 56 and rects.get(".admin-notification-layout", {}).get("height") == 1188 and rects.get(".admin-notification-composer", {}).get("top") == 172 and rects.get(".admin-notification-composer", {}).get("height") == 1072 and rects.get(".admin-notification-form", {}).get("top") == 250 and rects.get(".admin-notification-form", {}).get("height") == 993 and rects.get(".admin-notify-preview-card", {}).get("top") == 172 and rects.get(".admin-notify-preview-card", {}).get("height") == 428 and rects.get(".admin-notify-history-card", {}).get("top") == 616 and rects.get(".admin-notify-history-card", {}).get("height") == 549
            elif args.screen == "dashboard":
                checks["dashboard_binding"] = len(state.get("metricValues", [])) >= 9 and state.get("companyRows") == 4 and state.get("auditRows") == 6 and "%30.3" in state.get("metricValues", []) and state.get("diskProgress") == "30.3%" and "Tenant" in state.get("metricBadges", []) and "0 kuyrukta" in state.get("metricBadges", []) and str(state.get("chartLine", "")).count(" L ") >= 10
                checks["dashboard_shortcut_bindings"] = state.get("controlActionDisabledCount") == 0 and state.get("controlActionRoutes") == ["license-requests", "backup-restore", "notifications", "server-settings"]
                footer = state.get("auditFooter", "")
                checks["dashboard_reference_footer"] = len(footer) > 40 and "WebSocket Sync: Aktif" in footer
                checks["dashboard_performance_panel"] = state.get("performanceBackground") == "rgba(37, 42, 57, 0.4)"
                checks["dashboard_performance_average"] = state.get("performanceAverage") == "Ortalama: 12.4ms" and state.get("performanceCurrent") == "\u015eimdi (12ms)"
                checks["workspace_columns"] = len(str(state.get("workspaceColumns", "")).split()) == (1 if args.width <= 1023 else 2)
                if args.width >= 1400:
                    rects = {rect.get("sel"): rect for rect in state.get("dashboardRects", [])}
                    checks["dashboard_reference_geometry"] = rects.get(".control-dashboard-toolbar", {}).get("top") == 56 and rects.get(".control-dashboard-toolbar", {}).get("height") == 56 and rects.get(".control-kpi-primary", {}).get("top") == 124 and rects.get(".control-kpi-secondary", {}).get("top") == 244 and rects.get(".control-kpi-secondary", {}).get("height") == 106 and rects.get(".control-dashboard-grid", {}).get("top") == 362 and rects.get(".control-audit-panel", {}).get("height") == 567 and rects.get(".control-dashboard-aside", {}).get("height") == 634
            elif args.screen == "audit":
                checks["audit_binding"] = state.get("rows") == 6 and state.get("selectedAuditId") == "#AUD-9942" and "Olay Aciklamasi" in state.get("selectedInspector", "")
                checks["audit_reference_risk_binding"] = state.get("auditMetricValues", [None, None])[1] == "0 Risk" and state.get("firstAuditRisk") == "D\u00fc\u015f\u00fck Risk"
                checks["integrity_control"] = state.get("auditIntegrityButton") is True
                checks["integrity_action"] = "5 bağlantı doğrulandı" in state.get("auditIntegrityToast", "")
                checks["workspace_columns"] = len(str(state.get("workspaceColumns", "")).split()) == (1 if args.width <= 1023 else 2)
            elif args.screen == "license-requests":
                checks["invite_metrics"] = state.get("metricValues", []) == ["48", "12", "34", "2"]
                checks["invite_weekly_binding"] = state.get("licenseMetricDetails", [])[0] == "+6 Bu Hafta"
                checks["request_and_inventory_binding"] = state.get("licenseRequestCards") == 2 and state.get("licenseInventoryRows") == 4
                checks["license_telemetry_binding"] = state.get("licenseTelemetry") == ["ONLINE (11ms)", "ONLINE (14ms)", "ONLINE (19ms)", "UYARI (88ms)"]
                checks["license_reference_header"] = state.get("licenseTitle") == "Lisans & Yetki Da\u011f\u0131t\u0131m \u0130stasyonu" and state.get("licenseHsmBadge") == "HSM-VAULT v2.5" and state.get("licenseInviteButton") is True and state.get("licenseQueueTitle") == "Gelen Lisans Talepleri & Canl\u0131 Sipari\u015fler"
                checks["license_remote_action_bindings"] = state.get("licenseRemoteActionCount") == state.get("licenseInventoryRows", 0) * 3
                if args.width >= 1400:
                    checks["license_table_fits_desktop_content"] = state.get("licenseTableHorizontalOverflow") is False
                checks["invite_navigation"] = state.get("licenseInviteNavigates") is True
                checks["workspace_columns"] = len(str(state.get("workspaceColumns", "")).split()) == (1 if args.width <= 1100 else 2)
            elif args.screen == "server-settings":
                checks["server_metrics_and_controls"] = state.get("serverMetrics") == 5 and state.get("serverFields") == 6 and state.get("serverMaintenance") == 4
                checks["server_reference_metrics"] = state.get("serverMetricValues") == ["%3", "%52", "%30", "1.07 MB", "1.4 MB/s"] and state.get("serverMetricBadgeCount") == 5
                checks["server_tls_status_binding"] = state.get("serverTlsBadge") == "SSL: TLS 1.3"
                checks["workspace_columns"] = len(str(state.get("workspaceColumns", "")).split()) == (1 if args.width <= 1279 else 2)
            elif args.screen == "tenants":
                checks["company_detail_binding"] = state.get("companyListRows") == 4 and state.get("companyTitle") == "ASLAN TIC" and state.get("companyUserRows") == 2 and state.get("companyFieldCount") == 6
                behavior = state.get("companyStateActions", {})
                sector_write = behavior.get("sectorWrite") or {}
                checks["company_search_and_status_filters"] = behavior.get("searchMatches") == 1 and behavior.get("inactiveRows") == 0
                checks["company_sector_submission"] = sector_write.get("path") == "/api/control/tenant" and sector_write.get("method") == "POST" and sector_write.get("body", {}).get("tenant_id") == "tenant-1" and sector_write.get("body", {}).get("sector") == "otomotiv"
                checks["workspace_columns"] = len(str(state.get("workspaceColumns", "")).split()) == (1 if args.width <= 1279 else 2)
            elif args.screen == "database-query":
                checks["query_workbench"] = state.get("queryTenantOptions") == 4 and state.get("queryButtons") == 3 and state.get("queryTitle") == "Salt Okunur SQL Teşhis Sorgulayıcı"
                checks["query_reference_copy"] = state.get("querySubtitle") == "Güvenli SELECT & EXPLAIN sorguları çalıştırır (Yazma işlemleri kilitlidir)"
                checks["query_module_navigation"] = state.get("queryModuleNav") == 8 and state.get("queryActiveModule") == "database-query"
                checks["query_platform_status"] = state.get("queryPlatformCards") == 3 and state.get("queryHardwareMetrics") == 3 and bool(state.get("queryDatabasePath")) and bool(state.get("queryGatewayState"))
                checks["query_hardware_reference_values"] = state.get("queryHardwareValues") == ["3.2%", "52.4%", "30.3%"] and state.get("queryHardwareDetails") == ["4 \u00c7ekirdek @ 2.40 GHz", "4.1 GB / 8.0 GB", "30.0 GB / 99.0 GB"]
                checks["query_update_backup_telemetry"] = state.get("querySidePanels") == 2 and state.get("queryBackupRows") == 2 and state.get("queryTelemetryRows", 0) >= 4 and state.get("queryReleaseOptions") == 2
                checks["query_audit_filter_and_search"] = state.get("queryAuditBehavior") == {"allRows": 6, "securityRows": 1, "passwordRows": 1}
                checks["query_telemetry_reference_columns"] = state.get("queryTelemetryColumns") == 6 and state.get("queryFiltersInHeader") is True
                checks["query_reference_trace_console"] = state.get("queryTraceLines") == 4 and "TCP Socket accepted from 192.168.1.108:52410" in state.get("queryTraceText", "") and "Token verification payload" in state.get("queryTraceText", "") and "WAL checkpoint triggered" in state.get("queryTraceText", "") and "Health check report queued" in state.get("queryTraceText", "")
                checks["query_telemetry_reference_data"] = [row[2:4] for row in state.get("queryTelemetryFirstRows", [])] == [["AUTH_OK", "INFO"], ["BACKUP_CREATED", "AUDIT"], ["SYNC_OK", "TELEMETRY"], ["QUOTA_CHECK", "METRIC"]] and state.get("queryAuditFilterCounts") == ["TÜMÜ 324", "ERROR 0", "WARN 2", "AUDIT 48", "SECURITY 12"]
                checks["query_result_binding"] = state.get("queryHeaders") == ["id", "username", "role", "last_login", "disk_usage_mb"] and "enginmamu22" in state.get("queryResultText", "") and state.get("queryResultCount") == "3 satır / 5 sütun" and state.get("queryRows") == 3
                checks["workspace_columns"] = len(str(state.get("workspaceColumns", "")).split()) == 1
                query_rects = {rect.get("sel"): rect for rect in state.get("queryRects", [])}
                query_page_rect = query_rects.get(".admin-query-page", {})
                query_header_rect = query_rects.get(".admin-query-telemetry > header", {})
                checks["query_telemetry_fits_content"] = query_header_rect.get("left", 0) + query_header_rect.get("width", 0) <= query_page_rect.get("left", 0) + query_page_rect.get("width", 0)
                if args.width >= 1280:
                    rects = query_rects
                    checks["query_desktop_reference_geometry"] = rects.get(".admin-query-nav", {}).get("top") == 56 and rects.get(".admin-query-nav", {}).get("height") == 48 and rects.get(".admin-query-platform-status", {}).get("top") == 116 and rects.get(".admin-query-platform-status", {}).get("height") == 92 and rects.get(".admin-query-hero", {}).get("top") == 220 and rects.get(".admin-query-hero", {}).get("height") == 96 and rects.get(".admin-query-workbench", {}).get("top") == 316 and rects.get(".admin-query-workbench", {}).get("height") == 199 and rects.get(".admin-query-results", {}).get("top") == 515 and rects.get(".admin-query-workspace", {}).get("height") == 412 and rects.get(".admin-query-update", {}).get("top") == 220 and rects.get(".admin-query-update", {}).get("height") == 213 and rects.get(".admin-query-backups", {}).get("top") == 445 and rects.get(".admin-query-backups", {}).get("height") == 188 and rects.get(".admin-query-telemetry", {}).get("top") == 644 and rects.get(".admin-query-telemetry", {}).get("height") == 434 and rects.get(".admin-query-telemetry > header", {}).get("top") == 656 and rects.get(".admin-query-telemetry > header", {}).get("height") == 53 and rects.get(".admin-query-telemetry-table", {}).get("top") == 717 and rects.get(".admin-query-telemetry-table", {}).get("height") == 219 and rects.get(".admin-query-trace", {}).get("top") == 944 and rects.get(".admin-query-trace", {}).get("height") == 122
                if args.width == 390:
                    rects = {rect.get("sel"): rect for rect in state.get("queryRects", [])}
                    checks["query_mobile_reference_geometry"] = state.get("queryNavScrollbar") == "none" and rects.get(".admin-query-nav", {}).get("top") == 64 and rects.get(".admin-query-nav", {}).get("height") == 48 and rects.get(".admin-query-platform-status", {}).get("top") == 132 and rects.get(".admin-query-platform-status", {}).get("height") == 338 and rects.get(".admin-query-platform-status > article.database", {}).get("height") == 84 and rects.get(".admin-query-hardware", {}).get("top") == 220 and rects.get(".admin-query-hardware", {}).get("height") == 145 and rects.get(".admin-query-platform-status > article.gateway", {}).get("top") == 379 and rects.get(".admin-query-platform-status > article.gateway", {}).get("height") == 91 and rects.get(".admin-query-hero", {}).get("top") == 480
            elif args.screen == "backup-restore":
                checks["backup_bindings"] = state.get("backupRows") == 5 and state.get("backupMetrics") == 4 and state.get("backupColumns") == 7 and state.get("backupRowActionButtons") is True and "4 / 5" in state.get("backupMetadata", "")
                checks["backup_reference_defaults"] = state.get("backupDateFilter") == "7" and "cihaz ara" in state.get("backupSearchPlaceholder", "") and state.get("backupToolbarCountDisplay") == "none" and state.get("backupTableSubtitleVisible") is False
                behavior = state.get("backupBehavior") or {}
                checks["backup_filter_and_restore_gate"] = behavior.get("filtered") == 1 and behavior.get("restored") == 5 and behavior.get("initiallyDisabled") is True and behavior.get("enabledAfterConsent") is True and behavior.get("disabledAfterConsentRemoved") is True and behavior.get("selectedDownloadVisible") is True
                checks["workspace_columns"] = len(str(state.get("workspaceColumns", "")).split()) == 1
            elif args.screen == "quota-limits":
                checks["quota_bindings"] = state.get("quotaRows") == 4 and state.get("quotaMetrics") == 4 and state.get("metricValues", [])[0] == "3.77 MB / 100 GB" and state.get("metricValues", [])[1] == "8 / 40 Koltuk" and state.get("metricValues", [])[2] == "24 / 400 Cihaz" and state.get("metricValues", [])[3] == "412 / 4,000 Fi\u015f"
                checks["quota_metric_responsive_columns"] = state.get("quotaMetricColumns") == (1 if args.width <= 767 else 2 if args.width <= 1279 else 4)
                checks["quota_filters"] = state.get("quotaBehavior") == {"searchCount": 1, "packageCount": 2}
                quota_copy = state.get("quotaCopy", {})
                checks["quota_reference_copy"] = quota_copy.get("title") == "Kota & Limit Kontrol\u00fc (SaaS Multi-Tenant)" and quota_copy.get("subtitle") == "Kirac\u0131 firmalar\u0131n veritaban\u0131 boyutlar\u0131, kullan\u0131c\u0131 say\u0131lar\u0131, kay\u0131tl\u0131 cihaz ve servis formu kotalar\u0131n\u0131 anl\u0131k denetleyin ve limit a\u015f\u0131m kurallar\u0131n\u0131 y\u00f6netin." and quota_copy.get("tableTitle") == "Kirac\u0131 Firma Kota ve Kaynak T\u00fcketim Tablosu" and quota_copy.get("policyTitle") == "Otomatik Limit A\u015f\u0131m Politikalar\u0131 (Soft & Hard Limit)" and quota_copy.get("upgradeTitle") == "Se\u00e7ili Firma \u0130\u00e7in H\u0131zl\u0131 Kota Y\u00fckseltme Masas\u0131" and quota_copy.get("upgradeAmount") == "\u20ba 750,00 +KDV/ay"
                checks["quota_reference_table_headers"] = quota_copy.get("tableHeaderTransform") == "uppercase" and quota_copy.get("tableHeaders") == ["Kirac\u0131 Firma / Paket", "DB Boyutu (Kullan\u0131m / Limit)", "Kullan\u0131c\u0131 Kotas\u0131", "Kay\u0131tl\u0131 Cihaz", "Ayl\u0131k Servis Formu", "Durum", "Y\u00f6netim"]
                checks["quota_policy_and_upgrade_controls"] = quota_copy.get("policyInputs") == [True, True, True] and state.get("quotaPolicyToggle") is True and "Global politika ayarlar\u0131 senkronizedir" in quota_copy.get("policyFooter", "") and "\u0130stisna Listesini Y\u00f6net" in quota_copy.get("policyFooter", "") and quota_copy.get("upgradePrices") == ["\u20ba 450 / Ay", "\u20ba 300 / Ay", "\u20ba 200 / Ay"]
                quota_rects = {rect.get("sel"): rect for rect in state.get("quotaRects", [])}
                if args.width >= 1280:
                    checks["quota_reference_geometry"] = quota_rects.get(".admin-quota-hero", {}).get("top") == 76 and quota_rects.get(".admin-quota-hero", {}).get("height") == 94 and quota_rects.get(".admin-quota-metrics", {}).get("top") == 182 and quota_rects.get(".admin-quota-metrics", {}).get("height") == 132 and quota_rects.get(".admin-quota-table-card", {}).get("top") == 326 and quota_rects.get(".admin-quota-table-card", {}).get("height") == 393 and quota_rects.get(".admin-quota-bottom", {}).get("top") == 731 and quota_rects.get(".admin-quota-bottom", {}).get("height") == 310
                else:
                    policy_rect = quota_rects.get(".admin-quota-policy", {})
                    upgrade_rect = quota_rects.get(".admin-quota-upgrade", {})
                    checks["quota_responsive_panels"] = policy_rect.get("top", 0) + policy_rect.get("height", 0) + 11 <= upgrade_rect.get("top", 0) and quota_rects.get(".admin-quota-bottom", {}).get("height", 0) >= policy_rect.get("height", 0) + upgrade_rect.get("height", 0) + 11
                checks["workspace_columns"] = len(str(state.get("workspaceColumns", "")).split()) == 1
            elif args.screen == "staged-update":
                checks["update_bindings"] = state.get("updateRows", 0) >= 1 and state.get("updateMetrics", 0) >= 3
                checks["update_hero_status_bindings"] = state.get("otaHeroStatusCount") == 3 and state.get("otaHeroStatusValues") == ["v2.0.0", "v2.0.1-rc3", "API eri\u015filebilir"]
                checks["update_pilot_success_binding"] = state.get("updateMetricLabels", [])[1] == "PILOT TEST BA\u015eARISI" and state.get("updateMetricValues", [])[1] == "%50"
                checks["update_metric_responsive_columns"] = state.get("updateMetricColumns") == (1 if args.width <= 767 else 2 if args.width <= 1023 else 4)
                checks["update_target_matrix"] = state.get("updateTargetRows") == 4 and state.get("updateTargetVersions") == ["v2.0.1 Pilot", "v2.0.0", "v1.9.0", "v2.0.0"] and state.get("updateTargetStates") == ["G\u00fcncel & Aktif", "Bekliyor", "Kritik G\u00fcncelleme", "Bekliyor"]
                if args.width >= 1280:
                    geometry = state.get("otaGeometry") or []
                    checks["update_reference_vertical_geometry"] = len(geometry) == 4 and geometry[0] == {"top": 56, "height": 135} and geometry[1] == {"top": 210, "height": 128} and geometry[2] == {"top": 210, "height": 128} and geometry[3].get("top") == 357
                checks["workspace_columns"] = len(str(state.get("workspaceColumns", "")).split()) == 1
            elif args.screen == "error-telemetry":
                checks["error_log_binding"] = state.get("errorRows") == 5 and len(state.get("metricValues", [])) == 4 and state.get("errorDetail") and "database is locked" in state.get("errorDetail", "")
                checks["error_row_selection"] = state.get("errorRowSelection") is True
                checks["reference_table_columns"] = len(state.get("errorTableHeaders", [])) == 7
                table_metrics = state.get("errorTableMetrics", {})
                checks["error_table_fits_desktop"] = args.width < 1280 or (table_metrics.get("table", 0) <= table_metrics.get("wrap", 0) and table_metrics.get("scroll", 0) <= table_metrics.get("wrap", 0))
                checks["workspace_columns"] = len(str(state.get("workspaceColumns", "")).split()) == 1
            else:
                checks["live_status_binding"] = state.get("liveRows") == 4 and state.get("liveSessionRows") == 4 and state.get("liveDatabaseRows") == 4 and state.get("liveUserIds", [])[0] == "7" and "192.168.1.108" in state.get("liveSessionText", "") and "aslan.db" in state.get("liveDatabaseText", "") and state.get("companyRows") == 0 and state.get("liveFilterBehavior") == {"slowCount": 1, "restoredCount": 4}
                checks["live_latency_binding"] = state.get("livePingValues") == ["11ms", "14ms", "92ms", "18ms"] and state.get("liveAveragePing") == "16ms" and state.get("liveLatencyRows") == 4
                checks["live_action_bindings"] = state.get("liveActionCount") == 13 and state.get("liveActionDisabledCount") == 0 and state.get("liveActionRoutes") == ["audit", "backup", "diagnostics", "message", "ping"]
                behavior = state.get("liveActionBehavior", {})
                checks["live_action_behavior"] = behavior.get("diagnosticsOpened") is True and behavior.get("messageTenant") == "tenant-1" and behavior.get("notificationTab") == "notifications" and behavior.get("notificationTargets") == ["tenant-1"]
                checks["live_reference_header"] = state.get("duplicateGateway") == 0
                checks["workspace_columns"] = len(str(state.get("workspaceColumns", "")).split()) == (1 if args.width <= 900 else 2)
            state["checks"] = checks
            capture_ok.append(all(checks.values()))
            print(json.dumps(state, ensure_ascii=True))
            app.quit()

        if args.screen == "database-query":
            page.runJavaScript("(()=>{const tenant=document.querySelector('#adminQueryTenant'),button=document.querySelector('#adminQueryRun');if(tenant&&!tenant.value)tenant.value='tenant-1';button?.onclick?.();return true})()", lambda _result: QTimer.singleShot(500, lambda: page.runJavaScript(query, report)))
        else:
            page.runJavaScript(query, report)

    def wait_for_setup(attempt=0):
        if attempt >= 240:
            QTimer.singleShot(150, finish_capture)
            return
        def after_setup(done):
            if not done:
                QTimer.singleShot(50, lambda: wait_for_setup(attempt + 1))
                return
            page.runJavaScript(
                "new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(()=>setTimeout(resolve,250))))",
                lambda _value: QTimer.singleShot(100, finish_capture),
            )
        page.runJavaScript("window.__captureSetupDone===true", after_setup)

    def loaded(ok):
        if not ok:
            print(json.dumps({"error": "Web view failed to load."}))
            app.quit()
            return
        page.runJavaScript(setup, lambda _result: QTimer.singleShot(50, wait_for_setup))

    page.loadFinished.connect(loaded)
    view.load(QUrl.fromLocalFile(str(ROOT / "Web_Arayuzu" / "web" / "index.html")))
    view.show()
    app.exec()
    return 0 if capture_ok and capture_ok[0] else 1


if __name__ == "__main__":
    raise SystemExit(main())


