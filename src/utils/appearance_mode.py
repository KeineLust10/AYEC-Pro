# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (
    QApplication,
    QAbstractButton,
    QAbstractScrollArea,
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QFrame,
    QGraphicsDropShadowEffect,
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
        tokens = {
            "window": "#F4F7FB",
            "surface": "#FFFFFF",
            "surface_alt": "#E7EEF7",
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

            palette = ThemeManager.current_palette()
            for key, default in tuple(tokens.items()):
                value = palette.get(key, default)
                tokens[key] = value if isinstance(value, str) and value else default
        except Exception:
            pass
        # Classic mode keeps a stable high-contrast tooltip/text foreground;
        # do not let the modern light-theme token override it.
        tokens["text"] = "#111827"
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
            background: transparent;
            color: {text};
        }}
        QPushButton, QToolButton, QLineEdit, QTextEdit, QPlainTextEdit,
        QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit {{
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
            border-radius: 2px;
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
            background-color: #FFFFFF;
            color: #111827;
            border: 1px solid #94A3B8;
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
    def apply_to_widget_tree(cls, root, mode):
        if root is None:
            return
        classic = cls.normalize(mode) == cls.CLASSIC
        resolved_mode = cls.CLASSIC if classic else cls.MODERN
        widgets = [root]
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
                if mode_changed:
                    cls._apply_widget_effect(widget, classic)
                    widget.setProperty(cls._PROP_LAST_MODE, resolved_mode)
                if style_changed or mode_changed:
                    widget.style().unpolish(widget)
                    widget.style().polish(widget)
                    widget.update()
            except Exception:
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
        ancestor = widget
        while ancestor is not None:
            if ancestor.objectName() == "SideMenu" or type(ancestor).__name__ == "SideMenu":
                return ""
            try:
                ancestor = ancestor.parentWidget()
            except Exception:
                ancestor = None
        base_style = cls._strip_appearance_block(widget.styleSheet() or "")
        if not base_style.strip():
            return ""
        name = widget.objectName() or ""
        if name.startswith("Kanban") or name == "ColumnContent":
            return ""
        if name == "KanbanCard":
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
                {selector} {{ background: {surface}; color: {text}; border: 1px solid {border}; border-radius: 2px; padding: 4px 8px; min-height: 24px; }}
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
                    border-radius: 2px;
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
                {spin_selector}::up-arrow {{
                    image: none;
                    width: 0px;
                    height: 0px;
                    border-left: 4px solid transparent;
                    border-right: 4px solid transparent;
                    border-bottom: 6px solid {text};
                }}
                {spin_selector}::down-arrow {{
                    image: none;
                    width: 0px;
                    height: 0px;
                    border-left: 4px solid transparent;
                    border-right: 4px solid transparent;
                    border-top: 6px solid {text};
                }}
                {spin_selector}::up-button:disabled, {spin_selector}::down-button:disabled {{
                    background: {surface_alt};
                }}
                {spin_selector}::up-arrow:disabled {{
                    border-bottom-color: {text_muted};
                }}
                {spin_selector}::down-arrow:disabled {{
                    border-top-color: {text_muted};
                }}
            """
        if isinstance(widget, (QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit)):
            return f"{selector} {{ background: {surface}; color: {text}; border: 1px solid {border}; border-radius: 2px; padding: 3px 6px; min-height: 24px; selection-background-color: {selection_bg}; selection-color: {selection_text}; }}"
        if isinstance(widget, QGroupBox):
            return f"{selector} {{ background: {surface}; color: {text}; border: 1px solid {border}; border-radius: 2px; margin-top: 8px; padding: 10px; }}"
        if isinstance(widget, QLabel):
            name = widget.objectName() or ""
            if name == "StatusTileIcon":
                return f"QLabel#StatusTileIcon {{ color: {selection_text}; }}"
            if name == "StatusTilePct":
                return f"QLabel#StatusTilePct {{ background: transparent; color: {text_muted}; border: none; }}"
            return f"{selector} {{ background: transparent; color: {text}; border: none; }}"
        if isinstance(widget, (QFrame, QStackedWidget)):
            return f"{selector} {{ background: {surface}; color: {text}; border-radius: 2px; }}"
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
        if current == next_style or widget.property(cls._PROP_LAST_STYLE) == next_style:
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
        if isinstance(original_margins, tuple) and len(original_margins) == 4:
            layout.setContentsMargins(*original_margins)
        if isinstance(original_spacing, int):
            layout.setSpacing(original_spacing)

    @classmethod
    def _apply_widget_effect(cls, widget, classic):
        effect = widget.graphicsEffect()
        if not isinstance(effect, QGraphicsDropShadowEffect):
            return
        if widget.property(cls._PROP_ORIG_EFFECT_ENABLED) is None:
            widget.setProperty(cls._PROP_ORIG_EFFECT_ENABLED, effect.isEnabled())
        if classic:
            effect.setEnabled(False)
            return
        original_enabled = widget.property(cls._PROP_ORIG_EFFECT_ENABLED)
        effect.setEnabled(bool(original_enabled) if original_enabled is not None else True)

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
        app.setProperty("appearanceMode", resolved)
        app.setProperty("skipThemeTransform", False)
        tooltip_palette = QPalette(app.palette())
        if resolved == cls.CLASSIC:
            tokens = cls.classic_tokens()
            tooltip_base = QColor(tokens["surface"])
            tooltip_text = QColor(tokens["text"])
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
        return resolved
