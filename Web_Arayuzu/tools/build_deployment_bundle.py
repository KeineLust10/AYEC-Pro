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
    ".venv",
    "support_backups",
    "uploads",
}
REQUIRED_FILES = {
    "Dockerfile",
    "docker-compose.yml",
    ".env.example",
    "DEPLOYMENT.md",
    "Main.py",
    "web/index.html",
    "web/app.js",
}


def should_include(relative_path: Path) -> bool:
    parts = relative_path.parts
    if any(part in EXCLUDED_DIRS or part.startswith(("Kullan", ".venv-")) for part in parts):
        return False
    name = relative_path.name
    if name == ".env":
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
    for current, directories, filenames in os.walk(package_root):
        current_path = Path(current)
        directories[:] = [name for name in directories
                          if should_include((current_path / name).relative_to(package_root))]
        files.extend(current_path / name for name in filenames
                     if not (current_path / name).is_symlink()
                     and should_include((current_path / name).relative_to(package_root))
                     and (current_path / name).resolve() != output_path)
    files.sort()
    names = {path.relative_to(package_root).as_posix() for path in files}
    missing = sorted(REQUIRED_FILES - names)
    if missing:
        raise FileNotFoundError("Deployment package is missing: " + ", ".join(missing))

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in files:
            relative = path.relative_to(package_root).as_posix()
            archive.write(path, (package_root.name + "/" + relative))

    with zipfile.ZipFile(output_path) as archive:
        bad_member = archive.testzip()
        members = archive.namelist()
    if bad_member:
        output_path.unlink(missing_ok=True)
        raise zipfile.BadZipFile("Invalid deployment archive member: " + bad_member)

    forbidden = [name for name in members if not should_include(Path(name).relative_to(package_root.name))]
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
