import sqlite3
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPAIR_SCRIPT = ROOT / "Web_Arayuzu" / "onarim.py"


def _prepare_server_database(root: Path, include_vendor: bool) -> Path:
    (root / "data").mkdir()
    tenants = root / "Kullan\u0131c\u0131lar"
    tenants.mkdir()
    with sqlite3.connect(root / "data" / "ayecpro.db"):
        pass
    tenant_db = tenants / "example.db"
    with sqlite3.connect(tenant_db) as connection:
        connection.execute(
            "CREATE TABLE company_info (company_name TEXT)"
        )
        connection.execute(
            "INSERT INTO company_info(company_name) VALUES (?)", ("Example",)
        )
        connection.execute(
            "CREATE TABLE users ("
            "id INTEGER PRIMARY KEY, username TEXT, email TEXT, password TEXT, "
            "role TEXT, active INTEGER)"
        )
        if include_vendor:
            connection.execute(
                "INSERT INTO users VALUES (1,?,?,?,?,?)",
                ("ayecpro", "ayecpro@gmail.com", "original-hash", "admin", 1),
            )
        else:
            connection.execute(
                "INSERT INTO users VALUES (1,?,?,?,?,?)",
                ("owner", "owner@example.com", "owner-hash", "admin", 1),
            )
    return tenant_db


def test_repair_preserves_existing_user_and_password(tmp_path):
    tenant_db = _prepare_server_database(tmp_path, include_vendor=True)

    subprocess.run(
        [sys.executable, str(REPAIR_SCRIPT)],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    with sqlite3.connect(tenant_db) as connection:
        users = connection.execute("SELECT username, password FROM users").fetchall()
    assert users == [("ayecpro", "original-hash")]


def test_repair_does_not_create_missing_vendor_user(tmp_path):
    tenant_db = _prepare_server_database(tmp_path, include_vendor=False)

    subprocess.run(
        [sys.executable, str(REPAIR_SCRIPT)],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    with sqlite3.connect(tenant_db) as connection:
        users = connection.execute("SELECT username, password FROM users").fetchall()
    assert users == [("owner", "owner-hash")]
