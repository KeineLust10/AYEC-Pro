"""
Security Confirmation Dialog
Sifre korumali islemler icin onay dialogu
"""

import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QFrame, QLabel, QLineEdit, QPushButton, QVBoxLayout

from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.toast_notification import show_error
from src.utils.password_security import verify_password
from src.utils.theme_colors import theme_qss


logger = logging.getLogger(__name__)


class SecurityConfirmDialog(ModernDialog):
    """Kritik islemler icin sifre dogrulama dialogu"""

    confirmed = pyqtSignal()

    def __init__(
        self,
        db,
        title="Guvenlik Onayi",
        message="Bu islemi gerceklestirmek icin yonetici sifresini giriniz.",
        parent=None,
    ):
        super().__init__(title=title, parent=parent, width=460, height=360)
        self.db = db
        self.message_text = message
        self.set_footer_visible(False)
        self.setup_ui()

    def setup_ui(self):
        layout = self.content_layout
        layout.setContentsMargins(30, 28, 30, 28)
        layout.setSpacing(16)

        header_card = QFrame()
        header_card.setObjectName("SecurityConfirmHeader")
        header_card.setStyleSheet(
            theme_qss("""
            QFrame#SecurityConfirmHeader {
                background-color: @surface_alt;
                border: 1px solid @border;
                border-radius: 12px;
            }
            QFrame#SecurityConfirmHeader QLabel {
                background: transparent;
                border: none;
                color: @text;
            }
            """)
        )
        header_layout = QVBoxLayout(header_card)
        header_layout.setContentsMargins(16, 14, 16, 14)

        icon_label = QLabel("Guvenlik")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        header_layout.addWidget(icon_label)
        layout.addWidget(header_card)

        msg_label = QLabel(self.message_text)
        msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg_label.setWordWrap(True)
        msg_label.setMinimumHeight(72)
        msg_label.setStyleSheet(
            theme_qss("""
            QLabel {
                background-color: @surface_alt;
                color: @text;
                border: 1px solid @border;
                border-radius: 12px;
                padding: 12px 14px;
                font-size: 10pt;
            }
            """)
        )
        layout.addWidget(msg_label)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Sifrenizi girin")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setFixedHeight(45)
        self.password_input.returnPressed.connect(self.verify_password)
        self.password_input.setStyleSheet(
            theme_qss("""
            QLineEdit {
                background-color: @surface;
                border: 2px solid @border;
                border-radius: 10px;
                padding: 0 15px;
                font-size: 14px;
                color: @text;
            }
            QLineEdit:focus {
                border: 2px solid @accent;
                background-color: @surface_alt;
            }
            """)
        )
        layout.addWidget(self.password_input)

        btn_confirm = QPushButton("Dogrula ve Devam Et")
        btn_confirm.setFixedHeight(45)
        btn_confirm.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_confirm.clicked.connect(self.verify_password)
        btn_confirm.setStyleSheet(
            theme_qss("""
            QPushButton {
                background-color: @accent;
                color: @selection_text;
                border: none;
                border-radius: 10px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: @accent_hover;
            }
            """)
        )
        layout.addWidget(btn_confirm)
        self.password_input.setFocus()

    def verify_password(self):
        password = self.password_input.text().strip()
        if not password:
            show_error(self, "Lutfen sifrenizi girin!")
            return

        is_valid = False

        try:
            main_window = getattr(self.parent(), "main_window", None) or getattr(
                self.parent(), "window", lambda: None
            )()
            auth_mgr = getattr(main_window, "auth_manager", None)
            if auth_mgr is None and main_window is not None:
                from src.utils.auth_manager import AuthManager

                session_user = getattr(main_window, "current_user", None) or getattr(
                    main_window, "user_data", None
                )
                if session_user:
                    auth_mgr = AuthManager(self.db)
                    auth_mgr.current_user = dict(session_user)
            if auth_mgr and auth_mgr.verify_action_password(password):
                is_valid = True
        except Exception:
            logger.exception("Action password verification failed")

        try:
            from src.utils.auth_manager import AuthManager

            if AuthManager.verify_master_key(password):
                is_valid = True
        except Exception:
            logger.exception("Master key verification failed")

        if not is_valid:
            try:
                admin_pass = str(self.db.get_setting("admin_pass", "") or "")
                valid, upgraded = verify_password(password, admin_pass)
                if valid:
                    is_valid = True
                    if upgraded:
                        self.db.set_setting("admin_pass", upgraded)
            except Exception:
                logger.exception("Configured admin password verification failed")

        if is_valid:
            self.confirmed.emit()
            self.accept()
            return

        show_error(self, "Hatali sifre! Lutfen tekrar deneyin.")
        self.password_input.clear()
        self.password_input.setFocus()
