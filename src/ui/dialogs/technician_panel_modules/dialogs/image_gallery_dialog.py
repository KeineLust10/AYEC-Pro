# -*- coding: utf-8 -*-

"""
Image Gallery Dialog
Cihaz fotoğraflarını görüntüleme dialog'u
"""
from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.design_system import DesignTokens
import os


class ImageGalleryDialog(ModernDialog):
    """Cihaz fotoğraflarını gösteren dialog"""
    
    def __init__(self, path, parent=None):
        super().__init__("Cihaz Fotoğrafları", parent, width=800, height=600)
        self.path = path
        self.setup_content()
        
    def setup_content(self):
        lbl = QLabel()
        
        if self.path and os.path.exists(self.path):
            pix = QPixmap(self.path).scaled(
                750, 550, 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            lbl.setPixmap(pix)
        else:
            lbl.setText("Görüntü bulunamadı veya yol geçersiz.")
            lbl.setStyleSheet(
                f"color: {DesignTokens.MUTED_FOREGROUND}; font-size: 18px;"
            )
        
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.add_widget(lbl)
        self.add_cancel_button("Kapat")
