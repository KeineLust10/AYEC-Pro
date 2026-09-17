# -*- coding: utf-8 -*-
import json
import re
import weakref
from pathlib import Path
from datetime import datetime

import PyQt6.sip as sip
from PyQt6.QtCore import QEvent, QObject, QPropertyAnimation, QEasingCurve, QSize, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPalette
from PyQt6.QtWidgets import QAbstractButton, QApplication, QWidget

from src.utils.logger import logger
from src.utils.performance_monitor import perf_span
from src.utils.theme_filters import _StyleChangeFilter, _ComboClickOpenFilter

from ._theme_overlay import _ThemeRevealOverlay
from ._theme_constants import (
    THEME_DIR,
    THEME_ALIASES,
    THEME_FILES,
    THEMES,
    DISPLAY_THEMES,
    DARK_THEMES,
    UNSUPPORTED_QSS_DECL_RE,
)
from ._theme_color_utils import (
    contrast_text,
    contrast_ratio,
)
from ._theme_widget_repair import repair_widget_texts
from ._theme_qss_transformer import ThemeQSSTransformer


class _InterfaceScaleFilter(QObject):
    """Apply saved font and icon scale to widgets created after startup."""

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Type.Polish, QEvent.Type.Show):
            ThemeManager._scale_widget_font_and_icon(watched)
        return False


class ThemeManager:
    """Centralized light/dark theme manager (JSON + QSS + runtime hardcoded color adaptation)."""

    _repair_widget_texts = staticmethod(repair_widget_texts)

    THEME_DIR = THEME_DIR
    THEME_ALIASES = THEME_ALIASES
    THEME_FILES = THEME_FILES
    THEMES = THEMES
    DISPLAY_THEMES = DISPLAY_THEMES
    DARK_THEMES = DARK_THEMES

    _cache = {}
    _style_filter = None
    _combo_click_filter = None
    _current_theme = "AYEC"
    _stylesheet_patch_installed = False
    _original_set_stylesheet = None
    _active_theme_anims = []
    _style_repair_in_progress = False
    _refresh_in_progress = False
    _theme_generation = 0
    _combo_auto_popup_enabled = False
    _styled_widgets = weakref.WeakSet()
    _last_palette = None
    _qss_transform_cache = {}
    _qss_transformed_values = set()
    _qss_transform_cache_limit = 1024
    _compiled_stylesheet_cache = {}
    _palette_cache = {}
    _runtime_transform_caches = {}
    _runtime_transformed_values = {}
    INTERFACE_SCALE_STEPS = (80, 90, 100, 110, 120, 130, 140)
    INTERFACE_SCALE_SETTING = "interface_scale_percent"
    _interface_scale_percent = 100
    _interface_scale_filter = None
    _base_app_font = None

    _custom_accent_color = None
    _custom_text_color = None

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
        theme_data = cls.get_theme_data(theme_name) or {}
        palette = theme_data.get("palette") or {}
        bases = (
            palette.get("window"),
            palette.get("surface"),
            "#0F172A" if cls.is_dark_theme(theme_name) else "#F8FAFC",
        )
        valid_bases = [base for base in bases if QColor(base).isValid()]
        if valid_bases and min(contrast_ratio(c.name(), base) for base in valid_bases) < 4.0:
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
            text_col = db.get_setting("custom_text_color", "")
            next_accent = accent if accent else None
            next_text = text_col if text_col else None
            colors_changed = (
                next_accent != cls._custom_accent_color
                or next_text != cls._custom_text_color
            )
            cls._custom_accent_color = next_accent
            cls._custom_text_color = next_text
            if colors_changed:
                cls.invalidate_runtime_cache()

            cls._combo_auto_popup_enabled = db.get_setting("combo_auto_popup", "0") == "1"
            next_scale = cls.normalize_interface_scale(
                db.get_setting(cls.INTERFACE_SCALE_SETTING, "100")
            )
            if next_scale != cls._interface_scale_percent:
                cls._interface_scale_percent = next_scale
                cls.invalidate_runtime_cache()

    @classmethod
    def normalize_interface_scale(cls, value):
        try:
            numeric = int(float(value))
        except (TypeError, ValueError):
            numeric = 100
        return min(cls.INTERFACE_SCALE_STEPS, key=lambda step: abs(step - numeric))

    @classmethod
    def interface_scale_percent(cls):
        return cls._interface_scale_percent

    @classmethod
    def set_interface_scale(cls, value, app=None, refresh=True):
        normalized = cls.normalize_interface_scale(value)
        changed = normalized != cls._interface_scale_percent
        cls._interface_scale_percent = normalized
        if changed:
            cls.invalidate_runtime_cache()
        cls.apply_interface_scale(app=app, refresh=refresh)
        return normalized

    @classmethod
    def apply_interface_scale(cls, app=None, refresh=True):
        app = app or QApplication.instance()
        if not app:
            return
        if cls._base_app_font is None:
            cls._base_app_font = QFont(app.font())

        factor = cls._interface_scale_percent / 100.0
        scaled_font = QFont(cls._base_app_font)
        if scaled_font.pointSizeF() > 0:
            scaled_font.setPointSizeF(max(6.0, cls._base_app_font.pointSizeF() * factor))
        elif scaled_font.pixelSize() > 0:
            scaled_font.setPixelSize(max(8, round(cls._base_app_font.pixelSize() * factor)))
        app.setFont(scaled_font)

        if cls._interface_scale_filter is None:
            cls._interface_scale_filter = _InterfaceScaleFilter(app)
            app.installEventFilter(cls._interface_scale_filter)

        for widget in app.allWidgets():
            cls._scale_widget_font_and_icon(widget)
        if refresh:
            app.setStyleSheet(cls.get_stylesheet(cls._current_theme))
            cls.refresh_all_widgets(app)

    @classmethod
    def _scale_widget_font_and_icon(cls, widget):
        if not isinstance(widget, QWidget):
            return
        factor = cls._interface_scale_percent / 100.0
        try:
            if widget.testAttribute(Qt.WidgetAttribute.WA_SetFont):
                base_font = getattr(widget, "_interface_scale_base_font", None)
                if base_font is None:
                    base_font = QFont(widget.font())
                    setattr(widget, "_interface_scale_base_font", base_font)
                scaled_font = QFont(base_font)
                if base_font.pointSizeF() > 0:
                    scaled_font.setPointSizeF(max(6.0, base_font.pointSizeF() * factor))
                elif base_font.pixelSize() > 0:
                    scaled_font.setPixelSize(max(8, round(base_font.pixelSize() * factor)))
                widget.setFont(scaled_font)
        except (RuntimeError, TypeError, AttributeError):
            pass

        if not isinstance(widget, QAbstractButton) or widget.icon().isNull():
            return
        try:
            base_size = getattr(widget, "_interface_scale_base_icon_size", None)
            if base_size is None:
                base_size = QSize(widget.iconSize())
                setattr(widget, "_interface_scale_base_icon_size", base_size)
            widget.setIconSize(
                QSize(
                    max(8, round(base_size.width() * factor)),
                    max(8, round(base_size.height() * factor)),
                )
            )
        except (RuntimeError, TypeError, AttributeError):
            pass

    @classmethod
    def set_custom_accent_color(cls, color_hex):
        if color_hex == cls._custom_accent_color:
            return
        cls._custom_accent_color = color_hex
        cls.invalidate_runtime_cache()

    @classmethod
    def set_custom_text_color(cls, color_hex):
        if color_hex == cls._custom_text_color:
            return
        cls._custom_text_color = color_hex
        cls.invalidate_runtime_cache()

    @classmethod
    def _theme_cache_key(cls, theme_name=None):
        return (
            cls.normalize_theme_name(theme_name or cls._current_theme),
            cls._custom_accent_color or "",
            cls._custom_text_color or "",
            cls._interface_scale_percent,
        )

    @classmethod
    def _activate_runtime_cache(cls, theme_name):
        normalized = cls.normalize_theme_name(theme_name)
        if normalized != cls._current_theme:
            cls._theme_generation += 1
        cls._current_theme = normalized
        key = cls._theme_cache_key(cls._current_theme)
        cls._qss_transform_cache = cls._runtime_transform_caches.setdefault(key, {})
        cls._qss_transformed_values = cls._runtime_transformed_values.setdefault(key, set())
        return key

    @classmethod
    def invalidate_runtime_cache(cls):
        cls._compiled_stylesheet_cache.clear()
        cls._palette_cache.clear()
        cls._runtime_transform_caches.clear()
        cls._runtime_transformed_values.clear()
        cls._qss_transform_cache = {}
        cls._qss_transformed_values = set()

    @classmethod
    def normalize_theme_name(cls, theme_name):
        if not theme_name:
            return "AYEC"
        raw = str(theme_name).strip()
        if raw in cls.THEME_ALIASES:
            return cls.THEME_ALIASES[raw]
        key = raw.lower()
        if key in {"bulut", "dark", "karanlik", "karanlık", "koyu", "koyu modern"}:
            return "Nord"
        if key in {"nord", "nordic"}:
            return "Nord"
        if key in {"forest", "orman"}:
            return "Forest"
        if key in {"neon", "cyber", "cyberneon"}:
            return "Nord"
        if key in {"terra", "terracotta", "toprak"}:
            return "AYEC"
        if key in {"sakura", "rose", "pembe"}:
            return "Koyu Mavi"
        if key in {"sunset", "gunbatimi", "gunbat\u0131m\u0131"}:
            return "Forest"
        if key in {"midnight", "gece", "yari gece", "koyu mavi", "koyu tema", "dark blue"}:
            return "Koyu Mavi"
        if key in {"ocean", "ocaen", "okyanus", "deniz"}:
            return "Koyu Mavi"
        if key in {"lavender", "levander", "lavanta", "mor"}:
            return "Koyu Mavi"
        return "AYEC"

    @classmethod
    def get_available_themes(cls, db=None):
        themes = list(cls.DISPLAY_THEMES)
        if db and hasattr(db, "get_setting"):
            deleted = {cls.normalize_theme_name(t) for t in (db.get_setting("deleted_themes", "") or "").split(",") if t}
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
    def _light_fallback(cls, key, fallback=""):
        theme_data = cls.get_theme_data("AYEC") or {}
        return (theme_data.get("palette") or {}).get(key, fallback)

    @classmethod
    def get_palette_color(cls, theme_name, key, default=""):
        data = cls.get_theme_data(theme_name)
        val = data.get("palette", {}).get(key, default)
        if not isinstance(val, str) or not val.strip():
            val = default
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
            return contrast_text(selection_bg)
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
    def current_palette(cls, theme_name=None):
        theme_name = cls.normalize_theme_name(theme_name or cls._current_theme)
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
            p["selection_text"] = contrast_text(p.get("selection_bg", "#3B82F6"))
        p.setdefault("window", cls._light_fallback("window", "#F8FAFC"))
        p.setdefault("surface", cls._light_fallback("surface", "#FFFFFF"))
        p.setdefault("surface_alt", cls._light_fallback("surface_alt", "#E5E7EB"))
        p.setdefault("border", cls._light_fallback("border", "#CBD5E1"))
        p.setdefault("text", cls._light_fallback("text", "#111827"))
        p.setdefault("text_muted", cls._light_fallback("text_muted", "#64748B"))

        accent = (
            p.get("accent")
            or p.get("primary")
            or p.get("selection_bg")
            or cls._light_fallback("selection_bg", "#3B82F6")
        )
        p.setdefault("accent", accent)
        p.setdefault("primary", accent)
        p.setdefault("selection_bg", accent)
        p.setdefault("accent_hover", accent)
        p.setdefault("accent_pressed", accent)
        p.setdefault("hover_bg", p.get("surface_alt"))
        p.setdefault("bg", p.get("window"))
        p.setdefault("foreground", p.get("text"))
        p.setdefault("disabled_bg", p.get("surface_alt"))
        p.setdefault("disabled_text", p.get("text_muted"))
        p.setdefault("button_text", p.get("text"))

        semantic_defaults = {
            "success": "#10B981",
            "warning": "#F59E0B",
            "danger": "#EF4444",
            "info": accent,
        }
        for key, fallback in semantic_defaults.items():
            p.setdefault(key, fallback)
            p.setdefault(f"{key}_hover", p[key])
            p.setdefault(f"{key}_pressed", p[key])
            p.setdefault(f"{key}_bg", p.get("surface_alt"))
            p.setdefault(f"{key}_text", p.get("selection_text"))
        return p

    @classmethod
    def get_stylesheet(cls, theme_name):
        theme_name = cls.normalize_theme_name(theme_name)
        cache_key = cls._theme_cache_key(theme_name)
        cached = cls._compiled_stylesheet_cache.get(cache_key)
        if cached is not None:
            return cached

        base_qss = cls._load_theme_data(theme_name)["qss"]
        p = cls.current_palette(theme_name)
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
QLabel {{
    color: {text};
    background-color: transparent;
    border: none;
}}
QWidget#CentralWidget, QWidget#RightContainer, QStackedWidget#ContentArea, QWidget#StartupPlaceholder {{
    background-color: {window};
}}
QStackedWidget#ContentArea {{
    border: none;
}}
QStackedWidget#ContentArea > QWidget {{
    background-color: {window};
    color: {text};
}}
QDialog, QGroupBox {{
    background-color: {window};
    color: {text};
}}
QDialog QFrame, QGroupBox QFrame {{
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
    outline: none;
    show-decoration-selected: 1;
}}
QAbstractItemView:focus {{
    outline: none;
}}
QAbstractItemView::item {{
    color: {text};
    outline: none;
    border: none;
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
    border: none;
    outline: none;
}}
QAbstractItemView::item:selected:hover {{
    background-color: {selection_bg};
    color: {selection_text};
    border: none;
    outline: none;
}}
QAbstractItemView::item:focus,
QAbstractItemView::item:selected:focus,
QAbstractItemView::item:selected:active,
QAbstractItemView::item:focus:selected {{
    outline: none;
    border: none;
}}
QTableView, QTreeView {{
    background-color: {surface};
    alternate-background-color: {surface_alt};
    color: {text};
    border: 1px solid {border};
    outline: none;
}}
QTableWidget, QListWidget {{
    background-color: {surface};
    alternate-background-color: {surface_alt};
    color: {text};
    border: 1px solid {border};
    gridline-color: {border};
    outline: none;
}}
QTableView::viewport, QTreeView::viewport, QAbstractScrollArea::viewport {{
    background-color: {surface};
    color: {text};
}}
QTableWidget::item, QListWidget::item {{
    color: {text};
    background-color: transparent;
    outline: none;
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
    outline: none;
    border: none;
}}
QTableWidget::item:selected:hover, QListWidget::item:selected:hover,
QTreeView::item:selected:hover, QTableView::item:selected:hover {{
    background-color: {selection_bg};
    color: {selection_text};
    outline: none;
    border: none;
}}
QTreeView::item {{
    color: {text};
    outline: none;
}}
QTreeView::item:alternate {{
    background-color: {surface_alt};
    color: {text};
}}
QTreeView::item:hover {{
    background-color: {surface_alt};
    color: {text};
}}
QTreeView::item:selected {{
    background-color: {selection_bg};
    color: {selection_text};
    border: none;
}}
QTreeView::item:focus, QTableView::item:focus, QTableWidget::item:focus, QListWidget::item:focus,
QTreeView::item:selected:focus, QTableView::item:selected:focus, QTableWidget::item:selected:focus, QListWidget::item:selected:focus,
QTreeView::item:selected:active, QTableView::item:selected:active, QTableWidget::item:selected:active, QListWidget::item:selected:active {{
    outline: none;
    border: none;
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
    background-color: {surface};
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
    border: none;
    border-left: 1px solid {border};
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 30px;
    background-color: {surface_alt};
}}
QComboBox::drop-down:hover {{
    border-left: 1px solid {selection_bg};
    background-color: {selection_bg};
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
QAbstractSpinBox, QSpinBox, QDoubleSpinBox,
QDateEdit, QTimeEdit, QDateTimeEdit {{
    min-height: 40px;
    padding-right: 42px;
}}
QAbstractSpinBox::up-button, QAbstractSpinBox::down-button,
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button,
QDateEdit::up-button, QDateEdit::down-button,
QTimeEdit::up-button, QTimeEdit::down-button,
QDateTimeEdit::up-button, QDateTimeEdit::down-button {{
    width: 34px;
    subcontrol-origin: border;
    background-color: {selection_bg};
    border-left: 1px solid {border};
}}
QAbstractSpinBox::up-button,
QSpinBox::up-button, QDoubleSpinBox::up-button,
QDateEdit::up-button, QTimeEdit::up-button, QDateTimeEdit::up-button {{
    subcontrol-position: top right;
    border-bottom: 1px solid {border};
}}
QAbstractSpinBox::down-button,
QSpinBox::down-button, QDoubleSpinBox::down-button,
QDateEdit::down-button, QTimeEdit::down-button, QDateTimeEdit::down-button {{
    subcontrol-position: bottom right;
    border-top: 1px solid {border};
}}
QAbstractSpinBox::up-arrow,
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow,
QDateEdit::up-arrow, QTimeEdit::up-arrow, QDateTimeEdit::up-arrow {{
    image: none;
    width: 0px;
    height: 0px;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-bottom: 7px solid {selection_text};
}}
QAbstractSpinBox::down-arrow,
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow,
QDateEdit::down-arrow, QTimeEdit::down-arrow, QDateTimeEdit::down-arrow {{
    image: none;
    width: 0px;
    height: 0px;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 7px solid {selection_text};
}}
QAbstractSpinBox::up-arrow:disabled, QAbstractSpinBox::down-arrow:disabled,
QSpinBox::up-arrow:disabled, QSpinBox::down-arrow:disabled,
QDoubleSpinBox::up-arrow:disabled, QDoubleSpinBox::down-arrow:disabled,
QDateEdit::up-arrow:disabled, QDateEdit::down-arrow:disabled,
QTimeEdit::up-arrow:disabled, QTimeEdit::down-arrow:disabled,
QDateTimeEdit::up-arrow:disabled, QDateTimeEdit::down-arrow:disabled {{
    border-top-color: {border};
    border-bottom-color: {border};
}}
QAbstractSpinBox::up-button:disabled, QAbstractSpinBox::down-button:disabled,
QSpinBox::up-button:disabled, QSpinBox::down-button:disabled,
QDoubleSpinBox::up-button:disabled, QDoubleSpinBox::down-button:disabled,
QDateEdit::up-button:disabled, QDateEdit::down-button:disabled,
QTimeEdit::up-button:disabled, QTimeEdit::down-button:disabled,
QDateTimeEdit::up-button:disabled, QDateTimeEdit::down-button:disabled {{
    background-color: {surface_alt};
}}
QAbstractSpinBox::up-button:hover, QAbstractSpinBox::down-button:hover,
QSpinBox::up-button:hover, QSpinBox::down-button:hover,
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover,
QDateEdit::up-button:hover, QDateEdit::down-button:hover,
QTimeEdit::up-button:hover, QTimeEdit::down-button:hover,
QDateTimeEdit::up-button:hover, QDateTimeEdit::down-button:hover {{
    background-color: {selection_bg};
}}
QToolTip {{
    background-color: {surface_alt};
    color: {text};
    border: 1px solid {border};
}}
QFocusFrame {{
    border: none;
    outline: none;
}}
"""
        qss = extra_qss + "\n" + base_qss
        try:
            compiled = cls.transform_qss(qss, theme_name=theme_name, old_palette={})
        except Exception:
            compiled = cls._sanitize_qss(qss)
        cls._compiled_stylesheet_cache[cache_key] = compiled
        return compiled

    @classmethod
    def _build_palette(cls, theme_name):
        theme_name = cls.normalize_theme_name(theme_name)
        cache_key = cls._theme_cache_key(theme_name)
        cached = cls._palette_cache.get(cache_key)
        if cached is not None:
            return QPalette(cached)

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
        cls._palette_cache[cache_key] = QPalette(palette)
        return QPalette(palette)

    @classmethod
    def _install_style_filter(cls, app):
        if cls._style_filter is None:
            cls._style_filter = _StyleChangeFilter()
            app.installEventFilter(cls._style_filter)
        if cls._combo_click_filter is None:
            cls._combo_click_filter = _ComboClickOpenFilter()
            app.installEventFilter(cls._combo_click_filter)

    @classmethod
    def transform_qss(cls, qss_text, theme_name=None, old_palette=None):
        raw_qss = "" if qss_text is None else str(qss_text)
        resolved_theme = cls.normalize_theme_name(theme_name or cls._current_theme)
        cache_key = cls._theme_cache_key(resolved_theme)
        transform_cache = cls._runtime_transform_caches.setdefault(cache_key, {})
        transformed_values = cls._runtime_transformed_values.setdefault(cache_key, set())
        if resolved_theme == cls.normalize_theme_name(cls._current_theme):
            cls._qss_transform_cache = transform_cache
            cls._qss_transformed_values = transformed_values

        if raw_qss in transformed_values:
            return raw_qss

        cached = transform_cache.get(raw_qss)
        if cached is not None:
            return cached

        current_palette = cls.current_palette(resolved_theme)
        transformed = ThemeQSSTransformer.transform_qss(
            raw_qss,
            current_palette,
            cls._light_fallback,
            cls.is_dark_theme(resolved_theme),
            cls._last_palette if old_palette is None else old_palette,
        )
        transformed = cls._sanitize_qss(transformed)
        if len(transform_cache) >= cls._qss_transform_cache_limit:
            transform_cache.clear()
            transformed_values.clear()
        transform_cache[raw_qss] = transformed
        transformed_values.add(transformed)
        return transformed

    @classmethod
    def prewarm_themes(cls):
        raw_styles = set()
        for widget in list(cls._styled_widgets):
            try:
                if widget is not None and not sip.isdeleted(widget):
                    raw = getattr(widget, "_theme_raw_stylesheet", "")
                    if raw:
                        raw_styles.add(raw)
            except (RuntimeError, TypeError, AttributeError, SystemError):
                continue

        for theme_name in cls.DISPLAY_THEMES:
            cls._load_theme_data(theme_name)
            cls._build_palette(theme_name)
            cls.get_stylesheet(theme_name)
            for raw_qss in raw_styles:
                cls.transform_qss(raw_qss, theme_name=theme_name, old_palette={})

    @classmethod
    def _sanitize_qss(cls, qss_text):
        if not qss_text:
            return qss_text
        sanitized = UNSUPPORTED_QSS_DECL_RE.sub("", qss_text)
        sanitized = cls._strip_table_cell_hover_rules(sanitized)
        return cls._scale_qss_font_sizes(sanitized)

    @classmethod
    def _scale_qss_font_sizes(cls, qss_text):
        factor = cls._interface_scale_percent / 100.0
        if factor == 1.0:
            return qss_text

        def replace_size(match):
            number = float(match.group(2))
            scaled = max(6.0, number * factor)
            value = str(int(round(scaled))) if match.group(3).lower() == "px" else f"{scaled:.1f}"
            return f"{match.group(1)}{value}{match.group(3)}"

        return re.sub(
            r"(font-size\s*:\s*)(\d+(?:\.\d+)?)(px|pt)",
            replace_size,
            qss_text,
            flags=re.IGNORECASE,
        )

    @staticmethod
    def _strip_table_cell_hover_rules(qss_text):
        table_hover = re.compile(
            r"\bQ(?:Table|Tree)(?:Widget|View)\s*::item:hover\b",
            re.IGNORECASE,
        )

        def rewrite_rule(match):
            selectors = [part.strip() for part in match.group(1).split(",")]
            kept = []
            changed = False
            for selector in selectors:
                normalized = " ".join(selector.split())
                is_abstract_cell_hover = (
                    normalized.lower() == "qabstractitemview::item:hover"
                )
                if table_hover.search(normalized) or is_abstract_cell_hover:
                    changed = True
                    continue
                kept.append(selector)
            if not changed:
                return match.group(0)
            if not kept:
                return ""
            return f"{', '.join(kept)} {{{match.group(2)}}}"

        return re.sub(r"([^{}]+)\{([^{}]*)\}", rewrite_rule, qss_text)

    @classmethod
    def _install_stylesheet_patch(cls):
        if cls._stylesheet_patch_installed:
            return

        cls._original_set_stylesheet = QWidget.setStyleSheet
        cls._original_app_set_stylesheet = QApplication.setStyleSheet

        def _patched(target, qss):
            if qss is None:
                qss = ""
            raw_qss = qss

            # Bypass theme transformation for Setup Wizard and its steps to ensure correct color rendering
            is_wizard = False
            try:
                curr = target
                while curr is not None:
                    class_name = curr.__class__.__name__
                    if "Wizard" in class_name or "Step" in class_name:
                        is_wizard = True
                        break
                    if hasattr(curr, "parent"):
                        curr = curr.parent()
                    else:
                        curr = None
            except Exception:
                pass

            skip_transform = False
            try:
                skip_transform = bool(getattr(target, "property", lambda _k: False)("skipThemeTransform"))
            except Exception:
                skip_transform = False

            if is_wizard or skip_transform:
                if isinstance(target, QApplication):
                    return ThemeManager._original_app_set_stylesheet(target, qss)
                return ThemeManager._original_set_stylesheet(target, qss)

            # Avoid redundant transformation if already processed
            already_transformed = getattr(target, "_theme_applied_raw", None) == raw_qss

            try:
                # Always transform to ensure no @tokens ever reach Qt
                qss = ThemeManager.transform_qss(raw_qss)
            except Exception as e:
                logger.debug("transform_qss failed in patched setStyleSheet: %s", e)
                qss = ThemeManager._sanitize_qss(raw_qss)

            # Final safety check
            if qss is None:
                qss = ""

            # Check if this exact result was already applied to avoid Qt flicker/overhead
            if already_transformed and getattr(target, "_theme_applied_final", None) == qss:
                return None

            try:
                if isinstance(target, QWidget):
                    setattr(target, "_theme_raw_stylesheet", raw_qss)
                    setattr(target, "_theme_applied_raw", raw_qss)
                    setattr(target, "_theme_applied_final", qss)
                    setattr(
                        target,
                        "_theme_applied_generation",
                        ThemeManager._theme_generation,
                    )
                    ThemeManager._styled_widgets.add(target)
            except Exception:
                pass

            if isinstance(target, QApplication):
                return ThemeManager._original_app_set_stylesheet(target, qss)
            return ThemeManager._original_set_stylesheet(target, qss)

        QWidget.setStyleSheet = _patched
        QApplication.setStyleSheet = _patched
        cls._stylesheet_patch_installed = True

    @classmethod
    def refresh_widget_tree(cls, root, include_root=True):
        """Reapply tracked stylesheets for one widget tree."""
        if not isinstance(root, QWidget) or sip.isdeleted(root):
            return

        targets = [root] if include_root else []
        targets.extend(root.findChildren(QWidget))
        updates_enabled = root.updatesEnabled()
        root.setUpdatesEnabled(False)
        try:
            for target in targets:
                try:
                    if sip.isdeleted(target):
                        continue
                    raw = getattr(target, "_theme_raw_stylesheet", None)
                    if raw is not None:
                        setattr(target, "_theme_applied_final", None)
                        target.setStyleSheet(raw)
                    target.update()
                except (RuntimeError, AttributeError, SystemError) as exc:
                    logger.debug("Widget tree stylesheet refresh failed: %s", exc)
        finally:
            root.setUpdatesEnabled(updates_enabled)
            if updates_enabled:
                root.update()

    @classmethod
    def refresh_all_widgets(cls, app=None):
        app = app or QApplication.instance()
        if not app:
            return
        if cls._refresh_in_progress:
            return
        cls._refresh_in_progress = True
        with perf_span("theme.refresh_all_widgets"):
            try:
                # Clean up deleted/invalid widgets first to prevent memory leak and C++ crashes
                valid_styled = set()
                try:
                    styled_snapshot = list(getattr(cls, "_styled_widgets", set()))
                except Exception:
                    styled_snapshot = []
                    cls._styled_widgets = weakref.WeakSet()
                for child in styled_snapshot:
                    try:
                        if child and not sip.isdeleted(child):
                            child.parent()  # safety check
                            valid_styled.add(child)
                    except (RuntimeError, AttributeError, SystemError):
                        pass
                cls._styled_widgets = weakref.WeakSet(valid_styled)
                styled_widgets = list(valid_styled)
                top_levels = [w for w in app.topLevelWidgets() if isinstance(w, QWidget) and (w.isVisible() or w is app.activeWindow())]
                for w in top_levels:
                    try:
                        w.setUpdatesEnabled(False)
                        widgets_to_refresh = []
                        if getattr(w, "_theme_raw_stylesheet", None):
                            widgets_to_refresh.append(w)
                        widgets_to_refresh.extend(
                            child for child in styled_widgets
                            if (
                                child is not w
                                and isinstance(child, QWidget)
                                and child.window() is w
                                and child.isVisibleTo(w)
                                and getattr(child, "_theme_raw_stylesheet", None)
                            )
                        )

                        for target in widgets_to_refresh:
                            try:
                                raw = getattr(target, "_theme_raw_stylesheet", None)
                                if raw:
                                    target.setStyleSheet(raw)
                            except Exception as e:
                                logger.debug("Widget stylesheet refresh failed: %s", e)

                        if not getattr(w, "_theme_text_repair_done", False):
                            repair_widget_texts(w)
                            try:
                                setattr(w, "_theme_text_repair_done", True)
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
    def _apply_raw(
        cls,
        app,
        theme_name,
        deferred_refresh=True,
        refresh_widgets=True,
    ):
        cls._last_palette = cls.current_palette()
        cls._activate_runtime_cache(theme_name)
        cls._install_stylesheet_patch()
        with perf_span(f"theme.apply_raw.{cls._current_theme}"):
            app.setPalette(cls._build_palette(cls._current_theme))
            app.setStyleSheet(cls.get_stylesheet(cls._current_theme))
        if not refresh_widgets:
            return
        if deferred_refresh:
            QTimer.singleShot(0, lambda: cls.refresh_all_widgets(app))
        else:
            cls.refresh_all_widgets(app)

    @classmethod
    def apply_theme(cls, app, theme_name, window=None, animate=False, duration_ms=220):
        if not app:
            return
        name = cls.normalize_theme_name(theme_name)
        cls._install_style_filter(app)
        animate = False

        if animate and window is not None and window.isVisible():
            try:
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

                target_palette = cls.get_theme_data(name).get("palette", {})
                curtain_color = target_palette.get("window", cls.get_palette_color(name, "window", "#0F172A"))
                accent = target_palette.get("accent", cls.get_palette_color(name, "accent", "#38BDF8"))

                cls._apply_raw(
                    app,
                    name,
                    deferred_refresh=False,
                    refresh_widgets=window is None,
                )
                window.repaint()
                QApplication.processEvents()

                overlay = _ThemeRevealOverlay(window, curtain_color, accent)
                overlay.show()
                overlay.raise_()

                progress_anim = QPropertyAnimation(overlay, b"progress", overlay)
                progress_anim.setDuration(max(duration_ms, 260))
                progress_anim.setStartValue(0.0)
                progress_anim.setEndValue(1.0)
                progress_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
                opacity_anim = QPropertyAnimation(overlay, b"curtainOpacity", overlay)
                opacity_anim.setDuration(max(duration_ms, 260))
                opacity_anim.setStartValue(0.34 if cls.is_dark_theme(name) else 0.26)
                opacity_anim.setEndValue(0.0)
                opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                holder = {"overlay": overlay, "anim": progress_anim, "opacity_anim": opacity_anim}
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

                progress_anim.finished.connect(_cleanup)
                QTimer.singleShot(duration_ms + 300, _cleanup)
                progress_anim.start()
                opacity_anim.start()
                return
            except Exception as e:
                logger.debug("apply_theme animated path failed; fallback raw apply: %s", e)

        cls._apply_raw(
            app,
            name,
            deferred_refresh=True,
            refresh_widgets=True,
        )

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


theme_manager = ThemeManager
