# -*- coding: utf-8 -*-


import sys
import hashlib
import base64
import platform
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QMessageBox, QFrame)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon

class LicenseGenerator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AYEC Pro - Lisans Üretici")
        self.setFixedSize(500, 400)
        self.setStyleSheet("""
            QMainWindow { background-color: #f8f9fa; }
            QLabel { font-family: 'Segoe UI'; }
            QLineEdit { 
                padding: 10px; 
                border: 1px solid #ced4da; 
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton {
                background-color: #0d6efd;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #0b5ed7; }
        """)
        
        container = QWidget()
        self.setCentralWidget(container)
        layout = QVBoxLayout(container)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Header
        title = QLabel("Lisans Anahtarı Üretici")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # HWID Input
        lbl_hwid = QLabel("Müşteri HWID:")
        lbl_hwid.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(lbl_hwid)
        
        self.inp_hwid = QLineEdit()
        self.inp_hwid.setPlaceholderText("Müşteriden gelen HWID'yi yapıştırın...")
        layout.addWidget(self.inp_hwid)
        
        # Generate Button
        self.btn_gen = QPushButton("ANAHTAR ÜRET")
        self.btn_gen.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_gen.clicked.connect(self.generate_key)
        layout.addWidget(self.btn_gen)
        
        # Result Area
        res_group = QFrame()
        res_group.setStyleSheet("background-color: white; border-radius: 8px; border: 1px solid #e9ecef;")
        res_layout = QVBoxLayout(res_group)
        
        lbl_res = QLabel("Üretilen Lisans Anahtarı:")
        lbl_res.setStyleSheet("color: #6c757d; border: none;")
        res_layout.addWidget(lbl_res)
        
        self.out_key = QLineEdit()
        self.out_key.setReadOnly(True)
        self.out_key.setStyleSheet("background-color: #e9ecef; font-family: Consolas; font-weight: bold; color: #198754;")
        res_layout.addWidget(self.out_key)
        
        self.btn_copy = QPushButton("Kopyala")
        self.btn_copy.setStyleSheet("background-color: #198754; margin-top: 5px;")
        self.btn_copy.clicked.connect(self.copy_key)
        res_layout.addWidget(self.btn_copy)
        
        layout.addWidget(res_group)
        layout.addStretch()

    def generate_license_key(self, target_hwid):
        # Must match SecurityManager logic EXACTLY
        SALT = "BULUT_TEKNIK_SERVIS_2026_SECURE_SALT_!@#"
        raw_data = f"{target_hwid}{SALT}"
        hash_obj = hashlib.sha256(raw_data.encode())
        full_hash = hash_obj.hexdigest().upper()
        
        key_raw = full_hash[:25]
        parts = [key_raw[i:i+5] for i in range(0, 25, 5)]
        final_key = "-".join(parts)
        return final_key

    def generate_key(self):
        hwid = self.inp_hwid.text().strip()
        if not hwid:
            QMessageBox.warning(self, "Hata", "Lütfen bir HWID girin!")
            return
            
        key = self.generate_license_key(hwid)
        self.out_key.setText(key)
        
    def copy_key(self):
        key = self.out_key.text()
        if key:
            QApplication.clipboard().setText(key)
            QMessageBox.information(self, "Başarılı", "Lisans anahtarı kopyalandı!")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LicenseGenerator()
    window.show()
    sys.exit(app.exec())
