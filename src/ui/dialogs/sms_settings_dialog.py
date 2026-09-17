"""
SMS Settings Dialog
Allows configuration of Twilio credentials for SMS notifications.
"""

from PyQt6.QtGui import QFont
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QFormLayout, QGroupBox, QLabel, QLineEdit, QPushButton, QTextEdit, QHBoxLayout

from src.services.sms_service import SMSService
from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.design_system import DesignTokens
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import show_info


class SMSTestWorker(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, db_name="ayecpro.db"):
        super().__init__()
        self.db_name = db_name or "ayecpro.db"

    def run(self):
        db = None
        try:
            from src.database import Database
            db = Database(self.db_name, init_mode="auth")
            self.finished.emit(SMSService(db).test_connection())
        except Exception as exc:
            self.finished.emit({"status": "error", "message": str(exc)})
        finally:
            if db is not None:
                try:
                    db.close()
                except Exception:
                    pass


class SMSSettingsDialog(ModernDialog):
    """Dialog for configuring SMS notification settings."""

    def __init__(self, db, parent=None):
        super().__init__(title="SMS Bildirim Ayarlari", parent=parent, width=600, height=500)
        self.db = db
        self.set_footer_visible(False)
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        layout = self.content_layout
        self.setStyleSheet(theme_qss(f"QDialog {{ background-color: {DesignTokens.BACKGROUND}; border-radius: 15px; }}"))
        layout.setSpacing(20)

        header = QLabel("SMS Bildirim Sistemi")
        header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        layout.addWidget(header)

        desc = QLabel("Musterilere otomatik servis durumu bildirimleri gondermek icin Twilio hesabinizi yapilandirin.")
        desc.setWordWrap(True)
        desc.setStyleSheet(theme_qss("color: @text_muted;"))
        layout.addWidget(desc)

        cred_group = QGroupBox("Twilio API Bilgileri")
        cred_layout = QFormLayout(cred_group)
        self.inp_account_sid = QLineEdit()
        self.inp_account_sid.setPlaceholderText("ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        self.inp_account_sid.setEchoMode(QLineEdit.EchoMode.Password)
        self.inp_auth_token = QLineEdit()
        self.inp_auth_token.setPlaceholderText("xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        self.inp_auth_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.inp_from_number = QLineEdit()
        self.inp_from_number.setPlaceholderText("+905XXXXXXXXX")
        cred_layout.addRow("Account SID:", self.inp_account_sid)
        cred_layout.addRow("Auth Token:", self.inp_auth_token)
        cred_layout.addRow("Gonderen Numara:", self.inp_from_number)
        layout.addWidget(cred_group)

        test_group = QGroupBox("Baglanti Testi")
        test_layout = QFormLayout(test_group)
        self.test_result = QTextEdit()
        self.test_result.setReadOnly(True)
        self.test_result.setMaximumHeight(100)
        self.test_result.setPlaceholderText("Test sonuclari burada gorunecek...")
        test_layout.addRow(self.test_result)
        self.btn_test = QPushButton("Baglantiyi Test Et")
        self.btn_test.clicked.connect(self.test_connection)
        test_layout.addRow(self.btn_test)
        layout.addWidget(test_group)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_save = QPushButton("Kaydet")
        btn_save.clicked.connect(self.save_settings)
        btn_cancel = QPushButton("Iptal")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def load_settings(self):
        self.inp_account_sid.setText(self.db.get_setting("twilio_account_sid", ""))
        self.inp_auth_token.setText(self.db.get_setting("twilio_auth_token", ""))
        self.inp_from_number.setText(self.db.get_setting("twilio_from_number", ""))

    def save_settings(self):
        self.db.set_setting("twilio_account_sid", self.inp_account_sid.text().strip())
        self.db.set_setting("twilio_auth_token", self.inp_auth_token.text().strip())
        self.db.set_setting("twilio_from_number", self.inp_from_number.text().strip())
        show_info(self, "SMS ayarlari kaydedildi!")
        self.accept()

    def test_connection(self):
        self.test_result.clear()
        self.test_result.append("Baglanti test ediliyor...\n")
        self.btn_test.setEnabled(False)
        self.db.set_setting("twilio_account_sid", self.inp_account_sid.text().strip())
        self.db.set_setting("twilio_auth_token", self.inp_auth_token.text().strip())
        self.db.set_setting("twilio_from_number", self.inp_from_number.text().strip())
        self.sms_test_worker = SMSTestWorker(getattr(self.db, "_db_name", "ayecpro.db"))
        self.sms_test_worker.finished.connect(self.on_test_connection_finished)
        self.sms_test_worker.finished.connect(self.sms_test_worker.deleteLater)
        self.sms_test_worker.start()

    def on_test_connection_finished(self, result):
        self.btn_test.setEnabled(True)
        if result["status"] == "success":
            self.test_result.append(f"OK: {result['message']}")
            self.test_result.setStyleSheet(theme_qss("color: @success;"))
        else:
            self.test_result.append(f"Hata: {result['message']}")
            self.test_result.setStyleSheet(theme_qss("color: @danger;"))
