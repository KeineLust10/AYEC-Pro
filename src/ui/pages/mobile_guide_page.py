# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, QFrame, QHBoxLayout)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QPixmap, QImage
from src.utils.theme_colors import theme_qss, tc
from src.utils.design_system import DesignTokens
from src.utils.logger import logger

class MobileGuidePage(QWidget):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # Title
        title = QLabel("📱 Mobil Optik Giriş (Akıllı Stok)")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("color: @text;"))
        layout.addWidget(title)
        
        subtitle = QLabel("Telefonunuzu bir barkod okuyucuya dönüştürün. Depo yönetimi artık cebinizde.")
        subtitle.setStyleSheet(theme_qss("color: @text_muted; font-size: 16px;"))
        layout.addWidget(subtitle)
        
        # Content Card
        card = QFrame()
        card.setStyleSheet(theme_qss("""
            QFrame {
                background-color: @surface;
                border-radius: 20px;
                border: 1px solid @border;
            }
        """))
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(40, 40, 40, 40)
        card_layout.setSpacing(40)
        
        # Left: Steps
        steps_layout = QVBoxLayout()
        steps_layout.setSpacing(20)
        
        steps = [
            ("1. Bağlantı", "Telefonunuzun ve bilgisayarınızın aynı Wi-Fi ağında olduğundan emin olun."),
            ("2. Tarama", "Yandaki QR kodu telefonunuzun kamerasıyla okutun veya tarayıcıdan adresi girin."),
            ("3. Başlangıç", "Açılan ekranda 'Kameraya İzin Ver' diyerek barkod okutmaya başlayın."),
            ("4. Akıllı Stok", "Ürün varsa stok ekleyin, yoksa fotoğrafını çekip anında kaydedin.")
        ]
        
        import socket
        try:
            # Get Local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception as e:
            logger.debug(f"MobileGuidePage local IP fallback: {e}")
            local_ip = "127.0.0.1"
            
        url = f"http://{local_ip}:8000/static/stock_scanner.html"
        
        for head, body in steps:
            step_w = QWidget()
            sl = QVBoxLayout(step_w)
            sl.setContentsMargins(0,0,0,0)
            h = QLabel(head)
            h.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
            h.setStyleSheet(theme_qss("color: @text;"))
            b = QLabel(body)
            b.setStyleSheet(theme_qss("color: @text_muted; font-size: 14px;"))
            b.setWordWrap(True)
            sl.addWidget(h)
            sl.addWidget(b)
            steps_layout.addWidget(step_w)
            
        # Address Link
        link_lbl = QLabel(f"🔗 Manuel Adres: <a href='{url}'>{url}</a>")
        link_lbl.setOpenExternalLinks(True)
        link_lbl.setStyleSheet(theme_qss("font-size: 16px; margin-top: 20px; color: @accent_hover;"))
        steps_layout.addWidget(link_lbl)
        
        steps_layout.addStretch()
        card_layout.addLayout(steps_layout, 60)
        
        # Right: QR Code
        qr_frame = QFrame()
        qr_frame.setStyleSheet(theme_qss("background: @surface_alt; border-radius: 20px; border: 2px dashed @border;"))
        qr_layout = QVBoxLayout(qr_frame)
        qr_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        qr_lbl = QLabel()
        qr_layout.addWidget(qr_lbl)
        
        qr_desc = QLabel("Taramak için telefon kamerasını kullanın")
        qr_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qr_desc.setStyleSheet(theme_qss("color: @disabled_text; font-weight: 500; margin-top: 15px;"))
        qr_layout.addWidget(qr_desc)
        
        qr_ready = False
        try:
            import qrcode
            import io
            qr = qrcode.QRCode(box_size=10, border=2)
            qr.add_data(url)
            qr.make(fit=True)
            img = qr.make_image(fill_color=tc("text"), back_color=tc("selection_text"))
            buf = io.BytesIO()
            img.save(buf)
            qimg = QImage.fromData(buf.getvalue())
            pixmap = QPixmap.fromImage(qimg)
            qr_lbl.setPixmap(pixmap.scaled(300, 300, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            qr_ready = True
        except Exception:
            qr_lbl.setText("QR üretilemedi")
            qr_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            qr_lbl.setStyleSheet(theme_qss("color: @disabled_text; font-size: 14px; font-weight: 600;"))
        
        if not qr_ready:
            qr_desc.setText("Manuel adresi kullanın")
        
        card_layout.addWidget(qr_frame, 40)
        
        layout.addWidget(card)
        layout.addStretch()


