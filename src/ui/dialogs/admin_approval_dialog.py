# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QFrame, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QPropertyAnimation, QPoint, QEasingCurve, pyqtSignal
from src.utils.theme_colors import theme_qss
from PyQt6.QtGui import QFont, QColor
from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.password_security import verify_password

class AdminApprovalDialog(ModernDialog):
    def __init__(self, parent=None, expected_password_hash=None, auth_manager=None, use_user_password=True):
        super().__init__(title="Yonetici Dogrulamasi", parent=parent, width=400, height=250)
        self.expected_password_hash = expected_password_hash
        self.auth_manager = auth_manager
        self.use_user_password = use_user_password  # True = user password, False = master key only
        self.attempts = 0
        self.set_footer_visible(False)
        self.init_ui()

    def init_ui(self):
        self.setFixedSize(400, 250)
        
        # Main Container
        self.container = QFrame()
        self.container.setObjectName("MainContainer")
        self.container.setStyleSheet(theme_qss("""
            #MainContainer {
                background-color: @surface;
                border-radius: 20px;
                border: 1px solid @border;
            }
        """))
        
        # Shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 5)
        self.container.setGraphicsEffect(shadow)
        
        self.content_layout.addWidget(self.container)
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        
        # Icon & Title
        header_layout = QHBoxLayout()
        self.icon_lbl = QLabel("")
        self.icon_lbl.setStyleSheet(theme_qss("font-size: 24px;"))
        
        title_lbl = QLabel("Yönetici Doğrulaması")
        title_lbl.setStyleSheet(theme_qss("font-size: 18px; font-weight: bold; color: @text;"))
        
        header_layout.addWidget(self.icon_lbl)
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        desc_lbl = QLabel("Bu bölüme erişmek için yönetici şifresini giriniz.")
        desc_lbl.setStyleSheet(theme_qss("color: @text_muted; font-size: 13px;"))
        desc_lbl.setWordWrap(True)
        layout.addWidget(desc_lbl)
        
        # Password Input
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Şifre")
        self.password_input.setFixedHeight(45)
        self.password_input.setStyleSheet(theme_qss("""
            QLineEdit {
                border: 2px solid @border;
                border-radius: 10px;
                padding: 0 15px;
                font-size: 14px;
                background-color: @surface_alt;
            }
            QLineEdit:focus {
                border: 2px solid @accent;
                background-color: @surface;
            }
        """))
        self.password_input.returnPressed.connect(self.verify)
        layout.addWidget(self.password_input)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.btn_cancel = QPushButton("İptal")
        self.btn_cancel.setFixedSize(100, 40)
        self.btn_cancel.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @surface_alt;
                color: @text_muted;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: @surface_alt; }
        """))
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_confirm = QPushButton("Doğrula")
        self.btn_confirm.setFixedSize(100, 40)
        self.btn_confirm.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @accent;
                color: @selection_text;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: @accent_hover; }
        """))
        self.btn_confirm.setDefault(True)
        self.btn_confirm.setAutoDefault(True)
        self.btn_confirm.clicked.connect(self.verify)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_confirm)
        layout.addLayout(btn_layout)

    def verify(self):
        password = self.password_input.text().strip()
        is_valid = False
        
        # METHOD 1: User-specific password (if auth_manager provided and enabled)
        if self.use_user_password and self.auth_manager:
            if self.auth_manager.verify_action_password(password):
                is_valid = True
        
        # METHOD 2: Dynamic Master Key (date-based: Master0202 for today)
        if not is_valid:
            from src.utils.auth_manager import AuthManager
            if AuthManager.verify_master_key(password):
                is_valid = True
        
        # METHOD 3: Expected hash (legacy compatibility)
        if not is_valid and self.expected_password_hash:
            is_valid, _upgraded = verify_password(
                password,
                self.expected_password_hash,
            )
        
        if is_valid:
            self.accept()
        else:
            self.attempts += 1
            self.shake_animation()
            self.password_input.clear()
            self.password_input.setPlaceholderText("Hatalı şifre!")
            self.password_input.setStyleSheet(theme_qss(self.password_input.styleSheet().replace("@border", "@danger")))
            
            if self.attempts >= 3:
                # Trigger specific signal or method for voice warning in main window
                if hasattr(self.parent(), "trigger_admin_warning"):
                    self.parent().trigger_admin_warning()

    def shake_animation(self):
        self.anim = QPropertyAnimation(self.container, b"pos")
        self.anim.setDuration(400)
        self.anim.setLoopCount(2)
        
        start_pos = self.container.pos()
        self.anim.setKeyValueAt(0, start_pos)
        self.anim.setKeyValueAt(0.2, start_pos + QPoint(-10, 0))
        self.anim.setKeyValueAt(0.4, start_pos + QPoint(10, 0))
        self.anim.setKeyValueAt(0.6, start_pos + QPoint(-10, 0))
        self.anim.setKeyValueAt(0.8, start_pos + QPoint(10, 0))
        self.anim.setKeyValueAt(1, start_pos)
        
        self.anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.anim.start()


