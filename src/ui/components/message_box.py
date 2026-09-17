# -*- coding: utf-8 -*-

"""
ModernMessage - Premium mesaj kutuları (MessageBox)
QMessageBox yerine kullanılacak modern, şık bildirim pencereleri
"""

from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QWidget
from PyQt6.QtCore import Qt, QSize
from src.utils.theme_colors import theme_qss, tc
from PyQt6.QtGui import QFont, QPixmap, QPainter, QColor
from .modern_dialog import ModernDialog


class ModernMessage(ModernDialog):
    """
    Premium MessageBox Sınıfı
    
    Türler:
    - Success (✓ Başarılı)
    - Error (✕ Hata)
    - Warning (⚠ Uyarı)
    - Info (ℹ Bilgi)
    """
    
    def __init__(self, parent=None, title="Bildirim", message="", msg_type="info"):
        super().__init__(parent, title=title, width=420, height=210, blur_background=True)
        
        self.message_text = message
        self.msg_type = msg_type
        
        self._setup_message_ui()
    
    def _setup_message_ui(self):
        """Mesaj kutusuna özel UI"""
        # İkon ve renkler
        icon_configs = {
            "success": {"icon": "✓", "color": tc("success"), "bg": tc("success_bg")},
            "error": {"icon": "✕", "color": tc("danger"), "bg": tc("danger_bg")},
            "warning": {"icon": "⚠", "color": tc("warning"), "bg": tc("warning_bg")},
            "info": {"icon": "ℹ", "color": tc("accent"), "bg": tc("selection_bg")}
        }
        
        config = icon_configs.get(self.msg_type, icon_configs["info"])
        
        # İkon label
        icon_label = QLabel(config["icon"])
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFixedSize(64, 64)
        icon_label.setFont(QFont("Segoe UI", 36, QFont.Weight.Bold))
        icon_label.setStyleSheet(theme_qss(f"""
            QLabel {{
                color: {config['color']};
                background-color: {config['bg']};
                border-radius: 32px;
                border: 3px solid {config['color']};
            }}
        """))
        
        # Mesaj metni
        msg_label = QLabel(self.message_text)
        msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg_label.setWordWrap(True)
        msg_label.setFont(QFont("Segoe UI", 11))
        msg_label.setStyleSheet(theme_qss("""
            QLabel {
                color: @text;
                padding: 4px 8px;
                line-height: 1.5;
            }
        """))
        
        # Onay butonu
        self.btn_ok = QPushButton("Tamam")
        self.btn_ok.setFixedHeight(38)
        self.btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ok.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        
        # Buton rengi mesaj tipine göre
        self.btn_ok.setStyleSheet(theme_qss(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {config['color']}, stop:1 {self._darken_color(config['color'])});
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 22px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background: {self._darken_color(config['color'])};
            }}
            QPushButton:pressed {{
                background: {self._darken_color(config['color'], 0.3)};
            }}
        """))
        self.btn_ok.clicked.connect(self.accept)
        
        # Layout
        self.content_layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addSpacing(8)
        self.content_layout.addWidget(msg_label)
        self.content_layout.addSpacing(6)
        self.content_layout.addWidget(self.btn_ok, 0, Qt.AlignmentFlag.AlignCenter)
    
    def _darken_color(self, hex_color, factor=0.2):
        """Rengi koyulaştır"""
        color = QColor(hex_color)
        h, s, v, a = color.getHsv()
        v = int(v * (1 - factor))
        color.setHsv(h, s, v, a)
        return color.name()
    
    # --- STATIK METODLAR (Kolay kullanım) ---
    
    @staticmethod
    def show_success(parent, message, title="Başarılı"):
        """Başarı mesajı göster"""
        dialog = ModernMessage(parent, title=title, message=message, msg_type="success")
        return dialog.exec()
    
    @staticmethod
    def show_error(parent, message, title="Hata"):
        """Hata mesajı göster"""
        dialog = ModernMessage(parent, title=title, message=message, msg_type="error")
        return dialog.exec()
    
    @staticmethod
    def show_warning(parent, message, title="Uyarı"):
        """Uyarı mesajı göster"""
        dialog = ModernMessage(parent, title=title, message=message, msg_type="warning")
        return dialog.exec()
    
    @staticmethod
    def show_info(parent, message, title="Bilgi"):
        """Bilgi mesajı göster"""
        dialog = ModernMessage(parent, title=title, message=message, msg_type="info")
        return dialog.exec()


class ModernConfirm(ModernDialog):
    """
    Premium Onay Penceresi (Evet/Hayır)
    """
    
    def __init__(self, parent=None, title="Onay", message="Devam etmek istiyor musunuz?"):
        super().__init__(parent, title=title, width=450, height=250, blur_background=True)
        
        self.message_text = message
        self.result = False
        
        self._setup_confirm_ui()
    
    def _setup_confirm_ui(self):
        """Onay penceresi UI"""
        # Soru ikonu
        icon_label = QLabel("?")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFixedSize(70, 70)
        icon_label.setFont(QFont("Segoe UI", 42, QFont.Weight.Bold))
        icon_label.setStyleSheet(theme_qss("""
            QLabel {
                color: @warning;
                background-color: @warning_bg;
                border-radius: 35px;
                border: 3px solid @warning;
            }
        """))
        
        # Mesaj
        msg_label = QLabel(self.message_text)
        msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg_label.setWordWrap(True)
        msg_label.setFont(QFont("Segoe UI", 11))
        msg_label.setStyleSheet(theme_qss("color: @text; padding: 10px;"))
        
        # Butonlar
        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(15)
        
        self.btn_yes = QPushButton("Evet")
        self.btn_yes.setFixedHeight(40)
        self.btn_yes.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_yes.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.btn_yes.setStyleSheet(theme_qss("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 @success, stop:1 @success);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 40px;
            }
            QPushButton:hover {
                background: @success;
            }
        """))
        self.btn_yes.clicked.connect(self._on_yes)
        
        self.btn_no = QPushButton("Hayır")
        self.btn_no.setFixedHeight(40)
        self.btn_no.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_no.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.btn_no.setStyleSheet(theme_qss("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 @disabled_text, stop:1 @text_muted);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 40px;
            }
            QPushButton:hover {
                background: @text_muted;
            }
        """))
        self.btn_no.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_yes)
        btn_layout.addWidget(self.btn_no)
        
        # Layout
        self.content_layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addSpacing(15)
        self.content_layout.addWidget(msg_label)
        self.content_layout.addStretch()
        self.content_layout.addWidget(btn_container)
    
    def _on_yes(self):
        """Evet tıklandı"""
        self.result = True
        self.accept()
    
    @staticmethod
    def ask(parent, message, title="Onay"):
        """Onay sorusu sor (True/False döner)"""
        dialog = ModernConfirm(parent, title=title, message=message)
        dialog.exec()
        return dialog.result

# Alias for backward compatibility (Fixing ImportError)
ModernMessageBox = ModernMessage

