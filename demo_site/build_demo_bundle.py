from __future__ import annotations

import argparse
import os
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = PROJECT_ROOT / "Web_Arayuzu"
DEMO_ROOT = PROJECT_ROOT / "demo_site"
EXCLUDED_DIRS = {
    ".git",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "artifacts",
    "backups",
    "downloads",
    "logs",
    "node_modules",
    "output",
    "support_backups",
    "tenants",
    "uploads",
    "venv",
}
PRIVATE_SUFFIXES = {".key", ".pem", ".p12", ".pfx", ".sqlite", ".sqlite3"}
PRIVATE_NAMES = {
    "official-services.json",
    "private_key.pem",
    "private-key.pem",
    "license-signing-key.pem",
}


def include_file(path: Path, archive_name: str) -> bool:
    parts = Path(archive_name).parts
    if any(part in EXCLUDED_DIRS or part.startswith("Kullan") for part in parts):
        return False
    name = path.name
    if name == ".env" or name.startswith(".env.") and name != ".env.example":
        return False
    if name.lower() in PRIVATE_NAMES or path.suffix.lower() in PRIVATE_SUFFIXES:
        return False
    if name.endswith((".pyc", ".pyo", ".log", ".db-shm", ".db-wal")):
        return False
    if path.suffix.lower() == ".db":
        return archive_name == "AYEC_Pro_Demo/Web_Arayuzu/data/demo_template.db"
    if path.suffix.lower() == ".zip":
        return False
    return True


def collect_files() -> list[tuple[Path, str]]:
    files: list[tuple[Path, str]] = []
    roots = [
        (APP_ROOT, "AYEC_Pro_Demo/Web_Arayuzu"),
        (PROJECT_ROOT / "src", "AYEC_Pro_Demo/Web_Arayuzu/src"),
        (DEMO_ROOT, "AYEC_Pro_Demo/demo_site"),
    ]
    for source_root, archive_root in roots:
        if not source_root.is_dir():
            continue
        for current, directories, filenames in os.walk(source_root):
            current_path = Path(current)
            directories[:] = [name for name in directories if name not in EXCLUDED_DIRS]
            for filename in filenames:
                source = current_path / filename
                relative = source.relative_to(source_root).as_posix()
                member = archive_root + "/" + relative
                if source.is_symlink() or not include_file(source, member):
                    continue
                files.append((source, member))
    return sorted(files, key=lambda item: item[1])


def render_static_landing() -> None:
    php_source = (DEMO_ROOT / "index.php").read_text(encoding="utf-8")
    if "?>" not in php_source:
        raise RuntimeError("The PHP landing template has no document boundary.")
    static_html = php_source.split("?>", 1)[1].lstrip()
    static_html = static_html.replace(
        'action="<?= $entryUrl ?>"',
        'action="https://demo-panel.ayecpro.com/api/demo/session"',
    )
    if "<?= " in static_html:
        raise RuntimeError("The static landing page still contains a PHP expression.")
    (DEMO_ROOT / "index.html").write_text(static_html, encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an isolated AYEC Pro demo deployment archive")
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "dist" / "AYECPro_Demo_Server.zip",
    )
    args = parser.parse_args()
    template = APP_ROOT / "data" / "demo_template.db"
    if not template.is_file():
        parser.error("The seeded demo database is missing: " + str(template))
    render_static_landing()
    files = collect_files()
    members = {name for _, name in files}
    required = {
        "AYEC_Pro_Demo/Web_Arayuzu/Main.py",
        "AYEC_Pro_Demo/Web_Arayuzu/data/demo_template.db",
        "AYEC_Pro_Demo/Web_Arayuzu/web/index.html",
        "AYEC_Pro_Demo/demo_site/index.html",
        "AYEC_Pro_Demo/demo_site/auto-start.js",
        "AYEC_Pro_Demo/demo_site/iis-landing.web.config",
        "AYEC_Pro_Demo/demo_site/iis-app.web.config",
    }
    missing = sorted(required - members)
    if missing:
        parser.error("Required deployment files are missing: " + ", ".join(missing))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for source, member in files:
            archive.write(source, member)
    with zipfile.ZipFile(args.output) as archive:
        if archive.testzip() is not None:
            args.output.unlink(missing_ok=True)
            parser.error("Deployment archive validation failed")
    print("Archive: " + str(args.output.resolve()))
    print("Files: " + str(len(files)))
    print("Bytes: " + str(args.output.stat().st_size))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
