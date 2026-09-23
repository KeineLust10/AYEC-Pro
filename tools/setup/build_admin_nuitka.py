"""Build the AYEC Pro Admin Console as a portable native executable."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ADMIN_ROOT = ROOT / "Admin_Konsol"
BUILD_ROOT = ROOT / "admin_nuitka_build"
OUTPUT = ROOT / "Setup_Output" / "AYECPro_Admin_Console.exe"


def main() -> int:
    if BUILD_ROOT.exists():
        shutil.rmtree(BUILD_ROOT)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    python_path = ROOT / ".venv_active" / "Scripts" / "python.exe"
    if not python_path.is_file():
        python_path = Path(sys.executable)

    command = [
        str(python_path),
        "-m",
        "nuitka",
        "--onefile",
        "--jobs=4",
        "--enable-plugin=pyqt6",
        "--windows-console-mode=disable",
        "--assume-yes-for-downloads",
        "--include-package=pages",
        "--include-package=requests",
        "--include-data-dir=assets=assets",
        f"--include-data-files={ROOT / 'ecosystem' / 'products.json'}=ecosystem/products.json",
        "--windows-icon-from-ico=assets/admin_icon.ico",
        "--output-filename=AYECPro_Admin_Console.exe",
        f"--output-dir={BUILD_ROOT}",
        "main.py",
    ]
    subprocess.run(command, cwd=ADMIN_ROOT, check=True)

    source = BUILD_ROOT / "AYECPro_Admin_Console.exe"
    if not source.is_file():
        raise RuntimeError("Admin console build output was not created.")
    shutil.copy2(source, OUTPUT)
    print(f"Admin console created: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
