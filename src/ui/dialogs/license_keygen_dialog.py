from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.design_system import DesignTokens
from src.utils.security_manager import SecurityManager
from src.utils.theme_colors import theme_qss


class LicenseKeygenDialog(ModernDialog):
    def __init__(self, hwid_value="", parent=None):
        super().__init__(title="Lisans Anahtari Uretici", parent=parent, width=560, height=420)
        self.hwid_value = hwid_value
        self.set_footer_visible(False)
        self.setStyleSheet(theme_qss("background-color: @surface_alt;"))
        self._build_ui()

    def _build_ui(self):
        layout = self.content_layout
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)

        title = QLabel("Lisans Anahtari Uretici")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("color: @selection_text;"))
        layout.addWidget(title)

        subtitle = QLabel("Musteri HWID bilgisini girerek lisans anahtari uretin.")
        subtitle.setStyleSheet(theme_qss("color: @text_muted;"))
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        form_card = QFrame()
        form_card.setStyleSheet(
            theme_qss("background-color: @surface; border-radius: 12px; border: 1px solid @border;")
        )
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(16, 16, 16, 16)
        form_layout.setSpacing(12)

        lbl_hwid = QLabel("HWID")
        lbl_hwid.setStyleSheet(theme_qss("color: @text; font-weight: 700;"))
        self.inp_hwid = QLineEdit(self.hwid_value or "")
        self.inp_hwid.setPlaceholderText("HWID girin")
        self.inp_hwid.setStyleSheet(theme_qss("border: 1px solid @border; border-radius: 8px; padding: 10px;"))
        form_layout.addWidget(lbl_hwid)
        form_layout.addWidget(self.inp_hwid)

        btn_generate = QPushButton("Anahtar Uret")
        btn_generate.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_generate.setStyleSheet(
            theme_qss(
                """
                QPushButton {
                    background-color: @accent;
                    color: @selection_text;
                    padding: 10px;
                    border-radius: 8px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: @accent_hover; }
                """
            )
        )
        btn_generate.clicked.connect(self.generate_key)
        form_layout.addWidget(btn_generate)

        lbl_key = QLabel("Uretilen Lisans Anahtari")
        lbl_key.setStyleSheet(theme_qss("color: @text; font-weight: 700;"))
        self.out_key = QLineEdit()
        self.out_key.setReadOnly(True)
        self.out_key.setStyleSheet(
            theme_qss(
                "border: 1px solid @border; border-radius: 8px; padding: 10px; background: @surface_alt; font-weight: 700;"
            )
        )
        form_layout.addWidget(lbl_key)
        form_layout.addWidget(self.out_key)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_copy = QPushButton("Kopyala")
        btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy.setStyleSheet(theme_qss(DesignTokens.get_button_qss("outline")))
        btn_copy.clicked.connect(self.copy_key)
        btn_row.addWidget(btn_copy)
        form_layout.addLayout(btn_row)

        layout.addWidget(form_card)
        layout.addStretch()

    def generate_key(self):
        hwid = self.inp_hwid.text().strip()
        if not hwid:
            from src.utils.toast_notification import show_warning

            show_warning(self, "HWID gerekli.")
            return
        self.out_key.setText(SecurityManager.generate_license_key(hwid))

    def copy_key(self):
        key = self.out_key.text().strip()
        if not key:
            from src.utils.toast_notification import show_warning

            show_warning(self, "Kopyalanacak anahtar yok.")
            return
        QApplication.clipboard().setText(key)
        from src.utils.toast_notification import show_success

        show_success(self, "Lisans anahtari kopyalandi.")
