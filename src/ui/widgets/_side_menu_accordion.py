# -*- coding: utf-8 -*-
# _side_menu_accordion.py
# AccordionItem - Notion & Linear Inspired Minimal Premium Design (Safe selectors)

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer
from src.utils.theme_colors import theme_qss
from src.ui.widgets.themed_tooltip import ThemedToolTipFilter
from ._side_menu_constants import _is_classic_appearance, DesignTokens, PAGE_ICONS


class AccordionItem(QWidget):
    def __init__(self, title, icon, sub_items, parent_menu, allowed_pages=None):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.parent_menu = parent_menu
        self.allowed_pages = allowed_pages
        self._title = title
        self._icon = icon or "\U0001f4c2"
        self._icon_only = bool(getattr(parent_menu, "_icon_only", False))
        self._child_rows = []
        self._tooltip_filters = []

        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(0, 1, 0, 1)
        self.root_layout.setSpacing(0)

        # ---- Toggle Row Container ----
        self._toggle_row = QWidget()
        self._toggle_row.setObjectName("ToggleRowContainer")
        self._toggle_row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._toggle_row.setFixedHeight(38)
        self._toggle_row.setStyleSheet(self._row_qss(False))

        toggle_h = QHBoxLayout(self._toggle_row)
        toggle_h.setContentsMargins(12, 0, 12, 0)
        toggle_h.setSpacing(10)

        # Icon Label
        self._icon_lbl = QLabel(self._icon)
        self._icon_lbl.setFixedWidth(24)
        self._icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_lbl.setProperty("skipThemeTransform", False)
        self._icon_lbl.setStyleSheet("background: transparent; font-size: 14px; border: none; margin: 0px; padding: 0px;")
        toggle_h.addWidget(self._icon_lbl)

        # Title Label
        self._title_lbl = QLabel(title)
        self._title_lbl.setProperty("skipThemeTransform", False)
        self._title_lbl.setStyleSheet(theme_qss(
            "background: transparent; color: @text; font-size: 13px; font-weight: 600; border: none; margin: 0px; padding: 0px;"
        ))
        toggle_h.addWidget(self._title_lbl, 1)

        # Expand Arrow indicator
        self.arrow_label = QLabel(">")
        self.arrow_label.setFixedWidth(16)
        self.arrow_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.arrow_label.setProperty("skipThemeTransform", False)
        self.arrow_label.setStyleSheet(theme_qss(
            "background: transparent; color: @text_muted; font-size: 14px; font-weight: bold; border: none; margin: 0px; padding: 0px;"
        ))
        toggle_h.addWidget(self.arrow_label)
        self._toggle_row.setProperty("_side_menu_tooltip", title)
        self._toggle_row.setToolTip("")

        # Click transparent button on top
        self.toggle_btn = QPushButton("", self._toggle_row)
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.setProperty("skipThemeTransform", False)
        self.toggle_btn.setProperty("_side_menu_tooltip", title)
        self.toggle_btn.setToolTip("")
        self.toggle_btn.setStyleSheet("QPushButton { background: transparent; border: none; margin: 0px; padding: 0px; }")
        self.toggle_btn.clicked.connect(self.toggle_menu)
        self._install_themed_tooltip(self.toggle_btn, title)

        self.root_layout.addWidget(self._toggle_row)

        # ---- Sub Items Container ----
        self.sub_container = QWidget()
        self.sub_container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.sub_container.setProperty("skipThemeTransform", False)
        self.sub_container.setStyleSheet("background: transparent; border: none;")
        
        self.sub_layout = QVBoxLayout(self.sub_container)
        self.sub_layout.setContentsMargins(20, 2, 8, 2)
        self.sub_layout.setSpacing(2)

        self.sub_buttons = []
        self.nested_groups = []
        self._nested_page_map = {}
        any_allowed = False

        for name, page_target in sub_items:
            if isinstance(page_target, (list, tuple)):
                nested_allowed = self._add_nested_group(name, page_target)
                any_allowed = any_allowed or nested_allowed
                continue
            page_id = int(page_target)
            row_allowed = self._add_page_row(name, page_id, self.sub_layout)
            any_allowed = any_allowed or row_allowed

        self.root_layout.addWidget(self.sub_container)

        self.sub_container.setMinimumHeight(0)
        self.sub_container.setMaximumHeight(0)
        self.sub_container.setVisible(True)

        if not any_allowed:
            self.toggle_btn.setEnabled(False)
            self.toggle_btn.setCursor(Qt.CursorShape.ForbiddenCursor)
            self._title_lbl.setStyleSheet(theme_qss("background: transparent; color: @text_muted; font-size: 13px; font-weight: 600;"))

        self.is_expanded = False

    def _add_page_row(self, name, page_id, target_layout):
        pg_icon = PAGE_ICONS.get(int(page_id), "\U0001f4c4")

            # Child row widget
        child_row = QWidget()
        child_row.setObjectName("ChildRowContainer")
        child_row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        child_row.setFixedHeight(32)
        child_row.setProperty("skipThemeTransform", False)
        child_row.setStyleSheet(self._child_row_qss(False))

        ch = QHBoxLayout(child_row)
        ch.setContentsMargins(10, 0, 10, 0)
        ch.setSpacing(8)

        c_icon = QLabel(str(pg_icon))
        c_icon.setFixedWidth(16)
        c_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c_icon.setProperty("skipThemeTransform", False)
        c_icon.setStyleSheet("background: transparent; font-size: 12px; border: none; margin: 0px; padding: 0px;")
        ch.addWidget(c_icon)

        c_txt = QLabel(name)
        c_txt.setProperty("skipThemeTransform", False)
        c_txt.setStyleSheet(theme_qss(
            "background: transparent; color: @text_muted; font-size: 12px; font-weight: 500; border: none; margin: 0px; padding: 0px;"
        ))
        ch.addWidget(c_txt, 1)

        btn = QPushButton("", child_row)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setProperty("skipThemeTransform", False)
        btn.setStyleSheet("QPushButton { background: transparent; border: none; border-radius: 6px; margin: 0px; padding: 0px; }")
        btn.clicked.connect(lambda checked, pid=page_id: self.parent_menu.page_changed.emit(int(pid)))
        btn.setProperty("_side_menu_tooltip", name)
        btn.setToolTip("")
        btn._txt_lbl = c_txt
        btn._row = child_row
        self._install_themed_tooltip(btn, name)
        self._child_rows.append((child_row, c_icon, c_txt, btn))

        target_layout.addWidget(child_row)
        self.sub_buttons.append((btn, page_id))

        is_allowed = self.allowed_pages is None or int(page_id) in self.allowed_pages
        if not is_allowed:
            btn.setEnabled(False)
            btn.setCursor(Qt.CursorShape.ForbiddenCursor)
            c_txt.setStyleSheet(theme_qss("background: transparent; color: @border; font-size: 12px; font-weight: 500; border: none;"))
        return is_allowed

    def _add_nested_group(self, name, page_items):
        header = QPushButton(">  " + name)
        header.setCursor(Qt.CursorShape.PointingHandCursor)
        header.setFixedHeight(32)
        header.setProperty("skipThemeTransform", False)
        header.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @surface_alt;
                color: @text;
                border: 1px solid @border;
                border-radius: 6px;
                text-align: left;
                padding: 0 10px;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton:hover {
                border-color: @accent;
                background-color: @surface;
            }
        """))
        self.sub_layout.addWidget(header)

        container = QWidget()
        container.setProperty("skipThemeTransform", False)
        container.setStyleSheet("background: transparent; border: none;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(14, 2, 0, 2)
        layout.setSpacing(2)
        container.setVisible(False)
        self.sub_layout.addWidget(container)

        state = {"header": header, "container": container, "name": name, "expanded": False}
        self.nested_groups.append(state)
        any_allowed = False
        for child_name, child_page_id in page_items:
            child_page_id = int(child_page_id)
            any_allowed = self._add_page_row(child_name, child_page_id, layout) or any_allowed
            self._nested_page_map[child_page_id] = state
        header.setEnabled(any_allowed)
        header.setProperty("_side_menu_tooltip", name)
        header.setToolTip("")
        header.clicked.connect(lambda checked=False, item=state: self._toggle_nested(item))
        self._install_themed_tooltip(header, name)
        return any_allowed

    def _toggle_nested(self, state, force_open=False):
        expanded = bool(force_open or not state["expanded"])
        state["expanded"] = expanded
        state["container"].setVisible(expanded)
        if self._icon_only:
            state["header"].setText("\u22ef")
        else:
            state["header"].setText(("v  " if expanded else ">  ") + state["name"])
        if self.is_expanded:
            self.sub_container.setMaximumHeight(16777215)
            self.updateGeometry()

    def reveal_page(self, page_id):
        state = self._nested_page_map.get(int(page_id))
        if state is not None and not state["expanded"]:
            self._toggle_nested(state, force_open=True)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "toggle_btn") and self._toggle_row:
            self.toggle_btn.setGeometry(0, 0, self._toggle_row.width(), self._toggle_row.height())
        for btn, _ in self.sub_buttons:
            if hasattr(btn, "_row") and btn._row:
                btn.setGeometry(0, 0, btn._row.width(), btn._row.height())

    def set_icon_only(self, enabled: bool):
        self._icon_only = bool(enabled)
        self._update_tooltips()
        self._title_lbl.setVisible(not self._icon_only)
        self.arrow_label.setVisible(not self._icon_only)
        toggle_layout = self._toggle_row.layout()
        if self._icon_only:
            toggle_layout.setContentsMargins(12, 0, 12, 0)
            toggle_layout.setSpacing(0)
            self._icon_lbl.setFixedWidth(44)
        else:
            toggle_layout.setContentsMargins(12, 0, 12, 0)
            toggle_layout.setSpacing(10)
            self._icon_lbl.setFixedWidth(24)
        for child_row, icon_label, text_label, button in self._child_rows:
            text_label.setVisible(not self._icon_only)
            child_row.setToolTip(button.toolTip())
            if self._icon_only:
                child_row.layout().setContentsMargins(8, 0, 8, 0)
                child_row.layout().setSpacing(0)
                icon_label.setFixedWidth(44)
            else:
                child_row.layout().setContentsMargins(10, 0, 10, 0)
                child_row.layout().setSpacing(8)
                icon_label.setFixedWidth(16)
        for state in self.nested_groups:
            if self._icon_only:
                state["header"].setText("\u22ef")
            else:
                state["header"].setText(("v  " if state["expanded"] else ">  ") + state["name"])
        self.updateGeometry()

    def _update_tooltips(self):
        self._toggle_row.setToolTip("")
        self.toggle_btn.setToolTip("")
        for child_row, _icon_label, _text_label, button in self._child_rows:
            child_row.setToolTip("")
            button.setToolTip("")
        for state in self.nested_groups:
            state["header"].setToolTip("")
        for tooltip_filter in self._tooltip_filters:
            tooltip_filter.set_enabled(self._icon_only)

    def _install_themed_tooltip(self, widget, text):
        tooltip_filter = ThemedToolTipFilter(widget, text, db=self.parent_menu.db)
        tooltip_filter.set_enabled(self._icon_only)
        self._tooltip_filters.append(tooltip_filter)

    # ---- Notion & Linear style modern flat colors (Safe targeted selectors) ----

    def _row_qss(self, active):
        if active:
            return theme_qss("""
                QWidget#ToggleRowContainer {
                    background-color: @surface_alt;
                    border: none;
                    border-radius: 8px;
                    margin: 0px 8px;
                }
            """)
        return theme_qss("""
                QWidget#ToggleRowContainer {
                    background-color: transparent;
                    border: none;
                    border-radius: 8px;
                    margin: 0px 8px;
                }
                QWidget#ToggleRowContainer:hover {
                    background-color: @surface_alt;
                }
            """)

    def _child_row_qss(self, active):
        if active:
            return theme_qss("""
                QWidget#ChildRowContainer {
                    background-color: @selection_bg;
                    border-left: 3px solid @accent;
                    border-radius: 4px;
                    margin: 0px;
                }
            """)
        return theme_qss("""
                QWidget#ChildRowContainer {
                    background-color: transparent;
                    border-left: 3px solid transparent;
                    border-radius: 4px;
                    margin: 0px;
                }
                QWidget#ChildRowContainer:hover {
                    background-color: @surface_alt;
                }
            """)

    def _parent_button_style(self, active):
        return self._row_qss(active)

    def _child_button_style(self, active, disabled=False):
        return "QPushButton { background: transparent; border: none; }"

    # ---- Toggle Actions ----
    def toggle_menu(self):
        if self.is_expanded:
            self.collapse()
        else:
            self.expand()

    def expand(self):
        for group in self.parent_menu.accordion_groups:
            if group != self and group.is_expanded:
                group.collapse()

        self.is_expanded = True
        self.arrow_label.setText("v")
        self.arrow_label.setStyleSheet(theme_qss("background: transparent; color: @accent; font-size: 10px; border: none; margin: 0px;"))
        self._toggle_row.setStyleSheet(self._row_qss(True))
        
        self.sub_container.show()
        content_height = self.sub_container.layout().sizeHint().height() + 4
        self.anim = QPropertyAnimation(self.sub_container, b"maximumHeight")
        self.anim.setDuration(200)
        self.anim.setStartValue(self.sub_container.height())
        self.anim.setEndValue(content_height)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.finished.connect(lambda: self.sub_container.setMaximumHeight(16777215))
        self.anim.start()
        QTimer.singleShot(60, lambda: self.parent_menu.ensure_item_visible(self))

    def collapse(self):
        self.is_expanded = False
        self.arrow_label.setText(">")
        self.arrow_label.setStyleSheet(theme_qss("background: transparent; color: @text_muted; font-size: 14px; border: none; margin: 0px;"))
        self._toggle_row.setStyleSheet(self._row_qss(False))

        self.anim = QPropertyAnimation(self.sub_container, b"maximumHeight")
        self.anim.setDuration(160)
        self.anim.setStartValue(self.sub_container.height())
        self.anim.setEndValue(0)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.start()
