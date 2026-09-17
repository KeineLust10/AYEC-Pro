from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
)

from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.currency_helper import CurrencyHelper
from src.utils.design_system import DesignTokens
from src.utils.theme_colors import theme_qss


class AddServiceDefinitionDialog(ModernDialog):
    def __init__(self, parent=None, service_data=None):
        super().__init__(
            title="\u0130\u015f\u00e7ilik Tan\u0131m\u0131",
            parent=parent,
            width=780,
            height=480,
        )
        self.service_data = service_data or {}
        self.currency_db = getattr(parent, "db", None)
        self.set_footer_visible(True, 68)
        self._build_ui()

    def _build_ui(self):
        self.content_layout.setContentsMargins(18, 18, 18, 10)
        self.content_layout.setSpacing(14)

        intro = QLabel(
            "\u0130\u015f\u00e7ilik kart\u0131n\u0131 ve para birimi "
            "baz\u0131ndaki fiyatlar\u0131n\u0131 y\u00f6netin."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px;"))
        self.content_layout.addWidget(intro)

        top_row = QHBoxLayout()
        top_row.setSpacing(14)

        left_col = QVBoxLayout()
        left_col.setSpacing(10)
        left_col.addWidget(self._field_label("\u0130\u015f\u00e7ilik Ad\u0131"))
        self.inp_name = QLineEdit()
        self.inp_name.setPlaceholderText("\u00d6rn: Yaz\u0131c\u0131 Bak\u0131m ve Temizlik")
        left_col.addWidget(self.inp_name)
        left_col.addWidget(self._field_label("A\u00e7\u0131klama"))
        self.inp_desc = QPlainTextEdit()
        self.inp_desc.setPlaceholderText("\u0130\u015f\u00e7ilik a\u00e7\u0131klamas\u0131")
        self.inp_desc.setFixedHeight(94)
        left_col.addWidget(self.inp_desc)
        top_row.addLayout(left_col, 3)

        right_col = QVBoxLayout()
        right_col.setSpacing(10)
        right_col.addWidget(self._field_label("Referans Kodu / Barkod"))
        self.inp_barcode = QLineEdit()
        self.inp_barcode.setPlaceholderText("\u00d6rn: ISC001")
        right_col.addWidget(self.inp_barcode)
        self.chk_active = QCheckBox("Aktif")
        self.chk_active.setChecked(True)
        right_col.addWidget(self.chk_active)
        right_col.addStretch()
        top_row.addLayout(right_col, 2)
        self.content_layout.addLayout(top_row)

        prices_row = QHBoxLayout()
        prices_row.setSpacing(12)
        self.inp_price_try = self._price_field("TRY")
        self.inp_price_usd = self._price_field("USD")
        self.inp_price_eur = self._price_field("EUR")
        for label, widget in (
            ("TL", self.inp_price_try),
            ("USD", self.inp_price_usd),
            ("EURO", self.inp_price_eur),
        ):
            column = QVBoxLayout()
            column.setSpacing(6)
            column.addWidget(self._field_label(label))
            column.addWidget(widget)
            prices_row.addLayout(column, 1)
        self.content_layout.addLayout(prices_row)

        # Keep the legacy attribute available to older callers and tests.
        self.inp_price = self.inp_price_try
        self._load_existing_data()

        self.clear_footer()
        self.add_cancel_button("\u0130ptal")
        self.add_button("Kaydet", "success", self.accept)

    def _field_label(self, text):
        label = QLabel(text)
        label.setStyleSheet(
            theme_qss(
                "color: @text_muted; font-size: 12px; font-weight: 700; "
                "text-transform: uppercase;"
            )
        )
        return label

    @staticmethod
    def _price_field(suffix):
        widget = QDoubleSpinBox()
        widget.setRange(0, 999999999)
        widget.setDecimals(2)
        widget.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        widget.setFixedHeight(44)
        widget.setSuffix(f" {suffix}")
        DesignTokens.apply_spinbox_styles(widget)
        return widget

    def _load_existing_data(self):
        if not self.service_data:
            return
        self.inp_name.setText(str(self.service_data.get("name", "")))
        self.inp_desc.setPlainText(str(self.service_data.get("description", "")))
        self.inp_barcode.setText(str(self.service_data.get("barcode", "")))
        currency = str(self.service_data.get("currency", "TRY") or "TRY").upper()
        legacy_price = float(self.service_data.get("price", 0) or 0)
        defaults = {
            "price_try": legacy_price if currency == "TRY" else 0,
            "price_usd": legacy_price if currency == "USD" else 0,
            "price_eur": legacy_price if currency == "EUR" else 0,
        }
        self.inp_price_try.setValue(
            float(self.service_data.get("price_try", defaults["price_try"]) or 0)
        )
        saved_usd = float(self.service_data.get("price_usd", defaults["price_usd"]) or 0)
        saved_eur = float(self.service_data.get("price_eur", defaults["price_eur"]) or 0)
        try_value = float(self.service_data.get("price_try", defaults["price_try"]) or 0)
        if try_value > 0:
            if saved_usd <= 0:
                saved_usd = try_value / CurrencyHelper.require_rate(self.currency_db, "USD")
            if saved_eur <= 0:
                saved_eur = try_value / CurrencyHelper.require_rate(self.currency_db, "EUR")
        self.inp_price_usd.setValue(saved_usd)
        self.inp_price_eur.setValue(saved_eur)
        self.chk_active.setChecked(bool(self.service_data.get("is_active", 1)))

    def get_data(self):
        price_try = self.inp_price_try.value()
        price_usd = self.inp_price_usd.value()
        price_eur = self.inp_price_eur.value()
        currency = "TRY"
        legacy_price = price_try
        if not legacy_price and price_usd:
            currency, legacy_price = "USD", price_usd
        elif not legacy_price and price_eur:
            currency, legacy_price = "EUR", price_eur
        return {
            "name": self.inp_name.text().strip().upper(),
            "price": legacy_price,
            "currency": currency,
            "price_try": price_try,
            "price_usd": price_usd,
            "price_eur": price_eur,
            "is_active": int(self.chk_active.isChecked()),
            "description": self.inp_desc.toPlainText().strip(),
            "barcode": self.inp_barcode.text().strip(),
        }
