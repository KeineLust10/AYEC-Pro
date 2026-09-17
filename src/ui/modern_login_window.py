# -*- coding: utf-8 -*-

"""
Modern Login Window with Glassmorphism Design
Premium authentication interface for AYEC Pro
"""

from PyQt6.QtWidgets import (QDialog as QtDialog, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QStackedWidget,
                             QCheckBox, QApplication, QScrollArea, QProgressBar,
                             QFormLayout, QTextEdit, QInputDialog, QTableWidget, QTableWidgetItem,
                             QHeaderView, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QPoint, QSize, QThread, QUrl, QTimer
from PyQt6.QtGui import QFont, QColor, QPainter, QLinearGradient, QBrush, QPainterPath, QPixmap, QAction, QDesktopServices

from src.utils.theme_colors import theme_qss, qc, tc
from src.utils.toast_notification import show_success, show_error, show_warning, show_info
from src.utils.auth_manager import AuthManager
from src.ui.dialogs.license_keygen_dialog import LicenseKeygenDialog
from src.utils.design_system import DesignTokens
from src.utils.role_utils import is_admin_role
import sys
import shutil
from datetime import datetime
import os
import ctypes
from src.utils.logger import logger
from src.utils.desktop_web_sync import configured_sync_url, sync_session_path
from src.utils.web_sync_client import WebSyncClient, WebSyncError
from src.utils.license_api_client import LicenseApiClient, LicenseApiError

class _FullInitWorker(QThread):
    completed = pyqtSignal(bool, str)

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self._db_name = getattr(db, "_db_name", "ayecpro.db")

    def run(self):
        db = None
        try:
            from src.database import Database
            db = Database(self._db_name, init_mode="connection_only")
            db.ensure_full_initialized()
            self.completed.emit(True, "")
        except Exception as e:
            self.completed.emit(False, str(e))
        finally:
            if db is not None:
                try:
                    db.close()
                except Exception:
                    pass


class _RemoteAccountLoginWorker(QThread):
    completed = pyqtSignal(bool, object)

    def __init__(self, identifier, password, tenant_id="", parent=None):
        super().__init__(parent)
        self.identifier = str(identifier or "").strip()
        self.password = str(password or "")
        self.tenant_id = str(tenant_id or "").strip()

    def run(self):
        try:
            url = configured_sync_url()
            client = WebSyncClient(url, verify_tls=not url.lower().startswith("http://"), timeout=20)
            result = client.login(
                self.identifier,
                self.password,
                remember=True,
                tenant_id=self.tenant_id or None,
            )
            user = dict(result.get("user") or {})
            client.save_session(
                sync_session_path(),
                {
                    "username": user.get("username") or self.identifier,
                    "tenant_id": user.get("tenant_id") or self.tenant_id,
                    "company_name": user.get("company_name") or "",
                    "initial_pull_pending": True,
                },
            )
            self.completed.emit(True, result)
        except Exception as exc:
            self.completed.emit(False, {"error": str(exc)})


class _ServerAccessCheckWorker(QThread):
    completed = pyqtSignal(bool, bool, str, object)

    def __init__(self, identifier, password, tenant_id, parent=None):
        super().__init__(parent)
        self.identifier = str(identifier or "").strip()
        self.password = str(password or "")
        self.tenant_id = str(tenant_id or "").strip()

    def run(self):
        try:
            client = LicenseApiClient(timeout=8)
            payload = client.status_for_credentials(
                self.identifier, self.password, self.tenant_id
            )
            access = dict(payload.get("access") or {})
            allowed = bool(access.get("allowed", True))
            message = str(access.get("message") or "")
            if allowed:
                try:
                    url = configured_sync_url()
                    client = WebSyncClient(
                        url,
                        verify_tls=not url.lower().startswith("http://"),
                        timeout=8,
                    )
                    result = client.login(
                        self.identifier,
                        self.password,
                        remember=True,
                        tenant_id=self.tenant_id,
                    )
                    user = dict(result.get("user") or {})
                    client.save_session(
                        sync_session_path(),
                        {
                            "username": user.get("username") or self.identifier,
                            "tenant_id": user.get("tenant_id") or self.tenant_id,
                            "company_name": user.get("company_name") or "",
                            "initial_pull_pending": False,
                        },
                    )
                except Exception as session_exc:
                    logger.warning(
                        "Remembered web session could not be refreshed: %s",
                        session_exc,
                    )
            self.completed.emit(True, allowed, message, payload)
        except LicenseApiError as exc:
            message = str(exc)
            normalized = message.casefold()
            status_code = int(getattr(exc, "status_code", 0) or 0)
            unreachable = any(
                marker in normalized
                for marker in (
                    "baglanilamadi",
                    "timed out",
                    "timeout",
                    "connection refused",
                    "name or service not known",
                    "bad gateway",
                    "service unavailable",
                    "gateway timeout",
                )
            ) or status_code >= 500 or status_code in (408, 429)
            self.completed.emit(not unreachable, False, message, {})
        except Exception as exc:
            self.completed.emit(False, False, str(exc), {})


class _RememberedServerAccessWorker(QThread):
    completed = pyqtSignal(bool, bool, str)

    def __init__(self, username, tenant_id, parent=None):
        super().__init__(parent)
        self.username = str(username or "").strip()
        self.tenant_id = str(tenant_id or "").strip()

    def run(self):
        try:
            url = configured_sync_url()
            client = WebSyncClient(
                url,
                verify_tls=not url.lower().startswith("http://"),
                timeout=8,
            )
            metadata = client.load_session(sync_session_path())
            session_user = str(metadata.get("username") or "").strip()
            session_tenant = str(metadata.get("tenant_id") or "").strip()
            if (
                not client.cookies
                or not session_user
                or session_user.casefold() != self.username.casefold()
                or session_tenant != self.tenant_id
            ):
                self.completed.emit(
                    True,
                    False,
                    "Kayitli sunucu oturumu bulunamadi.",
                )
                return
            status = client.auth_status()
            remote_user = dict(status.get("user") or {})
            allowed = bool(
                status.get("authenticated")
                and str(remote_user.get("tenant_id") or "") == self.tenant_id
                and str(remote_user.get("username") or "").casefold()
                == self.username.casefold()
            )
            self.completed.emit(
                True,
                allowed,
                "" if allowed else "Kayitli sunucu oturumunun suresi doldu.",
            )
        except WebSyncError as exc:
            status_code = int(getattr(exc, "status_code", 0) or 0)
            self.completed.emit(
                bool(status_code and status_code < 500 and status_code not in (408, 429)),
                False,
                str(exc),
            )
        except Exception as exc:
            self.completed.emit(False, False, str(exc))


class _IconInput(QFrame):
    def __init__(self, placeholder, is_password=False):
        super().__init__()
        self.setObjectName("IconInput")
        self.setFixedHeight(55)

        icon_text, clean_placeholder = self._split_icon_placeholder(placeholder)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(10)

        self._icon = QLabel(icon_text)
        self._icon.setFixedWidth(22)
        self._icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon.setFont(QFont("Segoe UI Emoji", 16))
        self._icon.setStyleSheet(theme_qss("color: rgba(255, 255, 255, 0.85);"))
        layout.addWidget(self._icon)

        self._line_edit = QLineEdit()
        self._line_edit.setPlaceholderText(clean_placeholder)
        self._line_edit.setFrame(False)
        if is_password:
            self._line_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._line_edit.setStyleSheet(theme_qss("""
            QLineEdit {
                border: none;
                background: transparent;
                color: @surface_alt;
                padding: 0 2px;
                font-size: 15px;
                font-weight: 500;
                font-family: 'Segoe UI';
                selection-background-color: @accent;
            }
            QLineEdit::placeholder {
                color: rgba(148, 163, 184, 1.0);
            }
        """))
        layout.addWidget(self._line_edit, 1)

        self.setStyleSheet(theme_qss("""
            QFrame#IconInput {
                background: rgba(15, 23, 42, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 12px;
            }
            QFrame#IconInput:hover {
                background: rgba(30, 41, 59, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.30);
            }
        """))

        self.returnPressed = self._line_edit.returnPressed

    def _split_icon_placeholder(self, placeholder):
        s = (placeholder or "").strip()
        if not s:
            return "", ""
        icon_map = {"👤", "🔒", "📧"}
        if len(s) >= 2 and s[0] in icon_map and s[1] == " ":
            return s[0], s[2:].strip()
        return "", s

    def text(self):
        return self._line_edit.text()

    def setText(self, text):
        self._line_edit.setText(text)

    def clear(self):
        self._line_edit.clear()

    def setFocus(self, *args, **kwargs):
        self._line_edit.setFocus(*args, **kwargs)

class ModernLoginWindow(QtDialog):
    login_successful = pyqtSignal(object)
    
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.auth_manager = AuthManager(db)
        self._init_worker = None
        self._pending_user = None
        # Kept only in memory so the desktop startup sync can authenticate the
        # web tenant after a manual login. It is never written to disk.
        self._last_login_password = ""
        
        self._safe_ui = False
        try:
            if os.environ.get("AYEC_DISABLE_GLASS", "").strip() in ("1", "true", "True", "yes", "YES"):
                self._safe_ui = True
        except Exception:
            pass

        if not self._safe_ui:
            try:
                SM_REMOTESESSION = 0x1000
                self._safe_ui = bool(ctypes.windll.user32.GetSystemMetrics(SM_REMOTESESSION))
            except Exception as e:
                logger.warning(f"Remote session detection failed: {e}")

        # Her zaman frameless — custom title bar kullanıyoruz
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.resize(960, 720)
        self.setup_ui()

        self._setup_done = False  # Gerçek değer deferred'da yüklenecek
        self.setWindowTitle("AYEC Pro v69.0.0 - Giriş")
        from src.utils.path_helper import PathHelper
        self.setWindowIcon(PathHelper.get_app_icon())

        self.setMinimumSize(800, 600)
        self.center_window()

        QTimer.singleShot(0, lambda: PathHelper.apply_windows_taskbar_icon(self))

        # Dragging
        self.dragging = False
        self.drag_position = QPoint()

        self.stack.setCurrentIndex(1)  # Önce sayfayı göster

        # DB sorgularını pencere görüntülendikten SONRA çalıştır (freeze önleme)
        QTimer.singleShot(80, self._deferred_init)
    
    def center_window(self):
        # Correctly center on the screen
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = (geo.width() - self.width()) // 2
            y = (geo.height() - self.height()) // 2
            self.move(geo.x() + x, geo.y() + y)
    
    def paintEvent(self, event):
        """Modern window — rounded corners + subtle border + shadow."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Drop shadow (simulated via outer slightly-transparent rect)
        shadow_color = QColor(0, 0, 0, 30)
        for i in range(4, 0, -1):
            shadow_path = QPainterPath()
            shadow_path.addRoundedRect(i, i + 2, self.width() - i * 2, self.height() - i * 2, 18, 18)
            painter.fillPath(shadow_path, shadow_color)

        # Main background
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 16, 16)
        painter.fillPath(path, qc("surface"))

        # Border
        border_color = QColor(0, 0, 0, 22)
        painter.setPen(border_color)
        painter.drawPath(path)


    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── CUSTOM TITLE BAR ──────────────────────────────────────────────
        title_bar = QWidget()
        title_bar.setObjectName("TitleBar")
        title_bar.setFixedHeight(52)
        title_bar.setStyleSheet(theme_qss("""
            QWidget#TitleBar {
                background: @surface;
                border-bottom: 1px solid @border;
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
            }
        """))

        tb_layout = QHBoxLayout(title_bar)
        tb_layout.setContentsMargins(16, 0, 12, 0)
        tb_layout.setSpacing(10)

        # Logo (small)
        self.logo_label = QLabel()
        self.logo_label.setFixedSize(32, 32)
        self.logo_label.setScaledContents(True)
        self.setup_login_logo()
        tb_layout.addWidget(self.logo_label)

        # App title
        title_lbl = QLabel("AYEC Pro — Giriş")
        title_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        title_lbl.setStyleSheet(theme_qss("color: @text; background: transparent;"))
        tb_layout.addWidget(title_lbl)

        tb_layout.addStretch()

        # Window control buttons
        def _wc_btn(symbol, hover_color="#ef4444"):
            btn = QPushButton(symbol)
            btn.setFixedSize(36, 36)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFont(QFont("Segoe UI", 11))
            btn.setStyleSheet(theme_qss(f"""
                QPushButton {{
                    background: transparent;
                    color: @text_muted;
                    border: none;
                    border-radius: 8px;
                }}
                QPushButton:hover {{
                    background: {hover_color};
                    color: white;
                }}
            """))
            return btn

        btn_min = _wc_btn("─", "#64748b")
        btn_min.setToolTip("Simge Durumuna Küçült")
        btn_min.clicked.connect(self.showMinimized)
        tb_layout.addWidget(btn_min)

        btn_max = _wc_btn("□", "#64748b")
        btn_max.setToolTip("Büyüt / Küçült")
        btn_max.clicked.connect(self._toggle_maximize)
        tb_layout.addWidget(btn_max)

        btn_close = _wc_btn("✕", "#ef4444")
        btn_close.setToolTip("Kapat")
        btn_close.clicked.connect(self.close)
        tb_layout.addWidget(btn_close)

        main_layout.addWidget(title_bar)

        # Enable dragging via title bar
        title_bar.mousePressEvent = self._tb_mouse_press
        title_bar.mouseMoveEvent = self._tb_mouse_move
        title_bar.mouseReleaseEvent = self._tb_mouse_release
        
        # === STACKED WIDGET FOR PAGES ===
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(theme_qss("background: transparent;"))
        
        # Page 0: Registration
        self.stack.addWidget(self.create_register_page())
        
        # Page 1: Login (MAIN PAGE)
        self.stack.addWidget(self.create_login_page())
        
        # Page 2: Opening/Loading
        self.stack.addWidget(self.create_opening_page())
        
        main_layout.addWidget(self.stack)
        
    def create_circular_pixmap(self, source_pixmap, size):
        """Crop a pixmap into a circle"""
        target = QPixmap(size)
        target.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(target)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        path = QPainterPath()
        path.addEllipse(0, 0, size.width(), size.height())
        painter.setClipPath(path)
        
        scaled_pixmap = source_pixmap.scaled(
            size, 
            Qt.AspectRatioMode.KeepAspectRatioByExpanding, 
            Qt.TransformationMode.SmoothTransformation
        )
        
        # Center crop
        x = (scaled_pixmap.width() - size.width()) // 2
        y = (scaled_pixmap.height() - size.height()) // 2
        
        painter.drawPixmap(0, 0, scaled_pixmap, x, y, size.width(), size.height())
        painter.end()
        
        return target
    
    def _find_brand_logo_path(self):
        try:
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
            assets_dir = os.path.join(root_dir, "assets")
            candidates = [
                os.path.join(assets_dir, "ayec_logo.png"),  # AYEC Pro chip logo
                os.path.join(assets_dir, "app_icon.png"),
                os.path.join(assets_dir, "logo.png"),
                os.path.join(assets_dir, "brand_logo.png"),
                os.path.join(assets_dir, "icon.png"),
            ]
            for candidate in candidates:
                if os.path.exists(candidate):
                    return candidate
            return None
        except Exception as e:
            logger.warning(f"Logo path detection failed: {e}")
            return None

    def create_register_page(self):
        """Standardized registration landing - simplified to point to SetupWizard"""
        page = QWidget()
        page.setProperty("skipThemeTransform", True)
        page.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(30)
        
        layout.addStretch(1)
        
        title = QLabel("Hoş Geldiniz!")
        title.setFont(QFont("Segoe UI", 32, QFont.Weight.Bold))
        title.setProperty("skipThemeTransform", True)
        title.setStyleSheet(f"color: {tc('text', default='#F8FAFC')};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        desc = QLabel("AYEC Pro işletmenizi dijitalleştirmek için hazır.\nKurulum sadece birkaç dakika sürecek.")
        desc.setFont(QFont("Segoe UI", 16))
        desc.setProperty("skipThemeTransform", True)
        desc.setStyleSheet(f"color: {tc('text_muted', default='#CBD5E1')};")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)
        
        layout.addSpacing(20)
        
        btn_start = QPushButton("Kurulumu Başlat")
        btn_start.setFixedSize(280, 65)
        btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_start.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        btn_start.setProperty("skipThemeTransform", True)
        btn_start.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3B82F6, stop:1 #2563EB);
                color: white;
                border-radius: 32px;
                border: none;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #60A5FA, stop:1 #3B82F6);
            }
        """)
        btn_start.clicked.connect(self.open_company_wizard)
        layout.addWidget(btn_start, alignment=Qt.AlignmentFlag.AlignCenter)
        
        layout.addStretch(1)
        
        btn_back = QPushButton("Zaten bir hesabınız mı var? Giriş Yap")
        btn_back.setText("Kay\u0131tl\u0131 hesab\u0131m var")
        btn_back.setProperty("skipThemeTransform", True)
        btn_back.setStyleSheet(
            f"color: {tc('text_muted', default='#CBD5E1')}; background: transparent; "
            "border: none; font-size: 14px; text-decoration: underline;"
        )
        btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_back.clicked.connect(self.open_remote_account_login)
        layout.addWidget(btn_back, alignment=Qt.AlignmentFlag.AlignCenter)
        
        layout.addSpacing(40)
        return page
    
    def create_login_page(self):
        """Modern account selection page — compact hero + user grid + action bar."""
        page = QWidget()
        page.setStyleSheet(theme_qss("background: transparent;"))
        layout = QVBoxLayout(page)
        layout.setContentsMargins(36, 12, 36, 24)
        layout.setSpacing(16)

        # ── HERO BANNER ──────────────────────────────────────────────────────
        hero_card = QFrame()
        hero_card.setObjectName("loginHero")
        hero_card.setProperty("skipThemeTransform", True)
        hero_card.setFixedHeight(122)
        hero_card.setStyleSheet("""
            QFrame#loginHero {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0f172a,
                    stop:0.48 #172554,
                    stop:1 #2563eb
                );
                border-radius: 22px;
                border: 1px solid rgba(255,255,255,0.10);
            }
        """)
        hero_shadow = QGraphicsDropShadowEffect(self)
        hero_shadow.setBlurRadius(28)
        hero_shadow.setOffset(0, 8)
        hero_shadow.setColor(QColor(15, 23, 42, 90))
        hero_card.setGraphicsEffect(hero_shadow)

        hero_layout = QHBoxLayout(hero_card)
        hero_layout.setContentsMargins(26, 0, 26, 0)
        hero_layout.setSpacing(18)

        brand_mark = QLabel("AY")
        brand_mark.setFixedSize(58, 58)
        brand_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_mark.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        brand_mark.setStyleSheet("""
            background: rgba(255,255,255,0.14);
            color: white;
            border: 1px solid rgba(255,255,255,0.22);
            border-radius: 18px;
        """)
        hero_layout.addWidget(brand_mark)

        # Left: title + subtitle
        text_col = QVBoxLayout()
        text_col.setSpacing(4)
        text_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        eyebrow = QLabel("AYEC PRO  /  GUVENLI GIRIS")
        eyebrow.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        eyebrow.setStyleSheet(
            "color: rgba(191,219,254,0.90); background: transparent; letter-spacing: 1px;"
        )
        text_col.addWidget(eyebrow)

        title = QLabel("Kim Giri\u015f Yap\u0131yor?")
        title.setFont(QFont("Segoe UI", 21, QFont.Weight.Bold))
        title.setStyleSheet("color: white; background: transparent;")
        text_col.addWidget(title)

        subtitle = QLabel(
            "Kullan\u0131c\u0131 hesab\u0131n\u0131z\u0131 se\u00e7in ve kald\u0131\u011f\u0131n\u0131z yerden devam edin."
        )
        subtitle.setFont(QFont("Segoe UI", 10))
        subtitle.setStyleSheet("color: rgba(255,255,255,0.76); background: transparent;")
        text_col.addWidget(subtitle)

        hero_layout.addLayout(text_col, 1)

        # Right: chips
        chips_col = QHBoxLayout()
        chips_col.setSpacing(8)
        chips_col.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
        for chip_text in (
            "GUVENLI OTURUM",
            "COKLU HESAP",
        ):
            chip = QLabel(chip_text)
            chip.setFixedHeight(26)
            chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chip.setStyleSheet("""
                background: rgba(255,255,255,0.12);
                color: rgba(255,255,255,0.90);
                border: 1px solid rgba(255,255,255,0.18);
                border-radius: 13px;
                padding: 0 10px;
                font-size: 10px;
                font-weight: 600;
            """)
            chips_col.addWidget(chip)
        hero_layout.addLayout(chips_col)

        layout.addWidget(hero_card)

        # ── PROFILES CARD ─────────────────────────────────────────────────────
        profiles_card = QFrame()
        profiles_card.setObjectName("profilesPanel")
        profiles_card.setStyleSheet(theme_qss("""
            QFrame#profilesPanel {
                background: @surface;
                border: 1px solid @border;
                border-radius: 22px;
            }
        """))
        p_shadow = QGraphicsDropShadowEffect(self)
        p_shadow.setBlurRadius(20)
        p_shadow.setOffset(0, 4)
        p_shadow.setColor(QColor(0, 0, 0, 18))
        profiles_card.setGraphicsEffect(p_shadow)

        profiles_layout = QVBoxLayout(profiles_card)
        profiles_layout.setContentsMargins(26, 20, 26, 18)
        profiles_layout.setSpacing(14)

        # Section header row
        section_header = QHBoxLayout()
        section_header.setSpacing(12)

        header_text = QVBoxLayout()
        header_text.setSpacing(3)
        section_title = QLabel("Kay\u0131tl\u0131 Kullan\u0131c\u0131lar")
        section_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        section_title.setStyleSheet(theme_qss("color: @text; background: transparent;"))
        header_text.addWidget(section_title)

        section_desc = QLabel(
            "Oturum a\u00e7mak i\u00e7in bir profil se\u00e7in. Hesaplar yaln\u0131zca bu cihazda listelenir."
        )
        section_desc.setFont(QFont("Segoe UI", 9))
        section_desc.setStyleSheet(theme_qss("color: @text_muted; background: transparent;"))
        header_text.addWidget(section_desc)
        section_header.addLayout(header_text)
        section_header.addStretch()

        self.profile_count_label = QLabel("0 PROFIL")
        self.profile_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.profile_count_label.setFixedHeight(30)
        self.profile_count_label.setStyleSheet(theme_qss("""
            background: @surface_alt;
            color: @accent;
            border: 1px solid @border;
            border-radius: 10px;
            padding: 0 12px;
            font-size: 9px;
            font-weight: 700;
        """))
        section_header.addWidget(self.profile_count_label)

        profiles_layout.addLayout(section_header)

        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFixedHeight(1)
        divider.setStyleSheet(theme_qss("background: @border; border: none;"))
        profiles_layout.addWidget(divider)

        # User grid
        profiles_container = QWidget()
        profiles_container.setStyleSheet(theme_qss("background: transparent;"))
        from PyQt6.QtWidgets import QGridLayout
        self.profiles_grid = QGridLayout(profiles_container)
        self.profiles_grid.setHorizontalSpacing(18)
        self.profiles_grid.setVerticalSpacing(18)
        self.profiles_grid.setContentsMargins(0, 12, 0, 12)
        self.profiles_grid.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        profiles_layout.addWidget(profiles_container, 1)

        # ── ACTION BAR ────────────────────────────────────────────────────────
        action_divider = QFrame()
        action_divider.setFrameShape(QFrame.Shape.HLine)
        action_divider.setFixedHeight(1)
        action_divider.setStyleSheet(theme_qss("background: @border; border: none;"))
        profiles_layout.addWidget(action_divider)

        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)
        actions_row.setContentsMargins(0, 2, 0, 0)

        actions_label = QLabel("DIGER ISLEMLER")
        actions_label.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        actions_label.setStyleSheet(theme_qss("color: @text_muted; background: transparent;"))
        actions_row.addWidget(actions_label)
        actions_row.addSpacing(6)

        def _action_btn(label, primary=False, danger=False):
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(40)
            btn.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
            if primary:
                btn.setStyleSheet(theme_qss("""
                    QPushButton {
                        background: @accent;
                        color: white;
                        border: none;
                        border-radius: 12px;
                        padding: 0 14px;
                    }
                    QPushButton:hover { background: @accent_hover; }
                    QPushButton:pressed { background: @accent_pressed; }
                """))
            elif danger:
                btn.setStyleSheet(theme_qss("""
                    QPushButton {
                        background: transparent;
                        color: @text_muted;
                        border: 1px solid @border;
                        border-radius: 12px;
                        padding: 0 13px;
                    }
                    QPushButton:hover {
                        background: rgba(16,185,129,0.08);
                        color: @text;
                        border-color: @success;
                    }
                """))
            else:
                btn.setStyleSheet(theme_qss("""
                    QPushButton {
                        background: @surface_alt;
                        color: @text;
                        border: 1px solid @border;
                        border-radius: 12px;
                        padding: 0 13px;
                    }
                    QPushButton:hover {
                        background: rgba(37,99,235,0.07);
                        border-color: @accent;
                        color: @accent;
                    }
                """))
            return btn

        add_account_btn = _action_btn("+ Hesap Ekle")
        add_account_btn.clicked.connect(self.open_account_wizard)
        actions_row.addWidget(add_account_btn)

        remote_account_btn = _action_btn("Kay\u0131tl\u0131 Hesab\u0131m Var", primary=True)
        remote_account_btn.setToolTip(
            "Web veya mobil uygulamada kulland\u0131\u011f\u0131n\u0131z hesapla giri\u015f yap\u0131n."
        )
        remote_account_btn.clicked.connect(self.open_remote_account_login)
        actions_row.addWidget(remote_account_btn)

        add_company_btn = _action_btn("+ Firma Ekle", primary=True)
        add_company_btn.clicked.connect(self.open_company_wizard)
        actions_row.addWidget(add_company_btn)

        actions_row.addStretch()
        profiles_layout.addLayout(actions_row)
        layout.addWidget(profiles_card, 1)

        return page

    def create_opening_page(self):
        page = QWidget()
        page.setStyleSheet(theme_qss("background: transparent;"))
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        title = QLabel("Açılıyor")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("color: @text;"))
        layout.addWidget(title)

        self.lbl_opening_status = QLabel("Veriler hazırlanıyor...")
        self.lbl_opening_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_opening_status.setFont(QFont("Segoe UI", 12))
        self.lbl_opening_status.setStyleSheet(theme_qss("color: @text_muted;"))
        layout.addWidget(self.lbl_opening_status)

        self.opening_progress = QProgressBar()
        self.opening_progress.setRange(0, 0)
        self.opening_progress.setFixedHeight(6)
        self.opening_progress.setTextVisible(False)
        self.opening_progress.setStyleSheet(theme_qss("""
            QProgressBar {
                background: @border;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 @success,
                    stop:1 @accent
                );
                border-radius: 3px;
            }
        """))
        # Width limit for cleaner look
        progress_container = QWidget()
        pc_layout = QHBoxLayout(progress_container)
        pc_layout.addStretch()
        pc_layout.addWidget(self.opening_progress)
        self.opening_progress.setFixedWidth(300)
        pc_layout.addStretch()
        
        layout.addWidget(progress_container)

        layout.addSpacing(10)

        hint = QLabel("Lütfen bekleyin, uygulama hazırlanıyor.")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setFont(QFont("Segoe UI", 10))
        hint.setStyleSheet(theme_qss("color: @text_muted;"))
        layout.addWidget(hint)

        layout.addStretch()
        return page

    def fetch_known_usernames(self):
        try:
            self._repair_missing_setup_users()
            self.db.cursor.execute("""
                SELECT username, role
                FROM users
                WHERE username IS NOT NULL AND TRIM(username) <> ''
                  AND LOWER(TRIM(username)) NOT IN ('admin', 'master')
                  AND COALESCE(active, 1) = 1
                ORDER BY COALESCE(last_login, created_at) DESC, username ASC
            """)
            rows = self.db.cursor.fetchall() or []
            profiles = []
            for row in rows:
                username = None
                role = ""
                try:
                    username = row["username"]
                    role = row.get("role", "") if hasattr(row, "get") else ""
                except Exception:
                    try:
                        username = row[0]
                        role = row[1] if len(row) > 1 else ""
                    except Exception:
                        username = None
                username = (str(username or "")).strip()
                if username:
                    profiles.append({"username": username, "role": str(role or "")})
            return profiles
        except Exception:
            return []

    def _repair_missing_setup_users(self):
        try:
            user_cols = set(self.db._get_table_columns("users")) if hasattr(self.db, "_get_table_columns") else set()
            personnel_cols = set(self.db._get_table_columns("personnel")) if hasattr(self.db, "_get_table_columns") else set()
            if not user_cols or not personnel_cols:
                return

            self.db.cursor.execute("""
                SELECT COUNT(*)
                FROM users
                WHERE username IS NOT NULL AND TRIM(username) <> ''
                  AND LOWER(TRIM(username)) NOT IN ('admin', 'master')
            """)
            known_user_count = int((self.db.cursor.fetchone() or [0])[0])
            if known_user_count > 0:
                return

            self.db.cursor.execute("""
                SELECT id, name, username, password, role, email
                FROM personnel
                WHERE username IS NOT NULL AND TRIM(username) <> ''
                  AND password IS NOT NULL AND TRIM(password) <> ''
                  AND COALESCE(active, 1) = 1
                  AND LOWER(TRIM(username)) NOT IN ('admin', 'master')
                ORDER BY id ASC
            """)
            personnel_rows = self.db.cursor.fetchall() or []
            if not personnel_rows:
                return

            repaired = 0
            for row in personnel_rows:
                try:
                    personnel_id = row["id"]
                    full_name = row["name"]
                    username = row["username"]
                    password = row["password"]
                    role = row["role"]
                    email = row["email"]
                except Exception:
                    personnel_id, full_name, username, password, role, email = row

                username = (str(username or "")).strip()
                password = str(password or "")
                if not username or not password:
                    continue

                existing = self.db.cursor.execute(
                    "SELECT id FROM users WHERE username=?",
                    (username,),
                ).fetchone()
                if existing:
                    continue

                created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                user_data = {
                    "username": username,
                    "password": password,
                    "email": (str(email or "").strip() or None),
                    "role": (str(role or "").strip() or "Yönetici"),
                    "created_at": created_at,
                    "full_name": (str(full_name or "").strip() or username),
                    "name": (str(full_name or "").strip() or username),
                    "personnel_id": personnel_id,
                    "active": 1,
                    "is_active": 1,
                    "interface_edit_access": 1,
                }
                if "permissions" in user_cols:
                    user_data["permissions"] = '{"mode":"all"}'

                insert_cols = [col for col in user_data if col in user_cols]
                if not insert_cols:
                    continue
                placeholders = ",".join(["?"] * len(insert_cols))
                self.db.cursor.execute(
                    f"INSERT INTO users ({', '.join(insert_cols)}) VALUES ({placeholders})",
                    tuple(user_data[col] for col in insert_cols),
                )
                repaired += 1

            if repaired:
                self.db.conn.commit()
                logger.info("Login repair synced %s setup user(s) from personnel to users", repaired)
        except Exception as e:
            logger.warning(f"Setup user repair skipped: {e}")

    def refresh_user_list(self):
        """Populate Profile Grid — background thread ile DB sorgusu"""
        self._repair_missing_setup_users()
        # Clear existing grid
        while self.profiles_grid.count():
            item = self.profiles_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Yükleniyor placeholder
        lbl_loading = QLabel("Yükleniyor...")
        lbl_loading.setStyleSheet(theme_qss("color: @disabled_text; font-size: 14px;"))
        lbl_loading.setObjectName("_loading_placeholder")
        self.profiles_grid.addWidget(lbl_loading, 0, 0)

        class _UserLoader(QThread):
            done = pyqtSignal(list)
            def __init__(self, db, parent=None):
                super().__init__(parent)
                self._db_name = getattr(db, "_db_name", "ayecpro.db")
            def run(self):
                db = None
                try:
                    from src.database import Database
                    db = Database(self._db_name, init_mode="auth")
                    db.cursor.execute("""
                        SELECT username, role
                        FROM users
                        WHERE username IS NOT NULL AND TRIM(username) <> ''
                          AND LOWER(TRIM(username)) NOT IN ('admin', 'master')
                          AND COALESCE(active, 1) = 1
                        ORDER BY COALESCE(last_login, created_at) DESC, username ASC
                    """)
                    rows = db.cursor.fetchall() or []
                    profiles = []
                    for row in rows:
                        try:
                            username = row["username"]
                            role = row.get("role", "") if hasattr(row, "get") else ""
                        except Exception:
                            try:
                                username = row[0]
                                role = row[1] if len(row) > 1 else ""
                            except Exception:
                                username = None
                        username = (str(username or "")).strip()
                        if username:
                            profiles.append({"username": username, "role": str(role or "")})
                    self.done.emit(profiles)
                except Exception:
                    self.done.emit([])
                finally:
                    if db is not None:
                        try:
                            db.close()
                        except Exception:
                            pass

        self._user_loader = _UserLoader(self.db)
        app = QApplication.instance()
        if app:
            if not hasattr(app, "_active_threads"):
                app._active_threads = set()
            app._active_threads.add(self._user_loader)
            self._user_loader.finished.connect(lambda: app._active_threads.discard(self._user_loader) if app else None)

        def on_users_loaded(profiles):
            # Clear the temporary loading state.
            while self.profiles_grid.count():
                item = self.profiles_grid.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            if hasattr(self, "profile_count_label"):
                self.profile_count_label.setText(f"{len(profiles)} PROFIL")

            if not profiles:
                lbl = QLabel(
                    "Hen\u00fcz kay\u0131tl\u0131 kullan\u0131c\u0131 yok. Yeni bir hesap ekleyerek ba\u015flayabilirsiniz."
                )
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl.setStyleSheet(theme_qss("""
                    background: @surface_alt;
                    color: @text_muted;
                    border: 1px dashed @border;
                    border-radius: 16px;
                    padding: 28px;
                    font-size: 12px;
                """))
                self.profiles_grid.addWidget(lbl, 0, 0)
                return

            max_cols = 3
            total_items = len(profiles)
            num_rows = (total_items + max_cols - 1) // max_cols

            for idx, profile in enumerate(profiles):
                username = profile.get("username", "")
                role = profile.get("role", "")
                row = idx // max_cols
                col = idx % max_cols

                # Center last row items
                if row == num_rows - 1:
                    items_on_last = total_items % max_cols
                    if items_on_last == 1 and col == 0:
                        col = 1

                profile_card = self.create_profile_card(username, role, idx)
                self.profiles_grid.addWidget(profile_card, row, col, Qt.AlignmentFlag.AlignCenter)

            try:
                self._user_loader.deleteLater()
            except Exception:
                pass

        self._user_loader.done.connect(on_users_loaded)
        self._user_loader.start()
    
    def create_profile_card(self, username, role, idx):
        """Create a compact modern profile card."""
        card_widget = QFrame()
        card_widget.setObjectName("profileCard")
        card_widget.setFixedSize(210, 188)
        card_widget.setCursor(Qt.CursorShape.PointingHandCursor)
        card_widget.setStyleSheet(theme_qss("""
            QFrame#profileCard {
                background: @surface_alt;
                border: 1.5px solid @border;
                border-radius: 20px;
            }
            QFrame#profileCard:hover {
                background: rgba(37, 99, 235, 0.075);
                border-color: @accent;
            }
        """))
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(22)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(15, 23, 42, 34))
        card_widget.setGraphicsEffect(shadow)

        remove_button = QPushButton("\u00d7", card_widget)
        remove_button.setToolTip("Bu cihazdan kald\u0131r")
        remove_button.setFixedSize(26, 26)
        remove_button.move(174, 10)
        remove_button.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_button.setStyleSheet(theme_qss("""
            QPushButton {
                background: @surface;
                color: @danger;
                border: 1px solid @border;
                border-radius: 13px;
                font-size: 17px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: @danger;
                color: white;
                border-color: @danger;
            }
            QToolTip {
                background-color: #0f172a;
                color: #ffffff;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 9px;
                font-size: 11px;
                font-weight: 600;
            }
        """))
        remove_button.clicked.connect(
            lambda checked=False, value=username: self._remove_local_profile(value)
        )
        remove_button.raise_()

        card_layout = QVBoxLayout(card_widget)
        card_layout.setContentsMargins(18, 18, 18, 16)
        card_layout.setSpacing(7)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        initials = username[:2].upper() if len(username) >= 2 else username.upper()

        safe_role = (role or "").strip().lower()
        if is_admin_role(role):
            avatar_color = DesignTokens.ACCENT
            badge_text = "Y\u00f6netici"
            badge_style = "background: rgba(37,99,235,0.12); color: #2563eb;"
        elif safe_role in ("muhasebe", "accounting", "finans"):
            avatar_color = tc("success")
            badge_text = "Finans"
            badge_style = f"background: {DesignTokens.STATUS_SUCCESS_BG}; color: {DesignTokens.STATUS_SUCCESS_FG};"
        elif safe_role in ("teknisyen", "technician"):
            avatar_color = tc("warning")
            badge_text = "Teknisyen"
            badge_style = f"background: {DesignTokens.STATUS_WARNING_BG}; color: {tc('warning')};"
        else:
            colors = ["#2563eb", "#7c3aed", "#0891b2", "#059669", "#d97706"]
            avatar_color = colors[idx % len(colors)]
            badge_text = role.strip() if role and role.strip() else "Kullan\u0131c\u0131"
            badge_style = "background: rgba(148,163,184,0.14); color: #64748b;"

        avatar_fg = "white"
        try:
            clr = QColor(avatar_color)
            if clr.isValid():
                lum = 0.299 * clr.red() + 0.587 * clr.green() + 0.114 * clr.blue()
                avatar_fg = "#0f172a" if lum > 175 else "white"
        except Exception:
            pass

        # Avatar circle
        avatar_frame = QFrame()
        avatar_frame.setObjectName("profileAvatar")
        avatar_frame.setFixedSize(70, 70)
        avatar_frame.setStyleSheet(f"""
            QFrame#profileAvatar {{
                background-color: {avatar_color};
                border-radius: 35px;
                border: 4px solid rgba(255,255,255,0.72);
            }}
        """)
        af_layout = QVBoxLayout(avatar_frame)
        af_layout.setContentsMargins(0, 0, 0, 0)
        lbl_initials = QLabel(initials)
        lbl_initials.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_initials.setFont(QFont("Segoe UI", 21, QFont.Weight.Bold))
        lbl_initials.setStyleSheet(f"color: {avatar_fg}; background: transparent; border: none;")
        af_layout.addWidget(lbl_initials)
        card_layout.addWidget(avatar_frame, alignment=Qt.AlignmentFlag.AlignCenter)

        # Username
        name_label = QLabel(username)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setWordWrap(True)
        name_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        name_label.setStyleSheet(theme_qss("color: @text; background: transparent;"))
        card_layout.addWidget(name_label)

        # Role badge
        badge = QLabel(badge_text)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedHeight(22)
        badge.setStyleSheet(f"{badge_style} border-radius: 8px; padding: 0 8px; font-size: 10px; font-weight: 600;")
        card_layout.addWidget(badge)

        def on_click(event):
            if event.button() == Qt.MouseButton.LeftButton:
                self.show_password_dialog(username)

        card_widget.mousePressEvent = on_click
        return card_widget

    def _remove_local_profile(self, username):
        username = str(username or "").strip()
        if not username:
            return
        reply = QMessageBox.question(
            self,
            "Yerel Profili Kald\u0131r",
            f"'{username}' hesab\u0131 bu bilgisayar\u0131n giri\u015f listesinden "
            "kald\u0131r\u0131lacak. Firma verileri silinmeyecek. Devam edilsin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            columns = set(self.db._get_table_columns("users"))
            updates = []
            values = []
            if "active" in columns:
                updates.append("active=0")
            if "is_active" in columns:
                updates.append("is_active=0")
            if "auto_login" in columns:
                updates.append("auto_login=0")
            if "remember_token" in columns:
                updates.append("remember_token=NULL")
            if not updates:
                raise RuntimeError("Kullanici pasiflestirme alanlari bulunamadi")
            values.append(username)
            self.db.cursor.execute(
                f"UPDATE users SET {', '.join(updates)} WHERE username=?",
                tuple(values),
            )
            self.db.conn.commit()
            if str(self.db.get_setting("last_login_user", "") or "") == username:
                self.db.set_setting("last_login_user", "")
            remaining = int(
                self.db.cursor.execute(
                    "SELECT COUNT(*) FROM users "
                    "WHERE LOWER(TRIM(username)) NOT IN ('admin','master') "
                    "AND COALESCE(active,1)=1"
                ).fetchone()[0]
                or 0
            )
            revoked = str(
                self.db.get_setting("server_access_revoked", "0") or "0"
            ) == "1"
            if remaining == 0 and revoked:
                self.db.set_setting("web_sync_tenant_id", "")
                self.db.set_setting("web_sync_enabled", "0")
                self.db.set_setting("server_access_revoked", "0")
                self.db.set_setting("server_access_revoked_authoritative", "0")
                WebSyncClient.clear_session(sync_session_path())
            self.auth_manager.clear_token()
            self.auth_manager.logout()
            self.refresh_user_list()
            show_success(
                self,
                "Yerel giri\u015f profili bu cihazdan kald\u0131r\u0131ld\u0131.",
            )
        except Exception as exc:
            logger.exception("Local login profile could not be removed")
            show_error(self, f"Profil kald\u0131r\u0131lamad\u0131: {exc}")

    def setup_login_logo(self):
        # Look for logo in various possible locations
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        candidates = [
             os.path.join(base_path, "assets", "ayec_logo.png"),
             os.path.join(os.getcwd(), "assets", "ayec_logo.png"),
        ]
        
        # Check for PyInstaller _MEIPASS
        if hasattr(sys, "_MEIPASS"):
            candidates.insert(0, os.path.join(sys._MEIPASS, "assets", "ayec_logo.png"))
        
        logo_path = None
        for cand in candidates:
             if os.path.exists(cand): logo_path = cand; break

        if logo_path:
            pixmap = QPixmap(logo_path)
            # Logoyu 80x80 boyutunda pürüzsüzce yükle
            self.logo_label.setPixmap(pixmap.scaled(80, 80, 
                                      Qt.AspectRatioMode.KeepAspectRatio, 
                                      Qt.TransformationMode.SmoothTransformation))
            # Logoyu tam daire yap ve beyaz köşeleri gizle
            self.logo_label.setStyleSheet(theme_qss("border-radius: 40px; background: transparent;"))
        else:
            logger.warning("Logo bulunamadı")
            # Fallback
            self.logo_label.setText("AYEC")
            self.logo_label.setStyleSheet(theme_qss("color: @danger; border: 2px solid @danger; border-radius: 40px;"))

    def show_password_dialog(self, username):
        """Show custom modern password input dialog"""
        dialog = ModernPasswordDialog(self, username)
        if dialog.exec() == QtDialog.DialogCode.Accepted:
            password = dialog.password
            remember = bool(getattr(dialog, "remember_me", False))
            self.handle_login_direct(username, password, remember)

    def handle_login_direct(self, username, password, remember=False):
        """Handle login from selected user dialog"""
        uname = (username or "").strip()
        if uname.lower() in ("admin", "master"):
            show_error(self, "Bu kullanıcı hesabı sadece Teknik Servis Modu için kullanılabilir.")
            return
        success, message = self.auth_manager.login(uname, password, remember=remember)
        
        if success:
            self._verify_server_access(uname, password, remember)
        else:
            show_error(self, message)

    def _verify_server_access(self, username, password, remember):
        tenant_id = str(
            self.db.get_setting("web_sync_tenant_id", "") or ""
        ).strip()
        if not tenant_id:
            self._complete_local_login(username, password, remember)
            return
        worker = _ServerAccessCheckWorker(
            username, password, tenant_id, self
        )
        worker.completed.connect(
            lambda reachable, allowed, message, payload: self._server_access_checked(
                username,
                password,
                remember,
                reachable,
                allowed,
                message,
                payload,
            )
        )
        worker.finished.connect(worker.deleteLater)
        worker.finished.connect(
            lambda: self._clear_server_access_worker(worker)
        )
        worker.start()
        self._server_access_worker = worker

    def _clear_server_access_worker(self, worker):
        if getattr(self, "_server_access_worker", None) is worker:
            self._server_access_worker = None

    def _server_access_checked(
        self,
        username,
        password,
        remember,
        reachable,
        allowed,
        message,
        payload,
    ):
        if reachable and allowed:
            self.db.set_setting("server_access_revoked", "0")
            self.db.set_setting("server_access_revoked_authoritative", "0")
            self._complete_local_login(username, password, remember)
            return

        cached_revoked = str(
            self.db.get_setting("server_access_revoked", "0") or "0"
        ) == "1"
        cached_authoritative = str(
            self.db.get_setting(
                "server_access_revoked_authoritative", "0"
            )
            or "0"
        ) == "1"
        if not reachable and not (cached_revoked and cached_authoritative):
            show_warning(
                self,
                "Sunucuya ula\u015f\u0131lamad\u0131. Son ge\u00e7erli yerel oturumla "
                "\u00e7evrimd\u0131\u015f\u0131 devam ediliyor.",
            )
            self._complete_local_login(username, password, remember)
            return

        self.db.set_setting("server_access_revoked", "1")
        self.db.set_setting("server_access_revoked_authoritative", "1")
        try:
            self.db.cursor.execute(
                "UPDATE users SET auto_login=0,remember_token=NULL WHERE username=?",
                (username,),
            )
            self.db.conn.commit()
        except Exception as exc:
            logger.warning(f"Could not revoke local auto-login: {exc}")
        self.auth_manager.logout()
        self.auth_manager.clear_token()
        denial = message or "Firma eri\u015fimi sunucu taraf\u0131ndan iptal edildi."
        show_error(self, denial)

    def _complete_local_login(self, username, password, remember):
        self._last_login_password = password
        if remember and self.auth_manager.remember_token:
            self.auth_manager.save_token(self.auth_manager.remember_token)
        try:
            if self.db and hasattr(self.db, "set_setting"):
                self.db.set_setting("last_login_user", username)
        except Exception as exc:
            logger.warning(f"Could not persist last_login_user: {exc}")
        self._pending_user = self.auth_manager.current_user
        self.start_opening()
    
    def create_input(self, placeholder, is_password=False):
        return _IconInput(placeholder, is_password=is_password)
    
    def create_button(self, text, color):
        """Create styled button"""
        button = QPushButton(text)
        button.setFixedHeight(50)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        
        button.setStyleSheet(theme_qss(f"""
            QPushButton {{
                background-color: {color};
                border: none;
                border-radius: 12px;
                color: white;
                letter-spacing: 0.5px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {color}; 
                border: 1px solid rgba(255,255,255,0.3);
            }}
            QPushButton:pressed {{
                background-color: {color}dd;
            }}
        """))
        
        return button
    
    def handle_register(self):
        """Handle registration"""
        self.open_account_wizard()
    
    def handle_login(self):
        """Handle login"""
        username = self.log_username.text().strip()
        password = self.log_password.text()
        
        if not username:
            show_error(self, "Kullanıcı adı boş olamaz!")
            self.log_username.setFocus()
            return
        
        if not password:
            show_error(self, "Şifre boş olamaz!")
            self.log_password.setFocus()
            return
        
        lowered = username.lower()
        if lowered in ("admin", "master"):
            show_error(self, "Bu kullanıcı hesabı sadece Teknik Servis Modu için kullanılabilir.")
            return
        remember = self.chk_remember.isChecked()
        success, message = self.auth_manager.login(username, password, remember)
        
        if success:
            self._verify_server_access(username, password, remember)
        else:
            show_error(self, message)

    def start_opening(self):
        try:
            if hasattr(self, "_user_loader") and self._user_loader and self._user_loader.isRunning():
                self._user_loader.wait(1000)
        except Exception:
            pass
        self.stack.setCurrentIndex(2)
        try:
            if hasattr(self, "lbl_opening_status"):
                self.lbl_opening_status.setText("Veriler hazırlanıyor...")
        except Exception as e:
            logger.warning(f"Opening status label update failed: {e}")

        try:
            self._init_worker = _FullInitWorker(self.db)
            w = self._init_worker
            w.finished.connect(w.deleteLater)
            app = QApplication.instance()
            if app:
                if not hasattr(app, "_active_threads"):
                    app._active_threads = set()
                app._active_threads.add(w)
                w.finished.connect(lambda: app._active_threads.discard(w) if app else None)

            def on_finished(ok, err):
                self._init_worker = None
                if ok:
                    user = self._pending_user or self.auth_manager.current_user
                    if not user:
                        show_error(self, "Giriş tamamlandı ancak kullanıcı bilgisi alınamadı.")
                        self.stack.setCurrentIndex(1)
                        return
                    
                    # Check if this is first login after setup
                    try:
                        first_login = self.db.get_setting("first_login_pending", "false")
                        if first_login.lower() in ("true", "1", "yes"):
                            # Clear the flag
                            self.db.set_setting("first_login_pending", "false")
                            # Show welcome message with AI assistant info
                            from src.ui.components.message_box import ModernMessage
                            ModernMessage.show_info(
                                self,
                                "Kurulumuz başarıyla tamamlandı!\n\nAYEC Pro Servis Yönetim Sistemi'ne hoş geldiniz!\n\nİpucu: AI Asistan ayarlarını şu adresten yapılandırabilirsiniz:\nAraçlar > Ayarlar > Entegrasyon & API\n\nİyi çalışmalar dileriz!",
                                "Hoş Geldiniz!",
                            )
                    except Exception as e:
                        logger.warning(f"First login check error: {e}")
                    
                    self.login_successful.emit(user)
                    self.accept()
                else:
                    show_error(self, err or "Başlatma sırasında bir hata oluştu.")
                    self.stack.setCurrentIndex(1)

            self._init_worker.completed.connect(on_finished)
            self._init_worker.start()
        except Exception as e:
            show_error(self, str(e))
            self.stack.setCurrentIndex(1)
    
    def closeEvent(self, event):
        try:
            if hasattr(self, "_user_loader") and self._user_loader and self._user_loader.isRunning():
                self._user_loader.wait(1000)
        except Exception:
            pass
        try:
            if self._init_worker and self._init_worker.isRunning():
                if not self._init_worker.wait(8000):
                    try:
                        self._init_worker.terminate()
                    except Exception as e:
                        logger.warning(f"Worker terminate failed: {e}")
                    self._init_worker.wait(1500)
        except Exception as e:
            logger.warning(f"Opening status label update failed: {e}")
        super().closeEvent(event)
    
    def open_remote_account_login(self):
        dialog = QtDialog(self)
        dialog.setWindowTitle("AYEC Pro - Sunucu Hesab\u0131")
        dialog.setModal(True)
        dialog.setMinimumWidth(460)
        dialog.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)

        title = QLabel("Kay\u0131tl\u0131 Hesab\u0131m Var")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        layout.addWidget(title)

        description = QLabel(
            "Web veya mobil uygulamada kulland\u0131\u011f\u0131n\u0131z hesap bilgileriyle giri\u015f yap\u0131n."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        form = QFormLayout()
        identifier = QLineEdit()
        identifier.setPlaceholderText("Kullan\u0131c\u0131 ad\u0131 veya e-posta")
        password = QLineEdit()
        password.setEchoMode(QLineEdit.EchoMode.Password)
        password.setPlaceholderText("\u015eifre")
        tenant_id = QLineEdit()
        tenant_id.setPlaceholderText("Bo\u015f b\u0131rakabilirsiniz")
        form.addRow("Kullan\u0131c\u0131 / E-posta:", identifier)
        form.addRow("\u015eifre:", password)
        form.addRow("Firma Kodu:", tenant_id)
        layout.addLayout(form)

        remember = QCheckBox("Bu bilgisayarda oturumu g\u00fcvenli olarak hat\u0131rla")
        remember.setChecked(True)
        layout.addWidget(remember)

        status = QLabel("")
        status.setWordWrap(True)
        layout.addWidget(status)

        actions = QHBoxLayout()
        actions.addStretch()
        cancel_button = QPushButton("Vazge\u00e7")
        login_button = QPushButton("Giri\u015f Yap")
        login_button.setDefault(True)
        actions.addWidget(cancel_button)
        actions.addWidget(login_button)
        layout.addLayout(actions)

        cancel_button.clicked.connect(dialog.reject)

        def begin_login():
            user_text = identifier.text().strip()
            password_text = password.text()
            if not user_text or not password_text:
                status.setText("Kullan\u0131c\u0131 ad\u0131/e-posta ve \u015fifre zorunludur.")
                return
            login_button.setEnabled(False)
            cancel_button.setEnabled(False)
            status.setText("Sunucu hesab\u0131 do\u011frulan\u0131yor...")
            worker = _RemoteAccountLoginWorker(
                user_text,
                password_text,
                tenant_id.text().strip(),
                dialog,
            )
            self._remote_login_worker = worker

            def completed(ok, result):
                login_button.setEnabled(True)
                cancel_button.setEnabled(True)
                if not ok:
                    status.setText(
                        str(dict(result or {}).get("error") or "Giri\u015f ba\u015far\u0131s\u0131z.")
                    )
                    password.selectAll()
                    password.setFocus()
                    return
                try:
                    self._finish_remote_account_login(
                        dict(result or {}),
                        password_text,
                        bool(remember.isChecked()),
                    )
                except Exception as exc:
                    logger.exception("Remote desktop account setup failed")
                    status.setText(f"Hesap yerelde haz\u0131rlanamad\u0131: {exc}")
                    return
                dialog.accept()
                QTimer.singleShot(0, self.start_opening)

            worker.completed.connect(completed)
            worker.finished.connect(worker.deleteLater)
            worker.start()

        login_button.clicked.connect(begin_login)
        password.returnPressed.connect(begin_login)
        dialog.exec()

    def _finish_remote_account_login(self, result, password, remember):
        remote_user = dict(result.get("user") or {})
        username = str(remote_user.get("username") or "").strip()
        if not username:
            raise ValueError("Sunucu kullan\u0131c\u0131 bilgisi eksik.")

        if hasattr(self.db, "ensure_full_initialized"):
            self.db.ensure_full_initialized()
        user_columns = set(self.db._get_table_columns("users"))
        full_name = str(remote_user.get("full_name") or username).strip()
        local_user = {
            "username": username,
            "password": self.auth_manager.hash_password(password),
            "email": str(remote_user.get("email") or "").strip() or None,
            "role": str(remote_user.get("role") or "User"),
            "full_name": full_name,
            "name": full_name,
            "active": 1,
            "is_active": 1,
            "interface_edit_access": int(bool(remote_user.get("interface_edit_access"))),
            "permissions": remote_user.get("permissions") or None,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        existing = self.db.cursor.execute(
            "SELECT id FROM users WHERE username=?",
            (username,),
        ).fetchone()
        if existing:
            user_id = existing["id"] if hasattr(existing, "keys") else existing[0]
            updates = {key: value for key, value in local_user.items() if key in user_columns and key != "username"}
            setters = ", ".join(f'"{key}"=?' for key in updates)
            if setters:
                self.db.cursor.execute(
                    f'UPDATE users SET {setters} WHERE id=?',
                    (*updates.values(), user_id),
                )
        else:
            values = {key: value for key, value in local_user.items() if key in user_columns}
            columns = ", ".join(f'"{key}"' for key in values)
            marks = ", ".join("?" for _ in values)
            self.db.cursor.execute(
                f'INSERT INTO users ({columns}) VALUES ({marks})',
                tuple(values.values()),
            )

        tenant = str(remote_user.get("tenant_id") or "").strip()
        company = str(remote_user.get("company_name") or "").strip()
        self.db.set_setting("setup_completed", "true")
        self.db.set_setting("web_sync_enabled", "1")
        self.db.set_setting("web_sync_url", configured_sync_url())
        self.db.set_setting("web_sync_tenant_id", tenant)
        self.db.set_setting("web_is_control_admin", "1" if remote_user.get("is_control_admin") else "0")
        self.db.set_setting(
            "web_can_access_control_center",
            "1" if remote_user.get("can_access_control_center") else "0",
        )
        self.db.set_setting("last_login_user", username)
        if company:
            self.db.set_setting("company_name", company)
        self.db.conn.commit()

        success, message = self.auth_manager.login(username, password, remember=remember)
        if not success:
            raise ValueError(message)
        if remember and self.auth_manager.remember_token:
            self.auth_manager.save_token(self.auth_manager.remember_token)
        self._last_login_password = password
        self._pending_user = dict(self.auth_manager.current_user or {})
        self._pending_user.update(
            {
                "tenant_id": tenant,
                "company_name": company,
                "remote_account": True,
                "is_control_admin": bool(remote_user.get("is_control_admin")),
                "can_access_control_center": bool(remote_user.get("can_access_control_center")),
            }
        )

    def open_account_wizard(self):
        """Open the personnel/user creation dialog for login accounts."""
        try:
            from src.ui.pages.settings_widgets.user_management_dialogs import NewUserDialog
            dialog = NewUserDialog(self.db, parent=self)
            if dialog.exec() == QtDialog.DialogCode.Accepted:
                self.refresh_user_list()
                show_success(self, "Kullanıcı hesabı başarıyla oluşturuldu!")
                self.stack.setCurrentIndex(1)
        except Exception as e:
            import traceback
            traceback.print_exc()
            show_error(self, f"Personel ekleme dialogu açılamadı: {e}")

    def open_company_wizard(self):
        try:
            from src.ui.dialogs.setup_wizard import SetupWizardDialog
            wizard = SetupWizardDialog(self.db, self)
            if wizard.exec() == QtDialog.DialogCode.Accepted:
                self._setup_done = True
                self.refresh_user_list()
                show_success(self, "İşlem başarıyla tamamlandı!")
                self.stack.setCurrentIndex(1)
        except Exception as e:
            import traceback
            traceback.print_exc()
            show_error(self, f"Sihirbaz Hatası: {e}")

    def _deferred_init(self):
        """Pencere görüntülendikten sonra ağır DB işlemlerini yükle (freeze önleme)"""
        try:
            setup_value = self.db.get_setting("setup_completed", "")
            if not setup_value:
                setup_value = self.db.get_setting("setup_complete", "0")
            self._setup_done = str(setup_value or "").strip().lower() in ("1", "true", "yes", "ok")
        except Exception as e:
            logger.warning(f"Setup completion check failed: {e}")

        self.refresh_user_list()
        if not self._setup_done and not self.fetch_known_usernames():
            self.stack.setCurrentIndex(0)
        self.check_auto_login()

    def check_auto_login(self):
        """Check for saved token and auto-login"""
        token = self.auth_manager.get_saved_token()
        if not token or not self.auth_manager.auto_login(token):
            return

        tenant_id = str(
            self.db.get_setting("web_sync_tenant_id", "") or ""
        ).strip()
        if tenant_id:
            current_user = dict(self.auth_manager.current_user or {})
            username = str(current_user.get("username") or "").strip()
            if not username:
                self.auth_manager.logout()
                return
            worker = _RememberedServerAccessWorker(
                username,
                tenant_id,
                self,
            )
            worker.completed.connect(self._remembered_server_access_checked)
            worker.finished.connect(worker.deleteLater)
            worker.finished.connect(
                lambda: self._clear_remembered_server_worker(worker)
            )
            self._remembered_server_worker = worker
            worker.start()
            return
        self._pending_user = self.auth_manager.current_user
        self.start_opening()

    def _clear_remembered_server_worker(self, worker):
        if getattr(self, "_remembered_server_worker", None) is worker:
            self._remembered_server_worker = None

    def _remembered_server_access_checked(self, reachable, allowed, message):
        if allowed:
            self.db.set_setting("server_access_revoked", "0")
            self.db.set_setting("server_access_revoked_authoritative", "0")
            self._pending_user = self.auth_manager.current_user
            self.start_opening()
            return

        cached_revoked = str(
            self.db.get_setting("server_access_revoked", "0") or "0"
        ) == "1"
        cached_authoritative = str(
            self.db.get_setting(
                "server_access_revoked_authoritative", "0"
            )
            or "0"
        ) == "1"
        if not reachable and not (cached_revoked and cached_authoritative):
            show_warning(
                self,
                "Sunucuya ula\u015f\u0131lamad\u0131. Hat\u0131rlanan son ge\u00e7erli "
                "oturumla \u00e7evrimd\u0131\u015f\u0131 devam ediliyor.",
            )
            self._pending_user = self.auth_manager.current_user
            self.start_opening()
            return

        self.auth_manager.logout()
        self.auth_manager.clear_token()
        show_info(
            self,
            message
            or "Beni Hat\u0131rla oturumunun s\u00fcresi doldu. L\u00fctfen parolan\u0131zla "
            "yeniden giri\u015f yap\u0131n.",
        )
    
    # ── Title bar drag helpers ──────────────────────────────────────────────
    def _tb_mouse_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def _tb_mouse_move(self, event):
        if self.dragging and event.buttons() == Qt.MouseButton.LeftButton:
            if self.isMaximized():
                self.showNormal()
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def _tb_mouse_release(self, event):
        self.dragging = False

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    # Mouse events for dragging
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        self.dragging = False


from src.ui.modern_login_dialogs import (
    ModernPasswordDialog,
)
