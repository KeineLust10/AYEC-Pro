"""Load system Segoe UI and Arial fonts for offscreen Admin captures."""

from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtGui import QFont, QFontDatabase


def load_system_fallback_fonts() -> set[str]:
    windows_root = Path(os.environ.get("WINDIR", "C:/Windows"))
    font_root = windows_root / "Fonts"
    for filename in ("segoeui.ttf", "arial.ttf"):
        font_path = font_root / filename
        if font_path.is_file():
            QFontDatabase.addApplicationFont(str(font_path))
    families = {family.casefold() for family in QFontDatabase.families()}
    fallback = "Segoe UI" if "segoe ui" in families else "Arial"
    for family in ("Inter", "Plus Jakarta Sans"):
        if family.casefold() not in families:
            QFont.insertSubstitution(family, fallback)
    return families
