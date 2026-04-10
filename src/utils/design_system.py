"""
Design System Constants - Bulut Teknik Servis
Modern Enterprise (Shadcn UI / Tailwind Inspired)
"""

from PyQt6.QtWidgets import QStyledItemDelegate
from PyQt6.QtCore import QEvent
from PyQt6.QtGui import QColor


class RowHoverDelegate(QStyledItemDelegate):
    """QTableWidget için satır bazlı hover efekti.

    Kullanım:
        from src.utils.design_system import enable_row_hover
        enable_row_hover(self.table)
    """

    def __init__(self, table, hover_bg, hover_fg=None):
        super().__init__(table)
        self._table = table
        self._hover_row = -1
        self._hover_bg = QColor(hover_bg)
        self._hover_fg = QColor(hover_fg) if hover_fg else None
        table.setMouseTracking(True)
        table.viewport().installEventFilter(self)

    def eventFilter(self, obj, event):
        try:
            if obj is self._table.viewport():
                if event.type() == QEvent.Type.MouseMove:
                    index = self._table.indexAt(event.pos())
                    new_row = index.row() if index.isValid() else -1
                    if new_row != self._hover_row:
                        self._hover_row = new_row
                        self._table.viewport().update()
                elif event.type() == QEvent.Type.Leave:
                    if self._hover_row != -1:
                        self._hover_row = -1
                        self._table.viewport().update()
        except RuntimeError:
            return False
        return False

    def paint(self, painter, option, index):
        if index.row() == self._hover_row:
            painter.save()
            painter.fillRect(option.rect, self._hover_bg)
            if self._hover_fg:
                # Use a copy of option to avoid modifying the original globally
                from PyQt6.QtWidgets import QStyleOptionViewItem
                new_option = QStyleOptionViewItem(option)
                from PyQt6.QtGui import QPalette
                new_option.palette.setColor(QPalette.ColorRole.Text, self._hover_fg)
                new_option.palette.setColor(QPalette.ColorRole.WindowText, self._hover_fg)
                new_option.palette.setColor(QPalette.ColorRole.HighlightedText, self._hover_fg)
                option = new_option
            painter.restore()
        super().paint(painter, option, index)


def enable_row_hover(table, hover_bg=None, hover_fg=None):
    """Bir QTableWidget'a satır bazlı hover efekti ekler.

    Args:
        table: QTableWidget instance
        hover_bg: Hover arka plan rengi (varsayılan: tema selection_bg)
        hover_fg: Hover yazı rengi (opsiyonel)
    """
    if hover_bg is None:
        try:
            from src.utils.theme_colors import tc
            hover_bg = tc("selection_bg")
        except Exception:
            hover_bg = "#e0e7ff"
    delegate = RowHoverDelegate(table, hover_bg, hover_fg)
    table.setItemDelegate(delegate)
    # Delegate'i table'a bağla ki garbage collect edilmesin
    table._row_hover_delegate = delegate


def _tc_resolve(key, fallback=""):
    """Resolve a theme color key at runtime."""
    try:
        from src.utils.theme_colors import tc
        v = tc(key)
        return v if v else fallback
    except Exception:
        return fallback


class _DesignTokensMeta(type):
    """Metaclass that intercepts attribute access to resolve theme-aware colors."""

    # Map class attribute names → (theme_key, fallback_hex)
    _DYNAMIC_ATTRS = {
        "PRIMARY":                ("accent",         "#0F172A"),
        "PRIMARY_FOREGROUND":     ("selection_text",  "#F8FAFC"),
        "SECONDARY":              ("surface_alt",     "#F1F5F9"),
        "SECONDARY_FOREGROUND":   ("text",            "#0F172A"),
        "ACCENT":                 ("accent",          "#3B82F6"),
        "ACCENT_FOREGROUND":      ("selection_text",  "#FFFFFF"),
        "DESTRUCTIVE":            ("danger",          "#EF4444"),
        "DESTRUCTIVE_FOREGROUND": ("selection_text",  "#FFFFFF"),
        "BACKGROUND":             ("window",          "#F8FAFC"),
        "FOREGROUND":             ("text",            "#1E293B"),
        "MUTED":                  ("surface_alt",     "#F1F5F9"),
        "MUTED_FOREGROUND":       ("text_muted",      "#64748B"),
        "BORDER":                 ("border",          "#E2E8F0"),
        "INPUT":                  ("surface",         "#FFFFFF"),
        "RING":                   ("accent",          "#3B82F6"),
        "CARD":                   ("surface",         "#FFFFFF"),
        "CARD_FOREGROUND":        ("text",            "#1E293B"),
        "STATUS_SUCCESS_FG":      ("success",         "#10B981"),
        "STATUS_DANGER_FG":       ("danger",          "#EF4444"),
    }
    # Attributes that need a suffix appended after resolution
    _SUFFIX_ATTRS = {
        "STATUS_SUCCESS_BG": ("success", "#10B981", "20"),
        "STATUS_DANGER_BG":  ("danger",  "#EF4444", "20"),
    }

    def __getattr__(cls, name):
        if name in cls._DYNAMIC_ATTRS:
            key, fb = cls._DYNAMIC_ATTRS[name]
            return _tc_resolve(key, fb)
        if name in cls._SUFFIX_ATTRS:
            key, fb, suffix = cls._SUFFIX_ATTRS[name]
            return _tc_resolve(key, fb) + suffix
        raise AttributeError(f"type object 'DesignTokens' has no attribute {name!r}")


class DesignTokens(metaclass=_DesignTokensMeta):
    # Dark Mode Tokens (legacy compat – static)
    DARK_BACKGROUND = "#0F172A"
    DARK_FOREGROUND = "#F8FAFC"
    DARK_CARD = "#1E293B"
    DARK_BORDER = "#334155"
    DARK_INPUT = "#334155"

    # Shadows (QSS simulation via borders/gradients)
    SHADOW_SM = "1px 1px 2px rgba(0,0,0,0.05)"
    
    # Border Radius
    RADIUS_SM = "4px"
    RADIUS_MD = "8px"
    RADIUS_LG = "12px"
    RADIUS_XL = "16px"
    
    # Typography
    FONT_FAMILY = "'Inter', 'Segoe UI', system-ui, sans-serif"
    FONT_SIZE_BASE = "10pt"
    FONT_SIZE_SM = "9pt"
    FONT_SIZE_LG = "12pt"
    FONT_SIZE_XL = "14pt"

    # Status Colors - use tc() at runtime for theme awareness
    @staticmethod
    def status_color(status_type, part="bg"):
        from src.utils.theme_colors import tc
        _map = {
            ("success", "bg"): tc("success") + "20",
            ("success", "fg"): tc("success"),
            ("warning", "bg"): tc("warning") + "20",
            ("warning", "fg"): tc("warning"),
            ("danger", "bg"): tc("danger") + "20",
            ("danger", "fg"): tc("danger"),
            ("info", "bg"): tc("accent") + "20",
            ("info", "fg"): tc("accent"),
        }
        return _map.get((status_type, part), tc("text"))

    @classmethod
    def get_combobox_qss(cls, dark_mode=False):
        return f"""
            QComboBox {{
                background-color: @surface;
                color: @text;
                border: 1px solid @border;
                border-radius: {cls.RADIUS_MD};
                padding: 2px 12px 2px 12px;
                min-height: 42px;
                min-width: 140px;
                font-family: {cls.FONT_FAMILY};
                font-size: {cls.FONT_SIZE_BASE};
            }}
            QComboBox:editable {{
                padding: 0px 6px 0px 10px;
            }}
            QComboBox:hover {{
                border: 1px solid @accent;
            }}
            QComboBox:on {{
                border: 1px solid @accent;
            }}
            QComboBox::drop-down {{
                border-left: 1px solid @border;
                width: 30px;
                background: @surface_alt;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid @text;
                margin-right: 10px;
            }}
            QComboBox QAbstractItemView {{
                background-color: @surface;
                color: @text;
                border: 1px solid @border;
                selection-background-color: @selection_bg;
                selection-color: @selection_text;
                outline: none;
                border-radius: {cls.RADIUS_MD};
                padding: 4px;
            }}
            QComboBox QAbstractItemView::item {{
                height: 35px;
                padding-left: 8px;
                border-radius: {cls.RADIUS_SM};
            }}
        """

    @classmethod
    def get_input_qss(cls, dark_mode=False, state="normal"):
        bg = "@surface"
        fg = "@text"
        border = "@border"
        
        if state == "error":
            border = "@danger"
            bg = "@surface_alt"
        elif state == "success":
            border = "@success"
            bg = "@surface_alt"
            
        return f"""
            QLineEdit, QTextEdit, QPlainTextEdit, QDateEdit, QSpinBox, QDoubleSpinBox {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: {cls.RADIUS_MD};
                padding: 8px 12px;
                font-family: {cls.FONT_FAMILY};
                font-size: {cls.FONT_SIZE_BASE};
            }}
            QSpinBox, QDoubleSpinBox {{
                min-height: 42px;
                padding-right: 42px;
            }}
            QSpinBox::up-button, QSpinBox::down-button,
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
                width: 34px;
                background: @accent;
                color: @selection_text;
                border-left: 1px solid {border};
                subcontrol-origin: border;
            }}
            QSpinBox::up-button, QDoubleSpinBox::up-button {{
                subcontrol-position: top right;
                border-top-right-radius: {cls.RADIUS_MD};
            }}
            QSpinBox::down-button, QDoubleSpinBox::down-button {{
                subcontrol-position: bottom right;
                border-bottom-right-radius: {cls.RADIUS_MD};
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover,
            QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
                background: @success;
            }}
            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
                border: 2px solid @accent;
                background-color: {bg};
            }}
            QLineEdit::placeholder, QTextEdit::placeholder, QPlainTextEdit::placeholder {{
                color: @text_muted;
            }}
        """

    @classmethod
    def get_button_qss(cls, variant="primary", size="md"):
        # Size mapping
        dims = {"sm": "8px 16px", "md": "10px 20px", "lg": "14px 28px"}
        padding = dims.get(size, dims["md"])
        font_size = cls.FONT_SIZE_SM if size == "sm" else cls.FONT_SIZE_BASE

        # Variant mapping - use theme tokens
        if variant == "primary":
            bg, fg = "@accent", "@selection_text"
            hover_bg, hover_fg, hover_border, pressed_bg = "@accent_hover", "@selection_text", "@accent_hover", "@accent_pressed"
            outline = "border: 1px solid @accent;"
        elif variant == "secondary":
            bg, fg = "@surface_alt", "@text"
            hover_bg, hover_fg, hover_border, pressed_bg = "@surface", "@text", "@accent", "@surface_alt"
            outline = "border: 1px solid @border;"
        elif variant == "destructive":
            bg, fg = "@danger", "@selection_text"
            hover_bg, hover_fg, hover_border, pressed_bg = "@danger", "@selection_text", "@danger", "@danger_bg"
            outline = "border: 1px solid @danger;"
        elif variant == "success":
            bg, fg = "@success", "@selection_text"
            hover_bg, hover_fg, hover_border, pressed_bg = "@success", "@selection_text", "@success", "@success"
            outline = "border: 1px solid @success;"
        elif variant == "warning":
            bg, fg = "@warning", "@selection_text"
            hover_bg, hover_fg, hover_border, pressed_bg = "@warning", "@selection_text", "@warning", "@warning_bg"
            outline = "border: 1px solid @warning;"
        elif variant == "ghost":
            bg, fg = "transparent", "@text"
            hover_bg, hover_fg, hover_border, pressed_bg = "@surface_alt", "@text", "transparent", "@surface_alt"
            outline = "border: 1px solid transparent;"
        elif variant == "outline":
            bg, fg = "@surface", "@text"
            hover_bg, hover_fg, hover_border, pressed_bg = "@surface_alt", "@text", "@accent", "@surface_alt"
            outline = "border: 1px solid @border;"
        else:
            bg, fg = "@accent", "@selection_text"
            hover_bg, hover_fg, hover_border, pressed_bg = "@accent_hover", "@selection_text", "@accent_hover", "@accent_pressed"
            outline = "border: 1px solid @accent;"
        
        return f"""
            QPushButton {{
                background-color: {bg};
                color: {fg};
                {outline}
                border-radius: {cls.RADIUS_MD};
                padding: {padding};
                font-weight: 600;
                font-family: {cls.FONT_FAMILY};
                font-size: {font_size};
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
                color: {hover_fg};
                border-color: {hover_border};
            }}
            QPushButton:pressed {{
                background-color: {pressed_bg};
                color: {fg};
            }}
            QPushButton:disabled {{
                background-color: @disabled_bg;
                color: @disabled_text;
            }}
        """

    @classmethod
    def get_table_qss(cls, dark_mode=False):
        return f"""
            QTableWidget, QListWidget, QTreeWidget, QTreeView {{
                background-color: @surface;
                alternate-background-color: @surface_alt;
                border: 1px solid @border;
                border-radius: {cls.RADIUS_LG};
                gridline-color: transparent;
                color: @text;
                outline: none;
            }}
            QHeaderView::section {{
                background-color: @surface_alt;
                color: @text;
                font-family: 'Segoe UI';
                padding: 12px 10px;
                border: none;
                border-bottom: 2px solid @border;
                font-weight: 700;
                font-size: 11px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            QHeaderView::section:hover {{
                background-color: @surface;
                color: @text;
            }}
            QTableWidget::item, QListWidget::item, QTreeWidget::item, QTreeView::item {{
                padding: 10px;
                border-bottom: 1px solid @border;
                color: @text;
            }}
            QTableWidget::item:alternate, QListWidget::item:alternate,
            QTreeWidget::item:alternate, QTreeView::item:alternate {{
                background-color: @surface_alt;
                color: @text;
            }}
            QTableWidget::item:hover, QListWidget::item:hover,
            QTreeWidget::item:hover, QTreeView::item:hover {{
                background-color: @surface_alt;
                color: @text;
            }}
            QTableWidget::item:selected, QListWidget::item:selected,
            QTreeWidget::item:selected, QTreeView::item:selected {{
                background-color: @selection_bg;
                color: @selection_text;
                font-weight: 600;
            }}
            QTableWidget::item:selected:hover, QListWidget::item:selected:hover,
            QTreeWidget::item:selected:hover, QTreeView::item:selected:hover {{
                background-color: @selection_bg;
                color: @selection_text;
            }}
        """

    @classmethod
    def get_card_qss(cls, hover=True, dark_mode=False):
        hover_style = "QFrame:hover { border-color: @accent; background-color: @surface; }" if hover else ""

        return f"""
            QFrame {{
                background-color: @surface;
                border-radius: {cls.RADIUS_LG};
                border: 1px solid @border;
            }}
            {hover_style}
        """
