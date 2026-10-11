# -*- coding: utf-8 -*-
"""Load offline reference fonts without depending on installed system fonts."""

import sys
from pathlib import Path

from PyQt6.QtGui import QFont, QFontDatabase


FONT_DIRECTORY = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[2])) / 'assets' / 'fonts'
FONT_FILES = ('Inter-Variable.ttf', 'JetBrainsMono-Regular.ttf')
FONT_EXPECTED_FAMILIES = {'Inter-Variable.ttf': 'Inter', 'JetBrainsMono-Regular.ttf': 'JetBrains Mono'}
_font_ids = {}


def load_reference_fonts():
    families = []
    for filename in FONT_FILES:
        cached_id = _font_ids.get(filename, -1)
        cached_families = QFontDatabase.applicationFontFamilies(cached_id) if cached_id >= 0 else []
        if FONT_EXPECTED_FAMILIES[filename] not in cached_families:
            font_id = QFontDatabase.addApplicationFont(str(FONT_DIRECTORY / filename))
            if font_id >= 0:
                _font_ids[filename] = font_id
            else:
                _font_ids.pop(filename, None)
        font_id = _font_ids.get(filename, -1)
        families.extend(QFontDatabase.applicationFontFamilies(font_id))
    return tuple(families)


def apply_reference_font(app):
    families = load_reference_fonts()
    font = QFont(app.font())
    if 'Inter' in families:
        font.setFamilies(['Inter', 'Segoe UI', 'Arial'])
    else:
        font.setFamilies(['Segoe UI', 'Arial', 'Sans Serif'])
    if app.font() != font:
        app.setFont(font)
    return families
