# -*- coding: utf-8 -*-
import re
from PyQt6.QtGui import QColor
from ._theme_constants import (
    NEUTRAL_HEX_RE,
    VIVID_PALETTE_KEYS,
)


def is_vivid_color(hex_val):
    """Return True if the color is visibly saturated/vivid (not a neutral grey/white/black)."""
    if not hex_val or not str(hex_val).startswith("#"):
        return False
    c = QColor(str(hex_val))
    if not c.isValid():
        return False
    r, g, b = c.red(), c.green(), c.blue()
    return (max(r, g, b) - min(r, g, b)) >= 60


def contrast_text(hex_color):
    color = QColor(hex_color)
    if not color.isValid():
        return "#FFFFFF"
    luminance = (0.299 * color.red()) + (0.587 * color.green()) + (0.114 * color.blue())
    return "#0F172A" if luminance > 170 else "#F8FAFC"


def _relative_luminance(color):
    def channel(value):
        value = value / 255.0
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4

    return (
        0.2126 * channel(color.red())
        + 0.7152 * channel(color.green())
        + 0.0722 * channel(color.blue())
    )


def contrast_ratio(fg, bg):
    fg_color = QColor(fg)
    bg_color = QColor(bg)
    if not fg_color.isValid() or not bg_color.isValid():
        return 0.0
    fg_lum = _relative_luminance(fg_color)
    bg_lum = _relative_luminance(bg_color)
    light = max(fg_lum, bg_lum)
    dark = min(fg_lum, bg_lum)
    return (light + 0.05) / (dark + 0.05)


def is_neutral_value(value):
    if not value:
        return False
    low = value.lower()
    if "white" in low or "black" in low:
        return True
    if "rgb(" in low:
        nums = re.findall(r"\d+", low)
        if len(nums) >= 3:
            r, g, b = [int(n) for n in nums[:3]]
            return abs(r - g) <= 12 and abs(g - b) <= 12
    for hx in NEUTRAL_HEX_RE.findall(low):
        try:
            c = QColor(hx)
            if c.isValid() and abs(c.red() - c.green()) <= 12 and abs(c.green() - c.blue()) <= 12:
                return True
        except Exception:
            continue
    return False

