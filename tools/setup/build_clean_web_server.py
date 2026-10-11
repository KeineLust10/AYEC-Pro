from __future__ import annotations

import hashlib
import shutil
import tempfile
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "Web_Arayuzu"
OUTPUT = ROOT / "Setup_Output"
PACKAGE_NAME = "AYECPro_Web_Server_TEMIZ_KURULUM"
FILES = (
    "Main.py",
    "central_entitlements.py",
    ".env.example",
    "requirements.txt",
    "requirements-ocr.txt",
    "requirements-paddle.txt",
    "server-windows-start.ps1",
    "server-windows-install.ps1",
    "BACKUP_BEFORE_WIPE.cmd",
    "BACKUP_BEFORE_WIPE.ps1",
    "CLEAN_INSTALL.cmd",
    "CLEAN_INSTALL.ps1",
    "ONE_CLICK_CLEAN_INSTALL.cmd",
    "ONE_CLICK_CLEAN_INSTALL.ps1",
    "FIX_ADMIN_LOGIN.cmd",
    "FIX_ADMIN_LOGIN.ps1",
    "sync_tenant_registry.py",
    "check_admin_login_runtime.py",
)
DATA_DIRECTORIES = (
    "Kullan" + chr(0x0131) + "c" + chr(0x0131) + "lar",
    "backups",
    "support_backups",
    "deleted_tenants",
    "artifacts",
    "plugins",
    "ocr-models",
    "logs",
    "config",
)
README = """AYEC Pro Web Server - Clean Windows install

IMPORTANT: Do not delete C:\\Web_Arayuzu until the backup is complete and copied
to a second location. The backup includes shared licenses, tenant databases,
backup archives, signing material, service configuration, uploads, program
backup mirrors and public downloads.

1. Extract this package to a temporary folder outside C:\\Web_Arayuzu.
2. Double-click ONE_CLICK_CLEAN_INSTALL.cmd and approve the Administrator prompt.
3. Enter the admin password when asked, or press Enter to skip that check.
4. Wait for backup, restore, installation, and service health checks to finish.
5. Keep the C:\\AYEC_MIGRATION_BACKUP_* folder until the server is confirmed.
   If backup or installation fails, the installer restores prior server files.
6. The installer removes old application files only after all checks pass.
   Windows, IIS and IIS certificate bindings stay in place.

The clean package contains application code and installer files only. Production
databases, .env, license-signing-key.pem and customer backups are restored from
the migration backup and are never embedded in this ZIP.

Shared ecosystem contract:
- ecosystem\\products.json is the product catalog for all programs.
- data\\ayecpro.db is the shared license and tenant registry.
- Tenant databases are isolated by the registry.
- Product archives retain product, tenant, device and installation identity.
- The existing IIS HTTPS bindings stay on the server; the installer reconnects
  IIS to the local AYEC service on port 8501.

Default shared-data paths copied by the backup script are
C:\\AYECPro Programlar and C:\\Downloads. Set machine environment variables
AYEC_PROGRAM_BACKUP_ROOT or AYEC_DOWNLOADS_DIR if this server uses other paths.
"""


def copy_tree(source: Path, destination: Path, *, exclude_uploads: bool = False) -> None:
    ignored = {"__pycache__", "*.pyc", "*.pyo", ".DS_Store"}
    if exclude_uploads:
        ignored.add("uploads")
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns(*ignored))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build() -> Path:
    if not (WEB / "data" / "demo_template.db").is_file():
        raise RuntimeError("The clean server database template is missing.")
    for name in FILES:
        if not (WEB / name).is_file():
            raise RuntimeError(f"Required server file is missing: {name}")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with tempfile.TemporaryDirectory(prefix="ayec-clean-server-") as temp_name:
        stage = Path(temp_name) / "AYECPro_Web_Server"
        stage.mkdir()
        for name in FILES:
            shutil.copy2(WEB / name, stage / name)

        copy_tree(WEB / "web", stage / "web", exclude_uploads=True)
        (stage / "web" / "uploads").mkdir(parents=True, exist_ok=True)
        copy_tree(WEB / "iis", stage / "iis")
        (stage / "tools").mkdir()
        shutil.copy2(WEB / "tools" / "repair_database.py", stage / "tools" / "repair_database.py")

        (stage / "ecosystem").mkdir()
        shutil.copy2(ROOT / "ecosystem" / "products.json", stage / "ecosystem" / "products.json")
        copy_tree(ROOT / "ecosystem" / "src" / "ayec_core", stage / "ayec_core")
        (stage / "data").mkdir()
        shutil.copy2(WEB / "data" / "demo_template.db", stage / "data" / "demo_template.db")
        for name in DATA_DIRECTORIES:
            (stage / name).mkdir(exist_ok=True)

        (stage / "SERVER_CLEAN_INSTALL.txt").write_text(README, encoding="ascii")
        archive = shutil.make_archive(
            str(OUTPUT / f"{PACKAGE_NAME}_{stamp}"), "zip", stage.parent, stage.name
        )
        archive_path = Path(archive)
        digest_path = OUTPUT / f"{PACKAGE_NAME}_{stamp}.sha256.txt"
        digest_path.write_text(
            f"{sha256(archive_path)}  {archive_path.name}\n", encoding="ascii"
        )

    return archive_path


if __name__ == "__main__":
    result = build()
    print(result)
