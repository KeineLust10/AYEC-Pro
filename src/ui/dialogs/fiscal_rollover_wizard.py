from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QCheckBox, QLabel, QVBoxLayout, QWizard, QWizardPage

from src.utils.theme_colors import theme_qss


class _ApprovalPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Muhasebe Onayi")
        layout = QVBoxLayout(self)
        text = QLabel(
            "Yedek ve tutarlilik kontrolu basarili olmadan devir tamamlanmaz. "
            "Sonraki adimda yetkili kullanici sifresi ile onay alinacaktir."
        )
        text.setWordWrap(True)
        layout.addWidget(text)
        self.approval = QCheckBox(
            "Muhasebe kontrolunun yapildigini ve acilis fislerini onayladigimi kabul ediyorum."
        )
        self.approval.stateChanged.connect(self.completeChanged)
        layout.addWidget(self.approval)

    def isComplete(self):
        return self.approval.isChecked()


class FiscalRolloverWizard(QWizard):
    """Guided, non-destructive selection flow for fiscal rollover."""

    def __init__(self, fiscal_service, parent=None):
        super().__init__(parent)
        self.fiscal_service = fiscal_service
        self.plan = fiscal_service.get_manual_rollover_plan()
        self.setWindowTitle("Mali Yil Devir Sihirbazi")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setMinimumSize(680, 430)
        self.setStyleSheet(
            theme_qss(
                "QWizard { background: @surface; color: @text; } "
                "QLabel { color: @text; } "
                "QCheckBox { color: @text; padding: 6px; }"
            )
        )
        self._add_preflight_page()
        self._add_selection_page()
        self.approval_page = _ApprovalPage(self)
        self.addPage(self.approval_page)

    def _add_preflight_page(self):
        page = QWizardPage()
        page.setTitle("Yedek ve Tutarlilik Kontrolu")
        layout = QVBoxLayout(page)
        integrity_ok = self.plan.get("integrity") == "ok"
        status = "BASARILI" if integrity_ok else "BASARISIZ"
        details = (
            f"Veritabani tutarliligi: {status}\n"
            f"Ac ilis tarihi: {self.plan.get('opening_date', '-')}\n"
            "Devir aninda tam veritabani arsivi olusturulacak.\n\n"
            "Eski donem hareketleri degistirilmez; arsivden de goruntulenebilir. "
            "Yalnizca secilen bakiyeler yeni yil icin acilis fisi olarak yazilir."
        )
        label = QLabel(details)
        label.setWordWrap(True)
        layout.addWidget(label)
        if not integrity_ok:
            warning = QLabel("Tutarlilik kontrolu basarisiz oldugu icin bu devir tamamlanamaz.")
            warning.setStyleSheet(theme_qss("color: @danger; font-weight: 700;"))
            warning.setWordWrap(True)
            layout.addWidget(warning)
        self.addPage(page)

    def _add_selection_page(self):
        page = QWizardPage()
        page.setTitle("Devredilecek Bakiyeler")
        layout = QVBoxLayout(page)
        info = QLabel(
            "Secilmeyen kalem icin acilis fisi uretilmez. Stok kartlari, servis kayitlari "
            "ve onceki donem hareketleri korunur; bu akista yeniden yazilmaz."
        )
        info.setWordWrap(True)
        layout.addWidget(info)
        self.bank_check = QCheckBox("Banka hesap bakiyelerini acilis fisi olarak aktar")
        self.bank_check.setChecked(bool(self.plan.get("selections", {}).get("bank", True)))
        layout.addWidget(self.bank_check)
        self.customer_check = QCheckBox("Cari alacak ve avans bakiyelerini acilis fisi olarak aktar")
        self.customer_check.setChecked(bool(self.plan.get("selections", {}).get("customer", True)))
        layout.addWidget(self.customer_check)
        summary = QLabel(
            f"Onizleme: {self.plan.get('bank_count', 0)} banka, "
            f"{self.plan.get('customer_count', 0)} cari bakiye, "
            f"toplam {self.plan.get('entry_count', 0)} acilis fisi adayi."
        )
        summary.setAlignment(Qt.AlignmentFlag.AlignLeft)
        summary.setStyleSheet(theme_qss("color: @text_muted; padding-top: 12px;"))
        layout.addWidget(summary)
        self.addPage(page)

    def selected_options(self):
        return {"bank": self.bank_check.isChecked(), "customer": self.customer_check.isChecked()}

    def is_accountant_approved(self):
        return self.approval_page.approval.isChecked()
