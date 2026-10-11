from __future__ import annotations

import os
import sys
from contextlib import closing

import Main


EMAIL = "ayecpro@gmail.com"
PASSWORD = str(os.environ.get("AYEC_ADMIN_CHECK_PASSWORD") or "").strip()


def main() -> int:
    if not PASSWORD:
        print("ERROR: password was not received.")
        return 2

    print(f"REGISTRY_DB={Main.DB_PATH}")
    print(f"TENANT_ROOT={Main.TENANT_ROOT}")
    found = 0
    any_match = False
    any_super_admin = False

    for tenant in Main.tenant_records():
        filename = os.path.basename(str(tenant.get("db_filename") or ""))
        Main.set_tenant_context(tenant)
        path = Main.active_db_path()
        if not path.is_file():
            print(f"TENANT_DB={filename} FILE_EXISTS=False")
            continue

        with closing(Main.db_connect()) as conn:
            row = Main.find_account_by_identifier(conn, EMAIL)
            if not row:
                print(f"TENANT_DB={filename} USER_FOUND=False")
                continue
            found += 1
            password_match = Main.password_matches(PASSWORD, row["password"])
            user = dict(row)
            user["_tenant_id"] = str(tenant.get("id") or "")
            user["_company_name"] = str(tenant.get("company_name") or "")

        super_admin = bool(password_match and Main.is_control_admin(user))
        any_match = any_match or password_match
        any_super_admin = any_super_admin or super_admin
        print(
            f"TENANT_DB={filename} USER_FOUND=True "
            f"PASSWORD_MATCH={password_match} SUPER_ADMIN={super_admin}"
        )

    print(f"ACTIVE_TENANT_ACCOUNTS_FOUND={found}")
    print(f"OVERALL_PASSWORD_MATCH={any_match}")
    print(f"OVERALL_SUPER_ADMIN={any_super_admin}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
