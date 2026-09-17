# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QLabel

from src.ui.widgets.modern_dialog import ModernDialog
from src.ui.widgets.modern_inputs import ValidatedLineEdit
from src.utils.currency_helper import CurrencyHelper
from src.utils.validators import Validators


class ModernManualProductDialog(ModernDialog):
    def __init__(self, parent=None):
        super().__init__("Manuel Ürün/Hizmet Ekle", parent, width=400, height=350)
        self.result_data = None
        self.setup_content()

    def setup_content(self):
        self.inp_name = ValidatedLineEdit("Ürün/Hizmet Adı")
        self.inp_price = ValidatedLineEdit(
            f"Fiyat ({CurrencyHelper.get_label()})",
            validator_func=Validators.is_numeric,
        )

        self.add_widget(QLabel("Hizmet veya Ürün Adı:"))
        self.add_widget(self.inp_name)
        self.add_widget(QLabel("Birim Fiyat:"))
        self.add_widget(self.inp_price)

        self.add_button("Ekle", callback=self.save)
        self.add_cancel_button("İptal")

    def save(self):
        if not self.inp_name.text() or not self.inp_price.text():
            return
        try:
            price = float(self.inp_price.text().replace(",", "."))
        except ValueError:
            return
        self.result_data = (self.inp_name.text(), price)
        self.accept()
