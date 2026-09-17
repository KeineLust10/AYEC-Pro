from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QWidget,
)

from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.currency_helper import CurrencyHelper
from src.utils.theme_colors import theme_qss


class OfferAcceptanceDialog(ModernDialog):
    def __init__(
        self,
        total,
        currency_code="TRY",
        offer_no="",
        parent=None,
    ):
        super().__init__(
            title="Teklifi M\u00fc\u015fteri Hesab\u0131na \u0130\u015fle",
            parent=parent,
            width=620,
            height=450,
        )
        self.total = round(float(total or 0), 2)
        self.currency_code = str(currency_code or "TRY").upper()
        self.offer_no = str(offer_no or "")
        self.payment_amount = 0.0
        self.payment_method = "Cari Hesap"
        self._build_ui()

    def _build_ui(self):
        info = QLabel(
            "Teklif kabul edildi\u011finde stok kalemleri d\u00fc\u015fer, "
            "sat\u0131\u015f finans kayd\u0131 olu\u015fur ve pe\u015finat d\u00fc\u015f\u00fcld\u00fckten "
            "sonra kalan tutar m\u00fc\u015fteri cari hesab\u0131na bor\u00e7 yaz\u0131l\u0131r."
        )
        info.setWordWrap(True)
        info.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        info.setStyleSheet(
            theme_qss(
                """
                QLabel {
                    background: @surface_alt;
                    color: @text;
                    border: 1px solid @border;
                    border-radius: 8px;
                    padding: 14px;
                }
                """
            )
        )
        self.add_widget(info)

        form_widget = QWidget()
        form = QFormLayout(form_widget)
        form.setContentsMargins(0, 4, 0, 4)
        form.setVerticalSpacing(14)

        self.lbl_offer = QLabel(self.offer_no or "-")
        self.lbl_total = QLabel(self._format(self.total))
        self.lbl_total.setStyleSheet(theme_qss("font-weight: 800; color: @success;"))

        self.spin_payment = QDoubleSpinBox()
        self.spin_payment.setDecimals(2)
        self.spin_payment.setRange(0.0, self.total)
        self.spin_payment.setSingleStep(100.0)
        self.spin_payment.setSuffix(
            f" {CurrencyHelper.get_symbol(None, self.currency_code)}"
        )
        self.spin_payment.valueChanged.connect(self._refresh_remaining)

        self.cmb_method = QComboBox()
        self.cmb_method.addItems(
            [
                "Cari Hesap",
                "Nakit",
                "Banka",
                "Kredi Kart\u0131",
                "Havale / EFT",
                "Di\u011fer",
            ]
        )

        self.lbl_remaining = QLabel(self._format(self.total))
        self.lbl_remaining.setStyleSheet(
            theme_qss("font-weight: 800; color: @danger;")
        )

        form.addRow("Teklif No:", self.lbl_offer)
        form.addRow("Teklif Toplam\u0131:", self.lbl_total)
        form.addRow("Pe\u015finat / Al\u0131nan \u00d6deme:", self.spin_payment)
        form.addRow("\u00d6deme Y\u00f6ntemi:", self.cmb_method)
        form.addRow("Cari Hesaba Yaz\u0131lacak:", self.lbl_remaining)
        self.add_widget(form_widget)

        self.add_cancel_button("\u0130ptal")
        self.add_button(
            "Teklifi Kabul Et ve Hesaba \u0130\u015fle",
            "primary",
            self._accept_values,
        )

    def _format(self, amount):
        return CurrencyHelper.format_amount(
            float(amount or 0),
            currency_code=self.currency_code,
        )

    def _refresh_remaining(self, value):
        self.lbl_remaining.setText(self._format(max(0.0, self.total - value)))
        if value <= 0:
            self.cmb_method.setCurrentText("Cari Hesap")
        elif self.cmb_method.currentText() == "Cari Hesap":
            self.cmb_method.setCurrentText("Nakit")

    def _accept_values(self):
        self.payment_amount = round(float(self.spin_payment.value()), 2)
        self.payment_method = str(self.cmb_method.currentText() or "Cari Hesap")
        self.accept()
