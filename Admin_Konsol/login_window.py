"""
AYEC Pro Admin Konsol - Giris Ekrani
Super Admin email + sifre ile kimlik dogrulama.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QFrame, QMessageBox, QApplication
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon, QPixmap, QPalette, QColor

import config
import api_client


class _LoginThread(QThread):
    success = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, email: str, password: str):
        super().__init__()
        self._email = email
        self._password = password

    def run(self):
        try:
            result = api_client.login(self._email, self._password)
            self.success.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class LoginWindow(QDialog):
    login_ok = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AYEC Pro \u2013 Y\u00f6netim Konsolu")
        self.setFixedSize(420, 540)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self._drag_pos = None
        self._thread: _LoginThread | None = None
        self._login_in_progress = False
        self._build_ui()
        self._apply_style()

        # Son kullanic\u0131y\u0131 doldur
        if config.get("remember_last_user"):
            self._email.setText(config.get("last_email", ""))
            if self._email.text():
                self._password.setFocus()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- Title bar ---
        title_bar = QFrame()
        title_bar.setObjectName("titleBar")
        title_bar.setFixedHeight(48)
        tb_layout = QHBoxLayout(title_bar)
        tb_layout.setContentsMargins(18, 0, 12, 0)

        lbl_title = QLabel("\u26a1 AYEC Pro Admin")
        lbl_title.setObjectName("titleLabel")
        tb_layout.addWidget(lbl_title)
        tb_layout.addStretch()

        self._close_btn = QPushButton("\u2715")
        self._close_btn.setObjectName("closeBtn")
        self._close_btn.setFixedSize(28, 28)
        self._close_btn.setAutoDefault(False)
        self._close_btn.setDefault(False)
        self._close_btn.clicked.connect(self.reject)
        tb_layout.addWidget(self._close_btn)
        root.addWidget(title_bar)

        # --- Body ---
        body = QFrame()
        body.setObjectName("body")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(40, 36, 40, 36)
        body_layout.setSpacing(0)

        # Logo / baslik
        logo_lbl = QLabel("AYEC")
        logo_lbl.setObjectName("logoText")
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body_layout.addWidget(logo_lbl)

        sub_lbl = QLabel("Y\u00f6netim Konsolu")
        sub_lbl.setObjectName("subLabel")
        sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body_layout.addWidget(sub_lbl)
        body_layout.addSpacing(32)

        # Sunucu adresi
        srv_lbl = QLabel("Sunucu Adresi")
        srv_lbl.setObjectName("fieldLabel")
        body_layout.addWidget(srv_lbl)
        self._server = QLineEdit()
        self._server.setObjectName("fieldInput")
        self._server.setText(config.server_url())
        self._server.setPlaceholderText("http://85.117.239.60")
        body_layout.addWidget(self._server)
        body_layout.addSpacing(16)

        # Email
        email_lbl = QLabel("E-posta / Kullan\u0131c\u0131 Ad\u0131")
        email_lbl.setObjectName("fieldLabel")
        body_layout.addWidget(email_lbl)
        self._email = QLineEdit()
        self._email.setObjectName("fieldInput")
        self._email.setPlaceholderText("info@ayecpro.com")
        self._email.returnPressed.connect(self._focus_password)
        body_layout.addWidget(self._email)
        body_layout.addSpacing(16)

        # Sifre
        pass_lbl = QLabel("\u015eifre")
        pass_lbl.setObjectName("fieldLabel")
        body_layout.addWidget(pass_lbl)
        self._password = QLineEdit()
        self._password.setObjectName("fieldInput")
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        self._password.setPlaceholderText("\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022")
        self._password.returnPressed.connect(self._do_login)
        body_layout.addWidget(self._password)
        body_layout.addSpacing(12)

        self._remember = QCheckBox("Beni hat\u0131rla")
        self._remember.setChecked(bool(config.get("remember_last_user")))
        self._remember.setObjectName("rememberCheck")
        body_layout.addWidget(self._remember)
        body_layout.addSpacing(24)

        self._login_btn = QPushButton("Giri\u015f Yap")
        self._login_btn.setObjectName("loginBtn")
        self._login_btn.setFixedHeight(46)
        self._login_btn.setAutoDefault(False)
        self._login_btn.setDefault(False)
        self._login_btn.clicked.connect(self._do_login)
        body_layout.addWidget(self._login_btn)

        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("statusLabel")
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_lbl.setWordWrap(True)
        body_layout.addWidget(self._status_lbl)
        body_layout.addStretch()

        root.addWidget(body)

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog { background: #0f1117; }
            #titleBar { background: #13151c; border-bottom: 1px solid #1e2130; }
            #titleLabel { color: #7c6af7; font-size: 14px; font-weight: bold; font-family: 'Segoe UI'; }
            #closeBtn { background: transparent; color: #6b7280; border: none; font-size: 14px;
                        border-radius: 14px; }
            #closeBtn:hover { background: #dc2626; color: white; }
            #body { background: #0f1117; }
            #logoText { color: #7c6af7; font-size: 48px; font-weight: 900;
                        font-family: 'Segoe UI'; letter-spacing: 4px; }
            #subLabel { color: #6b7280; font-size: 13px; font-family: 'Segoe UI';
                        margin-top: -4px; margin-bottom: 0px; }
            #fieldLabel { color: #9ca3af; font-size: 11px; font-family: 'Segoe UI';
                          text-transform: uppercase; letter-spacing: 1px;
                          margin-bottom: 6px; }
            #fieldInput { background: #1a1d27; color: #e5e7eb; border: 1px solid #2d3147;
                          border-radius: 8px; padding: 10px 14px; font-size: 14px;
                          font-family: 'Segoe UI'; }
            #fieldInput:focus { border: 1px solid #7c6af7; }
            #rememberCheck { color: #6b7280; font-size: 12px; font-family: 'Segoe UI'; }
            #rememberCheck::indicator { width: 16px; height: 16px;
                border: 1px solid #2d3147; border-radius: 4px; background: #1a1d27; }
            #rememberCheck::indicator:checked { background: #7c6af7; border: 1px solid #7c6af7; }
            #loginBtn { background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop:0 #7c6af7, stop:1 #5a4fcf);
                        color: white; border: none; border-radius: 10px;
                        font-size: 15px; font-weight: bold; font-family: 'Segoe UI'; }
            #loginBtn:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                  stop:0 #8b7cf8, stop:1 #6b5fd0); }
            #loginBtn:pressed { background: #5a4fcf; }
            #loginBtn:disabled { background: #2d3147; color: #4b5563; }
            #statusLabel { color: #f87171; font-size: 12px; font-family: 'Segoe UI';
                           margin-top: 10px; min-height: 20px; }
        """)

    # Pencere suruklemesi
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def _do_login(self):
        if self._login_in_progress:
            return
        email = self._email.text().strip()
        password = self._password.text()
        server = self._server.text().strip()

        if not email or not password:
            self._show_error("L\u00fctfen e-posta ve \u015fifre girin.")
            return
        if not server:
            self._show_error("Sunucu adresi bo\u015f olamaz.")
            return

        # Sunucu adresini kaydet
        config.set("server_url", server.rstrip("/"))

        self._login_in_progress = True
        self._set_loading(True)
        self._status_lbl.setText("Ba\u011flan\u0131yor...")
        self._status_lbl.setStyleSheet("color: #60a5fa;")

        self._thread = _LoginThread(email, password)
        self._thread.success.connect(self._on_success)
        self._thread.failed.connect(self._on_failed)
        self._thread.start()

    def _on_success(self, data: dict):
        self._login_in_progress = False
        self._set_loading(False)
        if self._remember.isChecked():
            config.set("remember_last_user", True)
            config.set("last_email", self._email.text().strip())
        else:
            config.set("remember_last_user", False)
        self.accept()
        self.login_ok.emit()

    def _on_failed(self, error: str):
        self._login_in_progress = False
        self._set_loading(False)
        self._show_error(error)

    def _focus_password(self):
        self._password.setFocus()
        self._password.selectAll()

    def _set_loading(self, loading: bool):
        self._login_btn.setEnabled(not loading)
        self._email.setEnabled(not loading)
        self._password.setEnabled(not loading)
        self._server.setEnabled(not loading)
        self._close_btn.setEnabled(not loading)
        if loading:
            self._login_btn.setText("Ba\u011flan\u0131yor...")
        else:
            self._login_btn.setText("Giri\u015f Yap")

    def _show_error(self, msg: str):
        self._status_lbl.setText(msg)
        self._status_lbl.setStyleSheet("color: #f87171;")
