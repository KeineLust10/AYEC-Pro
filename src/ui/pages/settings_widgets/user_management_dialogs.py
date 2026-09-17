# -*- coding: utf-8 -*-

"""
User Management Widget
Kullanıcı yönetimi için ayarlar sayfası widget'ı
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTableWidget, QTableWidgetItem, QDialog as QtDialog, QLabel, 
                             QLineEdit, QComboBox, QMessageBox, QHeaderView, QGroupBox,
                             QGraphicsDropShadowEffect, QFrame, QCheckBox, QScrollArea, QMenu,
                             QAbstractItemView)
from PyQt6.QtCore import Qt
from src.utils.theme_colors import theme_qss, tc, qc
from PyQt6.QtGui import QFont, QColor, QAction
from datetime import datetime
import re
import hashlib
import json
import logging
from src.ui.widgets.toast_notification import show_toast
from src.ui.widgets.animated_toggle import AnimatedToggle
from src.utils.password_security import hash_password, validate_new_password
from src.utils.role_utils import is_admin_role, normalize_role
import hashlib

logger = logging.getLogger("AYECProLogger")



class NewUserDialog(QtDialog):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(760, 720)
        self.resize(760, 720)
        self.container = QFrame()
        self.container.setObjectName("NewUserContainer")
        self.container.setStyleSheet(theme_qss("""
            QFrame#NewUserContainer {
                background: @surface;
                border-radius: 8px;
                border: 1px solid @border;
            }
            QLabel {
                font-size: 16px;
                line-height: 24px;
                font-weight: 500;
                color: @text;
            }
            QLineEdit, QComboBox {
                font-size: 16px;
                font-weight: 500;
                color: @text;
                background: @surface;
                border: 1px solid @border;
                border-radius: 8px;
                padding: 10px 12px;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: @accent;
            }
            QLineEdit[hasError="true"], QComboBox[hasError="true"] {
                border: 1px solid @danger;
            }
        """))

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.addWidget(self.container)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setStyleSheet(theme_qss("background: @surface_alt; border-top-left-radius: 8px; border-top-right-radius: 8px;"))
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 14, 20, 14)
        title = QLabel("Yeni Kullanıcı Ekle")
        title.setStyleSheet(theme_qss("font-size: 16px; line-height: 24px; font-weight: 500; color: @selection_text;"))
        header_layout.addWidget(title)
        header_layout.addStretch()
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(32, 32)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet(theme_qss("""
            QPushButton {
                background: @surface;
                border: 1px solid @border;
                border-radius: 16px;
                font-size: 16px;
                line-height: 24px;
                font-weight: 500;
                color: @text_muted;
            }
            QPushButton:hover {
                background: @danger;
                color: @selection_text;
                border-color: @danger;
            }
        """))
        btn_close.clicked.connect(self.reject)
        header_layout.addWidget(btn_close)
        layout.addWidget(header)

        # Scroll area for body (fields can be many)
        from PyQt6.QtWidgets import QScrollArea, QProgressBar
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        body = QFrame()
        body.setStyleSheet("background: transparent;")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(24, 20, 24, 20)
        body_layout.setSpacing(12)

        # --- Ad Soyad ---
        self.inp_full_name = QLineEdit()
        self.inp_full_name.setPlaceholderText("Örn: Ahmet Yılmaz")
        self.inp_full_name.setMaxLength(60)
        self.lbl_full_name_error = QLabel("")
        self.lbl_full_name_error.setStyleSheet(theme_qss("color: @danger; font-size: 12px;"))
        self.lbl_full_name_error.hide()
        body_layout.addWidget(QLabel("Ad Soyad *"))
        body_layout.addWidget(self.inp_full_name)
        body_layout.addWidget(self.lbl_full_name_error)

        # --- Kullanıcı Adı ---
        self.inp_username = QLineEdit()
        self.inp_username.setPlaceholderText("Örn: ahmet.yilmaz")
        self.inp_username.setMaxLength(40)
        self.lbl_username_error = QLabel("")
        self.lbl_username_error.setStyleSheet(theme_qss("color: @danger; font-size: 12px;"))
        self.lbl_username_error.hide()
        body_layout.addWidget(QLabel("Kullanıcı Adı *"))
        body_layout.addWidget(self.inp_username)
        body_layout.addWidget(self.lbl_username_error)

        # --- Şifre + güç barı ---
        self.inp_password = QLineEdit()
        self.inp_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.inp_password.setPlaceholderText("En az 6 karakter")
        self.lbl_password_error = QLabel("")
        self.lbl_password_error.setStyleSheet(theme_qss("color: @danger; font-size: 12px;"))
        self.lbl_password_error.hide()
        self.pwd_strength_bar = QProgressBar()
        self.pwd_strength_bar.setRange(0, 100)
        self.pwd_strength_bar.setValue(0)
        self.pwd_strength_bar.setFixedHeight(4)
        self.pwd_strength_bar.setTextVisible(False)
        self.pwd_strength_bar.setStyleSheet(theme_qss(
            "QProgressBar { background: @border; border: none; border-radius: 2px; }"
            "QProgressBar::chunk { border-radius: 2px; background: @danger; }"
        ))
        body_layout.addWidget(QLabel("Şifre *"))
        body_layout.addWidget(self.inp_password)
        body_layout.addWidget(self.pwd_strength_bar)
        body_layout.addWidget(self.lbl_password_error)

        # --- E-posta ---
        self.inp_email = QLineEdit()
        self.inp_email.setPlaceholderText("ornek@firma.com (opsiyonel)")
        self.lbl_email_error = QLabel("")
        self.lbl_email_error.setStyleSheet(theme_qss("color: @danger; font-size: 12px;"))
        self.lbl_email_error.hide()
        body_layout.addWidget(QLabel("E-posta"))
        body_layout.addWidget(self.inp_email)
        body_layout.addWidget(self.lbl_email_error)

        # --- Rol ---
        self.cmb_role = QComboBox()
        self.cmb_role.addItems(["Teknisyen", "Muhasebe", "Satış", "Yönetici", "Admin", "Diğer"])
        body_layout.addWidget(QLabel("Rol / Görev *"))
        body_layout.addWidget(self.cmb_role)

        # --- Departman ---
        self.cmb_department = QComboBox()
        self.cmb_department.addItems(["IT", "İnsan Kaynakları", "Finans", "Pazarlama", "Teknik Servis", "Genel"])
        body_layout.addWidget(QLabel("Departman"))
        body_layout.addWidget(self.cmb_department)

        # --- Telefon ---
        self.inp_phone = QLineEdit()
        self.inp_phone.setInputMask("+90 000 000 00 00;_")
        self.inp_phone.setPlaceholderText("+90 5XX XXX XX XX")
        self.lbl_phone_error = QLabel("")
        self.lbl_phone_error.setStyleSheet(theme_qss("color: @danger; font-size: 12px;"))
        self.lbl_phone_error.hide()
        body_layout.addWidget(QLabel("Telefon (Opsiyonel)"))
        body_layout.addWidget(self.inp_phone)
        body_layout.addWidget(self.lbl_phone_error)

        # --- Durum toggle ---
        status_row = QHBoxLayout()
        status_label = QLabel("Durum")
        self.toggle_active = AnimatedToggle(active_color=tc("success"))
        self.toggle_active.setChecked(True)
        status_row.addWidget(status_label)
        status_row.addStretch()
        status_row.addWidget(self.toggle_active)
        body_layout.addLayout(status_row)

        scroll.setWidget(body)
        layout.addWidget(scroll)

        footer = QFrame()
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(24, 16, 24, 20)
        footer_layout.addStretch()
        self.btn_cancel = QPushButton("Vazgeç")
        self.btn_cancel.setFixedHeight(44)
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setStyleSheet(theme_qss("""
            QPushButton {
                background: @border;
                color: @text;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                line-height: 24px;
                font-weight: 500;
                padding: 8px 18px;
            }
            QPushButton:hover { background: @border; }
        """))
        self.btn_cancel.clicked.connect(self.reject)
        footer_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Kullanıcıyı Ekle")
        self.btn_save.setFixedHeight(44)
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setStyleSheet(theme_qss("""
            QPushButton {
                background: @accent;
                color: @selection_text;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                line-height: 24px;
                font-weight: 500;
                padding: 8px 22px;
            }
            QPushButton:disabled {
                background: @selection_bg;
                color: @surface_alt;
            }
        """))
        footer_layout.addWidget(self.btn_save)
        layout.addWidget(footer)

        self.inp_full_name.textChanged.connect(self._validate_form)
        self.inp_username.textChanged.connect(self._validate_form)
        self.inp_password.textChanged.connect(self._on_password_changed)
        self.inp_email.textChanged.connect(self._validate_form)
        self.cmb_department.currentTextChanged.connect(self._validate_form)
        self.cmb_role.currentTextChanged.connect(self._validate_form)
        self.inp_phone.textChanged.connect(self._validate_form)
        self.btn_save.clicked.connect(self._save)

        self._validate_form()

    def _set_field_error(self, widget, label, message):
        if message:
            label.setText(message)
            label.show()
            widget.setProperty("hasError", True)
        else:
            label.hide()
            widget.setProperty("hasError", False)
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        return not bool(message)

    def _on_password_changed(self, text):
        """Şifre güç barını güncelle."""
        score = 0
        if len(text) >= 6: score += 25
        if len(text) >= 10: score += 15
        if any(c.isupper() for c in text): score += 20
        if any(c.isdigit() for c in text): score += 20
        if any(not c.isalnum() for c in text): score += 20
        score = min(score, 100)
        self.pwd_strength_bar.setValue(score)
        if score < 40:
            color = tc("danger")
        elif score < 70:
            color = tc("warning")
        else:
            color = tc("success")
        self.pwd_strength_bar.setStyleSheet(
            f"QProgressBar {{ background: #e2e8f0; border: none; border-radius: 2px; }}"
            f"QProgressBar::chunk {{ border-radius: 2px; background: {color}; }}"
        )
        self._validate_form()

    def _validate_form(self):
        name = (self.inp_full_name.text() or "").strip()
        username = (self.inp_username.text() or "").strip()
        password = self.inp_password.text()
        email = (self.inp_email.text() or "").strip()
        phone = (self.inp_phone.text() or "").strip()

        name_ok = self._set_field_error(
            self.inp_full_name,
            self.lbl_full_name_error,
            "Ad Soyad zorunlu." if not name else ("Maksimum 60 karakter." if len(name) > 60 else "")
        )

        username_ok = self._set_field_error(
            self.inp_username,
            self.lbl_username_error,
            "Kullanıcı adı zorunlu." if not username else
            ("En az 3 karakter olmalı." if len(username) < 3 else
             ("Boşluk kullanılamaz." if " " in username else ""))
        )

        password_ok = self._set_field_error(
            self.inp_password,
            self.lbl_password_error,
            "Şifre zorunlu." if not password else
            ("En az 6 karakter olmalı." if len(password) < 6 else "")
        )

        email_pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
        email_ok = True
        if email:
            email_ok = self._set_field_error(
                self.inp_email,
                self.lbl_email_error,
                "" if re.match(email_pattern, email) else "E-posta formatı geçersiz."
            )
        else:
            self._set_field_error(self.inp_email, self.lbl_email_error, "")

        phone_msg = ""
        digits = "".join(ch for ch in phone if ch.isdigit())
        if digits and len(digits) > 2 and len(digits) not in (12, 13):
            phone_msg = "Telefon formatı +90 XXX XXX XX XX olmalı."
        phone_ok = self._set_field_error(self.inp_phone, self.lbl_phone_error, phone_msg)

        required_ok = name_ok and username_ok and password_ok and email_ok and phone_ok
        self.btn_save.setEnabled(required_ok)
        return required_ok

    def _save(self):
        if not self._validate_form():
            return
        name = (self.inp_full_name.text() or "").strip()
        username = (self.inp_username.text() or "").strip()
        password = self.inp_password.text()
        email = (self.inp_email.text() or "").strip()
        department = self.cmb_department.currentText()
        role = normalize_role(self.cmb_role.currentText())
        phone_raw = (self.inp_phone.text() or "").replace("_", "").strip()
        phone_digits = "".join(ch for ch in phone_raw if ch.isdigit())
        phone = "" if len(phone_digits) <= 2 else phone_raw
        active = 1 if self.toggle_active.isChecked() else 0
        password_error = validate_new_password(password)
        if password_error:
            self._set_field_error(
                self.inp_password,
                self.lbl_password_error,
                password_error,
            )
            return
        password_hash = hash_password(password)

        # Kullanıcı adı veya e-posta zaten kayıtlı mı?
        try:
            self.db.cursor.execute(
                "SELECT id FROM users WHERE username=?", (username,)
            )
            if self.db.cursor.fetchone():
                self._set_field_error(self.inp_username, self.lbl_username_error,
                                      "Bu kullanıcı adı zaten kullanılıyor.")
                self.btn_save.setEnabled(False)
                return
            if email:
                self.db.cursor.execute(
                    "SELECT id FROM users WHERE email=?", (email,)
                )
                if self.db.cursor.fetchone():
                    self._set_field_error(self.inp_email, self.lbl_email_error,
                                          "Bu e-posta zaten kayıtlı.")
                    self.btn_save.setEnabled(False)
                    return
        except Exception:
            pass

        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        personnel_id = None
        try:
            pcols = set(self.db._get_table_columns("personnel")) if hasattr(self.db, "_get_table_columns") else set()
            pdata = {
                "name": name,
                "role": role,
                "phone": phone,
                "email": email,
                "department": department,
                "active": active,
                "created_at": created_at,
            }
            pcols_used = [k for k in pdata if k in pcols]
            if pcols_used:
                ph = ", ".join(["?"] * len(pcols_used))
                self.db.cursor.execute(
                    f"INSERT INTO personnel ({', '.join(pcols_used)}) VALUES ({ph})",
                    tuple(pdata[k] for k in pcols_used),
                )
                personnel_id = self.db.cursor.lastrowid
        except Exception:
            personnel_id = None

        try:
            ucols = set(self.db._get_table_columns("users")) if hasattr(self.db, "_get_table_columns") else set()
            udata = {
                "username": username,
                "password": password_hash,
                "email": email or None,
                "role": role,
                "created_at": created_at,
                "full_name": name,
                "name": name,
                "personnel_id": personnel_id,
                "active": active,
            }
            ucols_used = [k for k in udata if k in ucols]
            if "is_active" in ucols:
                udata["is_active"] = active
                if "is_active" not in ucols_used:
                    ucols_used.append("is_active")
            if "permissions" in ucols:
                udata["permissions"] = json.dumps({"mode": "all"}) if is_admin_role(role) \
                    else json.dumps({"pages": []})
                if "permissions" not in ucols_used:
                    ucols_used.append("permissions")
            if "interface_edit_access" in ucols:
                udata["interface_edit_access"] = 1 if is_admin_role(role) or role == "Master" else 0
                if "interface_edit_access" not in ucols_used:
                    ucols_used.append("interface_edit_access")
            if ucols_used:
                ph = ", ".join(["?"] * len(ucols_used))
                self.db.cursor.execute(
                    f"INSERT INTO users ({', '.join(ucols_used)}) VALUES ({ph})",
                    tuple(udata[k] for k in ucols_used),
                )
            self.db.conn.commit()
            show_toast(self, f"'{name}' kullanıcısı başarıyla eklendi", "success", 3000)
            self.accept()
        except Exception as e:
            self.db.conn.rollback()
            show_toast(self, f"Hata: {e}", "error", 4000)

class UserDialog(QtDialog):
    def __init__(self, db, user_id=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.user_id = user_id
        
        # Frameless window setup
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(1120, 780)
        
        # Main container
        self.container = QWidget()
        self.container.setMinimumWidth(980)
        self.container.setStyleSheet(theme_qss("""
            QWidget {
                background: @surface;
                border-radius: 16px;
                border: 1px solid @border;
            }
            QLabel {
                color: @text;
                font-weight: 600;
                font-size: 14px;
                background: transparent;
            }
            QLineEdit, QComboBox {
                background: @surface_alt;
                border: 2px solid @border;
                border-radius: 12px;
                padding: 12px 14px;
                font-size: 14px;
                color: @text;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: @accent;
                background: @surface;
            }
        """))
        
        # Shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 5)
        self.container.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout(self)
        layout.addWidget(self.container)
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.init_ui()
        
        if user_id:
            self.load_user_data()
        else:
            self.apply_role_defaults(self.cmb_role.currentText())

    def init_ui(self):
        # Main Layout for Container
        main_layout = QVBoxLayout(self.container)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(10)
        
        # --- HEADER ---
        header_row = QHBoxLayout()
        title = QLabel("✏️ Kullanıcı Düzenle" if self.user_id else "➕ Yeni Kullanıcı")
        title.setStyleSheet(theme_qss("font-size: 22px; font-weight: bold; color: @text; border: none;"))
        header_row.addWidget(title)
        header_row.addStretch()
        
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(36, 36)
        btn_close.setStyleSheet(theme_qss("""
            QPushButton { background: @surface_alt; color: @text_muted; border-radius: 18px; font-size: 18px; font-weight: bold; border: none; }
            QPushButton:hover { background: @danger; color: @selection_text; }
        """))
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.reject)
        header_row.addWidget(btn_close)
        main_layout.addLayout(header_row)
        
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(theme_qss("background: @border; max-height: 1px;"))
        main_layout.addWidget(separator)
        
        # --- CONTENT AREA (2 Columns) ---
        content_layout = QHBoxLayout()
        content_layout.setSpacing(30)
        
        # LEFT COLUMN (User Details)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)
        
        left_layout.addWidget(QLabel("Kullanıcı Adı:"))
        self.txt_username = QLineEdit()
        self.txt_username.setPlaceholderText("örn: ahmet")
        left_layout.addWidget(self.txt_username)
        
        left_layout.addWidget(QLabel("Şifre:"))
        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_password.setPlaceholderText("Minimum 6 karakter")
        left_layout.addWidget(self.txt_password)
        
        left_layout.addWidget(QLabel("E-posta (Opsiyonel):"))
        self.txt_email = QLineEdit()
        self.txt_email.setPlaceholderText("örn: ahmet@firma.com")
        left_layout.addWidget(self.txt_email)

        left_layout.addWidget(QLabel("Gizli Soru:"))
        self.txt_secret_question = QLineEdit()
        self.txt_secret_question.setPlaceholderText("örn: İlk okul öğretmeninizin adı")
        left_layout.addWidget(self.txt_secret_question)

        left_layout.addWidget(QLabel("Gizli Yanıt:"))
        self.txt_secret_answer = QLineEdit()
        self.txt_secret_answer.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_secret_answer.setPlaceholderText("Yanıt (görünmez)")
        left_layout.addWidget(self.txt_secret_answer)
        
        left_layout.addWidget(QLabel("Rol:"))
        self.cmb_role = QComboBox()
        self.cmb_role.addItems(["Master", "Admin", "Teknisyen", "Muhasebe", "Personel"])
        self.cmb_role.setMaxVisibleItems(4)
        self.cmb_role.currentTextChanged.connect(self.apply_role_defaults)
        left_layout.addWidget(self.cmb_role)
        
        left_layout.addWidget(QLabel("Personel:"))
        self.cmb_personnel = QComboBox()
        self.load_personnel()
        left_layout.addWidget(self.cmb_personnel)
        
        # --- AUTO LOGIN TOGGLE ---
        left_layout.addSpacing(10)
        auto_login_layout = QHBoxLayout()
        auto_login_label = QLabel("Otomatik Giriş İzni:")
        auto_login_label.setStyleSheet(theme_qss("font-weight: bold; color: @text;"))
        self.toggle_auto_login = AnimatedToggle(
            active_color=tc("success")
        )
        auto_login_layout.addWidget(auto_login_label)
        auto_login_layout.addWidget(self.toggle_auto_login)
        auto_login_layout.addStretch()
        left_layout.addLayout(auto_login_layout)
        
        left_layout.addStretch() # Push everything up
        
        # RIGHT COLUMN (Permissions)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)
        
        label_perm = QLabel("Menü Yetkileri:")
        label_perm.setStyleSheet(theme_qss("font-size: 15px; font-weight: bold; color: @text; margin-bottom: 5px;"))
        right_layout.addWidget(label_perm)
        
        perm_scroll = QScrollArea()
        perm_scroll.setWidgetResizable(True)
        perm_scroll.setStyleSheet(theme_qss("""
            QScrollArea { border: none; background: transparent; }
            QWidget { background: transparent; }
        """))
        
        perm_container = QWidget()
        perm_container.setStyleSheet(theme_qss("""
            QWidget {
                background: @surface_alt;
                border: 1px solid @border;
                border-radius: 12px;
            }
            QLabel#PermSectionTitle {
                font-size: 13px;
                font-weight: 900;
                color: @selection_text;
                padding: 8px 10px;
                border: none;
            }
            QLabel#PermItemLabel {
                font-size: 13px;
                font-weight: 700;
                color: @text;
                border: none;
            }
        """))
        perm_items_layout = QVBoxLayout(perm_container)
        perm_items_layout.setContentsMargins(14, 14, 14, 14)
        perm_items_layout.setSpacing(12)

        self.menu_structure = [
            ("GENEL", [(40, "Genel Bakış")]),
            ("SERVİS OPERASYON", [
                (41, "Durum Paneli"),
                (62, "Teknisyen Paneli"),
                (61, "Saha Haritası"),
                (30, "Randevular"),
                (65, "Lojistik & Garanti Yönetimi"),
                (201, "İş/Servis Takibi Raporları"),
                (170, "AI Asistan"),
            ]),
            ("MÜŞTERİ", [
                (21, "Müşteri Listesi"),
                (26, "Çalışma Ortakları"),
                (25, "Sözleşmeler"),
                (90, "Hatırlatıcılar"),
                (120, "Duyurular"),
            ]),
            ("TİCARİ", [
                (200, "Proje Yönetimi"),
                (202, "Proje Arşivi"),
                (50, "Stok Y\u00f6netimi"),
                (60, "Ara\u00e7 Par\u00e7a Sto\u011fu"),
                (150, "Sales Hub"),
                (140, "Hizmet Tanımları"),
                (146, "\u00dcr\u00fcn Grubu Y\u00f6netimi"),
                (147, "Rapor C\u00fcmle Kal\u0131plar\u0131"),
                (145, "Cihaz Bilgisi & Markalar"),
                (66, "Emanet (Konsinye) Cihazlar"),
                (250, "Mobil Stok"),
                (300, "PC Builder"),
            ]),
            ("FİNANS", [
                (101, "Gelir / Gider"),
                (105, "Banka Hesapları"),
                (106, "Çek / Senet"),
                (115, "E-Fatura"),
            ]),
            ("PERSONEL", [
                (10, "Personel"),
            ]),
            ("SİSTEM", [
                (160, "Bilgi Bankası"),
                (130, "Ayarlar"),
                (135, "Log Kayıtları"),
                (180, "Yedekleme"),
                (261, "Kullanım Kılavuzu"),
                (70, "Destek"),
            ]),
        ]

        self.perm_toggles = {}
        for section, items in self.menu_structure:
            sec_lbl = QLabel(section)
            sec_lbl.setObjectName("PermSectionTitle")
            perm_items_layout.addWidget(sec_lbl)

            for page_id, title in items:
                row = QWidget()
                rl = QHBoxLayout(row)
                rl.setContentsMargins(8, 0, 8, 0)
                rl.setSpacing(10)

                lbl = QLabel(title)
                lbl.setObjectName("PermItemLabel")

                tgl = AnimatedToggle(active_color=tc("accent"))
                tgl.setFixedSize(44, 22)
                tgl.setChecked(True)

                rl.addWidget(lbl)
                rl.addStretch()
                rl.addWidget(tgl)
                perm_items_layout.addWidget(row)
                self.perm_toggles[int(page_id)] = tgl
            
        perm_scroll.setWidget(perm_container)
        right_layout.addWidget(perm_scroll)
        
        # Add columns to content layout
        content_layout.addWidget(left_widget, 1) # 50% width
        content_layout.addWidget(right_widget, 1) # 50% width
        
        main_layout.addLayout(content_layout)
        
        main_layout.addSpacing(10)
        
        # --- BUTTONS ---
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        self.btn_save = QPushButton("\U0001f4be KAYDET")
        self.btn_save.setObjectName("saveUserButton")
        self.btn_save.setFixedHeight(50)
        self.btn_save.clicked.connect(self.save_user)
        self.btn_save.setStyleSheet(theme_qss("""
            QPushButton { background: @success; color: @selection_text; border: none; border-radius: 12px; font-weight: bold; font-size: 15px; }
            QPushButton:hover { background: @success; }
        """))
        btn_layout.addWidget(self.btn_save)
        
        self.btn_cancel = QPushButton("\u274c \u0130PTAL")
        self.btn_cancel.setObjectName("cancelUserButton")
        self.btn_cancel.setFixedHeight(50)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_cancel.setStyleSheet(theme_qss("""
            QPushButton { background: @text_muted; color: @selection_text; border: none; border-radius: 12px; font-weight: bold; font-size: 15px; }
            QPushButton:hover { background: @text_muted; }
        """))
        btn_layout.addWidget(self.btn_cancel)
        
        main_layout.addLayout(btn_layout)
        # self.setLayout(layout) - Removed because layout belongs to container

    def apply_role_defaults(self, role):
        all_pages = set(self.perm_toggles.keys()) if hasattr(self, "perm_toggles") else set()
        normalized_role = normalize_role(role)
        if is_admin_role(normalized_role):
            allowed = all_pages
        elif normalized_role == "Teknisyen":
            allowed = {40, 41, 60, 61, 30, 150, 21, 50, 70}
        elif normalized_role == "Muhasebe":
            allowed = {40, 21, 101, 135, 130}
        else:
            allowed = {40, 41, 21, 50}

        for pid, tgl in getattr(self, "perm_toggles", {}).items():
            tgl.blockSignals(True)
            tgl.setChecked(pid in allowed)
            tgl.blockSignals(False)
            tgl.setEnabled(not is_admin_role(normalized_role))

    def _apply_saved_permissions(self, raw_permissions):
        if not raw_permissions:
            return False
        try:
            saved = json.loads(raw_permissions)
            if isinstance(saved, dict) and saved.get("mode") == "all":
                allowed = set(self.perm_toggles.keys())
            elif isinstance(saved, dict) and isinstance(saved.get("pages"), list):
                allowed = {int(value) for value in saved.get("pages", [])}
            elif isinstance(saved, list):
                allowed = {int(value) for value in saved}
            elif isinstance(saved, dict):
                legacy_map = {
                    "dashboard": {40},
                    "customers": {21, 25, 90, 120},
                    "services": {41, 60, 61, 30},
                    "stock": {50, 140, 146, 147},
                    "financial": {101},
                    "backup": {180},
                    "settings": {130},
                    "logs": {135},
                }
                allowed = set()
                for key, enabled in saved.items():
                    if enabled and key in legacy_map:
                        allowed |= legacy_map[key]
            else:
                return False

            for page_id, toggle in self.perm_toggles.items():
                toggle.blockSignals(True)
                toggle.setChecked(page_id in allowed)
                toggle.setEnabled(True)
                toggle.blockSignals(False)
            return True
        except Exception as exc:
            logger.error("User dialog permissions load error: %s", exc)
            return False

    
    def load_personnel(self):
        """Load personnel list"""
        self.cmb_personnel.clear()
        self.cmb_personnel.addItem("Atanmadı", None)
        
        try:
            self.db.cursor.execute("SELECT id, name FROM personnel ORDER BY name")
            personnel = self.db.cursor.fetchall()
            
            for p in personnel:
                self.cmb_personnel.addItem(p[1], p[0])
        except Exception as e:
            logger.error("User dialog personnel load error: %s", e)
    
    def load_user_data(self):
        """Load existing user data"""
        try:
            self.db.cursor.execute("""
                SELECT username, email, role, personnel_id, permissions, auto_login, secret_question
                FROM users WHERE id=?
            """, (self.user_id,))
            user = self.db.cursor.fetchone()
            
            if user:
                self.txt_username.setText(user[0] or "")
                self.txt_email.setText(user[1] or "")
                
                # Set role
                role_index = self.cmb_role.findText(normalize_role(user[2] or "Personel"))
                if role_index >= 0:
                    self.cmb_role.blockSignals(True)
                    self.cmb_role.setCurrentIndex(role_index)
                    self.cmb_role.blockSignals(False)
                
                # Set personnel
                if user[3]:
                    personnel_index = self.cmb_personnel.findData(user[3])
                    if personnel_index >= 0:
                        self.cmb_personnel.setCurrentIndex(personnel_index)
                
                # Set auto login
                self.toggle_auto_login.setChecked(bool(user[5]))

                self.txt_secret_question.setText(user[6] or "")
                self.txt_secret_answer.setPlaceholderText("Değiştirmek için yeni yanıt girin")
                        
                permissions_loaded = self._apply_saved_permissions(user[4] if len(user) > 4 else None)
                if is_admin_role(self.cmb_role.currentText()):
                    self.apply_role_defaults(self.cmb_role.currentText())
                elif not permissions_loaded:
                    self.apply_role_defaults(self.cmb_role.currentText())
                
                # Password not shown for security
                self.txt_password.setPlaceholderText("Değiştirmek için yeni şifre girin")
        except Exception as e:
            show_toast(self, f"Kullanıcı bilgileri yüklenemedi: {e}", "error")
    
    def save_user(self):
        """Save user"""
        username = (self.txt_username.text() or "").strip()
        password = self.txt_password.text().strip()
        email = self.txt_email.text().strip()
        role = normalize_role(self.cmb_role.currentText())
        personnel_id = self.cmb_personnel.currentData()
        auto_login = 1 if self.toggle_auto_login.isChecked() else 0
        secret_question = self.txt_secret_question.text().strip()
        secret_answer = self.txt_secret_answer.text().strip()
        
        # Get permissions
        if is_admin_role(role):
            permissions_json = json.dumps({"mode": "all"})
        else:
            allowed_pages = [pid for pid, tgl in self.perm_toggles.items() if tgl.isChecked()]
            permissions_json = json.dumps({"pages": allowed_pages})
        
        lowered = username.lower()
        if lowered in ("admin", "master"):
            if not self.user_id:
                show_toast(self, "Admin ve Master kullanıcı adları güvenlik nedeniyle kullanılamaz!", "warning")
                return
            try:
                self.db.cursor.execute("SELECT username FROM users WHERE id=?", (self.user_id,))
                row = self.db.cursor.fetchone()
                existing_username = (row[0] if row else "") or ""
            except Exception:
                existing_username = ""
            if existing_username.lower() != lowered:
                show_toast(self, "Admin ve Master kullanıcı adları güvenlik nedeniyle kullanılamaz!", "warning")
                return

        if not username:
            show_toast(self, "Kullanıcı adı gereklidir!", "warning")
            return
        
        if not self.user_id and not password:
            show_toast(self, "Şifre gereklidir!", "warning")
            return
        
        if password and len(password) < 6:
            show_toast(self, "Şifre en az 6 karakter olmalıdır!", "warning")
            return

        if password:
            password_error = validate_new_password(password)
            if password_error:
                show_toast(self, password_error, "warning")
                return

        if secret_question or secret_answer:
            if not secret_question or not secret_answer:
                show_toast(self, "Gizli soru ve yanıt birlikte girilmelidir!", "warning")
                return

        # Check for duplicate username
        try:
            if self.user_id:
                self.db.cursor.execute("SELECT id FROM users WHERE username=? AND id<>?", (username, self.user_id))
            else:
                self.db.cursor.execute("SELECT id FROM users WHERE username=?", (username,))
            if self.db.cursor.fetchone():
                show_toast(self, "Bu kullanıcı adı zaten başka bir kullanıcı tarafından kullanılıyor!", "warning")
                return
        except Exception:
            pass

        # Check for duplicate email
        if email:
            try:
                if self.user_id:
                    self.db.cursor.execute("SELECT id FROM users WHERE email=? AND id<>?", (email, self.user_id))
                else:
                    self.db.cursor.execute("SELECT id FROM users WHERE email=?", (email,))
                if self.db.cursor.fetchone():
                    show_toast(self, "Bu e-posta adresi zaten başka bir kullanıcı tarafından kullanılıyor!", "warning")
                    return
            except Exception:
                pass

        secret_payload = None
        if secret_question and secret_answer:
            secret_hash = hashlib.sha256(secret_answer.lower().encode()).hexdigest()
            secret_payload = (secret_question, secret_hash)
        
        try:
            if self.user_id:
                fields = ["username=?", "email=?", "role=?", "personnel_id=?", "permissions=?", "auto_login=?"]
                values = [username, email, role, personnel_id, permissions_json, auto_login]

                if password:
                    hashed_pw = hash_password(password)
                    fields.insert(1, "password=?")
                    values.insert(1, hashed_pw)

                if secret_payload:
                    fields.extend(["secret_question=?", "secret_answer_hash=?"])
                    values.extend(secret_payload)

                sql = "UPDATE users SET {assignments} WHERE id=?".format(
                    assignments=", ".join(fields)
                )
                values.append(self.user_id)
                self.db.cursor.execute(sql, tuple(values))
            else:
                from datetime import datetime
                hashed_pw = hash_password(password)
                created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                columns = ["username", "password", "email", "role", "personnel_id", "permissions", "auto_login", "created_at"]
                values = [username, hashed_pw, email, role, personnel_id, permissions_json, auto_login, created_at]

                if secret_payload:
                    columns.extend(["secret_question", "secret_answer_hash"])
                    values.extend(secret_payload)

                placeholders = ", ".join(["?"] * len(columns))
                self.db.cursor.execute(
                    f"INSERT INTO users ({', '.join(columns)}) VALUES ({placeholders})",
                    tuple(values)
                )
            
            self.db.conn.commit()
            show_toast(self, "Kullanıcı başarıyla kaydedildi!", "success")
            self.accept()
            
        except Exception as e:
            show_toast(self, f"Kullanıcı kaydedilemedi: {e}", "error")
