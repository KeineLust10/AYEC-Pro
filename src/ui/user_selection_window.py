# -*- coding: utf-8 -*-

"""
User Selection Window
Kayıtlı kullanıcıları görsel kartlar halinde gösteren modern seçim ekranı
"""

import os
from PyQt6.QtWidgets import (QDialog as QtDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QGraphicsDropShadowEffect, QGridLayout, QFileDialog, QWidget, QApplication)
QDialog = QtDialog
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect, QVariantAnimation
from PyQt6.QtGui import QFont, QColor, QPainter, QLinearGradient, QBrush, QAction
from src.ui.dialogs.password_prompt_dialog import PasswordPromptDialog
from src.utils.toast_notification import show_error, show_success
from src.utils.logger import logger

class UserCard(QFrame):
    """Modern, premium, glass-effect user card"""
    clicked = pyqtSignal(dict)
    
    def __init__(self, user_data, db=None, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.db = db
        self.setFixedSize(280, 420)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setup_ui()
        
        # Entrance/Hover Animations
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(20)
        self.shadow.setXOffset(0)
        self.shadow.setYOffset(8)
        self.shadow.setColor(QColor(0, 0, 0, 40))
        self.setGraphicsEffect(self.shadow)
        
        self.hover_anim = QVariantAnimation()
        self.hover_anim.setDuration(300)
        self.hover_anim.setStartValue(20)
        self.hover_anim.setEndValue(45)
        self.hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        def update_shadow(v):
            try:
                if hasattr(self, 'shadow') and self.shadow:
                    self.shadow.setBlurRadius(v)
            except RuntimeError: pass # Object was deleted
            
        self.hover_anim.valueChanged.connect(update_shadow)

    def setup_ui(self):
        # Professional glass/gradient style
        self.setStyleSheet("""
            UserCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(255, 255, 255, 0.15), stop:1 rgba(255, 255, 255, 0.05));
                border-radius: 32px;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 40, 30, 40)
        layout.setSpacing(20)
        
        # Avatar Container with Glow
        avatar_frame = QFrame()
        avatar_frame.setFixedSize(140, 140)
        avatar_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #3b82f6, stop:1 #1d4ed8);
                border-radius: 70px;
                border: 4px solid rgba(255, 255, 255, 0.3);
            }
        """)
        
        vbox_av = QVBoxLayout(avatar_frame)
        vbox_av.setContentsMargins(0,0,0,0)
        
        avatar_label = QLabel()
        avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        photo_loaded = False
        if self.db:
            try:
                email = self.user_data.get('email', '')
                if email:
                    self.db.cursor.execute("SELECT photo_path FROM personnel WHERE email=?", (email,))
                    res = self.db.cursor.fetchone()
                    if res and res[0] and os.path.exists(res[0]):
                        pix = QPixmap(res[0])
                        if not pix.isNull():
                            # Create circular mask in painter if needed, or just setScaledContents
                            avatar_label.setPixmap(pix.scaled(132, 132, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
                            avatar_label.setStyleSheet("border-radius: 66px;")
                            avatar_label.setScaledContents(True)
                            photo_loaded = True
            except Exception as photo_err:
                logger.warning(f"User avatar load failed for {self.user_data.get('username', 'unknown')}: {photo_err}")
            
        if not photo_loaded:
            username = self.user_data.get('username', 'U')
            avatar_text = username[0].upper() if username else 'U'
            avatar_label.setText(avatar_text)
            avatar_label.setFont(QFont("Segoe UI", 42, QFont.Weight.Bold))
            avatar_label.setStyleSheet("color: white; background: transparent;")
            
        vbox_av.addWidget(avatar_label)
        layout.addWidget(avatar_frame, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Name
        name_lbl = QLabel(self.user_data.get('username', 'Kullanıcı'))
        name_lbl.setFont(QFont("Segoe UI Light", 24))
        name_lbl.setStyleSheet("color: white; font-weight: 200;")
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_lbl)
        
        # Role Label (Modern Minimalist)
        role = self.user_data.get('role', 'Sistem')
        role_lbl = QLabel(role.upper())
        role_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        role_lbl.setStyleSheet("""
            color: #3b82f6;
            background: rgba(59, 130, 246, 0.15);
            border-radius: 12px;
            padding: 6px 15px;
            letter-spacing: 1px;
        """)
        layout.addWidget(role_lbl, 0, Qt.AlignmentFlag.AlignCenter)
        
        layout.addStretch()
        
        # Action Hint (Visible on Hover)
        self.hint_lbl = QLabel("OTURUMU AÇ")
        self.hint_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.hint_lbl.setStyleSheet("color: rgba(255,255,255,0.5);")
        self.hint_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.hint_lbl)

    def enterEvent(self, event):
        self.setStyleSheet("""
            UserCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(255, 255, 255, 0.25), stop:1 rgba(255, 255, 255, 0.1));
                border-radius: 32px;
                border: 2px solid #3b82f6;
            }
        """)
        self.hover_anim.setDirection(QVariantAnimation.Direction.Forward)
        self.hover_anim.start()
        self.hint_lbl.setStyleSheet("color: #3b82f6;")

    def leaveEvent(self, event):
        self.setStyleSheet("""
            UserCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(255, 255, 255, 0.15), stop:1 rgba(255, 255, 255, 0.05));
                border-radius: 32px;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
        """)
        self.hover_anim.setDirection(QVariantAnimation.Direction.Backward)
        self.hover_anim.start()
        self.hint_lbl.setStyleSheet("color: rgba(255,255,255,0.5);")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.user_data)

class UserSelectionWindow(QtDialog):
    user_selected = pyqtSignal(object)
    
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(1200, 850)
        self.setup_ui()
        
        # Center On Screen
        screen = QApplication.primaryScreen()
        self.move(screen.availableGeometry().center() - self.rect().center())

    def setup_ui(self):
        # Main Outer Container (Translucent Background for rounded corners of child)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(50, 50, 50, 50)
        
        # Content Card with Sophisticated Gradient
        content_card = QFrame()
        content_card.setObjectName("ContentCard")
        content_card.setStyleSheet("""
            #ContentCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0f172a, stop:0.5 #1e293b, stop:1 #0f172a);
                border-radius: 40px;
                border: 2px solid rgba(255,255,255,0.05);
            }
        """)
        
        # Master Shadow for the Window
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(60)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 20)
        content_card.setGraphicsEffect(shadow)
        
        self.main_layout.addWidget(content_card)
        
        vbox = QVBoxLayout(content_card)
        vbox.setContentsMargins(60, 60, 60, 40)
        vbox.setSpacing(40)
        
        # --- Header ---
        header = QHBoxLayout()
        
        logo_vbox = QVBoxLayout()
        logo_vbox.setSpacing(8)
        
        title = QLabel("BULUT TEKNOLOJİ")
        title.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        title.setStyleSheet("color: white; letter-spacing: 2px;")
        logo_vbox.addWidget(title)
        
        subtitle = QLabel("Hesabınızı seçerek devam edin")
        subtitle.setFont(QFont("Segoe UI Light", 14))
        subtitle.setStyleSheet("color: #94a3b8;")
        logo_vbox.addWidget(subtitle)
        
        header.addLayout(logo_vbox)
        header.addStretch()
        
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(45, 45)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.close)
        btn_close.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.1);
                color: #cbd5e1;
                font-size: 20px;
                border-radius: 22px;
                border: none;
            }
            QPushButton:hover { background: #ef4444; color: white; }
        """)
        header.addWidget(btn_close)
        vbox.addLayout(header)
        
        # --- Scrollable Area for Users ---
        from PyQt6.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        grid = QHBoxLayout(scroll_content)
        grid.setSpacing(40)
        grid.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        users = self.get_users()
        for idx, user in enumerate(users):
            card = UserCard(user, db=self.db)
            card.clicked.connect(self.on_user_selected)
            grid.addWidget(card)
            
            # Simple entrance animation for cards
            card.setGraphicsEffect(None) # Remove for anim performance if needed
            card.setGraphicsEffect(QGraphicsDropShadowEffect(blurRadius=20, yOffset=8, color=QColor(0,0,0,50)))
        
        scroll.setWidget(scroll_content)
        vbox.addWidget(scroll)
        
        # --- Footer ---
        footer_layout = QHBoxLayout()
        ver_lbl = QLabel("PREMIUM v68.1.0")
        ver_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        ver_lbl.setStyleSheet("color: #475569; letter-spacing: 1px;")
        footer_layout.addWidget(ver_lbl)
        
        footer_layout.addStretch()
        
        copy_lbl = QLabel("© 2026 BULUT TEKNOLOJİ")
        copy_lbl.setFont(QFont("Segoe UI", 9))
        copy_lbl.setStyleSheet("color: #475569;")
        footer_layout.addWidget(copy_lbl)
        
        vbox.addLayout(footer_layout)

    def get_users(self):
        try:
            self.db.cursor.execute("SELECT id, username, email, role FROM users")
            return [{'id': r[0], 'username': r[1], 'email': r[2], 'role': r[3]} for r in self.db.cursor.fetchall()]
        except Exception:
            return []

    def on_user_selected(self, user_data):
        from src.ui.dialogs.password_prompt_dialog import PasswordPromptDialog
        dialog = PasswordPromptDialog(user_data['username'], user_data['username'], self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            auth = self.db.authenticate_user(user_data['username'], dialog.password_value)
            if auth:
                self.db.set_setting('last_login_user', user_data['username'])
                # remember_me is NOT set here - user selection screen will appear on every launch
                # Users can enable auto-login from Settings if desired
                self.user_selected.emit(auth)
                self.accept()
            else:
                 from src.utils.toast_notification import show_error
                 show_error(self, "Hatalı şifre!")
