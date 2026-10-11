"""Windows shell helpers shared by the desktop and local web settings views."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[2]
SHORTCUT_NAME = "AYEC Pro.lnk"


def _require_windows():
    if os.name != "nt":
        raise OSError("Windows shell actions are available only on Windows.")


def _folder(kind: str) -> Path:
    _require_windows()
    roaming = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    if kind == "startup":
        return roaming / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    if kind == "start-menu":
        return roaming / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    if kind == "desktop":
        desktop = Path.home() / "Desktop"
        try:
            from win32com.shell import shell, shellcon

            desktop = Path(shell.SHGetFolderPath(0, shellcon.CSIDL_DESKTOPDIRECTORY, 0, 0))
        except (ImportError, OSError):
            pass
        return desktop
    raise ValueError("Unknown Windows shortcut location.")


def _app_command() -> tuple[str, str, str]:
    if getattr(sys, "frozen", False):
        target = Path(sys.executable).resolve()
        arguments = ""
    else:
        target = Path(sys.executable).resolve()
        entry = APP_ROOT / "Main.py"
        if not entry.is_file():
            raise FileNotFoundError("The AYEC Pro desktop entry point was not found.")
        arguments = subprocess.list2cmdline([str(entry)])
    if not target.is_file():
        raise FileNotFoundError("The AYEC Pro launch target was not found.")
    return str(target), arguments, str(APP_ROOT)


def create_shortcut(kind: str) -> Path:
    folder = _folder(kind)
    folder.mkdir(parents=True, exist_ok=True)
    target, arguments, working_directory = _app_command()
    from win32com.client import Dispatch

    path = folder / SHORTCUT_NAME
    shortcut = Dispatch("WScript.Shell").CreateShortcut(str(path))
    shortcut.TargetPath = target
    shortcut.Arguments = arguments
    shortcut.WorkingDirectory = working_directory
    shortcut.Description = "AYEC Pro"
    shortcut.IconLocation = target
    shortcut.Save()
    return path


def is_in_windows_startup() -> bool:
    try:
        return (_folder("startup") / SHORTCUT_NAME).is_file()
    except OSError:
        return False


def set_windows_startup(enabled: bool) -> bool:
    path = _folder("startup") / SHORTCUT_NAME
    if enabled:
        create_shortcut("startup")
        return True
    if path.exists():
        path.unlink()
    return False


def open_database_folder(database_path: str | Path) -> None:
    path = Path(database_path).expanduser().resolve()
    if not path.exists():
        path = path.parent
    if os.name == "nt":
        subprocess.Popen(["explorer.exe", "/select,", str(path)])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])
