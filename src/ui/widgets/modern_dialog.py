# -*- coding: utf-8 -*-

import os
from PyQt6.QtWidgets import (
    QDialog as QtDialog,
    QApplication,
    QVBoxLayout,
    QWidget,
    QFrame,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QGraphicsDropShadowEffect,
    QScrollArea,
    QAbstractScrollArea,
)
from PyQt6.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve, QEvent
from PyQt6.QtGui import QColor, QFont, QPixmap, QPainter, QPainterPath
from src.utils.theme_colors import theme_qss
from src.utils.design_system import DesignTokens
from src.utils.appearance_mode import AppearanceModeManager

if not os.environ.get("QT_QPA_FONTDIR"):
    windows_font_dir = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts")
    if os.path.isdir(windows_font_dir):
        os.environ["QT_QPA_FONTDIR"] = windows_font_dir


class NoWheelScrollArea(QScrollArea):
    """Scroll area that only scrolls via scrollbar/keyboard, not mouse wheel."""

    def wheelEvent(self, event):
        parent = self.parent()
        while parent is not None:
            if getattr(parent, "_allow_wheel_scroll", False):
                return super().wheelEvent(event)
            parent = parent.parent()
        event.ignore()


class ModernDialog(QtDialog):
    """
    AYEC Pro Web-Style Modal Dialog.
    Features:
    - Centered card with soft shadow
    - Integrated DesignTokens
    """

    def setStyleSheet(self, qss):
        safe_ui = getattr(self, "_safe_ui", False)
        bg_rule = "QDialog { background-color: @surface_alt; }" if safe_ui else "QDialog { background: transparent; }"
        if bg_rule not in qss:
            qss = bg_rule + "\n" + qss
        super().setStyleSheet(qss)

    def __init__(self, title="Dialog", parent=None, width=600, height=500, blur_background=False, **kwargs):
        # Backward compatibility:
        # - ModernDialog("Title", parent, ...)
        # - ModernDialog(parent, title="Title", ...)
        if parent is None and title is not None and not isinstance(title, str):
            parent = title
            title = kwargs.pop("title", "Dialog")

        super().__init__(parent)
        self.setProperty("skipThemeTransform", True)
        self._dialog_width = width
        self._dialog_height = height
        self._blur_background = blur_background
        self._allow_wheel_scroll = True
        self._drag_start_pos = None

        safe_ui_env = os.environ.get("AYECPRO_SAFE_UI", "").strip()
        if not safe_ui_env:
            safe_ui_env = os.environ.get("PB_SAFE_UI", "").strip()

        self._safe_ui = (safe_ui_env == "1")

        if self._safe_ui:
            self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.Window)
        else:
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._title = title or "Dialog"
        self.resize(width, height)
        ModernDialog.setup_ui(self, width, height)

    def _is_classic_appearance(self):
        app = QApplication.instance()
        return bool(app and app.property("appearanceMode") == AppearanceModeManager.CLASSIC)

    def _set_raw_stylesheet(self, widget, qss):
        if widget is None:
            return
        widget.setProperty("skipThemeTransform", False)
        widget.setStyleSheet(theme_qss(qss))

    def _apply_classic_chrome(self):
        if not self._is_classic_appearance():
            return
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self._set_raw_stylesheet(self, "QDialog { background: transparent; color: #111827; }")
        if hasattr(self, "card"):
            self._set_raw_stylesheet(self.card, """
                QFrame#ModernDialogCard {
                    background-color: #FFFFFF;
                    color: #111827;
                    border: 1px solid #AEB4BD;
                    border-radius: 2px;
                }
                QFrame#ModernDialogCard QLabel {
                    color: #111827;
                    background: transparent;
                    border: none;
                }
                QFrame#ModernDialogCard QLineEdit,
                QFrame#ModernDialogCard QTextEdit,
                QFrame#ModernDialogCard QPlainTextEdit,
                QFrame#ModernDialogCard QComboBox,
                QFrame#ModernDialogCard QDateEdit,
                QFrame#ModernDialogCard QSpinBox,
                QFrame#ModernDialogCard QDoubleSpinBox,
                QFrame#ModernDialogCard QTimeEdit {
                    background-color: #FFFFFF;
                    color: #111827;
                    border: 1px solid #AEB4BD;
                    border-radius: 2px;
                    padding: 5px 34px 5px 7px;
                    selection-background-color: #DCEBFF;
                    selection-color: #111827;
                }
                QFrame#ModernDialogCard QDateEdit::up-button,
                QFrame#ModernDialogCard QDateEdit::down-button,
                QFrame#ModernDialogCard QSpinBox::up-button,
                QFrame#ModernDialogCard QSpinBox::down-button,
                QFrame#ModernDialogCard QDoubleSpinBox::up-button,
                QFrame#ModernDialogCard QDoubleSpinBox::down-button,
                QFrame#ModernDialogCard QTimeEdit::up-button,
                QFrame#ModernDialogCard QTimeEdit::down-button {
                    width: 26px;
                    subcontrol-origin: border;
                    background-color: #DCEBFF;
                    border-left: 1px solid #AEB4BD;
                }
                QFrame#ModernDialogCard QDateEdit::up-button,
                QFrame#ModernDialogCard QSpinBox::up-button,
                QFrame#ModernDialogCard QDoubleSpinBox::up-button,
                QFrame#ModernDialogCard QTimeEdit::up-button {
                    subcontrol-position: top right;
                    border-bottom: 1px solid #AEB4BD;
                }
                QFrame#ModernDialogCard QDateEdit::down-button,
                QFrame#ModernDialogCard QSpinBox::down-button,
                QFrame#ModernDialogCard QDoubleSpinBox::down-button,
                QFrame#ModernDialogCard QTimeEdit::down-button {
                    subcontrol-position: bottom right;
                    border-top: 1px solid #AEB4BD;
                }
                QFrame#ModernDialogCard QDateEdit::up-arrow,
                QFrame#ModernDialogCard QSpinBox::up-arrow,
                QFrame#ModernDialogCard QDoubleSpinBox::up-arrow,
                QFrame#ModernDialogCard QTimeEdit::up-arrow {
                    image: none;
                    width: 0px;
                    height: 0px;
                    border-left: 4px solid transparent;
                    border-right: 4px solid transparent;
                    border-bottom: 6px solid #111827;
                }
                QFrame#ModernDialogCard QDateEdit::down-arrow,
                QFrame#ModernDialogCard QSpinBox::down-arrow,
                QFrame#ModernDialogCard QDoubleSpinBox::down-arrow,
                QFrame#ModernDialogCard QTimeEdit::down-arrow {
                    image: none;
                    width: 0px;
                    height: 0px;
                    border-left: 4px solid transparent;
                    border-right: 4px solid transparent;
                    border-top: 6px solid #111827;
                }
                QFrame#ModernDialogCard QComboBox::drop-down {
                    width: 24px;
                    border-left: 1px solid #B8C0CC;
                    background: #E5E7EB;
                }
            """)
            effect = self.card.graphicsEffect()
            if effect is not None:
                effect.setEnabled(False)
        if hasattr(self, "header"):
            self.header.setFixedHeight(48)
            self._set_raw_stylesheet(self.header, """
                QFrame {
                    background-color: #FFFFFF;
                    border-bottom: 1px solid #B8C0CC;
                    border-top-left-radius: 2px;
                    border-top-right-radius: 2px;
                }
            """)
        if hasattr(self, "lbl_title"):
            self._set_raw_stylesheet(self.lbl_title, "color: #111827; background: transparent; border: none; font-weight: 700;")
        if hasattr(self, "btn_close"):
            self._set_raw_stylesheet(self.btn_close, """
                QPushButton {
                    background: #FFFFFF;
                    color: #111827;
                    border: 1px solid #AEB4BD;
                    border-radius: 2px;
                    font-size: 13px;
                    font-weight: 800;
                }
                QPushButton:hover {
                    background: #FEE2E2;
                    border-color: #DC2626;
                    color: #991B1B;
                }
            """)
        if hasattr(self, "scroll_area"):
            self._set_raw_stylesheet(self.scroll_area, """
                QScrollArea { background: #F3F4F6; border: none; }
                QScrollArea::viewport { background: #F3F4F6; border: none; }
                QScrollArea > QWidget > QWidget { background: #F3F4F6; }
                QScrollBar:vertical { background: #EEF2F7; width: 10px; border: none; }
                QScrollBar::handle:vertical { background: #AEB4BD; min-height: 24px; border-radius: 0px; }
            """)
        if hasattr(self, "content_container"):
            self._set_raw_stylesheet(self.content_container, "QFrame#ModernDialogContent { background: #F3F4F6; color: #111827; border: none; }")
        if hasattr(self, "footer"):
            self._set_raw_stylesheet(self.footer, "background: #E5E7EB; border-top: 1px solid #B8C0CC; border-radius: 0px;")

    def setup_ui(self, width, height):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        if getattr(self, "_safe_ui", False):
            self.setStyleSheet(theme_qss("QDialog { background-color: @surface_alt; }"))
        else:
            self.setStyleSheet("QDialog { background: transparent; }")

        self.card = QFrame()
        self.card.setMinimumSize(420, 240)
        self.card.resize(width, height)
        self.card.setObjectName("ModernDialogCard")
        self.card.setStyleSheet(
            theme_qss(
                """
            #ModernDialogCard {
                background-color: @surface;
                border: 1px solid @border;
                border-radius: 12px;
            }
            #ModernDialogCard QLabel {
                color: @text;
            }
            #ModernDialogCard QLineEdit,
            #ModernDialogCard QTextEdit,
            #ModernDialogCard QPlainTextEdit,
            #ModernDialogCard QComboBox,
            #ModernDialogCard QDateEdit,
            #ModernDialogCard QSpinBox,
            #ModernDialogCard QDoubleSpinBox,
            #ModernDialogCard QTimeEdit {
                background-color: @surface_alt;
                color: @text;
                border: 1px solid @border;
                border-radius: 8px;
                padding: 8px 38px 8px 10px;
            }
            #ModernDialogCard QLineEdit:focus,
            #ModernDialogCard QTextEdit:focus,
            #ModernDialogCard QPlainTextEdit:focus,
            #ModernDialogCard QComboBox:focus,
            #ModernDialogCard QDateEdit:focus,
            #ModernDialogCard QSpinBox:focus,
            #ModernDialogCard QDoubleSpinBox:focus,
            #ModernDialogCard QTimeEdit:focus {
                border-color: @accent;
            }
            #ModernDialogCard QComboBox::drop-down {
                width: 24px;
                border-left: 1px solid @border;
                background: @surface;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
            }
            #ModernDialogCard QDateEdit::up-button,
            #ModernDialogCard QDateEdit::down-button,
            #ModernDialogCard QSpinBox::up-button,
            #ModernDialogCard QSpinBox::down-button,
            #ModernDialogCard QDoubleSpinBox::up-button,
            #ModernDialogCard QDoubleSpinBox::down-button,
            #ModernDialogCard QTimeEdit::up-button,
            #ModernDialogCard QTimeEdit::down-button {
                width: 30px;
                subcontrol-origin: border;
                background-color: @accent;
                border-left: 1px solid @border;
            }
            #ModernDialogCard QDateEdit::up-button,
            #ModernDialogCard QSpinBox::up-button,
            #ModernDialogCard QDoubleSpinBox::up-button,
            #ModernDialogCard QTimeEdit::up-button {
                subcontrol-position: top right;
                border-bottom: 1px solid @border;
                border-top-right-radius: 8px;
            }
            #ModernDialogCard QDateEdit::down-button,
            #ModernDialogCard QSpinBox::down-button,
            #ModernDialogCard QDoubleSpinBox::down-button,
            #ModernDialogCard QTimeEdit::down-button {
                subcontrol-position: bottom right;
                border-top: 1px solid @border;
                border-bottom-right-radius: 8px;
            }
            #ModernDialogCard QDateEdit::up-arrow,
            #ModernDialogCard QSpinBox::up-arrow,
            #ModernDialogCard QDoubleSpinBox::up-arrow,
            #ModernDialogCard QTimeEdit::up-arrow {
                image: none;
                width: 0px;
                height: 0px;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-bottom: 7px solid @selection_text;
            }
            #ModernDialogCard QDateEdit::down-arrow,
            #ModernDialogCard QSpinBox::down-arrow,
            #ModernDialogCard QDoubleSpinBox::down-arrow,
            #ModernDialogCard QTimeEdit::down-arrow {
                image: none;
                width: 0px;
                height: 0px;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 7px solid @selection_text;
            }
            #ModernDialogCard QComboBox::down-arrow {
                image: none;
            }
            QComboBox QAbstractItemView {
                background-color: @surface;
                color: @text;
                border: 1px solid @border;
                selection-background-color: @selection_bg;
                selection-color: @selection_text;
                outline: none;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: @surface_alt;
                color: @text;
            }
            #ModernDialogCard QCheckBox,
            #ModernDialogCard QRadioButton {
                color: @text;
                font-weight: 600;
            }
            #ModernDialogCard QCheckBox::indicator,
            #ModernDialogCard QRadioButton::indicator {
                width: 14px;
                height: 14px;
            }
            #ModernDialogCard *:disabled {
                color: @text_muted;
            }
        """
            )
        )

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 10)
        self.card.setGraphicsEffect(shadow)

        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(0, 0, 0, 0)
        self.card_layout.setSpacing(0)

        self.header = QFrame()
        self.header.setFixedHeight(60)
        self.header.setStyleSheet(
            theme_qss(
                """
            QFrame {
                background-color: @surface_alt;
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                border-bottom: 1px solid @border;
            }
        """
            )
        )
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(20, 0, 14, 0)

        self.lbl_title = QLabel(self._title)
        self.lbl_title.setFont(QFont(DesignTokens.FONT_FAMILY, 14, QFont.Weight.Bold))
        self.lbl_title.setStyleSheet(
            theme_qss("color: @text; border: none; font-weight: bold;")
        )

        self.btn_close = QPushButton("x")
        self.btn_close.setFixedSize(36, 36)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setStyleSheet(
            theme_qss(
                """
            QPushButton {
                background: @surface;
                border: 1px solid @border;
                color: @text;
                font-size: 18px;
                font-weight: 800;
                border-radius: 18px;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.14);
                border-color: #EF4444;
                color: #EF4444;
            }
        """
            )
        )
        self.btn_close.clicked.connect(self.reject)

        self.logo_label = QLabel()
        self.logo_label.setFixedSize(40, 40)
        self.logo_label.setScaledContents(True)

        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        candidates = [
            os.path.join(project_root, "assets", "ayec_logo.png"),
            os.path.join(project_root, "assets", "logo.png"),
            r"c:\Users\Admin\Desktop\Premium AYEC - Kopya\assets\ayec_logo.png",
        ]

        found_logo = next((cand for cand in candidates if os.path.exists(cand)), None)

        if found_logo:
            src_pix = QPixmap(found_logo)
            dest_pix = QPixmap(40, 40)
            dest_pix.fill(Qt.GlobalColor.transparent)
            painter = QPainter(dest_pix)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            path = QPainterPath()
            path.addEllipse(0, 0, 40, 40)
            painter.setClipPath(path)
            painter.drawPixmap(
                0,
                0,
                src_pix.scaled(
                    40,
                    40,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                ),
            )
            painter.end()
            self.logo_label.setPixmap(dest_pix)
        else:
            self.logo_label.setText("AYEC")
            self.logo_label.setStyleSheet(
                theme_qss(
                    "color: @text; font-weight: bold; border: 1px solid @text; border-radius: 20px;"
                )
            )
            self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        header_layout.addWidget(self.logo_label)
        header_layout.addSpacing(10)
        header_layout.addWidget(self.lbl_title)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_close)
        self.card_layout.addWidget(self.header)

        self.scroll_area = NoWheelScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_area.setStyleSheet(
            theme_qss(
                """
                QScrollArea {
                    background: transparent;
                    border: none;
                }
                QScrollArea > QWidget > QWidget {
                    background: transparent;
                }
                QScrollBar:vertical {
                    width: 10px;
                    background: transparent;
                    margin: 4px 2px 4px 0;
                    border: none;
                }
                QScrollBar::handle:vertical {
                    background: @border;
                    border-radius: 5px;
                    min-height: 24px;
                    border: none;
                }
                QScrollBar::handle:vertical:hover {
                    background: @text_muted;
                }
                QScrollBar::add-line:vertical,
                QScrollBar::sub-line:vertical {
                    height: 0px;
                    border: none;
                    background: transparent;
                }
                QScrollBar::add-page:vertical,
                QScrollBar::sub-page:vertical {
                    background: transparent;
                    border: none;
                }
                """
            )
        )

        self.content_container = QFrame()
        self.content_container.setObjectName("ModernDialogContent")
        self.content_container.setStyleSheet(
            theme_qss("#ModernDialogContent { background: transparent; border: none; }")
        )
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(12, 12, 16, 12)
        self.content_layout.setSpacing(12)

        self.scroll_area.setWidget(self.content_container)
        self._apply_no_wheel_policy(self.scroll_area)
        self.card_layout.addWidget(self.scroll_area, 1)

        self.footer = QFrame()
        self.footer.setFixedHeight(74)
        self.footer.setStyleSheet(
            theme_qss(
                """
                border-top: 1px solid @border;
                background: @surface_alt;
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
                """
            )
        )
        self.footer_layout = QHBoxLayout(self.footer)
        self.footer_layout.setContentsMargins(30, 0, 30, 0)
        self.footer_layout.setSpacing(15)

        self.card_layout.addWidget(self.footer)
        self.main_layout.addWidget(self.card)
        self._apply_classic_chrome()

    def add_widget(self, widget):
        self.content_layout.addWidget(widget)
        self._apply_wheel_bridge_recursive(widget)

    def add_layout(self, layout):
        self.content_layout.addLayout(layout)

    def add_button(self, text, variant="primary", callback=None):
        if not self.footer.isVisible():
            self.set_footer_visible(True)
        btn = QPushButton(text)
        btn.setFixedHeight(45)
        btn.setStyleSheet(theme_qss(DesignTokens.get_button_qss(variant)))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if callback:
            btn.clicked.connect(callback)
        self.footer_layout.addWidget(btn)
        return btn

    def clear_footer(self):
        while self.footer_layout.count():
            item = self.footer_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def set_footer_visible(self, visible, height=80):
        self.footer.setVisible(visible)
        self.footer.setFixedHeight(height if visible else 0)

    def set_dialog_size(self, width, height):
        self._dialog_width = width
        self._dialog_height = height
        self.resize(width, height)
        self.card.resize(width, height)

    def set_wheel_scroll_enabled(self, enabled: bool):
        self._allow_wheel_scroll = enabled

    def _apply_no_wheel_policy(self, scroll_area):
        if scroll_area is None:
            return
        scroll_area.viewport().installEventFilter(self)
        vbar = scroll_area.verticalScrollBar()
        if vbar is not None:
            vbar.installEventFilter(self)
        hbar = scroll_area.horizontalScrollBar()
        if hbar is not None:
            hbar.installEventFilter(self)

    def _apply_wheel_bridge_recursive(self, widget):
        if widget is None:
            return
        try:
            widget.installEventFilter(self)
            for child in widget.findChildren(QWidget):
                child.installEventFilter(self)
        except RuntimeError:
            return

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Wheel:
            if not self._allow_wheel_scroll:
                event.ignore()
                return True

            try:
                # Let nested scrollable widgets consume wheel events themselves.
                if isinstance(obj, QWidget):
                    parent = obj
                    while parent is not None:
                        if isinstance(parent, QAbstractScrollArea) and parent is not self.scroll_area:
                            bar = parent.verticalScrollBar()
                            if bar is not None and bar.isVisible() and bar.maximum() > 0:
                                return super().eventFilter(obj, event)
                        parent = parent.parentWidget()

                if (
                    isinstance(obj, QWidget)
                    and self.content_container is not None
                    and obj is not self.scroll_area.verticalScrollBar()
                    and obj is not self.scroll_area.horizontalScrollBar()
                    and (obj is self.content_container or self.content_container.isAncestorOf(obj))
                ):
                    delta = event.angleDelta().y()
                    if delta:
                        bar = self.scroll_area.verticalScrollBar()
                        if bar is not None and bar.isVisible():
                            bar.setValue(bar.value() - delta)
                            event.accept()
                            return True
            except RuntimeError:
                pass
        return super().eventFilter(obj, event)

    def _get_available_geometry(self):
        screen = None
        if self.parent():
            parent_win = self.parent().window()
            if parent_win is not None:
                screen = parent_win.screen()
        if screen is None and QApplication.instance() is not None:
            screen = QApplication.screenAt(self.pos())
        if screen is None and QApplication.instance() is not None:
            screen = QApplication.primaryScreen()
        return screen.availableGeometry() if screen is not None else None

    def _fit_to_screen(self):
        geometry = self._get_available_geometry()
        if geometry is None:
            self.resize(self._dialog_width, self._dialog_height)
            return

        max_width = max(420, geometry.width() - 48)
        max_height = max(260, geometry.height() - 48)
        try:
            if self.content_container is None:
                return
            content_hint = self.content_container.sizeHint()
        except RuntimeError:
            return
        target_width = min(max(self._dialog_width, content_hint.width() + 60), max_width)
        target_height = min(max(self._dialog_height, content_hint.height() + 150), max_height)

        self.setMinimumSize(420, 240)
        self.setMaximumSize(max_width, max_height)
        self.resize(target_width, target_height)

    def _is_header_drag_area(self, local_pos):
        try:
            if self.header is None or not self.header.isVisible():
                return False
            header_rect = self.header.geometry()
            if not header_rect.contains(local_pos):
                return False
            close_rect = self.btn_close.geometry().translated(header_rect.topLeft())
            return not close_rect.contains(local_pos)
        except RuntimeError:
            return False

    def mousePressEvent(self, event):
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self._is_header_drag_area(event.position().toPoint())
        ):
            self._drag_start_pos = event.globalPosition().toPoint()
            event.accept()
            return
        self._drag_start_pos = None
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_start_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self._drag_start_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self._drag_start_pos = event.globalPosition().toPoint()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_start_pos = None
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        return super().paintEvent(event)

    def add_cancel_button(self, text="İptal"):
        return self.add_button(text, "secondary", self.reject)

    def showEvent(self, event):
        try:
            self.card.setGraphicsEffect(None)
        except RuntimeError:
            super().showEvent(event)
            return
        self._fit_to_screen()
        if self.footer_layout.count() == 0:
            self.set_footer_visible(False)
        try:
            for scroll_area in self.findChildren(QScrollArea):
                self._apply_no_wheel_policy(scroll_area)
            self._apply_wheel_bridge_recursive(self.content_container)
        except RuntimeError:
            pass

        if self.parent():
            parent_win = self.parent().window()
            if parent_win and parent_win is not self:
                geometry = self._get_available_geometry() or parent_win.frameGeometry()
                center = geometry.center()
                self.move(
                    center.x() - (self.width() // 2),
                    center.y() - (self.height() // 2),
                )

        super().showEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def apply_theme_styles(self):
        """Re-applies background transparency after a theme change.

        Called by _main_window_base_mixin._refresh_visible_top_level_themes
        when the user switches themes while this dialog is open.  Without
        this, QSS-driven re-theming can strip WA_TranslucentBackground from
        the dialog, making the window chrome appear as a solid colour block
        instead of being transparent.
        """
        try:
            if getattr(self, "_safe_ui", False):
                # Safe-UI mode always uses an opaque window.
                self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
                self.setStyleSheet(
                    theme_qss("QDialog { background-color: @surface_alt; }")
                )
            else:
                # Normal mode \u2013 frameless + translucent, classic chrome on top.
                self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
                self.setStyleSheet("QDialog { background: transparent; }")
            # Re-apply classic chrome overrides if needed.
            self._apply_classic_chrome()
            # Re-apply card / header stylesheets so tokens are refreshed.
            if hasattr(self, "card"):
                self.card.setStyleSheet(
                    theme_qss(
                        """
                        #ModernDialogCard {
                            background-color: @surface;
                            border: 1px solid @border;
                            border-radius: 12px;
                        }
                        """
                    )
                )
            if hasattr(self, "header"):
                self.header.setStyleSheet(
                    theme_qss(
                        """
                        QFrame {
                            background-color: @surface_alt;
                            border-top-left-radius: 12px;
                            border-top-right-radius: 12px;
                            border-bottom: 1px solid @border;
                        }
                        """
                    )
                )
            if hasattr(self, "footer"):
                self.footer.setStyleSheet(
                    theme_qss(
                        """
                        border-top: 1px solid @border;
                        background: @surface_alt;
                        border-bottom-left-radius: 12px;
                        border-bottom-right-radius: 12px;
                        """
                    )
                )
            self.update()
        except Exception:
            pass
