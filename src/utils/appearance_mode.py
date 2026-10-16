# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (
    QApplication,
    QAbstractButton,
    QAbstractScrollArea,
    QComboBox,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QGraphicsEffect,
    QGroupBox,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidgetItem,
    QListWidget,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QTableView,
    QTableWidget,
    QTabWidget,
    QTextEdit,
    QTimeEdit,
    QToolButton,
    QToolTip,
    QTreeWidget,
    QWidget,
)
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtCore import QAbstractAnimation, QEvent, QObject, QTimer, Qt
from ._theme_color_utils import contrast_ratio, contrast_text
from weakref import ref


class AppearanceModeManager:
    """Centralized Modern/Classic appearance mode helpers."""

    SETTING_KEY = "appearance_mode"
    MODERN = "modern"
    CLASSIC = "classic"
    _STYLE_MARKER_START = "/* AYEC_APPEARANCE_MODE_START */"
    _STYLE_MARKER_END = "/* AYEC_APPEARANCE_MODE_END */"
    _PROP_ORIG_MARGINS = "_ayec_orig_layout_margins"
    _PROP_ORIG_SPACING = "_ayec_orig_layout_spacing"
    _PROP_ORIG_EFFECT_ENABLED = "_ayec_orig_effect_enabled"
    _PROP_ORIG_TEXT = "_ayec_orig_text"
    _PROP_LAST_MODE = "_ayec_last_appearance_mode"
    _PROP_LAST_STYLE = "_ayec_last_appearance_style"
    _PROP_CLASSIC_SKIP_TRANSFORM = "_ayec_classic_skip_transform"
    _PROP_MODE_BASE_STYLE = "_ayec_mode_base_stylesheet"
    _ORIGINAL_UI_EFFECTS = None
    _CLASSIC_PAUSED_ANIMATIONS = []
    _CLASSIC_TOKEN_CACHE = {}
    _CLASSIC_ACTIVE = False
    _PROP_CLASSIC_ANIMATION_GUARD = "_ayec_classic_animation_guard"
    _PROP_CLASSIC_SHOW_PENDING_PAINT = "_ayec_classic_show_pending_paint"
    _PROP_CLASSIC_ANIMATION_SCAN = "_ayec_classic_animation_scan"
    _PROP_CLASSIC_THEME_HOOK_MODE = "_ayec_classic_theme_hook_mode"
    _CLASSIC_WIDGET_FILTER = None
    _CLASSIC_ANIMATION_GENERATION = 0

    class _ClassicWidgetFilter(QObject):
        """Apply Classic appearance before newly shown widgets paint."""

        def eventFilter(self, watched, event):
            if not isinstance(watched, QWidget):
                return False
            app = QApplication.instance()
            if app is None or app.property("appearanceMode") != AppearanceModeManager.CLASSIC:
                return False

            event_type = event.type()
            if event_type == QEvent.Type.ChildAdded:
                try:
                    child = event.child()
                    if isinstance(child, QAbstractAnimation):
                        parent_ref = ref(watched)
                        QTimer.singleShot(
                            0,
                            lambda parent_ref=parent_ref: AppearanceModeManager._guard_classic_animations(
                                parent_ref()
                            )
                            if parent_ref() is not None
                            else None,
                        )
                except (RuntimeError, AttributeError):
                    pass
                return False
            if event_type == QEvent.Type.Show:
                AppearanceModeManager._apply_new_classic_widget(watched)
                watched.setProperty(
                    AppearanceModeManager._PROP_CLASSIC_SHOW_PENDING_PAINT,
                    True,
                )
            elif (
                event_type == QEvent.Type.Paint
                and watched.property(
                    AppearanceModeManager._PROP_CLASSIC_SHOW_PENDING_PAINT
                )
            ):
                watched.setProperty(
                    AppearanceModeManager._PROP_CLASSIC_SHOW_PENDING_PAINT,
                    False,
                )
                AppearanceModeManager._apply_new_classic_widget(watched)
            return False

    @classmethod
    def _install_classic_widget_filter(cls, app):
        if cls._CLASSIC_WIDGET_FILTER is None:
            cls._CLASSIC_WIDGET_FILTER = cls._ClassicWidgetFilter()
        try:
            app.installEventFilter(cls._CLASSIC_WIDGET_FILTER)
        except (RuntimeError, AttributeError):
            cls._CLASSIC_WIDGET_FILTER = None

    @classmethod
    def _apply_new_classic_widget(cls, widget):
        try:
            cls.apply_to_widget_tree(widget, cls.CLASSIC, manage_animations=False)
            cls._refresh_appearance_theme_hooks(widget, cls.CLASSIC)
            cls.apply_to_widget_tree(widget, cls.CLASSIC, manage_animations=False)
            cls._apply_animation_mode(
                QApplication.instance(), True, widget, include_app=False
            )
        except (RuntimeError, AttributeError):
            return

    @classmethod
    def normalize(cls, value):
        raw = str(value or cls.MODERN).strip().lower()
        return cls.CLASSIC if raw == cls.CLASSIC else cls.MODERN

    @classmethod
    def current(cls, db=None):
        try:
            if db and hasattr(db, "get_setting"):
                return cls.normalize(db.get_setting(cls.SETTING_KEY, cls.MODERN))
        except Exception:
            pass
        return cls.MODERN

    @classmethod
    def is_classic(cls, db=None):
        return cls.current(db) == cls.CLASSIC

    @classmethod
    def classic_tokens(cls):
        theme_manager = None
        cache_key = None
        tokens = {
            "window": "#F4F7FB",
            "surface": "#F1F5F9",
            "surface_alt": "#E2E8F0",
            "text": "#10233D",
            "text_muted": "#50657D",
            "border": "#B8C7D9",
            "accent": "#1F5FAE",
            "accent_hover": "#174B89",
            "accent_pressed": "#134477",
            "selection_bg": "#D8E9FF",
            "selection_text": "#10233D",
            "disabled_bg": "#EEF3F8",
            "disabled_text": "#7A8EA5",
        }
        try:
            from src.utils.theme_manager import ThemeManager

            theme_manager = ThemeManager
            cache_key = (
                ThemeManager.normalize_theme_name(ThemeManager._current_theme),
                ThemeManager._theme_generation,
                ThemeManager._custom_accent_color,
                ThemeManager._custom_text_color,
            )
            cached = cls._CLASSIC_TOKEN_CACHE.get(cache_key)
            if cached is not None:
                return cached.copy()
            palette = ThemeManager.current_palette()
            for key, default in tuple(tokens.items()):
                value = palette.get(key, default)
                tokens[key] = value if isinstance(value, str) and value else default
        except Exception:
            pass
        if contrast_ratio(tokens["disabled_text"], tokens["disabled_bg"]) < 4.5:
            tokens["disabled_text"] = contrast_text(tokens["disabled_bg"])
        if theme_manager is not None:
            if len(cls._CLASSIC_TOKEN_CACHE) >= 12:
                cls._CLASSIC_TOKEN_CACHE.clear()
            cls._CLASSIC_TOKEN_CACHE[cache_key] = tokens.copy()
        return tokens

    @classmethod
    def classic_qss(cls):
        c = cls.classic_tokens()
        return """
        QWidget {{
            background: {window};
            color: {text};
        }}
        QMainWindow, QWidget#CentralWidget, QWidget#RightContainer, QStackedWidget, QStackedWidget#ContentArea {{
            background: {window};
        }}
        QFrame, QGroupBox, QTabWidget::pane {{
            background-color: {surface};
            border: 1px solid {border};
            border-radius: 0px;
        }}
        QGroupBox {{
            margin-top: 10px;
            padding: 12px;
            font-weight: 700;
            color: {text};
        }}
        QLabel {{
            background-color: {surface};
            color: {text};
        }}
        QPushButton, QToolButton {{
            background-color: {surface};
            color: {text};
            border: 1px solid {border};
            border-radius: 0px;
        }}
        QLineEdit, QTextEdit, QPlainTextEdit, QComboBox,
        QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit {{
            background-color: {surface};
            color: {text};
            border: 1px solid {border};
            border-radius: 0px;
            padding: 4px 7px;
            min-height: 24px;
        }}
        QPushButton:hover, QToolButton:hover, QComboBox:hover, QLineEdit:focus,
        QTextEdit:focus, QPlainTextEdit:focus {{
            border-color: {accent};
            background-color: {surface_alt};
        }}
        QPushButton:pressed, QToolButton:pressed {{
            background-color: {selection_bg};
            color: {selection_text};
        }}
        QPushButton:disabled, QToolButton:disabled, QComboBox:disabled,
        QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled,
        QSpinBox:disabled, QDoubleSpinBox:disabled, QDateEdit:disabled,
        QTimeEdit:disabled {{
            background-color: {disabled_bg};
            color: {disabled_text};
            border-color: {border};
        }}
        QMenuBar, QMenu {{
            background-color: {surface};
            color: {text};
            border: 1px solid {border};
            border-radius: 0px;
        }}
        QMenu::item {{
            background-color: {surface};
            color: {text};
            padding: 4px 20px;
        }}
        QMenu::item:selected {{
            background-color: {selection_bg};
            color: {selection_text};
        }}
        QMenu::item:disabled {{
            color: {disabled_text};
        }}
        QComboBox QAbstractItemView, QCalendarWidget QAbstractItemView {{
            background-color: {surface};
            color: {text};
            selection-background-color: {selection_bg};
            selection-color: {selection_text};
            border: 1px solid {border};
            outline: none;
        }}
        QPushButton:checked, QListWidget::item:selected, QTreeWidget::item:selected,
        QTableWidget::item:selected, QTableView::item:selected {{
            background-color: {selection_bg};
            color: {selection_text};
        }}
        QTableWidget, QTableView, QListWidget, QTreeWidget {{
            background-color: {surface};
            color: {text};
            gridline-color: {border};
            alternate-background-color: {surface_alt};
            border: 1px solid {border};
            border-radius: 0px;
        }}
        QHeaderView::section {{
            background-color: {surface_alt};
            color: {text};
            padding: 4px 6px;
            border: 1px solid {border};
            border-radius: 0px;
            font-weight: 600;
        }}
        QTabBar::tab {{
            background-color: {surface_alt};
            color: {text};
            border: 1px solid {border};
            padding: 5px 10px;
            border-radius: 0px;
        }}
        QTabBar::tab:selected {{
            background-color: {surface};
            border-bottom-color: {surface};
        }}
        QScrollArea, QAbstractScrollArea {{
            background-color: {window};
            border: 1px solid {border};
            border-radius: 0px;
        }}
        QToolTip {{
            background-color: {surface};
            color: {text};
            border: 1px solid {border};
            padding: 5px 8px;
        }}
        """.format(**c)

    @classmethod
    def classic_tab_qss(cls):
        c = cls.classic_tokens()
        return """
        QTabWidget::pane {{
            background-color: {surface};
            border: 1px solid {border};
            border-radius: 0px;
            top: -1px;
        }}
        QTabBar::tab {{
            background-color: {surface_alt};
            color: {text};
            border: 1px solid {border};
            border-bottom: 1px solid {border};
            border-radius: 0px;
            padding: 6px 12px;
            margin-right: 2px;
            min-height: 22px;
            min-width: 84px;
            font-size: 11px;
            font-weight: 700;
        }}
        QTabBar::tab:selected {{
            background-color: {surface};
            color: {text};
            border: 1px solid {border};
            border-bottom-color: {surface};
        }}
        QTabBar::tab:hover {{
            background-color: {surface_alt};
            color: {text};
            border-color: {accent};
        }}
        QTabBar::tab:disabled {{
            background-color: {disabled_bg};
            color: {disabled_text};
        }}
        QTabBar::scroller {{
            width: 24px;
        }}
        """.format(**c)

    @classmethod
    def _strip_appearance_block(cls, stylesheet):
        if not stylesheet:
            return ""
        start = stylesheet.find(cls._STYLE_MARKER_START)
        end = stylesheet.find(cls._STYLE_MARKER_END)
        if start >= 0 and end >= start:
            end += len(cls._STYLE_MARKER_END)
            return (stylesheet[:start] + stylesheet[end:]).strip()
        return stylesheet

    @classmethod
    def stylesheet_for_mode(cls, stylesheet, mode):
        base = cls._strip_appearance_block(stylesheet)
        if cls.normalize(mode) != cls.CLASSIC:
            return base
        classic_qss = cls.classic_qss()
        return (
            base
            + "\n"
            + cls._STYLE_MARKER_START
            + "\n"
            + classic_qss
            + "\n"
            + cls._STYLE_MARKER_END
        )

    @classmethod
    def apply_to_widget_tree(cls, root, mode, include_children=True, manage_animations=True):
        if root is None:
            return
        classic = cls.normalize(mode) == cls.CLASSIC
        app = QApplication.instance()
        if app is not None and manage_animations:
            cls._apply_animation_mode(app, classic, root)
        resolved_mode = cls.CLASSIC if classic else cls.MODERN
        widgets = [root]
        if include_children:
            try:
                widgets.extend(root.findChildren(QWidget))
            except Exception:
                pass

        for widget in widgets:
            try:
                previous_mode = widget.property(cls._PROP_LAST_MODE)
                widget.setProperty("appearanceMode", resolved_mode)
                cls._apply_theme_transform_guard(widget, classic)
                style_changed = cls._apply_widget_stylesheet(widget, classic)
                mode_changed = previous_mode != resolved_mode
                cls._apply_widget_layout(widget, classic)
                cls._apply_widget_text(widget, classic)
                cls._apply_widget_visibility(widget, classic)
                if mode_changed or classic:
                    cls._apply_widget_effect(widget, classic)
                if mode_changed:
                    widget.setProperty(cls._PROP_LAST_MODE, resolved_mode)
                if style_changed or mode_changed:
                    widget.style().unpolish(widget)
                    widget.style().polish(widget)
                    widget.update()
            except Exception:
                continue

    @classmethod
    def _refresh_appearance_theme_hooks(cls, root, mode):
        if root is None:
            return
        try:
            widgets = [root]
            widgets.extend(root.findChildren(QWidget))
        except (RuntimeError, AttributeError):
            widgets = [root]
        for widget in widgets:
            try:
                if widget.property(cls._PROP_CLASSIC_THEME_HOOK_MODE) == mode:
                    continue
                widget.setProperty(cls._PROP_CLASSIC_THEME_HOOK_MODE, mode)
                hook = getattr(widget, "apply_theme_styles", None)
                if not callable(hook):
                    hook = getattr(widget, "refresh_theme", None)
                if callable(hook):
                    hook()
            except (RuntimeError, AttributeError, TypeError):
                continue

    @classmethod
    def _apply_theme_transform_guard(cls, widget, classic):
        try:
            owned = bool(widget.property(cls._PROP_CLASSIC_SKIP_TRANSFORM))
            if classic:
                widget.setProperty("skipThemeTransform", False)
                widget.setProperty(cls._PROP_CLASSIC_SKIP_TRANSFORM, True)
                return
            if owned:
                widget.setProperty("skipThemeTransform", False)
                widget.setProperty(cls._PROP_CLASSIC_SKIP_TRANSFORM, False)
        except Exception:
            pass

    @classmethod
    def _selector_for_widget(cls, widget):
        selector = None
        if isinstance(widget, QPushButton):
            selector = "QPushButton"
        elif isinstance(widget, QToolButton):
            selector = "QToolButton"
        elif isinstance(widget, QLineEdit):
            selector = "QLineEdit"
        elif isinstance(widget, QTextEdit):
            selector = "QTextEdit"
        elif isinstance(widget, QPlainTextEdit):
            selector = "QPlainTextEdit"
        elif isinstance(widget, QComboBox):
            selector = "QComboBox"
        elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            selector = "QAbstractSpinBox"
        elif isinstance(widget, QDateEdit):
            selector = "QDateEdit"
        elif isinstance(widget, QTimeEdit):
            selector = "QTimeEdit"
        elif isinstance(widget, QGroupBox):
            selector = "QGroupBox"
        elif isinstance(widget, QLabel):
            selector = "QLabel"
        elif isinstance(widget, QFrame):
            selector = "QFrame"
        elif isinstance(widget, QTabWidget):
            selector = "QTabWidget"
        elif isinstance(widget, QStackedWidget):
            selector = "QStackedWidget"
        elif isinstance(widget, QTableWidget):
            selector = "QTableWidget"
        elif isinstance(widget, QTableView):
            selector = "QTableView"
        elif isinstance(widget, QListWidget):
            selector = "QListWidget"
        elif isinstance(widget, QTreeWidget):
            selector = "QTreeWidget"
        elif isinstance(widget, QHeaderView):
            selector = "QHeaderView"
        elif isinstance(widget, QAbstractScrollArea):
            selector = "QAbstractScrollArea"
        elif isinstance(widget, QMainWindow):
            selector = "QMainWindow"
        elif isinstance(widget, QDialog):
            selector = "QDialog"
        elif isinstance(widget, QWidget):
            selector = "QWidget"
        if not selector:
            return None

        object_name = widget.objectName()
        if object_name:
            return f"{selector}#{object_name}"
        return selector

    @classmethod
    def _widget_classic_qss(cls, widget):
        selector = cls._selector_for_widget(widget)
        if not selector:
            return ""
        base_style = cls._strip_appearance_block(widget.styleSheet() or "")
        if not base_style.strip():
            return ""
        c = cls.classic_tokens()
        surface = c["surface"]
        surface_alt = c["surface_alt"]
        text = c["text"]
        text_muted = c["text_muted"]
        border = c["border"]
        accent = c["accent"]
        selection_bg = c["selection_bg"]
        selection_text = c["selection_text"]
        if isinstance(widget, (QPushButton, QToolButton)):
            return f"""
                {selector} {{ background: {surface}; color: {text}; border: 1px solid {border}; border-radius: 0px; padding: 4px 8px; min-height: 24px; }}
                {selector}:hover {{ background: {surface_alt}; color: {text}; border-color: {accent}; }}
                {selector}:pressed, {selector}:checked {{ background: {selection_bg}; color: {selection_text}; }}
            """
        if isinstance(widget, (QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit)):
            spin_selector = "QAbstractSpinBox"
            if isinstance(widget, QDateEdit):
                spin_selector = "QDateEdit"
            elif isinstance(widget, QTimeEdit):
                spin_selector = "QTimeEdit"
            return f"""
                {spin_selector} {{
                    background: {surface};
                    color: {text};
                    border: 1px solid {border};
                    border-radius: 0px;
                    padding: 3px 34px 3px 6px;
                    min-height: 24px;
                    selection-background-color: {selection_bg};
                    selection-color: {selection_text};
                }}
                {spin_selector}::up-button, {spin_selector}::down-button {{
                    width: 26px;
                    subcontrol-origin: border;
                    background: {surface_alt};
                    border-left: 1px solid {border};
                }}
                {spin_selector}::up-button {{
                    subcontrol-position: top right;
                    border-bottom: 1px solid {border};
                }}
                {spin_selector}::down-button {{
                    subcontrol-position: bottom right;
                    border-top: 1px solid {border};
                }}
                {spin_selector}::up-button:hover, {spin_selector}::down-button:hover {{
                    background: {selection_bg};
                }}
                {spin_selector}::up-button:disabled, {spin_selector}::down-button:disabled {{
                    background: {surface_alt};
                }}
            """
        if isinstance(widget, (QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit)):
            return f"{selector} {{ background: {surface}; color: {text}; border: 1px solid {border}; border-radius: 0px; padding: 3px 6px; min-height: 24px; selection-background-color: {selection_bg}; selection-color: {selection_text}; }}"
        if isinstance(widget, QGroupBox):
            return f"{selector} {{ background: {surface}; color: {text}; border: 1px solid {border}; border-radius: 0px; margin-top: 8px; padding: 10px; }}"
        if isinstance(widget, QLabel):
            name = widget.objectName() or ""
            if name == "AyecThemedToolTip":
                return f"QLabel#AyecThemedToolTip {{ background: {surface}; color: {text}; border: 1px solid {border}; border-radius: 0px; }}"
            if name == "StatusTileIcon":
                return f"QLabel#StatusTileIcon {{ color: {selection_text}; }}"
            if name == "StatusTilePct":
                return f"QLabel#StatusTilePct {{ background: {surface}; color: {text_muted}; border: none; }}"
            return f"{selector} {{ background: {surface}; color: {text}; border: none; }}"
        if isinstance(widget, (QFrame, QStackedWidget)):
            return f"{selector} {{ background: {surface}; color: {text}; border-radius: 0px; }}"
        if isinstance(widget, QTabWidget):
            return cls.classic_tab_qss()
        if isinstance(widget, (QTableWidget, QTableView)):
            return f"""
                {selector} {{
                    background: {surface};
                    color: {text};
                    alternate-background-color: {surface_alt};
                    gridline-color: {border};
                    border: 1px solid {border};
                    border-radius: 0px;
                    selection-background-color: {selection_bg};
                    selection-color: {selection_text};
                }}
                {selector}::item {{
                    color: {text};
                    border-bottom: 1px solid {border};
                }}
                {selector}::item:selected {{
                    background: {selection_bg};
                    color: {selection_text};
                }}
                {selector} QHeaderView::section, QHeaderView::section {{
                    background: {surface_alt};
                    color: {text};
                    padding: 4px 6px;
                    border: 1px solid {border};
                    border-radius: 0px;
                    font-weight: 700;
                }}
            """
        if isinstance(widget, (QListWidget, QTreeWidget, QAbstractScrollArea)):
            return f"{selector} {{ background: {surface}; color: {text}; border: 1px solid {border}; border-radius: 0px; }}"
        if isinstance(widget, QHeaderView):
            return f"{selector}::section {{ background: {surface_alt}; color: {text}; padding: 4px 6px; border-radius: 0px; }}"
        if isinstance(widget, QWidget):
            return f"{selector} {{ background: {surface}; color: {text}; border-radius: 0px; }}"
        return ""

    @classmethod
    def _apply_widget_stylesheet(cls, widget, classic):
        current = widget.styleSheet() or ""
        base = cls._strip_appearance_block(current)
        if not classic:
            saved_base = widget.property(cls._PROP_MODE_BASE_STYLE)
            restore_style = saved_base if isinstance(saved_base, str) else base
            widget.setProperty(cls._PROP_MODE_BASE_STYLE, None)
            if restore_style != current:
                widget.setStyleSheet(restore_style)
                widget.setProperty(cls._PROP_LAST_STYLE, restore_style)
                return True
            return False

        saved_base = widget.property(cls._PROP_MODE_BASE_STYLE)
        if isinstance(saved_base, str):
            base = saved_base
        else:
            widget.setProperty(cls._PROP_MODE_BASE_STYLE, base)

        extra = cls._widget_classic_qss(widget)
        if not extra:
            if (
                cls._STYLE_MARKER_START in current
                and cls._STYLE_MARKER_END in current
                and not base.strip()
            ):
                return False
            if base != current:
                widget.setStyleSheet(base)
                widget.setProperty(cls._PROP_LAST_STYLE, base)
                return True
            return False
        next_style = (
            base
            + "\n"
            + cls._STYLE_MARKER_START
            + "\n"
            + extra
            + "\n"
            + cls._STYLE_MARKER_END
        )
        if current == next_style:
            return False
        widget.setStyleSheet(next_style)
        widget.setProperty(cls._PROP_LAST_STYLE, next_style)
        return True

    @classmethod
    def _apply_widget_layout(cls, widget, classic):
        layout = widget.layout()
        if layout is None:
            return
        if widget.property(cls._PROP_ORIG_MARGINS) is None:
            margins = layout.contentsMargins()
            widget.setProperty(
                cls._PROP_ORIG_MARGINS,
                (margins.left(), margins.top(), margins.right(), margins.bottom()),
            )
        if widget.property(cls._PROP_ORIG_SPACING) is None:
            widget.setProperty(cls._PROP_ORIG_SPACING, layout.spacing())

        original_margins = widget.property(cls._PROP_ORIG_MARGINS)
        original_spacing = widget.property(cls._PROP_ORIG_SPACING)
        if isinstance(original_margins, (tuple, list)) and len(original_margins) == 4:
            if classic:
                compact_margins = tuple(min(8, max(0, int(value))) for value in original_margins)
                layout.setContentsMargins(*compact_margins)
            else:
                layout.setContentsMargins(*original_margins)
        if isinstance(original_spacing, int):
            compact_spacing = 4 if original_spacing < 0 else min(4, max(0, original_spacing))
            layout.setSpacing(compact_spacing if classic else original_spacing)

    @classmethod
    def _apply_widget_effect(cls, widget, classic):
        effect = widget.graphicsEffect()
        if not isinstance(effect, QGraphicsEffect):
            return
        if widget.property(cls._PROP_ORIG_EFFECT_ENABLED) is None:
            widget.setProperty(cls._PROP_ORIG_EFFECT_ENABLED, effect.isEnabled())
        if classic:
            effect.setEnabled(False)
            return
        original_enabled = widget.property(cls._PROP_ORIG_EFFECT_ENABLED)
        effect.setEnabled(bool(original_enabled) if original_enabled is not None else True)

    @classmethod
    def _apply_animation_mode(cls, app, classic, root=None, include_app=True):
        if classic and not cls._CLASSIC_ACTIVE:
            cls._CLASSIC_ANIMATION_GENERATION += 1
        cls._CLASSIC_ACTIVE = bool(classic)
        if classic:
            animations = {}
            roots = [root] if root is not None else []
            if include_app:
                try:
                    roots.extend(app.topLevelWidgets())
                except (RuntimeError, AttributeError):
                    pass
                roots.append(app)
            pending = list(roots)
            visited = set()
            while pending:
                parent = pending.pop()
                if not isinstance(parent, QObject) or id(parent) in visited:
                    continue
                visited.add(id(parent))
                try:
                    if parent.property(cls._PROP_CLASSIC_ANIMATION_SCAN) == cls._CLASSIC_ANIMATION_GENERATION:
                        continue
                    parent.setProperty(
                        cls._PROP_CLASSIC_ANIMATION_SCAN,
                        cls._CLASSIC_ANIMATION_GENERATION,
                    )
                except (RuntimeError, AttributeError):
                    pass
                try:
                    children = parent.children()
                except (RuntimeError, AttributeError):
                    continue
                for child in children:
                    if isinstance(child, QAbstractAnimation):
                        animations[id(child)] = child
                    if isinstance(child, QObject):
                        pending.append(child)
            for animation in animations.values():
                cls._guard_classic_animation(animation)
            return

        paused = cls._CLASSIC_PAUSED_ANIMATIONS
        cls._CLASSIC_PAUSED_ANIMATIONS = []
        for animation in paused:
            try:
                if animation.state() == QAbstractAnimation.State.Paused:
                    animation.resume()
            except (RuntimeError, AttributeError):
                continue

    @classmethod
    def _guard_classic_animation(cls, animation):
        try:
            if not animation.property(cls._PROP_CLASSIC_ANIMATION_GUARD):
                animation_ref = ref(animation)

                def pause_when_classic_starts(new_state, _old_state, animation_ref=animation_ref):
                    current = animation_ref()
                    if (
                        new_state == QAbstractAnimation.State.Running
                        and cls._CLASSIC_ACTIVE
                        and current is not None
                    ):
                        current.pause()
                        if not any(item is current for item in cls._CLASSIC_PAUSED_ANIMATIONS):
                            cls._CLASSIC_PAUSED_ANIMATIONS.append(current)

                animation.stateChanged.connect(pause_when_classic_starts)
                animation.setProperty(cls._PROP_CLASSIC_ANIMATION_GUARD, True)
            if animation.state() == QAbstractAnimation.State.Running:
                animation.pause()
                if not any(item is animation for item in cls._CLASSIC_PAUSED_ANIMATIONS):
                    cls._CLASSIC_PAUSED_ANIMATIONS.append(animation)
        except (RuntimeError, AttributeError):
            return

    @classmethod
    def _guard_classic_animations(cls, root):
        if not isinstance(root, QObject):
            return
        pending = [root]
        visited = set()
        while pending:
            parent = pending.pop()
            if id(parent) in visited:
                continue
            visited.add(id(parent))
            try:
                children = parent.children()
            except (RuntimeError, AttributeError):
                continue
            for child in children:
                if isinstance(child, QAbstractAnimation):
                    cls._guard_classic_animation(child)
                if isinstance(child, QObject):
                    pending.append(child)

    @classmethod
    def _clean_text(cls, text):
        if not text:
            return text
        clean = str(text).strip()
        for sep in ("   ", "  "):
            if sep in clean:
                parts = [p.strip() for p in clean.split(sep) if p.strip()]
                if len(parts) >= 2 and len(parts[0]) <= 8:
                    clean = parts[-1]
                    break
        while clean and not (clean[0].isalnum() or clean[0] in "ÇĞİÖŞÜçğıöşü"):
            clean = clean[1:].strip()
        for prefix in ("\u011f\u0178", "\u00e2\u2013\u00b8", "\u00e2\u0161", "\u00e2\u0153", "\u00e2\u00ac", "\u00e2\u0160"):
            if clean.startswith(prefix):
                pieces = [p.strip() for p in clean.split(" ") if p.strip()]
                clean = " ".join(pieces[1:]) if len(pieces) > 1 else ""
        return clean or text

    @classmethod
    def _apply_widget_text(cls, widget, classic):
        # Appearance refreshes must preserve live text. Restoring the first
        # observed value resets counters, filters and edited list items.
        if isinstance(widget, (QAbstractButton, QLabel)):
            widget.setProperty(cls._PROP_ORIG_TEXT, widget.text())
        if isinstance(widget, QListWidget):
            for i in range(widget.count()):
                item = widget.item(i)
                if isinstance(item, QListWidgetItem):
                    item.setData(0x0100 + 91, item.text())

    @classmethod
    def _apply_widget_visibility(cls, widget, classic):
        name = widget.objectName() or ""
        if name in {"HeaderIconButton"}:
            widget.setVisible(True)

    @classmethod
    def apply(cls, app=None, db=None, root=None, mode=None):
        app = app or QApplication.instance()
        if app is None:
            return cls.MODERN
        resolved = cls.normalize(mode if mode is not None else cls.current(db))
        if resolved == cls.CLASSIC:
            cls._install_classic_widget_filter(app)
        effect_names = (
            "UI_AnimateCombo",
            "UI_AnimateMenu",
            "UI_AnimateToolBox",
            "UI_AnimateTooltip",
            "UI_FadeMenu",
            "UI_FadeTooltip",
        )
        if cls._ORIGINAL_UI_EFFECTS is None:
            cls._ORIGINAL_UI_EFFECTS = {
                name: QApplication.isEffectEnabled(getattr(Qt.UIEffect, name))
                for name in effect_names
                if hasattr(Qt.UIEffect, name)
            }
        for name, was_enabled in cls._ORIGINAL_UI_EFFECTS.items():
            effect = getattr(Qt.UIEffect, name, None)
            if effect is not None:
                QApplication.setEffectEnabled(effect, False if resolved == cls.CLASSIC else was_enabled)
        app.setProperty("appearanceMode", resolved)
        app.setProperty("skipThemeTransform", False)
        tooltip_palette = QPalette(app.palette())
        if resolved == cls.CLASSIC:
            tooltip_base = QColor("#FFFFFF")
            tooltip_text = QColor("#111827")
        else:
            tooltip_base = app.palette().color(QPalette.ColorRole.ToolTipBase)
            tooltip_text = app.palette().color(QPalette.ColorRole.ToolTipText)
        for group in (
            QPalette.ColorGroup.Active,
            QPalette.ColorGroup.Inactive,
            QPalette.ColorGroup.Disabled,
        ):
            tooltip_palette.setColor(
                group,
                QPalette.ColorRole.ToolTipBase,
                tooltip_base,
            )
            tooltip_palette.setColor(
                group,
                QPalette.ColorRole.ToolTipText,
                tooltip_text,
            )
        QToolTip.setPalette(tooltip_palette)
        next_app_style = cls.stylesheet_for_mode(app.styleSheet(), resolved)
        if app.styleSheet() != next_app_style:
            app.setStyleSheet(next_app_style)

        if root is not None:
            cls.apply_to_widget_tree(root, resolved)
            cls._refresh_appearance_theme_hooks(root, resolved)
            cls.apply_to_widget_tree(root, resolved)
        return resolved
