# -*- coding: utf-8 -*-

"""Dialogs extracted from modern_login_window for modularity."""

from PyQt6.QtWidgets import (QDialog as QtDialog, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
                             QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QStackedWidget,
                             QCheckBox, QApplication, QScrollArea, QProgressBar,
                             QFormLayout, QTextEdit, QInputDialog, QTableWidget, QTableWidgetItem,
                             QHeaderView)
QDialog = QtDialog
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QPoint, QSize, QThread, QUrl, QTimer
from PyQt6.QtGui import QFont, QColor, QPainter, QLinearGradient, QBrush, QPainterPath, QPixmap, QAction, QDesktopServices, QKeySequence, QShortcut

from src.utils.theme_colors import theme_qss, qc, tc
from src.utils.toast_notification import show_success, show_error, show_warning, show_info
from src.utils.auth_manager import AuthManager
from src.utils.role_utils import is_admin_role, normalize_role
from src.utils.security_manager import SecurityManager
from src.utils.password_security import verify_password
from src.ui.dialogs.license_keygen_dialog import LicenseKeygenDialog
from src.ui.modern_login_deleted_records import DeletedRecordsDialog
from src.utils.design_system import DesignTokens
import sys
import shutil
from datetime import datetime
import os
import ctypes
from src.utils.logger import logger


class ModernPasswordDialog(QtDialog):
    def __init__(self, parent=None, username=""):
        super().__init__(parent)
        self.username = username
        self.password = None
        self.remember_me = False
        
        # Setup Window
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(400, 320)
        
        # Main Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Background Container
        self.container = QFrame()
        self.container.setStyleSheet(theme_qss("""
            QFrame {
                background-color: @surface;
                border-radius: 20px;
                border: 1px solid @border;
            }
        """))
        # Add shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 10)
        self.container.setGraphicsEffect(shadow)
        
        layout.addWidget(self.container)
        
        # Content Layout
        content_layout = QVBoxLayout(self.container)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(20)
        
        # User Icon/Avatar
        initials = username[:2].upper() if len(username) >= 2 else username.upper()
        lbl_avatar = QLabel(initials)
        lbl_avatar.setFixedSize(80, 80)
        lbl_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_avatar.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        # Consistent colorful background based on name
        colors = [tc("accent"), tc("accent"), tc("accent"), tc("warning"), tc("success"), tc("danger")]
        color_idx = sum(ord(c) for c in username) % len(colors)
        bg_color = colors[color_idx]
        
        lbl_avatar.setStyleSheet(theme_qss(f"""
            background-color: {bg_color};
            color: white;
            border-radius: 40px;
        """))
        
        content_layout.addWidget(lbl_avatar, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Welcome Text
        lbl_welcome = QLabel(f"Tekrar Hoşgeldin, {username}")
        lbl_welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_welcome.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl_welcome.setStyleSheet(theme_qss("color: @text; border: none;"))
        content_layout.addWidget(lbl_welcome)
        
        # Password Input
        self.txt_password = QLineEdit()
        self.txt_password.setPlaceholderText("Şifrenizi girin...")
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_password.setFixedHeight(45)
        self.txt_password.setFont(QFont("Segoe UI", 11))
        self.txt_password.setStyleSheet(theme_qss("""
            QLineEdit {
                background: @surface_alt;
                border: 2px solid @border;
                border-radius: 12px;
                padding: 0 15px;
                color: @text;
            }
            QLineEdit:focus {
                background: @surface;
                border: 2px solid @accent;
            }
        """))
        self.txt_password.returnPressed.connect(self.accept_login)
        content_layout.addWidget(self.txt_password)

        options_row = QHBoxLayout()
        options_row.setContentsMargins(2, 0, 2, 0)
        options_row.setSpacing(8)

        self.chk_remember = QCheckBox("Beni Hatırla")
        self.chk_remember.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_remember.setStyleSheet(theme_qss("""
            QCheckBox {
                color: @text_muted;
                font-weight: 600;
                background: transparent;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 6px;
                border: 1px solid @border;
                background: @surface_alt;
            }
            QCheckBox::indicator:checked {
                background: @accent;
                border: 1px solid @accent;
            }
        """))
        self.chk_remember.stateChanged.connect(self._sync_remember)
        options_row.addWidget(self.chk_remember)
        options_row.addStretch()

        btn_forgot = QPushButton("Şifremi Unuttum")
        btn_forgot.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_forgot.setStyleSheet(theme_qss("""
            QPushButton {
                border: none;
                color: @accent_hover;
                font-weight: 600;
                background: transparent;
            }
            QPushButton:hover { color: @accent_pressed; }
        """))
        btn_forgot.clicked.connect(self.open_password_reset)
        options_row.addWidget(btn_forgot)
        content_layout.addLayout(options_row)
        
        # Buttons Layout
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        # Cancel Button
        btn_cancel = QPushButton("\u0130ptal")
        btn_cancel.setAutoDefault(False)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setFixedHeight(40)
        btn_cancel.setStyleSheet(theme_qss("""
            QPushButton {
                background: white;
                border: 1px solid @border;
                border-radius: 12px;
                color: @text_muted;
                font-weight: 600;
            }
            QPushButton:hover {
                background: @surface_alt;
                color: @text;
            }
        """))
        btn_cancel.clicked.connect(self.reject)
        
        # Login Button
        btn_login = QPushButton("Giri\u015f Yap")
        btn_login.setAutoDefault(False)
        btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_login.setFixedHeight(40)
        btn_login.setStyleSheet(theme_qss("""
            QPushButton {
                background: @success;
                border: none;
                border-radius: 12px;
                color: white;
                font-weight: 600;
            }
            QPushButton:hover {
                background: @success;
            }
        """))
        btn_login.clicked.connect(self.accept_login)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_login)
        
        content_layout.addLayout(btn_layout)
        
    def _sync_remember(self, _state=None):
        self.remember_me = self.chk_remember.isChecked()

    def accept_login(self):
        if getattr(self, "_accepted_fired", False):
            return
        self._accepted_fired = True
        self.password = self.txt_password.text()
        self._sync_remember()
        self.accept()

    def open_password_reset(self):
        parent = self.parent()
        db = getattr(parent, "db", None)
        if not db:
            return
        from src.ui.dialogs.password_reset_dialog import PasswordResetDialog
        dialog = PasswordResetDialog(db, self)
        dialog.exec()

class TechnicalServiceAuthDialog(QtDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.user = None
        self.setWindowTitle("Teknik Servis Modu - Doğrulama")
        self.setFixedSize(420, 260)
        
        self.setStyleSheet(theme_qss("""
            QDialog {
                background-color: @surface;
            }
            QLabel {
                color: @text;
                font-weight: 600;
            }
            QLineEdit {
                background-color: @surface_alt;
                color: @text;
                border: 1px solid @border;
                border-radius: 8px;
                padding: 6px 10px;
            }
            QLineEdit:focus {
                border-color: @accent;
            }
        """))
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Teknik Servis Modu")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("color: @text;"))
        layout.addWidget(title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setFormAlignment(Qt.AlignmentFlag.AlignLeft)

        self.inp_user = QLineEdit()
        self.inp_user.setPlaceholderText("Kullanıcı adı")
        self.inp_user.setFixedHeight(36)

        self.inp_pass = QLineEdit()
        self.inp_pass.setPlaceholderText("Şifre")
        self.inp_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.inp_pass.setFixedHeight(36)
        self.inp_pass.returnPressed.connect(self.handle_login)

        form.addRow("Kullanıcı Adı", self.inp_user)
        form.addRow("Şifre", self.inp_pass)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        btn_cancel = QPushButton("İptal")
        btn_cancel.setFixedHeight(34)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @surface_alt;
                color: @text;
                border: 1px solid @border;
                border-radius: 8px;
                padding: 0 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: @border;
            }
        """))
        btn_cancel.clicked.connect(self.reject)
        
        btn_ok = QPushButton("Giriş")
        btn_ok.setFixedHeight(34)
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @accent;
                color: @selection_text;
                border: none;
                border-radius: 8px;
                padding: 0 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: @accent_hover;
            }
        """))
        btn_ok.clicked.connect(self.handle_login)
        
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

    def handle_login(self):
        username = (self.inp_user.text() or "").strip()
        password = self.inp_pass.text()
        if not username or not password:
            show_warning(self, "Lütfen kullanıcı adı ve şifre girin.")
            return
        auth = AuthManager(self.db)
        ok, msg = auth.login(username, password, remember=False)
        if not ok:
            show_error(self, msg)
            return
        user = auth.current_user or {}
        role = str(user.get("role", "")).strip()
        if not is_admin_role(role):
            show_error(self, "Bu işlem için yönetici yetkisi gerekir.")
            return
        self.user = user
        self.accept()

class TechnicalServiceCoverDialog(QtDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.user = None
        self.setWindowTitle("AYEC Pro Sistem Kontrolü")
        self.setFixedSize(520, 220)
        
        self.setStyleSheet(theme_qss("""
            QDialog {
                background-color: @surface;
            }
            QLabel {
                color: @text;
            }
            QLineEdit {
                background-color: @surface_alt;
                color: @text;
                border: 1px solid @border;
                border-radius: 8px;
                padding: 6px 10px;
            }
            QLineEdit:focus {
                border-color: @accent;
            }
        """))
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("AYEC Pro Sistem Kontrolü")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("color: @text;"))
        layout.addWidget(title)

        subtitle = QLabel("Güncellemeler Denetleniyor...")
        subtitle.setStyleSheet(theme_qss("color: @text_muted; font-size: 13px;"))
        layout.addWidget(subtitle)

        self.inp_secret = QLineEdit()
        self.inp_secret.setPlaceholderText("Sistem anahtarı")
        self.inp_secret.setEchoMode(QLineEdit.EchoMode.Password)
        self.inp_secret.setFixedHeight(36)
        self.inp_secret.returnPressed.connect(self.handle_login)
        layout.addWidget(self.inp_secret)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        btn_cancel = QPushButton("İptal")
        btn_cancel.setFixedHeight(34)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @surface_alt;
                color: @text;
                border: 1px solid @border;
                border-radius: 8px;
                padding: 0 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: @border;
            }
        """))
        btn_cancel.clicked.connect(self.reject)
        
        btn_ok = QPushButton("Onayla")
        btn_ok.setFixedHeight(34)
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @accent;
                color: @selection_text;
                border: none;
                border-radius: 8px;
                padding: 0 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: @accent_hover;
            }
        """))
        btn_ok.clicked.connect(self.handle_login)
        
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

    def _get_value(self, row, key, idx):
        try:
            return row[key]
        except Exception as e:
            logger.warning(f"Row key access failed for '{key}': {e}")
            try:
                return row[idx]
            except Exception as idx_error:
                logger.warning(f"Row index access failed for '{key}'[{idx}]: {idx_error}")
                return None

    def handle_login(self):
        secret = self.inp_secret.text()
        if not secret:
            show_warning(self, "Lütfen sistem anahtarını girin.")
            return
        try:
            self.db.cursor.execute("SELECT id, username, role, password FROM users")
            rows = self.db.cursor.fetchall() or []
        except Exception as e:
            show_error(self, f"Hata: {e}")
            return
        for row in rows:
            if not is_admin_role(self._get_value(row, "role", 2)):
                continue
            valid, upgraded = verify_password(
                secret,
                str(self._get_value(row, "password", 3)),
            )
            if valid:
                if upgraded:
                    self.db.cursor.execute(
                        "UPDATE users SET password=?, "
                        "password_updated_at=datetime('now') WHERE id=?",
                        (upgraded, self._get_value(row, "id", 0)),
                    )
                    self.db.conn.commit()
                self.user = {
                    "id": self._get_value(row, "id", 0),
                    "username": self._get_value(row, "username", 1),
                    "role": self._get_value(row, "role", 2)
                }
                self.accept()
                return
        show_error(self, "Giriş reddedildi.")

class TechnicalServiceDialog(QtDialog):
    def __init__(self, db, user, parent=None):
        super().__init__(parent)
        self.db = db
        self.user = user or {}
        self._operator_username = str(self.user.get('username', 'unknown') or 'unknown')
        self._operator_role = str(self.user.get('role', 'master') or 'master')
        self.setWindowTitle("Teknik Servis Paneli")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setFixedSize(980, 640)

        shell = QFrame()
        shell.setStyleSheet(theme_qss("background: @window; border: 1px solid @text; border-radius: 16px;"))
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(18, 18, 18, 18)
        shell_layout.setSpacing(14)

        header = QHBoxLayout()
        title_col = QVBoxLayout()
        title = QLabel("AYEC PRO KERNEL ACCESS")
        title.setStyleSheet(theme_qss("color: @danger; font-size: 18px; font-weight: 700;"))
        subtitle = QLabel("SYSTEM LAYER ACTIVE")
        subtitle.setStyleSheet(theme_qss("color: @disabled_text; font-size: 11px;"))
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        header.addLayout(title_col)
        header.addStretch()

        btn_add_user = QPushButton("HESAP EKLE")
        btn_add_user.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_user.setFixedSize(110, 32)
        btn_add_user.setStyleSheet(theme_qss("""
            QPushButton { background: @text; color: white; border-radius: 6px; font-weight: 600; font-size: 12px; }
            QPushButton:hover { background: @text_muted; }
        """))
        btn_add_user.clicked.connect(self.open_add_user_dialog)
        header.addWidget(btn_add_user)

        btn_keygen = QPushButton("🔑 Keygen Aç")
        btn_keygen.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_keygen.setFixedSize(100, 32)
        btn_keygen.setStyleSheet(theme_qss("""
            QPushButton { background: @text; color: white; border-radius: 6px; font-weight: 600; font-size: 12px; }
            QPushButton:hover { background: @text_muted; }
        """))
        btn_keygen.clicked.connect(self.open_keygen)
        header.addWidget(btn_keygen)

        btn_close = QPushButton("×")
        btn_close.setFixedSize(32, 32)
        btn_close.setStyleSheet(theme_qss("""
            QPushButton { background: @selection_text; color: @border; border-radius: 16px; font-weight: 700; }
            QPushButton:hover { background: @danger; color: white; }
        """))
        btn_close.clicked.connect(self.reject)
        header.addWidget(btn_close)
        shell_layout.addLayout(header)

        op_username = self._operator_username
        op_role_raw = self._operator_role
        op_role = normalize_role(op_role_raw)
        if op_role == "Master":
            role_badge = "[MASTER ACCESS]"
            role_color = tc("success")
        elif op_role == "Admin":
            role_badge = "[ADMIN ACCESS]"
            role_color = tc("warning")
        else:
            role_badge = f"[{op_role_raw.upper()}]"
            role_color = tc("accent_hover")
        user_line = QLabel(f"Operator: {op_username}  {role_badge}")
        user_line.setStyleSheet(theme_qss(f"color: {role_color}; font-size: 12px;"))
        shell_layout.addWidget(user_line)

        btns = QHBoxLayout()
        btns.setSpacing(10)
        self.btn_hwid = QPushButton("HWID SIFIRLA")
        self.btn_db = QPushButton("DB ONAR / VACUUM")
        self.btn_license = QPushButton("LİSANS YENİLE")
        self.btn_restore = QPushButton("SİLİNENLERİ KURTAR")
        for b in (self.btn_hwid, self.btn_db, self.btn_license, self.btn_restore):
            b.setFixedHeight(36)
            b.setStyleSheet(theme_qss("""
                QPushButton {
                    background: @selection_text;
                    color: @border;
                    border: 1px solid @text;
                    border-radius: 10px;
                    padding: 0 14px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    border-color: @accent_hover;
                    color: @accent_hover;
                }
            """))
            btns.addWidget(b)
        self.btn_restore.setStyleSheet(theme_qss("""
            QPushButton {
                background: @selection_text;
                color: @warning;
                border: 1px solid @warning;
                border-radius: 10px;
                padding: 0 14px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: @warning;
                color: @selection_text;
                border-color: @warning;
            }
        """))
        btns.addStretch()
        shell_layout.addLayout(btns)

        terminal_label = QLabel("CANLI LOG AKIŞI")
        terminal_label.setStyleSheet(theme_qss("color: @success; font-size: 11px; letter-spacing: 1px;"))
        shell_layout.addWidget(terminal_label)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet(theme_qss("background: @window; color: @success; border-radius: 12px; padding: 12px;"))
        self.log_view.setMinimumHeight(360)
        shell_layout.addWidget(self.log_view)

        self.status_line = QLabel("Sistem hazır.")
        self.status_line.setStyleSheet(theme_qss("color: @disabled_text; font-size: 11px;"))
        shell_layout.addWidget(self.status_line)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.addWidget(shell)

        self.btn_hwid.clicked.connect(self.reset_hwid)
        self.btn_db.clicked.connect(self.run_db_maintenance)
        self.btn_license.clicked.connect(self.renew_license)
        self.btn_restore.clicked.connect(self.show_deleted_records)

        self._log_path = None
        self._log_pos = 0
        self._log_timer = QTimer(self)
        self._log_timer.timeout.connect(self._poll_log)
        self._log_timer.start(1200)
        self._init_log_stream()

    def _append_log(self, text):
        from PyQt6.QtGui import QTextCursor
        self.log_view.moveCursor(QTextCursor.MoveOperation.End)
        self.log_view.insertPlainText(f"{text}\n")
        self.log_view.moveCursor(QTextCursor.MoveOperation.End)

    def _init_log_stream(self):
        from src.utils.path_helper import PathHelper
        self._log_path = PathHelper.get_log_path()
        try:
            if os.path.exists(self._log_path):
                with open(self._log_path, "r", encoding="utf-8", errors="ignore") as f:
                    f.seek(0, os.SEEK_END)
                    size = f.tell()
                    f.seek(max(size - 12000, 0))
                    data = f.read()
                    self._log_pos = f.tell()
                    if data:
                        self.log_view.setPlainText(data)
            else:
                self.log_view.setPlainText("Log dosyası bulunamadı.")
        except Exception as e:
            self.log_view.setPlainText(f"Hata: {e}")

    def _poll_log(self):
        if not self._log_path or not os.path.exists(self._log_path):
            return
        try:
            with open(self._log_path, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(self._log_pos)
                data = f.read()
                self._log_pos = f.tell()
            if data:
                self._append_log(data.rstrip())
        except Exception as e:
            self._append_log(f"[LOG ERROR] {e}")

    def open_keygen(self):
        try:
            hwid = SecurityManager.get_hwid()
            dialog = LicenseKeygenDialog(hwid, self)
            dialog.exec()
        except Exception as e:
            show_error(self, f"Keygen hatası: {e}")

    def open_add_user_dialog(self):
        try:
            from src.ui.pages.settings_widgets.user_management import NewUserDialog
            dialog = NewUserDialog(self.db, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.status_line.setText("Yeni kullanıcı hesabı oluşturuldu.")
                self._append_log("[OK] Teknik servis üzerinden yeni kullanıcı eklendi.")
        except Exception as e:
            show_error(self, f"Hesap ekleme hatası: {e}")
            self._append_log(f"[ERR] Hesap eklenemedi: {e}")

    def reset_hwid(self):
        try:
            hwid = SecurityManager.get_hwid()
            self.db.cursor.execute("UPDATE license_info SET hwid=?", (hwid,))
            self.db.conn.commit()
            self.status_line.setText("HWID güncellendi.")
            self._append_log(f"[OK] HWID güncellendi: {hwid[:16]}... (operator={self._operator_username}, role={self._operator_role})")
        except Exception as e:
            self.status_line.setText("HWID sıfırlama başarısız.")
            self._append_log(f"[ERR] HWID sıfırlama hatası: {e} (operator={self._operator_username}, role={self._operator_role})")

    def run_db_maintenance(self):
        try:
            self.db.cursor.execute("PRAGMA optimize")
            try:
                self.db.cursor.execute("VACUUM")
            except Exception as e:
                logger.warning(f"VACUUM failed during db maintenance: {e}")
            self.db.conn.commit()
            self.status_line.setText("DB onarım tamamlandı.")
            self._append_log(f"[OK] DB onarım / vacuum tamamlandı. (operator={self._operator_username}, role={self._operator_role})")
        except Exception as e:
            self.status_line.setText("DB onarım başarısız.")
            self._append_log(f"[ERR] DB onarım hatası: {e} (operator={self._operator_username}, role={self._operator_role})")

    def renew_license(self):
        days_str, ok = QInputDialog.getItem(self, "Lisans Yenile", "Süre (gün):", ["7", "30"], 0, False)
        if not ok:
            return
        days = int(days_str)
        endpoint = self.db.get_setting("license_admin_endpoint", "http://85.117.239.60/ayec_api/admin-extend.php")
        token = self.db.get_setting("license_admin_token", "")
        license_key = self.db.get_setting("license_key", "")
        payload = {
            "hwid": SecurityManager.get_hwid(),
            "days": days,
            "license_key": license_key
        }
        if token:
            payload["token"] = token
        try:
            import requests
            res = requests.post(endpoint, json=payload, timeout=15)
            ok_flag = False
            msg = res.text
            if res.status_code == 200:
                try:
                    data = res.json()
                    msg = data.get("message") or data.get("msg") or msg
                    ok_flag = data.get("ok") == True or data.get("success") == True or data.get("status") in ("ok", "success")
                except Exception as e:
                    logger.warning(f"License renewal response parse failed: {e}")
                    ok_flag = True
            if ok_flag:
                self._extend_local_expiry(days)
                self.status_line.setText("Lisans yenilendi.")
                self._append_log(f"[OK] Lisans yenileme başarılı ({days} gün). (operator={self._operator_username}, role={self._operator_role})")
            else:
                self.status_line.setText("Lisans yenileme reddedildi.")
                self._append_log(f"[ERR] Lisans yenileme reddedildi: {msg} (operator={self._operator_username}, role={self._operator_role})")
        except Exception as e:
            self.status_line.setText("Lisans yenileme hatası.")
            self._append_log(f"[ERR] Lisans yenileme hatası: {e} (operator={self._operator_username}, role={self._operator_role})")

    def _extend_local_expiry(self, days):
        try:
            row = self.db.cursor.execute("SELECT id, expiry_date FROM license_info ORDER BY id DESC LIMIT 1").fetchone()
            if not row:
                return
            try:
                expiry = row[1]
            except Exception as e:
                logger.warning(f"Local expiry row parse failed: {e}")
                expiry = row["expiry_date"]
            if not expiry:
                return
            from datetime import datetime, timedelta
            exp_dt = datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
            exp_dt = exp_dt + timedelta(days=days)
            new_exp = exp_dt.strftime("%Y-%m-%d %H:%M:%S")
            self.db.cursor.execute("UPDATE license_info SET expiry_date=? WHERE id=?", (new_exp, row[0]))
            self.db.conn.commit()
        except Exception as e:
            logger.warning(f"Local expiry update failed: {e}")

    def show_deleted_records(self):
        self._append_log(f"[SYSTEM]: Veritabanı derin taraması yapılıyor... (operator={self._operator_username}, role={self._operator_role})")
        self.status_line.setText("Silinen kayıtlar taranıyor...")
        def handle_scan(count, message):
            if message:
                self._append_log(f"[WARN] {message}")
                self.status_line.setText(message)
                return
            self._append_log(f"[SUCCESS]: {count} adet kaybolan kayıt bulundu ve indekslendi.")
            self.status_line.setText(f"{count} kayıt bulundu.")
        def handle_restore(record_id, tracking_no):
            self._append_log(f"[RESTORE] Kayıt geri yüklendi: #{record_id} | {tracking_no}")
            self.status_line.setText("Kayıt geri yüklendi.")
        dialog = DeletedRecordsDialog(self.db, on_scan=handle_scan, on_restore=handle_restore, parent=self)
        dialog.exec()

# ==========================================
# ACCOUNT CREATION WIZARD
# ==========================================
from PyQt6.QtWidgets import QWizard, QWizardPage, QRadioButton, QButtonGroup, QComboBox, QFormLayout
