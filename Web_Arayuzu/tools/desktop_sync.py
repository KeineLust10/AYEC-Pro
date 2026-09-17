r"""Run one desktop <-> company web database synchronization cycle.

Example:
  python tools/desktop_sync.py --url http://85.117.239.60 --db C:\AYEC\ayecpro.db
"""

from __future__ import annotations

import argparse
import getpass
import json
import sys

from src.utils.web_sync_client import WebSyncClient, WebSyncError


def main() -> int:
    parser = argparse.ArgumentParser(description="AYEC Pro firma veritabanı senkronizasyonu")
    parser.add_argument("--url", required=True, help="Web arayüzü adresi")
    parser.add_argument("--db", required=True, help="Masaüstü SQLite dosyası")
    parser.add_argument("--state", help="Senkronizasyon durum dosyası")
    parser.add_argument("--user", required=True, help="Firma kullanıcı adı veya e-posta")
    parser.add_argument("--tenant", help="Aynı kullanıcı birden fazla firmadaysa tenant kimliği")
    parser.add_argument("--password", help="Parola (önerilen: komut satırında vermeyin)")
    parser.add_argument("--insecure", action="store_true", help="HTTPS sertifika doğrulamasını kapat")
    args = parser.parse_args()
    password = args.password or getpass.getpass("AYEC Pro parolası: ")
    try:
        client = WebSyncClient(args.url, verify_tls=not args.insecure)
        client.login(args.user, password, remember=True, tenant_id=args.tenant)
        result = client.sync_sqlite(args.db, args.state)
    except WebSyncError as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
