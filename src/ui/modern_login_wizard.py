# -*- coding: utf-8 -*-

"""Dialogs extracted from modern_login_window for modularity."""

from PyQt6.QtWidgets import (QDialog, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
                             QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QStackedWidget,
                             QCheckBox, QApplication, QScrollArea, QProgressBar,
                             QFormLayout, QTextEdit, QInputDialog, QTableWidget, QTableWidgetItem,
                             QHeaderView, QWizard, QWizardPage, QButtonGroup, QComboBox, QRadioButton)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QPoint, QSize, QThread, QUrl, QTimer
from PyQt6.QtGui import QFont, QColor, QPainter, QLinearGradient, QBrush, QPainterPath, QPixmap, QAction, QDesktopServices, QKeySequence, QShortcut

from src.utils.theme_colors import theme_qss, qc, tc
from src.utils.toast_notification import show_success, show_error, show_warning, show_info
from src.utils.auth_manager import AuthManager
from src.utils.security_manager import SecurityManager
from src.utils.logger import logger
from src.ui.dialogs.license_keygen_dialog import LicenseKeygenDialog
from src.utils.design_system import DesignTokens
import sys
import shutil
from datetime import datetime
import os
import ctypes


class AccountWizard(QWizard):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        
        self.setWindowTitle("Hesap Oluşturma Sihirbazı")
        self.setFixedSize(700, 550)
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        
        # Styling
        self.setStyleSheet(theme_qss("""
            QWizard { background-color: white; }
            QLabel { color: @text; font-family: 'Segoe UI'; }
            QLineEdit, QComboBox { 
                padding: 10px; border: 1px solid @border; border-radius: 8px; font-size: 14px; color: @text;
            }
            QLineEdit:focus { border: 2px solid @accent; }
            QPushButton {
                background-color: @accent; color: white; border-radius: 6px; padding: 8px 16px; font-weight: bold;
            }
            QPushButton:hover { background-color: @accent_hover; }
        """))
        
        # Add Pages
        self.addPage(PageAccountType(self))
        self.addPage(PageIndustry(self))
        self.addPage(PageIdentity(self))
        self.addPage(PageSecurity(self))
        self.addPage(Pagecustomization(self))
        
    def accept(self):
        # Gather data and create user
        try:
            # We access fields from pages
            p_type = self.field("account_type")
            p_industry = self.field("industry")
            
            fullname = self.field("fullname")
            email = self.field("email")
            
            username = self.field("username")
            password = self.field("password")
            
            # Simple permission presets based on type
            role = "Personel"
            if p_type == "Yönetici": role = "Admin"
            
            # Create user via AuthManager (assuming parent has it, or we create one temp)
            from src.utils.auth_manager import AuthManager
            auth = AuthManager(self.db)
            
            success, msg = auth.register_user(username, password, email)
            if success:
                # Update extended details if needed (e.g. role, industry in a profile table)
                # For now, we update the role directly if columns exist
                try:
                    self.db.cursor.execute("UPDATE users SET role=? WHERE username=?", (role, username))
                    self.db.conn.commit()
                except Exception as role_err:
                    logger.warning(f"AccountWizard role update failed for {username}: {role_err}")
                
                super().accept()
            else:
                show_error(self, f"Kayıt hatası: {msg}")
                # Don't close wizard if error
        except Exception as e:
            show_error(self, f"Hata: {str(e)}")

class SidebarWizardPage(QWizardPage):
    """Base page with consistent header/layout"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(40, 20, 40, 20)
        self.layout.setSpacing(20)

        # Header
        h_layout = QHBoxLayout()
        logo = QLabel("AYEC")
        logo.setFixedSize(50, 50)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet(theme_qss("background: @text; color: white; border-radius: 25px; font-weight: bold;"))
        h_layout.addWidget(logo)
        
        self.lbl_title = QLabel()
        self.lbl_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        h_layout.addWidget(self.lbl_title)
        h_layout.addStretch()
        
        self.layout.addLayout(h_layout)
        self.layout.addSpacing(10)
        
        self.content_area = QWidget()
        self.layout.addWidget(self.content_area)
        self.layout.addStretch()

class PageAccountType(SidebarWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Hesap Türü")
        self.lbl_title.setText("Hesap Türü Seçin")
        
        vbox = QVBoxLayout(self.content_area)
        
        self.bg = QButtonGroup(self)
        self.hidden_result = QLineEdit()
        self.hidden_result.setVisible(False)
        vbox.addWidget(self.hidden_result)
        
        options = [
            ("Yönetici", "Tam yetkili sistem yöneticisi"),
            ("Teknik Personel", "Servis ve onarım işlemleri"),
            ("Saha Elemanı", "Dış görev ve müşteri ziyaretleri")
        ]
        
        for i, (name, desc) in enumerate(options):
            rb = QRadioButton(f"{name}\n{desc}")
            rb.setStyleSheet(theme_qss("""
                QRadioButton {
                    background: @surface_alt; border: 1px solid @surface_alt; border-radius: 8px; padding: 15px; font-size: 15px; font-weight: bold;
                }
                QRadioButton::indicator { width: 20px; height: 20px; }
                QRadioButton:checked { background: @selection_bg; border: 1px solid @accent; }
            """))
            vbox.addWidget(rb)
            self.bg.addButton(rb, i)
        
        self.bg.buttonClicked.connect(self.update_field)
        self.bg.buttons()[1].setChecked(True)
        self.update_field()
        
        self.registerField("account_type", self.hidden_result)

    def update_field(self):
        btn = self.bg.checkedButton()
        if btn:
            self.hidden_result.setText(btn.text().split("\n")[0])

class PageIndustry(SidebarWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Sektör / Amaç")
        self.lbl_title.setText("Kullanım Amacı")
        
        vbox = QVBoxLayout(self.content_area)
        
        options = ["Teknik Servis / Tamir", "Tekstil / Üretim Takip", "İnşaat / Şantiye Yönetimi", "Diğer"]
        self.combo = QComboBox()
        self.combo.addItems(options)
        self.combo.setStyleSheet(theme_qss("padding: 10px; font-size: 14px;"))
        
        vbox.addWidget(QLabel("İşletmenizin ana faaliyet alanı nedir?"))
        vbox.addWidget(self.combo)
        
        self.registerField("industry", self.combo)

class PageIdentity(SidebarWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Kimlik Bilgileri")
        self.lbl_title.setText("Kişisel Bilgiler")
        
        form = QFormLayout(self.content_area)
        form.setSpacing(15)
        
        self.inp_fullname = QLineEdit()
        self.inp_email = QLineEdit()
        self.inp_phone = QLineEdit()
        
        form.addRow("Ad Soyad:", self.inp_fullname)
        form.addRow("E-posta:", self.inp_email)
        form.addRow("Telefon:", self.inp_phone)
        
        self.registerField("fullname*", self.inp_fullname) # * = mandatory
        self.registerField("email", self.inp_email)

class PageSecurity(SidebarWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Güvenlik")
        self.lbl_title.setText("Giriş Bilgileri")
        
        form = QFormLayout(self.content_area)
        form.setSpacing(15)
        
        self.inp_user = QLineEdit()
        self.inp_pass = QLineEdit()
        self.inp_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.inp_pass2 = QLineEdit()
        self.inp_pass2.setEchoMode(QLineEdit.EchoMode.Password)
        
        form.addRow("Kullanıcı Adı:", self.inp_user)
        form.addRow("Şifre:", self.inp_pass)
        form.addRow("Şifre (Tekrar):", self.inp_pass2)
        
        self.registerField("username*", self.inp_user)
        self.registerField("password*", self.inp_pass)

class Pagecustomization(SidebarWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Tamamla")
        self.lbl_title.setText("Son Ayarlar")
        
        vbox = QVBoxLayout(self.content_area)
        
        vbox.addWidget(QLabel("Para Birimi:"))
        combo_curr = QComboBox()
        combo_curr.addItems(["TRY (Türk Lirası)", "USD (Amerikan Doları)", "EUR (Euro)"])
        vbox.addWidget(combo_curr)
        
        vbox.addSpacing(20)
        
        chk_terms = QCheckBox("Kullanım koşullarını okudum ve kabul ediyorum.")
        vbox.addWidget(chk_terms)
        
        # This page is the last one

    def _wire_ui_signals(self):
        self.combo.currentIndexChanged.connect(self._on_ui_widget_changed)
