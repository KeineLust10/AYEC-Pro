# -*- coding: utf-8 -*-
# _side_menu_constants.py
# SideMenu sabitleri ve yardımcı fonksiyonlar

import os
from PyQt6.QtWidgets import QApplication
from src.utils.theme_colors import theme_qss


def _is_classic_appearance():
    app = QApplication.instance()
    return bool(app and app.property("appearanceMode") == "classic")


# Legacy page icon map kept intentionally empty.
PAGE_ICONS_LEGACY = {}

PAGE_ICONS = {
    51: "\U0001f3ec",
    62: "\U0001f477",
    146: "\U0001f5c2",
    147: "\U0001f4dd",
    40: "📊",
    41: "📋",
    60: "🔧",
    61: "🗺",
    30: "📅",
    150: "🛒",
    145: "🧩",
    65: "🚚",
    201: "📊",
    170: "🤖",
    300: "🖥",
    21: "👤",
    25: "🧾",
    90: "🔔",
    120: "📢",
    26: "🤝",
    50: "📦",
    140: "🛠",
    66: "📥",
    250: "📱",
    200: "📂",
    202: "🗄",
    101: "💸",
    105: "🏦",
    106: "💳",
    115: "🧮",
    10: "👨",
    111: "📍",
    260: "📘",
    160: "📚",
    261: "❓",
    130: "⚙",
    135: "📝",
    180: "💾",
    70: "🆘",
    313: "\U0001f4c4",
    314: "\U0001f4c8",
}


class DesignTokens:
    # Use semantic tokens directly so colors always follow live theme changes
    SIDEBAR_BG_START = "@window"
    SIDEBAR_BG_END = "@surface_alt"
    SIDEBAR_BG = "@surface"
    HEADER_BG = "@surface"
    TEXT_COLOR = "@text"
    SUBTEXT_COLOR = "@text_muted"
    HOVER_COLOR = "@surface_alt"
    HOVER_ACCENT = "@accent_hover"
    ACTIVE_COLOR = "@selection_bg"
    ACTIVE_TEXT = "@selection_text"
    BORDER_COLOR = "@border"
    GOLD_ACCENT = "@warning"
    CARD_BG = "@surface_alt"
    CARD_BG_SOFT = "@surface"
    SECTION_TEXT = "@text_muted"
    ICON_BG = "@surface_alt"
    ICON_ACTIVE_BG = "@accent"
    ICON_ACTIVE_TEXT = "@selection_text"
    SECTION_BG = "@surface"
    SECTION_BORDER = "@border"
    HEADER_BADGE_BG = "@surface_alt"
    HEADER_BADGE_TEXT = "@text"
    FOOTER_SOFT_BG = "@surface"
    SECTION_PILL_BG = "@surface"
    SECTION_PILL_TEXT = "@text_muted"
    SECTION_PILL_BORDER = "@border"
    CHILD_ACTIVE_BAR = "@accent"
