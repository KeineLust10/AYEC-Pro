"""
Password Prompt Dialog
Kullanici secildikten sonra sifre girmek icin modern dialog
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QFrame, QLabel, QLineEdit, QPushButton, QVBoxLayout

from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.toast_notification import show_error
from src.utils.theme_colors import theme_qss

class PasswordPromptDialog(ModernDialog):
    """Sik sifre giris dialogu"""

    password_accepted = pyqtSignal(str)

    def __init__(self, username, user_fullname="", parent=None):
        super().__init__(title="Sifre Gecidi", parent=parent, width=460, height=350)
        self.username = username
        self.user_fullname = user_fullname or username
        self.set_footer_visible(False)
        self.setup_ui()

    def setup_ui(self):
        layout = self.content_layout
        layout.setContentsMargins(30, 28, 30, 28)
        layout.setSpacing(16)

        header_card = QFrame()
        header_card.setObjectName("PasswordPromptHeader")
        header_card.setStyleSheet(
            theme_qss("""
            QFrame#PasswordPromptHeader {
                background-color: @surface_alt;
                border: 1px solid @border;
                border-radius: 12px;
            }
            QFrame#PasswordPromptHeader QLabel {
                background: transparent;
                border: none;
            }
            """)
        )
        header_layout = QVBoxLayout(header_card)
        header_layout.setContentsMargins(16, 14, 16, 14)

        avatar_label = QLabel("Kullanici")
        avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        avatar_label.setStyleSheet(theme_qss("color: @accent;"))
        header_layout.addWidget(avatar_label)

        name_label = QLabel(self.user_fullname)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        name_label.setStyleSheet(theme_qss("color: @text;"))
        header_layout.addWidget(name_label)
        layout.addWidget(header_card)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Sifrenizi girin")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setFixedHeight(50)
        self.password_input.returnPressed.connect(self.verify_password)
        self.password_input.setStyleSheet(
            theme_qss("""
            QLineEdit {
                background-color: @surface;
                border: 2px solid @border;
                border-radius: 12px;
                padding: 0 18px;
                font-size: 15px;
                color: @text;
                font-family: 'Segoe UI';
            }
            QLineEdit:focus {
                border: 2px solid @accent;
                background-color: @surface_alt;
            }
            """)
        )
        layout.addWidget(self.password_input)

        btn_login = QPushButton("Giris Yap")
        btn_login.setFixedHeight(50)
        btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_login.clicked.connect(self.verify_password)
        btn_login.setStyleSheet(
            theme_qss("""
            QPushButton {
                background-color: @accent;
                color: @selection_text;
                border: none;
                border-radius: 12px;
                font-weight: 700;
                font-size: 14px;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background-color: @accent_hover;
            }
            QPushButton:pressed {
                background-color: @accent_pressed;
            }
            """)
        )
        layout.addWidget(btn_login)

        self.password_input.setFocus()

    def verify_password(self):
        password = self.password_input.text().strip()
        if not password:
            show_error(self, "Lutfen sifrenizi girin!")
            return

        self.password_accepted.emit(self.username)
        self.password_value = password
        self.accept()
