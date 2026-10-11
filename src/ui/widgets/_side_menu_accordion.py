# -*- coding: utf-8 -*-
# _side_menu_accordion.py
# AccordionItem - Notion & Linear Inspired Minimal Premium Design (Safe selectors)

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer
from src.utils.theme_colors import theme_qss
from src.ui.widgets.themed_tooltip import ThemedToolTipFilter
from src.ui.widgets.navigation_glyph import NavigationChevron, NavigationGlyph
from ._side_menu_constants import _is_classic_appearance, DesignTokens, PAGE_ICONS


class AccordionItem(QWidget):
    def __init__(self, title, icon, sub_items, parent_menu, allowed_pages=None, main_page_id=None):
        super().__init__()
        self.setObjectName("AccordionItemRoot")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.parent_menu = parent_menu
        self.allowed_pages = allowed_pages
        self._title = title
        self.main_page_id = int(main_page_id) if main_page_id is not None else None
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
        toggle_h.setContentsMargins(22, 0, 12, 0)
        toggle_h.setSpacing(10)

        # Icon Label
        self._icon_lbl = NavigationGlyph(self._icon, title=title, active_token='accent')
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
        self.arrow_label = NavigationChevron(">")
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
        self.toggle_btn.clicked.connect(self._on_toggle_clicked)
        self._install_themed_tooltip(self.toggle_btn, title)

        self.root_layout.addWidget(self._toggle_row)

        # ---- Sub Items Container ----
        self.sub_container = QWidget()
        self.sub_container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.sub_container.setProperty("skipThemeTransform", False)
        self.sub_container.setStyleSheet("background: transparent; border: none;")
        
        self.sub_layout = QVBoxLayout(self.sub_container)
        self.sub_layout.setContentsMargins(50, 10, 8, 2)
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
        self._active_stays_expanded = False

        if not any_allowed:
            self.toggle_btn.setEnabled(False)
            self.toggle_btn.setCursor(Qt.CursorShape.ForbiddenCursor)
            self._title_lbl.setStyleSheet(theme_qss("background: transparent; color: @text_muted; font-size: 13px; font-weight: 600;"))

        self.is_expanded = False

    def _on_toggle_clicked(self):
        self.toggle_menu()
        if self.main_page_id is not None:
            if self._title == "WhatsApp API Masas\u0131":
                self.parent_menu._requested_settings_tab = 20
            self.parent_menu.page_changed.emit(self.main_page_id)

    def _emit_page(self, page_id):
        if self._title == "WhatsApp API Masas\u0131":
            self.parent_menu._requested_settings_tab = 20
        self.parent_menu.page_changed.emit(int(page_id))

    def _add_page_row(self, name, page_id, target_layout):
        pg_icon = PAGE_ICONS.get(int(page_id), "\U0001f4c4")

            # Child row widget
        child_row = QWidget()
        child_row.setObjectName("ChildRowContainer")
        child_row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        child_row.setFixedHeight(42)
        child_row.setProperty("skipThemeTransform", False)
        child_row.setStyleSheet(self._child_row_qss(False))

        ch = QHBoxLayout(child_row)
        ch.setContentsMargins(10, 0, 10, 0)
        ch.setSpacing(8)

        c_icon = NavigationGlyph(pg_icon, page_id=int(page_id), title=name)
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

        active_dot = QLabel("\u25cf")
        active_dot.setFixedWidth(8)
        active_dot.setStyleSheet(theme_qss("color: @accent; background: transparent; border: none; font-size: 9px;"))
        active_dot.hide()
        ch.addWidget(active_dot)

        btn = QPushButton("", child_row)
        btn.setAccessibleName(name)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setProperty("skipThemeTransform", False)
        btn.setStyleSheet("QPushButton { background: transparent; border: none; border-radius: 6px; margin: 0px; padding: 0px; }")
        btn.clicked.connect(lambda checked=False, pid=page_id: self._emit_page(pid))
        btn.setProperty("_side_menu_tooltip", name)
        btn.setToolTip("")
        btn._txt_lbl = c_txt
        btn._icon_lbl = c_icon
        btn._active_dot = active_dot
        btn._row = child_row
        self._install_themed_tooltip(btn, name)
        self._child_rows.append((child_row, c_icon, c_txt, btn))

        target_layout.addWidget(child_row)
        self.sub_buttons.append((btn, page_id))

        is_allowed = self.allowed_pages is None or int(page_id) in self.allowed_pages
        c_icon.set_navigation_state(disabled=not is_allowed)
        if not is_allowed:
            btn.setEnabled(False)
            btn.setCursor(Qt.CursorShape.ForbiddenCursor)
            c_txt.setStyleSheet(theme_qss("background: transparent; color: @border; font-size: 12px; font-weight: 500; border: none;"))
        return is_allowed

    def _add_nested_group(self, name, page_items):
        header = QPushButton("")
        header.setAccessibleName(name)
        header.setCursor(Qt.CursorShape.PointingHandCursor)
        header.setFixedHeight(42)
        header.setProperty("skipThemeTransform", False)
        header.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: transparent;
                color: @text_muted;
                border: none;
                border-radius: 6px;
                text-align: left;
                padding: 0;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: @surface_alt;
            }
        """))
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(4, 0, 8, 0)
        header_layout.setSpacing(8)
        header_icon = NavigationGlyph("\u2699", title=name, active_token="accent")
        header_icon.setFixedSize(16, 20)
        header_icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        header_text = QLabel(name)
        header_text.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        header_text.setStyleSheet(theme_qss(
            "background: transparent; color: @text_muted; font-size: 12px; border: none;"
        ))
        header_arrow = NavigationChevron()
        header_arrow.setFixedSize(14, 20)
        header_arrow.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        header_layout.addWidget(header_icon)
        header_layout.addWidget(header_text, 1)
        header_layout.addWidget(header_arrow)
        self.sub_layout.addWidget(header)

        container = QWidget()
        container.setObjectName("NestedNavigationContainer")
        container.setProperty("skipThemeTransform", False)
        container.setStyleSheet(theme_qss(
            "QWidget#NestedNavigationContainer { background: transparent; "
            "border: none; border-left: 1px solid @border; }"
        ))
        layout = QVBoxLayout(container)
        layout.setContentsMargins(14, 2, 0, 2)
        layout.setSpacing(2)
        container.setVisible(False)
        self.sub_layout.addWidget(container)

        state = {"header": header, "container": container, "name": name, "expanded": False,
                 "icon": header_icon, "label": header_text, "arrow": header_arrow}
        self.nested_groups.append(state)
        any_allowed = False
        for child_name, child_page_id in page_items:
            child_page_id = int(child_page_id)
            any_allowed = self._add_page_row(child_name, child_page_id, layout) or any_allowed
            self._nested_page_map[child_page_id] = state
        header.setEnabled(any_allowed)
        self._update_nested_header(state)
        header.setProperty("_side_menu_tooltip", name)
        header.setToolTip("")
        header.clicked.connect(lambda checked=False, item=state: self._toggle_nested(item))
        self._install_themed_tooltip(header, name)
        return any_allowed

    def _toggle_nested(self, state, force_open=False):
        expanded = bool(force_open or not state["expanded"])
        state["expanded"] = expanded
        state["container"].setVisible(expanded)
        self._update_nested_header(state)
        if self.is_expanded:
            self.sub_container.setMaximumHeight(16777215)
            self.updateGeometry()

    def _update_nested_header(self, state):
        state["label"].setVisible(not self._icon_only)
        state["arrow"].setVisible(not self._icon_only)
        state["arrow"].setText("v" if state["expanded"] else ">")
        state["icon"].set_navigation_state(state["expanded"], not state["header"].isEnabled())

    def reveal_page(self, page_id):
        state = self._nested_page_map.get(int(page_id))
        if state is not None and not state["expanded"]:
            self._toggle_nested(state, force_open=True)
        if state is not None:
            state["header"].setStyleSheet(theme_qss(
                'QPushButton { background: @surface_alt; border: 1px solid @accent; '
                'border-bottom: none; border-radius: 7px 7px 0 0; }'
            ))
            state["container"].setStyleSheet(theme_qss(
                'QWidget#NestedNavigationContainer { background: @surface; '
                'border: 1px solid @accent; border-top: none; border-radius: 0 0 7px 7px; }'
            ))

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
            self._update_nested_header(state)
        self.updateGeometry()

    def set_compact_density(self, compact):
        compact = bool(compact)
        reference_catalog = (
            compact
            and getattr(self.parent_menu, "_last_active_page_id", None) == 146
        )
        if (getattr(self, "_compact_density", None) == compact
                and getattr(self, "_reference_catalog_density", False) == reference_catalog):
            return
        self._compact_density = compact
        self._reference_catalog_density = reference_catalog
        self.root_layout.setContentsMargins(0, 1, 0, 1)
        self._toggle_row.setFixedHeight((24 if reference_catalog else 22) if compact else 38)
        self._toggle_row.layout().setContentsMargins(8 if compact else 22, 0, 8 if compact else 12, 0)
        self._toggle_row.layout().setSpacing(7 if compact else 10)
        self._icon_lbl.setFixedWidth(20 if compact else 24)
        self._title_lbl.setStyleSheet(theme_qss(
            "background: transparent; color: @text; font-size: 11px; font-weight: 600; border: none; margin: 0px; padding: 0px;"
            if compact else
            "background: transparent; color: @text; font-size: 13px; font-weight: 600; border: none; margin: 0px; padding: 0px;"
        ))
        self.sub_layout.setContentsMargins(
            14 if compact else getattr(self, "_reference_submenu_indent", 36),
            1 if compact else getattr(self, "_reference_submenu_top_margin", 10),
                                           6 if compact else 8, 1)
        self.sub_layout.setSpacing(1)
        for child_row, icon_label, text_label, _button in self._child_rows:
            child_row.setFixedHeight(
                (23 if reference_catalog else 21) if compact else getattr(self, "_reference_child_row_height", 42)
            )
            child_row.layout().setContentsMargins(7 if compact else 26, 0, 7 if compact else 10, 0)
            child_row.layout().setSpacing(6 if compact else 8)
            icon_label.setFixedWidth(14 if compact else 16)
            text_label.setStyleSheet(theme_qss(
                "background: transparent; color: @text_muted; font-size: 10px; font-weight: 500; border: none; margin: 0px; padding: 0px;"
                if compact else
                "background: transparent; color: @text_muted; font-size: 12px; font-weight: 500; border: none; margin: 0px; padding: 0px;"
            ))
        for state in self.nested_groups:
            state["header"].setFixedHeight(26 if compact else 42)
            state["label"].setStyleSheet(theme_qss(
                "background: transparent; color: @text_muted; font-size: 10px; border: none;"
                if compact else
                "background: transparent; color: @text_muted; font-size: 12px; border: none;"
            ))
            if compact:
                for child_row in state["container"].findChildren(QWidget):
                    if child_row.objectName() == "ChildRowContainer":
                        child_row.setFixedHeight(24 if reference_catalog else 22)
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
                    background-color: @finance_surface_alt;
                    border-left: 3px solid @finance_breadcrumb_active;
                    border-top: none;
                    border-right: none;
                    border-bottom: none;
                    border-radius: 0px 8px 8px 0px;
                    margin: 0px 4px 0px 10px;
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
        if self._active_stays_expanded:
            return
        if self.is_expanded:
            self.collapse()
        else:
            self.expand()

    def expand(self):
        for group in self.parent_menu.accordion_groups:
            if (group != self and group.is_expanded
                    and not group._active_stays_expanded
                    and not getattr(group, "_keep_open_when_other_expands", False)):
                group.collapse()

        self.is_expanded = True
        self.arrow_label.setText("v")
        self.arrow_label.setStyleSheet(theme_qss("background: transparent; color: @selection_text; font-size: 10px; border: none; margin: 0px;"))
        self.setStyleSheet(theme_qss(
            "QWidget#AccordionItemRoot { background: transparent; border: none; border-radius: 0px; }"
        ))
        self._toggle_row.setStyleSheet(self._row_qss(False))
        self._title_lbl.setStyleSheet(theme_qss("background: transparent; color: @selection_text; font-size: 13px; font-weight: 700; border: none; margin: 0px; padding: 0px;"))
        self._icon_lbl.setStyleSheet(theme_qss(
            "background: transparent; color: @accent; font-size: 14px; border: none; margin: 0px; padding: 0px;"
        ))
        
        self.sub_container.show()
        visible_rows = sum(1 for row, *_rest in self._child_rows if row.isVisible() or row.isEnabled())
        nested_height = sum(
            state["container"].sizeHint().height()
            for state in self.nested_groups
            if state["container"].isVisible()
        )
        content_height = max(
            self.sub_container.layout().sizeHint().height() + 4,
            (visible_rows * 44) + (len(self.nested_groups) * 44) + nested_height + 8,
        )
        self.anim = QPropertyAnimation(self.sub_container, b"maximumHeight")
        self.anim.setDuration(200)
        self.anim.setStartValue(self.sub_container.height())
        self.anim.setEndValue(content_height)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.finished.connect(lambda: self.sub_container.setMaximumHeight(16777215))
        self.anim.start()
        ensure_visible = getattr(self.parent_menu, "ensure_item_visible", None)
        if callable(ensure_visible):
            QTimer.singleShot(60, lambda callback=ensure_visible: callback(self))

    def collapse(self):
        self.is_expanded = False
        self.arrow_label.setText(">")
        self.arrow_label.setStyleSheet(theme_qss("background: transparent; color: @text_muted; font-size: 14px; border: none; margin: 0px;"))
        self.setStyleSheet("")
        self._toggle_row.setStyleSheet(self._row_qss(False))
        self._title_lbl.setStyleSheet(theme_qss("background: transparent; color: @text; font-size: 13px; font-weight: 600; border: none; margin: 0px; padding: 0px;"))
        self._icon_lbl.setStyleSheet("background: transparent; font-size: 14px; border: none; margin: 0px; padding: 0px;")

        self.anim = QPropertyAnimation(self.sub_container, b"maximumHeight")
        self.anim.setDuration(160)
        self.anim.setStartValue(self.sub_container.height())
        self.anim.setEndValue(0)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.start()
