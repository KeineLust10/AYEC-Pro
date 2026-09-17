"""Small desktop entry helpers that must run before Qt imports."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def ensure_virtual_environment() -> None:
    """Relaunch the desktop entry with the bundled virtual environment."""
    if getattr(sys, "frozen", False) or "RELAUNCHED_IN_VENV" in os.environ:
        return

    base_dir = Path(__file__).resolve().parents[1]
    candidates = (
        base_dir / ".venv_active" / "Scripts" / "python.exe",
        base_dir / ".venv" / "Scripts" / "python.exe",
        base_dir / ".venv_ai" / "Scripts" / "python.exe",
        base_dir / "venv" / "Scripts" / "python.exe",
    )
    for interpreter in candidates:
        if interpreter.is_file() and Path(sys.executable).resolve() != interpreter.resolve():
            os.environ["RELAUNCHED_IN_VENV"] = "1"
            subprocess.call([str(interpreter), *sys.argv])
            raise SystemExit()
