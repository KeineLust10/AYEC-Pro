from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QWidget,
)

from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.currency_helper import CurrencyHelper
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import show_warning


class SalePaymentDialog(ModernDialog):
    def __init__(
        self,
        total,
        currency_code="TRY",
        customer_name="",
        parent=None,
    ):
        super().__init__(
            title="\u00d6deme Al ve Sat\u0131\u015f\u0131 Kaydet",
            parent=parent,
            width=620,
            height=480,
        )
        self.total = round(float(total or 0), 2)
        self.currency_code = str(currency_code or "TRY").upper()
        self.customer_name = str(customer_name or "")
        self.payment_amount = 0.0
        self.payment_method = "Nakit"
        self.payment_note = ""
        self._build_ui()

    def _build_ui(self):
        info = QLabel(
            "Al\u0131nan tutar\u0131 girin. Sat\u0131\u015f\u0131n kalan k\u0131sm\u0131 "
            "m\u00fc\u015fterinin cari hesab\u0131nda bor\u00e7 olarak kal\u0131r."
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

        customer = QLabel(self.customer_name or "-")
        total = QLabel(self._format(self.total))
        total.setStyleSheet(theme_qss("font-weight: 800; color: @success;"))

        self.spin_payment = QDoubleSpinBox()
        self.spin_payment.setDecimals(2)
        self.spin_payment.setRange(0.0, self.total)
        self.spin_payment.setSingleStep(100.0)
        self.spin_payment.setSuffix(
            f" {CurrencyHelper.get_symbol(None, self.currency_code)}"
        )
        self.spin_payment.setValue(self.total)
        self.spin_payment.selectAll()
        self.spin_payment.valueChanged.connect(self._refresh_remaining)

        self.cmb_method = QComboBox()
        self.cmb_method.addItems(
            [
                "Nakit",
                "Banka",
                "Kredi Kart\u0131",
                "Havale / EFT",
                "Di\u011fer",
            ]
        )

        self.txt_note = QLineEdit()
        self.txt_note.setPlaceholderText("\u00d6deme notu (iste\u011fe ba\u011fl\u0131)")

        self.lbl_remaining = QLabel(self._format(0.0))
        self.lbl_remaining.setStyleSheet(
            theme_qss("font-weight: 800; color: @danger;")
        )

        form.addRow("M\u00fc\u015fteri:", customer)
        form.addRow("Sat\u0131\u015f Toplam\u0131:", total)
        form.addRow("Al\u0131nan \u00d6deme:", self.spin_payment)
        form.addRow("\u00d6deme Y\u00f6ntemi:", self.cmb_method)
        form.addRow("Kalan Bor\u00e7:", self.lbl_remaining)
        form.addRow("Not:", self.txt_note)
        self.add_widget(form_widget)

        self.add_cancel_button("\u0130ptal")
        self.add_button(
            "\u00d6demeyi Onayla ve Kaydet",
            "success",
            self._accept_values,
        )

    def _format(self, amount):
        return CurrencyHelper.format_amount(
            float(amount or 0),
            currency_code=self.currency_code,
        )

    def _refresh_remaining(self, value):
        self.lbl_remaining.setText(self._format(max(0.0, self.total - value)))

    def _accept_values(self):
        payment_amount = round(float(self.spin_payment.value()), 2)
        if payment_amount <= 0:
            show_warning(
                self,
                "Al\u0131nan \u00f6deme s\u0131f\u0131rdan b\u00fcy\u00fck olmal\u0131d\u0131r.",
            )
            return
        self.payment_amount = payment_amount
        self.payment_method = str(self.cmb_method.currentText() or "Nakit")
        self.payment_note = self.txt_note.text().strip()
        self.accept()
