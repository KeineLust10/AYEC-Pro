from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLineEdit, QLabel

from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.theme_colors import tc


class PremiumDialogBase(ModernDialog):
    """Base class for premium-styled dialogs using the shared modern shell."""

    def __init__(self, parent=None, title="Dialog", width=400, height=300):
        super().__init__(title=title, parent=parent, width=width, height=height)
        self.set_footer_visible(False)
        self.inner_layout = self.content_layout

    def add_title(self, title, icon_emoji="!", color=None):
        color = color or tc("danger")
        lbl_title = QLabel(f"{icon_emoji} {title}")
        lbl_title.setStyleSheet(f"color: {color}; font-weight: 700; font-size: 18px;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.inner_layout.addWidget(lbl_title)

    def add_message(self, message):
        lbl_msg = QLabel(message)
        lbl_msg.setWordWrap(True)
        self.inner_layout.addWidget(lbl_msg)

    def add_buttons(self, confirm_text="Onayla", cancel_text="Iptal", confirm_color=None):
        self.add_cancel_button(cancel_text)
        btn = self.add_button(confirm_text, "danger" if confirm_color is None else "primary", self.accept)
        if confirm_color:
            btn.setStyleSheet(f"background-color: {confirm_color}; color: white;")


class PremiumWarningDialog(PremiumDialogBase):
    def __init__(self, parent=None, title="Dikkat", message=""):
        super().__init__(parent=parent, title=title, width=400, height=300)
        self.add_title(title)
        self.add_message(message)
        self.inner_layout.addStretch()
        self.add_buttons("Evet, Sil", "Iptal", tc("danger"))


class PasswordConfirmDialog(PremiumDialogBase):
    def __init__(self, parent=None):
        super().__init__(parent=parent, title="Guvenlik Kontrolu", width=400, height=340)
        self.add_title("Guvenlik Kontrolu", "Lock", tc("accent"))
        self.add_message("Devam etmek icin lutfen giris sifrenizi giriniz.")

        self.inp_password = QLineEdit()
        self.inp_password.setPlaceholderText("Sifreniz")
        self.inp_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.inp_password.setFixedHeight(45)
        self.inner_layout.addWidget(self.inp_password)
        self.inner_layout.addStretch()
        self.add_buttons("Dogrula", "Vazgec", tc("accent"))

    def get_password(self):
        return self.inp_password.text()
