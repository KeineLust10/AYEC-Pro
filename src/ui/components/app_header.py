import logging
import os

from PyQt6.QtCore import Qt, QPoint, QSize
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QStyle, QWidget

from src.ui.components.notification_center import NotificationBell
from src.ui.widgets.breadcrumb import Breadcrumb
from src.utils.auth_manager import AuthManager
from src.utils.theme_colors import theme_qss
from src.utils.theme_manager import ThemeManager

logger = logging.getLogger(__name__)


class AppHeader(QWidget):
    """
    Uygulamanin ust navigasyon ve aksiyon cubugu.
    Breadcrumb, bildirimler, tema ve dil kontrollerini barindirir.
    Frameless pencerede başlık çubuğu görevini de üstlenir (sürükleme + pencere butonları).
    """

    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self.db = main_window.db

        self.setFixedHeight(50)
        self.setObjectName("AppHeader")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._drag_active = False
        self._drag_pos = QPoint()

        self.init_ui()
        self.apply_theme_styles()

    # ── Pencere sürükleme ────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            mw = self.main_window
            if hasattr(mw, "start_window_drag"):
                mw.start_window_drag(event.globalPosition().toPoint())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        mw = self.main_window
        if hasattr(mw, "update_window_drag"):
            mw.update_window_drag(event.globalPosition().toPoint())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        mw = self.main_window
        if hasattr(mw, "stop_window_drag"):
            mw.stop_window_drag()
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Başlık çubuğuna çift tıkla → maximize/restore"""
        if event.button() == Qt.MouseButton.LeftButton:
            mw = self.main_window
            if hasattr(mw, "window_maximize_restore"):
                mw.window_maximize_restore()
        super().mouseDoubleClickEvent(event)

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 8, 0)
        layout.setSpacing(10)

        # ── Logo / İkon ──────────────────────────────────────────────────────
        self.lbl_logo = QLabel()
        self.lbl_logo.setFixedSize(28, 28)
        self.lbl_logo.setScaledContents(True)
        _icon_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "assets", "app_icon.png"
        )
        if os.path.exists(_icon_path):
            self.lbl_logo.setPixmap(QPixmap(_icon_path))
        else:
            self.lbl_logo.setText("⚙")
            self.lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_logo)

        # ── Uygulama adı ─────────────────────────────────────────────────────
        self.lbl_app_name = QLabel("AYEC Pro")
        self.lbl_app_name.setObjectName("AppNameLabel")
        self.lbl_app_name.setStyleSheet(
            "font-size: 13px; font-weight: 800; letter-spacing: 0.5px;"
        )
        layout.addWidget(self.lbl_app_name)

        layout.addSpacing(4)

        self.breadcrumb = Breadcrumb(self.main_window)
        layout.addWidget(self.breadcrumb, 1)

        self.notification_bell = NotificationBell()
        layout.addWidget(self.notification_bell)

        self.btn_interface_edit = QPushButton("Arayüz Düzenle")
        self.btn_interface_edit.setObjectName("HeaderActionButton")
        self.btn_interface_edit.setFixedHeight(34)
        self.btn_interface_edit.clicked.connect(self.main_window.open_interface_layout_editor)
        if not self._can_show_interface_editor():
            self.btn_interface_edit.hide()
        layout.addWidget(self.btn_interface_edit)

        self.btn_settings = QPushButton()
        self.btn_settings.setObjectName("HeaderIconButton")
        self.btn_settings.setFixedSize(34, 34)
        self.btn_settings.setToolTip("Sistem Ayarlari")
        self.btn_settings.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        self.btn_settings.setIconSize(self.btn_settings.size() * 0.52)
        self.btn_settings.clicked.connect(lambda: self.main_window.on_menu_click(130))
        layout.addWidget(self.btn_settings)

        self.btn_theme_toggle = QPushButton()
        self.btn_theme_toggle.setObjectName("HeaderIconButton")
        self.btn_theme_toggle.setFixedSize(34, 34)
        self.btn_theme_toggle.clicked.connect(self.main_window.toggle_theme_from_header)
        layout.addWidget(self.btn_theme_toggle)

        self.cmb_theme = QComboBox()
        self.cmb_theme.setObjectName("HeaderCombo")
        self.cmb_theme.setMinimumWidth(120)
        self.cmb_theme.setMaximumWidth(180)
        self.cmb_theme.addItems(ThemeManager.get_available_themes(self.db))
        self.cmb_theme.currentTextChanged.connect(self.main_window.on_header_theme_changed)
        layout.addWidget(self.cmb_theme)

        self.cmb_language = QComboBox()
        self.cmb_language.setObjectName("HeaderCombo")
        self.cmb_language.setFixedWidth(70)
        self.cmb_language.addItems(["TR", "EN"])
        self.cmb_language.currentTextChanged.connect(self.main_window.on_language_changed)
        layout.addWidget(self.cmb_language)

        # ── Pencere kontrol butonları (Frameless) ────────────────────────────
        layout.addSpacing(6)

        self.btn_minimize = QPushButton("─")
        self.btn_minimize.setObjectName("WinMinBtn")
        self.btn_minimize.setFixedSize(30, 30)
        self.btn_minimize.setToolTip("Küçült")
        self.btn_minimize.clicked.connect(self.main_window.window_minimize)
        layout.addWidget(self.btn_minimize)

        self.btn_maximize = QPushButton("□")
        self.btn_maximize.setObjectName("WinMaxBtn")
        self.btn_maximize.setFixedSize(30, 30)
        self.btn_maximize.setToolTip("Büyüt / Geri Al")
        self.btn_maximize.clicked.connect(self.main_window.window_maximize_restore)
        layout.addWidget(self.btn_maximize)

        self.btn_close = QPushButton("✕")
        self.btn_close.setObjectName("WinCloseBtn")
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.setToolTip("Kapat")
        self.btn_close.clicked.connect(self.main_window.window_close)
        layout.addWidget(self.btn_close)

    def _button_style(self):
        return theme_qss(
            """
            QPushButton#HeaderIconButton {
                background-color: @surface_alt;
                color: @text;
                border: 1px solid @border;
                border-radius: 17px;
                font-size: 12px;
                font-weight: 700;
                padding: 0px;
            }
            QPushButton#HeaderIconButton:hover {
                background-color: @window;
                border-color: @accent;
            }
            """
        )

    def _action_button_style(self):
        return theme_qss(
            """
            QPushButton#HeaderActionButton {
                background-color: @surface_alt;
                color: @text;
                border: 1px solid @border;
                border-radius: 10px;
                font-size: 12px;
                font-weight: 800;
                padding: 0 14px;
            }
            QPushButton#HeaderActionButton:hover {
                background-color: @window;
                border-color: @accent;
            }
            """
        )

    def _can_show_interface_editor(self):
        try:
            auth = AuthManager(self.db)
            auth.current_user = getattr(self.main_window, "current_user", None) or getattr(self.main_window, "user_data", None)
            return auth.has_interface_edit_permission()
        except Exception as e:
            logger.warning("Interface editor permission check failed: %s", e)
            return False

    def _combo_style(self):
        return theme_qss(
            """
            QComboBox#HeaderCombo {
                background-color: @surface_alt;
                color: @text;
                border: 1px solid @border;
                border-radius: 10px;
                padding: 6px 12px;
                min-height: 18px;
            }
            QComboBox#HeaderCombo:hover {
                border-color: @accent;
            }
            QComboBox#HeaderCombo::drop-down {
                border: none;
                width: 22px;
            }
            QComboBox#HeaderCombo QAbstractItemView {
                background-color: @surface;
                color: @text;
                border: 1px solid @border;
                selection-background-color: @selection_bg;
                selection-color: @selection_text;
            }
            """
        )

    def apply_theme_styles(self):
        self.setStyleSheet(
            theme_qss(
                """
                QWidget#AppHeader {
                    background-color: @surface;
                    border-bottom: 1px solid @border;
                }
                """
            )
        )
        self.lbl_app_name.setStyleSheet(
            theme_qss(
                "QLabel#AppNameLabel { color: @text; font-size: 13px; font-weight: 800; letter-spacing: 0.5px; }"
            )
        )
        self.btn_settings.setStyleSheet(self._button_style())
        self.btn_theme_toggle.setStyleSheet(self._button_style())
        self.btn_interface_edit.setStyleSheet(self._action_button_style())
        self.cmb_theme.setStyleSheet(self._combo_style())
        self.cmb_language.setStyleSheet(self._combo_style())
        self.btn_minimize.setStyleSheet(self._win_btn_style("minimize"))
        self.btn_maximize.setStyleSheet(self._win_btn_style("maximize"))
        self.btn_close.setStyleSheet(self._win_btn_style("close"))

    def _win_btn_style(self, kind: str) -> str:
        if kind == "close":
            return """
                QPushButton#WinCloseBtn {
                    background: transparent;
                    color: #aaaaaa;
                    border: none;
                    border-radius: 15px;
                    font-size: 13px;
                    font-weight: 700;
                }
                QPushButton#WinCloseBtn:hover {
                    background: #e74c3c;
                    color: #ffffff;
                }
                QPushButton#WinCloseBtn:pressed { background: #c0392b; }
            """
        elif kind == "maximize":
            return """
                QPushButton#WinMaxBtn {
                    background: transparent;
                    color: #aaaaaa;
                    border: none;
                    border-radius: 15px;
                    font-size: 13px;
                }
                QPushButton#WinMaxBtn:hover {
                    background: #2ecc71;
                    color: #ffffff;
                }
                QPushButton#WinMaxBtn:pressed { background: #27ae60; }
            """
        else:
            return """
                QPushButton#WinMinBtn {
                    background: transparent;
                    color: #aaaaaa;
                    border: none;
                    border-radius: 15px;
                    font-size: 15px;
                    font-weight: 300;
                }
                QPushButton#WinMinBtn:hover {
                    background: #f39c12;
                    color: #ffffff;
                }
                QPushButton#WinMinBtn:pressed { background: #d68910; }
            """

    def sync_theme_controls(self, current_theme):
        current_theme = ThemeManager.normalize_theme_name(current_theme)
        themes = ThemeManager.get_available_themes(self.db)
        try:
            idx = themes.index(current_theme)
        except ValueError:
            idx = -1
        next_theme = themes[(idx + 1) % len(themes)] if themes else current_theme
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload)
        self.btn_theme_toggle.setIcon(icon)
        self.btn_theme_toggle.setIconSize(self.btn_theme_toggle.size() * 0.48)
        self.btn_theme_toggle.setText("")
        self.btn_theme_toggle.setToolTip(f"Sonraki tema: {next_theme}")

        idx = self.cmb_theme.findText(current_theme)
        if idx >= 0:
            self.cmb_theme.blockSignals(True)
            self.cmb_theme.setCurrentIndex(idx)
            self.cmb_theme.blockSignals(False)
