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
    QSizeGrip,
    QScrollArea,
)
from PyQt6.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve, QEvent
from PyQt6.QtGui import QColor, QFont, QPixmap, QPainter, QPainterPath
from src.utils.theme_colors import theme_qss
from src.utils.design_system import DesignTokens


class NoWheelScrollArea(QScrollArea):
    """Scroll area that only scrolls via scrollbar/keyboard, not mouse wheel."""

    def wheelEvent(self, event):
        event.ignore()


class ModernDialog(QtDialog):
    """
    AYEC Pro Web-Style Modal Dialog.
    Features:
    - Centered card with soft shadow
    - Integrated DesignTokens
    """

    def __init__(self, title="Dialog", parent=None, width=600, height=500, blur_background=False, **kwargs):
        # Backward compatibility:
        # - ModernDialog("Title", parent, ...)
        # - ModernDialog(parent, title="Title", ...)
        if parent is None and title is not None and not isinstance(title, str):
            parent = title
            title = kwargs.pop("title", "Dialog")

        super().__init__(parent)
        self._dialog_width = width
        self._dialog_height = height
        self._blur_background = blur_background
        self._allow_wheel_scroll = False

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

    def setup_ui(self, width, height):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

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
                padding: 8px 10px;
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
            #ModernDialogCard QComboBox::down-arrow {
                image: none;
                width: 12px;
                height: 12px;
            }
            QComboBox QAbstractItemView {
                background-color: @surface;
                color: @text;
                border: 1px solid @border;
                selection-background-color: @selection_bg;
                selection-color: @selection_text;
                outline: none;
            }
            #ModernDialogCard QLineEdit::placeholder,
            #ModernDialogCard QTextEdit::placeholder,
            #ModernDialogCard QPlainTextEdit::placeholder {
                color: @text_muted;
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

    def add_widget(self, widget):
        self.content_layout.addWidget(widget)

    def add_layout(self, layout):
        self.content_layout.addLayout(layout)

    def add_button(self, text, variant="primary", callback=None):
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

    def eventFilter(self, obj, event):
        if (
            not self._allow_wheel_scroll
            and event.type() == QEvent.Type.Wheel
        ):
            event.ignore()
            return True
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
            self.card.resize(self._dialog_width, self._dialog_height)
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

        self.card.setFixedSize(target_width, target_height)
        self.resize(target_width, target_height)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if hasattr(self, "old_pos"):
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()

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
        try:
            for scroll_area in self.findChildren(QScrollArea):
                self._apply_no_wheel_policy(scroll_area)
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
