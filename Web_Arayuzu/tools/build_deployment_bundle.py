"""Create a clean AYEC Pro web deployment archive without local state."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import zipfile
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "artifacts",
    "backups",
    "data",
    "downloads",
    "node_modules",
    "output",
    ".venv",
    "support_backups",
    "uploads",
}
EXCLUDED_FILES = {
    "BACKUP_BEFORE_WIPE.cmd",
    "BACKUP_BEFORE_WIPE.ps1",
    "CHECK_ADMIN_LOGIN.cmd",
    "CHECK_ADMIN_LOGIN.ps1",
    "CLEAN_INSTALL.cmd",
    "CLEAN_INSTALL.ps1",
    "CLEANUP_SERVER.ps1",
    "FIX_ADMIN_LOGIN.cmd",
    "FIX_ADMIN_LOGIN.ps1",
    "ONE_CLICK_CLEAN_INSTALL.cmd",
    "ONE_CLICK_CLEAN_INSTALL.ps1",
    "RESET_ADMIN_PASSWORD.cmd",
}
REQUIRED_FILES = {
    "Dockerfile",
    "docker-compose.yml",
    ".env.example",
    "DEPLOYMENT.md",
    "CONFIGURE_GOOGLE_SIGNIN.cmd",
    "Main.py",
    "tools/configure_google_oauth.py",
    "tools/diagnose_server_502.ps1",
    "web/index.html",
    "web/app.js",
}
PRIVATE_KEY_SUFFIXES = (".key", ".p12", ".pfx")
PRIVATE_KEY_FILENAMES = {"license-signing-key.pem", "private-key.pem", "private_key.pem", "id_rsa", "id_ed25519"}


def should_include(relative_path: Path) -> bool:
    parts = relative_path.parts
    if any(part in EXCLUDED_DIRS or part.startswith(("Kullan", ".venv-")) for part in parts):
        return False
    if relative_path.as_posix() in EXCLUDED_FILES:
        return False
    name = relative_path.name
    if name == ".env":
        return False
    if name.lower() in PRIVATE_KEY_FILENAMES or name.lower().endswith(PRIVATE_KEY_SUFFIXES):
        return False
    if name.lower().endswith(".zip"):
        return False
    if name.startswith(".env.") and name != ".env.example":
        return False
    if name.endswith((".pyc", ".pyo", ".log", ".db", ".db-shm", ".db-wal", ".sqlite", ".sqlite3")):
        return False
    if any(fnmatch.fnmatch(name, pattern) for pattern in ("*.db-*", "*.sqlite-*")):
        return False
    return True


def build_bundle(package_root: Path, output_path: Path) -> dict[str, object]:
    package_root = package_root.resolve()
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    files = []
    source_root = package_root.parent / "src"
    roots = [(package_root, package_root.name)]
    if (source_root / "__init__.py").is_file():
        roots.append((source_root, f"{package_root.name}/src"))
    for walk_root, archive_root in roots:
        for current, directories, filenames in os.walk(walk_root):
            current_path = Path(current)
            directories[:] = [name for name in directories
                              if should_include((current_path / name).relative_to(walk_root))]
            files.extend(
                (current_path / name, archive_root + "/" + (current_path / name).relative_to(walk_root).as_posix())
                for name in filenames
                if not (current_path / name).is_symlink()
                and should_include((current_path / name).relative_to(walk_root))
                and (current_path / name).resolve() != output_path
            )
    files.sort(key=lambda item: item[1])
    names = {archive_name.removeprefix(package_root.name + "/") for _, archive_name in files}
    names.update(archive_name for _, archive_name in files if archive_name.startswith(package_root.name + "/src/"))
    missing = sorted(REQUIRED_FILES - names)
    if missing:
        raise FileNotFoundError("Deployment package is missing: " + ", ".join(missing))

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path, archive_name in files:
            archive.write(path, archive_name)

    with zipfile.ZipFile(output_path) as archive:
        bad_member = archive.testzip()
        members = archive.namelist()
    if bad_member:
        output_path.unlink(missing_ok=True)
        raise zipfile.BadZipFile("Invalid deployment archive member: " + bad_member)

    forbidden = [name for name in members if not should_include(Path(name).relative_to(package_root.name))]
    required_runtime = {
        f"{package_root.name}/src/__init__.py",
        f"{package_root.name}/src/database.py",
        f"{package_root.name}/src/utils/finance_manager.py",
    }
    missing_runtime = sorted(required_runtime - set(members))
    if missing_runtime:
        output_path.unlink(missing_ok=True)
        raise FileNotFoundError("Deployment package is missing runtime modules: " + ", ".join(missing_runtime))
    if forbidden:
        output_path.unlink(missing_ok=True)
        raise ValueError("Local state found in deployment archive: " + ", ".join(forbidden[:5]))
    return {"archive": str(output_path), "files": len(members), "bytes": output_path.stat().st_size}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path,
                        default=PACKAGE_ROOT.parent / "dist" / "AYEC_Pro_Web_Server.zip")
    args = parser.parse_args()
    print(json.dumps(build_bundle(PACKAGE_ROOT, args.output), ensure_ascii=True))


if __name__ == "__main__":
    main()
