# -*- coding: utf-8 -*-

"""
Login Dialog for Desktop Application
Uygulama açılışında kullanıcı doğrulama ekranı
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QFrame)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap, QIcon, QAction
from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.message_helper import show_error, show_warning


class LoginDialog(ModernDialog):
    """
    Modern Login Dialog
    Kullanıcı adı ve şifre ile giriş
    """
    def __init__(self, db, parent=None):
        super().__init__(title="AYEC Pro - Giris", parent=parent, width=450, height=500)
        self.db = db
        self.authenticated_user = None
        self.setModal(True)
        self.set_footer_visible(False)
        self.init_ui()
    
    def init_ui(self):
        layout = self.content_layout
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # Logo/Icon Area
        logo_frame = QFrame()
        logo_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #2563eb, stop:1 #1d4ed8);
                border-radius: 60px;
            }
        """)
        logo_frame.setFixedSize(120, 120)
        logo_layout = QVBoxLayout(logo_frame)
        
        logo_label = QLabel("🔐")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setStyleSheet("font-size: 60px; background: transparent;")
        logo_layout.addWidget(logo_label)
        
        logo_container = QHBoxLayout()
        logo_container.addStretch()
        logo_container.addWidget(logo_frame)
        logo_container.addStretch()
        layout.addLayout(logo_container)
        
        # Title
        title = QLabel("Giriş Yapın")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title.setStyleSheet("color: #1e293b; margin-top: 10px;")
        layout.addWidget(title)
        
        # Subtitle
        subtitle = QLabel("Devam etmek için kullanıcı bilgilerinizi girin")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #64748b; font-size: 13px; margin-bottom: 20px;")
        layout.addWidget(subtitle)
        
        # Username Field
        username_label = QLabel("Kullanıcı Adı")
        username_label.setStyleSheet("color: #475569; font-weight: 600; font-size: 13px;")
        layout.addWidget(username_label)
        
        self.txt_username = QLineEdit()
        self.txt_username.setPlaceholderText("Kullanıcı adınızı girin")
        self.txt_username.setStyleSheet("""
            QLineEdit {
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 14px;
                background: white;
            }
            QLineEdit:focus {
                border-color: #2563eb;
            }
        """)
        layout.addWidget(self.txt_username)
        
        # Password Field
        password_label = QLabel("Şifre")
        password_label.setStyleSheet("color: #475569; font-weight: 600; font-size: 13px; margin-top: 10px;")
        layout.addWidget(password_label)
        
        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_password.setPlaceholderText("Şifrenizi girin")
        self.txt_password.setStyleSheet("""
            QLineEdit {
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 14px;
                background: white;
            }
            QLineEdit:focus {
                border-color: #2563eb;
            }
        """)
        self.txt_username.returnPressed.connect(self.txt_password.setFocus)
        self.txt_password.returnPressed.connect(self.do_login)
        layout.addWidget(self.txt_password)
        
        # Login Button
        self.btn_login = QPushButton("Giriş Yap")
        self.btn_login.setFixedHeight(50)
        self.btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_login.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2563eb, stop:1 #1d4ed8);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 15px;
                font-weight: bold;
                margin-top: 10px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1d4ed8, stop:1 #1e40af);
            }
            QPushButton:pressed {
                background: #1e40af;
            }
        """)
        self.btn_login.clicked.connect(self.do_login)
        layout.addWidget(self.btn_login)
        
        # Info Text
        info_label = QLabel("Yetkili kullanici bilgilerinizle giris yapin.")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("color: #94a3b8; font-size: 11px; margin-top: 10px;")
        layout.addWidget(info_label)
        
        layout.addStretch()
        
        # Set focus to username
        self.txt_username.setFocus()
    
    def do_login(self):
        """Perform login authentication"""
        username = self.txt_username.text().strip()
        password = self.txt_password.text()
        
        if not username or not password:
            show_warning(
                self, 
                "Uyarı", 
                "Lütfen kullanıcı adı ve şifre girin!"
            )
            return
        
        try:
            # Authenticate user
            user = self.db.authenticate_user(username, password)
            
            if user:
                self.authenticated_user = {
                    'id': user['id'],
                    'username': user['username'],
                    'email': user['email'] if 'email' in user.keys() else '',
                    'role': user['role'] if 'role' in user.keys() else 'Personel',
                    'personnel_id': (
                        user['personnel_id']
                        if 'personnel_id' in user.keys()
                        else None
                    ),
                }
                self.accept()  # Close dialog with success
            else:
                show_error(
                    self,
                    "Giriş Başarısız",
                    "Kullanıcı adı veya şifre hatalı!"
                )
                self.txt_password.clear()
                self.txt_password.setFocus()
                
        except Exception as e:
            show_error(
                self,
                "Hata",
                f"Giriş sırasında hata oluştu: {e}"
            )
    
    def get_authenticated_user(self):
        """Return authenticated user info"""
        return self.authenticated_user

