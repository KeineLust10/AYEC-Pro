from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from src.api.einvoice_client import EInvoiceClient
from src.utils.secure_setting_store import SecureSettingStore
from src.utils.theme_colors import theme_qss


class EInvoiceIntegrationDialog(QDialog):
    """Configure the e-invoice API without storing its key as plaintext."""

    PROVIDERS = (
        ("Diger / Ozel Entegrator", "custom"),
        ("Uyumsoft", "uyumsoft"),
        ("Logo", "logo"),
        ("eFinans", "efinans"),
        ("Foriba", "foriba"),
    )

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("E-Fatura Entegrasyon Ayarlari")
        self.setMinimumWidth(560)
        self.setStyleSheet(
            theme_qss(
                "QDialog { background: @surface; color: @text; } "
                "QLabel { color: @text; } "
                "QLineEdit, QComboBox { background: @surface_alt; color: @text; "
                "border: 1px solid @border; border-radius: 6px; padding: 8px; }"
            )
        )
        self._build_ui()
        self._load_settings()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        info = QLabel(
            "API anahtari sifreli olarak saklanir. Test baglantisi fatura gondermez. "
            "Canli kullanim icin secilen entegratorun API dokumani gerekir."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        form = QFormLayout()
        self.provider = QComboBox()
        for label, code in self.PROVIDERS:
            self.provider.addItem(label, code)
        self.environment = QComboBox()
        self.environment.addItem("Sandbox / Test", "sandbox")
        self.environment.addItem("Canli", "live")
        self.api_url = QLineEdit()
        self.api_url.setPlaceholderText("https://api.entegratoriniz.com/v1")
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText("API anahtari")
        form.addRow("Entegrator:", self.provider)
        form.addRow("Ortam:", self.environment)
        form.addRow("API adresi:", self.api_url)
        form.addRow("API anahtari:", self.api_key)
        layout.addLayout(form)

        self.status = QLabel("Ayarlar kaydedilmedi.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        actions = QHBoxLayout()
        self.test_button = QPushButton("Test Baglantisi")
        self.test_button.clicked.connect(self._test_connection)
        save_button = QPushButton("Kaydet")
        save_button.clicked.connect(self._save)
        cancel_button = QPushButton("Iptal")
        cancel_button.clicked.connect(self.reject)
        actions.addWidget(self.test_button)
        actions.addStretch(1)
        actions.addWidget(cancel_button)
        actions.addWidget(save_button)
        layout.addLayout(actions)

    def _load_settings(self):
        provider = self.db.get_setting("einvoice_provider", "custom")
        index = self.provider.findData(provider)
        self.provider.setCurrentIndex(index if index >= 0 else 0)
        mode = self.db.get_setting("einvoice_environment", "sandbox")
        index = self.environment.findData(mode)
        self.environment.setCurrentIndex(index if index >= 0 else 0)
        self.api_url.setText(self.db.get_setting("einvoice_api_url", ""))
        self.api_key.setText(SecureSettingStore.get(self.db, "einvoice_api_key"))

    def _client(self):
        return EInvoiceClient(
            api_key=self.api_key.text().strip(),
            is_sandbox=self.environment.currentData() == "sandbox",
            base_url=self.api_url.text().strip(),
        )

    def _test_connection(self):
        ok, response = self._client().test_connection()
        detail = response.get("detail", "Bilinmeyen sonuc")
        if ok:
            self.status.setText(f"Test basarili: {detail}")
            self.status.setStyleSheet(theme_qss("color: @success; font-weight: 700;"))
        else:
            self.status.setText(f"Test basarisiz: {detail}")
            self.status.setStyleSheet(theme_qss("color: @danger; font-weight: 700;"))

    def _save(self):
        client = self._client()
        valid, message = client.validate_configuration()
        if not valid:
            self.status.setText(f"Kaydedilemedi: {message}")
            self.status.setStyleSheet(theme_qss("color: @danger; font-weight: 700;"))
            return
        self.db.set_setting("einvoice_provider", self.provider.currentData())
        self.db.set_setting("einvoice_environment", self.environment.currentData())
        self.db.set_setting("einvoice_api_url", self.api_url.text().strip())
        SecureSettingStore.set(self.db, "einvoice_api_key", self.api_key.text().strip())
        self.accept()
