"""AYEC Pro masaustu uygulamasinin yerel web sunucusu ve SQLite koprusu."""

from __future__ import annotations

import argparse
import base64
import binascii
import csv
import hashlib
import hmac
import html
import io
import importlib.util
import json
import logging
import mimetypes
import os
import re
import secrets
import shutil
import smtplib
import socket
import sqlite3
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import unicodedata
import zipfile
import zlib
from contextlib import closing
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie
from pathlib import Path, PureWindowsPath
from urllib.parse import parse_qs, unquote, urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web"
DIALOGS_MANIFEST = WEB_ROOT / "dialogs.generated.json"
_default_download_root = Path("C:/Downloads") if os.name == "nt" else ROOT / "downloads"
DOWNLOAD_ROOT = Path(
    os.environ.get("AYEC_DOWNLOADS_DIR", str(_default_download_root))
).expanduser().resolve()
_configured_db = os.environ.get("AYEC_DB_PATH", "").strip()
DB_PATH = (
    (ROOT / _configured_db).resolve()
    if _configured_db and not Path(_configured_db).is_absolute()
    else Path(_configured_db).expanduser().resolve()
    if _configured_db
    else Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "AYEC Pro" / "ayecpro.db"
)
# The registry database remains the compatibility entry point.  Operational
# data is routed to one database per company under this directory.
TENANT_ROOT = Path(
    os.environ.get("AYEC_TENANT_DIR", str(ROOT / "Kullan\u0131c\u0131lar"))
).expanduser().resolve()
DEMO_TEMPLATE_PATH = Path(
    os.environ.get("AYEC_DEMO_TEMPLATE", str(ROOT / "data" / "demo_template.db"))
).expanduser().resolve()

SESSION_COOKIE = "ayec_session"
PASSWORD_ITERATIONS = 310_000
VENDOR_NAME = os.environ.get("AYEC_VENDOR_NAME", "AYEC Pro").strip() or "AYEC Pro"
# Platform ownership must never be taken from a machine environment variable.
# It is limited to the AYEC legacy and official mail identities below.
VENDOR_EMAIL = "ayecpro@gmail.com"
OFFICIAL_EMAIL = "info@ayecpro.com"
SUPPORT_EMAIL = "destek@ayecpro.com"
PRODUCT_CATALOG_PATH = (ROOT.parent / "ecosystem" / "products.json").resolve()
if not PRODUCT_CATALOG_PATH.is_file():
    PRODUCT_CATALOG_PATH = ROOT / "ecosystem" / "products.json"


def configured_product_codes() -> set[str]:
    """Load the single product registry shared with Admin_Konsol."""
    try:
        payload = json.loads(PRODUCT_CATALOG_PATH.read_text(encoding="utf-8"))
        codes = {str(item.get("code") or "").strip().lower() for item in payload.get("products", ())}
        return {code for code in codes if code}
    except (OSError, ValueError, TypeError):
        return {"teknik_servis", "ciro", "elek", "barkod_okuyucu"}
OFFICIAL_WEBSITE = "https://www.ayecpro.com"


def is_platform_owner_email(email: str | None) -> bool:
    return str(email or "").strip().casefold() == VENDOR_EMAIL
VENDOR_PHONE = os.environ.get("AYEC_VENDOR_PHONE", "05348781047").strip()
PUBLIC_SERVER_URL = os.environ.get("AYEC_PUBLIC_URL", "https://panel.ayecpro.com").strip().rstrip("/")
SERVICE_TRACKING_URL = os.environ.get("AYEC_SERVICE_TRACKING_URL", "https://ayecpro.com/servis/takip").strip().rstrip("/")
SERVICE_TRACKING_SECRET = os.environ.get("AYEC_TRACKING_SECRET") or os.environ.get("AYEC_SECRET_KEY") or "ayecpro-development-tracking-secret"
SUPPORT_BACKUP_ROOT = Path(
    os.environ.get("AYEC_SUPPORT_BACKUP_DIR", str(ROOT / "support_backups"))
).expanduser().resolve()
# Stable product archive used by the Barkod Okuyucu desktop client.  The
# tenant-scoped support_backups tree remains the registry/source of truth;
# this mirror provides the requested operator-friendly folder layout.
PROGRAM_BACKUP_ROOT = Path(
    os.environ.get("AYEC_PROGRAM_BACKUP_ROOT", r"C:\AYECPro Programlar")
).expanduser().resolve()


def product_backup_root(product_code: str) -> Path | None:
    wanted = str(product_code or "").strip().lower()
    try:
        payload = json.loads(PRODUCT_CATALOG_PATH.read_text(encoding="utf-8"))
        item = next((row for row in payload.get("products", ()) if str(row.get("code") or "").lower() == wanted), None)
    except (OSError, ValueError, TypeError):
        item = None
    if not item:
        return None
    return (PROGRAM_BACKUP_ROOT / str(item.get("folder_name") or wanted) / str(item.get("backup_folder") or (wanted + "-AYEC"))).resolve()
try:
    SUPPORT_BACKUP_KEEP = max(3, min(100, int(os.environ.get("AYEC_SUPPORT_BACKUP_KEEP", "7"))))
except (TypeError, ValueError):
    SUPPORT_BACKUP_KEEP = 7
_SCHEMA_LOCK = threading.Lock()
_SCHEMA_READY_PATHS: set[str] = set()
_TENANT_LOCAL = threading.local()
_AUTH_LOCK = threading.Lock()
_AUTH_FAILURES: dict[str, list[float]] = {}
_GOOGLE_NONCES: dict[str, float] = {}
_GOOGLE_REGISTRATION_LOCK = threading.Lock()
PROVISION_RATE_WINDOW_SECONDS = 3600
PROVISION_RATE_MAX_ATTEMPTS = 5
TRIAL_DAYS = 15
LICENSE_PAYMENT_BANK = os.environ.get("AYEC_LICENSE_BANK", "Vak\u0131fBank").strip() or "Vak\u0131fBank"
LICENSE_PAYMENT_HOLDER = os.environ.get("AYEC_LICENSE_HOLDER", "Engin ASLAN").strip() or "Engin ASLAN"
LICENSE_PAYMENT_IBAN = os.environ.get("AYEC_LICENSE_IBAN", "TR66 0001 5001 5800 7321 0690 01").strip()
LICENSE_PLAN_DEFAULTS = (
    ("monthly", "Ayl\u0131k Esnek", 1, 790.0),
    ("six_months", "6 Ayl\u0131k Avantaj", 6, 3990.0),
    ("one_year", "1 Y\u0131ll\u0131k Profesyonel", 12, 6990.0),
    ("two_years", "2 Y\u0131ll\u0131k \u0130\u015fletme", 24, 11990.0),
    ("three_years", "3 Y\u0131ll\u0131k Kurumsal", 36, 15990.0),
)
logger = logging.getLogger(__name__)


class SyncEventHub:
    """Deliver small sync notifications over authenticated WebSocket sessions."""

    def __init__(self):
        self._clients: dict[str, set[tuple[socket.socket, str]]] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _frame(payload: dict) -> bytes:
        raw = json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
        size = len(raw)
        if size <= 125:
            return bytes([0x81, size]) + raw
        if size <= 65535:
            return bytes([0x81, 126]) + size.to_bytes(2, "big") + raw
        return bytes([0x81, 127]) + size.to_bytes(8, "big") + raw

    def register(self, tenant_id: str, connection: socket.socket, device_id: str) -> None:
        with self._lock:
            self._clients.setdefault(tenant_id, set()).add((connection, device_id))

    def unregister(self, tenant_id: str, connection: socket.socket) -> None:
        with self._lock:
            clients = self._clients.get(tenant_id, set())
            self._clients[tenant_id] = {
                item for item in clients if item[0] is not connection
            }
            if not self._clients[tenant_id]:
                self._clients.pop(tenant_id, None)

    def publish(self, tenant_id: str, payload: dict, source_device_id: str = "") -> None:
        with self._lock:
            clients = list(self._clients.get(tenant_id, set()))
        frame = self._frame(payload)
        failed: list[socket.socket] = []
        for connection, device_id in clients:
            if source_device_id and device_id == source_device_id:
                continue
            try:
                connection.sendall(frame)
            except OSError:
                failed.append(connection)
        for connection in failed:
            self.unregister(tenant_id, connection)


SYNC_EVENT_HUB = SyncEventHub()

TABLES = {
    "customers", "customer_currency_balances", "customer_notes", "customer_services",
    "devices", "used_parts", "parts", "stock_movements", "services", "service_definitions",
    "appointments", "reminders", "accounting", "currency_transactions", "offers", "offer_items",
    "personnel", "announcements", "contracts", "bank_accounts", "bank_cards", "loans",
    "checks_notes", "e_invoices", "projects", "project_units", "project_transactions",
    "loaner_devices", "loaner_transactions", "logistics", "external_warranty_tracking",
    "vehicle_maintenance_cards", "vehicle_maintenance_items", "customer_vehicles",
    "automotive_service_forms", "automotive_checklist_results", "automotive_damage_records",
    "automotive_checkup_forms", "automotive_quote_forms", "automotive_quote_items",
    "automotive_delivery_forms", "automotive_vehicle_history_events",
    "automotive_warranty_campaigns", "automotive_tire_suspension_records",
    "automotive_battery_electrical_tests", "automotive_maintenance_templates",
    "automotive_maintenance_template_items", "automotive_parts_requests",
    "automotive_parts_request_items", "automotive_damage_marks", "vehicle_maintenance_photos",
    "device_brands", "knowledge_base", "kb_articles", "audit_logs", "settings", "exchange_rates",
    "internal_settings", "notifications", "scheduled_alerts", "quick_notes",
    "product_groups",
    "users", "tickets", "company_info", "photos", "logs",
}

# Compressed CREATE TABLE/INDEX baseline from the desktop database.  The web
# server may be pointed at a brand-new SQLite file (for example after an IIS
# deployment).  Authentication alone only needs ``users``; the application
# shell, however, immediately reads operational tables such as ``customers``.
# Keeping the complete idempotent desktop schema here makes first start and
# upgrades self-healing instead of depending on a pre-populated database file.
_OPERATIONAL_SCHEMA_B64 = "eNrtPUtz20aa5/WvQKVqi3IVJ+NkZw7JnGSZTmliyx6Jno1PqCbRJDvEy3jIpv/A/oO56pjr6JLT3CT/r/26gW40gH6BBGVN7fqQiECjn9/71WeXs9P5zJufPn81885fehdv5t7sl/Or+ZWHlsukjAsSr72TJ17nHwm884v57KfZpff28vz16eV77+fZe+/03fzN+cXZ5ez17GI+7X1V7FLszWe/zKfeH/7g/YRDkk29n0iAs17TJSrwOsl2TfOXqCgzNPVeI/TlZupdoeL+lv7xM8mQd734ttcFiuj8PVjhK8VUsp2PP5TkGoVY22hZZhmOl9UkvBezl6fvXs29yfzy/aTfGH9ablC8xn4GU2cdii+++/ZZv32SkTWJUegb5xngfJmRtCBJXG1FvwUdTv1qmWF4Gfio0DUo8yKJcOY352loFKNINxLJfRJfJ2SJG8Dgq1esPUW7CLbdj3CxSQJNnwsUb/0aCo0TzHBYLdOhbZolv+KluU2RoeUW4N6PE83UMrzSv8xxCCPAfHKcXcOO5Kxdq9mUziMoYR51G3k+vXcS2sA+B9B9odxmr37Fz/vpX56cmfC7INcYuqvmuCeOe9X3Emx4m4+kOlLv3cX5397Npl6I8sIPEwD3/lZYJhnHcKRLTKHlgDkKFIG9JYB4xU5zdgUpQt50mcQFpQ3VL1QCqGb8VRuxxBmcvbu8hBH9+fnr2dX89PXbIUtNUz9ECxyq1kn/bfGu2WZ5uVNl8wCvUBkWPlC4Uoe2DZFzaCdT5IYY/hQmCxROdHOwUS/6r0yDPXbTaUcTEhcHwc5e1DDdJDEeTq4Lou3RvpF5Afwx7xzOc7wNyS7JJoyD8l9Tb44iFIUoDu5vp979P9MChTbm0aVfOMuTOMYhxyv+W6YEFW2ofywyGK/+O0oC8SVQOQJckJNTr8zWgudSJAwF1jF45s/rY+j8bNNRMSf5qURN46SoqTNMIymzNq2tn1BaL38PJBhoQeLX+9OnwxagzHMCZwUIB6OTFQG0gkPdn7ZFOM/Rms+5mb6KRQMIFTBgqOIdSvgpY1hkMDFLFhw7x6GCZUAYrxgPY8u8got6h9AibLErygc5VgHEFoiEuZrMD1oGgGPCGOwCFQWm0iaVCjK6/T5AHaVIbgd8jTdkGbYlhJrptsC6K7SID9OwYX98MtdJWFCoaYmpAAUgwmZr2ouuAYBJBj34ErhMvY8oi+lHIVlvCv4wWQT+EvA8VyCbM/+cujMH5wNZbvByW6b+Kski51Po7bgQbvobryRGqmNUnVCBI/bTB3bPCVEZRUioQmz6IdAQ/9dcwG2Gl0kEjC6AnSLQRS6//Kq7HQCrAaUIFrDdf7NN4G3b0Bz0SxnfPwNvln9/6sH4rveEzr4N8hSaH8X2ghJ9TTH6cUIz/gTUPAngeyAaKrazKoE9h/ga/kvbcoKS0P1ugb1YqLTz9TPY0CLpPULFYzifCBGqRaCYyhYctRmGup5V81XTnI518e7VK5BG4LW/zpIy5RoifcD0CP4Axs9AuAdM3OWqIxANtpFaqaz0CB34v3xzOTv/6YJO/USa61NAopcz2LWzmXVD8hPa/s0FDPtqBnt6dnp1dvpidtAmO+9vo1I1uyrW0RcHG7LMdPFKJlXtKoiJTMPuvfzuK4NkChw8B7H2QwliyDBYFB+pQJH2KxPWD0WHkMLCEwDORtKPgTgsk7zo0VsNeDXD66CrtbZDward2ajM6yCimpdpGpKWCuq1sBN/SisLlGT44Hv3WBjXhxIm8ki5VjU30RdK0yyhBLK1yeKpzJBIXpkgJZtuS3ouF0UCynbvBXuq++oRnNMgKtEcrYFnyUZN+ttCOBitSDNqTuhuT3UQCk38O0G0XXhXa9Y6+iJB7YHEhRt3awxQGsb2RQu+1Rw/lJ3vjzPK7lR4xJ9dE66K4Bi0S8z0QoNBEMfUPWMSG21ypbJbWdakI3CzklIERcslTgsmUkiaq9oyqtLIZL2npYzxTeb0w3X22+vt1vRRv2eQhT7x5bCvm9/qdRyBzqhHkvFOgG8L52q3hBrJhtqBG6wrSAaoV+YpjnOSxD7Vm7NgbFuMUq9nI5PP/PcqS4BPhHhVgBSZFpseWasaZNSkomkBx5WZemDvTR2gkKxj5ohrEcgFChnctx7mm2QJ8LfIk2zRtf8sMrTF/gYwoPHYPhpzDz+Meno+IHp8mPVNSSf3Nsmx+cjsUPZBtXXgFO3CBAV72Xac9+sjyjIUFzt/iaIUAYA8BHbwseR9EM90Yi6zRcoyLo5bIi+lgjS44FFApOzNHs+2zXptGbMr+XOThM3CCbTqvI/LaMHf9zuF819uJCZtDIQwarrWkAThfqyJTo9GDfJ4D7DQs51bIkb89xe+lF9qAhcaCVjjX80Ck1NRtKHe9D9ZG5GI9DQJo/83wAu3D4KSWnV3ZnGQIirz2tubDoKfYXKKVfjoHFVLBGlh7CiCCBMU81qeHBvq2sFVd/+Dt1PvCse4UB8iiCOy44vGY5GMfLnxTk7D+9sYxU+n0Mn97ZZGWXknf8cZCXH8VNlZmmTFKglJog+KsQZkNZBVmDCA5HkpCBtM+mf85QZo/JJ4f/SeJ9ndb2Gp/A5WS1LShHPAp3Sdy/tb7+Q5+QxMaYfgxL/cbFF+f/tUj9cWDK1pp6WVIMOJTa0wN3GLr1C6dt/SM7v7fRfgKjig+U3DAzY5Cb1ZQMKATL0zkiXix90/AmCz8MfPKPtyc38Lm7iFHftM4whQgNWHxlShFIEIOoL2MRTpEhAj4p1P4lUyXhRI3anCeNyPQ2SRQyD5B34VkbBH1AiOEAk171AQZDjXKagF+uQnq5WIw1A2MIoDYbJOTIc3LBZA4Z+XBKxRYwloABeI4McI/mmJ+bK8bhZJFXBUTVGWe9VWLiUSn24Lspo4hAsdJWKNS4U+LCHOqziK8fmaU4xqbdDis/ANcTBOnKgl8GqMVL14X920HCKN3Ym5PTjVKfJXlvzUove3z7Ti2pBQ347E5Z1I59kSt/hzJmoNpfHC9NXosfhTURl5HgIi3UyuCs3X2E7YTY2tpMA6Yzsp6M7YbodR5tCsMuWOYk48LCrULuU7gdzh0j0fRdDFGrHyB4VAB4JmaatRxZVtWWh3fVQGWBhOAdT9VNgl99AYJ/YmGjp9bDwZwZIJM7mAGYAYPvnvDSry0zSlf1+9vqL/O0NhOFHKDUKZGZ73MRg5nuyxrSL94UF3tp9QYQJh3tqgr30oUVzQjAEH64TeS9mHAIPHt9fY5IFyzP8ZV7LmJ1Hg5SZmMa18Jx8h261t0BaZsG5l46Z1Mxsz/T/L/Grx4DHwvEbMcoMTXYZCIxAJ4ccCS7WbW6LyzMksxzzEeVoZ4HwXq1fTmmYNLOUPui9XxCb3fwC8TbaYq4aMhW/j5GM82KMuu1Qe2ox7rKwhgRej8a09M4VMNp+2/PCcZHiX43Dq/VxmZZQrsnmolYcEJhNQspd5yZIlRJf3vUjl6djMpl6xbHyjXTtUz3JFo6toAoXwHIk0Pi/GZL1ZJNkm4dmkHjTFmDf9TFLZnSWDLUB7pA2NZV4UbTBXlIMSRNNJlKFHgA9plsDbCAHGKnuHF0UZ9G09YQL0Q/lGkRJKA/9JXkUz9DKPn42aMiqzyPEJvBubtvHn45GhgXSEL6eKHR0rg95q/SlYkKee4gAuN1l0LAv/7reCmfNDlg04h++ZsT/C1MrP/CJ3v4d3v939K4I13d/gjCjlU+18mIRIUGyasGBnT4Zu8PH2VisruKSAOkiTDpJkJzey976KzG/XSugrJXJCpSlvVMGCWCCeQTiBsyMRaocaK3LuXRQiO/qTCBPdECyvLfbDZLm11TowjNC0MbHLxtADWjhaFsbDsVt1gUkWRgdLvTMpyvOPSaablSpKuZ0JjCM86TBopUMjRMBK1YH5GU4Ryfx2mmQXxT0RQtQJyBHPlVN8n2wnnQT95uVFkkU0zbzKVonrsGsRzgNz1UQHN8GZrdiho8Q60tCLdeKvcH8aIn1J4tw0xDTPYbVNEnLN3jO84s4gARyynJ0tN+Ray9C7CVBuobnCTCwl07BQEhk0+ASruGo5L7uV60lzP1u6QaOitCPaBNDW6QnytMU76t5n8o14VTsgfJqdvGse87IiJgxg/m4WPiyrUOPJSJh7R0ZMYC67BTUo3z5/7s3m84v+GPXeCEBrtuDqdH5+NVHJBEtMgcYsN9Rtrrc6Qmb0qinP5MXl6ct5FX/A/px6sLx3sxdT74pFFJ6+fXv55u/09+Xsr7OzOf3r5en5q9mLPhUNViYaSkMm6YmjRvJ5D7Cw9ZIQZWjrre9+j4MqxsX769Wbi38fL3fLD3kMs8sAx0G5o/KTxSEKimro0AyvVrguUWM2jki0SApNPHv9fOIk8A8U66l9k/Efwcy43DgavgsW1w8gBrB9ffevLzfQgHizCMWg4l4k+xUpqasMGZqItfbN5IwESThzRVvkf3yvKOXV74WvxqO9VF+C/rG7v4XFlMAdaAiWQhaOCxMoJGWxAPoT+BUT1srMJHZq1pIW2v/EpLH3LkRwGFRvehOj7P42CtBUWYzMZMHfv8zECtUZfSM6WczKhJxZ/OQg3TsgOQgkOx8kWpXBccAuCHzJcUHr1ak2g6ftmusmNTWQBgz/K6KwYC3ncjgppv9a5V60rSw2FHs5GO1nw8rEjOCIcjuD7QKE4kLneHBMtNfW/irQ+vCSMCGQvjjHB8UhgkK+zHYpnUCTh847Nhx6PyztU0pamn3lBahCTqWnopYbT1GtB8sPQtgwQVSYB915oyvOdRimsAGc/UQrIlcEcmksBE2XxhZktGUXlinL+akOZR/Jsxd/Ue9OyxtIn43jCax6jwHkwvAxnK40Fcrt3T5q+eQsbfuefItbMiPxkqTwDS0w4PIFY3DUTOr6wXYL2pDSbaGL6lvk0fWwLywF59RLRySwifMDLDOD1Ha7p/z4eIEzQ73NB/OeSCZnCxzV9ucILQe40dWaPk6TAOnKRCIS7vwUgwwH+pTCfKYeZ4PDlTkM1pq5fSTfT33WR42L1qf9W+InXDmd+MDkpB4QkpzEAWEmQNDUnNoZo18pFfHXoGvEe0UPiBIpGS7KzDpQ1coY4sjBF7HiLIEbCA8J6h839c3TJN63ydRolO/BsiyrgAh0fxPe33pJGJT3NyVri7wNztFCYVlQ5HZVndCPUEBTxHbMVrgg4Zo83S+jQPBwW7oAjUeIQP3Y5NYMy6ywMdNKNqnt4gfnHpjAlWXU0T+n3nNSRISWZtdUlj2M8k4r+U9h3p6jbQ46HJnwJpJCxyQiZXwEk3yOHTlBi1/noJ8eIe3Tjfg6GASt3uDKPMQ8XCSLTFBnibQcSQAcTIbWDxmIAcOZpDGzIYfWrB3dWuhioTrAUdC7sWHykjA3IotmL5Ilde9O5jximD3d5QWOJmogarBXJycYQuDZCRCg6cJ+AROitZZooEDAXnn42/W33jc5ndmP333/X99MvW8o3fjxT3+mf3KU+fGHH75xp4bcFMbWL35M+P+553ai0wxVvu+Y+75pn+LHZEPWG/p/bsabWLFpX+sBnX2rg4GYl6xWNMSgqiE2MtjVfTtbA2itMVsmYadAmU41utYn1brzVFs8m6IYmtpM5J56UOMGKIuqWnQaxb1becaqTfODaUmX7OE4UmXV1ZHgyRYC5pyOMoT59gNktYQPmR13tX+P3XRiaaYodWr0A9tqt4l2+S5aJOGgBFobjOvKJ2oqXFS1GJ0aX6NCKQNqGzsm7ggZ3E0drNfn0+J0Q9bo/EEzdedPhs1IyRSDDK2KidV7r4Fjc2DHAOr0SBMOWJnZB0k2aBfoVXiJaPSk4eokzlwU7+AQNyjHjhxo0MVaBoKzAHlK/1Z3Yw2OcdgNhIxI7LfWL9r/eaoop1DbHuV0hW4YJ6t1LCUdNDUAWpW1KM0vyILnZ+dOEWm9KlqNFGGBNXFtywPAG1ViGmOjjpVawlqzJNwneSZHIXIgWU3yRE/7pzVxMhJ5CWwtNQH959PhebbGsi2aSIn/6ECmnCMTYIrDkeSZBhhZZyjiao7l9CmIfi0ThDXMuWkkBZnomMxaTp+uKldNqmSFyf0/v9yEOq3yWMYFHk3F7IgRSlNNHMphO91WTIapOtakf8fb9irVpor53QYq09n3z8xfWUKMxmfVxloCYk+nfMeeDj97Jmkf1d3jcnFh2/ZmvWNTbbV5jcLPOMLUevvl5u43EpKtdNvmHH25wRmQS1oHLMI5sVnDHTTL3lWQdBoXaEuKaWWEn7JydvvYEg+wa7NCZzQJqjK8iJ+iBNreHm56oxi7hqpZLT9dqsXnrE48rwyVZLm2E6vi6e5KV95G2jw1FgAdevNp11LQgHbLVlA/HsdaIG+wXxPr8ZGU9e6en95DadsHVIC3HXpbynfp0aLRDymA4eJ0R0EwTmWDerdVQFMhkhpyHiFAgrSKvx7L6ECtNrbfbsGqGhVLaxNbSEHVyiQ+N63MCeoVF6iTr2yZBPQY/AynB4SUsFQzdzssHXJA84BWaeAs09lg1fpqAG/O6AGwm/2GlITiA6UhMsZVJMuyig88mhh4ME4fjQYdQCy+Hp1Y0OxaGwlYhUmSmTVBtmfGFkqBjMmgtNxsJZCJn1PvEn/G2TWuxVSRxx6C9l6VrdV52xwhmk3YVlISQNUQYNFxzxijNSytlDm7YkNg8bsceVt6l3DOnxwgGw+QIUGYoHjfZSfV2rekNlBJMYGIZHjyqNjx+MjlKok5hfNYqslWPDFY42J/W/0LfI0Y2ohro+UnbldHHwG6FGFAygR1hTop1bymxcLjiSbtXeGmY1qWsL5ZMq8P0ZGaQsDCQGaG1w8lYcXBx0z9YtdImui7yS437BYIZ8u8eRcyTMOqMhbRsndOzaoMW7eWm6RORQ0jSZSlbpA0yaWscpA6WUEulxSrgsVa91J15DXuVScFpDhC8zQfMvjJHN1kqXhGcpbY77Jn5vJTcgBg98J6aYcV7h19oKN5r/PlBgdlSGcU4uwI7IR162wCBpBar6lGRtyYEDFVtNJ9MTSNkGWa1TMzRlQfKP3X9t1mx4badXNMzW8gj+EcH+Eo6+4t8vQW7+yRHnSCfpO8atwPadip6H341lSp3A9Sb3vPCw7HrbbNi6VvI3tQmDWW5tEUBz3+5Xt8SwK8IjE5jm+kV57AetWS1QE1wCRT1vLHoV6IY7km+e6MGv/M080GhkEzd+1ZLWhPvCQTAcEExdVvXUywWaSwuuJFRPWT4Tv3kFWO9yR2bul/tnpy9J+qSNf/k7HRi5k7BMaMH0plJ0RWPDIGJikG1N/PN22Fb9m2n1f2UBbykAp3WPqJckoHj6cJtdTBFsnyio+EXpGWi4wEVtFmeBoHC1N7GMmr43B0I0XtuDe1HUsVC6ePie7Hxz1yelTvW9tcScM8x6FFDACi5Bofp76Ck5uZDz/gqiVrNXH8sY7BdJK79hGqtErsAJpmo2sOB9gK7/hq/hxXcfnXZNER4WYh3oIGTwOD7m+v0dR7nuyQsu5V49YQFs4BEMFTHVjNnMfrJhx4/AVZbvH+Id9q6zXAFJ2htoSsk4nrzdvZhaEG65vL16evJg6X+nZI6QDmBmJ64Osi4h8kTHV4jI1NgxwnrKYdYu/nMUrzTTLkjl9HIdFmV61ktxGTo6lqNmK11DGizk0+AENEupXbWIr1P1HaSmnyeKwtyxphmoQg3+ihuoE0qXsxl+1iZvJ6gnnXcN4iN12nSY5h7YXPivhKRKZ6iuL8o8iT0HqJqhIJK0TV64Beu8DKI/dnbAYmXRnj8emJ6rr7Q3IC3QuumAo6y5fY7H/zn+Kim/6lNur4j8d70c3Q222E6bKZQgy6Vgu0LOuJUFzSoNo0TeCbqF3C1FM/VovRUtPGmyMo+bMffnz2bDK1RqdxX2CrKju9dA7692V9VCP20kS+1mpadeNJvKU3AbiaBqtwOfmbFirVtHSx+7dQ+RpqoLxlS9yLtcftpiqSdpxk+k6990Yv2CPzpAkWkLoBZkKLMAzwL1KewIrAq67o+eHZtGmxjZyvraJY3KZGzbOhVGIb+WoMsiJj65a2audbsKNlZaNoIarej5QgpgerTlKYLVq9mx02pub38CfwES8AYmphq73nw/eaMTofFISNQ6k+KiPb0w66m6tuxUrJ4tzSigmyOcaxpR2XZ23Yx1aA1uoCMCQ1BIW3onfzfokKpo1Yztdyrpwc8NoKcLpumr0sDErlbZrhzi9ezH7plr8OPvHEPcpuOceh028et66BHNIdI5HtruijQX1QvqHqqMq6c+yuETpy1hf3T9EupXdsdty84dBtY0ZfsDuEdj6orkt6zxytekAv7/IlPKCD2b84ab4YNANWfrlMfcoiDcO2mu07VoAiQB+gbNnWMJTcau+RePaFZVntdvuOJpNqgX/6QZXN9x2b2a34VTaGQdvt9h3tQwnyhW1TpUb7jlMAeffzEnSvuDJc4GUCLFA/puaDfcfnTHhDgIJRbLtmNEA7vLr9vqMLd/gSRSki69gwcr/toFHFzaPcslYZB2AM6a5e8bLiFkN67ffm1kPtR6/jeyW6yx3s1RPZJtgKlnYfQeZdvPNBjKvbkVhzr7dhSw8YF5f6aW7Gk4XQAR3WxE7uU766S7qjyr1T3cm49yDuspH6kBR5e0dy4XeqTtGOehXhT7juNbA/2pG6Q166e1h/zX71e3TduXa93E6XUiHdgf0VnySbSNObXGJAinoZ0Gtvgq0uXWdZFV/rUMK6uNsQdOD9SGZTqSMV5lfqjLbDxlot/ADQoXh6wp/apyaHzTXGLC7Fym9P+havYUShcXq1ELB5PAwHFd2Jeav7HDZdWW/1q5tEaNfy45NGKxzYH4vT6/bG9bS//C+Rw8dC"


def packaged_source_root() -> Path:
    """Return the self-contained engine root, with a development fallback."""
    if (ROOT / "src" / "utils" / "stock_import_parser.py").is_file():
        return ROOT
    development_root = ROOT.parent
    if (development_root / "src" / "utils" / "stock_import_parser.py").is_file():
        return development_root
    return ROOT


def ensure_packaged_source() -> Path:
    """Make the stock/PDF engine importable and return its resolved root."""
    source_root = packaged_source_root()
    root_text = str(source_root)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    return source_root


def runtime_status() -> dict:
    source_root = ensure_packaged_source()
    tesseract_path = shutil.which(os.environ.get("TESSERACT_CMD", "tesseract")) or ""
    status = {
        "python": sys.version.split()[0],
        "database": str(active_db_path()),
        "packaged_source": (source_root / "src" / "utils" / "stock_import_parser.py").exists(),
        "packaged_source_root": str(source_root),
        "tesseract": tesseract_path,
        "ocr_backends": {
            "tesseract": bool(tesseract_path),
            "easyocr": importlib.util.find_spec("easyocr") is not None,
            "paddleocr": importlib.util.find_spec("paddleocr") is not None,
        },
    }
    try:
        import reportlab
        import pypdf
        status.update({"pdf": True, "reportlab": getattr(reportlab, "Version", ""), "pypdf": getattr(pypdf, "__version__", "")})
    except Exception as error:
        status.update({"pdf": False, "pdf_error": str(error)})
    try:
        import PIL
        import pandas
        import pdfplumber
        status.update({"smart_import": True, "pillow": getattr(PIL, "__version__", ""), "pandas": pandas.__version__, "pdfplumber": pdfplumber.__version__})
    except Exception as error:
        status.update({"smart_import": False, "smart_import_error": str(error)})
    return status


def parse_xlsx(payload: bytes) -> list[dict]:
    """Read the first XLSX worksheet with only the standard library."""
    with zipfile.ZipFile(io.BytesIO(payload)) as book:
        shared = []
        if "xl/sharedStrings.xml" in book.namelist():
            root = ElementTree.fromstring(book.read("xl/sharedStrings.xml"))
            shared = ["".join(node.itertext()) for node in root]
        sheet_name = next(name for name in book.namelist() if name.startswith("xl/worksheets/sheet") and name.endswith(".xml"))
        root = ElementTree.fromstring(book.read(sheet_name))
        matrix = []
        for row in root.iter():
            if not row.tag.endswith("}row"):
                continue
            values = {}
            for cell in row:
                if not cell.tag.endswith("}c"):
                    continue
                ref = cell.attrib.get("r", "A1")
                col = 0
                for char in re.match(r"[A-Z]+", ref).group(0):
                    col = col * 26 + ord(char) - 64
                value_node = next((item for item in cell.iter() if item.tag.endswith("}v")), None)
                inline = next((item for item in cell.iter() if item.tag.endswith("}t")), None)
                value = value_node.text if value_node is not None else (inline.text if inline is not None else "")
                if cell.attrib.get("t") == "s" and value:
                    value = shared[int(value)]
                values[col - 1] = value or ""
            matrix.append([values.get(i, "") for i in range(max(values, default=-1) + 1)])
    if not matrix:
        return []
    headers = [str(value).strip() or f"kolon_{index + 1}" for index, value in enumerate(matrix[0])]
    return [dict(zip(headers, row + [""] * (len(headers) - len(row)))) for row in matrix[1:] if any(str(v).strip() for v in row)]


def smart_import(filename: str, payload: bytes) -> dict:
    suffix = Path(filename).suffix.lower()
    if suffix in {".xlsx", ".xls", ".csv", ".pdf", ".xml", ".docx", ".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp", ".ppm"}:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as source:
            source.write(payload)
            source_path = source.name
        try:
            ensure_packaged_source()
            from src.utils.stock_import_parser import StockImportParser
            parsed = StockImportParser.parse_file(source_path)
            if suffix in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp", ".ppm"} and not parsed.get("rows"):
                try:
                    from PIL import Image
                    with Image.open(source_path) as image:
                        parsed["text"] = StockImportParser._ocr_image_to_text(image)
                except Exception:
                    parsed.setdefault("text", "")
            parsed["engine"] = (parsed.get("metadata") or {}).get("import_engine") or "AYEC Pro StockImportParser"
            parsed["original_name"] = filename
            if parsed.get("rows") or suffix not in {".csv", ".xlsx"}:
                return parsed
            parser_message = "; ".join(filter(None, parsed.get("warnings") or [])) or "Masaüstü ayrıştırıcısı satır üretmedi; standart okuyucu devreye alındı."
        except Exception as parser_error:
            parser_message = str(parser_error)
        finally:
            Path(source_path).unlink(missing_ok=True)
    else:
        parser_message = ""
    if suffix == ".xlsx":
        return {"engine": "XLSX standart kitaplık okuyucusu", "rows": parse_xlsx(payload), "text": "", "warnings": [parser_message] if parser_message else []}
    if suffix in {".csv", ".txt", ".json"}:
        text = payload.decode("utf-8-sig", errors="replace")
        if suffix == ".json":
            data = json.loads(text)
            rows_data = data if isinstance(data, list) else data.get("stock", []) if isinstance(data, dict) else []
            return {"engine": "JSON", "rows": rows_data, "text": text, "warnings": []}
        try:
            dialect = csv.Sniffer().sniff(text[:4096], delimiters=";,\t|")
            reader = csv.DictReader(io.StringIO(text), dialect=dialect)
        except csv.Error:
            # A one-column/export-without-sample CSV cannot be sniffed.  The
            # desktop importer falls back to semicolon in that case.
            reader = csv.DictReader(io.StringIO(text), delimiter=";")
        return {"engine": "CSV akıllı eşleştirme", "rows": list(reader), "text": text, "warnings": [parser_message] if parser_message else []}
    if suffix in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}:
        configured_tesseract = os.environ.get("TESSERACT_CMD", "tesseract")
        executable_text = shutil.which(configured_tesseract)
        executable = Path(executable_text) if executable_text else next((p for p in (Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"), Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe")) if p.exists()), None)
        if not executable:
            raise RuntimeError("Tesseract OCR bulunamadı")
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as source:
            source.write(payload)
            source_path = source.name
        try:
            result = subprocess.run([str(executable), source_path, "stdout", "-l", "tur+eng", "--psm", "6"], capture_output=True, timeout=120)
            text = result.stdout.decode("utf-8", errors="replace").strip()
            if not text:
                raise RuntimeError(result.stderr.decode("utf-8", errors="replace") or "OCR metin bulamadı")
            return {"engine": "Tesseract OCR (tur+eng)", "rows": [], "text": text, "warnings": [parser_message] if parser_message else []}
        finally:
            Path(source_path).unlink(missing_ok=True)
    raise ValueError("Desteklenmeyen akıllı içe aktarma dosyası")


REQUIRED_OPERATIONAL_TABLES = {
    "customers", "customer_currency_balances", "devices", "used_parts", "parts",
    "stock_movements", "accounting", "appointments", "scheduled_alerts", "personnel",
    "offers", "offer_items", "settings", "internal_settings",
}
REQUIRED_WEB_TABLES = {"users", "company_info", "web_sessions"}


def operational_schema_ready(conn: sqlite3.Connection) -> bool:
    available = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    }
    return REQUIRED_OPERATIONAL_TABLES.issubset(available)


def schema_ready(conn: sqlite3.Connection) -> bool:
    available = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    }
    return operational_schema_ready(conn) and REQUIRED_WEB_TABLES.issubset(available)


def ensure_operational_schema(conn: sqlite3.Connection) -> None:
    """Create any desktop operational tables missing from a web deployment."""
    schema = zlib.decompress(base64.b64decode(_OPERATIONAL_SCHEMA_B64)).decode("utf-8")
    conn.execute("PRAGMA foreign_keys=OFF")
    try:
        conn.executescript(schema)
        conn.commit()
    finally:
        conn.execute("PRAGMA foreign_keys=ON")
    available = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    }
    missing = sorted(REQUIRED_OPERATIONAL_TABLES - available)
    if missing:
        raise RuntimeError(f"Operasyon veritabanı şeması oluşturulamadı: {', '.join(missing)}")


def ensure_web_schema(conn: sqlite3.Connection) -> None:
    """Add the web authentication schema without changing desktop data."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            email TEXT,
            role TEXT DEFAULT 'User',
            created_at TEXT,
            last_login TEXT,
            remember_token TEXT,
            auto_login INTEGER DEFAULT 0,
            permissions TEXT,
            full_name TEXT,
            active INTEGER DEFAULT 1,
            interface_edit_access INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS internal_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS company_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            authorized_person TEXT,
            phone TEXT,
            email TEXT,
            address TEXT,
            tax_office TEXT,
            tax_number TEXT,
            logo_path TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS web_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_hash TEXT NOT NULL UNIQUE,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            remember INTEGER DEFAULT 0,
            user_agent TEXT,
            ip_address TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_web_sessions_user ON web_sessions(user_id);
        CREATE INDEX IF NOT EXISTS idx_web_sessions_expiry ON web_sessions(expires_at);
        CREATE TABLE IF NOT EXISTS service_tracking_access (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tracking_no TEXT NOT NULL,
            accessed_at TEXT NOT NULL,
            ip_address TEXT,
            user_agent TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_service_tracking_access_tracking
            ON service_tracking_access(tracking_no, accessed_at);
        CREATE TABLE IF NOT EXISTS sync_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT NOT NULL,
            table_name TEXT NOT NULL,
            record_id TEXT,
            action TEXT NOT NULL,
            payload_hash TEXT,
            created_at TEXT NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_sync_events_source
            ON sync_events(source_id, table_name, COALESCE(record_id, ''), action);
        CREATE TABLE IF NOT EXISTS sync_conflicts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name TEXT NOT NULL,
            record_id TEXT NOT NULL,
            source_id TEXT NOT NULL,
            base_hash TEXT,
            server_hash TEXT NOT NULL,
            client_hash TEXT NOT NULL,
            server_payload_json TEXT NOT NULL,
            client_payload_json TEXT NOT NULL,
            resolution TEXT NOT NULL DEFAULT 'pending',
            detected_at TEXT NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_sync_conflicts_version
            ON sync_conflicts(table_name, record_id, server_hash, client_hash);
        """
    )
    user_columns = {row[1] for row in conn.execute('PRAGMA table_info("users")')}
    additions = {
        "email": "TEXT",
        "role": "TEXT DEFAULT 'User'",
        "created_at": "TEXT",
        "last_login": "TEXT",
        "remember_token": "TEXT",
        "auto_login": "INTEGER DEFAULT 0",
        "permissions": "TEXT",
        "full_name": "TEXT",
        "active": "INTEGER DEFAULT 1",
        "interface_edit_access": "INTEGER DEFAULT 0",
        "phone": "TEXT",
        "must_change_password": "INTEGER DEFAULT 0",
        "temporary_password_expires_at": "TEXT",
    }
    for column, definition in additions.items():
        if column not in user_columns:
            conn.execute(f'ALTER TABLE users ADD COLUMN "{column}" {definition}')

    used_part_columns = {
        row[1] for row in conn.execute('PRAGMA table_info("used_parts")')
    }
    used_part_additions = {
        "exchange_rate": "REAL DEFAULT 0",
        "price_try": "REAL DEFAULT 0",
    }
    for column, definition in used_part_additions.items():
        if column not in used_part_columns:
            conn.execute(
                f'ALTER TABLE used_parts ADD COLUMN "{column}" {definition}'
            )
    conn.execute(
        """
        UPDATE used_parts
        SET exchange_rate=1,
            price_try=COALESCE(price,0)
        WHERE UPPER(COALESCE(currency,'TRY'))='TRY'
          AND COALESCE(price_try,0)<=0
        """
    )
    conn.execute(
        """
        UPDATE used_parts
        SET exchange_rate=0
        WHERE UPPER(COALESCE(currency,'TRY')) IN ('USD','EUR')
          AND COALESCE(price_try,0)<=0
          AND COALESCE(exchange_rate,0)<=1
        """
    )
    conn.execute(
        """
        UPDATE used_parts
        SET exchange_rate=(
                SELECT er.selling_rate
                FROM exchange_rates er
                WHERE UPPER(er.currency)=UPPER(used_parts.currency)
                  AND COALESCE(er.selling_rate,0)>0
                ORDER BY datetime(er.created_at) DESC,er.id DESC
                LIMIT 1
            ),
            price_try=COALESCE(price,0)*(
                SELECT er.selling_rate
                FROM exchange_rates er
                WHERE UPPER(er.currency)=UPPER(used_parts.currency)
                  AND COALESCE(er.selling_rate,0)>0
                ORDER BY datetime(er.created_at) DESC,er.id DESC
                LIMIT 1
            )
        WHERE UPPER(COALESCE(currency,'TRY')) IN ('USD','EUR')
          AND COALESCE(price_try,0)<=0
          AND EXISTS (
                SELECT 1
                FROM exchange_rates er
                WHERE UPPER(er.currency)=UPPER(used_parts.currency)
                  AND COALESCE(er.selling_rate,0)>0
            )
        """
    )
            
    # Add licensing columns to the registry database when the table exists.
    tenant_table = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='tenants'"
    ).fetchone()
    if tenant_table:
        tenant_columns = {row[1] for row in conn.execute('PRAGMA table_info("tenants")')}
        tenant_additions = {
            "sector": "TEXT DEFAULT 'teknik_servis'",
            "license_type": "TEXT DEFAULT 'Lifetime'",
            "license_code": "TEXT",
            "license_start": "TEXT",
            "license_end": "TEXT",
            "license_status": "TEXT DEFAULT 'Active'",
        }
        for column, definition in tenant_additions.items():
            if column not in tenant_columns:
                conn.execute(f'ALTER TABLE tenants ADD COLUMN "{column}" {definition}')

    order_table = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='license_orders'"
    ).fetchone()
    if order_table:
        order_columns = {row[1] for row in conn.execute('PRAGMA table_info("license_orders")')}
        if "license_code" not in order_columns:
            conn.execute('ALTER TABLE license_orders ADD COLUMN "license_code" TEXT')

    # Backfill codes for licenses approved before the code field was added.
    if tenant_table:
        active_tenants = conn.execute(
            "SELECT id FROM tenants WHERE COALESCE(license_status,'Active')='Active' "
            "AND COALESCE(license_code,'')=''"
        ).fetchall()
        for tenant_row in active_tenants:
            generated_code = "AYEC-" + secrets.token_hex(24).upper()
            conn.execute(
                "UPDATE tenants SET license_code=? WHERE id=?",
                (generated_code, str(tenant_row[0])),
            )
            if order_table:
                conn.execute(
                    "UPDATE license_orders SET license_code=? WHERE tenant_id=? "
                    "AND status='active' AND COALESCE(license_code,'')=''",
                    (generated_code, str(tenant_row[0])),
                )

    # Create Super Admin system tables
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS error_telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            version TEXT,
            os_info TEXT,
            error_message TEXT,
            stack_trace TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS staged_updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version TEXT UNIQUE NOT NULL,
            notes TEXT,
            target_scope TEXT DEFAULT 'All',
            file_path TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS global_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_tenant_id TEXT DEFAULT 'All',
            message_title TEXT,
            message_content TEXT,
            popup INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            expires_at TEXT
        );
        """
    )
    conn.commit()


def _raw_connect(path: Path) -> sqlite3.Connection:
    path = Path(path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def _ensure_path_schema(conn: sqlite3.Connection, path: Path) -> None:
    current_path = str(Path(path).resolve())
    if current_path not in _SCHEMA_READY_PATHS or not schema_ready(conn):
        with _SCHEMA_LOCK:
            if current_path not in _SCHEMA_READY_PATHS or not schema_ready(conn):
                # Auto-migrate columns before views and indexes are recreated.
                try:
                    op_schema = zlib.decompress(base64.b64decode(_OPERATIONAL_SCHEMA_B64)).decode("utf-8")
                    migration_errors = []
                    table_defs = op_schema.split("CREATE TABLE IF NOT EXISTS ")
                    for t_def in table_defs[1:]:
                        parts = t_def.split("(", 1)
                        if len(parts) < 2:
                            continue
                        tbl_name = parts[0].strip().strip('"').strip('`')
                        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", tbl_name):
                            raise RuntimeError(f"Unsafe schema table identifier: {tbl_name!r}")
                        body = parts[1]
                        if ");" in body:
                            body = body.split(");", 1)[0]
                        elif ");\n" in body:
                            body = body.split(");\n", 1)[0]
                        
                        table_exists = conn.execute(
                            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                            (tbl_name,),
                        ).fetchone()
                        if not table_exists:
                            continue
                        
                        existing_cols = {row[1].lower() for row in conn.execute(f'PRAGMA table_info("{tbl_name}")')}
                        col_defs = []
                        depth = 0
                        current_chunk = []
                        for char in body:
                            if char == '(':
                                depth += 1
                            elif char == ')':
                                depth -= 1
                            if char == ',' and depth == 0:
                                col_defs.append("".join(current_chunk).strip())
                                current_chunk = []
                            else:
                                current_chunk.append(char)
                        if current_chunk:
                            col_defs.append("".join(current_chunk).strip())
                        
                        for col_def in col_defs:
                            col_def = col_def.strip()
                            if not col_def or col_def.upper().startswith(("PRIMARY KEY", "FOREIGN KEY", "UNIQUE", "CONSTRAINT")):
                                continue
                            words = col_def.split()
                            if not words:
                                continue
                            col_name = words[0].strip().strip('"').strip('`')
                            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", col_name):
                                continue
                            if col_name.lower() not in existing_cols:
                                col_type_def = " ".join(words[1:])
                                try:
                                    conn.execute(f'ALTER TABLE "{tbl_name}" ADD COLUMN "{col_name}" {col_type_def}')
                                except sqlite3.Error as typed_error:
                                    try:
                                        conn.execute(f'ALTER TABLE "{tbl_name}" ADD COLUMN "{col_name}" TEXT')
                                    except sqlite3.Error as fallback_error:
                                        migration_errors.append(
                                            f"{tbl_name}.{col_name}: {typed_error}; fallback: {fallback_error}"
                                        )
                    if migration_errors:
                        raise RuntimeError(
                            "Operational schema column migration failed: "
                            + " | ".join(migration_errors)
                        )
                except Exception:
                    logger.exception("Operational schema pre-migration failed for %s", current_path)
                    raise
                ensure_operational_schema(conn)
                ensure_web_schema(conn)
                if not schema_ready(conn):
                    raise RuntimeError(
                        f"Database schema verification failed after migration: {current_path}"
                    )
                _SCHEMA_READY_PATHS.add(current_path)


def _tenant_filename(company_name: str) -> str:
    """Return a safe, human-readable Windows filename for a company DB."""
    value = unicodedata.normalize("NFKC", str(company_name or "")).strip()
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "-", value)
    value = re.sub(r"\s+", " ", value).strip(" .") or "AYEC Pro"
    return f"{value}.db"


def _legacy_company_name(conn: sqlite3.Connection) -> str:
    row = conn.execute("SELECT company_name FROM company_info ORDER BY id LIMIT 1").fetchone()
    if row and str(row[0] or "").strip():
        return str(row[0]).strip()
    row = conn.execute("SELECT value FROM settings WHERE key='company_name'").fetchone()
    return str(row[0]).strip() if row and str(row[0] or "").strip() else "AYEC Pro"


def _legacy_has_data(conn: sqlite3.Connection) -> bool:
    for table in ("users", "company_info", "customers", "parts", "devices", "accounting"):
        try:
            if int(conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0] or 0):
                return True
        except sqlite3.Error:
            continue
    return False


def _new_tenant_id(company_name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", str(company_name or "AYEC Pro")).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^A-Za-z0-9]+", "-", ascii_name).strip("-").lower() or "firma"
    return f"{slug}-{secrets.token_hex(5)}"


def _tenant_row(conn: sqlite3.Connection, tenant_id: str):
    return conn.execute(
        "SELECT * FROM tenants WHERE id=? AND COALESCE(active,1)=1",
        (str(tenant_id or ""),),
    ).fetchone()


def _tenant_row_any(conn: sqlite3.Connection, tenant_id: str):
    return conn.execute("SELECT * FROM tenants WHERE id=?", (str(tenant_id or ""),)).fetchone()


def registry_connect() -> sqlite3.Connection:
    """Open the central registry and lazily migrate the old single DB."""
    conn = _raw_connect(DB_PATH)
    _ensure_path_schema(conn, DB_PATH)
    has_registry = bool(conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='tenants'").fetchone())
    if not has_registry:
        # Copy before creating registry metadata so the legacy file remains a
        # usable backup and all existing rows are preserved byte-for-byte.
        company_name = _legacy_company_name(conn)
        if _legacy_has_data(conn):
            TENANT_ROOT.mkdir(parents=True, exist_ok=True)
            filename = _tenant_filename(company_name)
            target = TENANT_ROOT / filename
            suffix = 2
            while target.exists() and target.resolve() != DB_PATH.resolve():
                target = TENANT_ROOT / f"{Path(filename).stem} ({suffix}).db"
                suffix += 1
            if target.resolve() != DB_PATH.resolve():
                with closing(sqlite3.connect(target, timeout=30)) as destination:
                    conn.backup(destination)
                    destination.commit()
                tenant_id = _new_tenant_id(company_name)
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS tenants (id TEXT PRIMARY KEY, company_name TEXT NOT NULL, db_filename TEXT UNIQUE NOT NULL, created_at TEXT NOT NULL, active INTEGER DEFAULT 1)"
                )
                conn.execute(
                    "INSERT INTO tenants(id,company_name,db_filename,created_at,active) VALUES (?,?,?,?,1)",
                    (tenant_id, company_name, target.name, utc_now().isoformat(timespec="seconds"),),
                )
                conn.commit()
                has_registry = True
    if not has_registry:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS tenants (id TEXT PRIMARY KEY, company_name TEXT NOT NULL, db_filename TEXT UNIQUE NOT NULL, created_at TEXT NOT NULL, active INTEGER DEFAULT 1, sector TEXT DEFAULT 'teknik_servis')"
        )
        conn.commit()
    tenant_columns = {row[1] for row in conn.execute('PRAGMA table_info("tenants")')}
    tenant_additions = {
        "sector": "TEXT DEFAULT 'teknik_servis'",
        "license_type": "TEXT DEFAULT 'Lifetime'",
        "license_code": "TEXT",
        "license_start": "TEXT",
        "license_end": "TEXT",
        "license_status": "TEXT DEFAULT 'Active'",
        "contact_name": "TEXT",
        "phone": "TEXT",
        "email": "TEXT",
        "company_address": "TEXT",
        "installation_lat": "REAL",
        "installation_lng": "REAL",
        "location_updated_at": "TEXT",
        "license_updated_at": "TEXT",
        "sync_epoch": "INTEGER NOT NULL DEFAULT 1",
        "product_code": "TEXT NOT NULL DEFAULT 'teknik_servis'",
        "muted": "INTEGER NOT NULL DEFAULT 0",
        "muted_at": "TEXT",
        "muted_reason": "TEXT",
    }
    for column, definition in tenant_additions.items():
        if column not in tenant_columns:
            conn.execute(f'ALTER TABLE tenants ADD COLUMN "{column}" {definition}')
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS control_admins (
            tenant_id TEXT NOT NULL,
            product_code TEXT NOT NULL DEFAULT 'teknik_servis',
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (tenant_id, user_id)
        )
        """
    )
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS support_backups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            original_name TEXT,
            sha256 TEXT NOT NULL,
            size_bytes INTEGER NOT NULL DEFAULT 0,
            source TEXT NOT NULL DEFAULT 'desktop',
            created_at TEXT NOT NULL,
            created_by_user_id INTEGER,
            product_code TEXT NOT NULL DEFAULT 'teknik_servis',
            hardware_id TEXT NOT NULL DEFAULT '',
            installation_id TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'available'
        );
        CREATE INDEX IF NOT EXISTS idx_support_backups_tenant
            ON support_backups(tenant_id, created_at DESC);
        CREATE TABLE IF NOT EXISTS desktop_commands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            command_type TEXT NOT NULL,
            payload_json TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            created_by_tenant_id TEXT,
            created_by_user_id INTEGER,
            created_at TEXT NOT NULL,
            claimed_at TEXT,
            completed_at TEXT,
            result_json TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_desktop_commands_pending
            ON desktop_commands(tenant_id, status, created_at);
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            expires_at TEXT NOT NULL,
            used_at TEXT,
            created_by_tenant_id TEXT,
            created_by_user_id INTEGER,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS support_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor_tenant_id TEXT,
            actor_user_id INTEGER,
            target_tenant_id TEXT,
            target_user_id INTEGER,
            action TEXT NOT NULL,
            detail_json TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS provision_invites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code_hash TEXT NOT NULL UNIQUE,
            code_value TEXT,
            expires_at TEXT NOT NULL,
            max_uses INTEGER NOT NULL DEFAULT 1,
            use_count INTEGER NOT NULL DEFAULT 0,
            revoked_at TEXT,
            created_by_tenant_id TEXT,
            created_by_user_id INTEGER,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_provision_invites_active
            ON provision_invites(expires_at, revoked_at);
        CREATE TABLE IF NOT EXISTS provision_rate_limits (
            client_key_hash TEXT PRIMARY KEY,
            window_started_at TEXT NOT NULL,
            attempt_count INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS license_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_no TEXT NOT NULL UNIQUE,
            tenant_id TEXT NOT NULL,
            requester_user_id INTEGER,
            requester_name TEXT,
            requester_email TEXT,
            requester_phone TEXT,
            hardware_id TEXT,
            plan_code TEXT NOT NULL,
            plan_label TEXT NOT NULL,
            duration_months INTEGER NOT NULL,
            amount_try REAL NOT NULL,
            currency TEXT NOT NULL DEFAULT 'TRY',
            payment_reference TEXT NOT NULL UNIQUE,
            license_code TEXT,
            status TEXT NOT NULL DEFAULT 'payment_pending',
            payment_reported_at TEXT,
            payment_note TEXT,
            admin_note TEXT,
            approved_by_user_id INTEGER,
            approved_at TEXT,
            license_start TEXT,
            license_end TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_license_orders_tenant
            ON license_orders(tenant_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_license_orders_status
            ON license_orders(status, created_at DESC);
        CREATE TABLE IF NOT EXISTS license_payment_profile (
            id INTEGER PRIMARY KEY CHECK (id=1),
            bank_name TEXT NOT NULL,
            account_holder TEXT NOT NULL,
            iban TEXT NOT NULL,
            notification_email TEXT,
            updated_at TEXT NOT NULL
        );
        """
    )
    support_backup_columns = {
        row[1] for row in conn.execute('PRAGMA table_info("support_backups")')
    }
    if "protected_until" not in support_backup_columns:
        conn.execute("ALTER TABLE support_backups ADD COLUMN protected_until TEXT")
    for column, declaration in {"product_code": "TEXT NOT NULL DEFAULT 'teknik_servis'",
                                "hardware_id": "TEXT NOT NULL DEFAULT ''",
                                "installation_id": "TEXT NOT NULL DEFAULT ''"}.items():
        if column not in support_backup_columns:
            conn.execute(f"ALTER TABLE support_backups ADD COLUMN {column} {declaration}")
    command_columns = {row[1] for row in conn.execute('PRAGMA table_info("desktop_commands")')}
    if "product_code" not in command_columns:
        conn.execute("ALTER TABLE desktop_commands ADD COLUMN product_code TEXT NOT NULL DEFAULT 'teknik_servis'")
    invite_columns = {
        row[1] for row in conn.execute('PRAGMA table_info("provision_invites")')
    }
    if "code_value" not in invite_columns:
        conn.execute('ALTER TABLE provision_invites ADD COLUMN "code_value" TEXT')
    order_columns = {row[1] for row in conn.execute('PRAGMA table_info("license_orders")')}
    if "product_code" not in order_columns:
        conn.execute("ALTER TABLE license_orders ADD COLUMN product_code TEXT NOT NULL DEFAULT 'teknik_servis'")
    if "location_json" not in order_columns:
        conn.execute("ALTER TABLE license_orders ADD COLUMN location_json TEXT NOT NULL DEFAULT '{}'")
    if "installation_id" not in order_columns:
        conn.execute("ALTER TABLE license_orders ADD COLUMN installation_id TEXT NOT NULL DEFAULT ''")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS license_device_bindings (
            tenant_id TEXT NOT NULL, product_code TEXT NOT NULL,
            hardware_id TEXT NOT NULL, installation_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (tenant_id, product_code, hardware_id)
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS muted_devices (
            tenant_id TEXT NOT NULL, product_code TEXT NOT NULL,
            hardware_id TEXT NOT NULL, installation_id TEXT NOT NULL DEFAULT '',
            muted_at TEXT NOT NULL, reason TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (tenant_id, product_code, hardware_id, installation_id)
        )"""
    )
    conn.execute(
        "INSERT OR IGNORE INTO license_payment_profile "
        "(id,bank_name,account_holder,iban,notification_email,updated_at) "
        "VALUES (1,?,?,?,?,?)",
        (LICENSE_PAYMENT_BANK, LICENSE_PAYMENT_HOLDER, LICENSE_PAYMENT_IBAN, SUPPORT_EMAIL,
         utc_now().isoformat(timespec="seconds")),
    )
    conn.execute(
        "UPDATE license_payment_profile SET bank_name=?,account_holder=?,iban=?,"
        "notification_email=?,updated_at=? "
        "WHERE id=1",
        (
            LICENSE_PAYMENT_BANK,
            LICENSE_PAYMENT_HOLDER,
            LICENSE_PAYMENT_IBAN,
            SUPPORT_EMAIL,
            utc_now().isoformat(timespec="seconds"),
        ),
    )
    conn.execute("CREATE TABLE IF NOT EXISTS google_identities (subject TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, user_id INTEGER NOT NULL, created_at TEXT NOT NULL)")
    conn.commit()
    return conn


def tenant_records() -> list[dict]:
    with closing(registry_connect()) as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM tenants WHERE COALESCE(active,1)=1 ORDER BY id")]


def tenant_by_id(tenant_id: str) -> dict | None:
    with closing(registry_connect()) as conn:
        row = _tenant_row(conn, tenant_id)
        return dict(row) if row else None


def _parse_registry_time(value) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def tenant_access_error(tenant: dict | None) -> str:
    """Return an access error for an inactive or expired tenant, otherwise an empty string."""
    if not tenant:
        return "Firma bulunamadi."
    if int(tenant.get("muted") or 0) == 1:
        return "Firma susturuldu. Yonetici ile iletisime gecin."
    if int(tenant.get("active") or 0) != 1:
        return "Firma erisime kapatildi."
    license_type = str(tenant.get("license_type") or "Lifetime").strip().casefold()
    license_status = str(tenant.get("license_status") or "Active").strip().casefold()
    if license_status in {"passive", "inactive", "cancelled", "canceled", "revoked", "expired"}:
        return "Lisans erisime kapatildi."
    expires_at = _parse_registry_time(tenant.get("license_end"))
    is_trial = license_type in {"trial", "demo", "deneme"} or license_status == "trial"
    if is_trial and (not expires_at or utc_now() > expires_at):
        return "15 gunluk deneme suresi doldu. Davet kodu veya lisans bilgisi gereklidir."
    if expires_at and license_type not in {"lifetime", "sinirsiz"} and utc_now() > expires_at:
        return "Lisans suresi doldu. Davet kodu veya lisans bilgisi gereklidir."
    return ""


def tenant_access_summary(tenant: dict | None) -> dict:
    error = tenant_access_error(tenant)
    status = str((tenant or {}).get("license_status") or "").casefold()
    expired = _parse_registry_time((tenant or {}).get("license_end"))
    reason = ""
    if error:
        if int((tenant or {}).get("muted") or 0) == 1:
            reason = "muted"
        elif status in {"inactive", "passive", "revoked", "cancelled", "canceled"} or (
            tenant and int(tenant.get("active") or 0) != 1
        ):
            reason = "revoked"
        elif status == "expired" or (expired and utc_now() >= expired):
            reason = "expired"
        else:
            reason = "inactive"
    return {
        "allowed": not bool(error),
        "message": error,
        "license_type": str((tenant or {}).get("license_type") or "Lifetime"),
        "license_code": str((tenant or {}).get("license_code") or ""),
        "license_status": str((tenant or {}).get("license_status") or "Active"),
        "license_start": str((tenant or {}).get("license_start") or ""),
        "license_end": str((tenant or {}).get("license_end") or ""),
        "license_updated_at": str((tenant or {}).get("license_updated_at") or ""),
        "muted": bool((tenant or {}).get("muted")),
        "muted_reason": str((tenant or {}).get("muted_reason") or ""),
        "reason_code": reason,
    }


def license_plan_catalog() -> list[dict]:
    return [
        {
            "code": code,
            "label": label,
            "duration_months": months,
            "amount_try": amount,
            "currency": "TRY",
        }
        for code, label, months, amount in LICENSE_PLAN_DEFAULTS
    ]


def license_payment_profile() -> dict:
    with closing(registry_connect()) as conn:
        row = conn.execute("SELECT bank_name,account_holder,iban,notification_email "
                           "FROM license_payment_profile WHERE id=1").fetchone()
    profile = dict(row) if row else {}
    return {
        "bank_name": str(profile.get("bank_name") or LICENSE_PAYMENT_BANK),
        "account_holder": str(profile.get("account_holder") or LICENSE_PAYMENT_HOLDER),
        "iban": str(profile.get("iban") or LICENSE_PAYMENT_IBAN),
        "notification_email": str(profile.get("notification_email") or SUPPORT_EMAIL),
    }


def _license_plan(plan_code: str) -> dict:
    wanted = str(plan_code or "").strip()
    for plan in license_plan_catalog():
        if plan["code"] == wanted:
            return plan
    raise ValueError("Gecerli bir lisans paketi secin.")


def _license_add_months(value: datetime, months: int) -> datetime:
    month_index = value.month - 1 + max(1, int(months))
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, (datetime(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)).day)
    return value.replace(year=year, month=month, day=day)


def _new_license_reference(conn: sqlite3.Connection) -> tuple[str, str]:
    while True:
        token = secrets.token_hex(4).upper()
        request_no = f"AYEC-{utc_now().strftime('%Y%m%d')}-{token}"
        payment_reference = f"LISANS-{token}"
        exists = conn.execute(
            "SELECT 1 FROM license_orders WHERE request_no=? OR payment_reference=?",
            (request_no, payment_reference),
        ).fetchone()
        if not exists:
            return request_no, payment_reference


def _license_request_payload(item: dict) -> dict:
    return {
        "id": int(item.get("id") or 0),
        "request_no": str(item.get("request_no") or ""),
        "tenant_id": str(item.get("tenant_id") or ""),
        "product_code": str(item.get("product_code") or "teknik_servis"),
        "company_name": str(item.get("company_name") or ""),
        "requester_name": str(item.get("requester_name") or ""),
        "requester_email": str(item.get("requester_email") or ""),
        "requester_phone": str(item.get("requester_phone") or ""),
        "hardware_id": str(item.get("hardware_id") or ""),
        "location_json": str(item.get("location_json") or "{}"),
        "plan_code": str(item.get("plan_code") or ""),
        "plan_label": str(item.get("plan_label") or ""),
        "duration_months": int(item.get("duration_months") or 0),
        "amount_try": float(item.get("amount_try") or 0),
        "currency": str(item.get("currency") or "TRY"),
        "payment_reference": str(item.get("payment_reference") or ""),
        "license_code": str(item.get("license_code") or ""),
        "status": str(item.get("status") or "payment_pending"),
        "payment_reported_at": str(item.get("payment_reported_at") or ""),
        "payment_note": str(item.get("payment_note") or ""),
        "admin_note": str(item.get("admin_note") or ""),
        "approved_at": str(item.get("approved_at") or ""),
        "license_start": str(item.get("license_start") or ""),
        "license_end": str(item.get("license_end") or ""),
        "created_at": str(item.get("created_at") or ""),
        "updated_at": str(item.get("updated_at") or ""),
    }


def official_service_settings() -> dict:
    """Read server-only configuration; never include secrets in API responses."""
    path = Path(os.environ.get("AYEC_OFFICIAL_CONFIG", str(ROOT / "official-services.json")))
    if not path.is_file():
        return {}
    try:
        config = json.loads(path.read_text(encoding="utf-8-sig"))
        return config if isinstance(config, dict) else {}
    except (OSError, ValueError):
        logger.error("Official service configuration could not be loaded.")
        return {}


def google_client_id() -> str:
    value = str(os.environ.get("AYEC_GOOGLE_CLIENT_ID") or official_service_settings().get("google_client_id") or "").strip()
    return value if value.endswith(".apps.googleusercontent.com") else ""


def google_challenge() -> dict:
    client_id = google_client_id()
    if not client_id:
        return {"enabled": False}
    nonce = secrets.token_urlsafe(32)
    now = time.time()
    with _AUTH_LOCK:
        for key, expiry in list(_GOOGLE_NONCES.items()):
            if expiry < now:
                _GOOGLE_NONCES.pop(key, None)
        if len(_GOOGLE_NONCES) >= 10000:
            raise ValueError("Google girisi yogun. Lutfen tekrar deneyin.")
        _GOOGLE_NONCES[nonce] = now + 600
    return {"enabled": True, "client_id": client_id, "nonce": nonce}


def verify_google_identity(credential: str, nonce: str) -> dict:
    client_id = google_client_id()
    if not client_id or not credential or len(credential) > 16384:
        raise ValueError("Google girisi yapilandirilmadi veya gecersiz yanit alindi.")
    with _AUTH_LOCK:
        expiry = _GOOGLE_NONCES.pop(nonce, 0)
    if expiry < time.time():
        raise ValueError("Google oturumu zaman asimina ugradi. Sayfayi yenileyin.")
    try:
        from google.auth.transport.requests import Request as GoogleRequest
        from google.oauth2 import id_token
        identity = id_token.verify_oauth2_token(credential, GoogleRequest(), client_id)
    except Exception:
        raise ValueError("Google kimligi dogrulanamadi. Yeniden deneyin.") from None
    if not secrets.compare_digest(str(identity.get("nonce") or ""), nonce):
        raise ValueError("Google oturum dogrulamasi basarisiz.")
    if not identity.get("sub") or identity.get("email_verified") is not True or not valid_email(str(identity.get("email") or "")):
        raise ValueError("Dogrulanmis bir Google e-posta hesabi gerekiyor.")
    return identity


def google_account(identity: dict, data: dict) -> dict:
    """Bind only a freshly created account; never promote or link by email."""
    subject = str(identity["sub"])
    with _GOOGLE_REGISTRATION_LOCK:
        with closing(registry_connect()) as conn:
            linked = conn.execute("SELECT tenant_id,user_id FROM google_identities WHERE subject=?", (subject,)).fetchone()
        if linked:
            tenant = tenant_by_id(str(linked["tenant_id"]))
            if not tenant:
                raise ValueError("Google hesabinin firmasi bulunamadi.")
            set_tenant_context(tenant)
            with closing(db_connect()) as conn:
                row = conn.execute("SELECT * FROM users WHERE id=? AND COALESCE(active,1)=1", (linked["user_id"],)).fetchone()
            if not row:
                raise ValueError("Hesap aktif degil. Destek ile iletisime gecin.")
            user = dict(row)
            user["_tenant_id"] = str(tenant["id"])
            user["_company_name"] = str(tenant["company_name"])
            return {"user": user, "created": False}
        if data.get("mode") != "register":
            raise ValueError("Bu Google hesabi kayitli degil. Kaydol ekranini kullanin. Mevcut hesaplar icin parola ile giris yapin.")
        clear_tenant_context()
        with closing(registry_connect()) as conn:
            if setting_value(conn, "web_registration_enabled", "1") == "0":
                raise PermissionError("Yeni kullanici kaydi kapali.")
        payload = {
            "username": data.get("username"), "password": secrets.token_urlsafe(32) + "A1",
            "company_name": data.get("company_name"), "sector": data.get("sector"),
            "full_name": str(identity.get("name") or data.get("full_name") or "Google User"),
            "email": str(identity["email"]).lower(),
        }
        result = register_account(payload)
        with closing(db_connect()) as conn:
            user = dict(find_account_by_identifier(conn, str(payload["username"])))
        tenant_id = active_tenant_id()
        with closing(registry_connect()) as conn:
            conn.execute("INSERT INTO google_identities(subject,tenant_id,user_id,created_at) VALUES(?,?,?,?)", (subject, tenant_id, user["id"], utc_now().isoformat(timespec="seconds")))
            conn.commit()
        user["_tenant_id"] = tenant_id
        user["_company_name"] = active_company_name()
        return {"user": user, "created": True, "mail_sent": result.get("mail_sent"), "mail_message": result.get("mail_message")}


def _license_smtp_settings(tenant_id: str = "") -> dict:
    """Platform notifications use the official mailbox, never tenant SMTP."""
    config = official_service_settings()
    return {
        "host": str(os.environ.get("AYEC_OFFICIAL_SMTP_HOST") or os.environ.get("AYECPRO_SMTP_SERVER") or config.get("smtp_host") or "srvm07.trwww.com").strip(),
        "port": str(os.environ.get("AYEC_OFFICIAL_SMTP_PORT") or os.environ.get("AYECPRO_SMTP_PORT") or config.get("smtp_port") or "465"),
        "from": str(os.environ.get("AYEC_OFFICIAL_SMTP_EMAIL") or os.environ.get("AYECPRO_SMTP_EMAIL") or OFFICIAL_EMAIL).strip(),
        "username": str(os.environ.get("AYEC_OFFICIAL_SMTP_USERNAME") or os.environ.get("AYECPRO_SMTP_EMAIL") or OFFICIAL_EMAIL).strip(),
        "password": os.environ.get("AYEC_OFFICIAL_SMTP_PASSWORD") or os.environ.get("AYECPRO_SMTP_APP_PASSWORD") or str(config.get("smtp_password") or ""),
        "tls": True,
    }


def _legacy_tenant_smtp_settings(tenant_id: str) -> dict:
    with closing(registry_connect()) as conn:
        stored_tenant = _tenant_row_any(conn, tenant_id)
    tenant = dict(stored_tenant) if stored_tenant else None
    values: dict[str, str] = {}
    if tenant:
        try:
            with closing(_raw_connect(_tenant_path(tenant))) as conn:
                values = {str(row[0]): str(row[1] or "") for row in conn.execute(
                    "SELECT key,value FROM settings"
                )}
        except sqlite3.Error:
            values = {}
    return {
        "host": str(os.environ.get("AYEC_SMTP_HOST") or os.environ.get("AYECPRO_SMTP_SERVER") or values.get("smtp_server") or values.get("smtp_host") or "").strip(),
        "port": str(os.environ.get("AYEC_SMTP_PORT") or os.environ.get("AYECPRO_SMTP_PORT") or values.get("smtp_port") or "587").strip(),
        "from": str(os.environ.get("AYEC_SMTP_FROM") or os.environ.get("AYECPRO_SMTP_EMAIL") or values.get("smtp_from") or values.get("smtp_email") or "").strip(),
        "username": str(os.environ.get("AYEC_SMTP_USERNAME") or os.environ.get("AYECPRO_SMTP_EMAIL") or values.get("smtp_username") or values.get("smtp_email") or "").strip(),
        "password": str(os.environ.get("AYEC_SMTP_PASSWORD") or os.environ.get("AYECPRO_SMTP_APP_PASSWORD") or values.get("smtp_password") or ""),
        "tls": str(os.environ.get("AYEC_SMTP_TLS") or os.environ.get("AYECPRO_SMTP_TLS") or values.get("smtp_tls") or "1") != "0",
    }


def send_license_email(tenant_id: str, recipient: str, subject: str, text: str) -> tuple[bool, str]:
    recipient = str(recipient or "").strip()
    if not valid_email(recipient):
        return False, "Recipient email is invalid."
    config = _license_smtp_settings(tenant_id)
    if not config["host"] or not config["password"]:
        return False, "info@ayecpro.com SMTP ayarlari tamamlanmadi; e-posta gonderilemedi."
    try:
        port = int(config["port"] or 587)
        message = EmailMessage()
        message["Subject"] = str(subject)
        message["From"] = config["from"]
        message["To"] = recipient
        message["Reply-To"] = SUPPORT_EMAIL
        message.set_content(str(text) + f"\n\nAYEC Pro\n{OFFICIAL_WEBSITE}\nGiris: {PUBLIC_SERVER_URL}/#login\nDestek: {SUPPORT_EMAIL}")
        if port == 465:
            server = smtplib.SMTP_SSL(config["host"], port, timeout=20, context=ssl.create_default_context())
        else:
            server = smtplib.SMTP(config["host"], port, timeout=20)
            server.ehlo()
            if config["tls"]:
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
        with server:
            if config["password"]:
                server.login(config["username"] or config["from"], config["password"])
            server.send_message(message)
        return True, "Email sent."
    except Exception as error:
        logger.warning("Official email delivery failed (%s).", type(error).__name__)
        return False, "E-posta gonderilemedi. Resmi SMTP baglantisini kontrol edin."


def _tenant_path(tenant: dict) -> Path:
    filename = Path(str(tenant.get("db_filename") or "")).name
    if not filename.lower().endswith(".db"):
        raise ValueError("Invalid tenant database path")
    return (TENANT_ROOT / filename).resolve()


def ensure_control_owner() -> None:
    """Keep platform ownership exclusive to the AYEC vendor account."""
    with closing(registry_connect()) as registry:
        vendor_owners: list[tuple[str, int]] = []
        for tenant in rows(registry, "SELECT * FROM tenants WHERE COALESCE(active,1)=1 ORDER BY created_at,id"):
            path = _tenant_path(tenant)
            if not path.exists():
                continue
            with closing(_raw_connect(path)) as tenant_conn:
                _ensure_path_schema(tenant_conn, path)
                owner = tenant_conn.execute(
                    "SELECT id FROM users WHERE lower(trim(COALESCE(email,'')))=? "
                    "AND COALESCE(active,1)=1 ORDER BY id LIMIT 1",
                    (VENDOR_EMAIL,),
                ).fetchone()
                # A tenant creator is a normal customer user. Legacy builds
                # created every first tenant account as Admin; remove those
                # grants while preserving only the AYEC platform identity.
                tenant_conn.execute(
                    "UPDATE users SET role='User',interface_edit_access=0 "
                    "WHERE lower(trim(COALESCE(email,'')))<>?",
                    (VENDOR_EMAIL,),
                )
                tenant_conn.commit()
            if owner:
                vendor_owners.append((str(tenant["id"]), int(owner[0])))

        # Remove grants made by legacy versions that promoted the first tenant
        # administrator. Recreate the list exclusively from configured AYEC
        # vendor identities on every check so a stale registry row cannot
        # bypass tenant boundaries.
        registry.execute("DELETE FROM control_admins")
        created_at = utc_now().isoformat(timespec="seconds")
        registry.executemany(
            "INSERT INTO control_admins(tenant_id,user_id,created_at) VALUES (?,?,?)",
            [(tenant_id, user_id, created_at) for tenant_id, user_id in vendor_owners],
        )
        registry.commit()


def is_control_admin(user: dict | sqlite3.Row | None) -> bool:
    if not user:
        return False
    item = dict(user)
    tenant_id = str(item.get("_tenant_id") or active_tenant_id() or "")
    user_id = int(item.get("id") or 0)
    if not tenant_id or not user_id:
        return False
    ensure_control_owner()
    with closing(registry_connect()) as conn:
        return bool(
            conn.execute(
                "SELECT 1 FROM control_admins WHERE tenant_id=? AND user_id=?",
                (tenant_id, user_id),
            ).fetchone()
        )


def can_access_control_center(user: dict | sqlite3.Row | None) -> bool:
    if not user:
        return False
    item = dict(user)
    return is_control_admin(item)


def can_manage_tenant(user: dict | sqlite3.Row | None, tenant_id: str) -> bool:
    if not user:
        return False
    item = dict(user)
    if is_control_admin(item):
        return True
    actor_tenant_id = str(item.get("_tenant_id") or active_tenant_id() or "")
    return role_is_admin(item.get("role")) and actor_tenant_id == str(tenant_id or "")


def _support_audit(
    actor: dict | sqlite3.Row | None,
    action: str,
    target_tenant_id: str = "",
    target_user_id: int = 0,
    detail: dict | None = None,
) -> None:
    item = dict(actor or {})
    with closing(registry_connect()) as conn:
        conn.execute(
            "INSERT INTO support_audit(actor_tenant_id,actor_user_id,target_tenant_id,"
            "target_user_id,action,detail_json,created_at) VALUES (?,?,?,?,?,?,?)",
            (
                str(item.get("_tenant_id") or ""),
                int(item.get("id") or 0),
                str(target_tenant_id or ""),
                int(target_user_id or 0),
                str(action or "")[:100],
                json.dumps(detail or {}, ensure_ascii=True, separators=(",", ":")),
                utc_now().isoformat(timespec="seconds"),
            ),
        )
        conn.commit()


def _tenant_record_required(tenant_id: str) -> dict:
    with closing(registry_connect()) as conn:
        row = conn.execute("SELECT * FROM tenants WHERE id=?", (str(tenant_id or ""),)).fetchone()
    if not row:
        raise LookupError("Company was not found")
    return dict(row)


def control_create_reset_link(actor: dict, data: dict) -> dict:
    if not is_control_admin(actor):
        raise PermissionError("Platform operator permission is required")
    tenant_id = str(data.get("tenant_id") or "").strip()
    user_id = int(data.get("user_id") or 0)
    tenant = _tenant_record_required(tenant_id)
    path = _tenant_path(tenant)
    if not path.exists():
        raise FileNotFoundError("Firma veritabani bulunamadi")
    with closing(_raw_connect(path)) as conn:
        _ensure_path_schema(conn, path)
        user = conn.execute(
            "SELECT id,username,email,phone,active FROM users WHERE id=?", (user_id,)
        ).fetchone()
    if not user:
        raise LookupError("User was not found")
    token = secrets.token_urlsafe(40)
    now = utc_now()
    expires_at = (now + timedelta(minutes=30)).isoformat(timespec="seconds")
    actor_item = dict(actor)
    with closing(registry_connect()) as conn:
        conn.execute(
            "UPDATE password_reset_tokens SET used_at=? WHERE tenant_id=? AND user_id=? AND used_at IS NULL",
            (now.isoformat(timespec="seconds"), tenant_id, user_id),
        )
        conn.execute(
            "INSERT INTO password_reset_tokens(tenant_id,user_id,token_hash,expires_at,"
            "created_by_tenant_id,created_by_user_id,created_at) VALUES (?,?,?,?,?,?,?)",
            (
                tenant_id,
                user_id,
                hashlib.sha256(token.encode("utf-8")).hexdigest(),
                expires_at,
                str(actor_item.get("_tenant_id") or ""),
                int(actor_item.get("id") or 0),
                now.isoformat(timespec="seconds"),
            ),
        )
        conn.commit()
    _support_audit(actor, "password_reset_link_created", tenant_id, user_id)
    recipient = str(user["email"] or "").strip()
    reset_url = f"{PUBLIC_SERVER_URL}/?reset={token}"
    mail_sent, mail_message = send_license_email(
        tenant_id,
        recipient,
        "AYEC Pro parola yenileme ba\u011flant\u0131s\u0131",
        (
            f"Merhaba {user['username'] or ''},\n\n"
            "Parolan\u0131z\u0131 yenilemek i\u00e7in a\u015fa\u011f\u0131daki ba\u011flant\u0131y\u0131 kullan\u0131n:\n"
            f"{reset_url}\n\n"
            f"Bu ba\u011flant\u0131 {expires_at} UTC tarihine kadar ve yaln\u0131zca bir kez ge\u00e7erlidir.\n"
            "Bu iste\u011fi siz ba\u015flatmad\u0131ysan\u0131z destek ekibinizle ileti\u015fime ge\u00e7in."
        ),
    )
    _support_audit(
        actor,
        "password_reset_email_sent" if mail_sent else "password_reset_email_failed",
        tenant_id,
        user_id,
        detail={"recipient": recipient, "message": mail_message},
    )
    return {
        "ok": True,
        "expires_at": expires_at,
        "reset_url": reset_url,
        "username": user["username"] or "",
        "mail_sent": mail_sent,
        "mail_message": mail_message,
    }


def complete_password_reset(data: dict) -> dict:
    token = str(data.get("token") or "").strip()
    password = str(data.get("password") or "")
    if len(password) < 10 or not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise ValueError("Password must contain at least 10 characters, one letter and one number")
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = utc_now().isoformat(timespec="seconds")
    with closing(registry_connect()) as registry:
        row = registry.execute(
            "SELECT * FROM password_reset_tokens WHERE token_hash=? AND used_at IS NULL AND expires_at>?",
            (token_hash, now),
        ).fetchone()
        if not row:
            raise ValueError("Reset link is invalid or expired")
        reset = dict(row)
        tenant = registry.execute("SELECT * FROM tenants WHERE id=?", (reset["tenant_id"],)).fetchone()
        if not tenant:
            raise ValueError("Company account is unavailable")
        registry.execute("UPDATE password_reset_tokens SET used_at=? WHERE id=?", (now, reset["id"]))
        registry.commit()
    path = _tenant_path(dict(tenant))
    with closing(_raw_connect(path)) as conn:
        _ensure_path_schema(conn, path)
        conn.execute("UPDATE users SET password=? WHERE id=?", (password_hash(password), reset["user_id"]))
        conn.execute("DELETE FROM web_sessions WHERE user_id=?", (reset["user_id"],))
        conn.commit()
    _support_audit(None, "password_reset_completed", reset["tenant_id"], reset["user_id"])
    return {"ok": True}


def complete_temporary_password_change(data: dict) -> dict:
    """Replace an emailed temporary password before creating a session."""
    tenant_id = str(data.get("tenant_id") or "").strip()
    identifier = str(data.get("identifier") or "").strip()
    temporary_password = str(data.get("temporary_password") or "")
    new_password = str(data.get("new_password") or "")
    if not tenant_id or not identifier or not temporary_password:
        raise ValueError("Firma, kullanici ve gecici parola gereklidir")
    if len(new_password) < 10 or not re.search(r"[A-Za-z]", new_password) or not re.search(r"\d", new_password):
        raise ValueError("Yeni parola en az 10 karakter, bir harf ve bir rakam icermelidir")
    if secrets.compare_digest(temporary_password, new_password):
        raise ValueError("Yeni parola gecici paroladan farkli olmalidir")
    user = authenticate_account(identifier, temporary_password, tenant_id)
    if not user or not bool(user.get("must_change_password")):
        raise PermissionError("Gecici parola gecersiz veya sureci tamamlanmis")
    tenant = _tenant_record_required(tenant_id)
    path = _tenant_path(tenant)
    with closing(_raw_connect(path)) as conn:
        _ensure_path_schema(conn, path)
        cursor = conn.execute(
            "UPDATE users SET password=?,must_change_password=0,temporary_password_expires_at=NULL,remember_token=NULL,auto_login=0 "
            "WHERE id=? AND COALESCE(must_change_password,0)=1 AND password=?",
            (password_hash(new_password), int(user["id"]), user["password"]),
        )
        if cursor.rowcount != 1:
            conn.rollback()
            raise PermissionError("Gecici parola degistirilmis. Yeniden giris yapin")
        conn.execute("DELETE FROM web_sessions WHERE user_id=?", (int(user["id"]),))
        conn.commit()
    _support_audit(None, "temporary_password_changed", tenant_id, int(user["id"]))
    return {"ok": True}


def prune_support_backups(tenant_id: str, keep: int | None = None) -> dict:
    """Keep a bounded backup history without deleting queued restore sources."""
    tenant_id = str(tenant_id or "").strip()
    if not tenant_id:
        raise ValueError("Company is required")
    retention = SUPPORT_BACKUP_KEEP if keep is None else max(3, min(100, int(keep)))
    protected_ids: set[int] = set()
    with closing(registry_connect()) as conn:
        commands = conn.execute(
            "SELECT payload_json FROM desktop_commands "
            "WHERE tenant_id=? AND command_type='restore_backup' "
            "AND status IN ('pending','claimed')",
            (tenant_id,),
        ).fetchall()
        for command in commands:
            try:
                backup_id = int(json.loads(command[0] or "{}").get("backup_id") or 0)
            except (TypeError, ValueError, json.JSONDecodeError):
                backup_id = 0
            if backup_id:
                protected_ids.add(backup_id)
        backup_rows = conn.execute(
            "SELECT id,filename,size_bytes,protected_until,product_code,hardware_id,installation_id FROM support_backups "
            "WHERE tenant_id=? AND status='available' ORDER BY id DESC",
            (tenant_id,),
        ).fetchall()
        retained_regular = {}
        removable = []
        for row in backup_rows:
            backup_id = int(row[0])
            if backup_id in protected_ids:
                continue
            if str(row[3] or "") > utc_now().isoformat(timespec="seconds"):
                continue
            scope = (str(row[4]), str(row[5]), str(row[6]))
            if retained_regular.get(scope, 0) < retention:
                retained_regular[scope] = retained_regular.get(scope, 0) + 1
                continue
            removable.append(row)
    tenant_dir = (SUPPORT_BACKUP_ROOT / tenant_id).resolve()
    removed_ids = []
    freed_bytes = 0
    for row in removable:
        target = (tenant_dir / Path(str(row[1] or "")).name).resolve()
        if tenant_dir not in target.parents:
            continue
        archive_root = product_backup_root(str(row[4]))
        if archive_root is not None and PROGRAM_BACKUP_ROOT in archive_root.parents:
            device_key = hashlib.sha256(str(row[5]).encode()).hexdigest()[:24] if row[5] else "legacy"
            installation_key = hashlib.sha256(str(row[6]).encode()).hexdigest()[:24] if row[6] else "legacy"
            versions = (archive_root / "tenants" / tenant_id / "devices" / device_key /
                        "installations" / installation_key / "versions").resolve()
            if archive_root not in versions.parents:
                continue
            try:
                for version in versions.glob(f"{int(row[0])}-*.db"):
                    if version.resolve().parent != versions:
                        raise ValueError("Invalid archive version path")
                    version.unlink()
            except OSError:
                # Keep the registry row so retention can retry the archive.
                continue
        if not target.exists():
            removed_ids.append(int(row[0]))
            continue
        try:
            target.unlink()
            removed_ids.append(int(row[0]))
            freed_bytes += int(row[2] or 0)
        except OSError:
            pass
    if removed_ids:
        with closing(registry_connect()) as conn:
            conn.executemany(
                "DELETE FROM support_backups WHERE id=? AND tenant_id=?",
                [(backup_id, tenant_id) for backup_id in removed_ids],
            )
            conn.commit()
    return {
        "ok": True,
        "retention": retention,
        "removed_count": len(removed_ids),
        "freed_bytes": freed_bytes,
        "protected_count": len(protected_ids),
    }


def _store_support_backup_for_tenant(
    tenant_id: str,
    created_by_user_id: int,
    payload: bytes,
    original_name: str,
    source: str,
    product_code: str = "teknik_servis",
    hardware_id: str = "",
    installation_id: str = "",
) -> dict:
    if len(payload) < 100 or len(payload) > 1024 * 1024 * 1024:
        raise ValueError("Backup size is invalid")
    if not payload.startswith(b"SQLite format 3\x00"):
        raise ValueError("Only valid SQLite database backups are accepted")
    if not tenant_id:
        raise PermissionError("Company session is required")
    digest = hashlib.sha256(payload).hexdigest()
    with closing(registry_connect()) as conn:
        existing = conn.execute(
            "SELECT id FROM support_backups WHERE tenant_id=? AND sha256=? AND product_code=? "
            "AND hardware_id=? AND installation_id=?",
            (tenant_id, digest, product_code, hardware_id, installation_id)
        ).fetchone()
    if existing:
        cleanup = prune_support_backups(tenant_id)
        return {"ok": True, "backup_id": int(existing[0]), "duplicate": True,
                "sha256": digest, "size_bytes": len(payload), **cleanup}
    tenant_dir = (SUPPORT_BACKUP_ROOT / tenant_id).resolve()
    if SUPPORT_BACKUP_ROOT not in tenant_dir.parents:
        raise ValueError("Backup path is invalid")
    tenant_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{product_code}-{secrets.token_hex(8)}-{digest[:12]}.db"
    target = tenant_dir / filename
    if not target.exists():
        target.write_bytes(payload)
    with closing(sqlite3.connect(target)) as check:
        integrity = str(check.execute("PRAGMA integrity_check").fetchone()[0] or "")
    if integrity.lower() != "ok":
        target.unlink(missing_ok=True)
        raise ValueError("Backup integrity check failed")
    with closing(registry_connect()) as conn:
        cursor = conn.execute(
            "INSERT INTO support_backups(tenant_id,filename,original_name,sha256,size_bytes,source,"
            "created_at,created_by_user_id,product_code,hardware_id,installation_id) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                tenant_id,
                filename,
                Path(str(original_name or "desktop.db")).name,
                digest,
                len(payload),
                str(source or "desktop")[:30],
                utc_now().isoformat(timespec="seconds"),
                int(created_by_user_id or 0),
                product_code,
                hardware_id,
                installation_id,
            ),
        )
        conn.commit()
        backup_id = int(cursor.lastrowid)
    cleanup = prune_support_backups(tenant_id)
    return {
        "ok": True,
        "backup_id": backup_id,
        "sha256": digest,
        "size_bytes": len(payload),
        **cleanup,
    }


def support_store_backup(user: dict, payload: bytes, original_name: str = "desktop.db",
                         program_name: str = "", product_code: str = "",
                         hardware_id: str = "", installation_id: str = "") -> dict:
    tenant_id = str(dict(user).get("_tenant_id") or active_tenant_id() or "")
    product_code = str(product_code or "teknik_servis").strip().lower()
    if product_code not in configured_product_codes():
        raise ValueError("Unknown backup product")
    if len(hardware_id) > 256 or any(ord(char) < 32 for char in hardware_id):
        raise ValueError("Invalid device identity")
    if len(installation_id) > 256 or any(ord(char) < 32 for char in installation_id):
        raise ValueError("Invalid installation identity")
    result = _store_support_backup_for_tenant(
        tenant_id,
        int(dict(user).get("id") or 0),
        payload,
        original_name,
        "desktop",
        product_code,
        hardware_id,
        installation_id,
    )
    # The registry remains authoritative. Mirror failures are visible to callers.
    try:
        root = product_backup_root(product_code)
        if root is None or PROGRAM_BACKUP_ROOT not in root.parents:
            raise ValueError("Product backup folder is not configured")
        catalog = json.loads(PRODUCT_CATALOG_PATH.read_text(encoding="utf-8"))
        product = next(row for row in catalog["products"] if row["code"] == product_code)
        database_name = str(product["database_name"])
        if Path(database_name).name != database_name or '\\' in database_name or '/' in database_name:
            raise ValueError("Invalid product database name")
        tenant_root = (root / "tenants" / tenant_id).resolve()
        if tenant_root.parent != root / "tenants":
            raise ValueError("Invalid backup tenant")
        device_key = hashlib.sha256(hardware_id.encode()).hexdigest()[:24] if hardware_id else "legacy"
        installation_key = hashlib.sha256(installation_id.encode()).hexdigest()[:24] if installation_id else "legacy"
        device_root = tenant_root / "devices" / device_key / "installations" / installation_key
        digest = hashlib.sha256(payload).hexdigest()
        for folder in (device_root / "current", device_root / "versions"):
            folder.mkdir(parents=True, exist_ok=True)
        latest = device_root / "current" / database_name
        version = device_root / "versions" / f"{result['backup_id']}-{digest[:16]}.db"
        if not version.exists():
            version.write_bytes(payload)
        temporary = latest.with_suffix(f".{secrets.token_hex(8)}.tmp")
        try:
            temporary.write_bytes(payload)
            os.replace(temporary, latest)
        finally:
            temporary.unlink(missing_ok=True)
        result["product_backup_path"] = str(latest)
        result["product_archive_ok"] = True
    except (OSError, ValueError, KeyError, StopIteration) as error:
        result["product_archive_ok"] = False
        result["product_archive_error"] = str(error)
    return result


def control_queue_restore(actor: dict, data: dict) -> dict:
    if not is_control_admin(actor):
        raise PermissionError("Platform operator permission is required")
    tenant_id = str(data.get("tenant_id") or "").strip()
    backup_id = int(data.get("backup_id") or 0)
    with closing(registry_connect()) as conn:
        backup = conn.execute(
            "SELECT * FROM support_backups WHERE id=? AND tenant_id=? AND status='available'",
            (backup_id, tenant_id),
        ).fetchone()
        if not backup:
            raise LookupError("Backup was not found")
        item = dict(actor)
        cursor = conn.execute(
            "INSERT INTO desktop_commands(tenant_id,command_type,payload_json,status,"
            "created_by_tenant_id,created_by_user_id,created_at,product_code) VALUES (?, 'restore_backup', ?, 'pending', ?, ?, ?, ?)",
            (
                tenant_id,
                json.dumps({"backup_id": backup_id, "sha256": backup["sha256"],
                            "size_bytes": backup["size_bytes"], "tenant_id": tenant_id,
                            "product_code": backup["product_code"],
                            "hardware_id": backup["hardware_id"],
                            "installation_id": backup["installation_id"]}, ensure_ascii=True),
                str(item.get("_tenant_id") or ""),
                int(item.get("id") or 0),
                utc_now().isoformat(timespec="seconds"),
                backup["product_code"],
            ),
        )
        conn.commit()
        command_id = int(cursor.lastrowid)
    _support_audit(actor, "desktop_restore_queued", tenant_id, detail={"backup_id": backup_id, "command_id": command_id})
    return {"ok": True, "command_id": command_id}


def control_prune_backups(actor: dict, data: dict) -> dict:
    if not is_control_admin(actor):
        raise PermissionError("Platform operator permission is required")
    tenant_id = str(data.get("tenant_id") or "").strip()
    with closing(registry_connect()) as conn:
        tenant = conn.execute("SELECT id FROM tenants WHERE id=?", (tenant_id,)).fetchone()
    if not tenant:
        raise LookupError("Company was not found")
    result = prune_support_backups(tenant_id, SUPPORT_BACKUP_KEEP)
    _support_audit(actor, "support_backups_pruned", tenant_id, detail=result)
    return result


def desktop_pending_commands(user: dict, product_code: str = "teknik_servis",
                             hardware_id: str = "", installation_id: str = "") -> dict:
    tenant_id = str(dict(user).get("_tenant_id") or active_tenant_id() or "")
    current_time = utc_now()
    now = current_time.isoformat(timespec="seconds")
    stale_at = (current_time - timedelta(minutes=10)).isoformat(timespec="seconds")
    with closing(registry_connect()) as conn:
        pending = rows(
            conn,
            "SELECT id,command_type,payload_json,created_at FROM desktop_commands "
            "WHERE tenant_id=? AND product_code=? "
            "AND (COALESCE(json_extract(payload_json,'$.hardware_id'),'')='' OR json_extract(payload_json,'$.hardware_id')=?) "
            "AND (COALESCE(json_extract(payload_json,'$.installation_id'),'')='' OR json_extract(payload_json,'$.installation_id')=?) "
            "AND (status='pending' OR (status='claimed' AND claimed_at<?)) "
            "ORDER BY id LIMIT 10",
            (tenant_id, product_code, hardware_id, installation_id, stale_at),
        )
        ids = [int(item["id"]) for item in pending]
        if ids:
            marks = ",".join("?" for _ in ids)
            conn.execute(
                f"UPDATE desktop_commands SET status='claimed',claimed_at=? WHERE id IN ({marks})",
                (now, *ids),
            )
            conn.commit()
    commands = []
    for item in pending:
        try:
            payload = json.loads(item.get("payload_json") or "{}")
        except (TypeError, ValueError):
            payload = {}
        commands.append({
            "id": item["id"],
            "command_type": item["command_type"],
            "payload": payload,
            "created_at": item["created_at"],
        })
    return {"ok": True, "commands": commands}


def desktop_complete_command(user: dict, data: dict, product_code: str = "teknik_servis",
                             hardware_id: str = "", installation_id: str = "") -> dict:
    tenant_id = str(dict(user).get("_tenant_id") or active_tenant_id() or "")
    command_id = int(data.get("command_id") or 0)
    success = bool(data.get("success"))
    result = dict(data.get("result") or {})
    with closing(registry_connect()) as conn:
        cursor = conn.execute(
            "UPDATE desktop_commands SET status=?,completed_at=?,result_json=? "
            "WHERE id=? AND tenant_id=? AND product_code=? "
            "AND (COALESCE(json_extract(payload_json,'$.hardware_id'),'')='' OR json_extract(payload_json,'$.hardware_id')=?) "
            "AND (COALESCE(json_extract(payload_json,'$.installation_id'),'')='' OR json_extract(payload_json,'$.installation_id')=?) "
            "AND status IN ('claimed','pending')",
            (
                "completed" if success else "failed",
                utc_now().isoformat(timespec="seconds"),
                json.dumps(result, ensure_ascii=True, separators=(",", ":")),
                command_id,
                tenant_id,
                product_code,
                hardware_id,
                installation_id,
            ),
        )
        conn.commit()
    if not cursor.rowcount:
        # The desktop outbox retries an acknowledgement when the response is
        # lost.  Return the stored terminal result instead of treating that
        # retry as a missing command or applying the command a second time.
        with closing(registry_connect()) as conn:
            existing = conn.execute(
                "SELECT status,result_json FROM desktop_commands "
                "WHERE id=? AND tenant_id=? AND product_code=? "
                "AND (COALESCE(json_extract(payload_json,'$.hardware_id'),'')='' OR json_extract(payload_json,'$.hardware_id')=?) "
                "AND (COALESCE(json_extract(payload_json,'$.installation_id'),'')='' OR json_extract(payload_json,'$.installation_id')=?)",
                (command_id, tenant_id, product_code, hardware_id, installation_id),
            ).fetchone()
        if not existing:
            raise LookupError("Desktop command was not found")
        if str(existing[0] or "") not in {"completed", "failed"}:
            raise LookupError("Desktop command is not available for completion")
        try:
            stored_result = json.loads(existing[1] or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            stored_result = {}
        return {"ok": True, "duplicate": True, "status": str(existing[0]),
                "result": stored_result}
    return {"ok": True}


def support_backup_file(user: dict, backup_id: int, product_code: str = "teknik_servis",
                        hardware_id: str = "", installation_id: str = "") -> tuple[bytes, str, str]:
    tenant_id = str(dict(user).get("_tenant_id") or active_tenant_id() or "")
    with closing(registry_connect()) as conn:
        row = conn.execute(
            "SELECT * FROM support_backups WHERE id=? AND tenant_id=? AND product_code=? "
            "AND (hardware_id='' OR hardware_id=?) "
            "AND (installation_id='' OR installation_id=?) AND status='available'",
            (int(backup_id), tenant_id, product_code, hardware_id, installation_id),
        ).fetchone()
    if not row:
        raise LookupError("Backup was not found")
    item = dict(row)
    target = (SUPPORT_BACKUP_ROOT / tenant_id / Path(item["filename"]).name).resolve()
    tenant_dir = (SUPPORT_BACKUP_ROOT / tenant_id).resolve()
    if target.parent != tenant_dir or not target.is_file():
        raise LookupError("Backup file was not found")
    payload = target.read_bytes()
    if not secrets.compare_digest(hashlib.sha256(payload).hexdigest(), str(item["sha256"])):
        raise ValueError("Backup checksum validation failed")
    return payload, str(item["sha256"]), str(item.get("original_name") or target.name)

# =============================================================================
# SUPER ADMIN API - Business Logic
# All functions require caller to have already validated is_control_admin(user).
# =============================================================================

def _admin_tenants_all() -> list:
    """Return all tenant rows from registry."""
    with closing(registry_connect()) as conn:
        return rows(conn, "SELECT * FROM tenants ORDER BY created_at, id")


def admin_dashboard() -> dict:
    """Dashboard statistics for Admin Console."""
    import shutil
    tenants = _admin_tenants_all()
    total = len(tenants)
    active = sum(1 for t in tenants if int(t.get("active") or 1) == 1)
    inactive = total - active
    # Disk usage
    try:
        usage = shutil.disk_usage(str(TENANT_ROOT))
        pct = int(usage.used / usage.total * 100)
        disk_str = f"%{pct} ({usage.used // (1024**3):.1f} / {usage.total // (1024**3):.1f} GB)"
    except Exception:
        pct = 0
        disk_str = "?"
    # Online users (sessions active in last 5 min) - approximate
    online = 0
    try:
        with closing(registry_connect()) as conn:
            cutoff = (utc_now() - timedelta(minutes=5)).isoformat(timespec="seconds")
            row = conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE last_seen >= ? OR created_at >= ?",
                (cutoff, cutoff)
            ).fetchone()
            online = int(row[0]) if row else 0
    except Exception:
        pass
    logs_data: list = []
    backup_coverage = 0
    pending_commands = 0
    failed_commands = 0
    expiring_licenses = 0
    try:
        with closing(registry_connect()) as conn:
            backup_coverage = int(scalar(
                conn,
                "SELECT COUNT(DISTINCT tenant_id) FROM support_backups "
                "WHERE status='available'",
                default=0,
            ))
            pending_commands = int(scalar(
                conn,
                "SELECT COUNT(*) FROM desktop_commands WHERE status IN ('pending','claimed')",
                default=0,
            ))
            failed_commands = int(scalar(
                conn,
                "SELECT COUNT(*) FROM desktop_commands WHERE status='failed'",
                default=0,
            ))
            today = utc_now().date()
            for item in rows(conn, "SELECT license_end FROM tenants WHERE COALESCE(active,1)=1"):
                try:
                    end_date = datetime.fromisoformat(str(item.get("license_end") or "")).date()
                    if today <= end_date <= today + timedelta(days=30):
                        expiring_licenses += 1
                except (TypeError, ValueError):
                    continue
            audit_rows = rows(
                conn,
                "SELECT a.created_at AS time,a.action,a.target_tenant_id,"
                "t.company_name AS company "
                "FROM support_audit a LEFT JOIN tenants t ON t.id=a.target_tenant_id "
                "ORDER BY a.id DESC LIMIT 20",
            )
            logs_data = [
                {
                    "time": item.get("time", ""),
                    "action": item.get("action", ""),
                    "company": item.get("company") or item.get("target_tenant_id") or "Sistem",
                }
                for item in audit_rows
            ]
    except Exception:
        pass
    return {
        "total_companies": total,
        "active_companies": active,
        "inactive_companies": inactive,
        "online_users": online,
        "logins_today": online,
        "disk_percent": pct,
        "disk_usage": disk_str,
        "backup_coverage": backup_coverage,
        "pending_commands": pending_commands,
        "failed_commands": failed_commands,
        "expiring_licenses": expiring_licenses,
        "recent_logs": logs_data,
    }


def admin_list_companies(search: str = "", product_code: str = "") -> list:
    """List all companies with optional search filter."""
    tenants = _admin_tenants_all()
    result = []
    for t in tenants:
        if product_code and str(t.get("product_code") or "teknik_servis") != product_code:
            continue
        name = str(t.get("company_name") or "")
        if search and search.lower() not in name.lower():
            continue
        profile = _tenant_company_profile(t)
        extra = {"last_login": None, "license_type": t.get("license_type", "Standart"),
                 "license_end": t.get("license_end"),
                 "contact_name": t.get("contact_name") or profile.get("authorized_person"),
                 "phone": t.get("phone") or profile.get("phone"),
                 "email": t.get("email") or profile.get("email"),
                 "company_address": t.get("company_address") or profile.get("address")}
        result.append({**dict(t), **extra})
    return result


def _tenant_company_profile(tenant: dict) -> dict:
    """Read legacy company details without allowing a broken tenant to block admin lists."""
    path = _tenant_path(tenant)
    if not path.exists():
        return {}
    try:
        with closing(_raw_connect(path)) as conn:
            row = conn.execute("SELECT * FROM company_info LIMIT 1").fetchone()
            return dict(row) if row else {}
    except Exception:
        return {}


def admin_company_detail(tenant_id: str) -> dict:
    """Single company detail."""
    with closing(registry_connect()) as conn:
        t = conn.execute("SELECT * FROM tenants WHERE id=?", (tenant_id,)).fetchone()
        if not t:
            raise LookupError("Firma bulunamadi")
    return dict(t)


def admin_customer_360(tenant_id: str) -> dict:
    """Return the support-facing 360 view for one tenant."""
    tenant_id = str(tenant_id or "").strip()
    company = admin_company_detail(tenant_id)
    users = admin_company_users(tenant_id)
    licenses = [
        item for item in admin_list_licenses(str(company.get("product_code") or ""))
        if str(item.get("tenant_id") or "") == tenant_id
    ]
    backups = admin_list_backups(tenant_id)
    logs = admin_error_logs(tenant_id, 25)
    audit = admin_audit_logs(tenant_id, 50)
    live = [
        item for item in admin_live_status()
        if str(item.get("tenant_id") or "") == tenant_id
    ]
    return {
        "company": company,
        "users": users,
        "licenses": licenses,
        "backups": backups,
        "error_logs": logs,
        "audit_logs": audit,
        "live_status": live[0] if live else None,
        "summary": {
            "user_count": len(users),
            "backup_count": len(backups),
            "error_count": len(logs),
            "audit_count": len(audit),
            "online": bool(live),
        },
    }


def admin_update_company(tenant_id: str, data: dict, actor: dict | None = None) -> dict:
    """Update company active status or metadata."""
    tenant_id = str(tenant_id or "").strip()
    with closing(registry_connect()) as conn:
        row = conn.execute("SELECT * FROM tenants WHERE id=?", (tenant_id,)).fetchone()
        if not row:
            raise LookupError("Firma bulunamadi")
        tenant = dict(row)
        device_hardware = str(data.get("hardware_id") or "").strip()
        device_installation = str(data.get("installation_id") or "").strip()
        if device_hardware:
            if len(device_hardware) < 12 or len(device_hardware) > 256:
                raise ValueError("Gecersiz donanim kimligi")
            if len(device_installation) > 256:
                raise ValueError("Gecersiz kurulum kimligi")
            device_muted = str(data.get("muted", "")).casefold() in {"1", "true", "yes", "on"}
            if device_muted:
                conn.execute(
                    "INSERT OR REPLACE INTO muted_devices(tenant_id,product_code,hardware_id,installation_id,muted_at,reason) VALUES (?,?,?,?,?,?)",
                    (tenant_id, str(tenant.get("product_code") or "teknik_servis"), device_hardware, device_installation,
                     utc_now().isoformat(timespec="seconds"), str(data.get("muted_reason") or "Yonetici tarafindan susturuldu.")[:500]),
                )
            else:
                # The admin UI may only know the hardware identity.  In that
                # case remove every mute entry for that device; otherwise an
                # installation-scoped row would survive and keep the device
                # blocked after the operator re-activates it.
                product = str(tenant.get("product_code") or "teknik_servis")
                if device_installation:
                    conn.execute(
                        "DELETE FROM muted_devices WHERE tenant_id=? AND product_code=? "
                        "AND hardware_id=? AND (installation_id=? OR installation_id='')",
                        (tenant_id, product, device_hardware, device_installation),
                    )
                else:
                    conn.execute(
                        "DELETE FROM muted_devices WHERE tenant_id=? AND product_code=? AND hardware_id=?",
                        (tenant_id, product, device_hardware),
                    )
            conn.commit()
            if not any(key in data for key in ("active", "company_name", "license_type", "license_end", "license_start", "contact_name", "phone", "email", "sector", "company_address", "installation_lat", "installation_lng")):
                return {"ok": True, "tenant_id": tenant_id, "hardware_id": device_hardware, "installation_id": device_installation, "muted": device_muted}
        allowed = {k: data[k] for k in ("active", "muted", "muted_reason", "company_name", "license_type",
                                         "license_end", "license_start", "contact_name",
                                         "phone", "email", "sector", "company_address",
                                         "installation_lat", "installation_lng") if k in data}
        if device_hardware:
            allowed.pop("muted", None)
            allowed.pop("muted_reason", None)
        if not allowed:
            raise ValueError("Guncellenecek alan bulunamadi")
        if "sector" in allowed:
            sector = str(allowed["sector"] or "").strip()
            if sector not in {"teknik_servis", "otomotiv"}:
                raise ValueError("Gecersiz sektor")
            allowed["sector"] = sector
            tenant_path = _tenant_path(tenant)
            if not tenant_path.exists():
                raise FileNotFoundError("Firma veritabani bulunamadi")
            with closing(_raw_connect(tenant_path)) as tenant_conn:
                _ensure_path_schema(tenant_conn, tenant_path)
                upsert_setting(tenant_conn, "internal_settings", "current_sector", sector)
                tenant_conn.commit()
        if "company_address" in allowed and "installation_lat" not in allowed and "installation_lng" not in allowed:
            latitude, longitude = resolve_installation_location(str(allowed["company_address"] or ""))
            if latitude is not None and longitude is not None:
                allowed["installation_lat"] = latitude
                allowed["installation_lng"] = longitude
        if "company_address" in allowed or "installation_lat" in allowed or "installation_lng" in allowed:
            allowed["location_updated_at"] = utc_now().isoformat(timespec="seconds")
        if "muted" in allowed:
            allowed["muted"] = 1 if str(allowed["muted"]).casefold() in {"1", "true", "yes", "on"} else 0
            allowed["muted_at"] = utc_now().isoformat(timespec="seconds") if allowed["muted"] else None
            if not allowed["muted"]:
                allowed["muted_reason"] = ""
        if "active" in allowed:
            allowed["active"] = 1 if str(allowed["active"]).casefold() in {"1", "true", "yes", "on", "aktif"} else 0
        sets = ", ".join(f'"{k}"=?' for k in allowed)
        vals = list(allowed.values()) + [tenant_id]
        conn.execute(f"UPDATE tenants SET {sets} WHERE id=?", vals)
        conn.commit()
    if actor:
        _support_audit(
            actor,
            "admin_company_updated",
            tenant_id,
            detail={key: allowed[key] for key in allowed},
        )
    return {
        "ok": True,
        "tenant_id": tenant_id,
        "active": int(allowed.get("active", tenant.get("active") or 0)),
        "muted": int(allowed.get("muted", tenant.get("muted") or 0)),
        "sector": allowed.get("sector", tenant.get("sector") or "teknik_servis"),
    }


def admin_refresh_company_locations(actor: dict | None = None) -> dict:
    """Fill missing map coordinates using each registered company address once."""
    if not is_control_admin(actor):
        raise PermissionError("Platform operator permission is required")
    updated = 0
    skipped = 0
    for tenant in _admin_tenants_all():
        if tenant.get("installation_lat") is not None and tenant.get("installation_lng") is not None:
            skipped += 1
            continue
        profile = _tenant_company_profile(tenant)
        address = str(tenant.get("company_address") or profile.get("address") or "").strip()
        latitude, longitude = resolve_installation_location(address)
        if latitude is None or longitude is None:
            skipped += 1
            continue
        with closing(registry_connect()) as conn:
            conn.execute(
                "UPDATE tenants SET company_address=?,installation_lat=?,installation_lng=?,location_updated_at=? WHERE id=?",
                (address, latitude, longitude, utc_now().isoformat(timespec="seconds"), tenant["id"]),
            )
            conn.commit()
        updated += 1
    _support_audit(actor, "admin_company_locations_refreshed", detail={"updated": updated, "skipped": skipped})
    return {"ok": True, "updated": updated, "skipped": skipped}


def admin_delete_company(tenant_id: str, actor: dict | None = None) -> dict:
    """Archive a tenant database and remove the company from the active registry."""
    if not is_control_admin(actor):
        raise PermissionError("Platform operator permission is required")
    tenant_id = str(tenant_id or "").strip()
    actor_tenant_id = str(dict(actor or {}).get("_tenant_id") or "")
    if not tenant_id:
        raise ValueError("Firma kimligi zorunludur")
    if tenant_id == actor_tenant_id:
        raise PermissionError("Platform yonetici firmasini silemezsiniz")
    with closing(registry_connect()) as conn:
        row = conn.execute("SELECT * FROM tenants WHERE id=?", (tenant_id,)).fetchone()
        if not row:
            raise LookupError("Firma bulunamadi")
        tenant = dict(row)
        control_owner = conn.execute(
            "SELECT 1 FROM control_admins WHERE tenant_id=? LIMIT 1", (tenant_id,)
        ).fetchone()
        if control_owner:
            raise PermissionError("Platform yoneticisi olan firma silinemez")
    source = _tenant_path(tenant)
    if not source.exists():
        raise FileNotFoundError("Firma veritabani bulunamadi")
    archive_root = (ROOT / "deleted_tenants").resolve()
    archive_root.mkdir(parents=True, exist_ok=True)
    stamp = utc_now().strftime("%Y%m%d-%H%M%S")
    archive_path = archive_root / f"{stamp}-{source.name}"
    suffix = 2
    while archive_path.exists():
        archive_path = archive_root / f"{stamp}-{suffix}-{source.name}"
        suffix += 1
    shutil.move(str(source), str(archive_path))
    try:
        with closing(registry_connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("DELETE FROM control_admins WHERE tenant_id=?", (tenant_id,))
            conn.execute("DELETE FROM support_backups WHERE tenant_id=?", (tenant_id,))
            conn.execute("DELETE FROM desktop_commands WHERE tenant_id=? OR created_by_tenant_id=?", (tenant_id, tenant_id))
            conn.execute("DELETE FROM password_reset_tokens WHERE tenant_id=? OR created_by_tenant_id=?", (tenant_id, tenant_id))
            conn.execute("DELETE FROM provision_invites WHERE created_by_tenant_id=?", (tenant_id,))
            conn.execute("DELETE FROM tenants WHERE id=?", (tenant_id,))
            conn.commit()
    except Exception:
        shutil.move(str(archive_path), str(source))
        raise
    _support_audit(
        actor,
        "admin_company_deleted",
        tenant_id,
        detail={"company_name": tenant["company_name"], "archive": archive_path.name},
    )
    return {"ok": True, "tenant_id": tenant_id, "archive": archive_path.name}


def admin_company_users(tenant_id: str) -> list:
    """List users in a specific tenant database."""
    with closing(registry_connect()) as conn:
        t = conn.execute("SELECT db_filename FROM tenants WHERE id=?", (tenant_id,)).fetchone()
        if not t:
            return []
        filename = t[0]
    path = TENANT_ROOT / filename
    if not path.exists():
        return []
    private = {"password", "remember_token", "secret_answer", "security_answer_hash",
               "reset_token", "reset_token_expires"}
    with closing(_raw_connect(path)) as conn:
        _ensure_path_schema(conn, path)
        user_rows = rows(conn, "SELECT * FROM users ORDER BY id")
    return [{k: v for k, v in u.items() if k not in private} for u in user_rows]


def admin_repair_company_users(
    tenant_id: str, actor: dict | None = None
) -> dict:
    """Restore missing authentication users from the latest pre-wipe backup."""
    tenant_id = str(tenant_id or "").strip()
    with closing(registry_connect()) as registry:
        tenant = registry.execute(
            "SELECT db_filename FROM tenants WHERE id=?", (tenant_id,)
        ).fetchone()
        backup = registry.execute(
            "SELECT id,filename FROM support_backups "
            "WHERE tenant_id=? AND source='pre-wipe' AND status='available' "
            "ORDER BY datetime(created_at) DESC,id DESC LIMIT 1",
            (tenant_id,),
        ).fetchone()
    if not tenant:
        raise LookupError("Firma bulunamadi")
    if not backup:
        raise LookupError("Korunan silme-oncesi yedek bulunamadi")

    tenant_path = TENANT_ROOT / Path(str(tenant[0])).name
    backup_path = (SUPPORT_BACKUP_ROOT / tenant_id / Path(str(backup[1])).name).resolve()
    backup_root = SUPPORT_BACKUP_ROOT.resolve()
    if backup_root not in backup_path.parents or not backup_path.exists():
        raise FileNotFoundError("Korunan yedek dosyasi bulunamadi")
    if not tenant_path.exists():
        raise FileNotFoundError("Firma veritabani bulunamadi")

    with closing(_raw_connect(tenant_path)) as target:
        _ensure_path_schema(target, tenant_path)
        current_count = int(
            target.execute("SELECT COUNT(*) FROM users").fetchone()[0] or 0
        )
        if current_count:
            return {"ok": True, "restored_users": 0, "already_present": True}
        target_columns = {
            row[1] for row in target.execute('PRAGMA table_info("users")')
        }
        with closing(_raw_connect(backup_path)) as source:
            source_columns = {
                row[1] for row in source.execute('PRAGMA table_info("users")')
            }
            columns = sorted(target_columns & source_columns)
            if not columns:
                raise RuntimeError("Yedekte kullanici semasi bulunamadi")
            column_sql = ",".join(f'"{column}"' for column in columns)
            user_rows = source.execute(
                f"SELECT {column_sql} FROM users ORDER BY id"
            ).fetchall()
        if not user_rows:
            raise LookupError("Korunan yedekte kullanici kaydi bulunamadi")
        placeholders = ",".join("?" for _ in columns)
        target.executemany(
            f"INSERT OR IGNORE INTO users ({column_sql}) VALUES ({placeholders})",
            [tuple(row[column] for column in columns) for row in user_rows],
        )
        target.commit()
        restored = int(target.execute("SELECT COUNT(*) FROM users").fetchone()[0] or 0)

    _support_audit(
        actor,
        "admin_company_users_repaired",
        tenant_id,
        detail={"backup_id": int(backup[0]), "restored_users": restored},
    )
    return {
        "ok": True,
        "restored_users": restored,
        "backup_id": int(backup[0]),
    }


def admin_reset_user_password(
    tenant_id: str,
    user_id: int,
    new_password: str,
    actor: dict | None = None,
) -> dict:
    """Set a new hashed password for a specific user in a tenant DB."""
    if not new_password or len(new_password) < 6:
        raise ValueError("Sifre en az 6 karakter olmali")
    with closing(registry_connect()) as conn:
        t = conn.execute("SELECT db_filename FROM tenants WHERE id=?", (tenant_id,)).fetchone()
        if not t:
            raise LookupError("Firma bulunamadi")
        filename = t[0]
    path = TENANT_ROOT / filename
    if not path.exists():
        raise LookupError("Firma veritabani dosyasi bulunamadi")
    hashed = password_hash(new_password)
    with closing(_raw_connect(path)) as conn:
        cursor = conn.execute("UPDATE users SET password=? WHERE id=?", (hashed, user_id))
        if cursor.rowcount != 1:
            raise LookupError("Kullanici bulunamadi")
        conn.commit()
    _support_audit(actor, "admin_password_reset", tenant_id, user_id)
    return {"ok": True, "user_id": user_id}


def admin_send_temporary_password(
    tenant_id: str,
    user_id: int,
    actor: dict | None = None,
) -> dict:
    """Generate a one-time temporary password and send it by email."""
    tenant_id = str(tenant_id or "").strip()
    with closing(registry_connect()) as registry:
        tenant = registry.execute("SELECT * FROM tenants WHERE id=?", (tenant_id,)).fetchone()
    if not tenant:
        raise LookupError("Firma bulunamadi")
    path = _tenant_path(dict(tenant))
    if not path.exists():
        raise FileNotFoundError("Firma veritabani bulunamadi")
    temporary_password = secrets.token_urlsafe(9) + "Aa1"
    temporary_expires_at = utc_now() + timedelta(minutes=30)
    with closing(_raw_connect(path)) as conn:
        _ensure_path_schema(conn, path)
        conn.execute("BEGIN IMMEDIATE")
        user = conn.execute(
            "SELECT id,username,email,active FROM users WHERE id=?", (int(user_id),)
        ).fetchone()
        if not user:
            conn.rollback()
            raise LookupError("Kullanici bulunamadi")
        recipient = str(user["email"] or "").strip()
        if not valid_email(recipient) or not int(user["active"] or 0):
            conn.rollback()
            raise ValueError("Kullanicinin e-posta adresi bulunamadi")
        conn.execute(
            "UPDATE users SET password=?,must_change_password=1,temporary_password_expires_at=?,remember_token=NULL,auto_login=0 WHERE id=?",
            (password_hash(temporary_password), temporary_expires_at.isoformat(timespec="seconds"), int(user_id)),
        )
        conn.execute("DELETE FROM web_sessions WHERE user_id=?", (int(user_id),))
        try:
            mail_sent, mail_message = send_license_email(
                tenant_id,
                recipient,
                "AYEC Pro gecici parola",
                (
                    f"Merhaba {user['username'] or ''},\n\n"
                    f"Gecici parolaniz: {temporary_password}\n\n"
                    f"Bu parola {temporary_expires_at.isoformat(timespec='seconds')} UTC tarihine kadar gecerlidir.\n"
                    "Ilk giriste yeni bir parola belirlemeniz istenecektir.\n"
                    "Bu e-postayi siz istemediyseniz destek ekibinizle iletisime gecin."
                ),
            )
        except Exception:
            conn.rollback()
            raise
        if mail_sent:
            conn.commit()
        else:
            conn.rollback()
    _support_audit(
        actor,
        "temporary_password_email_sent" if mail_sent else "temporary_password_email_failed",
        tenant_id,
        int(user_id),
        detail={"recipient": recipient, "message": mail_message},
    )
    return {
        "ok": True,
        "user_id": int(user_id),
        "recipient": recipient,
        "mail_sent": mail_sent,
        "mail_message": mail_message,
        "expires_at": temporary_expires_at.isoformat(timespec="seconds") if mail_sent else None,
    }


def admin_list_licenses(product_code: str = "") -> list:
    """List all tenant license information."""
    with closing(registry_connect()) as conn:
        tenant_list = rows(conn, "SELECT id, company_name, product_code, license_type, license_code, license_start, license_end, license_status, license_updated_at, active FROM tenants ORDER BY created_at, id")
        for tenant in tenant_list:
            if product_code and str(tenant.get("product_code") or "teknik_servis") != product_code:
                continue
            if str(tenant.get("license_code") or "").strip():
                continue
            # Older tenants may predate the license-code column. Generate one
            # once when the administrator first opens the license list.
            generated_code = "AYEC-" + secrets.token_hex(24).upper()
            conn.execute(
                "UPDATE tenants SET license_code=? WHERE id=? AND COALESCE(license_code,'')=''",
                (generated_code, tenant["id"]),
            )
            tenant["license_code"] = generated_code
        conn.commit()
    result = []
    for t in tenant_list:
        access = tenant_access_summary(t)
        status = "Aktif" if access["allowed"] else "Pasif"
        result.append({
            "tenant_id": t["id"],
            "company_name": t.get("company_name", "?"),
            "product_code": t.get("product_code", "teknik_servis") or "teknik_servis",
            "license_type": t.get("license_type", "Standart"),
            "license_code": t.get("license_code", ""),
            "license_start": t.get("license_start", ""),
            "license_end": t.get("license_end", ""),
            "license_updated_at": t.get("license_updated_at", ""),
            "status": status,
        })
    return result


def admin_licenses_usage() -> list:
    """Calculate DB size, user counts, and basic limits for all tenants."""
    tenants = _admin_tenants_all()
    usages = []
    for t in tenants:
        tid = t["id"]
        filename = t["db_filename"]
        path = TENANT_ROOT / filename
        db_size_mb = 0.0
        users_count = 0
        devices_count = 0
        services_count = 0
        if path.exists():
            try:
                db_size_mb = path.stat().st_size / (1024 * 1024)
                with closing(_raw_connect(path)) as conn:
                    # Count users
                    if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'").fetchone():
                        users_count = scalar(conn, "SELECT COUNT(*) FROM users", default=0)
                    # Count devices
                    if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='devices'").fetchone():
                        devices_count = scalar(conn, "SELECT COUNT(*) FROM devices", default=0)
                    # Count service forms
                    if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='services'").fetchone():
                        services_count = scalar(conn, "SELECT COUNT(*) FROM services", default=0)
            except Exception:
                pass
        usages.append({
            "tenant_id": tid,
            "company_name": t.get("company_name", "?"),
            "db_size_mb": db_size_mb,
            "users_count": users_count,
            "users_limit": 10,
            "devices_count": devices_count,
            "devices_limit": 100,
            "services_count": services_count,
            "services_limit": 1000
        })
    return usages


def admin_execute_query(tenant_id: str, sql: str, actor: dict | None = None) -> dict:
    """Execute a bounded read-only diagnostic query in a tenant database."""
    with closing(registry_connect()) as conn:
        t = conn.execute("SELECT db_filename FROM tenants WHERE id=?", (tenant_id,)).fetchone()
        if not t:
            raise LookupError("Firma bulunamadi")
        filename = t[0]
    path = TENANT_ROOT / filename
    if not path.exists():
        raise LookupError("Veritabani dosyasi bulunamadi")
    
    query = str(sql or "").strip()
    if not query:
        raise ValueError("Sorgu metni bos olamaz")
    without_trailing = query[:-1].rstrip() if query.endswith(";") else query
    if ";" in without_trailing:
        raise PermissionError("Ayni istekte yalnizca bir sorgu calistirilabilir")
    normalized = re.sub(
        r"^(?:(?:\s*--[^\n]*(?:\n|$))|(?:\s*/\*.*?\*/\s*))*",
        "",
        without_trailing,
        flags=re.DOTALL,
    ).strip().lower()
    safe_pragmas = (
        "pragma table_info",
        "pragma table_list",
        "pragma index_list",
        "pragma index_info",
        "pragma foreign_key_list",
        "pragma integrity_check",
        "pragma quick_check",
    )
    is_select = normalized == "select" or normalized.startswith("select ")
    is_explain = normalized.startswith("explain query plan select ")
    is_safe_pragma = any(normalized.startswith(prefix) for prefix in safe_pragmas)
    if not (is_select or is_explain or is_safe_pragma):
        raise PermissionError(
            "Uzak SQL yalnizca SELECT, EXPLAIN QUERY PLAN ve guvenli PRAGMA sorgularini kabul eder"
        )

    with closing(_raw_connect(path)) as conn:
        conn.execute("PRAGMA query_only=ON")
        conn.row_factory = None
        cursor = conn.execute(without_trailing)
        columns = [col[0] for col in cursor.description]
        rows_data = cursor.fetchmany(1001)
        truncated = len(rows_data) > 1000
        rows_data = rows_data[:1000]
    _support_audit(
        actor,
        "admin_readonly_query",
        tenant_id,
        detail={"statement": normalized.split(None, 1)[0], "rows": len(rows_data)},
    )
    return {"ok": True, "columns": columns, "rows": rows_data, "truncated": truncated}


def create_license_order(user: dict, data: dict) -> dict:
    tenant_id = str(user.get("_tenant_id") or "").strip()
    if not tenant_id:
        raise PermissionError("Firma bilgisi bulunamadi.")
    plan = _license_plan(str(data.get("plan_code") or ""))
    hardware_id = str(data.get("hardware_id") or "").strip()
    if len(hardware_id) < 12:
        raise ValueError("Donanim kimligi zorunludur.")
    with closing(registry_connect()) as conn:
        row = _tenant_row_any(conn, tenant_id)
    tenant = dict(row) if row else None
    if not tenant:
        raise LookupError("Firma bulunamadi.")
    if int(tenant.get("muted") or 0) == 1:
        raise PermissionError("Firma susturuldu. Yonetici ile iletisime gecin.")
    now = utc_now().isoformat(timespec="seconds")
    payment_reported = bool(data.get("payment_reported"))
    initial_status = "payment_reported" if payment_reported else "payment_pending"
    with closing(registry_connect()) as conn:
        request_no, payment_reference = _new_license_reference(conn)
        cursor = conn.execute(
            "INSERT INTO license_orders "
            "(request_no,tenant_id,product_code,requester_user_id,requester_name,requester_email,requester_phone,hardware_id,installation_id,location_json,"
            "plan_code,plan_label,duration_months,amount_try,currency,payment_reference,status,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                request_no, tenant_id, str(data.get("product_code") or tenant.get("product_code") or "teknik_servis"), int(user.get("id") or 0),
                str(user.get("full_name") or user.get("username") or ""),
                str(user.get("email") or ""), str(user.get("phone") or ""), hardware_id,
                str(data.get("installation_id") or ""),
                json.dumps(data.get("location") or data.get("location_json") or {}, ensure_ascii=False),
                plan["code"], plan["label"], plan["duration_months"], plan["amount_try"],
                plan["currency"], payment_reference, initial_status, now, now,
            ),
        )
        order_id = int(cursor.lastrowid)
        if payment_reported:
            conn.execute(
                "UPDATE license_orders SET payment_reported_at=?,payment_note=? WHERE id=?",
                (now, "Musteri masaustu uygulamasindan odeme bildirdi.", order_id),
            )
        item = dict(conn.execute(
            "SELECT o.*,t.company_name FROM license_orders o JOIN tenants t ON t.id=o.tenant_id WHERE o.id=?",
            (order_id,),
        ).fetchone())
        conn.commit()
    profile = license_payment_profile()
    order = _license_request_payload(item)
    mail_text = (
        f"AYEC Pro lisans talebiniz alindi.\n\nFirma: {order['company_name']}\n"
        f"Paket: {order['plan_label']}\nTutar: {order['amount_try']:.2f} TRY\n"
        f"Odeme aciklamasi: {order['payment_reference']}\n"
        f"Banka: {profile['bank_name']}\nAlici: {profile['account_holder']}\nIBAN: {profile['iban']}\n\n"
        + (
            "Odeme bildiriminiz yonetime iletildi."
            if payment_reported
            else "Odeme sonrasinda uygulamadaki 'Odemeyi yaptim' secenegini kullanin."
        )
    )
    customer_sent, customer_note = send_license_email(tenant_id, order["requester_email"], "AYEC Pro Lisans Talebi", mail_text)
    admin_subject = (
        "AYEC Pro Odeme Yapildi - Lisans Talebi"
        if payment_reported
        else "AYEC Pro Yeni Lisans Talebi"
    )
    admin_sent, admin_note = send_license_email(
        tenant_id, SUPPORT_EMAIL, admin_subject,
        f"Tarih/Saat: {now} UTC\nTalep: {order['request_no']}\n"
        f"Odeme durumu: {'Odeme bildirildi' if payment_reported else 'Odeme bekleniyor'}\n"
        f"Firma: {order['company_name']}\nTalep eden: {order['requester_name']}\n"
        f"E-posta: {order['requester_email']}\nTelefon: {order['requester_phone']}\n"
        f"Paket: {order['plan_label']}\nTutar: {order['amount_try']:.2f} TRY\n"
        f"Odeme aciklamasi: {order['payment_reference']}\nHWID: {order['hardware_id']}\n"
        f"Konum: {order.get('location_json') or '{}'}",
    )
    _support_audit(user, "license_order_created", tenant_id, detail={"order_id": order_id, "plan": plan["code"]})
    return {
        "ok": True, "order": order, "payment": profile,
        "mail": {"customer_sent": customer_sent, "customer_message": customer_note,
                 "admin_sent": admin_sent, "admin_message": admin_note,
                 "admin_recipient": SUPPORT_EMAIL},
    }


def report_license_payment(user: dict, order_id: int, data: dict) -> dict:
    tenant_id = str(user.get("_tenant_id") or "").strip()
    note = str(data.get("payment_note") or "").strip()[:1000]
    now = utc_now().isoformat(timespec="seconds")
    with closing(registry_connect()) as conn:
        row = conn.execute("SELECT * FROM license_orders WHERE id=? AND tenant_id=?", (int(order_id), tenant_id)).fetchone()
        if not row:
            raise LookupError("Lisans talebi bulunamadi.")
        if str(row["status"]) in {"active", "rejected", "cancelled"}:
            raise ValueError("Bu lisans talebinin durumu degistirilemez.")
        conn.execute(
            "UPDATE license_orders SET status='payment_reported',payment_reported_at=?,payment_note=?,updated_at=? WHERE id=?",
            (now, note, now, int(order_id)),
        )
        item = dict(conn.execute(
            "SELECT o.*,t.company_name FROM license_orders o JOIN tenants t ON t.id=o.tenant_id WHERE o.id=?",
            (int(order_id),),
        ).fetchone())
        conn.commit()
    admin_sent, admin_note = send_license_email(
        tenant_id, SUPPORT_EMAIL, "AYEC Pro Odeme Bildirimi",
        f"Odeme bildirildi. Talep: {item['request_no']}\nFirma: {item['company_name']}\n"
        f"Tutar: {float(item['amount_try']):.2f} TRY\nAciklama: {item['payment_reference']}\nNot: {note}",
    )
    _support_audit(user, "license_payment_reported", tenant_id, detail={"order_id": int(order_id)})
    return {
        "ok": True,
        "order": _license_request_payload(item),
        "mail": {
            "admin_sent": admin_sent,
            "admin_message": admin_note,
            "admin_recipient": SUPPORT_EMAIL,
        },
    }


def list_license_orders(tenant_id: str = "", limit: int = 250, status: str = "", product_code: str = "") -> list[dict]:
    sql = "SELECT o.*,t.company_name FROM license_orders o JOIN tenants t ON t.id=o.tenant_id"
    clauses: list[str] = []
    params: tuple = ()
    if tenant_id:
        clauses.append("o.tenant_id=?")
        params = (tenant_id,)
    if status:
        clauses.append("o.status=?")
        params += (status,)
    if product_code:
        clauses.append("COALESCE(t.product_code,'teknik_servis')=?")
        params += (product_code,)
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY CASE o.status WHEN 'payment_reported' THEN 0 WHEN 'payment_pending' THEN 1 ELSE 2 END,o.created_at DESC LIMIT ?"
    params += (max(1, min(int(limit), 1000)),)
    with closing(registry_connect()) as conn:
        return [_license_request_payload(dict(row)) for row in conn.execute(sql, params)]


def approve_license_order(order_id: int, data: dict, actor: dict) -> dict:
    requested = str(data.get("plan_code") or "").strip()
    admin_note = str(data.get("admin_note") or "").strip()[:1000]
    with closing(registry_connect()) as conn:
        row = conn.execute("SELECT * FROM license_orders WHERE id=?", (int(order_id),)).fetchone()
        if not row:
            raise LookupError("Lisans talebi bulunamadi.")
        if str(row["status"]) == "active":
            raise ValueError("Bu lisans talebi zaten etkinlestirilmis.")
        if str(row["status"]) != "payment_reported":
            raise ValueError("Odeme bildirimi bekleyen lisans talebi onaylanamaz.")
        plan = _license_plan(requested or str(row["plan_code"]))
        start = utc_now()
        end = _license_add_months(start, plan["duration_months"])
        now = start.isoformat(timespec="seconds")
        license_code = "AYEC-" + secrets.token_hex(24).upper()
        conn.execute(
            "UPDATE tenants SET active=1,license_type=?,license_code=?,license_status='Active',license_start=?,"
            "license_end=?,license_updated_at=? WHERE id=?",
            (
                plan["label"], license_code, now, end.isoformat(timespec="seconds"), now,
                str(row["tenant_id"]),
            ),
        )
        conn.execute(
            "UPDATE license_orders SET plan_code=?,plan_label=?,duration_months=?,amount_try=?,license_code=?,status='active',admin_note=?,"
            "approved_by_user_id=?,approved_at=?,license_start=?,license_end=?,updated_at=? WHERE id=?",
            (plan["code"], plan["label"], plan["duration_months"], plan["amount_try"], license_code, admin_note,
             int(actor.get("id") or 0), now, now, end.isoformat(timespec="seconds"), now, int(order_id)),
        )
        item = dict(conn.execute(
            "SELECT o.*,t.company_name FROM license_orders o JOIN tenants t ON t.id=o.tenant_id WHERE o.id=?",
            (int(order_id),),
        ).fetchone())
        conn.commit()
    tenant_id = str(item["tenant_id"])
    mail_sent, mail_message = send_license_email(
        tenant_id, str(item.get("requester_email") or ""), "AYEC Pro Lisansiniz Etkinlestirildi",
        f"Lisansiniz etkinlestirildi.\nFirma: {item['company_name']}\nPaket: {item['plan_label']}\n"
        f"Baslangic: {item['license_start']}\nBitis: {item['license_end']}\nLisans Kodu: {license_code}",
    )
    SYNC_EVENT_HUB.publish(tenant_id, {"type": "license_updated"})
    _support_audit(actor, "license_order_approved", tenant_id, detail={"order_id": int(order_id), "plan": plan["code"], "mail_sent": mail_sent})
    return {"ok": True, "order": _license_request_payload(item), "license": tenant_access_summary(tenant_by_id(tenant_id)), "mail_sent": mail_sent, "mail_message": mail_message}


def reject_license_order(order_id: int, data: dict, actor: dict) -> dict:
    note = str(data.get("admin_note") or "").strip()[:1000]
    if not note:
        raise ValueError("Red gerekcesi zorunludur.")
    now = utc_now().isoformat(timespec="seconds")
    with closing(registry_connect()) as conn:
        row = conn.execute("SELECT o.*,t.company_name FROM license_orders o JOIN tenants t ON t.id=o.tenant_id WHERE o.id=?", (int(order_id),)).fetchone()
        if not row:
            raise LookupError("Lisans talebi bulunamadi.")
        if str(row["status"]) == "active":
            raise ValueError("Etkin lisans talebi reddedilemez.")
        conn.execute("UPDATE license_orders SET status='rejected',admin_note=?,updated_at=? WHERE id=?", (note, now, int(order_id)))
        item = dict(conn.execute("SELECT o.*,t.company_name FROM license_orders o JOIN tenants t ON t.id=o.tenant_id WHERE o.id=?", (int(order_id),)).fetchone())
        conn.commit()
    send_license_email(str(item["tenant_id"]), str(item.get("requester_email") or ""), "AYEC Pro Lisans Talebi", f"Talebiniz isleme alinamadi. Gerekce: {note}")
    _support_audit(actor, "license_order_rejected", str(item["tenant_id"]), detail={"order_id": int(order_id)})
    return {"ok": True, "order": _license_request_payload(item)}


def cancel_license_order(order_id: int, data: dict, actor: dict) -> dict:
    note = str(data.get("admin_note") or "Yonetim panelinden iptal edildi.").strip()[:1000]
    now = utc_now().isoformat(timespec="seconds")
    with closing(registry_connect()) as conn:
        row = conn.execute(
            "SELECT o.*,t.company_name,t.email AS company_email FROM license_orders o "
            "JOIN tenants t ON t.id=o.tenant_id WHERE o.id=?",
            (int(order_id),),
        ).fetchone()
        if not row:
            raise LookupError("Lisans talebi bulunamadi.")
        if str(row["status"]) != "active":
            raise ValueError("Yalnizca aktif bir lisans iptal edilebilir.")
        tenant_id = str(row["tenant_id"])
        conn.execute(
            "UPDATE tenants SET active=0,license_status='Inactive',license_updated_at=? WHERE id=?",
            (now, tenant_id),
        )
        conn.execute(
            "UPDATE license_orders SET status='cancelled',admin_note=?,updated_at=? WHERE id=?",
            (note, now, int(order_id)),
        )
        item = dict(
            conn.execute(
                "SELECT o.*,t.company_name FROM license_orders o "
                "JOIN tenants t ON t.id=o.tenant_id WHERE o.id=?",
                (int(order_id),),
            ).fetchone()
        )
        conn.commit()
    recipient = str(row["requester_email"] or row["company_email"] or "")
    send_license_email(
        tenant_id,
        recipient,
        "AYEC Pro Lisans Durumu",
        f"Lisansiniz yonetim tarafindan iptal edildi.\nFirma: {item['company_name']}\n"
        f"Paket: {item['plan_label']}\nAciklama: {note}",
    )
    with closing(registry_connect()) as conn:
        tenant_after = _tenant_row_any(conn, tenant_id)
    license_payload = tenant_access_summary(dict(tenant_after) if tenant_after else None)
    SYNC_EVENT_HUB.publish(
        tenant_id,
        {"type": "license_updated", "license": license_payload},
    )
    _support_audit(
        actor,
        "license_order_cancelled",
        tenant_id,
        detail={"order_id": int(order_id), "note": note},
    )
    return {"ok": True, "order": _license_request_payload(item), "license": license_payload}


def license_status_for_user(user: dict) -> dict:
    with closing(registry_connect()) as conn:
        row = _tenant_row_any(conn, str(user.get("_tenant_id") or ""))
    tenant = dict(row) if row else None
    return {
        "ok": True,
        "access": tenant_access_summary(tenant),
        "plans": license_plan_catalog(),
        "payment": license_payment_profile(),
        "tenant": {
            "id": str((tenant or {}).get("id") or ""),
            "company_name": str((tenant or {}).get("company_name") or ""),
        },
    }


def license_user_from_credentials(data: dict) -> dict:
    identifier = str(data.get("identifier") or data.get("username") or "").strip()
    password = str(data.get("password") or "")
    tenant_id = str(data.get("tenant_id") or "").strip() or None
    if not identifier or not password:
        raise PermissionError("Kullanici adi ve parola zorunludur.")
    if tenant_id:
        with closing(registry_connect()) as conn:
            tenant = _tenant_row_any(conn, tenant_id)
        if not tenant:
            raise PermissionError("Firma bulunamadi.")
        set_tenant_context(dict(tenant))
        with closing(db_connect()) as conn:
            row = find_account_by_identifier(conn, identifier)
            if not row and normalize_identifier(identifier) == normalize_identifier(OFFICIAL_EMAIL):
                # Preserve the existing platform-owner credentials while the
                # public identity moves from the legacy Gmail address.
                row = find_account_by_identifier(conn, VENDOR_EMAIL)
            if not row or not password_matches(password, row["password"]):
                raise PermissionError("Kullanici adi/e-posta veya parola hatali.")
            user = dict(row)
            user["_tenant_id"] = str(tenant["id"])
            user["_company_name"] = str(tenant["company_name"])
    else:
        user = authenticate_account(identifier, password, None)
    if not user:
        raise PermissionError("Kullanici adi/e-posta veya parola hatali.")
    return user


def create_license_order_from_credentials(data: dict) -> dict:
    user = license_user_from_credentials(data)
    return create_license_order(user, data)


def license_user_from_device(data: dict, allow_provision: bool = False) -> dict:
    email = str(data.get("requester_email") or "").strip().lower()
    company_name = str(data.get("company_name") or "").strip()
    hardware_id = str(data.get("hardware_id") or "").strip()
    if not valid_email(email):
        raise ValueError("Kayitli firma e-posta adresi zorunludur.")
    if len(hardware_id) < 12:
        raise ValueError("Donanim kimligi zorunludur.")
    with closing(registry_connect()) as conn:
        tenants = [dict(row) for row in conn.execute(
            "SELECT * FROM tenants ORDER BY company_name"
        )]
    requested_tenant = str(data.get("tenant_id") or "").strip()
    requested_product = str(data.get("product_code") or "").strip()
    if requested_tenant:
        tenants = [tenant for tenant in tenants if str(tenant["id"]) == requested_tenant]
    matches = []
    for tenant in tenants:
        try:
            with closing(_raw_connect(_tenant_path(tenant))) as conn:
                row = find_account_by_identifier(conn, email)
        except sqlite3.Error:
            row = None
        if row:
            matches.append((tenant, dict(row)))
    if not matches:
        for tenant in tenants:
            tenant_email = str(tenant.get("email") or "").strip()
            if normalize_identifier(tenant_email) != normalize_identifier(email):
                continue
            matches.append((
                tenant,
                {
                    "id": 0,
                    "username": email,
                    "full_name": str(
                        data.get("requester_name")
                        or tenant.get("contact_name")
                        or tenant.get("company_name")
                        or ""
                    ),
                    "email": email,
                    "phone": str(
                        data.get("requester_phone") or tenant.get("phone") or ""
                    ),
                },
            ))
    if company_name:
        exact = [
            item for item in matches
            if str(item[0].get("company_name") or "").strip().casefold()
            == company_name.casefold()
        ]
        if exact:
            matches = exact
    if not matches and allow_provision and not str(data.get("tenant_id") or "").strip():
        identifier = str(data.get("identifier") or data.get("username") or "").strip()
        password = str(data.get("password") or "")
        if identifier and password:
            provisioned = provision_desktop_tenant({
                "username": identifier,
                "password": password,
                "full_name": str(data.get("requester_name") or identifier).strip(),
                "email": email,
                "phone": str(data.get("requester_phone") or "").strip(),
                "company_name": company_name,
                "company_email": email,
                "company_address": str(data.get("company_address") or "").strip(),
                "sector": str(data.get("sector") or "teknik_servis").strip(),
            })
            tenant_id = str(dict(provisioned.get("tenant") or {}).get("id") or "")
            tenant = tenant_by_id(tenant_id)
            if tenant:
                set_tenant_context(tenant)
                with closing(db_connect()) as conn:
                    row = find_account_by_identifier(conn, identifier)
                if row:
                    matches = [(tenant, dict(row))]
    if not matches:
        raise LookupError("Firma lisans servisinde bulunamadi.")
    if requested_product and not allow_provision:
        product_matches = [item for item in matches
                           if str(item[0].get("product_code") or "teknik_servis") == requested_product]
        if product_matches:
            matches = product_matches
    if len(matches) > 1:
        raise ValueError("E-posta birden fazla firmada kayitli. Firma adini kontrol edin.")
    tenant, user = matches[0]
    user["_tenant_id"] = str(tenant.get("id") or "")
    user["_company_name"] = str(tenant.get("company_name") or "")
    user["full_name"] = str(data.get("requester_name") or user.get("full_name") or "")
    user["phone"] = str(data.get("requester_phone") or user.get("phone") or "")
    return user


def create_license_order_from_device(data: dict) -> dict:
    return create_license_order(license_user_from_device(data, allow_provision=True), data)


def license_status_from_device(data: dict) -> dict:
    """Return an authenticated, scoped entitlement, including revoked tenants."""
    user = license_user_from_device(data)
    tenant_id = str(user["_tenant_id"])
    product = str(data.get("product_code") or "teknik_servis").strip()
    hardware = str(data.get("hardware_id") or "").strip()
    installation = str(data.get("installation_id") or "").strip()
    if product not in configured_product_codes():
        raise ValueError("Unknown product")
    with closing(registry_connect()) as conn:
        tenant = dict(_tenant_row_any(conn, tenant_id))
        device_mute = conn.execute(
            "SELECT 1 FROM muted_devices WHERE tenant_id=? AND product_code=? AND hardware_id=? "
            "AND (installation_id='' OR installation_id=?) LIMIT 1",
            (tenant_id, product, hardware, installation),
        ).fetchone()
        order = conn.execute(
            "SELECT * FROM license_orders WHERE tenant_id=? AND product_code=? AND hardware_id=? "
            "AND status IN ('active','cancelled') ORDER BY id DESC LIMIT 1",
            (tenant_id, product, hardware),
        ).fetchone()
    if device_mute:
        from Web_Arayuzu.central_entitlements import sign_access
        access = tenant_access_summary({**tenant, "muted": 1, "muted_reason": "Bu donanim yonetici tarafindan susturuldu."})
        access.update(product_code=product, tenant_id=tenant_id, hardware_id=hardware,
                      installation_id=installation, server_time=utc_now().isoformat(timespec="seconds"))
        return {"ok": True, "access": sign_access(access),
                "tenant": {"id": tenant_id, "company_name": str(tenant.get("company_name") or "")}}
    if order:
        order = dict(order)
        if order.get("installation_id") and order["installation_id"] != installation:
            raise PermissionError("Installation does not match the approved license")
        tenant.update(license_type=order["plan_label"], license_start=order["license_start"],
                      license_end=order["license_end"], license_code=order.get("license_code") or "")
        if order["status"] == "cancelled":
            tenant.update(active=0, license_status="Revoked")
    elif str(tenant.get("product_code") or "teknik_servis") != product:
        raise PermissionError("Product license is not registered")
    else:
        # First binding requires the centrally issued key or an authenticated
        # account; knowledge of an e-mail address and HWID is not activation.
        with closing(registry_connect()) as conn:
            binding = conn.execute(
                "SELECT installation_id FROM license_device_bindings "
                "WHERE tenant_id=? AND product_code=? AND hardware_id=?",
                (tenant_id, product, hardware),
            ).fetchone()
        if binding and binding["installation_id"] != installation:
            raise PermissionError("Installation identity mismatch")
        if not binding:
            supplied_key = str(data.get("license_key") or "")
            expected_key = str(tenant.get("license_code") or "")
            key_valid = bool(supplied_key and expected_key and hmac.compare_digest(supplied_key, expected_key))
            if not key_valid:
                credential_user = license_user_from_credentials(dict(data, tenant_id=tenant_id))
                if str(credential_user.get("_tenant_id")) != tenant_id:
                    raise PermissionError("License account identity mismatch")
    from Web_Arayuzu.central_entitlements import sign_access
    access = tenant_access_summary(tenant)
    access.update(product_code=product, tenant_id=tenant_id, hardware_id=hardware,
                  installation_id=installation, server_time=utc_now().isoformat(timespec="seconds"))
    signed = sign_access(access)
    if installation:
        with closing(registry_connect()) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO license_device_bindings "
                "(tenant_id,product_code,hardware_id,installation_id,created_at) VALUES (?,?,?,?,?)",
                (tenant_id, product, hardware, installation, utc_now().isoformat(timespec="seconds")),
            )
            conn.commit()
    return {"ok": True, "access": signed,
            "tenant": {"id": tenant_id, "company_name": str(tenant.get("company_name") or "")}}


def report_license_payment_from_credentials(order_id: int, data: dict) -> dict:
    user = license_user_from_credentials(data)
    return report_license_payment(user, order_id, data)


def license_status_from_credentials(data: dict) -> dict:
    user = license_user_from_credentials(data)
    return license_status_for_user(user)


def admin_update_license(tenant_id: str, data: dict, actor: dict | None = None) -> dict:
    """Update license fields for a tenant."""
    tenant_id = str(tenant_id or "").strip()
    with closing(registry_connect()) as conn:
        row = conn.execute("SELECT * FROM tenants WHERE id=?", (tenant_id,)).fetchone()
    if not row:
        raise LookupError("Firma bulunamadi")
    tenant = dict(row)
    current_active = int(tenant.get("active") or 0) == 1
    status = str(data.get("status") or ("Aktif" if current_active else "Pasif")).strip()
    license_type = str(
        data.get("license_type") or tenant.get("license_type") or "Standart"
    ).strip()
    is_active = status == "Aktif"
    is_lifetime = license_type.casefold() in {"lifetime", "suresiz", "sinirsiz"}
    now = utc_now()
    start_text = str(
        data.get("license_start") if "license_start" in data
        else tenant.get("license_start") or ""
    ).strip()
    end_text = str(
        data.get("license_end") if "license_end" in data
        else tenant.get("license_end") or ""
    ).strip()
    start = _parse_registry_time(start_text) if start_text else now
    end = _parse_registry_time(end_text) if end_text else None
    if start is None:
        raise ValueError("Lisans baslangic tarih ve saati gecersiz")
    if is_active and not is_lifetime and end is None:
        raise ValueError("Sureli lisans icin bitis tarih ve saati zorunludur")
    if is_active and end is not None and end <= start:
        raise ValueError("Lisans bitis zamani baslangictan sonra olmalidir")
    start_value = start.isoformat(timespec="seconds")
    end_value = "" if is_lifetime else (end.isoformat(timespec="seconds") if end else "")
    updated_at = now.isoformat(timespec="seconds")
    with closing(registry_connect()) as conn:
        conn.execute(
            "UPDATE tenants SET active=?,license_type=?,license_status=?,license_start=?,"
            "license_end=?,license_updated_at=? WHERE id=?",
            (
                1 if is_active else 0,
                license_type,
                "Active" if is_active else "Inactive",
                start_value,
                end_value,
                updated_at,
                tenant_id,
            ),
        )
        conn.commit()
    license_payload = tenant_access_summary(tenant_by_id(tenant_id))
    if is_active:
        end_label = end_value or "Suresiz"
        send_license_email(
            tenant_id,
            str(tenant.get("email") or ""),
            "AYEC Pro Lisansiniz Etkinlestirildi",
            f"Lisansiniz yonetim tarafindan etkinlestirildi.\n"
            f"Firma: {tenant.get('company_name') or '-'}\n"
            f"Lisans: {license_type}\nBaslangic: {start_value}\nBitis: {end_label}",
        )
    SYNC_EVENT_HUB.publish(
        tenant_id,
        {"type": "license_updated", "license": license_payload},
    )
    _support_audit(
        actor,
        "admin_license_updated",
        tenant_id,
        detail={
            "license_type": license_type,
            "status": status,
            "license_start": start_value,
            "license_end": end_value,
            "license_updated_at": updated_at,
        },
    )
    return {"ok": True, "license": license_payload}


def admin_list_backups(tenant_id: str) -> list:
    """List available backup files for a tenant."""
    with closing(registry_connect()) as conn:
        t = conn.execute("SELECT db_filename, company_name FROM tenants WHERE id=?", (tenant_id,)).fetchone()
        if not t:
            return []
        filename, company_name = t[0], t[1]
    result = []
    with closing(registry_connect()) as conn:
        support_rows = rows(
            conn,
            "SELECT id,original_name,size_bytes,source,created_at,status,product_code,hardware_id,installation_id,sha256 "
            "FROM support_backups WHERE tenant_id=? AND status='available' "
            "ORDER BY id DESC LIMIT 25",
            (tenant_id,),
        )
    for item in support_rows:
        result.append({
            "index": int(item["id"]),
            "backup_id": int(item["id"]),
            "filename": item.get("original_name") or f"support-{item['id']}.db",
            "size_bytes": int(item.get("size_bytes") or 0),
            "modified": item.get("created_at") or "",
            "source": item.get("source") or "desktop",
            "kind": "support",
            "product_code": item["product_code"],
            "hardware_id": item["hardware_id"],
            "installation_id": item["installation_id"],
            "sha256": item["sha256"],
        })
    backup_dir = TENANT_ROOT.parent / "backups"
    if backup_dir.exists():
        stem = Path(filename).stem
        for i, f in enumerate(sorted(backup_dir.glob(f"{stem}*.db"), reverse=True)[:10]):
            stat = f.stat()
            result.append({
                "index": i,
                "filename": f.name,
                "size_bytes": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                "source": "server",
                "kind": "legacy",
            })
    # Also include current DB as backup[0]
    path = TENANT_ROOT / filename
    if path.exists():
        stat = path.stat()
        result.insert(0, {
            "index": -1,
            "filename": filename + " (guncel)",
            "size_bytes": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
            "source": "server",
            "kind": "current",
        })
    return result


def admin_download_support_backup(actor: dict, tenant_id: str, backup_id: int) -> tuple:
    """Resolve the selected customer's product and device for an operator."""
    if not is_control_admin(actor):
        raise PermissionError("Platform operator permission is required")
    with closing(registry_connect()) as conn:
        backup = conn.execute(
            "SELECT product_code,hardware_id,installation_id FROM support_backups WHERE id=? AND tenant_id=?",
            (int(backup_id), tenant_id),
        ).fetchone()
    if not backup:
        raise LookupError("Backup was not found")
    return support_backup_file({**actor, "_tenant_id": tenant_id}, backup_id,
                               str(backup[0]), str(backup[1]), str(backup[2] or ""))


def admin_download_backup(tenant_id: str, backup_index: int) -> tuple:
    """Return raw bytes of the tenant DB file for download."""
    with closing(registry_connect()) as conn:
        t = conn.execute("SELECT db_filename FROM tenants WHERE id=?", (tenant_id,)).fetchone()
        if not t:
            raise LookupError("Firma bulunamadi")
        filename = t[0]
    if int(backup_index) == -1:
        path = TENANT_ROOT / filename
    else:
        backup_dir = TENANT_ROOT.parent / "backups"
        candidates = sorted(
            backup_dir.glob(f"{Path(filename).stem}*.db"),
            reverse=True,
        ) if backup_dir.exists() else []
        if backup_index < 0 or backup_index >= len(candidates):
            raise LookupError("Yedek bulunamadi")
        path = candidates[backup_index]
    if not path.exists():
        raise LookupError("Veritabani dosyasi bulunamadi")
    return path.read_bytes(), path.name


def admin_restore_backup(
    tenant_id: str,
    backup_index: int,
    actor: dict | None = None,
    backup_id: int = 0,
) -> dict:
    """Mark a restore command so next client sync pulls the backup."""
    if backup_id:
        if not actor:
            raise PermissionError("Yonetici oturumu gerekli")
        return control_queue_restore(
            actor,
            {"tenant_id": tenant_id, "backup_id": int(backup_id)},
        )
    if not actor:
        raise PermissionError("Yonetici oturumu gerekli")
    payload, filename = admin_download_backup(tenant_id, backup_index)
    stored = _store_support_backup_for_tenant(
        tenant_id,
        int(dict(actor).get("id") or 0),
        payload,
        filename,
        "server",
    )
    return control_queue_restore(
        actor,
        {"tenant_id": tenant_id, "backup_id": stored["backup_id"]},
    )


def admin_send_notification(data: dict, actor: dict | None = None) -> dict:
    """Store a notification for one or all tenants to display on next launch."""
    target = str(data.get("target") or "all")
    title = str(data.get("title") or "")
    body_text = str(data.get("body") or "")
    icon = str(data.get("icon") or "info")
    popup = bool(data.get("popup", True))
    if not title or not body_text:
        raise ValueError("Baslık ve icerik zorunludur")
    with closing(registry_connect()) as conn:
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='platform_notifications'").fetchone():
            conn.execute("""CREATE TABLE IF NOT EXISTS platform_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                icon TEXT DEFAULT 'info',
                popup INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                read_at TEXT
            )""")
        if target == "all":
            conn.execute(
                "INSERT INTO platform_notifications(tenant_id,title,body,icon,popup,created_at) VALUES (NULL,?,?,?,?,?)",
                (title, body_text, icon, int(popup), utc_now().isoformat(timespec="seconds"))
            )
            sent_to = "Tum firmalar"
        else:
            conn.execute(
                "INSERT INTO platform_notifications(tenant_id,title,body,icon,popup,created_at) VALUES (?,?,?,?,?,?)",
                (target, title, body_text, icon, int(popup), utc_now().isoformat(timespec="seconds"))
            )
            sent_to = target
        conn.commit()
    _support_audit(
        actor,
        "admin_notification_sent",
        "" if target == "all" else target,
        detail={"target": target, "title": title, "popup": popup},
    )
    return {"ok": True, "sent_to": sent_to}


def admin_audit_logs(tenant_id: str = "", limit: int = 200) -> list:
    """Return vendor support actions with tenant names and structured detail."""
    safe_limit = max(1, min(int(limit or 200), 1000))
    with closing(registry_connect()) as conn:
        where = "WHERE a.target_tenant_id=?" if tenant_id else ""
        params = (tenant_id, safe_limit) if tenant_id else (safe_limit,)
        items = rows(
            conn,
            "SELECT a.id,a.created_at,a.action,a.actor_tenant_id,a.actor_user_id,"
            "a.target_tenant_id,a.target_user_id,a.detail_json,"
            "COALESCE(t.company_name,a.target_tenant_id,'Sistem') AS company_name "
            "FROM support_audit a LEFT JOIN tenants t ON t.id=a.target_tenant_id "
            f"{where} ORDER BY a.id DESC LIMIT ?",
            params,
        )
    for item in items:
        try:
            item["detail"] = json.loads(item.get("detail_json") or "{}")
        except (TypeError, ValueError):
            item["detail"] = {}
        item.pop("detail_json", None)
    return items


def admin_error_logs(tenant_id: str = "", limit: int = 100) -> list:
    """Retrieve telemetry error logs from registry."""
    with closing(registry_connect()) as conn:
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='telemetry_errors'").fetchone():
            return []
        where = "WHERE tenant_id=?" if tenant_id else ""
        params = (tenant_id, limit) if tenant_id else (limit,)
        return rows(conn, f"SELECT * FROM telemetry_errors {where} ORDER BY id DESC LIMIT ?", params)


def admin_server_status() -> dict:
    """System resource usage."""
    import shutil
    result: dict = {"version": "2.0.0", "db_path": str(DB_PATH)}
    try:
        import psutil
        result["cpu_percent"] = psutil.cpu_percent(interval=0.2)
        ram = psutil.virtual_memory()
        result["ram_percent"] = ram.percent
    except ImportError:
        result["cpu_percent"] = 0
        result["ram_percent"] = 0
    try:
        usage = shutil.disk_usage(str(TENANT_ROOT))
        result["disk_percent"] = int(usage.used / usage.total * 100)
        result["disk_usage"] = f"%{result['disk_percent']}"
    except Exception:
        result["disk_percent"] = 0
        result["disk_usage"] = "?"
    with closing(registry_connect()) as conn:
        result["tenant_count"] = scalar(conn, "SELECT COUNT(*) FROM tenants")
    return result


def admin_live_status() -> list:
    """Return online/offline status per tenant based on recent sessions."""
    tenants = _admin_tenants_all()
    result = []
    try:
        with closing(registry_connect()) as conn:
            cutoff = (utc_now() - timedelta(minutes=10)).isoformat(timespec="seconds")
            for t in tenants:
                tid = t.get("id", "")
                active_sessions = scalar(
                    conn,
                    "SELECT COUNT(*) FROM sessions WHERE tenant_id=? AND (last_seen >= ? OR created_at >= ?)",
                    (tid, cutoff, cutoff),
                    default=0,
                )
                result.append({
                    "id": tid,
                    "company_name": t.get("company_name", "?"),
                    "online": active_sessions > 0,
                    "active_users": active_sessions,
                    "last_seen": "",
                })
    except Exception:
        for t in tenants:
            result.append({
                "id": t.get("id", ""),
                "company_name": t.get("company_name", "?"),
                "online": False,
                "active_users": 0,
                "last_seen": "",
            })
    return result


def admin_deploy_update(data: dict, actor: dict | None = None) -> dict:
    """Store an update deployment command for all or selected tenants."""
    version = str(data.get("version") or "")
    targets = data.get("targets") or []
    changelog = str(data.get("changelog") or "")
    if not version:
        raise ValueError("Surum numarasi gerekli")
    with closing(registry_connect()) as conn:
        channel = str(data.get("channel") or "pilot").strip().lower()
        if channel not in {"pilot", "stable"}:
            raise ValueError("Gecersiz dagitim kanali")
        payload = json.dumps(
            {"version": version, "changelog": changelog, "channel": channel},
            ensure_ascii=True,
        )
        if not targets:
            targets = [
                item["id"]
                for item in rows(
                    conn,
                    "SELECT id FROM tenants WHERE COALESCE(active,1)=1 ORDER BY id",
                )
            ]
        known_targets = {
            item["id"]
            for item in rows(
                conn,
                "SELECT id FROM tenants WHERE id IN ("
                + ",".join("?" for _ in targets)
                + ")",
                tuple(targets),
            )
        } if targets else set()
        unknown = sorted(set(targets) - known_targets)
        if unknown:
            raise LookupError("Gecersiz firma hedefi: " + ", ".join(unknown))
        now = utc_now().isoformat(timespec="seconds")
        actor_item = dict(actor or {})
        for tid in targets:
            conn.execute(
                "INSERT INTO desktop_commands(tenant_id,command_type,payload_json,status,"
                "created_by_tenant_id,created_by_user_id,created_at) "
                "VALUES (?, 'deploy_update', ?, 'pending', ?, ?, ?)",
                (
                    tid,
                    payload,
                    str(actor_item.get("_tenant_id") or ""),
                    int(actor_item.get("id") or 0),
                    now,
                ),
            )
        conn.commit()
    for target_tenant_id in targets:
        _support_audit(
            actor,
            "admin_update_deployed",
            str(target_tenant_id),
            detail={
                "version": version,
                "channel": channel,
                "targets": targets,
            },
        )
    return {"ok": True, "version": version, "targets": targets}


# =============================================================================
def control_overview(user: dict) -> dict:

    if not can_access_control_center(user):
        raise PermissionError("Management permission is required")
    platform_scope = is_control_admin(user)
    actor_tenant_id = str(dict(user).get("_tenant_id") or active_tenant_id() or "")
    result = []
    with closing(registry_connect()) as registry:
        if platform_scope:
            tenants = rows(registry, "SELECT * FROM tenants ORDER BY created_at,id")
        else:
            tenants = rows(
                registry,
                "SELECT * FROM tenants WHERE id=? ORDER BY created_at,id",
                (actor_tenant_id,),
            )
    for tenant in tenants:
        path = _tenant_path(tenant)
        sector = "teknik_servis"
        tenant_users = []
        if path.exists():
            with closing(_raw_connect(path)) as conn:
                _ensure_path_schema(conn, path)
                sector = str(
                    scalar(
                        conn,
                        "SELECT value FROM internal_settings WHERE key='current_sector'",
                        default="teknik_servis",
                    )
                    or "teknik_servis"
                )
                tenant_users = rows(
                    conn,
                    "SELECT id,username,full_name,email,phone,role,active,last_login,created_at "
                    "FROM users ORDER BY id",
                )
        if sector not in {"teknik_servis", "otomotiv"}:
            sector = "teknik_servis"
        with closing(registry_connect()) as registry:
            backup_rows = rows(
                registry,
                "SELECT id,original_name,sha256,size_bytes,source,created_at,status "
                "FROM support_backups WHERE tenant_id=? ORDER BY created_at DESC LIMIT 25",
                (tenant["id"],),
            )
            command_rows = rows(
                registry,
                "SELECT id,command_type,status,created_at,claimed_at,completed_at,result_json "
                "FROM desktop_commands WHERE tenant_id=? ORDER BY id DESC LIMIT 20",
                (tenant["id"],),
            )
        result.append({
            **tenant,
            "sector": sector,
            "users": tenant_users,
            "backups": backup_rows if platform_scope else [],
            "commands": command_rows if platform_scope else [],
        })
    return {
        "ok": True,
        "scope": "platform" if platform_scope else "tenant",
        "vendor": {
            "name": VENDOR_NAME,
            "email": SUPPORT_EMAIL,
            "phone": VENDOR_PHONE,
            "server": PUBLIC_SERVER_URL,
        },
        "tenants": result,
    }


def control_update_tenant(user: dict, data: dict) -> dict:
    tenant_id = str(data.get("tenant_id") or "").strip()
    if not can_manage_tenant(user, tenant_id):
        raise PermissionError("Company management permission is required")
    sector = str(data.get("sector") or "").strip()
    if sector not in {"teknik_servis", "otomotiv"}:
        raise ValueError("Invalid sector")
    with closing(registry_connect()) as registry:
        row = registry.execute("SELECT * FROM tenants WHERE id=?", (tenant_id,)).fetchone()
        if not row:
            raise LookupError("Company was not found")
        tenant = dict(row)
        active = 1 if str(data.get("active", tenant.get("active", 1))) in {"1", "true", "True"} else 0
        company_name = str(data.get("company_name") or tenant["company_name"]).strip()
        if len(company_name) < 2:
            raise ValueError("Company name is required")
        if is_control_admin(user):
            license_type = str(data.get("license_type") or tenant.get("license_type") or "Lifetime").strip()
            license_start = str(data.get("license_start") or tenant.get("license_start") or "").strip()
            license_end = str(data.get("license_end") or tenant.get("license_end") or "").strip()
            license_status = str(data.get("license_status") or tenant.get("license_status") or "Active").strip()
            registry.execute(
                "UPDATE tenants SET company_name=?, active=?, sector=?, license_type=?, license_start=?, license_end=?, license_status=? WHERE id=?",
                (company_name, active, sector, license_type, license_start, license_end, license_status, tenant_id),
            )
        else:
            registry.execute(
                "UPDATE tenants SET company_name=?, active=?, sector=? WHERE id=?",
                (company_name, active, sector, tenant_id),
            )
        registry.commit()
    path = _tenant_path(tenant)
    with closing(_raw_connect(path)) as conn:
        _ensure_path_schema(conn, path)
        upsert_setting(conn, "internal_settings", "current_sector", sector)
        upsert_setting(conn, "settings", "company_name", company_name)
        conn.execute("UPDATE company_info SET company_name=?,updated_at=CURRENT_TIMESTAMP", (company_name,))
        conn.commit()
    _support_audit(
        user,
        "control_company_updated",
        tenant_id,
        detail={"company_name": company_name, "sector": sector, "active": active},
    )
    return {"ok": True, "tenant_id": tenant_id, "sector": sector, "active": active}


def update_current_company_sector(user: dict, data: dict) -> dict:
    if not role_is_admin(dict(user or {}).get("role")):
        raise PermissionError("Company administrator permission is required")
    tenant_id = str(dict(user or {}).get("_tenant_id") or active_tenant_id() or "").strip()
    if not tenant_id:
        raise PermissionError("Company session is required")
    sector = str(data.get("sector") or "").strip()
    if sector not in {"teknik_servis", "otomotiv"}:
        raise ValueError("Invalid sector")
    with closing(registry_connect()) as registry:
        row = registry.execute("SELECT * FROM tenants WHERE id=?", (tenant_id,)).fetchone()
        if not row:
            raise LookupError("Company was not found")
        tenant = dict(row)
        registry.execute("UPDATE tenants SET sector=? WHERE id=?", (sector, tenant_id))
        registry.commit()
    path = _tenant_path(tenant)
    with closing(_raw_connect(path)) as conn:
        _ensure_path_schema(conn, path)
        upsert_setting(conn, "internal_settings", "current_sector", sector)
        conn.commit()
    _support_audit(user, "company_sector_changed", tenant_id, detail={"sector": sector})
    return {"ok": True, "tenant_id": tenant_id, "sector": sector}


def update_current_company_location(user: dict, data: dict) -> dict:
    if not role_is_admin(dict(user or {}).get("role")):
        raise PermissionError("Company administrator permission is required")
    tenant_id = str(dict(user or {}).get("_tenant_id") or active_tenant_id() or "").strip()
    if not tenant_id:
        raise PermissionError("Company session is required")
    profile = {
        "installation_lat": data.get("installation_lat"),
        "installation_lng": data.get("installation_lng"),
        "installation_address": str(
            data.get("installation_address") or data.get("company_address") or ""
        ).strip(),
    }
    sync_tenant_directory_from_company_info(tenant_id, profile)
    tenant = tenant_by_id(tenant_id)
    return {
        "ok": True,
        "tenant_id": tenant_id,
        "installation_lat": (tenant or {}).get("installation_lat"),
        "installation_lng": (tenant or {}).get("installation_lng"),
    }


def control_update_user(actor: dict, data: dict) -> dict:
    tenant_id = str(data.get("tenant_id") or "").strip()
    if not can_manage_tenant(actor, tenant_id):
        raise PermissionError("User management permission is required")
    user_id = int(data.get("user_id") or 0)
    with closing(registry_connect()) as registry:
        row = registry.execute("SELECT * FROM tenants WHERE id=?", (tenant_id,)).fetchone()
        if not row:
            raise LookupError("Company was not found")
        tenant = dict(row)
    path = _tenant_path(tenant)
    with closing(_raw_connect(path)) as conn:
        _ensure_path_schema(conn, path)
        existing = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if not existing:
            raise LookupError("User was not found")
        updates = {
            "username": str(data.get("username") or existing["username"] or "").strip(),
            "full_name": str(data.get("full_name") or existing["full_name"] or "").strip(),
            "email": str(data.get("email") or existing["email"] or "").strip().lower(),
            "phone": str(data.get("phone") or existing["phone"] or "").strip(),
            "role": str(data.get("role") or existing["role"] or "User").strip(),
            "active": 1 if str(data.get("active", existing["active"])) in {"1", "true", "True"} else 0,
        }
        if not re.fullmatch(r"[A-Za-z0-9_.-]{3,40}", updates["username"]):
            raise ValueError("Username format is invalid")
        if str(data.get("password") or ""):
            raise ValueError("Use a single-use password reset link instead of setting a password directly")
        setters = ",".join(f'"{key}"=?' for key in updates)
        conn.execute(f"UPDATE users SET {setters} WHERE id=?", (*updates.values(), user_id))
        if not updates["active"]:
            conn.execute("DELETE FROM web_sessions WHERE user_id=?", (user_id,))
        conn.commit()
    _support_audit(
        actor,
        "control_user_updated",
        tenant_id,
        user_id,
        {key: value for key, value in updates.items() if key != "email"},
    )
    return {"ok": True, "tenant_id": tenant_id, "user_id": user_id}


def control_server_status(actor: dict) -> dict:
    if not can_access_control_center(actor):
        raise PermissionError("Management permission is required")
    import psutil
    cpu_percent = psutil.cpu_percent()
    virtual_memory = psutil.virtual_memory()
    disk_usage = psutil.disk_usage('/')
    return {
        "ok": True,
        "cpu_percent": cpu_percent,
        "ram_percent": virtual_memory.percent,
        "ram_total_gb": round(virtual_memory.total / (1024**3), 2),
        "ram_used_gb": round(virtual_memory.used / (1024**3), 2),
        "disk_percent": disk_usage.percent,
        "disk_total_gb": round(disk_usage.total / (1024**3), 2),
        "disk_used_gb": round(disk_usage.used / (1024**3), 2),
        "server_time": utc_now().isoformat(timespec="seconds")
    }


def control_add_error_log(data: dict) -> dict:
    tenant_id = str(data.get("tenant_id") or "Unknown").strip()
    version = str(data.get("version") or "Unknown").strip()
    os_info = str(data.get("os_info") or "Unknown").strip()
    error_message = str(data.get("error_message") or "").strip()
    stack_trace = str(data.get("stack_trace") or "").strip()
    if not error_message:
        return {"ok": False, "error": "Error message is required"}
    with closing(registry_connect()) as conn:
        conn.execute(
            "INSERT INTO error_telemetry(tenant_id,version,os_info,error_message,stack_trace,created_at) VALUES (?,?,?,?,?,?)",
            (tenant_id, version, os_info, error_message, stack_trace, utc_now().isoformat(timespec="seconds")),
        )
        conn.commit()
    return {"ok": True}


def control_get_error_logs(actor: dict) -> dict:
    if not can_access_control_center(actor):
        raise PermissionError("Management permission is required")
    with closing(registry_connect()) as conn:
        logs_list = rows(conn, "SELECT * FROM error_telemetry ORDER BY id DESC LIMIT 100")
    return {"ok": True, "logs": logs_list}


def control_send_notification(actor: dict, data: dict) -> dict:
    if not is_control_admin(actor):
        raise PermissionError("Platform operator permission is required")
    target_tenant_id = str(data.get("target_tenant_id") or "All").strip()
    message_title = str(data.get("message_title") or "").strip()
    message_content = str(data.get("message_content") or "").strip()
    popup = 1 if data.get("popup") else 0
    if not message_content:
        raise ValueError("Message content is required")
    with closing(registry_connect()) as conn:
        conn.execute(
            "INSERT INTO global_notifications(target_tenant_id,message_title,message_content,popup,created_at) VALUES (?,?,?,?,?)",
            (target_tenant_id, message_title, message_content, popup, utc_now().isoformat(timespec="seconds")),
        )
        conn.commit()
    _support_audit(
        actor,
        "control_notification_sent",
        "" if target_tenant_id == "All" else target_tenant_id,
        detail={"title": message_title, "popup": bool(popup)},
    )
    return {"ok": True}


def control_get_staged_updates(actor: dict) -> dict:
    if not can_access_control_center(actor):
        raise PermissionError("Management permission is required")
    with closing(registry_connect()) as conn:
        updates = rows(conn, "SELECT * FROM staged_updates ORDER BY id DESC LIMIT 50")
    return {"ok": True, "updates": updates}


def control_add_staged_update(actor: dict, data: dict) -> dict:
    if not is_control_admin(actor):
        raise PermissionError("Platform operator permission is required")
    version = str(data.get("version") or "").strip()
    notes = str(data.get("notes") or "").strip()
    target_scope = str(data.get("target_scope") or "All").strip()
    file_path = str(data.get("file_path") or "").strip()
    if not version:
        raise ValueError("Version is required")
    with closing(registry_connect()) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO staged_updates(version,notes,target_scope,file_path,created_at) VALUES (?,?,?,?,?)",
            (version, notes, target_scope, file_path, utc_now().isoformat(timespec="seconds")),
        )
        conn.commit()
    _support_audit(
        actor,
        "control_update_staged",
        detail={"version": version, "target_scope": target_scope},
    )
    return {"ok": True}


def clear_tenant_context() -> None:
    for name in ("tenant_id", "db_path", "company_name"):
        if hasattr(_TENANT_LOCAL, name):
            delattr(_TENANT_LOCAL, name)


def set_tenant_context(tenant: dict | None) -> None:
    clear_tenant_context()
    if not tenant:
        return
    filename = Path(str(tenant.get("db_filename") or "")).name
    if not filename.lower().endswith(".db"):
        return
    _TENANT_LOCAL.tenant_id = str(tenant.get("id") or "")
    _TENANT_LOCAL.company_name = str(tenant.get("company_name") or "")
    _TENANT_LOCAL.db_path = (TENANT_ROOT / filename).resolve()


def active_db_path() -> Path:
    return Path(getattr(_TENANT_LOCAL, "db_path", None) or DB_PATH).resolve()


def active_tenant_id() -> str:
    return str(getattr(_TENANT_LOCAL, "tenant_id", "") or "")


def active_company_name() -> str:
    return str(getattr(_TENANT_LOCAL, "company_name", "") or "")


def resolve_installation_location(address: str) -> tuple[float | None, float | None]:
    """Resolve a newly supplied installation address once; failure remains non-blocking."""
    address = str(address or "").strip()
    if len(address) < 5:
        return None, None
    try:
        from urllib.parse import urlencode
        from urllib.request import Request, urlopen
        query = urlencode({"q": address, "format": "jsonv2", "limit": "1"})
        request = Request(
            "https://nominatim.openstreetmap.org/search?" + query,
            headers={"User-Agent": "AYEC-Pro-Installation-Map/1.0"},
        )
        with urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if payload:
            return float(payload[0]["lat"]), float(payload[0]["lon"])
    except Exception:
        pass
    return None, None


def create_tenant(
    company_name: str,
    sector: str = "teknik_servis",
    contact_name: str = "",
    phone: str = "",
    email: str = "",
    company_address: str = "",
    installation_lat=None,
    installation_lng=None,
    product_code: str = "teknik_servis",
) -> dict:
    company_name = str(company_name or "").strip() or "AYEC Pro"
    sector = str(sector or "").strip()
    if sector not in {"teknik_servis", "otomotiv"}:
        raise ValueError("Invalid sector")
    product_code = str(product_code or "teknik_servis").strip().lower()
    if product_code not in configured_product_codes():
        raise ValueError("Invalid product code")
    contact_name = str(contact_name or "").strip()
    phone = str(phone or "").strip()
    email = str(email or "").strip().lower()
    company_address = str(company_address or "").strip()
    try:
        latitude = float(installation_lat) if installation_lat not in (None, "") else None
        longitude = float(installation_lng) if installation_lng not in (None, "") else None
    except (TypeError, ValueError):
        latitude, longitude = None, None
    if latitude is None or longitude is None:
        latitude, longitude = resolve_installation_location(company_address)
    elif not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise ValueError("Invalid installation coordinates")
    with closing(registry_connect()) as conn:
        filename = _tenant_filename(company_name)
        target = TENANT_ROOT / filename
        registered_filenames = {
            str(row[0] or "").casefold()
            for row in conn.execute("SELECT db_filename FROM tenants")
        }
        suffix = 2
        while target.exists() or target.name.casefold() in registered_filenames:
            target = TENANT_ROOT / f"{Path(filename).stem} ({suffix}).db"
            suffix += 1
        now = utc_now()
        tenant = {
            "id": _new_tenant_id(company_name),
            "company_name": company_name,
            "db_filename": target.name,
            "created_at": now.isoformat(timespec="seconds"),
            "active": 1,
            "sector": sector,
            "product_code": product_code,
            "license_type": "Trial",
            "license_start": now.isoformat(timespec="seconds"),
            "license_end": (now + timedelta(days=TRIAL_DAYS)).isoformat(timespec="seconds"),
            "license_status": "Trial",
            "contact_name": contact_name,
            "phone": phone,
            "email": email,
            "company_address": company_address,
            "installation_lat": latitude,
            "installation_lng": longitude,
            "location_updated_at": now.isoformat(timespec="seconds") if latitude is not None else "",
        }
        conn.execute(
            "INSERT INTO tenants(id,company_name,db_filename,created_at,active,sector,product_code,license_type,license_start,license_end,license_status,contact_name,phone,email,company_address,installation_lat,installation_lng,location_updated_at) VALUES (?,?,?,?,1,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                tenant["id"],
                tenant["company_name"],
                tenant["db_filename"],
                tenant["created_at"],
                tenant["sector"],
                tenant["product_code"],
                tenant["license_type"],
                tenant["license_start"],
                tenant["license_end"],
                tenant["license_status"],
                tenant["contact_name"],
                tenant["phone"],
                tenant["email"],
                tenant["company_address"],
                tenant["installation_lat"],
                tenant["installation_lng"],
                tenant["location_updated_at"],
            ),
        )
        conn.commit()
    target.parent.mkdir(parents=True, exist_ok=True)
    if DEMO_TEMPLATE_PATH.is_file():
        shutil.copy2(DEMO_TEMPLATE_PATH, target)
    with closing(_raw_connect(target)) as tenant_conn:
        _ensure_path_schema(tenant_conn, target)
        tenant_conn.commit()
    return tenant


def db_connect() -> sqlite3.Connection:
    path = active_db_path()
    conn = _raw_connect(path)
    _ensure_path_schema(conn, path)
    return conn


def table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [row[1] for row in conn.execute(f'PRAGMA table_info("{table}")')]


def rows(conn: sqlite3.Connection, sql: str, params=()) -> list[dict]:
    return [dict(row) for row in conn.execute(sql, params).fetchall()]


def scalar(conn: sqlite3.Connection, sql: str, params=(), default=0):
    row = conn.execute(sql, params).fetchone()
    return row[0] if row and row[0] is not None else default


def utc_now() -> datetime:
    # Keep the database representation naive for desktop compatibility while
    # sourcing the value from an explicitly UTC-aware clock.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def service_tracking_token_value(token: str) -> str | None:
    """Validate a public service token and return its tracking number."""
    try:
        encoded, signature = str(token or "").split(".", 1)
        padded = encoded + "=" * (-len(encoded) % 4)
        tracking_no = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8").strip()
    except (ValueError, UnicodeError, binascii.Error):
        return None
    if not tracking_no or len(signature) != 32:
        return None
    expected = hmac.new(
        SERVICE_TRACKING_SECRET.encode("utf-8"),
        tracking_no.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:32]
    return tracking_no if hmac.compare_digest(signature, expected) else None


def public_service_record(token: str, ip_address: str, user_agent: str) -> dict | None:
    tracking_no = service_tracking_token_value(token)
    if not tracking_no:
        return None
    candidate_paths = [active_db_path()]
    try:
        with closing(registry_connect()) as registry:
            for row in registry.execute("SELECT db_filename FROM tenants WHERE active=1"):
                path = (TENANT_ROOT / Path(str(row[0] or "")).name).resolve()
                if path not in candidate_paths:
                    candidate_paths.append(path)
    except Exception:
        pass
    for path in candidate_paths:
        if not path.is_file():
            continue
        try:
            with closing(_raw_connect(path)) as conn:
                columns = set(table_columns(conn, "devices"))
                if "tracking_no" not in columns:
                    continue
                row = conn.execute(
                    "SELECT * FROM devices WHERE tracking_no=? AND COALESCE(is_deleted,0)=0 ORDER BY id DESC LIMIT 1",
                    (tracking_no,),
                ).fetchone()
                if not row:
                    continue
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS service_tracking_access (id INTEGER PRIMARY KEY AUTOINCREMENT, tracking_no TEXT NOT NULL, accessed_at TEXT NOT NULL, ip_address TEXT, user_agent TEXT)"
                )
                conn.execute(
                    "INSERT INTO service_tracking_access(tracking_no,accessed_at,ip_address,user_agent) VALUES (?,?,?,?)",
                    (tracking_no, utc_now().isoformat(timespec="seconds"), ip_address, user_agent[:300]),
                )
                conn.commit()
                data = dict(row)
                return {
                    "tracking_no": tracking_no,
                    "status": str(data.get("status") or "-"),
                    "device": " ".join(str(data.get(key) or "").strip() for key in ("device_brand", "device_model")).strip() or "-",
                    "received_at": str(data.get("entry_date") or data.get("created_at") or "-")[:32],
                    "delivery_status": str(data.get("delivery_type") or "-")[:80],
                }
        except (OSError, sqlite3.Error, TypeError):
            continue
    return None


def public_service_html(record: dict) -> str:
    esc = lambda value: html.escape(str(value or "-"), quote=True)
    return """<!doctype html><html lang="tr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AYEC Pro Servis Takip</title><style>body{font-family:Arial,sans-serif;background:#f4f7fb;color:#172033;margin:0;padding:24px}.card{max-width:560px;margin:4vh auto;background:#fff;border-radius:18px;padding:28px;box-shadow:0 12px 32px #17203318}h1{margin:0 0 8px;color:#155c88;font-size:24px}.muted{color:#637089;margin-bottom:22px}.row{display:flex;justify-content:space-between;border-top:1px solid #e5eaf0;padding:14px 0;gap:20px}.row b{color:#637089}.value{text-align:right;font-weight:700}.foot{margin-top:18px;color:#637089;font-size:12px;text-align:center}</style><div class="card"><h1>AYEC Pro Servis Takip</h1><div class="muted">Servis kaydinizin guncel durumu</div><div class="row"><b>Takip No</b><span class="value">%s</span></div><div class="row"><b>Cihaz</b><span class="value">%s</span></div><div class="row"><b>Durum</b><span class="value">%s</span></div><div class="row"><b>Kabul Tarihi</b><span class="value">%s</span></div><div class="row"><b>Teslim Sekli</b><span class="value">%s</span></div><div class="foot">Bilgiler servis kaydinizdaki son durumu gosterir.</div></div></html>""" % tuple(esc(record.get(key)) for key in ("tracking_no", "device", "status", "received_at", "delivery_status"))


def password_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}"


def password_matches(password: str, stored: str | None) -> bool:
    stored = str(stored or "")
    if stored.startswith("pbkdf2_sha256$"):
        try:
            _, iterations, salt, expected = stored.split("$", 3)
            digest = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), bytes.fromhex(salt), int(iterations)
            ).hex()
            return secrets.compare_digest(digest, expected)
        except (TypeError, ValueError):
            return False
    # Try bcrypt if installed
    if stored.startswith(("$2a$", "$2b$", "$2y$")):
        try:
            import bcrypt
            encoded = password.encode("utf-8")
            if bcrypt.checkpw(encoded, stored.encode("utf-8")):
                return True
            # Desktop releases used bcrypt over SHA-256 password material.
            return bcrypt.checkpw(hashlib.sha256(encoded).digest(), stored.encode("utf-8"))
        except (ImportError, ValueError, TypeError):
            logger.warning("Bcrypt password verification is unavailable or hash is invalid")
            return False
    legacy = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return bool(stored) and secrets.compare_digest(legacy, stored)



def role_is_admin(role: str | None) -> bool:
    normalized = unicodedata.normalize("NFKD", str(role or ""))
    normalized = normalized.encode("ascii", "ignore").decode("ascii").casefold()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized).strip()
    return normalized in {
        "admin",
        "administrator",
        "superadmin",
        "super admin",
        "super administrator",
        "master admin",
        "platform admin",
        "system admin",
        "company admin",
        "master",
        "yonetici",
        "sistem yoneticisi",
        "firma yoneticisi",
        "firma sahibi",
        "owner",
        "tenant owner",
        "en yetkili",
        "en yetkili kisi",
    }


def public_user(user: dict | sqlite3.Row) -> dict:
    item = dict(user)
    return {
        "id": item.get("id"),
        "username": item.get("username") or "",
        "full_name": item.get("full_name") or item.get("username") or "",
        "email": item.get("email") or "",
        "phone": item.get("phone") or "",
        "must_change_password": bool(item.get("must_change_password")),
        "role": item.get("role") or "User",
        "permissions": item.get("permissions") or "",
        "is_admin": role_is_admin(item.get("role")),
        "interface_edit_access": bool(item.get("interface_edit_access")) or role_is_admin(item.get("role")),
        "tenant_id": item.get("_tenant_id") or active_tenant_id() or None,
        "company_name": item.get("_company_name") or active_company_name() or "",
        "is_control_admin": is_control_admin(item),
        "can_access_control_center": can_access_control_center(item),
    }


def update_current_user_profile(user: dict, data: dict) -> dict:
    user_id = int(dict(user or {}).get("id") or 0)
    if user_id <= 0:
        raise PermissionError("Authenticated user is required")
    full_name = str(data.get("full_name") or "").strip()
    email = str(data.get("email") or "").strip().lower()
    phone = str(data.get("phone") or "").strip()
    if not 2 <= len(full_name) <= 80:
        raise ValueError("Full name must contain 2 to 80 characters")
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise ValueError("A valid email address is required")
    if len(phone) > 30:
        raise ValueError("Phone number is too long")
    with closing(db_connect()) as conn:
        duplicate = conn.execute(
            "SELECT id FROM users WHERE LOWER(email)=LOWER(?) AND id<>?",
            (email, user_id),
        ).fetchone()
        if duplicate:
            raise ValueError("This email address is already in use")
        cursor = conn.execute(
            "UPDATE users SET full_name=?,email=?,phone=? WHERE id=?",
            (full_name, email, phone, user_id),
        )
        conn.commit()
        if cursor.rowcount != 1:
            raise LookupError("User was not found")
        updated = dict(conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone())
    updated["_tenant_id"] = dict(user).get("_tenant_id") or active_tenant_id()
    updated["_company_name"] = dict(user).get("_company_name") or active_company_name()
    return {"ok": True, "user": public_user(updated)}


def setting_value(conn: sqlite3.Connection, key: str, default: str = "") -> str:
    return str(scalar(conn, "SELECT value FROM settings WHERE key=?", (key,), default=default) or default)


def upsert_setting(conn: sqlite3.Connection, table: str, key: str, value) -> None:
    if table not in {"settings", "internal_settings"}:
        raise ValueError("Geçersiz ayar tablosu")
    conn.execute(
        f'INSERT INTO "{table}" (key,value) VALUES (?,?) '
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, str(value or "")),
    )


def auth_status(token: str = "") -> dict:
    user = session_user(token) if token else None
    tenants = tenant_records()
    setup_required = not tenants
    with closing(db_connect() if user else registry_connect()) as conn:
        registration_enabled = setting_value(conn, "web_registration_enabled", "1") != "0"
        smtp_configured = bool(
            (setting_value(conn, "smtp_server") or setting_value(conn, "smtp_host"))
            and (setting_value(conn, "smtp_email") or setting_value(conn, "smtp_user"))
        )
    return {
        "ok": True,
        "setup_required": setup_required,
        "authenticated": bool(user),
        "registration_enabled": registration_enabled and not setup_required,
        "smtp_configured": smtp_configured,
        "user": public_user(user) if user else None,
        "tenants": [{"id": item["id"], "company_name": item["company_name"]} for item in tenants],
    }


def session_user(token: str) -> dict | None:
    if not token:
        return None
    if "." in token:
        tenant_id = token.partition(".")[0]
        tenant = tenant_by_id(tenant_id)
        if not tenant:
            clear_tenant_context()
            return None
        set_tenant_context(tenant)
    token_digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = utc_now().isoformat(timespec="seconds")
    with closing(db_connect()) as conn:
        row = conn.execute(
            """
            SELECT u.* FROM web_sessions s
            JOIN users u ON u.id=s.user_id
            WHERE s.token_hash=? AND s.expires_at>? AND COALESCE(u.active,1)=1
            """,
            (token_digest, now),
        ).fetchone()
        if not row:
            clear_tenant_context()
            return None
        conn.execute("UPDATE web_sessions SET last_seen_at=? WHERE token_hash=?", (now, token_digest))
        conn.commit()
        result = dict(row)
        result["_tenant_id"] = active_tenant_id()
        result["_company_name"] = active_company_name()
        tenant = tenant_by_id(result["_tenant_id"])
        if tenant_access_error(tenant) and not is_control_admin(result):
            clear_tenant_context()
            return None
        return result


def create_session(user_id: int, remember: bool, user_agent: str, ip_address: str, tenant_id: str | None = None) -> tuple[str, int]:
    if tenant_id:
        tenant = tenant_by_id(tenant_id)
        if not tenant:
            raise LookupError("Firma bulunamadı.")
        set_tenant_context(tenant)
    tenant_id = tenant_id or active_tenant_id()
    token = f"{tenant_id}.{secrets.token_urlsafe(48)}" if tenant_id else secrets.token_urlsafe(48)
    now = utc_now()
    lifetime = timedelta(days=30 if remember else 1)
    max_age = int(lifetime.total_seconds())
    with closing(db_connect()) as conn:
        conn.execute("DELETE FROM web_sessions WHERE expires_at<=?", (now.isoformat(timespec="seconds"),))
        conn.execute(
            """
            INSERT INTO web_sessions
            (token_hash,user_id,created_at,expires_at,last_seen_at,remember,user_agent,ip_address)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                hashlib.sha256(token.encode("utf-8")).hexdigest(), user_id,
                now.isoformat(timespec="seconds"), (now + lifetime).isoformat(timespec="seconds"),
                now.isoformat(timespec="seconds"), int(remember), user_agent[:500], ip_address[:100],
            ),
        )
        conn.execute("UPDATE users SET auto_login=? WHERE id=?", (int(remember), user_id))
        conn.commit()
    return token, max_age


def delete_session(token: str) -> None:
    if not token:
        return
    if "." in token:
        tenant = tenant_by_id(token.partition(".")[0])
        if tenant:
            set_tenant_context(tenant)
    with closing(db_connect()) as conn:
        conn.execute(
            "DELETE FROM web_sessions WHERE token_hash=?",
            (hashlib.sha256(token.encode("utf-8")).hexdigest(),),
        )
        conn.commit()


def valid_email(value: str) -> bool:
    return bool(re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value.strip()))


def normalize_identifier(value) -> str:
    """Normalize legacy desktop usernames and e-mail identifiers for login."""
    return unicodedata.normalize("NFKC", str(value or "")).strip().casefold()


def find_account_by_identifier(conn: sqlite3.Connection, identifier: str):
    needle = normalize_identifier(identifier)
    if not needle:
        return None
    # SQLite lower() is ASCII-focused. Comparing normalized values in Python
    # keeps old Turkish/Unicode usernames and legacy whitespace-compatible.
    for row in conn.execute("SELECT * FROM users WHERE COALESCE(active,1)=1"):
        if needle in {normalize_identifier(row["username"]), normalize_identifier(row["email"])}:
            return row
    return None


def validate_account(data: dict, require_company: bool = False) -> dict:
    clean = {
        "username": str(data.get("username") or "").strip(),
        "password": str(data.get("password") or ""),
        "full_name": str(data.get("full_name") or "").strip(),
        "email": str(data.get("email") or "").strip().lower(),
        "phone": str(data.get("phone") or "").strip(),
        "company_name": str(data.get("company_name") or "").strip(),
    }
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,40}", clean["username"]):
        raise ValueError("Kullanıcı adı 3-40 karakter olmalı; harf, rakam, nokta, tire ve alt çizgi kullanılabilir.")
    if len(clean["full_name"]) < 3:
        raise ValueError("Ad soyad en az 3 karakter olmalıdır.")
    if not valid_email(clean["email"]):
        raise ValueError("Geçerli bir e-posta adresi girin.")
    if len(clean["password"]) < 8 or not re.search(r"[A-Za-z]", clean["password"]) or not re.search(r"\d", clean["password"]):
        raise ValueError("Parola en az 8 karakter olmalı ve en az bir harf ile bir rakam içermelidir.")
    if require_company and len(clean["company_name"]) < 2:
        raise ValueError("Firma adı zorunludur.")
    return clean


def send_registration_emails(member: dict, event: str = "registration") -> tuple[bool, str]:
    with closing(db_connect()) as conn:
        config = {row["key"]: row["value"] for row in conn.execute("SELECT key,value FROM settings")}
    official = _license_smtp_settings()
    smtp_host = official["host"]
    smtp_from = OFFICIAL_EMAIL
    if not smtp_host or not official["password"]:
        return False, "Hesap olusturuldu; info@ayecpro.com SMTP ayarlari eksik oldugu icin e-posta gonderilemedi."
    try:
        smtp_port = int(official["port"])
    except (TypeError, ValueError):
        smtp_port = 587
    smtp_password = official["password"]
    smtp_username = OFFICIAL_EMAIL
    admin_email = SUPPORT_EMAIL
    company_name = str(config.get("company_name") or "AYEC Pro").strip()
    member_email = str(member.get("email") or "").strip()
    if not valid_email(member_email) or not valid_email(admin_email):
        return False, "Üye veya yönetici e-posta adresi geçersiz."

    member_name = html.escape(str(member.get("full_name") or member.get("username") or "Kullanıcı"))
    username = html.escape(str(member.get("username") or ""))
    event_label = "ilk kurulum yöneticisi" if event == "setup" else "yeni kullanıcı"
    messages: list[EmailMessage] = []

    welcome = EmailMessage()
    welcome["Subject"] = f"{company_name} · AYEC Pro hesabınız hazır"
    welcome["From"] = smtp_from
    welcome["To"] = member_email
    welcome["Reply-To"] = SUPPORT_EMAIL
    welcome.set_content(f"Merhaba {member.get('full_name') or member.get('username')}, AYEC Pro hesabınız oluşturuldu. Kullanıcı adınız: {member.get('username')}")
    welcome.add_alternative(
        f"<div style='font-family:Segoe UI,Arial;padding:24px'><h2>Ho\u015f geldiniz, {member_name}</h2>"
        f"<p><b>{html.escape(company_name)}</b> AYEC Pro hesab\u0131n\u0131z olu\u015fturuldu.</p>"
        f"<p>Kullan\u0131c\u0131 ad\u0131n\u0131z: <b>{username}</b></p><p>Giri\u015f adresi: {html.escape(PUBLIC_SERVER_URL)}</p>"
        f"<p>Web: {OFFICIAL_WEBSITE} | Destek: {SUPPORT_EMAIL}</p>"
        "<p>G\u00fcvenli\u011finiz i\u00e7in parolan\u0131z e-postada g\u00f6sterilmez.</p></div>",
        subtype="html",
    )
    messages.append(welcome)

    notice = EmailMessage()
    notice["Subject"] = f"AYEC Pro · {event_label.title()} kaydı"
    notice["From"] = smtp_from
    notice["To"] = admin_email
    notice["Reply-To"] = SUPPORT_EMAIL
    notice.set_content(f"{member.get('full_name')} ({member.get('username')}) için yeni hesap oluşturuldu: {member_email}")
    notice.add_alternative(
        f"<div style='font-family:Segoe UI,Arial;padding:24px'><h2>Yeni hesap kaydı</h2>"
        f"<p><b>Ad Soyad:</b> {member_name}</p><p><b>Kullanıcı:</b> {username}</p>"
        f"<p><b>E-posta:</b> {html.escape(member_email)}</p><p><b>Rol:</b> {html.escape(str(member.get('role') or 'User'))}</p></div>",
        subtype="html",
    )
    messages.append(notice)

    try:
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=20, context=ssl.create_default_context())
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=20)
            server.ehlo()
            if official["tls"]:
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
        recipients = [("üye", welcome, member_email), ("yönetici", notice, admin_email)]
        delivered: list[str] = []
        failed: list[str] = []
        with server:
            if smtp_password:
                server.login(smtp_username, smtp_password)
            for label, message, recipient in recipients:
                try:
                    server.send_message(message)
                    delivered.append(label)
                except Exception as error:
                    failed.append(f"{label}: {error}")
        if not failed:
            return True, "Üye ve yönetici e-postaları gönderildi."
        if delivered:
            return False, f"{', '.join(delivered)} e-postası gönderildi; {failed[0]} gönderilemedi."
        return False, f"E-postalar gönderilemedi: {failed[0]}"
    except Exception as error:
        return False, f"Hesap oluşturuldu fakat e-posta gönderilemedi: {error}"


def setting_bool(value) -> bool:
    return str(value or "").strip().casefold() in {"1", "true", "yes", "on", "evet", "aktif"}


def provision_invites_required() -> bool:
    return setting_bool(os.environ.get("AYEC_PROVISION_INVITES_REQUIRED", "0"))


def _provision_client_key(client_ip: str, device_id: str) -> str:
    raw = f"{str(client_ip or '').strip()}|{str(device_id or '').strip()[:128]}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def consume_provision_rate_limit(client_ip: str, device_id: str) -> int:
    key_hash = _provision_client_key(client_ip, device_id)
    now = utc_now()
    with closing(registry_connect()) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT window_started_at,attempt_count FROM provision_rate_limits WHERE client_key_hash=?",
            (key_hash,),
        ).fetchone()
        if row:
            try:
                window_started = datetime.fromisoformat(str(row["window_started_at"]))
            except ValueError:
                window_started = now
            attempts = int(row["attempt_count"] or 0)
        else:
            window_started = now
            attempts = 0
        if now - window_started >= timedelta(seconds=PROVISION_RATE_WINDOW_SECONDS):
            window_started = now
            attempts = 0
        if attempts >= PROVISION_RATE_MAX_ATTEMPTS:
            conn.commit()
            retry_after = max(1, PROVISION_RATE_WINDOW_SECONDS - int((now - window_started).total_seconds()))
            raise PermissionError(f"Provisioning rate limit exceeded. Retry after {retry_after} seconds.")
        attempts += 1
        conn.execute(
            "INSERT INTO provision_rate_limits(client_key_hash,window_started_at,attempt_count,updated_at) "
            "VALUES (?,?,?,?) ON CONFLICT(client_key_hash) DO UPDATE SET "
            "window_started_at=excluded.window_started_at,attempt_count=excluded.attempt_count,updated_at=excluded.updated_at",
            (key_hash, window_started.isoformat(timespec="seconds"), attempts, now.isoformat(timespec="seconds")),
        )
        conn.commit()
    return PROVISION_RATE_MAX_ATTEMPTS - attempts


def _claim_provision_invite(code: str) -> None:
    if not provision_invites_required():
        return
    normalized = str(code or "").strip()
    if not normalized:
        raise PermissionError("A valid provisioning invitation code is required.")
    code_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    now = utc_now().isoformat(timespec="seconds")
    with closing(registry_connect()) as conn:
        conn.execute("BEGIN IMMEDIATE")
        cursor = conn.execute(
            "UPDATE provision_invites SET use_count=use_count+1 WHERE code_hash=? "
            "AND revoked_at IS NULL AND expires_at>? AND use_count<max_uses",
            (code_hash, now),
        )
        if cursor.rowcount != 1:
            conn.rollback()
            raise PermissionError("Provisioning invitation code is invalid, expired, or already used.")
        conn.commit()


def control_create_provision_invite(actor: dict, data: dict) -> dict:
    if not is_control_admin(actor):
        raise PermissionError("Platform operator permission is required")
    try:
        expires_in_hours = int(data.get("expires_in_hours", 72))
        max_uses = int(data.get("max_uses", 1))
    except (TypeError, ValueError) as error:
        raise ValueError("Invitation limits must be numeric") from error
    if not 1 <= expires_in_hours <= 720:
        raise ValueError("Invitation expiry must be between 1 and 720 hours")
    if not 1 <= max_uses <= 20:
        raise ValueError("Invitation uses must be between 1 and 20")
    code = "AYEC-" + secrets.token_urlsafe(24)
    now = utc_now()
    expires_at = now + timedelta(hours=expires_in_hours)
    item = dict(actor)
    with closing(registry_connect()) as conn:
        conn.execute(
            "INSERT INTO provision_invites(code_hash,code_value,expires_at,max_uses,use_count,created_by_tenant_id,created_by_user_id,created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (
                hashlib.sha256(code.encode("utf-8")).hexdigest(),
                code,
                expires_at.isoformat(timespec="seconds"),
                max_uses,
                0,
                str(item.get("_tenant_id") or ""),
                int(item.get("id") or 0),
                now.isoformat(timespec="seconds"),
            ),
        )
        conn.commit()
    _support_audit(actor, "provision_invite_created", detail={"expires_at": expires_at.isoformat(timespec="seconds"), "max_uses": max_uses})
    return {"ok": True, "invite_code": code, "expires_at": expires_at.isoformat(timespec="seconds"), "max_uses": max_uses}


def control_list_provision_invites(actor: dict) -> dict:
    if not is_control_admin(actor):
        raise PermissionError("Platform operator permission is required")
    with closing(registry_connect()) as conn:
        items = rows(
            conn,
            "SELECT id,code_value AS invite_code,expires_at,max_uses,use_count,revoked_at,created_at "
            "FROM provision_invites ORDER BY id DESC LIMIT 100",
        )
    return {"ok": True, "required": provision_invites_required(), "invites": items}


def control_revoke_provision_invite(actor: dict, data: dict) -> dict:
    if not is_control_admin(actor):
        raise PermissionError("Platform operator permission is required")
    invite_id = int(data.get("invite_id") or 0)
    if invite_id <= 0:
        raise ValueError("Invitation id is required")
    with closing(registry_connect()) as conn:
        cursor = conn.execute(
            "UPDATE provision_invites SET revoked_at=? WHERE id=? AND revoked_at IS NULL",
            (utc_now().isoformat(timespec="seconds"), invite_id),
        )
        conn.commit()
    if cursor.rowcount != 1:
        raise LookupError("Invitation was not found or is already revoked")
    _support_audit(actor, "provision_invite_revoked", detail={"invite_id": invite_id})
    return {"ok": True, "invite_id": invite_id}


def setup_application(data: dict, allow_existing: bool = False) -> dict:
    account = validate_account(data, require_company=True)
    sector = str(data.get("sector") or "").strip()
    product_code = str(data.get("product_code") or ("elek" if sector == "elek" else "teknik_servis")).strip().lower()
    if sector not in {"teknik_servis", "otomotiv", "elek"}:
        raise ValueError("Sekt\u00f6r se\u00e7imi zorunludur")
    existing_tenants = tenant_records()
    if existing_tenants and not allow_existing:
        raise PermissionError("İlk kurulum daha önce tamamlanmış.")
    normalized_company_name = normalize_identifier(account["company_name"])
    if any(
        normalize_identifier(tenant["company_name"]) == normalized_company_name
        for tenant in existing_tenants
    ):
        raise PermissionError(
            "Bu firma ad\u0131 zaten kay\u0131tl\u0131. Giri\u015f yap\u0131n veya "
            "y\u00f6neticinizden davet isteyin."
        )
    tenant = create_tenant(
        account["company_name"],
        sector,
        contact_name=account["full_name"],
        phone=account["phone"],
        email=str(data.get("company_email") or account["email"]).strip(),
        company_address=str(data.get("company_address") or "").strip(),
        installation_lat=data.get("installation_lat"),
        installation_lng=data.get("installation_lng"),
        product_code=product_code,
    )
    set_tenant_context(tenant)
    with closing(db_connect()) as conn:
        if scalar(conn, "SELECT COUNT(*) FROM users", default=0):
            raise PermissionError("İlk kurulum daha önce tamamlanmış.")
        is_platform_owner = is_platform_owner_email(account["email"])
        conn.execute("BEGIN IMMEDIATE")
        cursor = conn.execute(
            """
            INSERT INTO users (username,password,email,role,created_at,full_name,active,interface_edit_access)
            VALUES (?,?,?,?,?,?,1,?)
            """,
            (account["username"], password_hash(account["password"]), account["email"], "Admin" if is_platform_owner else "User", utc_now().isoformat(timespec="seconds"), account["full_name"], 1 if is_platform_owner else 0),
        )
        user_id = int(cursor.lastrowid)
        company_values = {
            "company_name": account["company_name"], "authorized_person": account["full_name"],
            "phone": account["phone"], "email": str(data.get("company_email") or account["email"]).strip(),
            "address": str(data.get("company_address") or "").strip(),
        }
        insert_available(conn, "company_info", company_values)
        settings = {
            "company_name": account["company_name"], "company_email": company_values["email"],
            "company_phone": account["phone"], "company_address": company_values["address"],
            "default_currency": str(data.get("currency") or "TRY"),
            "smtp_server": str(data.get("smtp_server") or "").strip(),
            "smtp_port": str(data.get("smtp_port") or "587"),
            "smtp_email": str(data.get("smtp_email") or "").strip(),
            "smtp_username": str(data.get("smtp_username") or data.get("smtp_email") or "").strip(),
            "smtp_password": str(data.get("smtp_password") or ""),
            "smtp_tls": "1", "admin_notification_email": str(data.get("admin_email") or account["email"]).strip(),
            "web_registration_enabled": "1", "web_setup_completed": "1",
            "installation_lat": str(data.get("installation_lat") or ""),
            "installation_lng": str(data.get("installation_lng") or ""),
            "installation_address": str(
                data.get("installation_address") or data.get("company_address") or ""
            ).strip(),
        }
        for key, value in settings.items():
            upsert_setting(conn, "settings", key, value)
        upsert_setting(conn, "internal_settings", "current_sector", sector)
        upsert_setting(conn, "internal_settings", "web_setup_completed", "1")
        conn.commit()
        user = dict(conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone())
    sent, message = send_registration_emails(user, "setup")
    user["_tenant_id"] = tenant["id"]
    user["_company_name"] = tenant["company_name"]
    return {
        "ok": True,
        "tenant": {"id": tenant["id"], "company_name": tenant["company_name"], "db_filename": tenant["db_filename"]},
        "user": public_user(user), "mail_sent": sent, "mail_message": message,
    }


def provision_desktop_tenant(data: dict, invitation_code: str = "") -> dict:
    """Create the first remote tenant for a completed desktop installation."""
    account = validate_account(data, require_company=True)
    company_name = normalize_identifier(account["company_name"])
    if any(normalize_identifier(tenant["company_name"]) == company_name for tenant in tenant_records()):
        raise PermissionError("Bu firma adi icin sunucu kaydi zaten bulunuyor.")
    has_invite = bool(str(invitation_code or "").strip())
    if has_invite:
        _claim_provision_invite(invitation_code)
    result = setup_application(data, allow_existing=True)
    if has_invite:
        tenant_id = str(dict(result.get("tenant") or {}).get("id") or "")
        with closing(registry_connect()) as conn:
            conn.execute(
                "UPDATE tenants SET license_type=?,license_status=?,license_end=? WHERE id=?",
                ("Invitation", "Active", "", tenant_id),
            )
            conn.commit()
    return result


def activate_tenant_invitation(data: dict) -> dict:
    """Activate an expired tenant after a verified account signs in with an invite."""
    tenant_id = str(data.get("tenant_id") or "").strip()
    identifier = str(data.get("identifier") or data.get("username") or "").strip()
    password = str(data.get("password") or "")
    invitation_code = str(data.get("invitation_code") or data.get("provision_invite_code") or "").strip()
    if not identifier or not password or not invitation_code:
        raise ValueError("Kullanici, parola ve davet kodu zorunludur.")
    user = authenticate_account(identifier, password, tenant_id)
    if not user:
        raise PermissionError("Kullanici adi veya parola hatali.")
    tenant_id = str(tenant_id or user.get("_tenant_id") or "").strip()
    if not tenant_id:
        raise LookupError("Firma bulunamadi.")
    _claim_provision_invite(invitation_code)
    with closing(registry_connect()) as conn:
        cursor = conn.execute(
            "UPDATE tenants SET active=1,license_type=?,license_status=?,license_start=?,license_end=? WHERE id=?",
            ("Invitation", "Active", utc_now().isoformat(timespec="seconds"), "", tenant_id),
        )
        conn.commit()
    if cursor.rowcount != 1:
        raise LookupError("Firma bulunamadi.")
    tenant = tenant_by_id(tenant_id)
    return {"ok": True, "tenant": tenant_access_summary(tenant)}


def register_account(data: dict, tenant_id: str | None = None) -> dict:
    account = validate_account(data)
    if tenant_id:
        tenant = tenant_by_id(tenant_id)
        if not tenant:
            raise LookupError("Firma bulunamadı.")
        set_tenant_context(tenant)
    if not active_tenant_id():
        if account["company_name"]:
            return setup_application(data, allow_existing=True)
        raise PermissionError("Firma seçimi gerekiyor. Yeni firma için firma adını girin.")
    with closing(db_connect()) as conn:
        if scalar(conn, "SELECT COUNT(*) FROM users", default=0) == 0:
            raise PermissionError("Önce ilk kurulum sihirbazını tamamlayın.")
        if setting_value(conn, "web_registration_enabled", "1") == "0":
            raise PermissionError("Yeni kullanıcı kaydı yönetici tarafından kapatılmış.")
        duplicate = find_account_by_identifier(conn, account["username"])
        duplicate = duplicate or find_account_by_identifier(conn, account["email"])
        if duplicate:
            raise ValueError("Bu kullanıcı adı veya e-posta zaten kayıtlı.")
        cursor = conn.execute(
            """
            INSERT INTO users (username,password,email,role,created_at,full_name,active,interface_edit_access)
            VALUES (?,?,?,?,?,?,1,0)
            """,
            (account["username"], password_hash(account["password"]), account["email"], "User", utc_now().isoformat(timespec="seconds"), account["full_name"]),
        )
        conn.commit()
        user = dict(conn.execute("SELECT * FROM users WHERE id=?", (cursor.lastrowid,)).fetchone())
    sent, message = send_registration_emails(user, "registration")
    user["_tenant_id"] = active_tenant_id()
    user["_company_name"] = active_company_name()
    return {"ok": True, "tenant": {"id": active_tenant_id(), "company_name": active_company_name()}, "user": public_user(user), "mail_sent": sent, "mail_message": message}


def authenticate_account(identifier: str, password: str, tenant_id: str | None = None) -> dict | None:
    clear_tenant_context()
    if tenant_id:
        selected = tenant_by_id(tenant_id)
        candidates = [selected] if selected else []
    else:
        candidates = tenant_records()
    for tenant in candidates:
        if not tenant:
            continue
        set_tenant_context(tenant)
        with closing(db_connect()) as conn:
            row = find_account_by_identifier(conn, identifier)
            if not row or not password_matches(password, row["password"]):
                continue
            if not str(row["password"] or "").startswith("pbkdf2_sha256$"):
                conn.execute("UPDATE users SET password=? WHERE id=?", (password_hash(password), row["id"]))
            conn.execute("UPDATE users SET last_login=? WHERE id=?", (utc_now().isoformat(timespec="seconds"), row["id"]))
            conn.commit()
            result = dict(conn.execute("SELECT * FROM users WHERE id=?", (row["id"],)).fetchone())
            temporary_expiry = _parse_registry_time(result.get("temporary_password_expires_at"))
            if bool(result.get("must_change_password")) and temporary_expiry and utc_now() > temporary_expiry:
                continue
            result["_tenant_id"] = tenant["id"]
            result["_company_name"] = tenant["company_name"]
            return result
    clear_tenant_context()
    return None


def auth_rate_limited(client_key: str) -> bool:
    now = time.time()
    with _AUTH_LOCK:
        recent = [stamp for stamp in _AUTH_FAILURES.get(client_key, []) if now - stamp < 900]
        _AUTH_FAILURES[client_key] = recent
        return len(recent) >= 10


def record_auth_failure(client_key: str) -> None:
    with _AUTH_LOCK:
        _AUTH_FAILURES.setdefault(client_key, []).append(time.time())


def clear_auth_failures(client_key: str) -> None:
    with _AUTH_LOCK:
        _AUTH_FAILURES.pop(client_key, None)


def create_database_backup(prefix: str = "manual") -> Path:
    configured = os.environ.get("AYEC_BACKUP_DIR", "").strip()
    backup_dir = Path(configured).expanduser().resolve() if configured else ROOT / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    target = backup_dir / f"{prefix}-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}.db"
    with closing(sqlite3.connect(active_db_path(), timeout=30)) as source:
        with closing(sqlite3.connect(target)) as destination:
            source.backup(destination)
            if destination.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("Otomatik yedek bütünlük kontrolünden geçemedi.")
            destination.commit()
    return target


WIPE_PRESERVE_TABLES = {
    "users", "settings", "internal_settings", "company_info", "web_sessions",
    "license_info", "registration", "sector_presets", "alembic_version",
    "schema_migrations", "app_labels", "device_brands", "product_bank_mappings",
    "automotive_maintenance_templates", "automotive_maintenance_template_items",
}


def tenant_sync_epoch(tenant_id: str | None = None) -> int:
    selected_tenant = str(tenant_id or active_tenant_id() or "")
    if not selected_tenant:
        return 1
    with closing(registry_connect()) as registry:
        return max(1, int(scalar(
            registry,
            "SELECT COALESCE(sync_epoch,1) FROM tenants WHERE id=?",
            (selected_tenant,),
            default=1,
        ) or 1))


def increment_tenant_sync_epoch(tenant_id: str) -> int:
    with closing(registry_connect()) as registry:
        registry.execute(
            "UPDATE tenants SET sync_epoch=COALESCE(sync_epoch,1)+1 WHERE id=?",
            (tenant_id,),
        )
        epoch = max(1, int(scalar(
            registry,
            "SELECT COALESCE(sync_epoch,1) FROM tenants WHERE id=?",
            (tenant_id,),
            default=1,
        ) or 1))
        registry.commit()
    return epoch


def validate_sync_epoch(body: dict) -> int:
    current = tenant_sync_epoch()
    supplied = body.get("sync_epoch")
    if supplied is None and current == 1:
        return current
    try:
        supplied_value = int(supplied)
    except (TypeError, ValueError):
        supplied_value = 0
    if supplied_value != current:
        raise ValueError(
            f"SYNC_RESET_REQUIRED: server epoch is {current}; refresh the desktop client"
        )
    return current


def wipe_user_data(user: dict, password: str, phrase: str) -> dict:
    if not role_is_admin(user.get("role")):
        raise PermissionError("Wipe All yalnızca yönetici tarafından çalıştırılabilir.")
    if phrase.strip() != "TÜM VERİLERİ SİL":
        raise ValueError("Onay metni hatalı.")
    with closing(db_connect()) as conn:
        stored = conn.execute("SELECT password FROM users WHERE id=?", (user["id"],)).fetchone()
        if not stored or not password_matches(password, stored["password"]):
            raise PermissionError("Yönetici parolası hatalı.")
    tenant_id = str(user.get("_tenant_id") or active_tenant_id() or "")
    backup = create_database_backup("pre-wipe")
    stored_backup = support_store_backup(user, backup.read_bytes(), backup.name)
    protected_until = (utc_now() + timedelta(days=30)).isoformat(timespec="seconds")
    with closing(registry_connect()) as registry:
        registry.execute(
            "UPDATE support_backups SET source='pre-wipe',protected_until=? WHERE id=?",
            (protected_until, int(stored_backup.get("backup_id") or 0)),
        )
        registry.commit()
    deleted: dict[str, int] = {}
    with closing(db_connect()) as conn:
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("BEGIN IMMEDIATE")
        tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        for table in tables:
            if table in WIPE_PRESERVE_TABLES:
                continue
            cursor = conn.execute(f'DELETE FROM "{table}"')
            deleted[table] = max(cursor.rowcount, 0)
        conn.commit()
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("VACUUM")
    sync_epoch = increment_tenant_sync_epoch(tenant_id)
    return {
        "ok": True,
        "deleted_rows": sum(deleted.values()),
        "tables": {table: count for table, count in deleted.items() if count},
        "backup": backup.name,
        "backup_id": int(stored_backup.get("backup_id") or 0),
        "protected_until": protected_until,
        "sync_epoch": sync_epoch,
    }


def insert_available(conn: sqlite3.Connection, table: str, values: dict) -> int:
    """Insert only columns present in an installed desktop database version."""
    columns = set(table_columns(conn, table))
    clean = {key: value for key, value in values.items() if key in columns}
    names = ",".join(f'"{key}"' for key in clean)
    marks = ",".join("?" for _ in clean)
    cursor = conn.execute(f'INSERT INTO "{table}" ({names}) VALUES ({marks})', tuple(clean.values()))
    return int(cursor.lastrowid)


def update_available(conn: sqlite3.Connection, table: str, row_id: int, values: dict) -> None:
    """Update only columns present in an installed desktop database version."""
    columns = set(table_columns(conn, table))
    clean = {key: value for key, value in values.items() if key in columns and key != "id"}
    if not clean:
        return
    assignments = ",".join(f'"{key}"=?' for key in clean)
    conn.execute(f'UPDATE "{table}" SET {assignments} WHERE id=?', (*clean.values(), row_id))


def save_web_customer_balances(
    conn: sqlite3.Connection,
    customer_id: int,
    balances: object,
) -> None:
    """Persist web customer opening balances in the same transaction."""
    if not isinstance(balances, dict):
        return
    updated_at = datetime.now().isoformat(timespec="seconds")
    for currency in ("TRY", "USD", "EUR"):
        try:
            balance = float(balances.get(currency, 0) or 0)
        except (TypeError, ValueError) as error:
            raise ValueError(f"Invalid {currency} balance") from error
        balance_id = scalar(
            conn,
            "SELECT id FROM customer_currency_balances "
            "WHERE customer_id=? AND currency=? ORDER BY id DESC LIMIT 1",
            (customer_id, currency),
            default=0,
        )
        values = {
            "customer_id": customer_id,
            "currency": currency,
            "balance": balance,
            "last_updated": updated_at,
        }
        if balance_id:
            update_available(conn, "customer_currency_balances", int(balance_id), values)
        else:
            # The customer/currency pair is unique; use an upsert so sync
            # remains idempotent even when a legacy database has no row id.
            conn.execute(
                """
                INSERT INTO customer_currency_balances
                    (customer_id, currency, balance, last_updated)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(customer_id, currency) DO UPDATE SET
                    balance=excluded.balance,
                    last_updated=excluded.last_updated
                """,
                (customer_id, currency, balance, updated_at),
            )


def link_web_automotive_service(
    conn: sqlite3.Connection,
    device_id: int,
    device_values: dict,
    request_values: dict,
) -> dict:
    """Create the vehicle, intake form and maintenance card atomically."""
    plate = str(
        request_values.get("vehicle_plate")
        or device_values.get("vehicle_plate")
        or device_values.get("serial_no")
        or ""
    ).strip().upper()
    if not plate:
        raise ValueError("Vehicle plate is required")
    customer_id = device_values.get("customer_id")
    created_at = device_values.get("created_at") or datetime.now().isoformat(timespec="seconds")
    model = str(
        request_values.get("vehicle_model_name")
        or device_values.get("device_model")
        or ""
    ).strip()
    odometer = int(float(request_values.get("vehicle_odometer") or 0))
    vehicle_values = {
        "customer_id": customer_id,
        "plate": plate,
        "brand": device_values.get("device_brand"),
        "model": model,
        "year": request_values.get("vehicle_year"),
        "vehicle_type": request_values.get("vehicle_type"),
        "engine_type": request_values.get("engine_type"),
        "fuel_type": request_values.get("fuel_type"),
        "last_known_odometer": odometer,
        "is_active": 1,
        "updated_at": created_at,
    }
    vehicle_id = scalar(
        conn,
        "SELECT id FROM customer_vehicles "
        "WHERE customer_id=? AND UPPER(REPLACE(plate,' ',''))=? "
        "ORDER BY id DESC LIMIT 1",
        (customer_id, re.sub(r"\s+", "", plate)),
        default=0,
    )
    if vehicle_id:
        update_available(conn, "customer_vehicles", int(vehicle_id), vehicle_values)
    else:
        vehicle_values["created_at"] = created_at
        vehicle_id = insert_available(conn, "customer_vehicles", vehicle_values)
    form_id = insert_available(
        conn,
        "automotive_service_forms",
        {
            "device_id": device_id,
            "tracking_no": device_values.get("tracking_no"),
            "customer_id": customer_id,
            "vehicle_id": vehicle_id,
            "vehicle_plate": plate,
            "vehicle_vin": request_values.get("vehicle_vin"),
            "entry_odometer": odometer,
            "created_at": created_at,
            "updated_at": created_at,
        },
    )
    card_id = insert_available(
        conn,
        "vehicle_maintenance_cards",
        {
            "vehicle_id": vehicle_id,
            "customer_id": customer_id,
            "customer_name": device_values.get("customer_name"),
            "customer_phone": request_values.get("customer_phone"),
            "vehicle_plate": plate,
            "vehicle_brand": device_values.get("device_brand"),
            "vehicle_model": model,
            "vehicle_year": request_values.get("vehicle_year"),
            "vehicle_type": request_values.get("vehicle_type"),
            "engine_type": request_values.get("engine_type"),
            "fuel_type": request_values.get("fuel_type"),
            "odometer": odometer,
            "service_date": device_values.get("entry_date"),
            "next_maintenance_date": device_values.get("estimated_date"),
            "notes": device_values.get("fault_description"),
            "linked_device_tracking_no": device_values.get("tracking_no"),
            "linked_device_id": device_id,
            "created_by": "Web",
            "created_at": created_at,
            "updated_at": created_at,
        },
    )
    update_available(
        conn,
        "devices",
        device_id,
        {"vehicle_maintenance_card_id": card_id},
    )
    return {"vehicle_id": int(vehicle_id), "form_id": form_id, "card_id": card_id}


def vehicle_maintenance_detail(card_id: int) -> dict:
    with closing(db_connect()) as conn:
        card_row = conn.execute(
            "SELECT * FROM vehicle_maintenance_cards WHERE id=?",
            (card_id,),
        ).fetchone()
        if not card_row:
            raise LookupError("Bak\u0131m kart\u0131 bulunamad\u0131")
        card = dict(card_row)
        items = rows(
            conn,
            "SELECT * FROM vehicle_maintenance_items WHERE card_id=? ORDER BY id",
            (card_id,),
        )
        appointment = None
        if card.get("draft_appointment_id"):
            appointment_row = conn.execute(
                "SELECT * FROM appointments WHERE id=?",
                (card["draft_appointment_id"],),
            ).fetchone()
            appointment = dict(appointment_row) if appointment_row else None
        service = None
        if card.get("linked_device_id"):
            service_row = conn.execute(
                "SELECT * FROM devices WHERE id=?",
                (card["linked_device_id"],),
            ).fetchone()
            service = dict(service_row) if service_row else None
        return {"ok": True, "card": card, "items": items, "appointment": appointment, "service": service}


def save_vehicle_maintenance_web(data: dict) -> dict:
    customer_id = int(data.get("customer_id") or 0)
    plate = str(data.get("vehicle_plate") or "").strip().upper()
    if not customer_id:
        raise ValueError("M\u00fc\u015fteri se\u00e7imi zorunludur")
    if not plate:
        raise ValueError("Plaka zorunludur")

    selected_items = [item for item in (data.get("items") or []) if bool(item.get("performed"))]
    if not selected_items:
        raise ValueError("En az bir bak\u0131m kalemi se\u00e7ilmelidir")

    now = datetime.now().isoformat(timespec="seconds")
    service_date = str(data.get("service_date") or datetime.now().strftime("%Y-%m-%d"))[:10]
    appointment_date = str(data.get("appointment_date") or data.get("manual_appointment_date") or "")[:10]
    appointment_time = str(data.get("appointment_time") or "09:00")[:5]
    labels = [str(item.get("item_label") or item.get("item_type") or "").strip() for item in selected_items]
    work_summary = ", ".join(label for label in labels if label)
    notes = str(data.get("notes") or "").strip()
    card_id = int(data.get("id") or 0)

    with closing(db_connect()) as conn:
        conn.execute("BEGIN IMMEDIATE")
        customer_row = conn.execute(
            "SELECT * FROM customers WHERE id=? AND COALESCE(is_deleted,0)=0",
            (customer_id,),
        ).fetchone()
        if not customer_row:
            raise LookupError("M\u00fc\u015fteri bulunamad\u0131")
        customer = dict(customer_row)
        customer_name = str(customer.get("name") or customer.get("full_name") or "").strip()
        customer_phone = str(customer.get("phone") or customer.get("phone1") or "").strip()

        vehicle_id = int(data.get("vehicle_id") or 0)
        if not vehicle_id:
            vehicle_id = int(scalar(
                conn,
                "SELECT id FROM customer_vehicles WHERE UPPER(TRIM(plate))=? ORDER BY id DESC LIMIT 1",
                (plate,),
                default=0,
            ) or 0)
        vehicle_values = {
            "customer_id": customer_id,
            "plate": plate,
            "brand": str(data.get("vehicle_brand") or "").strip(),
            "model": str(data.get("vehicle_model") or "").strip(),
            "year": int(data.get("vehicle_year") or 0) or None,
            "vehicle_type": str(data.get("vehicle_type") or "").strip(),
            "engine_type": str(data.get("engine_type") or "").strip(),
            "fuel_type": str(data.get("fuel_type") or "").strip(),
            "inspection_due_date": str(data.get("inspection_due_date") or "")[:10],
            "last_known_odometer": int(data.get("odometer") or 0),
            "notes": notes,
            "is_active": 1,
            "updated_at": now,
        }
        if vehicle_id:
            update_available(conn, "customer_vehicles", vehicle_id, vehicle_values)
        else:
            vehicle_values["created_at"] = now
            vehicle_id = insert_available(conn, "customer_vehicles", vehicle_values)

        card_values = {
            "vehicle_id": vehicle_id,
            "customer_id": customer_id,
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "vehicle_plate": plate,
            "vehicle_brand": vehicle_values["brand"],
            "vehicle_model": vehicle_values["model"],
            "vehicle_year": vehicle_values["year"],
            "vehicle_type": vehicle_values["vehicle_type"],
            "engine_type": vehicle_values["engine_type"],
            "fuel_type": vehicle_values["fuel_type"],
            "inspection_due_date": vehicle_values["inspection_due_date"],
            "odometer": vehicle_values["last_known_odometer"],
            "service_date": service_date,
            "next_maintenance_date": str(data.get("next_maintenance_date") or "")[:10],
            "manual_appointment_date": appointment_date,
            "appointment_date": appointment_date,
            "appointment_time": appointment_time,
            "notes": notes,
            "reminder_date": str(data.get("reminder_date") or "")[:10],
            "created_by": "Web",
            "updated_at": now,
        }
        if card_id:
            if not scalar(conn, "SELECT COUNT(*) FROM vehicle_maintenance_cards WHERE id=?", (card_id,)):
                raise LookupError("Bak\u0131m kart\u0131 bulunamad\u0131")
            update_available(conn, "vehicle_maintenance_cards", card_id, card_values)
            conn.execute("DELETE FROM vehicle_maintenance_items WHERE card_id=?", (card_id,))
        else:
            card_values["created_at"] = now
            card_id = insert_available(conn, "vehicle_maintenance_cards", card_values)

        for item in selected_items:
            insert_available(conn, "vehicle_maintenance_items", {
                "card_id": card_id,
                "item_type": str(item.get("item_type") or "custom").strip(),
                "item_label": str(item.get("item_label") or item.get("item_type") or "").strip(),
                "performed": 1,
                "interval_days": int(item.get("interval_days") or 0),
                "interval_km": int(item.get("interval_km") or 0),
                "next_due_date": str(item.get("next_due_date") or "")[:10],
                "next_due_odometer": int(item.get("next_due_odometer") or 0),
                "notes": str(item.get("notes") or "").strip(),
            })

        existing_card = dict(conn.execute(
            "SELECT * FROM vehicle_maintenance_cards WHERE id=?",
            (card_id,),
        ).fetchone())
        appointment_id = int(existing_card.get("draft_appointment_id") or 0)
        appointment_values = {
            "customer_id": customer_id,
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "date": appointment_date,
            "time": appointment_time,
            "title": "Ara\u00e7 bak\u0131m randevusu",
            "description": work_summary,
            "status": "Planland\u0131",
            "source_type": "vehicle_maintenance",
            "source_ref_id": card_id,
            "is_auto_created": 1,
            "updated_at": now,
        }
        if appointment_date:
            if appointment_id:
                update_available(conn, "appointments", appointment_id, appointment_values)
            else:
                appointment_values["created_at"] = now
                appointment_id = insert_available(conn, "appointments", appointment_values)

        device_id = int(existing_card.get("linked_device_id") or 0)
        tracking_no = str(existing_card.get("linked_device_tracking_no") or "").strip()
        if not tracking_no:
            tracking_no = f"SRV-WEB-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        device_values = {
            "tracking_no": tracking_no,
            "customer_id": customer_id,
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "device_type": "Otomobil",
            "device_brand": vehicle_values["brand"],
            "device_model": vehicle_values["model"],
            "serial_no": plate,
            "vehicle_plate": plate,
            "vehicle_year": vehicle_values["year"],
            "fault_description": work_summary,
            "repair_details": notes,
            "status": "Bekliyor",
            "entry_date": service_date,
            "estimated_date": appointment_date,
            "maintenance_card_id": card_id,
            "service_source": "vehicle_maintenance",
            "updated_at": now,
        }
        if device_id:
            update_available(conn, "devices", device_id, device_values)
        else:
            device_values["created_at"] = now
            device_id = insert_available(conn, "devices", device_values)

        service_form_id = int(scalar(
            conn,
            "SELECT id FROM automotive_service_forms WHERE device_id=? ORDER BY id DESC LIMIT 1",
            (device_id,),
            default=0,
        ) or 0)
        service_form_values = {
            "device_id": device_id,
            "tracking_no": tracking_no,
            "vehicle_id": vehicle_id,
            "updated_at": now,
        }
        if service_form_id:
            update_available(conn, "automotive_service_forms", service_form_id, service_form_values)
        else:
            service_form_values["created_at"] = now
            insert_available(conn, "automotive_service_forms", service_form_values)

        update_available(conn, "vehicle_maintenance_cards", card_id, {
            "draft_appointment_id": appointment_id or None,
            "linked_device_tracking_no": tracking_no,
            "linked_device_id": device_id,
            "updated_at": now,
        })
        conn.commit()
        return {
            "ok": True,
            "id": card_id,
            "vehicle_id": vehicle_id,
            "appointment_id": appointment_id or None,
            "tracking_no": tracking_no,
            "device_id": device_id,
            "customer_phone": customer_phone,
            "customer_name": customer_name,
            "vehicle_plate": plate,
            "important_items": [
                label for item, label in zip(selected_items, labels)
                if str(item.get("item_type") or "") != "glass_water"
            ],
        }


def exchange_rates(refresh: bool = True) -> dict:
    """Return the same latest TCMB selling rates used by the desktop application."""
    result = {
        "TRY": {"currency": "TRY", "buying": 1.0, "selling": 1.0, "date": datetime.now().strftime("%Y-%m-%d"), "source": "Sabit"}
    }
    with closing(db_connect()) as conn:
        if refresh and scalar(conn, "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='exchange_rates'"):
            try:
                today = datetime.now().strftime("%Y-%m-%d")
                has_today = scalar(conn, "SELECT COUNT(*) FROM exchange_rates WHERE DATE(effective_date)=DATE(?)", (today,))
                if not has_today:
                    request = Request(
                        "https://www.tcmb.gov.tr/kurlar/today.xml",
                        headers={"User-Agent": "AYEC-Pro/2.0"},
                    )
                    with urlopen(request, timeout=4) as response:
                        root = ElementTree.fromstring(response.read())
                    for node in root.findall("Currency"):
                        currency = str(node.get("CurrencyCode") or "").upper()
                        if currency not in {"USD", "EUR"}:
                            continue
                        buying_node = node.find("ForexBuying")
                        selling_node = node.find("ForexSelling")
                        buying = float(buying_node.text or 0) if buying_node is not None else 0
                        selling = float(selling_node.text or 0) if selling_node is not None else 0
                        if selling > 0:
                            insert_available(conn, "exchange_rates", {
                                "currency": currency, "buying_rate": buying or selling,
                                "selling_rate": selling,
                                "effective_date": now_text if (now_text := datetime.now().strftime("%Y-%m-%d %H:%M:%S")) else today,
                                "source": "TCMB", "created_at": now_text,
                            })
                    conn.commit()
            except Exception:
                # The last successful desktop rate remains usable when TCMB is temporarily unavailable.
                pass
        if scalar(conn, "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='exchange_rates'"):
            for currency in ("USD", "EUR"):
                row = conn.execute(
                    """
                    SELECT currency,buying_rate,selling_rate,effective_date,source
                    FROM exchange_rates WHERE UPPER(currency)=?
                    ORDER BY datetime(created_at) DESC,id DESC LIMIT 1
                    """,
                    (currency,),
                ).fetchone()
                if row and float(row["selling_rate"] or 0) > 0:
                    result[currency] = {
                        "currency": currency,
                        "buying": float(row["buying_rate"] or row["selling_rate"]),
                        "selling": float(row["selling_rate"]),
                        "date": row["effective_date"] or "",
                        "source": row["source"] or "TCMB",
                    }
    return result


def resolve_exchange_rate(conn: sqlite3.Connection, currency: str, supplied=None) -> float:
    currency = str(currency or "TRY").upper()
    if currency == "TRY":
        return 1.0
    try:
        supplied_rate = float(supplied or 0)
    except (TypeError, ValueError):
        supplied_rate = 0.0
    if supplied_rate > 0:
        if currency in {"USD", "EUR"} and supplied_rate <= 1:
            raise ValueError(f"{currency} satis kuru gecersiz")
        return supplied_rate
    row = conn.execute(
        "SELECT selling_rate FROM exchange_rates WHERE UPPER(currency)=? ORDER BY datetime(created_at) DESC,id DESC LIMIT 1",
        (currency,),
    ).fetchone()
    rate = float(row[0] or 0) if row else 0.0
    if currency in {"USD", "EUR"} and 0 < rate <= 1:
        raise ValueError(f"{currency} satis kuru gecersiz")
    if rate <= 0:
        raise ValueError(f"{currency} satış kuru bulunamadı. Kur bilgisini güncelleyip tekrar deneyin.")
    return rate


def normalize_accounting_payload(
    conn: sqlite3.Connection,
    data: dict,
    existing: dict | None = None,
) -> dict:
    """Return canonical original-currency and TRY accounting values."""
    payload = dict(data)
    current = existing or {}
    currency = str(payload.get("currency") or current.get("currency") or "TRY").upper()
    if currency not in {"TRY", "USD", "EUR"}:
        raise ValueError("Para birimi TRY, USD veya EUR olmal\u0131d\u0131r")

    raw_amount = payload.get("original_amount")
    if raw_amount in (None, ""):
        raw_amount = payload.get("amount")
    if raw_amount in (None, ""):
        raw_amount = current.get("original_amount", current.get("amount", 0))
    try:
        amount = parse_money_amount(raw_amount)
    except (TypeError, ValueError) as error:
        raise ValueError("Mali i\u015flem tutar\u0131 ge\u00e7ersiz") from error
    if amount < 0:
        raise ValueError("Mali i\u015flem tutar\u0131 negatif olamaz")

    supplied_rate = payload.get("exchange_rate")
    same_currency = currency == str(current.get("currency") or "TRY").upper()
    if supplied_rate in (None, "") and same_currency:
        supplied_rate = current.get("exchange_rate")
    rate = resolve_exchange_rate(conn, currency, supplied_rate)
    payload.update({
        "amount": amount,
        "original_amount": amount,
        "currency": currency,
        "exchange_rate": rate,
        "try_equivalent": round(amount * rate, 4),
    })
    return payload


def parse_money_amount(value: object) -> float:
    """Parse browser, desktop and Turkish-locale money values consistently."""
    if value in (None, ""):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace("\u00a0", "").replace(" ", "")
    text = re.sub(r"[^0-9,.-]", "", text)
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        tail = text.rsplit(",", 1)[1]
        text = text.replace(".", "").replace(",", ".") if len(tail) <= 2 else text.replace(",", "")
    elif text.count(".") > 1:
        text = text.replace(".", "")
    elif text.count(".") == 1 and len(text.rsplit(".", 1)[1]) == 3:
        text = text.replace(".", "")
    return float(text or 0)


def save_stock_card(data: dict) -> dict:
    """Save part, movement and purchase expense in one atomic desktop-compatible operation."""
    now = datetime.now()
    name = str(data.get("name") or "").strip()
    code = str(data.get("code") or "").strip()
    if not name or not code:
        raise ValueError("Stok kodu ve ürün adı zorunludur")
    currency = str(data.get("currency") or "TRY").upper()
    if currency not in {"TRY", "USD", "EUR"}:
        raise ValueError("Para birimi TRY, USD veya EUR olmalıdır")
    new_stock = max(0.0, float(data.get("stock") or 0))
    purchase_price = max(0.0, float(data.get("purchase_price") or 0))
    sale_price = max(0.0, float(data.get("price") or 0))
    row_id = int(data.get("id") or 0)
    with closing(db_connect()) as conn:
        conn.execute("BEGIN IMMEDIATE")
        old = None
        if row_id:
            old = conn.execute("SELECT * FROM parts WHERE id=? AND COALESCE(is_deleted,0)=0", (row_id,)).fetchone()
            if not old:
                raise LookupError("Stok kartı bulunamadı")
            old_stock = float(old["stock"] or 0)
            columns = set(table_columns(conn, "parts"))
            values = {
                "name": name, "part_name": name, "code": code,
                "barcode": str(data.get("barcode") or "").strip(),
                "category": str(data.get("category") or "Genel").strip(),
                "currency": currency, "stock": new_stock,
                "min_stock": max(0.0, float(data.get("min_stock") or 0)),
                "purchase_price": purchase_price, "price": sale_price,
                "brand": str(data.get("brand") or "").strip(),
                "shelf_number": str((data.get("shelf_number") if "shelf_number" in data else (old["shelf_number"] if "shelf_number" in columns else "")) or "").strip(),
                "oem_code": str((data.get("oem_code") if "oem_code" in data else (old["oem_code"] if "oem_code" in columns else "")) or "").strip(),
                "equivalent_code": str((data.get("equivalent_code") if "equivalent_code" in data else (old["equivalent_code"] if "equivalent_code" in columns else "")) or "").strip(),
                "compatible_models": str((data.get("compatible_models") if "compatible_models" in data else (old["compatible_models"] if "compatible_models" in columns else "")) or "").strip(),
                "description": str(data.get("description") or "").strip(),
                "updated_at": now.isoformat(timespec="microseconds"),
            }
            clean = {key: value for key, value in values.items() if key in columns}
            conn.execute(
                f'UPDATE parts SET {",".join(f"\"{key}\"=?" for key in clean)} WHERE id=?',
                (*clean.values(), row_id),
            )
        else:
            old_stock = 0.0
            row_id = insert_available(conn, "parts", {
                "name": name, "part_name": name, "code": code,
                "barcode": str(data.get("barcode") or "").strip(),
                "category": str(data.get("category") or "Genel").strip(),
                "currency": currency, "stock": new_stock,
                "min_stock": max(0.0, float(data.get("min_stock") or 0)),
                "purchase_price": purchase_price, "price": sale_price,
                "brand": str(data.get("brand") or "").strip(),
                "shelf_number": str(data.get("shelf_number") or "").strip(),
                "oem_code": str(data.get("oem_code") or "").strip(),
                "equivalent_code": str(data.get("equivalent_code") or "").strip(),
                "compatible_models": str(data.get("compatible_models") or "").strip(),
                "description": str(data.get("description") or "").strip(),
                "created_at": now.isoformat(timespec="seconds"), "is_deleted": 0,
                "updated_at": now.isoformat(timespec="microseconds"),
            })
        delta = round(new_stock - old_stock, 6)
        movement_id = None
        if delta:
            movement_id = insert_available(conn, "stock_movements", {
                "part_id": row_id,
                "movement_type": "Giriş" if delta > 0 else "Çıkış",
                "amount": abs(delta), "new_stock": new_stock,
                "description": "Ürün ekleme" if old is None else "Stok düzenleme",
                "created_at": now.isoformat(timespec="seconds"), "is_deleted": 0,
            })
        finance_id = None
        expense = round(max(delta, 0) * purchase_price, 4)
        rate = resolve_exchange_rate(conn, currency, data.get("exchange_rate")) if expense else (1.0 if currency == "TRY" else float(data.get("exchange_rate") or 0))
        if expense:
            ref_no = f"WEB-STOCK-{row_id}-{movement_id or 0}"
            finance_id = insert_available(conn, "accounting", {
                "type": "Gider", "category": "Stok Alımı" if old is None else "Stok Güncelleme",
                "amount": expense, "original_amount": expense,
                "try_equivalent": round(expense * rate, 4), "currency": currency,
                "exchange_rate": rate,
                "description": f"{'Stok Alımı' if old is None else 'Stok Güncelleme'}: {max(delta, 0):g} x {name}",
                "date": now.strftime("%Y-%m-%d"), "created_at": now.isoformat(timespec="seconds"),
                "payment_method": str(data.get("payment_method") or "Nakit"),
                "ref_no": ref_no, "product_service_id": row_id,
                "product_service_type": "stock", "is_deleted": 0,
                "selected_services": json.dumps({"part_id": row_id, "movement_id": movement_id, "quantity": max(delta, 0), "unit_cost": purchase_price, "currency": currency}, ensure_ascii=False),
            })
        elif old is not None and row_id:
            linked = conn.execute(
                "SELECT id,amount FROM accounting WHERE product_service_id=? AND product_service_type='stock' "
                "AND COALESCE(is_deleted,0)=0 ORDER BY id DESC LIMIT 1",
                (row_id,),
            ).fetchone()
            if linked:
                linked_amount = float(linked[1] or 0)
                linked_rate = resolve_exchange_rate(conn, currency, data.get("exchange_rate"))
                conn.execute(
                "UPDATE accounting SET amount=?,currency=?,exchange_rate=?,try_equivalent=?,original_amount=? WHERE id=?",
                (round(linked_amount * linked_rate, 4), currency, linked_rate, round(linked_amount * linked_rate, 4), linked_amount, int(linked[0])),
                )
        conn.commit()
        part = dict(conn.execute("SELECT * FROM parts WHERE id=?", (row_id,)).fetchone())
    return {"ok": True, "id": row_id, "part": part, "delta": delta, "movement_id": movement_id, "finance_id": finance_id, "expense": expense, "currency": currency, "exchange_rate": rate}


def reconcile_stock_finance(part_ids: list[int]) -> list[dict]:
    """Idempotently repair stock cards saved by the former web flow without DB signals."""
    repaired = []
    now = datetime.now()
    exchange_rates(refresh=False)
    with closing(db_connect()) as conn:
        conn.execute("BEGIN IMMEDIATE")
        for part_id in part_ids:
            part_row = conn.execute("SELECT * FROM parts WHERE id=? AND COALESCE(is_deleted,0)=0", (int(part_id),)).fetchone()
            if not part_row:
                continue
            part = dict(part_row)
            marker = f"WEB-STOCK-RECONCILE-{part_id}"
            if conn.execute("SELECT 1 FROM accounting WHERE ref_no=? LIMIT 1", (marker,)).fetchone():
                continue
            existing_finance = conn.execute(
                "SELECT 1 FROM accounting WHERE product_service_id=? AND product_service_type='stock' "
                "AND type='Gider' AND COALESCE(is_deleted,0)=0 LIMIT 1",
                (part_id,),
            ).fetchone()
            if existing_finance:
                continue
            stock = max(0.0, float(part.get("stock") or 0))
            purchase_price = max(0.0, float(part.get("purchase_price") or 0))
            if stock <= 0 or purchase_price <= 0:
                continue
            movement = conn.execute(
                "SELECT id FROM stock_movements WHERE part_id=? AND COALESCE(is_deleted,0)=0 AND movement_type LIKE 'Giriş%' ORDER BY id LIMIT 1",
                (part_id,),
            ).fetchone()
            movement_id = int(movement[0]) if movement else insert_available(conn, "stock_movements", {
                "part_id": part_id, "movement_type": "Giriş", "amount": stock, "new_stock": stock,
                "description": "Web stok sinyali düzeltmesi", "created_at": part.get("created_at") or now.isoformat(timespec="seconds"), "is_deleted": 0,
            })
            currency = str(part.get("currency") or "TRY").upper()
            rate = resolve_exchange_rate(conn, currency)
            expense = round(stock * purchase_price, 4)
            finance_id = insert_available(conn, "accounting", {
                "type": "Gider", "category": "Stok Alımı", "amount": expense,
                "original_amount": expense, "try_equivalent": round(expense * rate, 4),
                "currency": currency, "exchange_rate": rate,
                "description": f"Stok Alımı: {stock:g} x {part.get('name') or part.get('part_name') or ''}",
                "date": str(part.get("created_at") or now.strftime("%Y-%m-%d"))[:10],
                "created_at": part.get("created_at") or now.isoformat(timespec="seconds"),
                "payment_method": "Nakit", "ref_no": marker,
                "product_service_id": part_id, "product_service_type": "stock", "is_deleted": 0,
                "selected_services": json.dumps({"repair": True, "part_id": part_id, "movement_id": movement_id, "quantity": stock, "unit_cost": purchase_price, "currency": currency}, ensure_ascii=False),
            })
            repaired.append({"part_id": part_id, "movement_id": movement_id, "finance_id": finance_id, "expense": expense, "currency": currency, "try_equivalent": round(expense * rate, 4)})
        conn.commit()
    return repaired


def repair_explicit_stock_accounting_currency(conn: sqlite3.Connection) -> int:
    """Repair legacy stock expenses only when their line payload proves currency."""
    repaired = 0
    finance_rows = rows(
        conn,
        "SELECT id,currency,exchange_rate,selected_services FROM accounting "
        "WHERE COALESCE(is_deleted,0)=0 AND COALESCE(selected_services,'')<>''",
    )
    for finance_row in finance_rows:
        try:
            payload = json.loads(finance_row.get("selected_services") or "[]")
        except (TypeError, ValueError):
            continue
        items = payload if isinstance(payload, list) else [payload]
        items = [item for item in items if isinstance(item, dict)]
        items = [
            item
            for item in items
            if item.get("kind") == "stock_purchase"
            or item.get("part_id") not in (None, "")
            or item.get("repair") is True
        ]
        currencies = {
            str(item.get("currency") or "").upper()
            for item in items
            if str(item.get("currency") or "").upper() in {"USD", "EUR"}
        }
        if len(currencies) != 1:
            continue
        currency = currencies.pop()
        original_amount = 0.0
        for item in items:
            if str(item.get("currency") or "").upper() != currency:
                continue
            line_total = item.get("line_total")
            if line_total in (None, ""):
                quantity = parse_money_amount(item.get("quantity") or 0)
                unit_price = parse_money_amount(
                    item.get("unit_price") or item.get("unit_cost") or 0
                )
                line_total = quantity * unit_price
            original_amount += parse_money_amount(line_total)
        if original_amount <= 0:
            continue
        current_currency = str(finance_row.get("currency") or "TRY").upper()
        current_rate = parse_money_amount(finance_row.get("exchange_rate") or 0)
        if current_currency == currency and current_rate > 1:
            continue
        try:
            rate = resolve_exchange_rate(conn, currency)
        except ValueError:
            continue
        try_equivalent = round(original_amount * rate, 4)
        conn.execute(
            "UPDATE accounting SET amount=?,original_amount=?,currency=?,"
            "exchange_rate=?,try_equivalent=? WHERE id=?",
            (
                round(original_amount, 4),
                round(original_amount, 4),
                currency,
                rate,
                try_equivalent,
                int(finance_row["id"]),
            ),
        )
        repaired += 1
    if repaired:
        conn.commit()
    return repaired


def _customer_balance(conn: sqlite3.Connection, customer_id: int, currency: str) -> float:
    row = conn.execute(
        "SELECT balance FROM customer_currency_balances WHERE customer_id=? AND currency=?",
        (customer_id, currency),
    ).fetchone()
    return float(row[0] or 0) if row else 0.0


def _set_customer_balance(conn: sqlite3.Connection, customer_id: int, currency: str, balance: float, now: datetime) -> None:
    conn.execute(
        """
        INSERT INTO customer_currency_balances (customer_id,currency,balance,last_updated)
        VALUES (?,?,?,?)
        ON CONFLICT(customer_id,currency) DO UPDATE SET balance=excluded.balance,last_updated=excluded.last_updated
        """,
        (customer_id, currency, balance, now.isoformat(timespec="seconds")),
    )


def _service_used_parts_total_try(conn: sqlite3.Connection, tracking_no: str) -> float:
    columns = set(table_columns(conn, "used_parts"))
    if not columns:
        return 0.0
    price_try = (
        "CASE WHEN COALESCE(price_try,0)>0 THEN price_try "
        "WHEN UPPER(COALESCE(currency,'TRY'))='TRY' THEN COALESCE(price,0) "
        "WHEN COALESCE(exchange_rate,0)>0 "
        "THEN COALESCE(price,0)*exchange_rate ELSE 0 END"
        if {"price_try", "exchange_rate"} <= columns
        else "COALESCE(price,0)"
    )
    deleted = " AND COALESCE(is_deleted,0)=0" if "is_deleted" in columns else ""
    return round(
        float(
            scalar(
                conn,
                f"SELECT COALESCE(SUM(({price_try})*COALESCE(quantity,1)),0) "
                f"FROM used_parts WHERE tracking_no=?{deleted}",
                (tracking_no,),
                0,
            )
            or 0
        ),
        4,
    )


def _sync_service_debit(
    conn: sqlite3.Connection,
    customer_id: int,
    tracking_no: str,
    amount_try: float,
    now: datetime,
) -> int | None:
    row = conn.execute(
        "SELECT id,COALESCE(amount,0) FROM currency_transactions "
        "WHERE customer_id=? AND currency='TRY' AND transaction_type='DEBIT' "
        "AND tracking_no=? ORDER BY id DESC LIMIT 1",
        (customer_id, tracking_no),
    ).fetchone()
    debit_id = int(row[0]) if row else None
    old_amount = float(row[1] or 0) if row else 0.0
    amount_try = round(max(0.0, float(amount_try or 0)), 4)
    delta = round(amount_try - old_amount, 4)
    if abs(delta) <= 0.0001:
        return debit_id
    current = _customer_balance(conn, customer_id, "TRY")
    updated_balance = round(current - delta, 4)
    description = f"Servis hizmet borcu: {tracking_no}"
    if debit_id:
        conn.execute(
            "UPDATE currency_transactions SET amount=?,try_equivalent=?,description=?,current_balance=? "
            "WHERE id=?",
            (amount_try, amount_try, description, updated_balance, debit_id),
        )
    elif amount_try > 0:
        debit_id = insert_available(
            conn,
            "currency_transactions",
            {
                "customer_id": customer_id,
                "transaction_type": "DEBIT",
                "amount": amount_try,
                "currency": "TRY",
                "exchange_rate": 1,
                "try_equivalent": amount_try,
                "description": description,
                "tracking_no": tracking_no,
                "created_at": now.isoformat(timespec="seconds"),
                "current_balance": updated_balance,
            },
        )
    _set_customer_balance(conn, customer_id, "TRY", updated_balance, now)
    return debit_id


def _reconcile_service_debits(conn: sqlite3.Connection) -> int:
    now = datetime.now()
    repaired = 0
    service_rows = conn.execute(
        """
        SELECT customer_id,tracking_no,
               COALESCE(labor_cost,0),
               COALESCE(cargo_fee,0)
        FROM devices
        WHERE COALESCE(is_deleted,0)=0
          AND COALESCE(customer_id,0)>0
          AND COALESCE(tracking_no,'')<>''
        """
    ).fetchall()
    for customer_id, tracking_no, labor_cost, cargo_fee in service_rows:
        amount_try = round(
            float(labor_cost or 0)
            + float(cargo_fee or 0)
            + _service_used_parts_total_try(conn, str(tracking_no)),
            4,
        )
        row = conn.execute(
            "SELECT COALESCE(amount,0) FROM currency_transactions "
            "WHERE customer_id=? AND currency='TRY' AND transaction_type='DEBIT' "
            "AND tracking_no=? ORDER BY id DESC LIMIT 1",
            (int(customer_id), str(tracking_no)),
        ).fetchone()
        old_amount = float(row[0] or 0) if row else 0.0
        if abs(old_amount - amount_try) <= 0.0001:
            continue
        _sync_service_debit(
            conn,
            int(customer_id),
            str(tracking_no),
            amount_try,
            now,
        )
        _refresh_service_payment_status(conn, str(tracking_no))
        repaired += 1
    if repaired:
        conn.commit()
    return repaired


def _refresh_service_payment_status(
    conn: sqlite3.Connection, tracking_no: str
) -> str:
    debit = float(
        scalar(
            conn,
            "SELECT COALESCE(SUM(COALESCE(try_equivalent,amount,0)),0) FROM currency_transactions "
            "WHERE tracking_no=? AND transaction_type='DEBIT'",
            (tracking_no,),
            0,
        )
        or 0
    )
    credit = float(
        scalar(
            conn,
            "SELECT COALESCE(SUM(COALESCE(try_equivalent,amount,0)),0) FROM currency_transactions "
            "WHERE tracking_no=? AND transaction_type='CREDIT'",
            (tracking_no,),
            0,
        )
        or 0
    )
    if debit <= 0:
        status = "Beklemede"
    elif credit <= 0:
        status = "\u00d6denmedi"
    elif credit + 0.0001 < debit:
        status = "K\u0131smi \u00d6dendi"
    else:
        status = "\u00d6dendi"
    if scalar(
        conn,
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='devices'",
        default=0,
    ):
        device_columns = set(table_columns(conn, "devices"))
        if "payment_status" in device_columns:
            conn.execute(
                "UPDATE devices SET payment_status=? WHERE tracking_no=?",
                (status, tracking_no),
            )
    return status


def commit_sales_hub(data: dict) -> dict:
    """Execute Sales Hub proforma, paid sale or service signal as one database transaction."""
    mode = str(data.get("mode") or "").lower()
    if mode not in {"proforma", "payment", "service"}:
        raise ValueError("Geçersiz Sales Hub işlemi")
    customer_name_hint = str(data.get("customer_name") or "").strip()
    try:
        customer_id = int(data.get("customer_id") or 0)
    except (TypeError, ValueError):
        customer_id = 0
    if not customer_id and not customer_name_hint:
        raise ValueError("Müşteri seçilmelidir")
    raw_lines = data.get("lines") or []
    if not isinstance(raw_lines, list) or not raw_lines:
        raise ValueError("Sepette en az bir ürün bulunmalıdır")
    currency = str(data.get("currency") or "TRY").upper()
    if currency not in {"TRY", "USD", "EUR"}:
        raise ValueError("Geçersiz teklif para birimi")
    rates = data.get("rates") if isinstance(data.get("rates"), dict) else {}
    now = datetime.now()
    vat_percent = max(0.0, min(float(data.get("vat_rate") or 0), 100.0))
    with closing(db_connect()) as conn:
        conn.execute("BEGIN IMMEDIATE")
        if not customer_id and customer_name_hint:
            customer_match = conn.execute(
                "SELECT id FROM customers WHERE lower(trim(name))=lower(trim(?)) "
                "AND COALESCE(is_deleted,0)=0 ORDER BY id DESC LIMIT 1",
                (customer_name_hint,),
            ).fetchone()
            if customer_match:
                customer_id = int(customer_match["id"])
        if not customer_id:
            raise ValueError("M\u00fc\u015fteri se\u00e7ilmelidir")
        customer_row = conn.execute("SELECT * FROM customers WHERE id=? AND COALESCE(is_deleted,0)=0", (customer_id,)).fetchone()
        if not customer_row:
            raise LookupError("Müşteri kaydı bulunamadı")
        customer = dict(customer_row)
        selected_rate = resolve_exchange_rate(conn, currency, data.get("exchange_rate") or rates.get(currency))
        lines = []
        subtotal_try = 0.0
        total_cost_try = 0.0
        for raw in raw_lines:
            part_id = int(raw.get("product_id") or raw.get("part_id") or 0)
            quantity = max(0.0, float(raw.get("qty") or 0))
            if not part_id or quantity <= 0:
                raise ValueError("Sepet satırı geçersiz")
            part_row = conn.execute("SELECT * FROM parts WHERE id=? AND COALESCE(is_deleted,0)=0", (part_id,)).fetchone()
            if not part_row:
                raise LookupError("Sepetteki stok kartlarından biri bulunamadı")
            part = dict(part_row)
            if mode == "payment" and quantity > float(part.get("stock") or 0):
                raise ValueError(f"{part.get('name') or part.get('part_name')} için yeterli stok yok")
            source_currency = str(part.get("currency") or "TRY").upper()
            source_rate = resolve_exchange_rate(conn, source_currency, rates.get(source_currency))
            unit_try = round(float(part.get("price") or 0) * source_rate, 6)
            unit_selected = round(unit_try / selected_rate, 6)
            cost_try = round(float(part.get("purchase_price") or 0) * source_rate, 6)
            line_try = unit_try * quantity
            subtotal_try += line_try
            total_cost_try += cost_try * quantity
            lines.append({
                "part": part, "part_id": part_id, "qty": quantity,
                "source_currency": source_currency, "source_rate": source_rate,
                "unit_try": unit_try, "unit_selected": unit_selected,
                "line_try": line_try, "line_selected": line_try / selected_rate,
            })
        subtotal_try = round(subtotal_try, 4)
        vat_try = round(subtotal_try * vat_percent / 100.0, 4)
        total_try = round(subtotal_try + vat_try, 4)
        subtotal = round(subtotal_try / selected_rate, 4)
        vat_amount = round(vat_try / selected_rate, 4)
        total = round(total_try / selected_rate, 4)
        symbol = {"TRY": "₺", "USD": "$", "EUR": "€"}[currency]
        customer_name = customer.get("name") or customer.get("customer_name") or ""
        # Proforma issuer comes from Firma AyarlarÄ±. The customer remains the
        # recipient/contact; it must not replace the issuer company name.
        issuer_company = setting_value(conn, "company_name", "").strip()
        if not issuer_company:
            company_row = conn.execute(
                "SELECT company_name FROM company_info ORDER BY id DESC LIMIT 1"
            ).fetchone()
            issuer_company = str(company_row["company_name"] if company_row else "").strip()
        if not issuer_company:
            issuer_company = str(customer.get("company_name") or customer_name or "AYEC Pro").strip()
        result = {
            "ok": True, "mode": mode, "currency": currency, "currency_symbol": symbol,
            "exchange_rate": selected_rate, "subtotal": subtotal, "vat_amount": vat_amount,
            "total": total, "subtotal_try": subtotal_try, "vat_amount_try": vat_try,
            "total_try": total_try,
        }
        if mode == "proforma":
            from src.utils.service_work_details import (
                clean_offer_line_description,
            )
            existing_offer_id = int(data.get("offer_id") or 0)
            existing_offer = None
            if existing_offer_id:
                existing_offer = conn.execute(
                    "SELECT * FROM offers WHERE id=?",
                    (existing_offer_id,),
                ).fetchone()
                if not existing_offer:
                    raise LookupError("Teklif kaydi bulunamadi")
                status = str(existing_offer["status"] or "").strip().casefold()
                status = status.replace("\u0131", "i").replace("\u015f", "s")
                if status in {"accepted", "processed", "kabul edildi", "islendi"}:
                    raise ValueError("Kabul edilmis teklif degistirilemez")
            offer_no = str(
                data.get("offer_no")
                or (existing_offer["offer_no"] if existing_offer else "")
                or f"PRF-{now.year}-{now.strftime('%m%d%H%M%S')}"
            )
            offer_payload = {
                "offer_no": offer_no, "customer_id": customer_id, "customer_name": customer_name,
                "company_name": issuer_company,
                "contact_name": customer_name, "project_name": str(data.get("project_name") or ""),
                "template_type": str(data.get("template_type") or "modern"),
                "currency_code": currency, "currency_symbol": symbol, "exchange_rate": selected_rate,
                "subtotal": subtotal, "discount": 0, "vat_rate": vat_percent / 100.0,
                "vat_amount": vat_amount, "total": total, "subtotal_try": subtotal_try,
                "discount_try": 0, "vat_amount_try": vat_try, "total_try": total_try,
                "status": "Teklif", "source": "Web Sales Hub", "created_at": now.isoformat(timespec="seconds"),
            }
            offer_payload["payload_json"] = json.dumps({**offer_payload, "items": [{"productId": item["part_id"], "name": item["part"].get("name"), "qty": item["qty"], "price": item["unit_selected"], "price_try": item["unit_try"]} for item in lines]}, ensure_ascii=False)
            if existing_offer_id:
                offer_payload["updated_at"] = now.isoformat(timespec="seconds")
                update_available(
                    conn, "offers", existing_offer_id, offer_payload
                )
                conn.execute(
                    "DELETE FROM offer_items WHERE offer_id=?",
                    (existing_offer_id,),
                )
                offer_id = existing_offer_id
            else:
                offer_id = insert_available(conn, "offers", offer_payload)
            item_ids = []
            for item in lines:
                part = item["part"]
                item_ids.append(insert_available(conn, "offer_items", {
                    "offer_id": offer_id, "item_id": item["part_id"], "item_type": "stock",
                    "service": part.get("name") or part.get("part_name") or "",
                    "description": clean_offer_line_description(
                        part.get("description"),
                        service=part.get("name") or part.get("part_name") or "",
                        brand=part.get("brand") or "",
                        category=part.get("category") or "",
                    ),
                    "brand": part.get("brand") or "", "qty": item["qty"],
                    "unit_price": item["unit_selected"], "line_total": item["line_selected"],
                    "payload_json": json.dumps({"code": part.get("code"), "currency": currency, "unit_try": item["unit_try"], "source_currency": item["source_currency"]}, ensure_ascii=False),
                }))
            result.update({
                "offer_id": offer_id,
                "offer_no": offer_no,
                "item_ids": item_ids,
                "updated": bool(existing_offer_id),
            })
        elif mode == "payment":
            sale_no = str(data.get("reference") or f"SAT-{now.strftime('%Y%m%d%H%M%S')}")
            income_id = insert_available(conn, "accounting", {
                "type": "Gelir", "category": "Satış", "amount": total,
                "original_amount": total, "try_equivalent": total_try, "currency": currency,
                "exchange_rate": selected_rate, "description": f"{sale_no} Sales Hub peşin satış",
                "date": now.strftime("%Y-%m-%d"), "created_at": now.isoformat(timespec="seconds"),
                "customer_id": customer_id, "customer_name": customer_name,
                "payment_method": str(data.get("payment_method") or "Web"), "tracking_no": sale_no,
                "ref_no": sale_no, "is_deleted": 0,
            })
            cost_id = None
            if total_cost_try > 0:
                cost_id = insert_available(conn, "accounting", {
                    "type": "Gider", "category": "Satılan Malın Maliyeti", "amount": round(total_cost_try, 4),
                    "original_amount": round(total_cost_try, 4), "try_equivalent": round(total_cost_try, 4),
                    "currency": "TRY", "exchange_rate": 1,
                    "description": f"Satılan Malın Maliyeti - {sale_no} ({len(lines)} kalem)",
                    "date": now.strftime("%Y-%m-%d"), "created_at": now.isoformat(timespec="seconds"),
                    "customer_id": customer_id, "customer_name": customer_name,
                    "payment_method": "Mahsup", "tracking_no": sale_no, "ref_no": sale_no, "is_deleted": 0,
                })
            movement_ids = []
            for item in lines:
                new_stock = round(float(item["part"].get("stock") or 0) - item["qty"], 6)
                conn.execute("UPDATE parts SET stock=? WHERE id=?", (new_stock, item["part_id"]))
                movement_ids.append(insert_available(conn, "stock_movements", {
                    "part_id": item["part_id"], "movement_type": "Çıkış", "amount": item["qty"],
                    "new_stock": new_stock, "description": f"{sale_no} Sales Hub peşin satış",
                    "created_at": now.isoformat(timespec="seconds"), "is_deleted": 0,
                }))
            current_balance = _customer_balance(conn, customer_id, currency)
            # Desktop convention: a debit (sale/service) makes the customer
            # balance more negative; a credit (payment) brings it back toward
            # zero.  Keeping this sign is what lets the web payment dialog
            # calculate the actual open debt.
            debit_balance = round(current_balance - total, 4)
            debit_id = insert_available(conn, "currency_transactions", {
                "customer_id": customer_id, "transaction_type": "DEBIT", "amount": total,
                "currency": currency, "exchange_rate": selected_rate, "try_equivalent": total_try,
                "description": f"Peşin satış borç kaydı: {sale_no}", "tracking_no": sale_no,
                "created_at": now.isoformat(timespec="seconds"), "current_balance": debit_balance,
            })
            credit_id = insert_available(conn, "currency_transactions", {
                "customer_id": customer_id, "transaction_type": "CREDIT", "amount": total,
                "currency": currency, "exchange_rate": selected_rate, "try_equivalent": total_try,
                "description": f"Peşin satış tahsilatı: {sale_no}", "tracking_no": sale_no,
                "created_at": now.isoformat(timespec="seconds"), "current_balance": current_balance,
            })
            _set_customer_balance(conn, customer_id, currency, current_balance, now)
            result.update({"reference": sale_no, "income_id": income_id, "cost_id": cost_id, "movement_ids": movement_ids, "debit_id": debit_id, "credit_id": credit_id})
        else:
            service_no = str(data.get("reference") or f"SRV-{now.strftime('%Y%m%d%H%M%S')}")
            product_names = ", ".join(str(item["part"].get("name") or item["part"].get("part_name") or "") for item in lines)
            device_id = insert_available(conn, "devices", {
                "tracking_no": service_no, "customer_id": customer_id, "customer_name": customer_name,
                "device_type": str(data.get("device_type") or "Cihaz"), "device_model": product_names,
                "fault_description": f"Sales Hub kaydı — {data.get('offer_no') or service_no}",
                "repair_details": f"Sepet toplamı: {total:g} {currency} | TRY karşılığı: {total_try:g}",
                "status": "Bekliyor", "entry_date": now.strftime("%Y-%m-%d"),
                "estimated_date": data.get("estimated_date") or None,
                "service_source": "Web Sales Hub", "priority": "Normal", "payment_status": "Beklemede",
                "price": total, "created_at": now.isoformat(timespec="seconds"), "is_deleted": 0,
            })
            current_balance = _customer_balance(conn, customer_id, currency)
            debit_balance = round(current_balance - total, 4)
            debit_id = insert_available(conn, "currency_transactions", {
                "customer_id": customer_id, "transaction_type": "DEBIT", "amount": total,
                "currency": currency, "exchange_rate": selected_rate, "try_equivalent": total_try,
                "description": f"Servis borç kaydı: {service_no}", "tracking_no": service_no,
                "created_at": now.isoformat(timespec="seconds"), "current_balance": debit_balance,
            })
            _set_customer_balance(conn, customer_id, currency, debit_balance, now)
            result.update({"reference": service_no, "device_id": device_id, "device": product_names, "debit_id": debit_id})
        conn.commit()
    return result


def update_technician_job(data: dict) -> dict:
    """Apply technician form, used-part stock signal and optional collection atomically."""
    device_id = int(data.get("device_id") or 0)
    tracking_no = str(data.get("tracking_no") or "").strip()
    if not device_id and not tracking_no:
        raise ValueError("Servis kayd\u0131 belirtilmedi")
    now = datetime.now()
    with closing(db_connect()) as conn:
        conn.execute("BEGIN IMMEDIATE")
        device_row = conn.execute(
            "SELECT * FROM devices WHERE " + ("id=?" if device_id else "tracking_no=?") + " AND COALESCE(is_deleted,0)=0",
            (device_id if device_id else tracking_no,),
        ).fetchone()
        if not device_row:
            raise LookupError("Servis kayd\u0131 bulunamad\u0131")
        device = dict(device_row)
        device_id = int(device["id"])
        tracking_no = str(device.get("tracking_no") or tracking_no)
        columns = set(table_columns(conn, "devices"))
        candidate = {
            "status": data.get("status") or device.get("status") or "Bekliyor",
            "technician": str(data.get("technician") or ""),
            "internal_notes": str(data.get("internal_notes") or ""),
            "repair_details": str(data.get("repair_details") or ""),
            "labor_cost": max(0.0, float(data.get("labor_cost") or 0)),
            "cargo_fee": max(0.0, float(data.get("cargo_fee") or 0)),
            "delivery_type": str(data.get("delivery_type") or ""),
            "payment_status": str(device.get("payment_status") or "Beklemede"),
            "warranty_status": str(data.get("warranty_status") or device.get("warranty_status") or "Yok"),
            "warranty_end_date": data.get("warranty_end_date") or None,
            "estimated_date": data.get("estimated_date") or device.get("estimated_date"),
            "priority": str(data.get("priority") or device.get("priority") or "Normal"),
            "updated_at": now.isoformat(timespec="seconds"),
        }
        if str(candidate["status"]).casefold() in {
            "tamamland\u0131",
            "teslim edildi",
        } and "exit_date" in columns:
            candidate["exit_date"] = now.strftime("%Y-%m-%d")
        clean = {key: value for key, value in candidate.items() if key in columns}
        conn.execute(f'UPDATE devices SET {",".join(f"\"{key}\"=?" for key in clean)} WHERE id=?', (*clean.values(), device_id))
        automotive_form_id = None
        automotive_form = data.get("automotive_form")
        if isinstance(automotive_form, dict):
            form_values = {
                "device_id": device_id,
                "tracking_no": tracking_no,
                "customer_id": int(device.get("customer_id") or 0) or None,
                "vehicle_id": int(automotive_form.get("vehicle_id") or 0) or None,
                "vehicle_plate": str(automotive_form.get("vehicle_plate") or device.get("vehicle_plate") or device.get("serial_no") or "").strip(),
                "vehicle_vin": str(automotive_form.get("vehicle_vin") or device.get("vehicle_vin") or "").strip(),
                "engine_code": str(automotive_form.get("engine_code") or "").strip(),
                "entry_odometer": max(0, int(float(automotive_form.get("entry_odometer") or 0))),
                "exit_odometer": max(0, int(float(automotive_form.get("exit_odometer") or 0))),
                "fuel_level_entry": str(automotive_form.get("fuel_level_entry") or "").strip(),
                "fuel_level_exit": str(automotive_form.get("fuel_level_exit") or "").strip(),
                "acceptance_notes": str(automotive_form.get("acceptance_notes") or "").strip(),
                "checklist_json": json.dumps(automotive_form.get("checklist") or {}, ensure_ascii=False),
                "damage_marks_json": json.dumps(automotive_form.get("damage_marks") or [], ensure_ascii=False),
                "customer_approval": 1 if automotive_form.get("customer_approval") else 0,
                "kvkk_approval": 1 if automotive_form.get("kvkk_approval") else 0,
                "customer_approval_text": str(automotive_form.get("customer_approval_text") or "").strip(),
                "kvkk_text": str(automotive_form.get("kvkk_text") or "").strip(),
                "updated_at": now.isoformat(timespec="seconds"),
            }
            automotive_form_id = int(scalar(
                conn,
                "SELECT id FROM automotive_service_forms WHERE device_id=? ORDER BY id DESC LIMIT 1",
                (device_id,),
                default=0,
            ) or 0)
            if automotive_form_id:
                update_available(conn, "automotive_service_forms", automotive_form_id, form_values)
            else:
                form_values["created_at"] = now.isoformat(timespec="seconds")
                automotive_form_id = insert_available(conn, "automotive_service_forms", form_values)

            odometer = max(form_values["entry_odometer"], form_values["exit_odometer"])
            plate = form_values["vehicle_plate"]
            if plate:
                vehicle_row = conn.execute(
                    "SELECT id FROM customer_vehicles WHERE UPPER(REPLACE(plate,' ',''))=? ORDER BY id DESC LIMIT 1",
                    (plate.replace(" ", "").upper(),),
                ).fetchone()
                if vehicle_row:
                    update_available(conn, "customer_vehicles", int(vehicle_row[0]), {
                        "last_known_odometer": odometer,
                        "updated_at": now.isoformat(timespec="seconds"),
                    })
        movement_ids: list[int] = []
        used_part_ids: list[int] = []
        requested_parts: dict[int, float] = {}
        raw_used_parts = data.get("used_parts")
        if isinstance(raw_used_parts, str):
            try:
                raw_used_parts = json.loads(raw_used_parts)
            except (TypeError, ValueError, json.JSONDecodeError) as error:
                raise ValueError("Kullan\u0131lan par\u00e7a listesi ge\u00e7ersiz") from error
        if isinstance(raw_used_parts, list):
            for entry in raw_used_parts:
                if not isinstance(entry, dict):
                    continue
                try:
                    part_id = int(float(entry.get("part_id") or entry.get("id") or 0))
                    quantity = max(0.0, float(entry.get("quantity") or entry.get("part_quantity") or 0))
                except (TypeError, ValueError) as error:
                    raise ValueError("Kullan\u0131lan par\u00e7a bilgisi ge\u00e7ersiz") from error
                if part_id and quantity:
                    requested_parts[part_id] = requested_parts.get(part_id, 0.0) + quantity
        if not requested_parts:
            try:
                part_id = int(float(data.get("part_id") or 0))
                quantity = max(0.0, float(data.get("part_quantity") or 0))
            except (TypeError, ValueError) as error:
                raise ValueError("Kullan\u0131lan par\u00e7a bilgisi ge\u00e7ersiz") from error
            if part_id and quantity:
                requested_parts[part_id] = quantity

        prepared_parts: list[tuple[int, dict, float, float]] = []
        for part_id, quantity in requested_parts.items():
            part_row = conn.execute(
                "SELECT * FROM parts WHERE id=? AND COALESCE(is_deleted,0)=0", (part_id,)
            ).fetchone()
            if not part_row:
                raise LookupError("Kullan\u0131lacak stok kart\u0131 bulunamad\u0131")
            part = dict(part_row)
            old_stock = float(part.get("stock") or 0)
            if quantity > old_stock + 0.000001:
                raise ValueError(
                    f"{part.get('name') or part.get('part_name')} i\u00e7in yeterli stok yok"
                )
            prepared_parts.append((part_id, part, quantity, old_stock))

        for part_id, part, quantity, old_stock in prepared_parts:
            new_stock = round(old_stock - quantity, 6)
            part_currency = str(part.get("currency") or "TRY").upper()
            part_rate = resolve_exchange_rate(conn, part_currency)
            part_price = parse_money_amount(part.get("price"))
            conn.execute("UPDATE parts SET stock=? WHERE id=?", (new_stock, part_id))
            movement_ids.append(insert_available(conn, "stock_movements", {
                "part_id": part_id,
                "movement_type": "\u00c7\u0131k\u0131\u015f",
                "amount": quantity,
                "new_stock": new_stock,
                "description": f"{tracking_no} teknisyen kullan\u0131m\u0131",
                "created_at": now.isoformat(timespec="seconds"), "is_deleted": 0,
            }))
            used_part_ids.append(insert_available(conn, "used_parts", {
                "tracking_no": tracking_no, "part_id": part_id,
                "part_name": part.get("name") or part.get("part_name") or "",
                "price": part_price, "quantity": quantity,
                "purchase_price_snapshot": parse_money_amount(part.get("purchase_price")),
                "currency": part_currency, "exchange_rate": part_rate,
                "price_try": round(part_price * part_rate, 4),
                "created_at": now.isoformat(timespec="seconds"), "is_deleted": 0,
            }))
        movement_id = movement_ids[0] if movement_ids else None
        used_part_id = used_part_ids[0] if used_part_ids else None
        # Keep one service debit synchronized with labour, cargo and all used
        # parts. Later edits apply only the difference to the customer balance.
        service_customer_id = int(device.get("customer_id") or 0)
        service_charge = round(
            float(candidate.get("labor_cost") or 0)
            + float(candidate.get("cargo_fee") or 0)
            + _service_used_parts_total_try(conn, tracking_no),
            4,
        )
        service_debit_id = None
        if service_customer_id:
            service_debit_id = _sync_service_debit(
                conn, service_customer_id, tracking_no, service_charge, now
            )
        finance_id = currency_transaction_id = None
        payment = max(0.0, float(data.get("payment_amount") or 0)) if data.get("collect_payment") else 0.0
        payment_currency = str(data.get("payment_currency") or "TRY").upper()
        if payment:
            if not int(device.get("customer_id") or 0):
                raise ValueError(
                    "Tahsilat i\u00e7in servis m\u00fc\u015fterisi bulunamad\u0131"
                )
            rate = resolve_exchange_rate(conn, payment_currency, data.get("exchange_rate"))
            customer_id = int(device.get("customer_id") or 0)
            customer_name = str(device.get("customer_name") or "")
            finance_id = insert_available(conn, "accounting", {
                "type": "Gelir", "category": "Tahsilat", "amount": payment,
                "original_amount": payment, "try_equivalent": round(payment * rate, 4),
                "currency": payment_currency, "exchange_rate": rate,
                "description": f"Servis Tahsilat\u0131: {tracking_no}",
                "date": now.strftime("%Y-%m-%d"), "created_at": now.isoformat(timespec="seconds"),
                "customer_id": customer_id or None, "customer_name": customer_name,
                "payment_method": str(data.get("payment_method") or "Nakit"),
                "tracking_no": tracking_no, "ref_no": tracking_no, "is_deleted": 0,
            })
            if customer_id:
                current = _customer_balance(conn, customer_id, payment_currency)
                open_debt = max(0.0, -current)
                if open_debt <= 0:
                    raise ValueError("Bu para biriminde a\u00e7\u0131k bor\u00e7 bulunmuyor")
                if payment > open_debt + 0.0001:
                    raise ValueError(
                        "Tahsilat a\u00e7\u0131k borcu a\u015famaz "
                        f"(en fazla {open_debt:g} {payment_currency})"
                    )
                updated = round(current + payment, 4)
                currency_transaction_id = insert_available(conn, "currency_transactions", {
                    "customer_id": customer_id, "transaction_type": "CREDIT", "amount": payment,
                    "currency": payment_currency, "exchange_rate": rate,
                    "try_equivalent": round(payment * rate, 4),
                    "description": f"Servis tahsilat\u0131: {tracking_no}",
                    "tracking_no": tracking_no,
                    "created_at": now.isoformat(timespec="seconds"), "current_balance": updated,
                })
                _set_customer_balance(conn, customer_id, payment_currency, updated, now)
        payment_status = _refresh_service_payment_status(conn, tracking_no)
        conn.commit()
    return {"ok": True, "device_id": device_id, "tracking_no": tracking_no, "movement_id": movement_id, "used_part_id": used_part_id, "movement_ids": movement_ids, "used_part_ids": used_part_ids, "finance_id": finance_id, "currency_transaction_id": currency_transaction_id, "automotive_form_id": automotive_form_id, "service_debit_id": service_debit_id, "service_charge_try": service_charge, "payment_status": payment_status}


def record_customer_payment(data: dict) -> dict:
    """Record a customer credit only up to the current open debt.

    The balance sign follows the desktop application: negative means the
    customer owes the company, and a CREDIT increases the balance toward zero.
    """
    try:
        customer_id = int(data.get("customer_id") or 0)
    except (TypeError, ValueError):
        customer_id = 0
    customer_name_hint = str(data.get("customer_name") or "").strip()
    currency = str(data.get("currency") or "TRY").upper()
    if currency not in {"TRY", "USD", "EUR"}:
        raise ValueError("Para birimi TRY, USD veya EUR olmal\u0131d\u0131r")
    try:
        amount = round(float(data.get("amount") or 0), 4)
    except (TypeError, ValueError):
        amount = 0.0
    if amount <= 0:
        raise ValueError(
            "Tahsilat tutar\u0131 s\u0131f\u0131rdan b\u00fcy\u00fck olmal\u0131d\u0131r"
        )
    now = datetime.now()
    with closing(db_connect()) as conn:
        conn.execute("BEGIN IMMEDIATE")
        if not customer_id and customer_name_hint:
            match = conn.execute(
                "SELECT id FROM customers WHERE lower(trim(name))=lower(trim(?)) AND COALESCE(is_deleted,0)=0 ORDER BY id DESC LIMIT 1",
                (customer_name_hint,),
            ).fetchone()
            if match:
                customer_id = int(match["id"])
        if not customer_id:
            raise ValueError("M\u00fc\u015fteri se\u00e7ilmelidir")
        customer_row = conn.execute(
            "SELECT * FROM customers WHERE id=? AND COALESCE(is_deleted,0)=0", (customer_id,)
        ).fetchone()
        if not customer_row:
            raise LookupError("M\u00fc\u015fteri kayd\u0131 bulunamad\u0131")
        customer = dict(customer_row)
        current = _customer_balance(conn, customer_id, currency)
        open_debt = max(0.0, -current)
        if open_debt <= 0:
            raise ValueError("Bu para biriminde a\u00e7\u0131k bor\u00e7 bulunmuyor")
        if amount > open_debt + 0.0001:
            raise ValueError(
                "Tahsilat a\u00e7\u0131k borcu a\u015famaz "
                f"(en fazla {open_debt:g} {currency})"
            )
        rate = resolve_exchange_rate(conn, currency, data.get("exchange_rate"))
        updated = round(current + amount, 4)
        reference = str(data.get("reference") or data.get("tracking_no") or "").strip()
        description = str(
            data.get("description") or "M\u00fc\u015fteri tahsilat\u0131"
        ).strip()
        method = str(data.get("payment_method") or "Web").strip()
        customer_name = customer.get("name") or customer.get("customer_name") or customer_name_hint
        finance_id = insert_available(conn, "accounting", {
            "type": "Gelir", "category": "Tahsilat", "amount": amount,
            "original_amount": amount, "try_equivalent": round(amount * rate, 4),
            "currency": currency, "exchange_rate": rate, "description": description,
            "date": now.strftime("%Y-%m-%d"), "created_at": now.isoformat(timespec="seconds"),
            "customer_id": customer_id, "customer_name": customer_name,
            "payment_method": method, "tracking_no": reference, "ref_no": reference, "is_deleted": 0,
        })
        transaction_id = insert_available(conn, "currency_transactions", {
            "customer_id": customer_id, "transaction_type": "CREDIT", "amount": amount,
            "currency": currency, "exchange_rate": rate, "try_equivalent": round(amount * rate, 4),
            "description": description, "tracking_no": reference,
            "created_at": now.isoformat(timespec="seconds"), "current_balance": updated,
        })
        _set_customer_balance(conn, customer_id, currency, updated, now)
        payment_status = (
            _refresh_service_payment_status(conn, reference) if reference else None
        )
        conn.commit()
    return {
        "ok": True, "finance_id": finance_id, "currency_transaction_id": transaction_id,
        "customer_id": customer_id, "customer_name": customer_name, "currency": currency,
        "amount": amount, "open_debt_before": open_debt, "open_debt_after": max(0.0, -updated),
        "exchange_rate": rate, "try_equivalent": round(amount * rate, 4),
        "payment_method": method, "reference": reference,
        "payment_status": payment_status,
    }


def resolve_logo_path(value) -> Path | None:
    """Resolve project-relative logos and migrated Windows paths on every server OS."""
    raw = str(value or "").strip()
    if not raw:
        return None
    candidate = Path(raw).expanduser()
    if candidate.is_file():
        return candidate.resolve()
    if not candidate.is_absolute():
        project_candidate = (ROOT / candidate).resolve()
        if project_candidate.is_file():
            return project_candidate
    filename = PureWindowsPath(raw).name
    migrated = (WEB_ROOT / "uploads" / filename).resolve()
    return migrated if filename and migrated.is_file() else None


class _PDFSettingsAdapter:
    def __init__(self, values: dict[str, str]):
        self.values = values

    def get_setting(self, key, default=""):
        value = self.values.get(key)
        if key == "logo_path":
            logo = resolve_logo_path(value)
            return str(logo) if logo else default
        return default if value in (None, "") else value


class _ServiceWorkDbAdapter:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.cursor = conn.cursor()


def build_offer_pdf(offer_id: int, requested_template: str | None = None) -> tuple[Path, str]:
    """Generate a proforma with the desktop application's own three PDF templates."""
    allowed_templates = {"modern", "corporate", "minimal"}
    ensure_packaged_source()
    from src.utils.service_work_details import (
        clean_offer_line_description,
        format_numbered_work_lines,
        load_service_work_lines,
    )
    with closing(db_connect()) as conn:
        offer_row = conn.execute("SELECT * FROM offers WHERE id=?", (offer_id,)).fetchone()
        if not offer_row:
            raise ValueError("Teklif kaydı bulunamadı")
        offer = dict(offer_row)
        item_rows = rows(conn, "SELECT * FROM offer_items WHERE offer_id=? ORDER BY id", (offer_id,))
        settings = {row["key"]: row["value"] for row in rows(conn, "SELECT key,value FROM settings")}
        company_row = conn.execute("SELECT * FROM company_info ORDER BY id DESC LIMIT 1").fetchone()
        company_info = dict(company_row) if company_row else {}
        customer_company = ""
        if offer.get("customer_id"):
            customer_row = conn.execute(
                "SELECT COALESCE(company_name, '') AS company_name FROM customers WHERE id=?",
                (offer.get("customer_id"),),
            ).fetchone()
            customer_company = str(customer_row["company_name"] if customer_row else "").strip()
    # Older offers stored the selected customer's name in company_name. Fill
    # missing settings from company_info and prefer the current issuer when a
    # previously saved proforma is opened again.
    for setting_key, info_key in {
        "company_name": "company_name",
        "company_phone": "phone",
        "company_email": "email",
        "company_address": "address",
        "logo_path": "logo_path",
    }.items():
        if not str(settings.get(setting_key) or "").strip() and str(company_info.get(info_key) or "").strip():
            settings[setting_key] = company_info[info_key]
    issuer_company = str(
        settings.get("company_name")
        or offer.get("company_name")
        or offer.get("customer_name")
        or "AYEC Pro"
    ).strip()

    template = requested_template if requested_template in allowed_templates else offer.get("template_type")
    if template not in allowed_templates:
        template = "modern"
    vat_rate = float(offer.get("vat_rate") or 0)
    if vat_rate > 1:
        vat_rate /= 100
    totals = (
        float(offer.get("subtotal") or 0),
        float(offer.get("discount") or 0),
        vat_rate,
        float(offer.get("vat_amount") or 0),
        float(offer.get("total") or 0),
    )
    cart_items = []
    for item in item_rows:
        try:
            payload = json.loads(item.get("payload_json") or "{}")
        except (TypeError, ValueError):
            payload = {}
        cart_items.append({
            "service": item.get("service") or payload.get("name") or "Ürün / Hizmet",
            "name": item.get("service") or payload.get("name") or "Ürün / Hizmet",
            "description": clean_offer_line_description(
                item.get("description") or payload.get("description"),
                service=item.get("service") or payload.get("name") or "",
                brand=item.get("brand") or payload.get("brand") or "",
                model=payload.get("model") or "",
                category=payload.get("category") or "",
            ),
            "brand": item.get("brand") or payload.get("brand") or "",
            "model": payload.get("model") or "",
            "code": payload.get("code") or "",
            "qty": float(item.get("qty") or payload.get("qty") or 1),
            "price": float(item.get("unit_price") or payload.get("price") or 0),
        })

    with closing(db_connect()) as service_conn:
        service_db = _ServiceWorkDbAdapter(service_conn)
        for cart_item, item in zip(cart_items, item_rows):
            service_name = str(cart_item.get("service") or "")
            if not normalize_identifier(service_name).startswith("servis "):
                continue
            try:
                payload = json.loads(item.get("payload_json") or "{}")
            except (TypeError, ValueError):
                payload = {}
            tracking_no = str(payload.get("tracking_no") or offer.get("project_name") or "").strip()
            device_row = service_conn.execute(
                "SELECT tracking_no, repair_details, fault_description FROM devices "
                "WHERE tracking_no=? ORDER BY id DESC LIMIT 1",
                (tracking_no,),
            ).fetchone() if tracking_no else None
            if not device_row:
                continue
            work_lines = load_service_work_lines(
                service_db,
                device_row["tracking_no"],
                repair_details=device_row["repair_details"],
                fault_description=device_row["fault_description"],
            )
            cart_item["description"] = (
                format_numbered_work_lines(work_lines) or cart_item["description"]
            )
    if not cart_items:
        try:
            payload = json.loads(offer.get("payload_json") or "{}")
            cart_items = payload.get("items") or []
        except (TypeError, ValueError):
            cart_items = []

    ensure_packaged_source()
    from src.utils.pdf_manager import PDFManagerQt

    handle = tempfile.NamedTemporaryFile(prefix=f"{offer.get('offer_no') or 'proforma'}-", suffix=".pdf", delete=False)
    target = Path(handle.name)
    handle.close()
    manager = PDFManagerQt(_PDFSettingsAdapter(settings))
    manager._open_file = lambda _filename: None
    currency = offer.get("currency_symbol") or {"TRY": "₺", "USD": "$", "EUR": "€"}.get(offer.get("currency_code"), "₺")
    success, result = manager.create_proforma(
        template_type=template,
        cart_items=cart_items,
        totals=totals,
        company_name=issuer_company,
        customer_name=offer.get("customer_name") or "Sayın İlgili",
        project_name=offer.get("project_name") or "",
        contact_name=offer.get("contact_name") or offer.get("customer_name") or "",
        reference_no=offer.get("offer_no") or f"PRF-{offer_id}",
        offer_date=offer.get("created_at"),
        customer_company=customer_company,
        currency_code=offer.get("currency_code") or "TRY",
        save_path=str(target),
        currency=currency,
    )
    if not success or not target.exists():
        target.unlink(missing_ok=True)
        raise RuntimeError(str(result))
    return target, str(offer.get("offer_no") or f"PRF-{offer_id}")


def delete_stock_with_reversal(part_id: int) -> dict:
    """Mirror the desktop stock context-menu deletion and finance reversal atomically."""
    now = datetime.now()
    exchange_rates(refresh=True)
    with closing(db_connect()) as conn:
        part_row = conn.execute(
            "SELECT id,name,stock,purchase_price,currency FROM parts WHERE id=? AND COALESCE(is_deleted,0)=0",
            (part_id,),
        ).fetchone()
        if not part_row:
            raise LookupError("Stok kartı bulunamadı veya daha önce silinmiş")
        part = dict(part_row)
        stock = float(part.get("stock") or 0)
        purchase_price = float(part.get("purchase_price") or 0)
        currency = str(part.get("currency") or "TRY").upper()
        movement_id = insert_available(conn, "stock_movements", {
            "part_id": part_id,
            "movement_type": "Çıkış (Silindi)",
            "amount": -stock,
            "new_stock": 0,
            "description": f"Kart Silindi: {part.get('name') or ''}",
            "created_at": now.isoformat(timespec="seconds"),
            "is_deleted": 0,
        })
        finance_id = None
        refund = stock * purchase_price
        rate = resolve_exchange_rate(conn, currency) if refund else 1.0
        if refund > 0:
            finance_id = insert_available(conn, "accounting", {
                "type": "Gelir",
                "category": "Stok İptali / Silinme",
                "amount": refund,
                "try_equivalent": round(refund * rate, 4),
                "currency": currency,
                "exchange_rate": rate,
                "original_amount": refund,
                "description": f"Stok Kartı Silinme İadesi: {stock:g} x {part.get('name') or ''}",
                "date": now.strftime("%Y-%m-%d"),
                "created_at": now.isoformat(timespec="seconds"),
                "payment_method": "Mahsup",
                "ref_no": f"WEB-STOCK-DELETE-{part_id}",
                "product_service_id": part_id,
                "product_service_type": "stock",
                "is_deleted": 0,
            })
        columns = set(table_columns(conn, "parts"))
        if "deleted_at" in columns:
            conn.execute("UPDATE parts SET is_deleted=1,deleted_at=? WHERE id=?", (now.isoformat(timespec="seconds"), part_id))
        else:
            conn.execute("UPDATE parts SET is_deleted=1 WHERE id=?", (part_id,))
        conn.commit()
    conn.close()
    return {
        "ok": True,
        "id": part_id,
        "movement_id": movement_id,
        "finance_id": finance_id,
        "refund": refund,
        "currency": currency,
        "stock": stock,
        "purchase_price": purchase_price,
        "exchange_rate": rate,
        "try_equivalent": round(refund * rate, 4),
    }


def desktop_bootstrap() -> dict:
    with closing(db_connect()) as conn:
        stock_part_ids = [
            int(row[0])
            for row in conn.execute(
                "SELECT id FROM parts WHERE COALESCE(is_deleted,0)=0"
            ).fetchall()
        ]
    if stock_part_ids:
        reconcile_stock_finance(stock_part_ids)
    with closing(db_connect()) as conn:
        repair_explicit_stock_accounting_currency(conn)
        _reconcile_service_debits(conn)
        accounting_columns = set(table_columns(conn, "accounting"))
        if {"amount", "original_amount", "try_equivalent", "currency", "exchange_rate"}.issubset(accounting_columns):
            conn.execute(
                """
                UPDATE accounting
                   SET amount = ROUND(original_amount * exchange_rate, 4),
                       try_equivalent = ROUND(original_amount * exchange_rate, 4)
                 WHERE UPPER(COALESCE(currency, 'TRY')) IN ('USD', 'EUR')
                   AND COALESCE(original_amount, 0) > 0
                   AND COALESCE(exchange_rate, 0) > 1
                   AND ABS(COALESCE(try_equivalent, 0) - (original_amount * exchange_rate)) > 0.01
                """
            )
            conn.commit()
        customers = rows(conn, "SELECT * FROM customers WHERE COALESCE(is_deleted,0)=0 ORDER BY id DESC")
        balances = rows(conn, "SELECT customer_id,currency,balance FROM customer_currency_balances")
        balance_map: dict[int, dict[str, float]] = {}
        for item in balances:
            balance_map.setdefault(item["customer_id"], {"TRY": 0, "USD": 0, "EUR": 0})[item["currency"]] = item["balance"] or 0
        for customer in customers:
            customer["balances"] = balance_map.get(customer["id"], {"TRY": 0, "USD": 0, "EUR": 0})
            customer["services"] = []
            customer["quotes"] = []
        by_id = {customer["id"]: customer for customer in customers}
        devices = rows(conn, "SELECT * FROM devices WHERE COALESCE(is_deleted,0)=0 ORDER BY id DESC")
        customer_vehicles = rows(
            conn,
            "SELECT * FROM customer_vehicles WHERE COALESCE(is_active,1)=1 ORDER BY id DESC",
        )
        vehicles_by_customer_plate: dict[tuple[int, str], dict] = {}
        for vehicle in customer_vehicles:
            vehicle_key = (
                int(vehicle.get("customer_id") or 0),
                re.sub(r"\s+", "", str(vehicle.get("plate") or "")).upper(),
            )
            vehicles_by_customer_plate.setdefault(vehicle_key, vehicle)
        used_part_rows = rows(conn, "SELECT * FROM used_parts WHERE COALESCE(is_deleted,0)=0 ORDER BY id DESC")
        parts_by_tracking: dict[str, list[dict]] = {}
        for used_part in used_part_rows:
            parts_by_tracking.setdefault(str(used_part.get("tracking_no") or ""), []).append(used_part)
        for device in devices:
            customer = by_id.get(device.get("customer_id"))
            if customer:
                tracking_no = str(device.get("tracking_no") or "")
                service_parts = parts_by_tracking.get(tracking_no, [])
                parts_total_try = _service_used_parts_total_try(conn, tracking_no)
                service_total_try = round(
                    float(device.get("labor_cost") or 0)
                    + float(device.get("cargo_fee") or 0)
                    + parts_total_try,
                    4,
                )
                vehicle_plate = str(device.get("vehicle_plate") or device.get("serial_no") or "").strip()
                vehicle = vehicles_by_customer_plate.get((
                    int(device.get("customer_id") or 0),
                    re.sub(r"\s+", "", vehicle_plate).upper(),
                ), {})
                customer["services"].append({
                    "id": device.get("id"),
                    "date": device.get("entry_date") or device.get("created_at") or "",
                    "no": device.get("tracking_no") or f'SRV-{device.get("id")}',
                    "device": " ".join(filter(None, [device.get("device_brand"), device.get("device_model")])) or device.get("device_type") or "Cihaz",
                    "device_type": device.get("device_type") or "Cihaz",
                    "brand": device.get("device_brand") or "",
                    "model": device.get("device_model") or "",
                    "serial": device.get("serial_no") or "",
                    "plate": vehicle_plate,
                    "vehicle_plate": vehicle_plate,
                    "vehicle_vin": device.get("vehicle_vin") or "",
                    "vehicle_id": vehicle.get("id"),
                    "odometer": vehicle.get("last_known_odometer") or 0,
                    "status": device.get("status") or "Bekliyor",
                    "approval_status": device.get("approval_status") or "",
                    "note": device.get("fault_description") or "",
                    "internal_notes": device.get("internal_notes") or "",
                    "repair_details": device.get("repair_details") or "",
                    "technician": device.get("technician") or "",
                    "labor_cost": device.get("labor_cost") or 0,
                    "cargo_fee": device.get("cargo_fee") or 0,
                    "delivery_type": device.get("delivery_type") or "",
                    "warranty_status": device.get("warranty_status") or "Yok",
                    "warranty_end_date": device.get("warranty_end_date") or "",
                    "accessories": device.get("accessories") or "",
                    "amount": service_total_try,
                    "currency": "TRY",
                    "delivery": device.get("estimated_date") or device.get("exit_date") or device.get("delivered_at") or "",
                    "service": device.get("service_source") or "Servis",
                    "priority": device.get("priority") or device.get("urgency") or "Normal",
                    "payment_status": device.get("payment_status") or "Beklemede",
                    "used_parts": service_parts,
                })
        offers = rows(conn, "SELECT * FROM offers ORDER BY id DESC")
        offer_items = rows(conn, "SELECT * FROM offer_items ORDER BY id")
        items_by_offer: dict[int, list[dict]] = {}
        for item in offer_items:
            try:
                payload = json.loads(item.get("payload_json") or "{}")
            except (TypeError, ValueError):
                payload = {}
            normalized = dict(item)
            normalized.update({key: value for key, value in payload.items() if key not in normalized or normalized.get(key) in (None, "")})
            normalized["name"] = normalized.get("service") or normalized.get("description") or "Ürün / Hizmet"
            normalized["price"] = normalized.get("unit_price") or 0
            items_by_offer.setdefault(item.get("offer_id"), []).append(normalized)
        for offer in offers:
            offer["items"] = items_by_offer.get(offer.get("id"), [])
            offer["no"] = offer.get("offer_no")
            offer["customerId"] = offer.get("customer_id")
            offer["date"] = offer.get("created_at") or ""
            customer = by_id.get(offer.get("customer_id"))
            if customer:
                customer_offer = dict(offer)
                customer_offer["total"] = offer.get("total_try") or offer.get("total") or 0
                customer_offer["status"] = offer.get("status") or "Teklif"
                customer["quotes"].append(customer_offer)
        stock = rows(conn, "SELECT * FROM parts WHERE COALESCE(is_deleted,0)=0 ORDER BY id DESC")
        for part in stock:
            part["currency"] = str(part.get("currency") or part.get("unit") or "TRY").upper()
        stock_locations: list[dict] = []
        stock_location_summary = {
            "warehouses": 0,
            "vehicles": 0,
            "vehicle_quantity": 0,
            "locations": 0,
        }
        if scalar(
            conn,
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='stock_locations'",
            default=0,
        ) and scalar(
            conn,
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='stock_location_balances'",
            default=0,
        ):
            stock_locations = rows(
                conn,
                """
                SELECT l.id,l.name,l.location_type,l.vehicle_plate,l.personnel_id,l.active,
                       COALESCE(SUM(b.quantity),0) AS quantity,
                       COUNT(DISTINCT CASE WHEN ABS(COALESCE(b.quantity,0)) > 0.000001
                                           THEN b.part_id END) AS part_count
                FROM stock_locations l
                LEFT JOIN stock_location_balances b ON b.location_id=l.id
                WHERE COALESCE(l.active,1)=1
                GROUP BY l.id,l.name,l.location_type,l.vehicle_plate,l.personnel_id,l.active
                ORDER BY CASE l.location_type WHEN 'main' THEN 0 WHEN 'vehicle' THEN 1 ELSE 2 END,l.name
                """,
            )
            stock_location_summary = {
                "warehouses": sum(
                    1 for item in stock_locations
                    if item.get("location_type") in {"main", "warehouse"}
                ),
                "vehicles": sum(
                    1 for item in stock_locations
                    if item.get("location_type") == "vehicle"
                ),
                "vehicle_quantity": int(round(sum(
                    float(item.get("quantity") or 0)
                    for item in stock_locations
                    if item.get("location_type") == "vehicle"
                ))),
                "locations": len(stock_locations),
            }
        movements = rows(conn, "SELECT sm.*,p.name product FROM stock_movements sm LEFT JOIN parts p ON p.id=sm.part_id WHERE COALESCE(sm.is_deleted,0)=0 ORDER BY sm.id DESC LIMIT 500")
        finance = rows(conn, "SELECT * FROM accounting WHERE COALESCE(is_deleted,0)=0 ORDER BY date DESC,id DESC LIMIT 1000")
        appointments = rows(conn, "SELECT * FROM appointments ORDER BY date DESC,time DESC LIMIT 1000")
        plan_by_appointment: dict[int, list[dict]] = {}
        if scalar(
            conn,
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='appointment_plan_items'",
            default=0,
        ):
            plan_rows = rows(
                conn,
                "SELECT * FROM appointment_plan_items ORDER BY appointment_id,id",
            )
            for plan_row in plan_rows:
                plan_by_appointment.setdefault(int(plan_row.get("appointment_id") or 0), []).append(plan_row)
        for appointment in appointments:
            appointment["plan_items"] = plan_by_appointment.get(int(appointment.get("id") or 0), [])
            customer = by_id.get(appointment.get("customer_id"))
            if customer:
                appointment["customer_name"] = (
                    customer.get("name")
                    or customer.get("company")
                    or customer.get("title")
                    or ""
                )
        scheduled_alerts = rows(conn, "SELECT * FROM scheduled_alerts WHERE COALESCE(is_enabled,1)=1 ORDER BY trigger_time")
        personnel = rows(conn, "SELECT id,name,role,department,active FROM personnel WHERE COALESCE(active,1)=1 ORDER BY name")
        raw_settings = {row["key"]: row["value"] for row in rows(conn, "SELECT key,value FROM settings")}
        sensitive = re.compile(r"(password|pass$|token|api_key|secret|security_answer_hash)", re.I)
        settings = {key: ("" if sensitive.search(key) else value) for key, value in raw_settings.items()}
        settings_configured = [key for key, value in raw_settings.items() if value and sensitive.search(key)]
        internal_settings = {row["key"]: row["value"] for row in rows(conn, "SELECT key,value FROM internal_settings")}
        current_sector = internal_settings.get("current_sector") or raw_settings.get("current_sector") or "teknik_servis"
        if current_sector not in {"teknik_servis", "otomotiv"}:
            current_sector = "teknik_servis"
        return {
            "database": str(active_db_path()), "tenant_id": active_tenant_id(), "company_name": active_company_name(), "customers": customers, "stock": stock, "stock_locations": stock_locations, "stock_location_summary": stock_location_summary, "devices": devices,
            "customer_vehicles": customer_vehicles,
            "movements": movements, "finance": finance, "appointments": appointments,
            "offers": offers, "scheduled_alerts": scheduled_alerts, "personnel": personnel,
            "used_parts": used_part_rows, "exchange_rates": exchange_rates(refresh=False), "settings": settings,
            "settings_configured": settings_configured,
            "internal_settings": internal_settings, "current_sector": current_sector, "counts": {
                "customers": len(customers), "services": len(devices), "stock": len(stock),
                "appointments": len(appointments), "offers": len(offers),
            },
        }


def update_mobile_personnel_presence(user: dict, payload: dict) -> dict:
    """Persist a field user's current state on the shared desktop record."""
    if not user:
        raise PermissionError("Authentication is required")
    with closing(db_connect()) as conn:
        personnel_columns = set(table_columns(conn, "personnel"))
        if not personnel_columns:
            raise LookupError("Personnel table is unavailable")
        for column, ddl in (
            ("lat", "REAL"),
            ("lng", "REAL"),
            ("status", "TEXT"),
            ("last_seen", "TEXT"),
        ):
            if column not in personnel_columns:
                conn.execute(f'ALTER TABLE "personnel" ADD COLUMN "{column}" {ddl}')
                personnel_columns.add(column)
        personnel_id = int(user.get("personnel_id") or 0)
        if personnel_id and not scalar(conn, "SELECT COUNT(*) FROM personnel WHERE id=?", (personnel_id,), default=0):
            personnel_id = 0
        username = str(user.get("username") or "").strip()
        if not personnel_id and username and "username" in personnel_columns:
            personnel_id = int(scalar(
                conn,
                "SELECT id FROM personnel WHERE username=?",
                (username,),
                default=0,
            ) or 0)
        if not personnel_id:
            values = {
                "name": str(user.get("full_name") or username or "Field User"),
                "username": username,
                "role": str(user.get("role") or "Personnel"),
                "active": 1,
            }
            insert_values = {key: value for key, value in values.items() if key in personnel_columns}
            keys = list(insert_values)
            cursor = conn.execute(
                "INSERT INTO personnel (" + ",".join(f'\"{key}\"' for key in keys) + ") VALUES (" + ",".join("?" for _ in keys) + ")",
                [insert_values[key] for key in keys],
            )
            personnel_id = int(cursor.lastrowid)
            if "personnel_id" in table_columns(conn, "users"):
                conn.execute("UPDATE users SET personnel_id=? WHERE id=?", (personnel_id, int(user.get("id") or 0)))
        updates = {key: payload[key] for key in ("lat", "lng", "status") if key in payload}
        if updates:
            updates["last_seen"] = utc_now().isoformat(timespec="seconds")
            conn.execute(
                "UPDATE personnel SET " + ",".join(f'\"{key}\"=?' for key in updates) + " WHERE id=?",
                [updates[key] for key in updates] + [personnel_id],
            )
        conn.commit()
    return {"ok": True, "personnel_id": personnel_id, "last_seen": utc_now().isoformat(timespec="seconds")}


SYNC_EXCLUDED_TABLES = {"users", "web_sessions", "tenants", "sync_events", "sync_conflicts"}
SYNC_TABLES = TABLES - SYNC_EXCLUDED_TABLES


def sync_row_hash(row: dict, table: str = "") -> str:
    normalized = dict(row)
    if table == "offers":
        normalized.pop("pdf_path", None)
    return hashlib.sha256(
        json.dumps(normalized, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]


def record_sync_conflict(
    conn: sqlite3.Connection,
    table: str,
    record_id: str,
    source_id: str,
    base_hash: str,
    server_row: dict,
    client_row: dict,
) -> None:
    server_hash = sync_row_hash(server_row, table)
    client_hash = sync_row_hash(client_row, table)
    conn.execute(
        """
        INSERT OR IGNORE INTO sync_conflicts
        (table_name,record_id,source_id,base_hash,server_hash,client_hash,
         server_payload_json,client_payload_json,resolution,detected_at)
        VALUES (?,?,?,?,?,?,?,?, 'pending', ?)
        """,
        (
            table,
            record_id,
            source_id,
            base_hash,
            server_hash,
            client_hash,
            json.dumps(server_row, ensure_ascii=True, sort_keys=True, default=str),
            json.dumps(client_row, ensure_ascii=True, sort_keys=True, default=str),
            utc_now().isoformat(timespec="seconds"),
        ),
    )


def sync_manifest() -> dict:
    tenant_id = active_tenant_id()
    if not tenant_id:
        raise PermissionError("Senkronizasyon için firma oturumu gerekiyor.")
    result = {
        "ok": True,
        "tenant_id": tenant_id,
        "company_name": active_company_name(),
        "sync_epoch": tenant_sync_epoch(tenant_id),
        "reset_tables": sorted(SYNC_TABLES - WIPE_PRESERVE_TABLES),
        "tables": {},
    }
    with closing(db_connect()) as conn:
        for table in sorted(SYNC_TABLES):
            if not scalar(conn, "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (table,)):
                continue
            columns = table_columns(conn, table)
            item = {"count": int(scalar(conn, f'SELECT COUNT(*) FROM "{table}"', default=0)), "columns": columns}
            if "id" in columns:
                item["last_id"] = int(scalar(conn, f'SELECT COALESCE(MAX(id),0) FROM "{table}"', default=0) or 0)
            for timestamp in ("updated_at", "created_at", "date"):
                if timestamp in columns:
                    item["last_timestamp"] = scalar(conn, f'SELECT MAX("{timestamp}") FROM "{table}"', default="") or ""
                    break
            result["tables"][table] = item
    tenant = tenant_by_id(tenant_id) or {}
    result["db_filename"] = tenant.get("db_filename", "")
    return result


def sync_pull(body: dict) -> dict:
    validate_sync_epoch(body)
    tables = body.get("tables") or sorted(SYNC_TABLES)
    if not isinstance(tables, list):
        raise ValueError("Senkronizasyon tablo listesi geçersiz.")
    since = body.get("since") or {}
    limit = min(max(int(body.get("limit") or 5000), 1), 5000)
    changes: dict[str, list[dict]] = {}
    with closing(db_connect()) as conn:
        for table in tables:
            if table not in SYNC_TABLES or not scalar(conn, "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (table,)):
                continue
            columns = table_columns(conn, table)
            marker = since.get(table, "") if isinstance(since, dict) else ""
            where, params = "", []
            if "id" in columns and str(marker).isdigit():
                where, params = " WHERE id>?", [int(marker)]
            elif marker:
                timestamp = next((name for name in ("updated_at", "created_at", "date") if name in columns), None)
                if timestamp:
                    where, params = f' WHERE COALESCE("{timestamp}",\'\')>?', [str(marker)]
            order = " ORDER BY id ASC" if "id" in columns else ""
            changes[table] = rows(conn, f'SELECT * FROM "{table}"{where}{order} LIMIT ?', (*params, limit))
    return {"ok": True, "tenant_id": active_tenant_id(), "changes": changes}


def sync_tenant_directory_from_company_info(tenant_id: str, profile: dict) -> None:
    """Mirror synchronized desktop company details to the operator registry."""
    tenant_id = str(tenant_id or "").strip()
    if not tenant_id or not profile:
        return
    field_map = {
        "company_name": "company_name",
        "authorized_person": "contact_name",
        "phone": "phone",
        "email": "email",
    }
    updates = {
        target: str(profile.get(source) or "").strip()
        for source, target in field_map.items()
        if str(profile.get(source) or "").strip()
    }
    address = str(
        profile.get("installation_address")
        or profile.get("company_address")
        or profile.get("address")
        or ""
    ).strip()
    if address:
        updates["company_address"] = address
    try:
        latitude = float(profile.get("installation_lat"))
        longitude = float(profile.get("installation_lng"))
    except (TypeError, ValueError):
        latitude, longitude = None, None
    if latitude is None or longitude is None:
        latitude, longitude = resolve_installation_location(address)
    if latitude is not None and longitude is not None:
        if -90 <= latitude <= 90 and -180 <= longitude <= 180:
            updates["installation_lat"] = latitude
            updates["installation_lng"] = longitude
    if address or latitude is not None:
        updates["location_updated_at"] = utc_now().isoformat(timespec="seconds")
    if not updates:
        return
    sets = ", ".join(f'"{key}"=?' for key in updates)
    with closing(registry_connect()) as registry:
        registry.execute(
            f"UPDATE tenants SET {sets} WHERE id=?",
            (*updates.values(), tenant_id),
        )
        registry.commit()


def sync_push(body: dict, source_device_id: str = "") -> dict:
    validate_sync_epoch(body)
    changes = body.get("changes") or []
    if isinstance(changes, dict):
        changes = [{"table": table, "row": row, "action": "upsert"} for table, items in changes.items() for row in (items if isinstance(items, list) else [items])]
    if not isinstance(changes, list) or len(changes) > 5000:
        raise ValueError("Senkronizasyon değişiklik paketi geçersiz veya çok büyük.")
    applied = skipped = 0
    errors: list[str] = []
    conflicts: list[dict] = []
    changed_tables: set[str] = set()
    company_profile: dict | None = None
    with closing(db_connect()) as conn:
        conn.execute("PRAGMA foreign_keys=OFF")
        for change in changes:
            if not isinstance(change, dict) or change.get("table") not in SYNC_TABLES:
                errors.append("İzin verilmeyen tablo")
                continue
            table = str(change["table"])
            row = dict(change.get("row") or {})
            action = str(change.get("action") or "upsert").lower()
            source_id = str(change.get("source_id") or f"{table}:{row.get('id','')}:{action}:{hashlib.sha256(json.dumps(row, sort_keys=True, default=str).encode()).hexdigest()[:16]}")
            record_id = str(row.get("id") or "")
            try:
                duplicate = conn.execute(
                    "SELECT 1 FROM sync_events WHERE source_id=? AND table_name=? AND COALESCE(record_id,'')=? AND action=?",
                    (source_id, table, record_id, action),
                ).fetchone()
                if duplicate:
                    skipped += 1
                    continue
                columns = table_columns(conn, table)
                if "updated_at" in columns and action != "delete":
                    body["updated_at"] = datetime.now().isoformat(
                        timespec="microseconds"
                    )
                if action == "delete" and row.get("id") is not None:
                    if "is_deleted" in columns:
                        conn.execute(f'UPDATE "{table}" SET is_deleted=1 WHERE id=?', (row["id"],))
                    else:
                        conn.execute(f'DELETE FROM "{table}" WHERE id=?', (row["id"],))
                else:
                    clean = {key: value for key, value in row.items() if key in columns}
                    if not clean:
                        raise ValueError("Boş kayıt")
                    if table == "customer_currency_balances" and clean.get("customer_id") is not None and clean.get("currency"):
                        # Composite identity is customer + currency; desktop sync
                        # payloads may omit the server row id.
                        existing = conn.execute(
                            "SELECT id FROM customer_currency_balances WHERE customer_id=? AND currency=? LIMIT 1",
                            (clean["customer_id"], clean["currency"]),
                        ).fetchone()
                        if existing:
                            updates = {key: value for key, value in clean.items() if key not in {"id", "customer_id", "currency"}}
                            if updates:
                                setters = ",".join(f'"{key}"=?' for key in updates)
                                conn.execute(
                                    f'UPDATE "{table}" SET {setters} WHERE id=?',
                                    (*updates.values(), existing[0]),
                                )
                        else:
                            names = ",".join(f'"{key}"' for key in clean)
                            marks = ",".join("?" for _ in clean)
                            conn.execute(f'INSERT INTO "{table}" ({names}) VALUES ({marks})', tuple(clean.values()))
                    elif "id" in columns and clean.get("id") is not None:
                        existing = conn.execute(f'SELECT * FROM "{table}" WHERE id=?', (clean["id"],)).fetchone()
                        if existing:
                            existing_row = dict(existing)
                            server_hash = sync_row_hash(existing_row, table)
                            client_hash = sync_row_hash(clean, table)
                            base_hash = str(change.get("base_hash") or "")
                            concurrent_change = bool(
                                base_hash
                                and server_hash != base_hash
                                and client_hash != server_hash
                            )
                            stale_change = bool(
                                "updated_at" in columns
                                and clean.get("updated_at")
                                and existing["updated_at"]
                                and str(clean["updated_at"]) <= str(existing["updated_at"])
                                and client_hash != server_hash
                            )
                            if concurrent_change or stale_change:
                                record_sync_conflict(
                                    conn,
                                    table,
                                    record_id,
                                    source_id,
                                    base_hash,
                                    existing_row,
                                    clean,
                                )
                                conflicts.append(
                                    {"table": table, "record_id": record_id, "resolution": "server_kept"}
                                )
                                skipped += 1
                                continue
                            updates = {key: value for key, value in clean.items() if key != "id"}
                            if updates:
                                setters = ",".join(f'"{key}"=?' for key in updates)
                                conn.execute(f'UPDATE "{table}" SET {setters} WHERE id=?', (*updates.values(), clean["id"]))
                        else:
                            names = ",".join(f'"{key}"' for key in clean)
                            marks = ",".join("?" for _ in clean)
                            conn.execute(f'INSERT INTO "{table}" ({names}) VALUES ({marks})', tuple(clean.values()))
                    else:
                        names = ",".join(f'"{key}"' for key in clean)
                        marks = ",".join("?" for _ in clean)
                        conn.execute(f'INSERT INTO "{table}" ({names}) VALUES ({marks})', tuple(clean.values()))
                conn.execute(
                    "INSERT OR IGNORE INTO sync_events(source_id,table_name,record_id,action,payload_hash,created_at) VALUES (?,?,?,?,?,?)",
                    (source_id, table, record_id, action, hashlib.sha256(json.dumps(row, sort_keys=True, default=str).encode()).hexdigest(), utc_now().isoformat(timespec="seconds")),
                )
                applied += 1
                changed_tables.add(table)
            except Exception as error:
                errors.append(f"{table}: {error}")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.commit()
        if "company_info" in changed_tables or "settings" in changed_tables:
            profile_row = conn.execute(
                "SELECT * FROM company_info ORDER BY id DESC LIMIT 1"
            ).fetchone()
            company_profile = dict(profile_row) if profile_row else {}
            wanted = {
                "installation_lat", "installation_lng", "installation_address",
                "company_address",
            }
            for setting_row in rows(conn, "SELECT key,value FROM settings"):
                key = str(setting_row.get("key") or "")
                if key in wanted and setting_row.get("value") not in (None, ""):
                    company_profile[key] = setting_row.get("value")
    if company_profile:
        sync_tenant_directory_from_company_info(active_tenant_id(), company_profile)
    if applied:
        SYNC_EVENT_HUB.publish(
            active_tenant_id(),
            {
                "type": "sync_delta",
                "tenant_id": active_tenant_id(),
                "tables": sorted(changed_tables),
            },
            source_device_id,
        )
    return {
        "ok": not errors,
        "tenant_id": active_tenant_id(),
        "applied": applied,
        "skipped": skipped,
        "conflicts": conflicts,
        "errors": errors,
    }


class AYECRequestHandler(BaseHTTPRequestHandler):
    server_version = "AYECProWeb/2.0"

    def log_message(self, _format, *_args):
        return

    def session_token(self) -> str:
        authorization = self.headers.get("Authorization", "").strip()
        if authorization.lower().startswith("bearer "):
            return authorization[7:].strip()
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
            return cookie[SESSION_COOKIE].value if SESSION_COOKIE in cookie else ""
        except Exception:
            return ""

    def current_user(self) -> dict | None:
        if not hasattr(self, "_current_user_cache"):
            self._current_user_cache = session_user(self.session_token())
        return self._current_user_cache

    def client_ip(self) -> str:
        forwarded = self.headers.get("X-Forwarded-For", "").split(",", 1)[0].strip()
        return forwarded or self.client_address[0]

    def session_cookie_header(self, token: str, max_age: int = 0, remember: bool = False) -> str:
        value = f"{SESSION_COOKIE}={token}; Path=/; HttpOnly; SameSite=Lax"
        if remember and max_age > 0:
            value += f"; Max-Age={max_age}"
        if not token:
            value += "; Max-Age=0"
        secure = setting_bool(os.environ.get("AYEC_COOKIE_SECURE")) or self.headers.get("X-Forwarded-Proto", "").lower() == "https"
        if secure:
            value += "; Secure"
        return value

    def same_origin(self) -> bool:
        origin = self.headers.get("Origin", "").strip()
        if not origin:
            return True
        return urlparse(origin).netloc.lower() == self.headers.get("Host", "").lower()

    def _headers(self, status: int, content_type: str, length: int, extra_headers: dict | None = None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' data: https://accounts.google.com; style-src 'self' 'unsafe-inline' https://accounts.google.com; script-src 'self' https://accounts.google.com/gsi/client; frame-src 'self' https://accounts.google.com; connect-src 'self' https://accounts.google.com; object-src 'none'; base-uri 'self'; form-action 'self'")
        self.send_header("Cache-Control", "no-store")
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.end_headers()

    def send_json(self, data, status=200, headers: dict | None = None):
        payload = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self._headers(status, "application/json; charset=utf-8", len(payload), headers)
        self.wfile.write(payload)
        self._notify_sync_listeners_after_write(status)

    def _notify_sync_listeners_after_write(self, status: int) -> None:
        if status >= 400 or self.command not in {"POST", "PUT", "PATCH", "DELETE"}:
            return
        path = unquote(urlparse(self.path).path)
        if path.startswith("/api/auth/") or path in {
            "/api/sync/push",
            "/api/sync/pull",
            "/api/sync/provision",
        }:
            return
        tenant_id = active_tenant_id()
        if not tenant_id:
            return
        SYNC_EVENT_HUB.publish(
            tenant_id,
            {"type": "sync_delta", "tenant_id": tenant_id, "tables": []},
            self.headers.get("X-AYEC-Device-ID", ""),
        )

    def send_bytes(self, payload: bytes, content_type: str, status=200, disposition: str | None = None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Cache-Control", "no-store")
        if disposition:
            self.send_header("Content-Disposition", disposition)
        self.end_headers()
        self.wfile.write(payload)

    def send_file(self, target: Path, disposition: str | None = None):
        size = target.stat().st_size
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(size))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Cache-Control", "no-store")
        if disposition:
            self.send_header("Content-Disposition", disposition)
        self.end_headers()
        try:
            with target.open("rb") as source:
                shutil.copyfileobj(source, self.wfile, length=1024 * 1024)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            return

    def read_json(self):
        size = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(size).decode("utf-8")) if size else {}

    def _read_websocket_frame(self) -> int | None:
        header = self.connection.recv(2)
        if len(header) != 2:
            return None
        opcode = header[0] & 0x0F
        length = header[1] & 0x7F
        masked = bool(header[1] & 0x80)
        if length == 126:
            extra = self.connection.recv(2)
            if len(extra) != 2:
                return None
            length = int.from_bytes(extra, "big")
        elif length == 127:
            extra = self.connection.recv(8)
            if len(extra) != 8:
                return None
            length = int.from_bytes(extra, "big")
        if length > 65535:
            return None
        remaining = length + (4 if masked else 0)
        while remaining:
            chunk = self.connection.recv(min(remaining, 4096))
            if not chunk:
                return None
            remaining -= len(chunk)
        return opcode

    def open_sync_events(self):
        user = self.current_user()
        if not user:
            return self.send_json({"error": "Authentication required"}, 401)
        if self.headers.get("Upgrade", "").strip().lower() != "websocket":
            return self.send_json({"error": "WebSocket upgrade required"}, 426)
        key = self.headers.get("Sec-WebSocket-Key", "").strip()
        try:
            if len(base64.b64decode(key.encode("ascii"), validate=True)) != 16:
                raise ValueError("Invalid WebSocket key")
        except (ValueError, UnicodeError):
            return self.send_json({"error": "Invalid WebSocket key"}, 400)
        tenant_id = str(user.get("_tenant_id") or active_tenant_id() or "")
        if not tenant_id:
            return self.send_json({"error": "Tenant session required"}, 403)
        accept = base64.b64encode(
            hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")).digest()
        ).decode("ascii")
        self.send_response(101, "Switching Protocols")
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", accept)
        self.end_headers()
        device_id = str(self.headers.get("X-AYEC-Device-ID", "") or "").strip()[:128]
        SYNC_EVENT_HUB.register(tenant_id, self.connection, device_id)
        try:
            self.connection.settimeout(60)
            self.connection.sendall(SyncEventHub._frame({"type": "connected", "tenant_id": tenant_id}))
            while True:
                try:
                    opcode = self._read_websocket_frame()
                except socket.timeout:
                    continue
                if opcode is None or opcode == 0x08:
                    break
        except OSError:
            pass
        finally:
            SYNC_EVENT_HUB.unregister(tenant_id, self.connection)

    def do_GET(self):
        try:
            clear_tenant_context()
            parsed = urlparse(self.path)
            path = unquote(parsed.path)
            query = parse_qs(parsed.query)
            if path.startswith("/api/public/service/") or path.startswith("/servis/takip/"):
                prefix = "/api/public/service/" if path.startswith("/api/public/service/") else "/servis/takip/"
                token = path[len(prefix):].strip("/")
                record = public_service_record(token, self.client_ip(), self.headers.get("User-Agent", ""))
                if not record:
                    if prefix.startswith("/api"):
                        return self.send_json({"error": "Service record not found"}, 404)
                    payload = b"<!doctype html><meta charset=\"utf-8\"><title>AYEC Pro</title><h1>Servis kaydi bulunamadi</h1>"
                    return self._headers(404, "text/html; charset=utf-8", len(payload)) or self.wfile.write(payload)
                if prefix.startswith("/api"):
                    return self.send_json(record)
                payload = public_service_html(record).encode("utf-8")
                self._headers(200, "text/html; charset=utf-8", len(payload))
                return self.wfile.write(payload)
            if path == "/api/auth/status":
                return self.send_json(auth_status(self.session_token()))
            if path == "/api/auth/google/config":
                challenge = google_challenge()
                headers = {}
                if challenge.get("enabled"):
                    headers["Set-Cookie"] = "ayec_google_nonce=" + challenge["nonce"] + "; Path=/api/auth/google; HttpOnly; Secure; SameSite=Strict; Max-Age=600"
                return self.send_json(challenge, headers=headers)
            if path == "/api/license/catalog":
                return self.send_json({
                    "plans": license_plan_catalog(),
                    "payment": license_payment_profile(),
                })
            if path.startswith("/downloads/"):
                filename = path[len("/downloads/"):]
                if not filename or "/" in filename or "\\" in filename:
                    return self.send_json({"error": "Invalid download path"}, 400)
                target = (DOWNLOAD_ROOT / filename).resolve()
                if target.parent != DOWNLOAD_ROOT or not target.is_file():
                    return self.send_json({"error": "Download file not found"}, 404)
                return self.send_file(target, disposition=f'attachment; filename="{target.name}"')
            if path == "/api/desktop/health":
                try:
                    with closing(db_connect()) as conn:
                        available = {
                            row[0]
                            for row in conn.execute(
                                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                            )
                        }
                    missing = sorted(REQUIRED_OPERATIONAL_TABLES - available)
                    return self.send_json({
                        "ok": not missing,
                        "service": "AYEC Pro Web",
                        "schema_ready": not missing,
                        "missing_tables": missing,
                    }, 200 if not missing else 503)
                except Exception as error:
                    return self.send_json({"ok": False, "service": "AYEC Pro Web", "error": str(error)}, 503)
            if path == "/api/sync/events":
                return self.open_sync_events()
            # Super Admin login - no session needed
            if path == "/api/admin/login":
                return self.send_json({"error": "POST gerekli"}, 405)
            # Super Admin endpoints - validate with is_control_admin
            if path.startswith("/api/admin/"):
                user = self.current_user()
                if not user or not is_control_admin(user):
                    return self.send_json({"error": "Super Admin yetkisi gerekli.", "code": "FORBIDDEN"}, 403)
                # Dashboard
                if path == "/api/admin/dashboard":
                    return self.send_json(admin_dashboard())
                # Companies list
                if path == "/api/admin/companies":
                    search = query.get("q", [""])[0]
                    product_code = query.get("product_code", [""])[0]
                    return self.send_json({"companies": admin_list_companies(search, product_code)})
                # Customer 360 support view
                if path.startswith("/api/admin/customer-360/"):
                    tid = path.split("/api/admin/customer-360/")[-1].strip("/")
                    return self.send_json(admin_customer_360(tid))
                # Company detail
                if path.startswith("/api/admin/companies/") and not path.endswith("/users"):
                    tid = path.split("/api/admin/companies/")[-1]
                    return self.send_json(admin_company_detail(tid))
                # Company users
                if path.endswith("/users") and "/api/admin/companies/" in path:
                    tid = path.split("/api/admin/companies/")[-1].replace("/users", "")
                    return self.send_json({"users": admin_company_users(tid)})
                # Licenses
                if path == "/api/admin/licenses/usage":
                    return self.send_json({"usages": admin_licenses_usage()})
                if path == "/api/admin/licenses":
                    return self.send_json({"licenses": admin_list_licenses(query.get("product_code", [""])[0])})
                if path == "/api/admin/license-orders":
                    status = query.get("status", [""])[0]
                    return self.send_json({"orders": list_license_orders(status=status, product_code=query.get("product_code", [""])[0])})
                # Backups list
                if path.startswith("/api/admin/backups/") and not "/download/" in path and not path.endswith("/restore"):
                    tid = path.split("/api/admin/backups/")[-1]
                    return self.send_json({"backups": admin_list_backups(tid)})
                # Backup download
                if "/api/admin/backups/" in path and "/download/" in path:
                    parts = path.rsplit("/download/", 1)
                    tid = parts[0].split("/api/admin/backups/")[-1]
                    try:
                        idx = int(parts[1])
                    except ValueError:
                        idx = 0
                    backup_id = int(query.get("backup_id", ["0"])[0] or 0)
                    if backup_id:
                        payload, _digest, filename = admin_download_support_backup(user, tid, backup_id)
                    else:
                        payload, filename = admin_download_backup(tid, idx)
                    return self.send_bytes(payload, "application/vnd.sqlite3",
                        disposition=f'attachment; filename="{filename}"')
                # Error logs
                if path == "/api/admin/logs":
                    tid = query.get("tenant_id", [""])[0]
                    limit = int(query.get("limit", ["100"])[0])
                    return self.send_json({"logs": admin_error_logs(tid, limit)})
                if path == "/api/admin/audit-logs":
                    tid = query.get("tenant_id", [""])[0]
                    limit = int(query.get("limit", ["200"])[0])
                    return self.send_json({"logs": admin_audit_logs(tid, limit)})
                # Server status
                if path == "/api/admin/server-status":
                    return self.send_json(admin_server_status())
                # Live status
                if path == "/api/admin/live-status":
                    return self.send_json({"companies": admin_live_status()})
                return self.send_json({"error": "Endpoint bulunamadi"}, 404)
            if path.startswith("/api/") and not self.current_user():
                return self.send_json({"error": "Oturum açmanız gerekiyor.", "code": "AUTH_REQUIRED"}, 401)
            if path == "/api/control/overview":
                try:
                    return self.send_json(control_overview(self.current_user()))
                except PermissionError as error:
                    return self.send_json({"error": str(error)}, 403)
            if path == "/api/license/status":
                return self.send_json(license_status_for_user(self.current_user()))
            if path == "/api/license/orders":
                return self.send_json({"orders": list_license_orders(tenant_id=str(self.current_user().get("_tenant_id") or ""))})
            if path == "/api/control/provision-invites":
                try:
                    return self.send_json(control_list_provision_invites(self.current_user()))
                except PermissionError as error:
                    return self.send_json({"error": str(error)}, 403)
            if path == "/api/control/server-status":
                try:
                    return self.send_json(control_server_status(self.current_user()))
                except PermissionError as error:
                    return self.send_json({"error": str(error)}, 403)
            if path == "/api/control/telemetry/errors":
                try:
                    return self.send_json(control_get_error_logs(self.current_user()))
                except PermissionError as error:
                    return self.send_json({"error": str(error)}, 403)
            if path == "/api/control/staged-update":
                try:
                    return self.send_json(control_get_staged_updates(self.current_user()))
                except PermissionError as error:
                    return self.send_json({"error": str(error)}, 403)
            if path == "/api/support/desktop/commands":
                return self.send_json(desktop_pending_commands(self.current_user(),
                    self.headers.get("X-AYEC-Product-Code", "teknik_servis"),
                    self.headers.get("X-AYEC-Device-ID", ""),
                    self.headers.get("X-AYEC-Installation-ID", "")))
            if path.startswith("/api/support/backups/"):
                backup_text = path.rsplit("/", 1)[-1]
                if not backup_text.isdigit():
                    return self.send_json({"error": "Invalid backup number"}, 400)
                try:
                    payload, digest, name = support_backup_file(self.current_user(), int(backup_text),
                        self.headers.get("X-AYEC-Product-Code", "teknik_servis"),
                        self.headers.get("X-AYEC-Device-ID", ""),
                        self.headers.get("X-AYEC-Installation-ID", ""))
                    return self.send_bytes(
                        payload,
                        "application/vnd.sqlite3",
                        disposition=f'attachment; filename="{Path(name).name}"',
                    )
                except LookupError as error:
                    return self.send_json({"error": str(error)}, 404)
                except ValueError as error:
                    return self.send_json({"error": str(error)}, 409)
            if path == "/api/sync/manifest":
                return self.send_json(sync_manifest())
            if path == "/api/sync/pull":
                return self.send_json(sync_pull({"tables": query.get("table") or None, "since": {}}))
            if path == "/api/desktop/bootstrap":
                payload = desktop_bootstrap()
                payload["current_user"] = public_user(self.current_user())
                return self.send_json(payload)
            if path == "/api/desktop/exchange-rates":
                return self.send_json({"ok": True, "rates": exchange_rates(refresh=query.get("refresh", ["1"])[0] != "0")})
            if path == "/api/desktop/dialogs":
                data = json.loads(DIALOGS_MANIFEST.read_text(encoding="utf-8")) if DIALOGS_MANIFEST.exists() else {"summary": {}, "dialogs": []}
                return self.send_json(data)
            if path == "/api/desktop/company-logo":
                with closing(db_connect()) as conn:
                    logo_path = scalar(conn, "SELECT value FROM settings WHERE key='logo_path'", default="")
                logo = resolve_logo_path(logo_path)
                if not logo:
                    return self.send_json({"error": "Firma logosu ayarlanmamış"}, 404)
                content_type = mimetypes.guess_type(logo.name)[0] or "application/octet-stream"
                if content_type not in {"image/png", "image/jpeg", "image/webp"}:
                    return self.send_json({"error": "Firma logosu desteklenmeyen biçimde"}, 415)
                return self.send_bytes(logo.read_bytes(), content_type)
            if path.startswith("/api/desktop/proforma/"):
                offer_text = path.rsplit("/", 1)[-1]
                if not offer_text.isdigit():
                    return self.send_json({"error": "Geçersiz teklif numarası"}, 400)
                template = query.get("template", [None])[0]
                target, offer_no = build_offer_pdf(int(offer_text), template)
                try:
                    payload = target.read_bytes()
                finally:
                    target.unlink(missing_ok=True)
                mode = "attachment" if query.get("download", ["0"])[0] == "1" else "inline"
                safe_name = re.sub(r"[^A-Za-z0-9_-]+", "-", offer_no).strip("-") or "proforma"
                return self.send_bytes(payload, "application/pdf", disposition=f'{mode}; filename="{safe_name}.pdf"')
            if path.startswith("/api/desktop/vehicle-maintenance/detail/"):
                card_text = path.rsplit("/", 1)[-1]
                if not card_text.isdigit():
                    return self.send_json({"error": "Ge\u00e7ersiz bak\u0131m kart\u0131"}, 400)
                try:
                    return self.send_json(vehicle_maintenance_detail(int(card_text)))
                except LookupError as error:
                    return self.send_json({"error": str(error)}, 404)
            if path.startswith("/api/desktop/table/"):
                table = path.rsplit("/", 1)[-1]
                if table not in TABLES:
                    return self.send_json({"error": "Tablo izinli değil"}, 404)
                request_user = self.current_user()
                if table == "users" and not role_is_admin(request_user.get("role")):
                    return self.send_json({"error": "Kullanıcı yönetimi için yönetici yetkisi gerekiyor."}, 403)
                limit = min(max(int(query.get("limit", [100])[0]), 1), 1000)
                q = query.get("q", [""])[0].strip()
                with closing(db_connect()) as conn:
                    if not scalar(conn, "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (table,)):
                        return self.send_json({"table": table, "columns": [], "rows": [], "count": 0, "available": False})
                    columns = table_columns(conn, table)
                    where, params = "", []
                    if "is_deleted" in columns:
                        where = " WHERE COALESCE(is_deleted,0)=0"
                    if q:
                        searchable = [c for c in columns if c not in {"id", "is_deleted"}][:12]
                        prefix = " AND " if where else " WHERE "
                        where += prefix + "(" + " OR ".join(f'CAST("{c}" AS TEXT) LIKE ?' for c in searchable) + ")"
                        params.extend([f"%{q}%"] * len(searchable))
                    order = " ORDER BY id DESC" if "id" in columns else ""
                    data = rows(conn, f'SELECT * FROM "{table}"{where}{order} LIMIT ?', (*params, limit))
                    if table == "settings":
                        sensitive = re.compile(r"(password|pass$|token|api_key|secret|security_answer_hash)", re.I)
                        for item in data:
                            if sensitive.search(str(item.get("key", ""))):
                                item["value"] = ""
                    if table == "users":
                        private_columns = {
                            "password", "remember_token", "secret_answer", "security_answer_hash",
                            "reset_token", "reset_token_expires",
                        }
                        columns = [column for column in columns if column not in private_columns]
                        data = [
                            {key: value for key, value in item.items() if key not in private_columns}
                            for item in data
                        ]
                    return self.send_json({"table": table, "columns": columns, "rows": data, "count": len(data)})
            requested = path
            target = (WEB_ROOT / requested.lstrip("/")).resolve()
            if requested == "/" or not target.exists() or (target != WEB_ROOT and WEB_ROOT not in target.parents):
                target = WEB_ROOT / "index.html"
            payload = target.read_bytes()
            content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            if content_type.startswith("text/") or content_type == "application/javascript":
                content_type += "; charset=utf-8"
            self._headers(200, content_type, len(payload))
            self.wfile.write(payload)
        except Exception as exc:
            (ROOT / ".ayec-handler-error.log").write_text(traceback.format_exc(), encoding="utf-8")
            self.send_json({"error": str(exc)}, 500)

    def do_POST(self):
        try:
            clear_tenant_context()
            path = unquote(urlparse(self.path).path)
            if path == "/api/sync/provision":
                try:
                    payload = self.read_json()
                    consume_provision_rate_limit(
                        self.client_ip(),
                        self.headers.get("X-AYEC-Device-ID", ""),
                    )
                    result = provision_desktop_tenant(
                        payload,
                        str(payload.get("provision_invite_code") or ""),
                    )
                    tenant_id = str(dict(result.get("tenant") or {}).get("id") or "")
                    tenant = tenant_by_id(tenant_id)
                    if not tenant:
                        raise RuntimeError("Provisioned tenant was not found")
                    set_tenant_context(tenant)
                    with closing(db_connect()) as conn:
                        user = find_account_by_identifier(
                            conn,
                            str(dict(result.get("user") or {}).get("username") or ""),
                        )
                    if not user:
                        raise RuntimeError("Provisioned user was not found")
                    user = dict(user)
                    user["_tenant_id"] = tenant_id
                    user["_company_name"] = tenant["company_name"]
                    token, max_age = create_session(
                        int(user["id"]),
                        True,
                        self.headers.get("User-Agent", ""),
                        self.client_ip(),
                        tenant_id,
                    )
                    result["user"] = public_user(user)
                    result["token"] = token
                    result["access_token"] = token
                    return self.send_json(
                        result,
                        201,
                        headers={"Set-Cookie": self.session_cookie_header(token, max_age, True)},
                    )
                except PermissionError as error:
                    message = str(error)
                    normalized = message.casefold()
                    status = 429 if "rate limit" in normalized else 403 if "invitation" in normalized else 409
                    return self.send_json({"error": message}, status)
                except ValueError as error:
                    return self.send_json({"error": str(error)}, 400)
            if path == "/api/auth/setup":
                try:
                    result = setup_application(self.read_json())
                    return self.send_json(result, 201)
                except PermissionError as error:
                    return self.send_json({"error": str(error)}, 409)
                except ValueError as error:
                    return self.send_json({"error": str(error)}, 400)
            if path == "/api/license/activate":
                try:
                    return self.send_json(activate_tenant_invitation(self.read_json()))
                except PermissionError as error:
                    return self.send_json({"error": str(error), "code": "AUTH_REQUIRED"}, 401)
                except LookupError as error:
                    return self.send_json({"error": str(error)}, 404)
                except ValueError as error:
                    return self.send_json({"error": str(error)}, 400)
            if path == "/api/license/orders/device":
                try:
                    body = self.read_json()
                    consume_provision_rate_limit(
                        self.client_ip(),
                        "license:" + str(body.get("hardware_id") or ""),
                    )
                    return self.send_json(create_license_order_from_device(body), 201)
                except PermissionError as error:
                    return self.send_json({"error": str(error)}, 429)
                except LookupError as error:
                    return self.send_json({"error": str(error)}, 404)
                except ValueError as error:
                    return self.send_json({"error": str(error)}, 400)
            if path == "/api/license/status/device":
                try:
                    return self.send_json(license_status_from_device(self.read_json()))
                except PermissionError as error:
                    return self.send_json({"error": str(error), "code": "AUTH_REQUIRED"}, 401)
                except RuntimeError:
                    return self.send_json({"error": "Entitlement signing is not configured",
                                           "code": "SIGNING_UNAVAILABLE"}, 503)
                except LookupError as error:
                    return self.send_json({"error": str(error)}, 404)
                except ValueError as error:
                    return self.send_json({"error": str(error)}, 400)
            if path == "/api/license/orders/public":
                try:
                    return self.send_json(create_license_order_from_credentials(self.read_json()), 201)
                except PermissionError as error:
                    return self.send_json({"error": str(error), "code": "AUTH_REQUIRED"}, 401)
                except ValueError as error:
                    return self.send_json({"error": str(error)}, 400)
            if path == "/api/license/status/public":
                try:
                    return self.send_json(license_status_from_credentials(self.read_json()))
                except PermissionError as error:
                    return self.send_json({"error": str(error), "code": "AUTH_REQUIRED"}, 401)
            if path.startswith("/api/license/orders/") and path.endswith("/payment-reported/public"):
                try:
                    order_id = int(path.split("/api/license/orders/")[-1].replace("/payment-reported/public", ""))
                    return self.send_json(report_license_payment_from_credentials(order_id, self.read_json()))
                except PermissionError as error:
                    return self.send_json({"error": str(error), "code": "AUTH_REQUIRED"}, 401)
                except LookupError as error:
                    return self.send_json({"error": str(error)}, 404)
                except ValueError as error:
                    return self.send_json({"error": str(error)}, 400)
            if path == "/api/auth/google":
                if not self.same_origin() or not self.headers.get("Origin"):
                    return self.send_json({"error": "Gecersiz kaynak."}, 403)
                if auth_rate_limited(self.client_ip()):
                    return self.send_json({"error": "Cok fazla deneme. Daha sonra tekrar deneyin."}, 429)
                try:
                    body = self.read_json()
                    cookies = SimpleCookie(self.headers.get("Cookie", ""))
                    nonce_cookie = cookies.get("ayec_google_nonce")
                    nonce = nonce_cookie.value if nonce_cookie else ""
                    identity = verify_google_identity(str(body.get("credential") or ""), nonce)
                    if body.get("mode") == "register":
                        consume_provision_rate_limit(self.client_ip(), "google-registration")
                    result = google_account(identity, body)
                    user = result["user"]
                    access_error = tenant_access_error(tenant_by_id(str(user.get("_tenant_id") or "")))
                    if access_error and not is_control_admin(user):
                        return self.send_json({"error": access_error, "code": "LICENSE_REQUIRED"}, 403)
                    token, max_age = create_session(int(user["id"]), False, self.headers.get("User-Agent", ""), self.client_ip(), user.get("_tenant_id"))
                    clear_auth_failures(self.client_ip())
                    return self.send_json({"ok": True, "user": public_user(user), "created": result["created"], "mail_sent": result.get("mail_sent"), "mail_message": result.get("mail_message")}, headers={"Set-Cookie": self.session_cookie_header(token, max_age, False)})
                except (ValueError, PermissionError) as error:
                    record_auth_failure(self.client_ip())
                    return self.send_json({"error": str(error)}, 400)
            if path == "/api/auth/register":
                try:
                    body = self.read_json()
                    existing_user = self.current_user()
                    result = register_account(body, (existing_user or {}).get("_tenant_id"))
                    return self.send_json(result, 201)
                except PermissionError as error:
                    return self.send_json({"error": str(error)}, 403)
                except ValueError as error:
                    return self.send_json({"error": str(error)}, 400)
            if path == "/api/auth/company":
                try:
                    return self.send_json(setup_application(self.read_json(), allow_existing=True), 201)
                except PermissionError as error:
                    return self.send_json({"error": str(error)}, 409)
                except ValueError as error:
                    return self.send_json({"error": str(error)}, 400)
            if path == "/api/auth/login":
                client_key = self.client_ip()
                if auth_rate_limited(client_key):
                    return self.send_json({"error": "Çok fazla başarısız deneme. 15 dakika sonra tekrar deneyin."}, 429)
                body = self.read_json()
                user = authenticate_account(
                    str(body.get("identifier") or ""),
                    str(body.get("password") or ""),
                    str(body.get("tenant_id") or "") or None,
                )
                if not user:
                    record_auth_failure(client_key)
                    return self.send_json({"error": "Kullanıcı adı/e-posta veya parola hatalı."}, 401)
                if bool(user.get("must_change_password")):
                    clear_auth_failures(client_key)
                    return self.send_json({
                        "ok": True,
                        "password_change_required": True,
                        "tenant_id": user.get("_tenant_id"),
                    })
                access_error = tenant_access_error(tenant_by_id(str(user.get("_tenant_id") or "")))
                if access_error and not is_control_admin(user):
                    return self.send_json({"error": access_error, "code": "LICENSE_REQUIRED"}, 403)
                clear_auth_failures(client_key)
                remember = bool(body.get("remember"))
                token, max_age = create_session(
                    int(user["id"]), remember, self.headers.get("User-Agent", ""), self.client_ip(), user.get("_tenant_id")
                )
                return self.send_json(
                    {"ok": True, "token": token, "access_token": token, "user": public_user(user)},
                    headers={"Set-Cookie": self.session_cookie_header(token, max_age, remember)},
                )
            if path == "/api/auth/logout":
                delete_session(self.session_token())
                return self.send_json(
                    {"ok": True}, headers={"Set-Cookie": self.session_cookie_header("")}
                )
            if path == "/api/auth/profile":
                user = self.require_user()
                try:
                    return self.send_json(update_current_user_profile(user, self.read_json()))
                except (LookupError, ValueError) as error:
                    return self.send_json({"error": str(error)}, 400)
            if path == "/api/auth/reset-password":
                try:
                    return self.send_json(complete_password_reset(self.read_json()))
                except ValueError as error:
                    return self.send_json({"error": str(error)}, 400)
            if path == "/api/auth/change-temporary-password":
                if not self.same_origin() or not self.headers.get("Origin"):
                    return self.send_json({"error": "Gecersiz istek kaynagi."}, 403)
                if auth_rate_limited(self.client_ip()):
                    return self.send_json({"error": "Cok fazla deneme. Daha sonra tekrar deneyin."}, 429)
                try:
                    result = complete_temporary_password_change(self.read_json())
                    clear_auth_failures(self.client_ip())
                    return self.send_json(result)
                except (ValueError, PermissionError) as error:
                    record_auth_failure(self.client_ip())
                    return self.send_json({"error": str(error)}, 400)
            if path == "/api/control/telemetry/errors":
                try:
                    return self.send_json(control_add_error_log(self.read_json()))
                except Exception as error:
                    return self.send_json({"error": str(error)}, 400)
            # Super Admin POST - login
            if path == "/api/admin/login":
                body = self.read_json()
                user = authenticate_account(
                    str(body.get("email") or body.get("identifier") or ""),
                    str(body.get("password") or ""),
                    None,
                )
                if not user or not is_control_admin(user):
                    return self.send_json({"error": "Super Admin yetkisi yok veya kimlik bilgileri hatali."}, 401)
                if bool(user.get("must_change_password")):
                    return self.send_json({"error": "Once gecici parolanizi degistirin."}, 403)
                token, max_age = create_session(
                    int(user["id"]), True, self.headers.get("User-Agent", ""),
                    self.client_ip(), user.get("_tenant_id")
                )
                return self.send_json(
                    {"ok": True, "user": public_user(user)},
                    headers={"Set-Cookie": self.session_cookie_header(token, max_age, True)},
                )
            # Wipe All belongs to the signed-in company administrator, not the
            # platform administrator API handled by this block.
            if path.startswith("/api/admin/") and path != "/api/admin/wipe-user-data":
                user = self.current_user()
                if not user or not is_control_admin(user):
                    return self.send_json({"error": "Super Admin yetkisi gerekli.", "code": "FORBIDDEN"}, 403)
                body = self.read_json()
                if path == "/api/admin/companies/locations/refresh":
                    return self.send_json(admin_refresh_company_locations(user))
                # Execute Remote SQL
                if path.startswith("/api/admin/companies/") and path.endswith("/query"):
                    tid = path.split("/api/admin/companies/")[-1].replace("/query", "")
                    return self.send_json(admin_execute_query(tid, body.get("sql", ""), user))
                if path.startswith("/api/admin/companies/") and path.endswith("/delete"):
                    tid = path.split("/api/admin/companies/")[-1].replace("/delete", "")
                    return self.send_json(admin_delete_company(tid, user))
                if path.startswith("/api/admin/companies/") and path.endswith("/repair-users"):
                    tid = path.split("/api/admin/companies/")[-1].replace("/repair-users", "")
                    return self.send_json(admin_repair_company_users(tid, user))
                # Update company
                if path.startswith("/api/admin/companies/") and not "/users" in path and not "/restore" in path and not "/repair-users" in path:
                    tid = path.split("/api/admin/companies/")[-1]
                    return self.send_json(admin_update_company(tid, body, user))
                # Reset password
                if path.startswith("/api/admin/users/") and path.endswith("/reset-password"):
                    uid = int(path.split("/api/admin/users/")[-1].replace("/reset-password", ""))
                    return self.send_json(admin_reset_user_password(
                        body.get("tenant_id", ""), uid, body.get("new_password", ""), user
                    ))
                if path == "/api/admin/users/temporary-password":
                    return self.send_json(admin_send_temporary_password(
                        body.get("tenant_id", ""), int(body.get("user_id") or 0), user
                    ))
                if path.startswith("/api/admin/license-orders/") and path.endswith("/approve"):
                    order_id = int(path.split("/api/admin/license-orders/")[-1].replace("/approve", ""))
                    return self.send_json(approve_license_order(order_id, body, user))
                if path.startswith("/api/admin/license-orders/") and path.endswith("/reject"):
                    order_id = int(path.split("/api/admin/license-orders/")[-1].replace("/reject", ""))
                    return self.send_json(reject_license_order(order_id, body, user))
                if path.startswith("/api/admin/license-orders/") and path.endswith("/cancel"):
                    order_id = int(path.split("/api/admin/license-orders/")[-1].replace("/cancel", ""))
                    return self.send_json(cancel_license_order(order_id, body, user))
                # Update license
                if path.startswith("/api/admin/licenses/"):
                    tid = path.split("/api/admin/licenses/")[-1]
                    return self.send_json(admin_update_license(tid, body, user))
                # Restore backup
                if path.endswith("/restore") and "/api/admin/backups/" in path:
                    tid = path.split("/api/admin/backups/")[-1].replace("/restore", "")
                    return self.send_json(admin_restore_backup(
                        tid,
                        int(body.get("backup_index", 0)),
                        user,
                        int(body.get("backup_id", 0)),
                    ))
                # Send notification
                if path == "/api/admin/notifications/send":
                    return self.send_json(admin_send_notification(body, user))
                # Deploy update
                if path == "/api/admin/updates/deploy":
                    return self.send_json(admin_deploy_update(body, user))
                return self.send_json({"error": "Endpoint bulunamadi"}, 404)

            user = self.current_user()
            if not user:
                return self.send_json({"error": "Oturum açmanız gerekiyor.", "code": "AUTH_REQUIRED"}, 401)
            if not self.same_origin():
                return self.send_json({"error": "İstek kaynağı doğrulanamadı."}, 403)
            if path == "/api/license/orders":
                try:
                    return self.send_json(create_license_order(user, self.read_json()), 201)
                except ValueError as error:
                    return self.send_json({"error": str(error)}, 400)
            if path.startswith("/api/license/orders/") and path.endswith("/payment-reported"):
                try:
                    order_id = int(path.split("/api/license/orders/")[-1].replace("/payment-reported", ""))
                    return self.send_json(report_license_payment(user, order_id, self.read_json()))
                except LookupError as error:
                    return self.send_json({"error": str(error)}, 404)
                except ValueError as error:
                    return self.send_json({"error": str(error)}, 400)
            if path == "/api/control/tenant":
                try:
                    return self.send_json(control_update_tenant(user, self.read_json()))
                except PermissionError as error:
                    return self.send_json({"error": str(error)}, 403)
                except LookupError as error:
                    return self.send_json({"error": str(error)}, 404)
                except ValueError as error:
                    return self.send_json({"error": str(error)}, 400)
            if path == "/api/control/provision-invite":
                try:
                    return self.send_json(control_create_provision_invite(user, self.read_json()), 201)
                except PermissionError as error:
                    return self.send_json({"error": str(error)}, 403)
                except ValueError as error:
                    return self.send_json({"error": str(error)}, 400)
            if path == "/api/control/provision-invite/revoke":
                try:
                    return self.send_json(control_revoke_provision_invite(user, self.read_json()))
                except PermissionError as error:
                    return self.send_json({"error": str(error)}, 403)
                except LookupError as error:
                    return self.send_json({"error": str(error)}, 404)
                except ValueError as error:
                    return self.send_json({"error": str(error)}, 400)
            if path == "/api/company/sector":
                try:
                    return self.send_json(update_current_company_sector(user, self.read_json()))
                except PermissionError as error:
                    return self.send_json({"error": str(error)}, 403)
                except LookupError as error:
                    return self.send_json({"error": str(error)}, 404)
                except ValueError as error:
                    return self.send_json({"error": str(error)}, 400)
            if path == "/api/company/location":
                try:
                    return self.send_json(update_current_company_location(user, self.read_json()))
                except PermissionError as error:
                    return self.send_json({"error": str(error)}, 403)
                except ValueError as error:
                    return self.send_json({"error": str(error)}, 400)
            if path == "/api/control/send-notification":
                try:
                    return self.send_json(control_send_notification(user, self.read_json()))
                except PermissionError as error:
                    return self.send_json({"error": str(error)}, 403)
                except ValueError as error:
                    return self.send_json({"error": str(error)}, 400)
            if path == "/api/control/staged-update":
                try:
                    return self.send_json(control_add_staged_update(user, self.read_json()))
                except PermissionError as error:
                    return self.send_json({"error": str(error)}, 403)
                except ValueError as error:
                    return self.send_json({"error": str(error)}, 400)
            if path == "/api/control/user":
                try:
                    return self.send_json(control_update_user(user, self.read_json()))
                except PermissionError as error:
                    return self.send_json({"error": str(error)}, 403)
                except LookupError as error:
                    return self.send_json({"error": str(error)}, 404)
                except (ValueError, sqlite3.IntegrityError) as error:
                    return self.send_json({"error": str(error)}, 400)
            if path == "/api/control/password-reset":
                try:
                    return self.send_json(control_create_reset_link(user, self.read_json()))
                except PermissionError as error:
                    return self.send_json({"error": str(error)}, 403)
                except LookupError as error:
                    return self.send_json({"error": str(error)}, 404)
                except ValueError as error:
                    return self.send_json({"error": str(error)}, 400)
            if path == "/api/control/restore":
                try:
                    return self.send_json(control_queue_restore(user, self.read_json()))
                except PermissionError as error:
                    return self.send_json({"error": str(error)}, 403)
                except LookupError as error:
                    return self.send_json({"error": str(error)}, 404)
                except ValueError as error:
                    return self.send_json({"error": str(error)}, 400)
            if path == "/api/control/backups/prune":
                try:
                    return self.send_json(control_prune_backups(user, self.read_json()))
                except PermissionError as error:
                    return self.send_json({"error": str(error)}, 403)
                except LookupError as error:
                    return self.send_json({"error": str(error)}, 404)
                except ValueError as error:
                    return self.send_json({"error": str(error)}, 400)
            if path == "/api/mobile/personnel/location":
                try:
                    body = self.read_json()
                    latitude = float(body.get("lat"))
                    longitude = float(body.get("lng"))
                    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                        raise ValueError("Coordinates are out of range")
                    return self.send_json(update_mobile_personnel_presence(
                        user,
                        {"lat": latitude, "lng": longitude},
                    ))
                except (TypeError, ValueError) as error:
                    return self.send_json({"error": str(error)}, 400)
            if path == "/api/mobile/personnel/status":
                try:
                    body = self.read_json()
                    status = str(body.get("status") or "").strip()
                    if not status or len(status) > 40:
                        raise ValueError("Status is invalid")
                    return self.send_json(update_mobile_personnel_presence(user, {"status": status}))
                except ValueError as error:
                    return self.send_json({"error": str(error)}, 400)
            if path == "/api/support/desktop/complete":
                try:
                    return self.send_json(desktop_complete_command(user, self.read_json(),
                        self.headers.get("X-AYEC-Product-Code", "teknik_servis"),
                        self.headers.get("X-AYEC-Device-ID", ""),
                        self.headers.get("X-AYEC-Installation-ID", "")))
                except LookupError as error:
                    return self.send_json({"error": str(error)}, 404)
            if path == "/api/support/backups/upload":
                try:
                    size = int(self.headers.get("Content-Length", "0"))
                    if size <= 0 or size > 1024 * 1024 * 1024:
                        return self.send_json({"error": "Backup size is invalid"}, 413)
                    payload = self.rfile.read(size)
                    return self.send_json(
                        support_store_backup(
                            user, payload,
                            self.headers.get("X-AYEC-Backup-Name", "desktop.db"),
                            self.headers.get("X-AYEC-Program", ""),
                            self.headers.get("X-AYEC-Product-Code", ""),
                            self.headers.get("X-AYEC-Device-ID", ""),
                            self.headers.get("X-AYEC-Installation-ID", ""),
                        )
                    )
                except PermissionError as error:
                    return self.send_json({"error": str(error)}, 403)
                except ValueError as error:
                    return self.send_json({"error": str(error)}, 400)
            if path == "/api/sync/push":
                try:
                    return self.send_json(
                        sync_push(
                            self.read_json(),
                            self.headers.get("X-AYEC-Device-ID", ""),
                        )
                    )
                except ValueError as error:
                    return self.send_json({"error": str(error)}, 400)
            if path == "/api/sync/pull":
                return self.send_json(sync_pull(self.read_json()))
            if path == "/api/admin/wipe-user-data":
                body = self.read_json()
                try:
                    return self.send_json(wipe_user_data(user, str(body.get("password") or ""), str(body.get("phrase") or "")))
                except PermissionError as error:
                    return self.send_json({"error": str(error)}, 403)
                except ValueError as error:
                    return self.send_json({"error": str(error)}, 400)
            if path == "/api/desktop/company-logo":
                if not role_is_admin(user.get("role")):
                    return self.send_json({"error": "Firma ayarları için yönetici yetkisi gerekiyor."}, 403)
                body = self.read_json()
                if body.get("remove"):
                    with closing(db_connect()) as conn:
                        conn.execute("INSERT INTO settings (key,value) VALUES ('logo_path','') ON CONFLICT(key) DO UPDATE SET value='' ")
                        conn.commit()
                    return self.send_json({"ok": True, "path": "", "url": ""})
                payload = base64.b64decode(body.get("data", ""), validate=True)
                if not payload or len(payload) > 5 * 1024 * 1024:
                    return self.send_json({"error": "Logo boş veya 5 MB sınırını aşıyor"}, 413)
                if payload.startswith(b"\x89PNG\r\n\x1a\n"):
                    extension = ".png"
                elif payload.startswith(b"\xff\xd8\xff"):
                    extension = ".jpg"
                elif payload.startswith(b"RIFF") and payload[8:12] == b"WEBP":
                    extension = ".webp"
                else:
                    return self.send_json({"error": "Yalnızca PNG, JPG veya WEBP logo yüklenebilir"}, 415)
                upload_dir = WEB_ROOT / "uploads"
                upload_dir.mkdir(parents=True, exist_ok=True)
                target = upload_dir / f"company-logo-{datetime.now().strftime('%Y%m%d%H%M%S%f')}{extension}"
                target.write_bytes(payload)
                stored_path = target.relative_to(ROOT).as_posix()
                with closing(db_connect()) as conn:
                    conn.execute(
                        "INSERT INTO settings (key,value) VALUES ('logo_path',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                        (stored_path,),
                    )
                    conn.commit()
                return self.send_json({"ok": True, "path": stored_path, "url": "/api/desktop/company-logo"})
            if path == "/api/desktop/customer/payment":
                exchange_rates(refresh=True)
                try:
                    return self.send_json(record_customer_payment(self.read_json()))
                except LookupError as error:
                    return self.send_json({"error": str(error)}, 404)
                except ValueError as error:
                    return self.send_json({"error": str(error)}, 400)
            if path == "/api/desktop/stock/delete":
                body = self.read_json()
                part_id = int(body.get("id") or 0)
                if not part_id:
                    return self.send_json({"error": "Geçersiz stok kartı"}, 400)
                try:
                    return self.send_json(delete_stock_with_reversal(part_id))
                except LookupError as error:
                    return self.send_json({"error": str(error)}, 404)
            if path == "/api/desktop/stock/save":
                exchange_rates(refresh=True)
                try:
                    return self.send_json(save_stock_card(self.read_json()))
                except LookupError as error:
                    return self.send_json({"error": str(error)}, 404)
                except ValueError as error:
                    return self.send_json({"error": str(error)}, 400)
            if path == "/api/desktop/sales/commit":
                exchange_rates(refresh=True)
                try:
                    return self.send_json(commit_sales_hub(self.read_json()))
                except LookupError as error:
                    return self.send_json({"error": str(error)}, 404)
                except ValueError as error:
                    return self.send_json({"error": str(error)}, 400)
            if path == "/api/desktop/technician/update":
                exchange_rates(refresh=True)
                try:
                    return self.send_json(update_technician_job(self.read_json()))
                except LookupError as error:
                    return self.send_json({"error": str(error)}, 404)
                except ValueError as error:
                    return self.send_json({"error": str(error)}, 400)
            if path == "/api/desktop/vehicle-maintenance/save":
                try:
                    return self.send_json(save_vehicle_maintenance_web(self.read_json()))
                except LookupError as error:
                    return self.send_json({"error": str(error)}, 404)
                except ValueError as error:
                    return self.send_json({"error": str(error)}, 400)
            if path == "/api/desktop/smart-import":
                try:
                    body = self.read_json()
                    payload = base64.b64decode(body.get("data", ""), validate=True)
                    if not payload:
                        return self.send_json({"error": "İçe aktarılacak dosya boş"}, 400)
                    if len(payload) > 25 * 1024 * 1024:
                        return self.send_json({"error": "Dosya 25 MB sınırını aşıyor"}, 413)
                    return self.send_json(smart_import(body.get("name", "belge"), payload))
                except (ValueError, json.JSONDecodeError) as error:
                    return self.send_json({"error": f"İçe aktarma verisi geçersiz: {error}"}, 400)
                except Exception as error:
                    (ROOT / ".ayec-import-error.log").write_text(traceback.format_exc(), encoding="utf-8")
                    return self.send_json({"error": f"Akıllı içe aktarma başarısız: {error}"}, 500)
            if not path.startswith("/api/desktop/table/"):
                return self.send_json({"error": "Endpoint bulunamadı"}, 404)
            table = path.rsplit("/", 1)[-1]
            if table not in TABLES:
                return self.send_json({"error": "Tablo izinli değil"}, 404)
            if table in {"users", "settings", "internal_settings"} and not role_is_admin(user.get("role")):
                return self.send_json({"error": "Bu ayarı değiştirmek için yönetici yetkisi gerekiyor."}, 403)
            body = self.read_json()
            if (
                table == "internal_settings"
                and str(body.get("key") or "") == "current_sector"
            ):
                return self.send_json(
                    {"error": "Sector can only be changed from the platform management panel"},
                    403,
                )
            action = body.pop("_action", "insert")
            row_id = body.pop("id", None)
            with closing(db_connect()) as conn:
                if not scalar(conn, "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (table,)):
                    return self.send_json({"error": "Masaüstü veritabanında bu modül tablosu henüz oluşturulmamış"}, 404)
                columns = table_columns(conn, table)
                if table == "accounting" and action != "delete" and any(
                    key in body
                    for key in ("amount", "original_amount", "currency", "exchange_rate", "try_equivalent")
                ):
                    existing = {}
                    if action == "update" and row_id is not None:
                        current_row = conn.execute(
                            'SELECT * FROM "accounting" WHERE id=?',
                            (row_id,),
                        ).fetchone()
                        existing = dict(current_row) if current_row else {}
                    body = normalize_accounting_payload(conn, body, existing)
                clean = {
                    k: v
                    for k, v in body.items()
                    if k in columns and k not in {"id", "password", "remember_token"}
                }
                if table in {"settings", "internal_settings"} and "key" in body:
                    conn.execute(
                        f'INSERT INTO "{table}" (key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                        (body["key"], str(body.get("value", ""))),
                    )
                    conn.commit()
                    return self.send_json({"ok": True, "id": body["key"], "action": "upsert"})
                if table == "customer_currency_balances" and clean.get("customer_id") is not None and clean.get("currency"):
                    balance_row = conn.execute(
                        "SELECT id FROM customer_currency_balances WHERE customer_id=? AND currency=? LIMIT 1",
                        (clean["customer_id"], clean["currency"]),
                    ).fetchone()
                    if balance_row:
                        updates = {k: v for k, v in clean.items() if k not in {"customer_id", "currency", "id"}}
                        if updates:
                            sets = ",".join(f'"{k}"=?' for k in updates)
                            conn.execute(f'UPDATE customer_currency_balances SET {sets} WHERE id=?', (*updates.values(), balance_row[0]))
                        row_id = balance_row[0]
                        action = "update"
                    else:
                        names = ",".join(f'"{k}"' for k in clean)
                        marks = ",".join("?" for _ in clean)
                        conn.execute(f'INSERT INTO customer_currency_balances ({names}) VALUES ({marks})', tuple(clean.values()))
                        row_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                        action = "insert"
                elif action == "delete" and row_id is not None:
                    if "is_deleted" in columns:
                        if "updated_at" in columns:
                            conn.execute(
                                f'UPDATE "{table}" SET is_deleted=1,updated_at=? WHERE id=?',
                                (datetime.now().isoformat(timespec="microseconds"), row_id),
                            )
                        else:
                            conn.execute(f'UPDATE "{table}" SET is_deleted=1 WHERE id=?', (row_id,))
                    else:
                        conn.execute(f'DELETE FROM "{table}" WHERE id=?', (row_id,))
                elif action == "update" and row_id is not None:
                    if clean:
                        sets = ",".join(f'"{k}"=?' for k in clean)
                        conn.execute(f'UPDATE "{table}" SET {sets} WHERE id=?', (*clean.values(), row_id))
                else:
                    if "created_at" in columns and "created_at" not in clean:
                        clean["created_at"] = datetime.now().isoformat(timespec="seconds")
                    names = ",".join(f'"{k}"' for k in clean)
                    marks = ",".join("?" for _ in clean)
                    cur = conn.execute(f'INSERT INTO "{table}" ({names}) VALUES ({marks})', tuple(clean.values()))
                    row_id = cur.lastrowid
                    if table == "devices" and str(clean.get("service_source") or "") == "Web Otomotiv":
                        link_web_automotive_service(conn, int(row_id), clean, body)
                if table == "customers" and row_id is not None:
                    save_web_customer_balances(conn, int(row_id), body.get("balances"))
                conn.commit()
            return self.send_json({"ok": True, "id": row_id, "action": action})
        except Exception as exc:
            (ROOT / ".ayec-handler-error.log").write_text(traceback.format_exc(), encoding="utf-8")
            self.send_json({"error": str(exc)}, 400)


def main() -> None:
    global DB_PATH, TENANT_ROOT
    parser = argparse.ArgumentParser(description="AYEC Pro web arayuzu")
    parser.add_argument("--host", default=os.environ.get("AYEC_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("AYEC_PORT", "8501")))
    parser.add_argument("--db", default=str(DB_PATH), help="SQLite veritabanı dosyası")
    parser.add_argument("--tenant-dir", default=str(TENANT_ROOT), help="Firma SQLite dosyalarının klasörü")
    args = parser.parse_args()
    DB_PATH = Path(args.db).expanduser().resolve()
    TENANT_ROOT = Path(args.tenant_dir).expanduser().resolve()
    mimetypes.add_type("application/javascript", ".js")
    server = ThreadingHTTPServer((args.host, args.port), AYECRequestHandler)
    print(f"AYEC Pro hazır: http://127.0.0.1:{args.port} | Veritabanı: {DB_PATH}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
