"""
Modern User Switch Dialog
Premium tasarimli kullanici degistir dialogu
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QFrame

from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.design_system import DesignTokens
from src.utils.theme_colors import theme_qss


class UserSwitchDialog(ModernDialog):
    """Modern ve premium kullanici degistir dialogu"""

    confirmed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(title="Kullanici Degistir", parent=parent, width=500, height=600)
        self.set_footer_visible(False)
        self.setup_ui()

    def setup_ui(self):
        layout = self.content_layout
        layout.setContentsMargins(15, 15, 15, 15)

        container = QFrame()
        container.setStyleSheet(
            theme_qss(
                f"""
                QFrame {{
                    background-color: {DesignTokens.BACKGROUND};
                    border-radius: 24px;
                }}
                """
            )
        )

        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(40, 40, 40, 40)
        container_layout.setSpacing(25)

        icon_container = QFrame()
        icon_container.setFixedSize(100, 100)
        icon_container.setStyleSheet(
            """
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #3b82f6, stop:1 #2563eb);
                border-radius: 50px;
            }
            """
        )

        icon_layout = QVBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)

        icon_label = QLabel("Kullanici")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        icon_label.setStyleSheet("background: transparent; color: white;")
        icon_layout.addWidget(icon_label)

        icon_h_layout = QHBoxLayout()
        icon_h_layout.addStretch()
        icon_h_layout.addWidget(icon_container)
        icon_h_layout.addStretch()
        container_layout.addLayout(icon_h_layout)

        title = QLabel("Kullanici Degistir")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("color: @text;"))
        container_layout.addWidget(title)

        message = QLabel(
            "Kullanici degistirmek icin programi yeniden baslatmaniz gerekiyor.\n\nDevam etmek istiyor musunuz?"
        )
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message.setWordWrap(True)
        message.setFont(QFont("Segoe UI", 13))
        message.setStyleSheet(theme_qss("color: @text_muted; line-height: 1.6;"))
        container_layout.addWidget(message)

        container_layout.addSpacing(10)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(15)

        btn_cancel = QPushButton("Iptal")
        btn_cancel.setFixedHeight(50)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        btn_cancel.setStyleSheet(
            theme_qss(
                """
                QPushButton {
                    background-color: @surface_alt;
                    color: @text;
                    border: none;
                    border-radius: 12px;
                    font-weight: 700;
                    font-size: 14px;
                    padding: 0 30px;
                }
                QPushButton:hover {
                    background-color: @border;
                }
                """
            )
        )

        btn_confirm = QPushButton("Evet, Degistir")
        btn_confirm.setFixedHeight(50)
        btn_confirm.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_confirm.clicked.connect(self.confirm_switch)
        btn_confirm.setStyleSheet(
            theme_qss(
                """
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 @accent, stop:1 @accent);
                    color: @selection_text;
                    border: none;
                    border-radius: 12px;
                    font-weight: 700;
                    font-size: 14px;
                    padding: 0 30px;
                }
                QPushButton:hover {
                    opacity: 0.8;
                }
                QPushButton:pressed {
                    background: @accent_pressed;
                }
                """
            )
        )

        buttons_layout.addWidget(btn_cancel)
        buttons_layout.addWidget(btn_confirm)
        container_layout.addLayout(buttons_layout)
        layout.addWidget(container)

    def confirm_switch(self):
        self.confirmed.emit()
        self.accept()
