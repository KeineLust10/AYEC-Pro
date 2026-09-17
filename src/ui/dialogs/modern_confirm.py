from PyQt6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton

from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.password_security import verify_password


class ModernConfirmDialog(ModernDialog):
    """Password-gated modern confirm dialog."""

    def __init__(self, title, message, correct_password, parent=None):
        super().__init__(title=title, parent=parent, width=400, height=250)
        self.correct_password = str(correct_password)
        self.set_footer_visible(False)
        self.setup_ui(message)

    def setup_ui(self, message):
        lbl_msg = QLabel(message)
        lbl_msg.setWordWrap(True)
        self.content_layout.addWidget(lbl_msg)

        self.inp_pass = QLineEdit()
        self.inp_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.inp_pass.setPlaceholderText("Yonetici sifresi giriniz")
        self.inp_pass.setFixedHeight(44)
        self.inp_pass.returnPressed.connect(self.handle_confirm)
        self.content_layout.addWidget(self.inp_pass)
        self.content_layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Iptal")
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("Onayla")
        btn_ok.clicked.connect(self.handle_confirm)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_ok)
        self.content_layout.addLayout(btn_layout)

    def handle_confirm(self):
        valid, _upgraded = verify_password(
            self.inp_pass.text(),
            self.correct_password,
        )
        if valid:
            self.accept()
            return
        self.inp_pass.clear()
        self.inp_pass.setPlaceholderText("Hatali sifre")
        self.inp_pass.setStyleSheet("border: 1px solid #dc2626;")
