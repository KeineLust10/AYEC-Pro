# -*- coding: utf-8 -*-


import sys
import hashlib
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QMessageBox, QFrame, QGraphicsDropShadowEffect)
from PyQt6.QtGui import QFont, QIcon, QColor, QPalette, QBrush, QLinearGradient, QPainter, QPainterPath
from PyQt6.QtCore import Qt, QSize, QPoint

class ModernKeygen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AYEC Pro - Lisans Yöneticisi")
        self.setFixedSize(800, 550)
        
        # Frameless & Rounded Settings
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Dragging variables
        self.oldPos = self.pos()
        
        # Premium Dark Theme Strategy
        self.setup_theme()
        self.init_ui()

    def setup_theme(self):
        # Setting up a dark premium palette
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(0, 0, 0, 0)) # Transparent for window
        self.setPalette(palette)
        self.font_main = QFont("Segoe UI", 10)
        self.setFont(self.font_main)

    def paintEvent(self, event):
        # Draw rounded background
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 20, 20)
        
        # Dark Background Fill
        painter.fillPath(path, QBrush(QColor(30, 30, 35))) 

    def init_ui(self):
        # Main layout wrapper
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20) # Padding for window content
        main_layout.setSpacing(10)

        # 0. Custom Title Bar Area
        title_bar = QHBoxLayout()
        title_bar.addStretch()
        
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(30, 30)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #7f8c8d;
                border: none;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                color: #e74c3c;
            }
        """)
        btn_close.clicked.connect(self.close)
        title_bar.addWidget(btn_close)
        
        main_layout.addLayout(title_bar)

        # 1. Header Area
        header_layout = QVBoxLayout()
        header_layout.setSpacing(5)
        
        title = QLabel("LİSANS ANAHTARI OLUŞTURUCU")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: #3498db; letter-spacing: 2px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        subtitle = QLabel("AYEC Pro Teknik Servis Yazılımı")
        subtitle.setFont(QFont("Segoe UI", 11))
        subtitle.setStyleSheet("color: #7f8c8d;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        main_layout.addLayout(header_layout)

        # 2. Main Card
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #2c3e50;
                border-radius: 12px;
                border: 1px solid #34495e;
            }
        """)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(25, 25, 25, 25)
        card_layout.setSpacing(15)
        
        # Input Section
        lbl_hwid = QLabel("HEDEF CİHAZ KİMLİĞİ (HWID)")
        lbl_hwid.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_hwid.setStyleSheet("color: #bdc3c7;")
        
        self.inp_hwid = QLineEdit()
        self.inp_hwid.setPlaceholderText("HWID Yapıştırın...")
        self.inp_hwid.setFixedHeight(45)
        self.inp_hwid.setStyleSheet("""
            QLineEdit {
                background-color: #34495e;
                border: 1px solid #465a6f;
                border-radius: 6px;
                color: white;
                font-size: 13px;
                padding: 10px;
            }
            QLineEdit:focus {
                border: 1px solid #3498db;
                background-color: #3d566e;
            }
        """)
        
        card_layout.addWidget(lbl_hwid)
        card_layout.addWidget(self.inp_hwid)
        
        # Generate Button - Full Width within card
        self.btn_gen = QPushButton("🔒 ANAHTAR OLUŞTUR")
        self.btn_gen.setFixedHeight(50)
        self.btn_gen.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_gen.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.btn_gen.setStyleSheet("""
            QPushButton {
                background-color: #2980b9;
                color: white;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #3498db;
            }
        """)
        self.btn_gen.clicked.connect(self.generate_key)
        card_layout.addWidget(self.btn_gen)
        
        # Result Section
        lbl_res = QLabel("ÜRETİLEN LİSANS ANAHTARI")
        lbl_res.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_res.setStyleSheet("color: #2ecc71; margin-top: 10px;")
        
        self.out_key = QLineEdit()
        self.out_key.setReadOnly(True)
        self.out_key.setPlaceholderText("XXXXX-XXXXX-XXXXX-XXXXX-XXXXX")
        self.out_key.setFixedHeight(55)
        self.out_key.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.out_key.setStyleSheet("""
            QLineEdit {
                background-color: #253340;
                border: 2px dashed #2ecc71;
                border-radius: 6px;
                color: #2ecc71;
                font-size: 22px;
                font-family: 'Consolas', monospace;
                font-weight: bold;
            }
        """)
        
        card_layout.addWidget(lbl_res)
        card_layout.addWidget(self.out_key)

        main_layout.addWidget(card)

        # Footer Actions (Close to card)
        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(15)
        
        btn_clear = QPushButton("🗑️ Temizle")
        btn_clear.setFixedWidth(120)
        btn_clear.setFixedHeight(35)
        btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #e74c3c;
                border: 1px solid #e74c3c;
                border-radius: 17px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e74c3c;
                color: white;
            }
        """)
        btn_clear.clicked.connect(self.clear_all)
        
        btn_copy = QPushButton("📋 Kopyala")
        btn_copy.setFixedWidth(120)
        btn_copy.setFixedHeight(35)
        btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #2c3e50;
                border-radius: 17px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ecf0f1;
            }
        """)
        btn_copy.clicked.connect(self.copy_key)
        
        footer_layout.addStretch()
        footer_layout.addWidget(btn_clear)
        footer_layout.addWidget(btn_copy)
        footer_layout.addStretch()
        
        main_layout.addLayout(footer_layout)
        
        # Brand Footer
        brand = QLabel("Bulut Teknik Servis Security Systems")
        brand.setStyleSheet("color: #555; font-size: 10px;")
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(brand)

    # Window Drag Logic
    def mousePressEvent(self, event):
        self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        delta = QPoint(event.globalPos() - self.oldPos)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.oldPos = event.globalPos()

    def generate_key(self):
        hwid = self.inp_hwid.text().strip()
        if not hwid:
            QMessageBox.warning(self, "Uyarı", "Lütfen önce bir HWID (Cihaz Kimliği) giriniz.")
            return

        try:
            # Replicated logic to ensure standalone function
            SALT = "BULUT_TEKNIK_SERVIS_2026_SECURE_SALT_!@#"
            raw_data = f"{hwid}{SALT}"
            import hashlib
            hash_obj = hashlib.sha256(raw_data.encode())
            full_hash = hash_obj.hexdigest().upper()
            
            key_raw = full_hash[:25]
            parts = [key_raw[i:i+5] for i in range(0, 25, 5)]
            final_key = "-".join(parts)
            
            self.out_key.setText(final_key)
            
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Üretim Hatası: {str(e)}")

    def copy_key(self):
        key = self.out_key.text()
        if key:
            clipboard = QApplication.clipboard()
            clipboard.setText(key)
            QMessageBox.information(self, "Bilgi", "Lisans anahtarı panoya kopyalandı!")
        else:
             QMessageBox.warning(self, "Uyarı", "Kopyalanacak bir anahtar yok.")

    def clear_all(self):
        self.inp_hwid.clear()
        self.out_key.clear()
        self.inp_hwid.setFocus()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModernKeygen()
    window.show()
    sys.exit(app.exec())
