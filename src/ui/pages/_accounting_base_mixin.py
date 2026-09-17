# -*- coding: utf-8 -*-

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from src.utils.appearance_mode import AppearanceModeManager
from src.utils.theme_colors import theme_qss

class AccountingBaseMixin:
    def _is_classic_appearance(self):
        return AppearanceModeManager.current(self.db) == AppearanceModeManager.CLASSIC

    def _classic_table_qss(self):
        return """
            QTableWidget {
                border: 1px solid #B8C0CC;
                background: #FFFFFF;
                alternate-background-color: #F7F8FA;
                gridline-color: #D1D5DB;
                color: #111827;
                font-size: 11px;
                selection-background-color: #DCEBFF;
                selection-color: #111827;
            }
            QTableWidget::item {
                padding: 4px 6px;
                border-bottom: 1px solid #D1D5DB;
            }
            QTableWidget QHeaderView::section,
            QHeaderView::section {
                background: #E5E7EB;
                color: #111827;
                padding: 5px 6px;
                border: 1px solid #B8C0CC;
                font-weight: 700;
            }
        """

    def _modern_table_qss(self):
        return theme_qss(
            """
            QTableWidget { border: none; font-size: 13px; selection-background-color: @border; selection-color: @selection_text; }
            QHeaderView::section { background-color: @surface_alt; color: @text_muted; border: none; border-bottom: 1px solid @border; padding: 12px; font-weight: 800; }
            QTableWidget::item { border-bottom: 1px solid @border; padding: 8px; color: @text; }
            QTableWidget::item:selected { background-color: @accent; color: @selection_text; border: none; outline: none; }
        """
        )

    def apply_theme_styles(self):
        classic = self._is_classic_appearance()
        self.setStyleSheet("background: #F3F4F6; color: #111827;" if classic else theme_qss("background: @window; color: @text;"))
        if hasattr(self, "tabs"):
            self.tabs.setStyleSheet(
                AppearanceModeManager.classic_tab_qss()
                if classic
                else theme_qss("QTabWidget::pane { background: @window; border: none; } QTabBar::tab { padding: 8px 14px; }")
            )
        if hasattr(self, "table"):
            self.table.setProperty("skipThemeTransform", False)
            self.table.setStyleSheet(self._classic_table_qss() if classic else self._modern_table_qss())
            self.table.horizontalHeader().setProperty("skipThemeTransform", False)
            if classic:
                self.table.horizontalHeader().setStyleSheet(
                    "QHeaderView::section { background: #E5E7EB; color: #111827; "
                    "border: 1px solid #B8C0CC; padding: 5px 6px; font-weight: 700; }"
                )
            else:
                self.table.horizontalHeader().setStyleSheet("")
            self.table.verticalHeader().setDefaultSectionSize(30 if classic else 55)
        for attr in ("table_container", "footer_frame", "right_panel", "quick_actions_container", "cards_container"):
            widget = getattr(self, attr, None)
            if widget is None:
                continue
            widget.setProperty("skipThemeTransform", False)
            if classic:
                widget.setStyleSheet("background: #FFFFFF; border: 1px solid #B8C0CC; border-radius: 0px;")

    def _animate_right_panel_width(self, target_width: int):
        panel = getattr(self, "right_panel", None)
        if not panel:
            return
        try:
            if self._right_panel_anim:
                self._right_panel_anim.stop()
        except Exception:
            pass
        self._right_panel_anim = QPropertyAnimation(panel, b"maximumWidth", self)
        self._right_panel_anim.setDuration(180)
        self._right_panel_anim.setStartValue(panel.width())
        self._right_panel_anim.setEndValue(target_width)
        self._right_panel_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        panel.setMinimumWidth(64 if target_width <= 80 else 390)
        self._right_panel_anim.start()

    def _expand_right_panel(self):
        if not getattr(self, "right_panel", None):
            return
        self._right_panel_collapsed = False
        self._set_right_panel_content_visible(True)
        self._animate_right_panel_width(390)

    def _collapse_right_panel(self):
        if not getattr(self, "right_panel", None):
            return
        if not getattr(self, "_right_panel_hover_enabled", True):
            return
        self._right_panel_collapsed = True
        self._set_right_panel_content_visible(False)
        self._animate_right_panel_width(64)

    def _set_right_panel_content_visible(self, visible: bool):
        for widget in (
            getattr(self, "quick_actions_container", None),
            getattr(self, "cards_container", None),
        ):
            if widget:
                widget.setVisible(visible)
        try:
            layout = self.right_panel.layout() if self.right_panel else None
            if layout:
                for i in range(layout.count()):
                    item = layout.itemAt(i)
                    widget = item.widget()
                    if widget and widget not in {
                        getattr(self, "right_panel_handle", None),
                        getattr(self, "btn_pin_shortcuts", None),
                    }:
                        widget.setVisible(visible)
        except Exception:
            pass

    def _relayout_summary_cards(self):
        if not hasattr(self, "cards_layout") or self.cards_layout is None:
            return
        if not self.card_widgets:
            return

        width = 0
        try:
            width = int(self.cards_container.width() or 0)
        except Exception:
            width = 0
        # The expanded panel is wide enough for a compact two-column summary.
        cols = 2 if width >= 360 else 1
        self._last_cols_cards = cols

        for card in self.card_widgets:
            self.cards_layout.removeWidget(card)

        for index, card in enumerate(self.card_widgets):
            row = index // cols
            col = index % cols
            self.cards_layout.addWidget(card, row, col)
            card.setVisible(True)

    def _relayout_quick_actions(self):
        if not hasattr(self, "quick_actions_layout") or self.quick_actions_layout is None:
            return
        if not self.quick_action_buttons:
            return
        cols = 2

        if getattr(self, "_last_cols_actions", None) == cols:
            for btn in self.quick_action_buttons:
                btn.setVisible(True)
            return
        self._last_cols_actions = cols

        for btn in self.quick_action_buttons:
            self.quick_actions_layout.removeWidget(btn)

        for index, btn in enumerate(self.quick_action_buttons):
            row = index // cols
            col = index % cols
            self.quick_actions_layout.addWidget(btn, row, col)
            btn.setVisible(True)

    def _clear_layout(self, layout):
        if not layout:
            return
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if child_layout is not None:
                self._clear_layout(child_layout)
            if widget is not None:
                widget.setParent(None)
