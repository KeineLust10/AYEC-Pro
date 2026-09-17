from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QLabel, QLineEdit, QPushButton

from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import show_error


class AppLockDialog(ModernDialog):
    """Simple login dialog for the app lock feature."""

    def __init__(self, correct_password, parent=None):
        super().__init__(
            title="Bulut Teknik Servis - Guvenlik",
            parent=parent,
            width=400,
            height=300,
        )
        self.correct_password = correct_password
        self.set_footer_visible(False)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setWindowFlag(Qt.WindowType.Tool, True)
        self.setup_ui()
        self.apply_theme_styles()

    def setup_ui(self):
        layout = self.content_layout
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        self.lbl_icon = QLabel("Kilit")
        self.lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_icon)

        self.lbl_title = QLabel("Uygulama Kilitli")
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        layout.addWidget(self.lbl_title)

        self.inp_password = QLineEdit()
        self.inp_password.setPlaceholderText("Giris sifresi")
        self.inp_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.inp_password.returnPressed.connect(self.check_password)
        layout.addWidget(self.inp_password)

        self.btn_login = QPushButton("Giris Yap")
        self.btn_login.clicked.connect(self.check_password)
        layout.addWidget(self.btn_login)

        self.btn_exit = QPushButton("Cikis")
        self.btn_exit.setFlat(True)
        self.btn_exit.clicked.connect(self.reject)
        layout.addWidget(self.btn_exit)

    def apply_theme_styles(self):
        self.lbl_icon.setStyleSheet(theme_qss("font-size: 32px; font-weight: 700; color: @accent;"))
        self.lbl_title.setStyleSheet(theme_qss("color: @text;"))
        self.inp_password.setStyleSheet(
            theme_qss(
                """
                QLineEdit {
                    padding: 12px;
                    border: 2px solid @border;
                    border-radius: 8px;
                    font-size: 11pt;
                    background-color: @surface;
                    color: @text;
                }
                QLineEdit:focus {
                    border: 2px solid @accent;
                    background-color: @surface_alt;
                }
                """
            )
        )
        self.btn_login.setStyleSheet(
            theme_qss(
                """
                QPushButton {
                    background-color: @accent;
                    color: @selection_text;
                    font-weight: bold;
                    padding: 12px;
                    border-radius: 8px;
                }
                QPushButton:hover { background-color: @accent_hover; }
                """
            )
        )
        self.btn_exit.setStyleSheet(theme_qss("color: @text_muted; text-decoration: underline;"))

    def refresh_theme(self):
        self.apply_theme_styles()

    def check_password(self):
        if self.inp_password.text() == self.correct_password:
            self.accept()
            return

        show_error(self, "Yanlis sifre!")
        self.inp_password.clear()
