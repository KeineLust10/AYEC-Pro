# -*- coding: utf-8 -*-
# _tp_styles.py

from PyQt6.QtWidgets import (
    QApplication, QFrame, QLabel, QPushButton, QLineEdit, QTextEdit, 
    QPlainTextEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox, 
    QTimeEdit, QTableWidget, QGroupBox, QScrollArea, QTabWidget, QTabBar, QWidget,
    QVBoxLayout
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from src.utils.theme_colors import theme_qss
from src.utils.design_system import DesignTokens
from src.utils.appearance_mode import AppearanceModeManager
from src.utils.logger import logger

class _TpStyles:
    def _technician_tabs_qss(self):
        if self._is_classic_appearance():
            return """
            QTabWidget#TechnicianPanelTabs {
                background: #F3F4F6;
                color: #111827;
            }
            QTabWidget#TechnicianPanelTabs::pane {
                background: #F3F4F6;
                border: 1px solid #B8C0CC;
                border-radius: 0px;
                top: -1px;
            }
            QTabWidget#TechnicianPanelTabs QTabBar,
            QTabBar {
                background: #F3F4F6;
                color: #111827;
                border: none;
            }
            QTabWidget#TechnicianPanelTabs QTabBar::tab {
                background: #E5E7EB;
                color: #111827;
                border: 1px solid #B8C0CC;
                border-bottom: 1px solid #B8C0CC;
                padding: 7px 14px;
                margin-right: 2px;
                min-width: 112px;
                min-height: 24px;
                font-size: 11px;
                font-weight: 700;
            }
            QTabBar::tab {
                background: #E5E7EB;
                color: #111827;
                border: 1px solid #B8C0CC;
                border-bottom: 1px solid #B8C0CC;
                padding: 7px 14px;
                margin-right: 2px;
                min-width: 112px;
                min-height: 24px;
                font-size: 11px;
                font-weight: 700;
            }
            QTabWidget#TechnicianPanelTabs QTabBar::tab:selected {
                background: #FFFFFF;
                color: #0F3F74;
                border-bottom-color: #FFFFFF;
            }
            QTabBar::tab:selected {
                background: #FFFFFF;
                color: #0F3F74;
                border-bottom-color: #FFFFFF;
            }
            QTabWidget#TechnicianPanelTabs QTabBar::tab:hover {
                background: #F8FAFC;
                color: #111827;
            }
            QTabBar::tab:hover {
                background: #F8FAFC;
                color: #111827;
            }
            """
        return theme_qss(f"""
            QTabWidget::pane {{
                border: 1px solid {DesignTokens.BORDER};
                border-radius: {DesignTokens.RADIUS_LG};
                background: white;
                top: -1px;
            }}
            QTabBar::tab {{
                background: @surface_alt;
                color: @text_muted;
                padding: 8px 18px;
                margin-right: 6px;
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                font-weight: 700;
                font-size: 12px;
                border: 1px solid @border;
                border-bottom: none;
                min-width: 120px;
            }}
            QTabBar::tab:selected {{
                background: white;
                color: @accent;
                border-bottom: 3px solid @accent;
                padding-bottom: 12px;
            }}
            QTabBar::tab:hover {{
                background: @surface_alt;
            }}
        """)

    def _classic_panel_qss(self):
        return """
            QDialog, QWidget {
                background: #F3F4F6;
                color: #111827;
            }
            QLabel {
                color: #111827;
                background: transparent;
                border: none;
            }
            QFrame {
                background: #FFFFFF;
                color: #111827;
                border: 1px solid #B8C0CC;
                border-radius: 0px;
            }
            QScrollArea {
                background: #F3F4F6;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background: #F3F4F6;
            }
            QScrollBar:vertical {
                background: #EEF2F7;
                width: 10px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background: #AEB4BD;
                min-height: 24px;
                border-radius: 0px;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """

    def _classic_group_qss(self):
        return """
            QGroupBox {
                background-color: #FFFFFF;
                color: #111827;
                border: 1px solid #B8C0CC;
                border-radius: 0px;
                margin-top: 12px;
                padding: 18px 8px 8px 8px;
                font-weight: 700;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 8px;
                padding: 0 4px;
                background-color: #FFFFFF;
                color: #111827;
                border: 0px;
            }
            QGroupBox QWidget {
                background: #FFFFFF;
                color: #111827;
            }
            QGroupBox QFrame {
                background: #FFFFFF;
                color: #111827;
                border: 1px solid #B8C0CC;
                border-radius: 0px;
            }
            QGroupBox QLabel {
                background: transparent;
                color: #111827;
                border: none;
            }
            QWidget#ClassicQuickToggleItem,
            QWidget#ClassicAccessoryToggleItem {
                background: #FFFFFF;
                color: #111827;
                border: 1px solid #D1D5DB;
                border-radius: 0px;
            }
        """

    def _classic_input_qss(self):
        return """
            QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QDateEdit,
            QSpinBox, QDoubleSpinBox, QTimeEdit {
                background: #FFFFFF;
                color: #111827;
                border: 1px solid #AEB4BD;
                border-radius: 2px;
                padding: 5px 7px;
                min-height: 24px;
                selection-background-color: #DCEBFF;
                selection-color: #111827;
            }
            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
                border-color: #1F4E79;
                background: #FFFFFF;
            }
            QComboBox::drop-down {
                width: 24px;
                border-left: 1px solid #B8C0CC;
                background: #E5E7EB;
            }
            QTextEdit QWidget, QPlainTextEdit QWidget {
                background: #FFFFFF;
                color: #111827;
            }
        """

    def _classic_button_qss(self, primary=False):
        if primary:
            return """
                QPushButton {
                    background: #2F7DEB;
                    color: #FFFFFF;
                    border: 1px solid #1D5FB8;
                    border-radius: 3px;
                    padding: 6px 12px;
                    min-height: 26px;
                    font-weight: 700;
                }
                QPushButton:hover { background: #2469C9; }
            """
        return """
            QPushButton {
                background: #FFFFFF;
                color: #111827;
                border: 1px solid #AEB4BD;
                border-radius: 2px;
                padding: 6px 12px;
                min-height: 26px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #F3F4F6;
                border-color: #1F4E79;
            }
        """

    def _classic_table_qss(self):
        return """
            QTableWidget {
                background: #FFFFFF;
                color: #111827;
                alternate-background-color: #F7F8FA;
                gridline-color: #D1D5DB;
                border: 1px solid #B8C0CC;
                border-radius: 0px;
                selection-background-color: #DCEBFF;
                selection-color: #111827;
                outline: none;
            }
            QTableWidget::item {
                color: #111827;
                padding: 6px;
                border-bottom: 1px solid #E5E7EB;
                outline: none;
            }
            QTableWidget::item:selected {
                background-color: #DCEBFF;
                color: #111827;
                outline: none;
            }
            QTableWidget::item:focus {
                outline: none;
                border: none;
            }
            QHeaderView::section {
                background: #E5E7EB;
                color: #111827;
                padding: 6px;
                border: 1px solid #B8C0CC;
                font-weight: 700;
            }
        """

    def _classic_container_qss(self, surface="#F3F4F6", border="none"):
        return f"background-color: {surface}; color: #111827; border: {border}; border-radius: 0px;"

    def _set_raw_stylesheet(self, widget, qss):
        if widget is None:
            return
        try:
            widget.setProperty("skipThemeTransform", False)
        except Exception:
            pass
        widget.setStyleSheet(theme_qss(qss))

    def _set_classic_surface(self, widget, surface="#F3F4F6", border="none"):
        if widget is None:
            return
        widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        widget.setAutoFillBackground(True)
        name = widget.objectName()
        if name:
            selector = f"{widget.metaObject().className()}#{name}"
        else:
            selector = widget.metaObject().className()
        self._set_raw_stylesheet(
            widget,
            f"{selector} {{ {self._classic_container_qss(surface, border)} }}"
        )

    def _apply_classic_panel_shell_styles(self):
        """Style only the visible dialog shell before the first tab is built."""
        if not self._is_classic_appearance():
            return
        self._set_raw_stylesheet(
            self,
            self._classic_panel_qss()
            + self._classic_group_qss()
            + self._classic_input_qss(),
        )
        if hasattr(self, "card"):
            self._set_raw_stylesheet(
                self.card,
                """
                QFrame#ModernDialogCard {
                    background: #FFFFFF;
                    border: 1px solid #AEB4BD;
                    border-radius: 2px;
                }
                QFrame#ModernDialogCard QLabel { color: #111827; }
                """,
            )
            effect = self.card.graphicsEffect()
            if effect is not None:
                effect.setEnabled(False)
        if hasattr(self, "header"):
            self.header.setFixedHeight(48)
            self._set_raw_stylesheet(
                self.header,
                """
                QFrame {
                    background: #FFFFFF;
                    border-bottom: 1px solid #B8C0CC;
                    border-top-left-radius: 2px;
                    border-top-right-radius: 2px;
                }
                """,
            )
        if hasattr(self, "content_container"):
            self._set_raw_stylesheet(
                self.content_container,
                "QFrame#ModernDialogContent { background: #F3F4F6; border: none; }",
            )
        if hasattr(self, "scroll_area"):
            self._set_raw_stylesheet(
                self.scroll_area,
                """
                QScrollArea { background: #F3F4F6; border: none; }
                QScrollArea > QWidget > QWidget { background: #F3F4F6; }
                QScrollArea::viewport { background: #F3F4F6; }
                """,
            )
        if hasattr(self, "footer"):
            self._set_raw_stylesheet(
                self.footer,
                "background: #E5E7EB; border-top: 1px solid #B8C0CC; border-radius: 0px;",
            )
        if hasattr(self, "tabs"):
            self.tabs.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            self._set_raw_stylesheet(self.tabs, self._technician_tabs_qss())

    def _scrub_classic_panel_colors(self):
        if not self._is_classic_appearance():
            return
        if getattr(self, "_classic_style_scrub_running", False):
            return
        self._classic_style_scrub_running = True

        try:
            open_surface = "#F3F4F6"
            card_surface = "#FFFFFF"
            classic_border = "1px solid #B8C0CC"

            self._set_raw_stylesheet(
                self,
                self._classic_panel_qss() + self._classic_group_qss() + self._classic_input_qss(),
            )
            self._set_classic_surface(getattr(self, "content_container", None), open_surface)
            self._set_classic_surface(getattr(self, "general_widget", None), open_surface)
            for obj_name in (
                "TechnicianPanelLeftContainer",
                "TechnicianPanelRightContainer",
                "TechnicianPanelRightStack",
                "TechnicianPanelMainArea",
            ):
                self._set_classic_surface(self.findChild(QWidget, obj_name), open_surface)

            for card in self.findChildren(QFrame, "TechnicianPanelGeneralCard"):
                self._set_classic_surface(card, card_surface, classic_border)

            for group in self.findChildren(QGroupBox):
                group.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
                group.setAutoFillBackground(True)
                self._set_raw_stylesheet(group, self._classic_group_qss())

            for frame in self.findChildren(QFrame):
                name = frame.objectName() or ""
                if name in {"ModernDialogCard"}:
                    continue
                if name == "ModernDialogContent":
                    self._set_classic_surface(frame, open_surface)
                elif name == "TechnicianPanelGeneralCard":
                    self._set_classic_surface(frame, card_surface, classic_border)
                elif name:
                    self._set_classic_surface(frame, card_surface, classic_border)

            for page_name in ("wizard_page1", "wizard_page2", "wizard_page3"):
                page = getattr(self, page_name, None)
                if page is not None:
                    self._set_classic_surface(page, open_surface)

            toggle_qss = """
                QWidget#ClassicQuickToggleItem,
                QWidget#ClassicAccessoryToggleItem {
                    background: #FFFFFF;
                    color: #111827;
                    border: 1px solid #D1D5DB;
                    border-radius: 0px;
                }
                QWidget#ClassicQuickToggleItem QLabel,
                QWidget#ClassicAccessoryToggleItem QLabel {
                    background: transparent;
                    color: #111827;
                    border: none;
                }
            """
            for widget in self.findChildren(QWidget):
                if widget.objectName() in {"ClassicQuickToggleItem", "ClassicAccessoryToggleItem"}:
                    widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
                    self._set_raw_stylesheet(widget, toggle_qss)
                elif isinstance(widget, QLabel):
                    self._set_raw_stylesheet(widget, "background: transparent; color: #111827; border: none;")

            input_types = (
                QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QDateEdit,
                QSpinBox, QDoubleSpinBox, QTimeEdit,
            )
            for input_type in input_types:
                for editor in self.findChildren(input_type):
                    self._set_raw_stylesheet(editor, self._classic_input_qss())
                    if isinstance(editor, (QTextEdit, QPlainTextEdit)):
                        self._set_raw_stylesheet(editor.viewport(), "background: #FFFFFF; color: #111827; border: none;")

            for table in self.findChildren(QTableWidget):
                self._set_raw_stylesheet(table, self._classic_table_qss())

            for button in self.findChildren(QPushButton):
                is_primary = button.text() in {
                    "Güncellemeleri Kaydet",
                    "Galeriyi Aç",
                    "Galeriyi A\u00e7",
                    "Kaydet",
                }
                self._set_raw_stylesheet(button, self._classic_button_qss(primary=is_primary))

            if hasattr(self, "tabs"):
                self.tabs.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
                self._set_raw_stylesheet(self.tabs, self._technician_tabs_qss())
                tab_bar = self.tabs.findChild(QTabBar)
                if tab_bar is not None:
                    tab_bar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
                    tab_bar.setAutoFillBackground(True)
                    self._set_raw_stylesheet(tab_bar, """
                        QTabBar {
                            background: #F3F4F6;
                            color: #111827;
                            border: none;
                        }
                        QTabBar::tab {
                            background: #E5E7EB;
                            color: #111827;
                            border: 1px solid #B8C0CC;
                            border-bottom: 1px solid #B8C0CC;
                            padding: 7px 14px;
                            margin-right: 2px;
                            min-width: 112px;
                            min-height: 24px;
                            font-size: 11px;
                            font-weight: 700;
                        }
                        QTabBar::tab:selected {
                            background: #FFFFFF;
                            color: #0F3F74;
                            border-bottom-color: #FFFFFF;
                        }
                        QTabBar::tab:hover {
                            background: #F8FAFC;
                            color: #111827;
                        }
                    """)
            if hasattr(self, "btn_close"):
                self._set_raw_stylesheet(self.btn_close, self._classic_button_qss())
            pattern_widget = getattr(getattr(self, "wizard_page1", None), "pattern_widget", None)
            if pattern_widget is not None:
                pattern_widget.update()
        finally:
            self._classic_style_scrub_running = False

    def _apply_classic_panel_styles(self):
        if not self._is_classic_appearance():
            return
        self._set_raw_stylesheet(self, self._classic_panel_qss() + self._classic_group_qss() + self._classic_input_qss())
        if hasattr(self, "card"):
            self._set_raw_stylesheet(self.card, """
                QFrame#ModernDialogCard {
                    background: #FFFFFF;
                    border: 1px solid #AEB4BD;
                    border-radius: 2px;
                }
                QFrame#ModernDialogCard QLabel { color: #111827; }
            """)
            effect = self.card.graphicsEffect()
            if effect is not None:
                effect.setEnabled(False)
        if hasattr(self, "header"):
            self.header.setFixedHeight(48)
            self._set_raw_stylesheet(self.header, """
                QFrame {
                    background: #FFFFFF;
                    border-bottom: 1px solid #B8C0CC;
                    border-top-left-radius: 2px;
                    border-top-right-radius: 2px;
                }
            """)
        if hasattr(self, "content_container"):
            self._set_raw_stylesheet(
                self.content_container,
                "QFrame#ModernDialogContent { background: #F3F4F6; border: none; }"
            )
        if hasattr(self, "scroll_area"):
            self._set_raw_stylesheet(self.scroll_area, """
                QScrollArea { background: #F3F4F6; border: none; }
                QScrollArea > QWidget > QWidget { background: #F3F4F6; }
            """)
        if hasattr(self, "footer"):
            self._set_raw_stylesheet(
                self.footer,
                "background: #E5E7EB; border-top: 1px solid #B8C0CC; border-radius: 0px;"
            )
        if hasattr(self, "tabs"):
            self._set_raw_stylesheet(self.tabs, self._technician_tabs_qss() + """
                QTabWidget#TechnicianPanelTabs QWidget#TechnicianPanelGeneral,
                QTabWidget#TechnicianPanelTabs QWidget#TechnicianPanelTest,
                QTabWidget#TechnicianPanelTabs QWidget#TechnicianPanelLog {
                    background: #F3F4F6;
                    color: #111827;
                }
                QTabWidget#TechnicianPanelTabs QFrame {
                    background: #FFFFFF;
                    color: #111827;
                    border: 1px solid #B8C0CC;
                }
                QTabWidget#TechnicianPanelTabs QLabel {
                    background: transparent;
                    color: #111827;
                    border: none;
                }
                QTabWidget#TechnicianPanelTabs QWidget#ClassicQuickToggleItem,
                QTabWidget#TechnicianPanelTabs QWidget#ClassicAccessoryToggleItem {
                    background: #FFFFFF;
                    color: #111827;
                    border: 1px solid #D1D5DB;
                    border-radius: 0px;
                }
                QTabWidget#TechnicianPanelTabs QWidget#ClassicQuickToggleItem QLabel,
                QTabWidget#TechnicianPanelTabs QWidget#ClassicAccessoryToggleItem QLabel {
                    background: transparent;
                    color: #111827;
                    border: none;
                }
            """)
        for name in ("general_widget", "test_widget", "log_widget"):
            page = getattr(self, name, None)
            if page is not None:
                self._set_classic_surface(page, "#F3F4F6", "none")
                page.setAutoFillBackground(True)
        if hasattr(self, "general_widget"):
            self._set_raw_stylesheet(self.general_widget, """
                QWidget#TechnicianPanelGeneral {
                    background: #F3F4F6;
                    color: #111827;
                }
                QWidget#TechnicianPanelGeneral QWidget {
                    background: #FFFFFF;
                    color: #111827;
                }
                QWidget#TechnicianPanelGeneral QScrollArea,
                QWidget#TechnicianPanelGeneral QScrollArea::viewport,
                QWidget#TechnicianPanelGeneral QScrollArea > QWidget > QWidget {
                    background: #F3F4F6;
                    color: #111827;
                    border: none;
                }
                QWidget#TechnicianPanelGeneral QFrame {
                    background: #FFFFFF;
                    color: #111827;
                    border: 1px solid #B8C0CC;
                    border-radius: 0px;
                }
                QWidget#TechnicianPanelGeneral QGroupBox {
                    background: #FFFFFF;
                    color: #111827;
                    border: 1px solid #B8C0CC;
                    border-radius: 0px;
                    margin-top: 12px;
                    padding: 18px 8px 8px 8px;
                    font-weight: 700;
                }
                QWidget#TechnicianPanelGeneral QGroupBox::title {
                    subcontrol-origin: margin;
                    subcontrol-position: top left;
                    left: 8px;
                    padding: 0 4px;
                    background: #FFFFFF;
                    color: #111827;
                }
                QWidget#TechnicianPanelGeneral QLabel {
                    background: transparent;
                    color: #111827;
                    border: none;
                }
                QWidget#TechnicianPanelGeneral QLineEdit,
                QWidget#TechnicianPanelGeneral QTextEdit,
                QWidget#TechnicianPanelGeneral QPlainTextEdit,
                QWidget#TechnicianPanelGeneral QComboBox,
                QWidget#TechnicianPanelGeneral QDateEdit {
                    background: #FFFFFF;
                    color: #111827;
                    border: 1px solid #AEB4BD;
                    border-radius: 2px;
                    padding: 5px 7px;
                }
                QWidget#TechnicianPanelGeneral QWidget#ClassicQuickToggleItem,
                QWidget#TechnicianPanelGeneral QWidget#ClassicAccessoryToggleItem {
                    background: #FFFFFF;
                    color: #111827;
                    border: 1px solid #D1D5DB;
                    border-radius: 0px;
                }
                QWidget#TechnicianPanelGeneral QWidget#ClassicQuickToggleItem QLabel,
                QWidget#TechnicianPanelGeneral QWidget#ClassicAccessoryToggleItem QLabel {
                    background: transparent;
                    color: #111827;
                    border: none;
                }
            """)
        container_names = (
            "wizard_page1", "wizard_page2", "wizard_page3", "content_container"
        )
        for name in container_names:
            widget = getattr(self, name, None)
            if widget is not None:
                self._set_classic_surface(widget, "#F3F4F6", "none")
                widget.setAutoFillBackground(True)
        for widget in self.findChildren(QWidget):
            if widget.objectName() in {"ClassicQuickToggleItem", "ClassicAccessoryToggleItem"}:
                continue
            if isinstance(widget, (QPushButton, QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox, QTimeEdit, QTableWidget, QGroupBox, QScrollArea, QTabWidget)):
                continue
            if isinstance(widget, QLabel):
                self._set_raw_stylesheet(widget, "background: transparent; color: #111827; border: none;")
                continue
            self._set_classic_surface(widget, "#F3F4F6", "none")
            widget.setAutoFillBackground(True)
        for frame in self.findChildren(QFrame):
            name = frame.objectName() or ""
            if name in {"ModernDialogContent"}:
                self._set_raw_stylesheet(frame, "QFrame#ModernDialogContent { background: #F3F4F6; color: #111827; border: none; border-radius: 0px; }")
            elif name in {"ModernDialogCard"}:
                continue
            else:
                self._set_classic_surface(frame, "#FFFFFF", "1px solid #B8C0CC")
        for scroll in self.findChildren(QScrollArea):
            self._set_raw_stylesheet(scroll, """
                QScrollArea { background: #F3F4F6; border: none; }
                QScrollArea > QWidget > QWidget { background: #F3F4F6; }
                QScrollArea::viewport { background: #F3F4F6; }
                QScrollBar:vertical { background: #EEF2F7; width: 10px; border: none; }
                QScrollBar::handle:vertical { background: #AEB4BD; min-height: 24px; border-radius: 0px; }
            """)
        for group in self.findChildren(QGroupBox):
            self._set_raw_stylesheet(group, self._classic_group_qss())
        input_types = (QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox, QTimeEdit)
        for input_type in input_types:
            for editor in self.findChildren(input_type):
                self._set_raw_stylesheet(editor, self._classic_input_qss())
                if isinstance(editor, (QTextEdit, QPlainTextEdit)):
                    self._set_raw_stylesheet(editor.viewport(), "background: #FFFFFF; color: #111827; border: none;")

        for table in self.findChildren(QTableWidget):
            self._set_raw_stylesheet(table, self._classic_table_qss())
        for button in self.findChildren(QPushButton):
            is_primary = button.text() in {"Güncellemeleri Kaydet", "Güncellemeleri Kaydet", "Galeriyi Aç", "Galeriyi A\u00e7"}
            self._set_raw_stylesheet(button, self._classic_button_qss(primary=is_primary))
        if hasattr(self, "btn_toggle_editor"):
            self._set_raw_stylesheet(self.btn_toggle_editor, self._classic_button_qss(primary=True))
        for page_name in ("wizard_page1", "wizard_page2", "wizard_page3"):
            page = getattr(self, page_name, None)
            if page is not None and hasattr(page, "apply_classic_styles"):
                page.apply_classic_styles()
        self._scrub_classic_panel_colors()

    def apply_theme_styles(self):
        if self._is_classic_appearance():
            self._apply_classic_panel_styles()

    def _schedule_classic_panel_styles(self):
        if not self._is_classic_appearance():
            return
        if getattr(self, "_classic_style_pending", False):
            return
        self._classic_style_pending = True

        def _apply():
            self._classic_style_pending = False
            try:
                self._apply_classic_panel_styles()
            except Exception as exc:
                logger.debug("Deferred classic technician style skipped: %s", exc)

        QTimer.singleShot(0, _apply)

    def _make_general_card(self, title):
        card = QFrame()
        card.setObjectName("TechnicianPanelGeneralCard")
        card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        card.setStyleSheet(
            theme_qss("""
            QFrame {
                background: @surface;
                border: 1px solid @border;
                border-radius: 12px;
            }
        """)
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 6, 8, 8)
        layout.setSpacing(4)
        title_label = QLabel(title)
        title_label.setFont(QFont(DesignTokens.FONT_FAMILY, 10, QFont.Weight.Bold))
        title_label.setStyleSheet(
            theme_qss(
                "color: @warning; background: transparent; border: none; letter-spacing: 0.2px;"
            )
        )
        layout.addWidget(title_label)
        return card
