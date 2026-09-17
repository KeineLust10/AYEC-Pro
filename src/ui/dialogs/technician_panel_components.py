# -*- coding: utf-8 -*-

import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout

from src.ui.widgets.modern_dialog import ModernDialog
from src.ui.widgets.modern_inputs import ValidatedLineEdit
from src.utils.validators import Validators
from src.utils.design_system import DesignTokens
from src.utils.theme_colors import theme_qss


# Helper for grid form rows
def add_field(layout, label_text, widget, row, col=0, colspan=1):
    lbl = QLabel(label_text)
    lbl.setStyleSheet(theme_qss(f"color: {DesignTokens.MUTED_FOREGROUND}; font-size: 13px; font-weight: 600; margin-bottom: 2px; border:none; background:transparent;"))
    vbox = QVBoxLayout()
    vbox.setSpacing(2)
    vbox.addWidget(lbl)
    vbox.addWidget(widget)
    layout.addLayout(vbox, row, col, 1, colspan)

class ImageGalleryDialog(ModernDialog):
    def __init__(self, path, parent=None):
        super().__init__("Cihaz Fotoğrafları", parent, width=800, height=600)
        self.path = path
        self.setup_content()
        
    def setup_content(self):
        lbl = QLabel()
        if self.path and os.path.exists(self.path):
            pix = QPixmap(self.path).scaled(750, 550, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            lbl.setPixmap(pix)
        else:
            lbl.setText("Görüntü bulunamadı veya yol geçersiz.")
            lbl.setStyleSheet(theme_qss(f"color: {DesignTokens.MUTED_FOREGROUND}; font-size: 18px;"))
        
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.add_widget(lbl)
        self.add_cancel_button("Kapat")

class ModernManualProductDialog(ModernDialog):
    def __init__(self, parent=None):
        super().__init__("Manuel Ürün/Hizmet Ekle", parent, width=400, height=350)
        self.result_data = None
        self.setup_content()
        
    def setup_content(self):
        self.inp_name = ValidatedLineEdit("Ürün/Hizmet Adı")
        self.inp_price = ValidatedLineEdit("Fiyat (₺)", validator_func=Validators.is_numeric)
        
        self.add_widget(QLabel("Hizmet veya Ürün Adı:"))
        self.add_widget(self.inp_name)
        self.add_widget(QLabel("Birim Fiyat:"))
        self.add_widget(self.inp_price)
        
        self.add_button("Ekle", callback=self.save)
        self.add_cancel_button("İptal")
        
    def save(self):
        if self.inp_name.text() and self.inp_price.text():
            try:
                price = float(self.inp_price.text().replace(",", "."))
                self.result_data = (self.inp_name.text(), price)
                self.accept()
            except ValueError:
                return


