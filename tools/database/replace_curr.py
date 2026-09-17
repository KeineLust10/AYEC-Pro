# -*- coding: utf-8 -*-

"""
Patches:
1. add_service_definition_dialog.py - add chip buttons next to the price spin box
2. add_device_dialog.py - add chip buttons next to the spin_cost spin box
"""
import os

CHIP_STYLE = """theme_qss('''
            QRadioButton {
                background: @surface_alt;
                color: @text_muted;
                padding: 5px 12px;
                border-radius: 10px;
                font-weight: bold;
                font-size: 13px;
                border: 1px solid @border;
            }
            QRadioButton::indicator { width: 0; height: 0; }
            QRadioButton:checked { background: @accent; color: @selection_text; border: 1px solid @accent; }
            QRadioButton:hover:!checked { background: @surface; color: @text; }
        ''')"""

# ─────────────────────────────────────────────────────────────────
# 1. add_service_definition_dialog.py
# ─────────────────────────────────────────────────────────────────
fpath = r'src/ui/dialogs/add_service_definition_dialog.py'
with open(fpath, 'r', encoding='utf-8') as f:
    content = f.read()

# Add imports
if 'QRadioButton' not in content:
    content = content.replace(
        'from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, \n                             QLineEdit, QPushButton, QDoubleSpinBox, QFormLayout, QFrame,\n                             QGraphicsDropShadowEffect, QPlainTextEdit)',
        'from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, \n                             QLineEdit, QPushButton, QDoubleSpinBox, QFormLayout, QFrame,\n                             QGraphicsDropShadowEffect, QPlainTextEdit, QRadioButton, QButtonGroup)'
    )

# Replace the price setup block with chip buttons
old_price = '''        self.inp_price = QDoubleSpinBox()
        self.inp_price.setRange(0, 999999)
        symbol = CurrencyHelper.get_symbol()
        self.inp_price.setSuffix(f" {symbol}")
        self.inp_price.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons) # Cleaner look
        content_box.addLayout(create_input_group("Birim Fiyat", self.inp_price))'''

new_price = '''        self.inp_price = QDoubleSpinBox()
        self.inp_price.setRange(0, 999999)
        self.inp_price.setSuffix(" ₺")
        self.inp_price.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)

        # Currency Chip Buttons
        _chip_sty = ''' + CHIP_STYLE + '''
        self.svc_btn_try = QRadioButton("₺")
        self.svc_btn_usd = QRadioButton("$")
        self.svc_btn_eur = QRadioButton("€")
        self.svc_btn_grp = QButtonGroup(self)
        self.svc_btn_grp.addButton(self.svc_btn_try, 1)
        self.svc_btn_grp.addButton(self.svc_btn_usd, 2)
        self.svc_btn_grp.addButton(self.svc_btn_eur, 3)
        for _b in [self.svc_btn_try, self.svc_btn_usd, self.svc_btn_eur]:
            _b.setStyleSheet(_chip_sty)
            _b.setCursor(Qt.CursorShape.PointingHandCursor)
        self.svc_btn_try.setChecked(True)

        def _svc_update_suffix():
            _sym = "$" if self.svc_btn_usd.isChecked() else "€" if self.svc_btn_eur.isChecked() else "₺"
            self.inp_price.setSuffix(f" {_sym}")
        self.svc_btn_try.toggled.connect(_svc_update_suffix)
        self.svc_btn_usd.toggled.connect(_svc_update_suffix)
        self.svc_btn_eur.toggled.connect(_svc_update_suffix)

        svc_price_h = QHBoxLayout()
        svc_price_h.addWidget(self.inp_price)
        svc_price_h.addWidget(self.svc_btn_try)
        svc_price_h.addWidget(self.svc_btn_usd)
        svc_price_h.addWidget(self.svc_btn_eur)

        price_wrap = QVBoxLayout()
        price_wrap.addWidget(QLabel("Birim Fiyat", styleSheet=theme_qss("color: @text_muted; font-size: 12px; font-weight: 700;")))
        price_wrap.addLayout(svc_price_h)
        content_box.addLayout(price_wrap)'''

content = content.replace(old_price, new_price)

# Also fix get_data to expose currency selection
old_get = '''    def get_data(self):
        return {
            "name": self.inp_name.text().strip().upper(),
            "price": self.inp_price.value(),
            "description": self.inp_desc.toPlainText().strip(),
            "barcode": self.inp_barcode.text().strip()
        }'''
new_get = '''    def get_data(self):
        _curr = "USD" if self.svc_btn_usd.isChecked() else "EUR" if self.svc_btn_eur.isChecked() else "TRY"
        return {
            "name": self.inp_name.text().strip().upper(),
            "price": self.inp_price.value(),
            "currency": _curr,
            "description": self.inp_desc.toPlainText().strip(),
            "barcode": self.inp_barcode.text().strip()
        }'''
content = content.replace(old_get, new_get)

with open(fpath, 'w', encoding='utf-8') as f:
    f.write(content)
print(f'Patched {fpath}')


# ─────────────────────────────────────────────────────────────────
# 2. add_device_dialog.py - spin_cost  (Tahmini Tutar)
# ─────────────────────────────────────────────────────────────────
fpath = r'src/ui/dialogs/add_device_dialog.py'
with open(fpath, 'r', encoding='utf-8') as f:
    content = f.read()

# Add imports
if 'QRadioButton' not in content:
    content = content.replace(
        'from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, \n                             QLineEdit, QPushButton, QComboBox, QTextEdit, \n                             QDateEdit, QFormLayout, QFrame, QGraphicsDropShadowEffect)',
        'from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, \n                             QLineEdit, QPushButton, QComboBox, QTextEdit, \n                             QDateEdit, QFormLayout, QFrame, QGraphicsDropShadowEffect,\n                             QRadioButton, QButtonGroup, QDoubleSpinBox)'
    )

old_cost = '''        self.spin_cost = QDoubleSpinBox()
        self.spin_cost.setRange(0, 50000)
        self.spin_cost.setSuffix(" TL")
        self.spin_cost.setFixedHeight(45)
        self.spin_cost.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        
        ff.addRow("Arıza Tanımı:", desc_h)
        ff.addRow("Öncelik:", self.combo_urgency)
        ff.addRow("Tahmini Tutar:", self.spin_cost)'''

new_cost = '''        self.spin_cost = QDoubleSpinBox()
        self.spin_cost.setRange(0, 50000)
        self.spin_cost.setSuffix(" ₺")
        self.spin_cost.setFixedHeight(45)
        self.spin_cost.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        # Currency Chips
        _dc_chip_sty = ''' + CHIP_STYLE + '''
        self.cost_btn_try = QRadioButton("₺")
        self.cost_btn_usd = QRadioButton("$")
        self.cost_btn_eur = QRadioButton("€")
        self.cost_btn_grp = QButtonGroup(self)
        self.cost_btn_grp.addButton(self.cost_btn_try, 1)
        self.cost_btn_grp.addButton(self.cost_btn_usd, 2)
        self.cost_btn_grp.addButton(self.cost_btn_eur, 3)
        for _b in [self.cost_btn_try, self.cost_btn_usd, self.cost_btn_eur]:
            _b.setStyleSheet(_dc_chip_sty)
            _b.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cost_btn_try.setChecked(True)
        def _dc_suffix():
            _s = "$" if self.cost_btn_usd.isChecked() else "€" if self.cost_btn_eur.isChecked() else "₺"
            self.spin_cost.setSuffix(f" {_s}")
        self.cost_btn_try.toggled.connect(_dc_suffix)
        self.cost_btn_usd.toggled.connect(_dc_suffix)
        self.cost_btn_eur.toggled.connect(_dc_suffix)

        cost_h = QHBoxLayout()
        cost_h.addWidget(self.spin_cost)
        cost_h.addWidget(self.cost_btn_try)
        cost_h.addWidget(self.cost_btn_usd)
        cost_h.addWidget(self.cost_btn_eur)
        
        ff.addRow("Arıza Tanımı:", desc_h)
        ff.addRow("Öncelik:", self.combo_urgency)
        ff.addRow("Tahmini Tutar:", cost_h)'''

content = content.replace(old_cost, new_cost)

with open(fpath, 'w', encoding='utf-8') as f:
    f.write(content)
print(f'Patched {fpath}')

print('Done')
