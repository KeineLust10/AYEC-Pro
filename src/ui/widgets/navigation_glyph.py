"""Offline stroke icons for the reference navigation system."""

from PyQt6.QtCore import QByteArray, QRectF, Qt
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QLabel

from src.utils.theme_colors import qc


PAGE_KINDS = {
    10: 'person', 21: 'person', 25: 'document', 26: 'link', 30: 'calendar',
    40: 'chart', 41: 'board', 42: 'clipboard', 50: 'box', 51: 'store',
    60: 'tool', 61: 'map', 62: 'person', 65: 'truck', 66: 'inbox',
    70: 'support', 90: 'bell', 100: 'money', 101: 'money', 105: 'bank', 106: 'card',
    111: 'pin', 115: 'calculator', 120: 'megaphone', 130: 'settings',
    135: 'document', 140: 'tool', 145: 'tag', 146: 'folder',
    147: 'message', 160: 'book', 170: 'robot', 180: 'save', 200: 'folder',
    201: 'chart', 202: 'archive', 250: 'phone', 260: 'book', 261: 'help',
    300: 'monitor', 313: 'document', 314: 'chart', 150: 'cart',
}

SYMBOL_KINDS = {
    '\U0001f504': 'refresh',
    '\U0001f50d': 'search',
    '\U0001f4cc': 'thumbtack',
    '\U0001f527': 'tool', '\U0001f6e0': 'tool', '\u2699': 'settings',
    '\U0001f465': 'people', '\U0001f464': 'person', '\U0001f4e6': 'box',
    '\U0001f4c2': 'folder', '\U0001f4c1': 'folder', '\U0001f4c4': 'document',
    '\U0001f4b8': 'money', '\U0001f3e6': 'bank', '\U0001f4ca': 'chart',
    '\U0001f4cb': 'clipboard', '\U0001f916': 'robot', '\U0001f4bb': 'monitor',
    '\U0001f5a5': 'monitor', '\U0001f4f1': 'phone', '\U0001f3e0': 'home',
    '\U0001f6d2': 'cart', '\U0001f9e9': 'tag', '\U0001f4bc': 'folder',
    '\U0001f50c': 'plug',
    '\U0001f4b0': 'money', '\U0001f4b3': 'card',
    '\U0001f468': 'person', '\U0001f4da': 'book', '\U0001f4d8': 'book',
    '\U0001f4be': 'save', '\U0001f198': 'support', '\U0001f514': 'bell',
}

PATHS = {
    'clock': '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    'copy': '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3"/>',
    'printer': '<path d="M6 9V3h12v6M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><path d="M6 14h12v7H6zM18 12h.01"/>',
    'send': '<path d="M22 2 11 13"/><path d="m22 2-7 20-4-9-9-4 20-7z"/>',
    'filter': '<path d="M3 5h18l-7 8v5l-4 2v-7L3 5z"/>',
    'search': '<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>',
    'plus_circle': '<circle cx="12" cy="12" r="9"/><path d="M12 8v8M8 12h8"/>',
    'plus': '<path d="M12 5v14M5 12h14"/>',
    'refresh': '<path d="M20 7a8 8 0 0 0-13-3L3 8m0-5v5h5M4 17a8 8 0 0 0 13 3l4-4m0 5v-5h-5"/>',
    'building': '<rect x="5" y="3" width="14" height="18" rx="1"/><path d="M9 7h1m4 0h1m-6 4h1m4 0h1m-6 4h1m4 0h1M10 21v-3h4v3"/>',
    'globe': '<circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18M5 7h14M5 17h14"/>',
    'percent': '<path d="m5 19 14-14"/><circle cx="6" cy="6" r="3"/><circle cx="18" cy="18" r="3"/>',
    'palette': '<path d="M12 3a9 9 0 1 0 0 18h1a2 2 0 0 0 1-4c-2-1-1-3 1-3h3a3 3 0 0 0 3-3 9 9 0 0 0-9-8z"/><path d="M7 9h.01M10 6h.01M15 6h.01M18 9h.01"/>',
    'plug': '<path d="M8 3v5m8-5v5M6 8h12v3a6 6 0 0 1-12 0V8zm6 9v4"/>',
    'pencil': '<path d="m3 21 2-7L16 3l5 5L10 19l-7 2zm11-16 5 5M5 14l5 5"/>',
    'trash': '<path d="M3 6h18m-2 0-1 15H6L5 6m4 0V4h6v2m-5 4v7m4-7v7"/>',
    'shield': '<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6l8-3zm-4 9 3 3 5-6"/>',
    'lock': '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3m-4 5v2"/>',
    'chevron_right': '<path d="m9 5 7 7-7 7"/>',
    'chevron_down': '<path d="m5 9 7 7 7-7"/>',
    'more_vertical': '<circle cx="12" cy="5" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="12" cy="19" r="1"/>',
    'north_east': '<path d="M7 17 17 7M8 7h9v9"/>',
    'wallet': '<rect x="3" y="5" width="18" height="15" rx="2"/><path d="M3 8h18m-6 4h4"/>',
    'verified': '<path d="m12 3 7 3v6c0 4-7 9-7 9s-7-5-7-9V6l7-3z"/><path d="m9 12 2 2 4-4"/>',
    'chart': '<path d="M4 3v17h17M8 16v-5m5 5V7m5 9V4"/>',
    'clipboard': '<rect x="5" y="4" width="14" height="17" rx="2"/><rect x="9" y="2" width="6" height="4" rx="1"/><path d="M9 11h6m-6 4h6"/>',
    'board': '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16m6-16v16M6 8v4m6-4v7m6-7v4"/>',
    'tool': '<path d="M14 3a6 6 0 0 0-7 7L3 16a3 3 0 0 0 5 4l5-6a6 6 0 0 0 7-7l-4 4-3-3 4-4z"/>',
    'map': '<path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3V6zm6-3v15m6-12v15"/>',
    'calendar': '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4m10-4v4M3 10h18m-14 4h2m4 0h2m-8 4h2"/>',
    'cart': '<path d="M2 3h3l3 13h11l3-10H6M10 21h.01M18 21h.01"/>',
    'tag': '<path d="M3 3h8l10 10-8 8L3 11V3z"/><circle cx="7" cy="7" r="1"/>',
    'truck': '<path d="M3 5h12v12H3V5zm12 4h4l3 4v4h-7"/><circle cx="7" cy="18" r="2"/><circle cx="18" cy="18" r="2"/>',
    'robot': '<rect x="4" y="7" width="16" height="13" rx="3"/><path d="M12 3v4M1 11v5m22-5v5M9 16h6"/><circle cx="8" cy="11" r="1"/><circle cx="16" cy="11" r="1"/>',
    'monitor': '<rect x="3" y="3" width="18" height="14" rx="2"/><path d="M12 17v4m-5 0h10"/>',
    'person': '<circle cx="12" cy="7" r="4"/><path d="M4 21v-3a8 8 0 0 1 16 0v3"/>',
    'people': '<circle cx="9" cy="7" r="3"/><path d="M2 21v-3a7 7 0 0 1 14 0v3M17 4a3 3 0 0 1 0 6m2 4a6 6 0 0 1 3 5v2"/>',
    'document': '<path d="M5 3h9l5 5v13H5V3zm9 0v6h5M8 13h8m-8 4h6"/>',
    'message': '<path d="M3 3h18v14H9l-6 4V3zM7 8h10M7 12h7"/>',
    'bell': '<path d="M5 17h14l-2-3V9a5 5 0 0 0-10 0v5l-2 3zm4 3a3 3 0 0 0 6 0M12 2v2"/>',
    'megaphone': '<path d="M3 9h5l12-5v16L8 15H3V9zm5 6 2 6h4l-3-5M8 9v6"/>',
    'link': '<path d="m9 15 6-6m-5-3 3-3a5 5 0 0 1 7 7l-3 3m-3 5-3 3a5 5 0 0 1-7-7l3-3"/>',
    'box': '<path d="m3 7 9-4 9 4v11l-9 4-9-4V7zm0 0 9 4 9-4M12 11v11M7 5l10 4"/>',
    'inbox': '<path d="M3 4h18v16H3V4zm0 10h5l2 3h4l2-3h5"/>',
    'folder': '<path d="M3 5h7l2 3h9v13H3V5z"/>',
    'archive': '<rect x="3" y="3" width="18" height="5" rx="1"/><path d="M5 8v13h14V8M9 12h6"/>',
    'money': '<rect x="2" y="5" width="20" height="14" rx="2"/><circle cx="12" cy="12" r="3"/><path d="M5 9v6m14-6v6"/>',
    'bank': '<path d="m2 8 10-6 10 6H2zm2 4v6m5-6v6m6-6v6m5-6v6M2 22h20M3 19h18"/>',
    'card': '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="M2 9h20M6 16h4"/>',
    'calculator': '<rect x="5" y="2" width="14" height="20" rx="2"/><path d="M8 6h8m-8 5h1m3 0h1m3 0h1m-9 4h1m3 0h1m3 0h1m-9 4h1m3 0h5"/>',
    'pin': '<path d="M19 9c0 5-7 13-7 13S5 14 5 9a7 7 0 0 1 14 0z"/><circle cx="12" cy="9" r="2"/>',
    'thumbtack': '<path d="m9 3 12 12-3 3-4-2-4 4-1-1 4-4-2-4-5-5 3-3zM9 15l-6 6"/>',
    'phone': '<rect x="6" y="2" width="12" height="20" rx="2"/><path d="M10 5h4M11 19h2"/>',
    'book': '<path d="M3 3h7l2 2 2-2h7v17h-7l-2 2-2-2H3V3zm9 2v17M6 7h3m6 0h3M6 11h3m6 0h3"/>',
    'help': '<circle cx="12" cy="12" r="10"/><path d="M9 8a3 3 0 0 1 6 0c0 2-3 2-3 5m0 4h.01"/>',
    'settings': '<circle cx="12" cy="12" r="4"/><path d="M10 2h4l1 3 3 1 3-1 2 4-2 2v3l2 2-2 4-3-1-3 1-1 3h-4l-1-3-3-1-3 1-2-4 2-2v-3L1 9l2-4 3 1 3-1 1-3z"/>',
    'save': '<path d="M3 3h15l3 3v15H3V3zm4 0v6h10V3M7 21v-8h10v8"/>',
    'support': '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="4"/><path d="m5 5 4 4m6 6 4 4M5 19l4-4m6-6 4-4"/>',
    'store': '<path d="M3 9 5 3h14l2 6M3 9v12h18V9M8 21v-7h8v7M3 9h18"/>',
    'home': '<path d="m2 11 10-9 10 9M5 9v13h14V9M9 22v-8h6v8"/>',
}


def navigation_icon(kind, size=18, normal_token='text_muted'):
    """Build local SVG icons for all item states without an emoji font."""
    icon = QIcon()
    for mode, token in ((QIcon.Mode.Normal, normal_token),
                        (QIcon.Mode.Selected, 'selection_text'),
                        (QIcon.Mode.Disabled, 'border')):
        color = QColor(token).name() if token.startswith('#') else qc(token).name()
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
               'fill="none" stroke="' + color + '" stroke-width="1.7" '
               'stroke-linecap="round" stroke-linejoin="round">' + PATHS[kind] + '</svg>')
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer = QSvgRenderer(QByteArray(svg.encode('ascii')))
        renderer.render(painter)
        painter.end()
        icon.addPixmap(pixmap, mode)
    return icon


class NavigationGlyph(QLabel):
    def __init__(self, legacy_symbol='', *, page_id=None, title='', active_token='selection_text'):
        super().__init__(str(legacy_symbol))
        symbol = str(legacy_symbol).replace('\ufe0f', '')
        self.kind = PAGE_KINDS.get(page_id) or SYMBOL_KINDS.get(symbol)
        self.active_token = active_token
        self.custom_color = None
        self.active = False
        self.disabled = False
        self._renderer = None
        self._render_key = None
        self.setAccessibleName(title)

    def set_navigation_state(self, active=False, disabled=False):
        self.active = bool(active)
        self.disabled = bool(disabled)
        self.update()

    def set_render_color(self, color):
        self.custom_color = str(color or "") or None
        self._render_key = None
        self.update()

    def paintEvent(self, event):
        if self.kind not in PATHS:
            super().paintEvent(event)
            return
        color = QColor(self.custom_color).name() if self.custom_color and self.active else qc(
            'border' if self.disabled or not self.isEnabled() else self.active_token if self.active else 'text_muted'
        ).name()
        key = (self.kind, color)
        if self._render_key != key:
            svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
                   'fill="none" stroke="' + color + '" stroke-width="1.7" '
                   'stroke-linecap="round" stroke-linejoin="round">' + PATHS[self.kind] + '</svg>')
            if self._renderer is not None:
                self._renderer.deleteLater()
            self._renderer = QSvgRenderer(QByteArray(svg.encode('ascii')), self)
            self._render_key = key
        size = max(1, min(18, self.width() - 2, self.height() - 2))
        target = QRectF((self.width() - size) / 2, (self.height() - size) / 2, size, size)
        painter = QPainter(self)
        self._renderer.render(painter, target)
        painter.end()


class NavigationChevron(NavigationGlyph):
    """Keep legacy state text while painting a stroke disclosure indicator."""

    def __init__(self, text='>'):
        super().__init__(text, active_token='accent')
        self.setText(text)

    def setText(self, text):
        super().setText(text)
        self.kind = 'chevron_down' if text == 'v' else 'chevron_right'
        self.set_navigation_state(text == 'v')
