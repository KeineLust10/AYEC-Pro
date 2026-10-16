# -*- coding: utf-8 -*-
"""Load offline reference fonts without depending on installed system fonts."""

import sys
import os
from pathlib import Path

from PyQt6.QtGui import QFont, QFontDatabase


FONT_DIRECTORY = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[2])) / 'assets' / 'fonts'
FONT_FILES = ('Inter-Variable.ttf', 'JetBrainsMono-Regular.ttf')
FONT_EXPECTED_FAMILIES = {'Inter-Variable.ttf': 'Inter', 'JetBrainsMono-Regular.ttf': 'JetBrains Mono'}
_font_ids = {}
_system_fallback_font_ids = {}


def _load_system_fallback_fonts():
    font_dir = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts'
    for family, filename in (('Segoe UI', 'segoeui.ttf'), ('Arial', 'arial.ttf')):
        cached_id = _system_fallback_font_ids.get(family, -1)
        cached_families = QFontDatabase.applicationFontFamilies(cached_id) if cached_id >= 0 else []
        if family in cached_families:
            continue
        font_path = font_dir / filename
        if not font_path.is_file():
            continue
        font_id = QFontDatabase.addApplicationFont(str(font_path))
        if font_id >= 0 and family in QFontDatabase.applicationFontFamilies(font_id):
            _system_fallback_font_ids[family] = font_id


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
    _load_system_fallback_fonts()
    font = QFont(app.font())
    if 'Inter' in families:
        font.setFamilies(['Inter', 'Segoe UI', 'Arial'])
    else:
        font.setFamilies(['Segoe UI', 'Arial', 'Sans Serif'])
    if app.font() != font:
        app.setFont(font)
    return families
