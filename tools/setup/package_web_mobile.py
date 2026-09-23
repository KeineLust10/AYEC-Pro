"""Create clean deployable AYEC Pro Web and Mobile release archives."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "Setup_Output"
WEB_ROOT = ROOT / "Web_Arayuzu"
MOBILE_ROOT = ROOT / "premium-field-app"
DESKTOP_VERSION = (ROOT / "version.txt").read_text(encoding="ascii").strip()
WEB_RUNTIME_UTILS = {
    "pdf_manager.py",
    "logger.py",
    "date_utils.py",
    "service_work_details.py",
    "stock_import_parser.py",
}


def copy_tree(source: Path, destination: Path, ignored: set[str]) -> None:
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns(*sorted(ignored)),
        dirs_exist_ok=True,
    )


def archive_directory(source: Path, target_base: Path) -> Path:
    archive = shutil.make_archive(str(target_base), "zip", source.parent, source.name)
    return Path(archive)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def copy_web_runtime(destination: Path) -> None:
    """Copy the stock import and PDF runtime required by the web server."""
    source_package = ROOT / "src"
    source_utils = source_package / "utils"
    target_package = destination / "src"
    target_utils = target_package / "utils"
    target_utils.mkdir(parents=True, exist_ok=True)
    (destination / "ecosystem").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "ecosystem" / "products.json", destination / "ecosystem" / "products.json")
    shutil.copy2(source_package / "__init__.py", target_package / "__init__.py")
    shutil.copy2(source_utils / "__init__.py", target_utils / "__init__.py")
    runtime_files = {
        *(source_utils / name for name in WEB_RUNTIME_UTILS),
        *source_utils.glob("_sip_*.py"),
        *source_utils.glob("_pdf_*_mixin.py"),
    }
    for source in sorted(runtime_files):
        shutil.copy2(source, target_utils / source.name)
    copy_tree(
        ROOT / "ecosystem" / "src" / "ayec_core",
        destination / "ayec_core",
        {"__pycache__", "*.pyc"},
    )


def main() -> int:
    if not WEB_ROOT.is_dir():
        raise RuntimeError("Web source directory was not found.")
    if not MOBILE_ROOT.is_dir():
        raise RuntimeError("Mobile source directory was not found.")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with tempfile.TemporaryDirectory(prefix="ayec-release-") as temp_text:
        temp = Path(temp_text)
        web_stage = temp / "AYECPro_Web_Server"
        web_stage.mkdir()
        for filename in (
            "Main.py",
            ".env.example",
            "requirements.txt",
            "requirements-ocr.txt",
            "requirements-paddle.txt",
            "server-windows-start.ps1",
            "server-windows-install.ps1",
            "AYEC_START.cmd",
            "AYEC_START.ps1",
            "setup_server.sh",
            "start_server.sh",
        ):
            shutil.copy2(WEB_ROOT / filename, web_stage / filename)
        for filename in ("configure_official_services.py", "CONFIGURE_AYEC_OFFICIAL_SERVICES.cmd"):
            shutil.copy2(ROOT / "tools" / "setup" / filename, web_stage / filename)
        copy_tree(WEB_ROOT / "web", web_stage / "web", {"__pycache__", "*.pyc"})
        copy_tree(WEB_ROOT / "iis", web_stage / "iis", {"__pycache__", "*.pyc"})
        copy_tree(
            WEB_ROOT / "tools",
            web_stage / "tools",
            {"__pycache__", "*.pyc", "*.log"},
        )
        (web_stage / "data").mkdir(parents=True, exist_ok=True)
        shutil.copy2(WEB_ROOT / "data" / "demo_template.db", web_stage / "data" / "demo_template.db")
        copy_web_runtime(web_stage)
        deploy_readme = web_stage / "DEPLOYMENT.txt"
        deploy_readme.write_text(
            "AYEC Pro Web Server\n\n"
            "1. Extract this archive to C:\\Web_Arayuzu.\n"
            "2. Create .venv with the required Python version.\n"
            "3. Run: .venv\\Scripts\\python.exe -m pip install -r requirements.txt\n"
            "4. Copy the production ayecpro.db into data\\ayecpro.db.\n"
            "5. Double-click AYEC_START.cmd. It prepares the runtime, resets the Admin password, and starts the Web server.\n\n"
            "Set AYEC_PUBLIC_URL=https://panel.ayecpro.com in the server environment.\n"
            "Set AYEC_LICENSE_API_URL=https://lisans.ayecpro.com for license checks.\n"
            "Bind panel.ayecpro.com and lisans.ayecpro.com to HTTPS in IIS before enabling public login.\n\n"
            "Public program downloads are served from C:\\Downloads by default.\n"
            "Use these exact filenames: AnyDesk.exe, AYECPro.exe, SmartPSS.exe, ConfigTools.exe.\n"
            "To use another directory, set AYEC_DOWNLOADS_DIR before starting the server.\n\n"
            "Do not copy tenant database files manually. The desktop client syncs them through the server API.\n"
            "Run CONFIGURE_AYEC_OFFICIAL_SERVICES.cmd after deployment to configure official SMTP and Google sign-in.\n",
            encoding="ascii",
        )
        web_archive = archive_directory(web_stage, OUTPUT / f"AYECPro_Web_Server_{stamp}")

        mobile_stage = temp / "AYECPro_Mobile"
        copy_tree(
            MOBILE_ROOT,
            mobile_stage,
            {
                "node_modules",
                ".expo",
                ".git",
                "__pycache__",
                "*.pyc",
                "*.log",
                ".env",
                ".expo-build-check",
                ".expo-web-check",
            },
        )
        mobile_archive = archive_directory(mobile_stage, OUTPUT / f"AYECPro_Mobile_{stamp}")

    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "web_package": {"name": web_archive.name, "sha256": sha256(web_archive)},
        "mobile_package": {"name": mobile_archive.name, "sha256": sha256(mobile_archive)},
        "desktop_installer": f"AYECPro_Setup_v{DESKTOP_VERSION}_Final.exe",
        "admin_console": "AYECPro_Admin_Console.exe",
    }
    manifest_path = OUTPUT / f"AYECPro_Release_Manifest_{stamp}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="ascii")
    print(f"Web package created: {web_archive}")
    print(f"Mobile package created: {mobile_archive}")
    print(f"Release manifest created: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
