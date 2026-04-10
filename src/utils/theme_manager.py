# -*- coding: utf-8 -*-
import json
import re
import weakref
from pathlib import Path
from datetime import datetime
from src.utils.logger import logger

from PyQt6.QtCore import QEvent, QObject, QPropertyAnimation, QEasingCurve, QTimer, Qt, QPoint, QPointF, pyqtProperty
from PyQt6.QtGui import QColor, QPalette, QAction
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QGraphicsOpacityEffect,
    QWidget,
    QAbstractButton,
    QLineEdit,
    QComboBox,
    QGroupBox,
    QTabWidget,
    QTextEdit,
    QTextBrowser,
    QPlainTextEdit,
    QTableWidget,
    QListWidget,
    QTreeWidget,
    QMenu,
)



from src.utils.theme_filters import _StyleChangeFilter, _ComboClickOpenFilter


class _ThemeRevealOverlay(QWidget):
    """Visible shockwave overlay for theme transitions."""

    def __init__(self, parent, origin, color):
        super().__init__(parent)
        self._origin = QPointF(origin)
        self._radius = 0.0
        self._opacity = 0.72
        self._color = QColor(color)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setGeometry(parent.rect())

    def _get_radius(self):
        return self._radius

    def _set_radius(self, value):
        self._radius = float(value)
        self.update()

    radius = pyqtProperty(float, fget=_get_radius, fset=_set_radius)

    def _get_opacity(self):
        return self._opacity

    def _set_opacity(self, value):
        self._opacity = float(value)
        self.update()

    rippleOpacity = pyqtProperty(float, fget=_get_opacity, fset=_set_opacity)

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter, QPen

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        glow_fill = QColor(self._color)
        glow_fill.setAlphaF(max(0.0, min(1.0, self._opacity * 0.34)))
        stroke = QColor(self._color)
        stroke.setAlphaF(max(0.0, min(1.0, self._opacity)))
        glow = QColor("#FFFFFF")
        glow.setAlphaF(max(0.0, min(1.0, self._opacity * 0.96)))

        # Hot center flash.
        if self._radius > 1:
            hot = QColor("#FFFFFF")
            hot.setAlphaF(max(0.0, min(1.0, self._opacity * 0.82)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(hot)
            core = min(18.0 + self._radius * 0.07, 34.0)
            painter.drawEllipse(self._origin, core, core)

        # Soft accent aura.
        if self._radius > 8:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(glow_fill)
            aura = min(self._radius * 0.42, 118.0)
            painter.drawEllipse(self._origin, aura, aura)

        # Main shockwave ring.
        painter.setPen(QPen(stroke, 10))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(self._origin, self._radius, self._radius)

        # Bright edge ring.
        if self._radius > 24:
            painter.setPen(QPen(glow, 5))
            inner = max(1.0, self._radius - 18.0)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(self._origin, inner, inner)

        # Secondary trailing ring.
        if self._radius > 52:
            trail = QColor(self._color)
            trail.setAlphaF(max(0.0, min(1.0, self._opacity * 0.46)))
            painter.setPen(QPen(trail, 4))
            trail_radius = max(1.0, self._radius * 0.66)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(self._origin, trail_radius, trail_radius)

        # Final faint outer echo.
        if self._radius > 96:
            echo = QColor("#FFFFFF")
            echo.setAlphaF(max(0.0, min(1.0, self._opacity * 0.18)))
            painter.setPen(QPen(echo, 2))
            echo_radius = max(1.0, self._radius * 1.08)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(self._origin, echo_radius, echo_radius)
        painter.end()

class ThemeManager:
    """Centralized light/dark theme manager (JSON + QSS + runtime hardcoded color adaptation)."""

    THEME_DIR = Path(__file__).resolve().parents[1] / "themes"

    THEME_ALIASES = {
        "AYEC": "AYEC",
        "Bulut": "Bulut",
        "Nord": "Nord",
        "Forest": "Forest",
        "Neon": "Neon",
        "Terra": "Terra",
        "Sakura": "Sakura",
    }

    THEME_FILES = {
        "AYEC": {"json": "light_theme.json", "qss": "light_theme.qss"},
        "Bulut": {"json": "dark_theme.json", "qss": "dark_theme.qss"},
        "Nord": {"json": "nord_theme.json", "qss": "nord_theme.qss"},
        "Forest": {"json": "forest_theme.json", "qss": "forest_theme.qss"},
        "Neon": {"json": "neon_theme.json", "qss": "neon_theme.qss"},
        "Terra": {"json": "terra_theme.json", "qss": "terra_theme.qss"},
        "Sakura": {"json": "sakura_theme.json", "qss": "sakura_theme.qss"},
    }

    # Canonical theme names
    THEMES = {name: {} for name in THEME_FILES}
    DARK_THEMES = {"Bulut", "Nord", "Forest", "Neon"}

    _cache = {}
    _style_filter = None
    _combo_click_filter = None
    _current_theme = "AYEC"
    _stylesheet_patch_installed = False
    _original_set_stylesheet = None
    _active_theme_anims = []
    _style_repair_in_progress = False
    _refresh_in_progress = False
    _combo_auto_popup_enabled = False
    _styled_widgets = weakref.WeakSet()

    _stylesheet_patch_installed = False
    _original_set_stylesheet = None
    _active_theme_anims = []
    _last_palette = None

    _COLOR_TOKEN_RE = re.compile(
        r"(#[A-Fa-f0-9]{3,8}|rgb\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)|\bwhite\b|\bblack\b)",
        re.IGNORECASE,
    )
    _BLOCK_RE = re.compile(r"([^{}]+)\{([^{}]*)\}", re.DOTALL)
    _DECL_RE = re.compile(r"([\w\-]+)\s*:\s*([^;]+);")
    _TOKEN_REF_RE = re.compile(r"@([a-z_]+)")
    _MOJIBAKE_HINT_RE = re.compile(r"([\u00C3\u00C4\u00C5\u00E2\u00C2].)")
    
    _custom_accent_color = None
    _custom_text_color = None
    _NEUTRAL_HEX_RE = re.compile(
        r"#(?:fff(?:fff)?|000(?:000)?|f[0-9a-f]{5}|e[0-9a-f]{5}|d[0-9a-f]{5}|c[0-9a-f]{5}|"
        r"[0-4][0-9a-f]{5}|[5-9a-f][0-9a-f]{1,5})\b",
        re.IGNORECASE,
    )

    @staticmethod
    def _contrast_text(hex_color):
        color = QColor(hex_color)
        if not color.isValid():
            return "#FFFFFF"
        luminance = (0.299 * color.red()) + (0.587 * color.green()) + (0.114 * color.blue())
        return "#0F172A" if luminance > 170 else "#F8FAFC"

    @classmethod
    def _safe_text_color(cls, candidate_hex, theme_name):
        c = QColor(candidate_hex)
        if not c.isValid():
            return None
        lum = (0.299 * c.red()) + (0.587 * c.green()) + (0.114 * c.blue())
        if cls.is_dark_theme(theme_name):
            if lum < 120:
                return None
        else:
            if lum > 180:
                return None
        return c.name()

    @classmethod
    def _muted_from_text(cls, text_hex, theme_name):
        """Produce a muted text tone derived from chosen text color."""
        text_c = QColor(text_hex)
        if not text_c.isValid():
            return None
        theme_data = cls.get_theme_data(theme_name) or {}
        base_hex = (theme_data.get("palette") or {}).get(
            "window", "#0F172A" if cls.is_dark_theme(theme_name) else "#F8FAFC"
        )
        base_c = QColor(base_hex)
        if not base_c.isValid():
            base_c = QColor("#0F172A" if cls.is_dark_theme(theme_name) else "#F8FAFC")
        ratio = 0.72 if cls.is_dark_theme(theme_name) else 0.58
        r = int(text_c.red() * ratio + base_c.red() * (1.0 - ratio))
        g = int(text_c.green() * ratio + base_c.green() * (1.0 - ratio))
        b = int(text_c.blue() * ratio + base_c.blue() * (1.0 - ratio))
        return QColor(r, g, b).name()

    @classmethod
    def _ensure_dark_theme_texts(cls, palette_dict, theme_name):
        """Clamp dark-theme foreground tokens to readable light tones."""
        if not cls.is_dark_theme(theme_name):
            return palette_dict

        text = cls._safe_text_color(palette_dict.get("text", "#F1F5F9"), theme_name) or "#F1F5F9"
        muted = cls._safe_text_color(palette_dict.get("text_muted", "#CBD5E1"), theme_name)
        disabled = cls._safe_text_color(palette_dict.get("disabled_text", "#AFC0D6"), theme_name)

        palette_dict["text"] = text
        palette_dict["button_text"] = text
        palette_dict["text_muted"] = muted or cls._muted_from_text(text, theme_name) or "#CBD5E1"
        palette_dict["disabled_text"] = disabled or palette_dict["text_muted"]
        palette_dict["selection_text"] = (
            cls._safe_text_color(palette_dict.get("selection_text", "#F8FAFC"), theme_name) or "#F8FAFC"
        )
        return palette_dict

    @classmethod
    def load_custom_colors(cls, db):
        if db and hasattr(db, "get_setting"):
            accent = db.get_setting("custom_accent_color", "")
            cls._custom_accent_color = accent if accent else None
            
            text_col = db.get_setting("custom_text_color", "")
            cls._custom_text_color = text_col if text_col else None

            # ComboBox auto-popup ayarını yükle
            cls._combo_auto_popup_enabled = db.get_setting("combo_auto_popup", "0") == "1"

    @classmethod
    def set_custom_accent_color(cls, color_hex):
        cls._custom_accent_color = color_hex

    @classmethod
    def set_custom_text_color(cls, color_hex):
        cls._custom_text_color = color_hex

    @classmethod
    def normalize_theme_name(cls, theme_name):
        if not theme_name:
            return "AYEC"
        raw = str(theme_name).strip()
        if raw in cls.THEME_ALIASES:
            return cls.THEME_ALIASES[raw]
        key = raw.lower()
        if key in {"bulut", "dark", "karanlik", "karanlık", "koyu", "koyu modern"}:
            return "Bulut"
        if key in {"nord", "nordic"}:
            return "Nord"
        if key in {"forest", "orman"}:
            return "Forest"
        if key in {"neon", "cyber", "cyberneon"}:
            return "Neon"
        if key in {"terra", "terracotta", "toprak"}:
            return "Terra"
        if key in {"sakura", "rose", "pembe"}:
            return "Sakura"
        return "AYEC"

    @classmethod
    def get_available_themes(cls, db=None):
        themes = list(cls.THEME_FILES.keys())
        if db and hasattr(db, "get_setting"):
            deleted = set((db.get_setting("deleted_themes", "") or "").split(","))
            themes = [t for t in themes if t not in deleted]
        return themes

    @classmethod
    def is_dark_theme(cls, theme_name):
        return cls.normalize_theme_name(theme_name) in cls.DARK_THEMES

    @classmethod
    def _load_theme_data(cls, theme_name):
        name = cls.normalize_theme_name(theme_name)
        if name in cls._cache:
            return cls._cache[name]

        # Return safe default if theme not found
        if name not in cls.THEME_FILES:
            logger.warning(f"Theme '{name}' not found in THEME_FILES, returning empty data")
            return {"name": name, "data": {}, "qss": ""}

        meta = cls.THEME_FILES[name]
        json_path = cls.THEME_DIR / meta["json"]
        qss_path = cls.THEME_DIR / meta["qss"]

        data = {}
        if json_path.exists():
            try:
                data = json.loads(json_path.read_text(encoding="utf-8-sig"))
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Failed to load theme JSON for '{name}': {e}")
                data = {}

        try:
            qss = qss_path.read_text(encoding="utf-8") if qss_path.exists() else ""
        except IOError as e:
            logger.error(f"Failed to load theme QSS for '{name}': {e}")
            qss = ""

        cls._cache[name] = {"name": name, "data": data, "qss": qss}
        return cls._cache[name]

    @classmethod
    def get_theme_data(cls, theme_name):
        return cls._load_theme_data(theme_name)["data"]

    @classmethod
    def get_palette_color(cls, theme_name, key, default=""):
        data = cls.get_theme_data(theme_name)
        val = data.get("palette", {}).get(key, default)
        normalized = cls.normalize_theme_name(theme_name)
        
        if cls._custom_accent_color:
            if key in ["accent", "primary", "selection_bg", "accent_hover", "accent_pressed"]:
                return cls._custom_accent_color
                
        if cls._custom_text_color:
            if key in ["text", "button_text", "text_muted"]:
                safe = cls._safe_text_color(cls._custom_text_color, normalized)
                if safe:
                    if key == "text_muted":
                        muted = cls._muted_from_text(safe, normalized)
                        return muted or safe
                    return safe
        if key == "selection_text":
            if cls.is_dark_theme(normalized):
                return cls._safe_text_color(val or "#F8FAFC", normalized) or "#F8FAFC"
            selection_bg = data.get("palette", {}).get("selection_bg", default or "#3B82F6")
            if cls._custom_accent_color:
                selection_bg = cls._custom_accent_color
            return cls._contrast_text(selection_bg)
        if key in ["text", "button_text", "text_muted", "disabled_text"] and cls.is_dark_theme(normalized):
            fallback_map = {
                "text": "#F1F5F9",
                "button_text": "#F1F5F9",
                "text_muted": "#CBD5E1",
                "disabled_text": "#AFC0D6",
            }
            safe = cls._safe_text_color(val or fallback_map[key], normalized)
            if safe:
                return safe
            return fallback_map[key]
                
        return val

    @classmethod
    def current_palette(cls):
        theme_name = cls.normalize_theme_name(cls._current_theme)
        theme_data = cls.get_theme_data(theme_name) or {}
        p = (theme_data.get("palette") or {}).copy()
        if cls._custom_accent_color:
            for k in ["accent", "primary", "selection_bg", "accent_hover", "accent_pressed"]:
                p[k] = cls._custom_accent_color
        if cls._custom_text_color:
            safe_text = cls._safe_text_color(cls._custom_text_color, theme_name)
            if safe_text:
                for k in ["text", "button_text"]:
                    p[k] = safe_text
                p["text_muted"] = cls._muted_from_text(safe_text, theme_name) or p.get("text_muted", safe_text)
        p = cls._ensure_dark_theme_texts(p, theme_name)
        if cls.is_dark_theme(theme_name):
            p["selection_text"] = p.get("selection_text", "#F8FAFC")
        else:
            p["selection_text"] = cls._contrast_text(p.get("selection_bg", "#3B82F6"))
        return p

    @classmethod
    def get_stylesheet(cls, theme_name):
        base_qss = cls._load_theme_data(theme_name)["qss"]
        p = cls.current_palette()
        window = p.get("window", "#1E1E1E")
        surface = p.get("surface", "#2D2D2D")
        surface_alt = p.get("surface_alt", "#3C3C3C")
        text = p.get("text", "#E5E7EB")
        text_muted = p.get("text_muted", "#9CA3AF")
        border = p.get("border", "#4A4A4A")
        selection_bg = p.get("selection_bg", "#3B82F6")
        selection_text = p.get("selection_text", "#FFFFFF")
        disabled_bg = p.get("disabled_bg", "#374151")
        disabled_text = p.get("disabled_text", "#6B7280")
        extra_qss = f"""
QMainWindow, QMainWindow > QWidget {{
    background-color: {window};
    color: {text};
}}
QWidget {{
    color: {text};
}}
QWidget#CentralWidget, QWidget#RightContainer {{
    background-color: {window};
}}
QDialog, QFrame, QGroupBox {{
    background-color: {window};
    color: {text};
}}
QDialog QLabel, QDialog QCheckBox, QDialog QRadioButton {{
    color: {text};
}}
QDialog QGroupBox::title {{
    color: {text};
}}
QGroupBox::title {{
    color: {text};
}}
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {surface};
    color: {text};
    border: 1px solid {border};
}}
QLineEdit::placeholder, QTextEdit::placeholder, QPlainTextEdit::placeholder {{
    color: {disabled_text};
}}
QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover {{
    border-color: {selection_bg};
}}
QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
    background-color: {disabled_bg};
    color: {disabled_text};
}}
QLineEdit[readOnly="true"], QTextEdit[readOnly="true"], QPlainTextEdit[readOnly="true"] {{
    background-color: {surface_alt};
    color: {text_muted};
}}
QAbstractItemView {{
    background-color: {surface};
    alternate-background-color: {surface_alt};
    color: {text};
    selection-background-color: {selection_bg};
    selection-color: {selection_text};
}}
QAbstractItemView::item {{
    color: {text};
}}
QAbstractItemView::item:alternate {{
    background-color: {surface_alt};
    color: {text};
}}
QAbstractItemView::item:hover {{
    background-color: {surface_alt};
    color: {text};
}}
QAbstractItemView::item:selected {{
    background-color: {selection_bg};
    color: {selection_text};
}}
QAbstractItemView::item:selected:hover {{
    background-color: {selection_bg};
    color: {selection_text};
}}
QTableView, QTreeView {{
    background-color: {surface};
    alternate-background-color: {surface_alt};
    color: {text};
    border: 1px solid {border};
}}
QTableWidget, QListWidget {{
    background-color: {surface};
    alternate-background-color: {surface_alt};
    color: {text};
    border: 1px solid {border};
    gridline-color: {border};
}}
QTableView::viewport, QTreeView::viewport, QAbstractScrollArea::viewport {{
    background-color: {surface};
    color: {text};
}}
QTableWidget::item, QListWidget::item {{
    color: {text};
    background-color: transparent;
}}
QTableWidget::item:alternate, QListWidget::item:alternate {{
    background-color: {surface_alt};
    color: {text};
}}
QTableWidget::item:hover, QListWidget::item:hover {{
    background-color: {surface_alt};
    color: {text};
}}
QTableWidget::item:selected, QListWidget::item:selected,
QTreeView::item:selected, QTableView::item:selected {{
    background-color: {selection_bg};
    color: {selection_text};
}}
QTableWidget::item:selected:hover, QListWidget::item:selected:hover,
QTreeView::item:selected:hover, QTableView::item:selected:hover {{
    background-color: {selection_bg};
    color: {selection_text};
}}
QTreeView::item {{
    color: {text};
}}
QTreeView::item:alternate {{
    background-color: {surface_alt};
    color: {text};
}}
QTreeView::item:hover {{
    background-color: {surface_alt};
    color: {text};
}}
QHeaderView::section {{
    background-color: {surface_alt};
    color: {text};
    border: 1px solid {border};
    padding: 8px 10px;
    font-weight: 700;
}}
QHeaderView::section:hover {{
    background-color: {surface};
    color: {text};
}}
QTabBar::tab {{
    background-color: {surface};
    color: {text_muted};
    border: 1px solid {border};
    padding: 8px 14px;
}}
QTabBar::tab:hover {{
    background-color: {surface_alt};
    color: {text};
    border-color: {selection_bg};
}}
QTabBar::tab:selected {{
    background-color: {surface_alt};
    color: {text};
    border-color: {selection_bg};
}}
QScrollBar:vertical {{
    background-color: transparent;
    width: 10px;
    margin: 4px 2px 4px 2px;
}}
QScrollBar::handle:vertical {{
    background-color: {border};
    min-height: 24px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {selection_bg};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}
QScrollBar:horizontal {{
    background-color: transparent;
    height: 10px;
    margin: 2px 4px 2px 4px;
}}
QScrollBar::handle:horizontal {{
    background-color: {border};
    min-width: 24px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {selection_bg};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: transparent;
}}
QAbstractScrollArea {{
    background-color: {window};
}}
QComboBox {{
    background-color: {surface};
    color: {text};
    border: 1px solid {border};
    selection-background-color: {selection_bg};
    selection-color: {selection_text};
}}
QComboBox:hover {{
    background-color: {surface_alt};
    border-color: {selection_bg};
}}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 30px;
    border-left: 1px solid {border};
    background-color: {surface_alt};
}}
QComboBox::drop-down:hover {{
    border-left: 1px solid {selection_bg};
    background-color: {selection_bg};
}}
QComboBox::down-arrow {{
    image: none;
    width: 0px;
    height: 0px;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {text};
}}
QComboBox QAbstractItemView {{
    background-color: {surface};
    color: {text};
    selection-background-color: {selection_bg};
    selection-color: {selection_text};
    outline: none;
    border: 1px solid {border};
}}
QComboBox QAbstractItemView::item {{
    padding: 6px;
    min-height: 24px;
    background-color: {surface};
    color: {text};
}}
QComboBox QAbstractItemView::item:hover {{
    background-color: {surface_alt};
    color: {text};
}}
QComboBox QAbstractItemView::item:selected {{
    background-color: {selection_bg};
    color: {selection_text};
}}
QSpinBox, QDoubleSpinBox {{
    min-height: 40px;
    padding-right: 42px;
}}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    width: 34px;
    subcontrol-origin: border;
    background-color: {surface_alt};
    border-left: 1px solid {border};
}}
QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-position: top right;
}}
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-position: bottom right;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover,
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
    background-color: {selection_bg};
}}
QToolTip {{
    background-color: {surface_alt};
    color: {text};
    border: 1px solid {border};
}}
"""
        return base_qss + "\n" + extra_qss

    @classmethod
    def _light_fallback(cls, key, fallback=""):
        theme_data = cls.get_theme_data("AYEC") or {}
        return (theme_data.get("palette") or {}).get(key, fallback)

    @classmethod
    def _build_palette(cls, theme_name):
        palette = QPalette()
        window = QColor(cls.get_palette_color(theme_name, "window", cls._light_fallback("window")))
        text = QColor(cls.get_palette_color(theme_name, "text", cls._light_fallback("text")))
        base = QColor(cls.get_palette_color(theme_name, "surface", cls._light_fallback("surface")))
        alt = QColor(cls.get_palette_color(theme_name, "surface_alt", cls._light_fallback("surface_alt")))
        button = QColor(cls.get_palette_color(theme_name, "surface", cls._light_fallback("surface")))
        button_text = QColor(cls.get_palette_color(theme_name, "text", cls._light_fallback("text")))
        highlight = QColor(cls.get_palette_color(theme_name, "selection_bg", cls._light_fallback("selection_bg")))
        highlighted_text = QColor(cls.get_palette_color(theme_name, "selection_text", cls._light_fallback("selection_text")))

        palette.setColor(QPalette.ColorRole.Window, window)
        palette.setColor(QPalette.ColorRole.WindowText, text)
        palette.setColor(QPalette.ColorRole.Base, base)
        palette.setColor(QPalette.ColorRole.AlternateBase, alt)
        palette.setColor(QPalette.ColorRole.ToolTipBase, base)
        palette.setColor(QPalette.ColorRole.ToolTipText, text)
        palette.setColor(QPalette.ColorRole.Text, text)
        palette.setColor(QPalette.ColorRole.Button, button)
        palette.setColor(QPalette.ColorRole.ButtonText, button_text)
        palette.setColor(QPalette.ColorRole.Highlight, highlight)
        palette.setColor(QPalette.ColorRole.HighlightedText, highlighted_text)
        return palette

    @classmethod
    def _install_style_filter(cls, app):
        if cls._style_filter is None:
            cls._style_filter = _StyleChangeFilter()
            app.installEventFilter(cls._style_filter)
        if cls._combo_click_filter is None:
            cls._combo_click_filter = _ComboClickOpenFilter()
            app.installEventFilter(cls._combo_click_filter)

    @classmethod
    def _replace_color_tokens(cls, value, target_hex):
        if not value or "qlineargradient" in value.lower() or "qradialgradient" in value.lower():
            return value
        return cls._COLOR_TOKEN_RE.sub(target_hex, value)

    @classmethod
    def _is_neutral_value(cls, value):
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
        for hx in cls._NEUTRAL_HEX_RE.findall(low):
            try:
                c = QColor(hx)
                if c.isValid() and abs(c.red() - c.green()) <= 12 and abs(c.green() - c.blue()) <= 12:
                    return True
            except Exception:
                continue
        return False

    @classmethod
    def _map_decl_color(cls, selector, prop, value):
        p = cls.current_palette()
        sel = selector.lower()
        prop_l = prop.lower()

        if "transparent" in value.lower() or "none" in value.lower():
            return value

        # Primary semantic mapping
        if "selection-background-color" in prop_l:
            return cls._replace_color_tokens(value, p.get("selection_bg", cls._light_fallback("selection_bg")))
        if "selection-color" in prop_l:
            return cls._replace_color_tokens(value, p.get("selection_text", cls._light_fallback("selection_text")))
        if prop_l == "color":
            if not cls._is_neutral_value(value):
                return value
            if "qpushbutton" in sel:
                if ":disabled" in sel:
                    return cls._replace_color_tokens(value, p.get("disabled_text", cls._light_fallback("disabled_text")))
                if ":pressed" in sel or ":checked" in sel or ":selected" in sel:
                    return cls._replace_color_tokens(value, p.get("selection_text", cls._light_fallback("selection_text")))
                return cls._replace_color_tokens(value, p.get("button_text", cls._light_fallback("text")))
            if ":disabled" in sel:
                return cls._replace_color_tokens(value, p.get("disabled_text", cls._light_fallback("disabled_text")))
            return cls._replace_color_tokens(value, p.get("text", cls._light_fallback("text")))

        if "border" in prop_l:
            if not cls._is_neutral_value(value):
                return value
            return cls._replace_color_tokens(value, p.get("border", cls._light_fallback("border")))

        if "background" in prop_l:
            if not cls._is_neutral_value(value):
                return value
            if "qpushbutton" in sel:
                if ":disabled" in sel:
                    return cls._replace_color_tokens(value, p.get("disabled_bg", cls._light_fallback("disabled_bg")))
                # Keep button hover/default backgrounds as authored in QSS to avoid unreadable states.
                return value

            if "qcombobox" in sel and "qabstractitemview::item:selected" in sel:
                return cls._replace_color_tokens(value, p.get("selection_bg", cls._light_fallback("selection_bg")))
            if "qcombobox" in sel and "qabstractitemview::item:hover" in sel:
                return cls._replace_color_tokens(value, p.get("surface_alt", cls._light_fallback("surface_alt")))
            if "qcombobox::drop-down:hover" in sel:
                return cls._replace_color_tokens(value, p.get("selection_bg", cls._light_fallback("selection_bg")))
            if "qcombobox::drop-down" in sel:
                return cls._replace_color_tokens(value, p.get("surface_alt", cls._light_fallback("surface_alt")))
            if "qcombobox:hover" in sel:
                return cls._replace_color_tokens(value, p.get("surface_alt", cls._light_fallback("surface_alt")))

            if "qlineedit" in sel or "qtextedit" in sel or "qcombobox" in sel:
                return cls._replace_color_tokens(value, p.get("surface", cls._light_fallback("surface")))

            if "qmenubar" in sel or "qstatusbar" in sel or "qheaderview" in sel:
                return cls._replace_color_tokens(value, p.get("surface_alt", cls._light_fallback("surface_alt")))

            if "qscrollbar" in sel:
                return cls._replace_color_tokens(value, p.get("disabled_bg", cls._light_fallback("disabled_bg")))

            return cls._replace_color_tokens(value, p.get("window", cls._light_fallback("window")))

        return value

    @classmethod
    def transform_qss(cls, qss_text):
        if not qss_text:
            return qss_text

        # Pre-process legacy literal neutrals first to avoid overwriting matched tokens 
        out = cls._harmonize_literal_neutrals(qss_text)

        # Resolve semantic token refs.
        palette = cls.current_palette()
        out = cls._TOKEN_REF_RE.sub(lambda m: palette.get(m.group(1), m.group(0)), out)
        out = cls._remap_qss_declarations(out)
        out = cls._remap_palette_literals(out)
        return out

    @classmethod
    def _remap_qss_declarations(cls, qss_text):
        if not qss_text:
            return qss_text

        rebuilt = []
        last_end = 0

        for match in cls._BLOCK_RE.finditer(qss_text):
            rebuilt.append(qss_text[last_end:match.start()])
            selector = match.group(1)
            body = match.group(2)
            last_end = match.end()

            body_out = []
            body_last = 0
            for decl in cls._DECL_RE.finditer(body):
                body_out.append(body[body_last:decl.start()])
                prop = decl.group(1)
                value = decl.group(2)
                try:
                    mapped = cls._map_decl_color(selector, prop, value)
                except Exception:
                    mapped = value
                body_out.append(f"{prop}: {mapped};")
                body_last = decl.end()
            body_out.append(body[body_last:])
            rebuilt.append(f"{selector}{{{''.join(body_out)}}}")

        rebuilt.append(qss_text[last_end:])
        return "".join(rebuilt)

    @classmethod
    def _remap_palette_literals(cls, qss_text):
        if not qss_text:
            return qss_text
        old_palette = getattr(cls, "_last_palette", None)
        if not old_palette:
            return qss_text
        new_palette = cls.current_palette()
        pairs = []
        for key, old_val in old_palette.items():
            new_val = new_palette.get(key)
            if not old_val or not new_val:
                continue
            if str(old_val).lower() == str(new_val).lower():
                continue
            pairs.append((str(old_val), str(new_val)))
        if not pairs:
            return qss_text
        txt = qss_text
        for old, new in sorted(pairs, key=lambda item: len(item[0]), reverse=True):
            txt = re.sub(re.escape(old), new, txt, flags=re.IGNORECASE)
        return txt

    @classmethod
    def _harmonize_literal_neutrals(cls, qss_text):
        """
        Normalize legacy hardcoded neutral literals to current theme palette.
        Keeps vivid semantic/status colors intact; only maps common grayscale literals.
        """
        if not qss_text:
            return qss_text

        p = cls.current_palette()
        theme = cls.normalize_theme_name(getattr(cls, "_current_theme", "AYEC"))
        txt = qss_text

        if cls.is_dark_theme(theme):
            txt = re.sub(r"\bwhite\b", p.get("surface", "#2D2D2D"), txt, flags=re.IGNORECASE)
            txt = re.sub(r"\bblack\b", p.get("text", "#E5E7EB"), txt, flags=re.IGNORECASE)
            replacements = {
                # light backgrounds -> dark surfaces
                "#FFFFFF": p.get("surface", "#2D2D2D"),
                "#FFF": p.get("surface", "#2D2D2D"),
                "#FAFAFA": p.get("window", "#1E1E1E"),
                "#F7F8FC": p.get("window", "#1E1E1E"),
                "#F5F5F5": p.get("surface_alt", "#3C3C3C"),
                "#F3F4F8": p.get("surface_alt", "#3C3C3C"),
                "#ECEFF5": p.get("surface_alt", "#3C3C3C"),
                "#E8E8E8": p.get("surface_alt", "#3C3C3C"),
                "#E5EAF2": p.get("border", "#4A4A4A"),
                "#D6DDE9": p.get("border", "#4A4A4A"),
                "#D6D6D6": p.get("border", "#4A4A4A"),
                # dark text literals from light theme -> dark theme text
                "#111827": p.get("text", "#E5E7EB"),
                "#1F2937": p.get("text", "#E5E7EB"),

                "#374151": p.get("text", "#E5E7EB"),
                "#4B5563": p.get("text", "#E5E7EB"),
                "#64748B": p.get("text_muted", "#9CA3AF"),
                # DesignTokens light-mode values
                "#F8FAFC": p.get("window", "#1E1E1E"),
                "#F1F5F9": p.get("surface_alt", "#3C3C3C"),
            }
        else:
            txt = re.sub(r"\bwhite\b", p.get("window", "#FFFFFF"), txt, flags=re.IGNORECASE)
            txt = re.sub(r"\bblack\b", p.get("text", "#1F2937"), txt, flags=re.IGNORECASE)
            replacements = {
                # dark neutrals -> light surfaces
                "#1E1E1E": p.get("window", "#FAFAFA"),
                "#2D2D2D": p.get("surface", "#F5F5F5"),
                "#3C3C3C": p.get("surface_alt", "#E8E8E8"),
                "#4A4A4A": p.get("border", "#D6D6D6"),
                "#374151": p.get("disabled_bg", "#ECEFF5"),
                "#1F2937": p.get("text", "#1F2937"),
                "#E5E7EB": p.get("text", "#1F2937"),
                "#F3F4F6": p.get("text", "#1F2937"),
                "#D1D5DB": p.get("text_muted", "#6B7280"),
                "#6B7280": p.get("text_muted", "#6B7280"),
            }

        for old, new in replacements.items():
            txt = re.sub(re.escape(old), new, txt, flags=re.IGNORECASE)
        return txt

    @classmethod
    def _fix_mojibake_text(cls, text):
        if not text or not isinstance(text, str):
            return text
        if not cls._MOJIBAKE_HINT_RE.search(text):
            return text

        best = text
        best_score = len(cls._MOJIBAKE_HINT_RE.findall(text))

        try:
            from ftfy import fix_text
            cand = fix_text(text)
            score = len(cls._MOJIBAKE_HINT_RE.findall(cand))
            if score < best_score and cand.strip():
                best = cand
                best_score = score
        except Exception as e:
            logger.debug("ftfy fix_text failed: %s", e)

        for enc in ("cp1254", "cp1252", "latin-1"):
            try:
                cand = best.encode(enc, errors="ignore").decode("utf-8", errors="ignore")
            except Exception:
                continue
            score = len(cls._MOJIBAKE_HINT_RE.findall(cand))
            if score < best_score and cand.strip():
                best = cand
                best_score = score
        return best

    @classmethod
    def _repair_widget_texts(cls, w):
        try:
            if isinstance(w, QLabel):
                t = w.text()
                ft = cls._fix_mojibake_text(t)
                if ft != t:
                    w.setText(ft)
            elif isinstance(w, QAbstractButton):
                t = w.text()
                ft = cls._fix_mojibake_text(t)
                if ft != t:
                    w.setText(ft)
            elif isinstance(w, QLineEdit):
                p = w.placeholderText()
                fp = cls._fix_mojibake_text(p)
                if fp != p:
                    w.setPlaceholderText(fp)
            elif isinstance(w, QTextEdit):
                p = w.placeholderText()
                fp = cls._fix_mojibake_text(p)
                if fp != p:
                    w.setPlaceholderText(fp)
            elif isinstance(w, QTextBrowser):
                ht = w.toHtml()
                fht = cls._fix_mojibake_text(ht)
                if fht != ht:
                    w.setHtml(fht)
            elif isinstance(w, QPlainTextEdit):
                p = w.placeholderText()
                fp = cls._fix_mojibake_text(p)
                if fp != p:
                    w.setPlaceholderText(fp)
            elif isinstance(w, QComboBox):
                p = w.placeholderText()
                fp = cls._fix_mojibake_text(p)
                if fp != p:
                    w.setPlaceholderText(fp)
                for i in range(w.count()):
                    txt = w.itemText(i)
                    ftxt = cls._fix_mojibake_text(txt)
                    if ftxt != txt:
                        w.setItemText(i, ftxt)
            elif isinstance(w, QGroupBox):
                t = w.title()
                ft = cls._fix_mojibake_text(t)
                if ft != t:
                    w.setTitle(ft)
            elif isinstance(w, QTabWidget):
                for i in range(w.count()):
                    t = w.tabText(i)
                    ft = cls._fix_mojibake_text(t)
                    if ft != t:
                        w.setTabText(i, ft)
            elif isinstance(w, QTableWidget):
                for c in range(w.columnCount()):
                    hi = w.horizontalHeaderItem(c)
                    if hi:
                        txt = hi.text()
                        ftxt = cls._fix_mojibake_text(txt)
                        if ftxt != txt:
                            hi.setText(ftxt)
                for r in range(w.rowCount()):
                    for c in range(w.columnCount()):
                        it = w.item(r, c)
                        if it:
                            txt = it.text()
                            ftxt = cls._fix_mojibake_text(txt)
                            if ftxt != txt:
                                it.setText(ftxt)
            elif isinstance(w, QListWidget):
                for i in range(w.count()):
                    it = w.item(i)
                    if it:
                        txt = it.text()
                        ftxt = cls._fix_mojibake_text(txt)
                        if ftxt != txt:
                            it.setText(ftxt)
            elif isinstance(w, QTreeWidget):
                def _fix_tree_item(item):
                    if not item:
                        return
                    for c in range(w.columnCount()):
                        txt = item.text(c)
                        ftxt = cls._fix_mojibake_text(txt)
                        if ftxt != txt:
                            item.setText(c, ftxt)
                    for i in range(item.childCount()):
                        _fix_tree_item(item.child(i))

                for i in range(w.topLevelItemCount()):
                    _fix_tree_item(w.topLevelItem(i))
            elif isinstance(w, QMenu):
                t = w.title()
                ft = cls._fix_mojibake_text(t)
                if ft != t:
                    w.setTitle(ft)

            if hasattr(w, "actions"):
                try:
                    for act in w.actions():
                        if not isinstance(act, QAction):
                            continue
                        at = act.text()
                        fat = cls._fix_mojibake_text(at)
                        if fat != at:
                            act.setText(fat)
                except Exception as e:
                    logger.debug("Action text repair failed: %s", e)
            t = w.windowTitle()
            ft = cls._fix_mojibake_text(t)
            if ft != t:
                w.setWindowTitle(ft)
        except Exception as e:
            logger.debug("Widget text repair failed: %s", e)

    @classmethod
    def _install_stylesheet_patch(cls):
        if cls._stylesheet_patch_installed:
            return

        cls._original_set_stylesheet = QWidget.setStyleSheet

        def _patched(widget, qss):
            raw_qss = qss
            try:
                qss = ThemeManager.transform_qss(qss)
            except Exception as e:
                logger.debug("transform_qss failed in patched setStyleSheet: %s", e)
            # Keep original style template so theme refresh can re-render from source.
            try:
                setattr(widget, "_theme_raw_stylesheet", raw_qss)
            except Exception as e:
                logger.debug("raw stylesheet stash failed: %s", e)
            try:
                ThemeManager._styled_widgets.add(widget)
            except Exception as e:
                logger.debug("styled widget registry add failed: %s", e)
            return ThemeManager._original_set_stylesheet(widget, qss)

        QWidget.setStyleSheet = _patched
        cls._stylesheet_patch_installed = True

    @classmethod
    def refresh_all_widgets(cls, app=None):
        app = app or QApplication.instance()
        if not app:
            return
        if cls._refresh_in_progress:
            return
        cls._refresh_in_progress = True
        try:
            top_levels = [w for w in app.topLevelWidgets() if isinstance(w, QWidget) and (w.isVisible() or w is app.activeWindow())]
            styled_widgets = list(getattr(cls, "_styled_widgets", []))
            for w in top_levels:
                try:
                    w.setUpdatesEnabled(False)
                    widgets_to_refresh = []
                    if getattr(w, "_theme_raw_stylesheet", None):
                        widgets_to_refresh.append(w)
                    widgets_to_refresh.extend(
                        child for child in styled_widgets
                        if child is not w and isinstance(child, QWidget) and child.window() is w and getattr(child, "_theme_raw_stylesheet", None)
                    )

                    for target in widgets_to_refresh:
                        try:
                            raw = getattr(target, "_theme_raw_stylesheet", None)
                            if raw:
                                target.setStyleSheet(raw)
                        except Exception as e:
                            logger.debug("Widget stylesheet refresh failed: %s", e)

                    cls._repair_widget_texts(w)
                    # Her zaman tüm widget ağacını yeniden polish et —
                    # stylesheet olmayan widget'ların da paletini güncellemek için
                    w.style().unpolish(w)
                    w.style().polish(w)
                    QApplication.sendEvent(w, QEvent(QEvent.Type.StyleChange))
                    # Tüm child widget'lara da StyleChange olayını ilet
                    for child in w.findChildren(QWidget):
                        try:
                            child.style().unpolish(child)
                            child.style().polish(child)
                            QApplication.sendEvent(child, QEvent(QEvent.Type.StyleChange))
                        except Exception:
                            pass
                except Exception as e:
                    logger.debug("Top-level widget refresh failed: %s", e)
                finally:
                    w.setUpdatesEnabled(True)
                    w.update()
        finally:
            cls._refresh_in_progress = False

    @classmethod
    def _apply_raw(cls, app, theme_name, deferred_refresh=True):
        # Apply palette and QSS instantly so UI looks correct immediately.
        # Heavy per-widget refresh is deferred via QTimer to prevent UI freeze.
        cls._last_palette = cls.current_palette()
        cls._current_theme = cls.normalize_theme_name(theme_name)
        # Cache'i temizle — eski temadan kalan renk verileri silinsin
        cls._cache.clear()
        cls._install_stylesheet_patch()
        app.setPalette(cls._build_palette(cls._current_theme))
        app.setStyleSheet(cls.get_stylesheet(cls._current_theme))
        if deferred_refresh:
            # Defer so UI can repaint before heavy iteration (prevents freeze)
            QTimer.singleShot(0, lambda: cls.refresh_all_widgets(app))
        else:
            cls.refresh_all_widgets(app)

    @classmethod
    def apply_theme(cls, app, theme_name, window=None, animate=False, duration_ms=220):
        if not app:
            return
        name = cls.normalize_theme_name(theme_name)
        cls._install_style_filter(app)

        if animate and window is not None and window.isVisible():
            try:
                # Do not stack transition overlays; stale overlays can cause "washed/faded" UI.
                for holder in list(cls._active_theme_anims):
                    ov = holder.get("overlay")
                    anim = holder.get("anim")
                    opacity_anim = holder.get("opacity_anim")
                    try:
                        if anim:
                            anim.stop()
                    except Exception as e:
                        logger.debug("Theme overlay animation stop failed: %s", e)
                    try:
                        if opacity_anim:
                            opacity_anim.stop()
                    except Exception as e:
                        logger.debug("Theme overlay opacity animation stop failed: %s", e)
                    try:
                        if ov:
                            ov.deleteLater()
                    except Exception as e:
                        logger.debug("Theme overlay delete failed: %s", e)
                    try:
                        cls._active_theme_anims.remove(holder)
                    except Exception as e:
                        logger.debug("Active animation list cleanup failed: %s", e)

                origin = window.rect().topRight() - QPoint(24, -24)
                accent = cls.get_palette_color(name, "accent", "#38BDF8")

                cls._apply_raw(app, name, deferred_refresh=False)
                window.repaint()
                QApplication.processEvents()

                overlay = _ThemeRevealOverlay(window, origin, accent)
                overlay.show()
                overlay.raise_()

                # Strong local shockwave instead of a screen-wide wash.
                max_radius = min(max(window.width(), window.height()) * 0.44, 560.0)
                radius_anim = QPropertyAnimation(overlay, b"radius", overlay)
                radius_anim.setDuration(max(duration_ms, 420))
                radius_anim.setStartValue(0.0)
                radius_anim.setEndValue(max_radius)
                radius_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                opacity_anim = QPropertyAnimation(overlay, b"rippleOpacity", overlay)
                opacity_anim.setDuration(max(duration_ms, 420))
                opacity_anim.setStartValue(0.96)
                opacity_anim.setEndValue(0.0)
                opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                holder = {"overlay": overlay, "anim": radius_anim, "opacity_anim": opacity_anim}
                cls._active_theme_anims.append(holder)

                def _cleanup():
                    try:
                        overlay.deleteLater()
                    except Exception as e:
                        logger.debug("Overlay cleanup delete failed: %s", e)
                    try:
                        if holder in cls._active_theme_anims:
                            cls._active_theme_anims.remove(holder)
                    except Exception as e:
                        logger.debug("Overlay cleanup list remove failed: %s", e)

                radius_anim.finished.connect(_cleanup)
                # Safety cleanup in case animation signal is skipped.
                QTimer.singleShot(duration_ms + 300, _cleanup)
                radius_anim.start()
                opacity_anim.start()
                return
            except Exception as e:
                logger.debug("apply_theme animated path failed; fallback raw apply: %s", e)

        cls._apply_raw(app, name)

    @classmethod
    def run_stress_test(
        cls,
        app,
        window=None,
        interval_ms=100,
        switches=40,
        report_dir=None,
        report_prefix="theme_stress",
        capture_every=10,
    ):
        themes = list(cls.THEME_FILES.keys())
        state = {"i": 0, "count": 0}
        log_file = None
        out_dir = None

        if report_dir:
            try:
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                out_dir = Path(report_dir) / f"{report_prefix}_{stamp}"
                out_dir.mkdir(parents=True, exist_ok=True)
                log_file = out_dir / "stress_log.txt"
                log_file.write_text(
                    f"started={datetime.now().isoformat()}\n"
                    f"interval_ms={interval_ms}\n"
                    f"switches={switches}\n"
                    f"capture_every={capture_every}\n",
                    encoding="utf-8",
                )
            except Exception as e:
                logger.warning("Theme stress test report init failed: %s", e)
                log_file = None
                out_dir = None

        def _append_log(msg):
            if not log_file:
                return
            try:
                with log_file.open("a", encoding="utf-8") as f:
                    f.write(f"{datetime.now().isoformat()} {msg}\n")
            except Exception as e:
                logger.warning("Theme stress test log append failed: %s", e)

        def _capture(name):
            if not out_dir or window is None:
                return
            try:
                shot = window.grab()
                shot.save(str(out_dir / name), "PNG")
            except Exception as e:
                logger.warning("Theme stress test screenshot failed: %s", e)

        def _tick():
            theme_name = themes[state["i"] % 2]
            cls.apply_theme(app, theme_name, window=window, animate=False)
            state["i"] += 1
            state["count"] += 1
            _append_log(f"switch={state['count']} theme={theme_name}")

            if capture_every > 0 and (state["count"] % capture_every == 0):
                _capture(f"switch_{state['count']:04d}_{theme_name}.png")

            if state["count"] >= switches:
                timer.stop()
                _capture("final.png")
                _append_log("completed=true")

        timer = QTimer(app)
        timer.timeout.connect(_tick)
        timer.start(interval_ms)
        return timer


def get_theme_color(theme_name, key, default=""):
    return ThemeManager.get_palette_color(theme_name, key, default)


# Backward-compatible alias for older imports expecting an object named
# `theme_manager`. Class methods on ThemeManager can be used directly via this alias.
theme_manager = ThemeManager
