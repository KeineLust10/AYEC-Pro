import logging
import os

from PyQt6.QtCore import Qt, QPoint, QSize, QRect, QEvent
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import QApplication, QComboBox, QHBoxLayout, QLabel, QPushButton, QStyle, QWidget

from src.ui.components.notification_center import NotificationBell, NotificationPanel
from src.ui.widgets.breadcrumb import Breadcrumb
from src.utils.auth_manager import AuthManager
from src.utils.appearance_mode import AppearanceModeManager
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
            self.lbl_logo.setText("*")
            self.lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_logo)

        # ── Uygulama adı ─────────────────────────────────────────────────────
        self.lbl_app_name = QLabel("AYEC Pro")
        self.lbl_app_name.setObjectName("AppNameLabel")
        self.lbl_app_name.setStyleSheet("font-size: 13px; font-weight: 800;")
        layout.addWidget(self.lbl_app_name)

        layout.addSpacing(4)

        self.breadcrumb = Breadcrumb(self.main_window)
        layout.addWidget(self.breadcrumb, 1)

        # --- Update Button ---
        self.btn_update = QPushButton("G\u00fcncelleme")
        self.btn_update.setObjectName("UpdateHeaderBtn")
        self.btn_update.setFixedHeight(34)
        self.btn_update.hide()
        self.btn_update.clicked.connect(self.on_update_clicked)
        layout.addWidget(self.btn_update)

        from PyQt6.QtCore import QTimer
        self.pulse_timer = QTimer(self)
        self.pulse_timer.timeout.connect(self.pulse_update_button)
        self.pulse_val = 0
        self.pulse_dir = 1
        self.pulse_timer.start(50)

        self.btn_web_sync = QPushButton("\u21bb")
        self.btn_web_sync.setObjectName("HeaderIconButton")
        self.btn_web_sync.setFixedSize(34, 34)
        self.btn_web_sync.setToolTip("Web ve mobil verilerini \u015fimdi senkronize et")
        self.btn_web_sync.clicked.connect(
            lambda: self.main_window.start_web_sync(silent=False)
        )
        layout.addWidget(self.btn_web_sync)

        self.notification_bell = NotificationBell()
        self.notification_bell.clicked.connect(self.open_notification_panel)
        layout.addWidget(self.notification_bell)
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

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
        self.btn_settings.setToolTip("Sistem Ayarlar\u0131")
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



        # ── Pencere kontrol butonları (Frameless) ────────────────────────────
        layout.addSpacing(6)

        self.btn_minimize = QPushButton("-")
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

        self.btn_close = QPushButton("x")
        self.btn_close.setObjectName("WinCloseBtn")
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.setToolTip("Kapat")
        self.btn_close.clicked.connect(self.main_window.window_close)
        layout.addWidget(self.btn_close)

    def set_web_sync_state(self, running=False, success=None, detail=""):
        if not hasattr(self, "btn_web_sync"):
            return
        self.btn_web_sync.setEnabled(not running)
        if running:
            self.btn_web_sync.setText("...")
            self.btn_web_sync.setToolTip("Web ve mobil verileri senkronize ediliyor")
        else:
            self.btn_web_sync.setText("\u21bb")
            if success is True:
                self.btn_web_sync.setToolTip("Senkronizasyon tamamland\u0131")
            elif success is False:
                self.btn_web_sync.setToolTip(detail or "Senkronizasyon ba\u015far\u0131s\u0131z")
            else:
                self.btn_web_sync.setToolTip("Web ve mobil verilerini \u015fimdi senkronize et")

    def _button_style(self):
        if self._is_classic_appearance():
            return theme_qss("""
            QPushButton#HeaderIconButton,
            QPushButton#HeaderIconButton:enabled {
                background-color: @surface;
                color: @text;
                border: 1px solid @border;
                border-radius: 0px;
                font-size: 12px;
                font-weight: 700;
                padding: 0px;
            }
            QPushButton#HeaderIconButton:hover,
            QPushButton#HeaderIconButton:hover:enabled {
                background-color: @surface_alt;
                color: @text;
                border-color: @accent;
            }
            QPushButton#HeaderIconButton:pressed {
                background-color: @selection_bg;
                color: @selection_text;
            }
            """)
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
        if self._is_classic_appearance():
            return theme_qss("""
            QPushButton#HeaderActionButton,
            QPushButton#HeaderActionButton:enabled {
                background-color: @surface;
                color: @text;
                border: 1px solid @border;
                border-radius: 0px;
                font-size: 11px;
                font-weight: 800;
                padding: 0 10px;
            }
            QPushButton#HeaderActionButton:hover,
            QPushButton#HeaderActionButton:hover:enabled {
                background-color: @surface_alt;
                color: @text;
                border-color: @accent;
            }
            QPushButton#HeaderActionButton:pressed {
                background-color: @selection_bg;
                color: @selection_text;
            }
            """)
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

    def _is_classic_appearance(self):
        app = QApplication.instance()
        if app and app.property("appearanceMode") == "classic":
            return True
        try:
            return AppearanceModeManager.is_classic(self.db)
        except Exception:
            return False

    def open_notification_panel(self):
        try:
            panel = getattr(self, "_notification_panel", None)
            if panel is not None and panel.isVisible():
                # Keep one popup instance and hide it. Recreating a Qt.Popup
                # during the same mouse event can make the panel reopen.
                panel.hide()
                return

            if panel is None:
                panel = NotificationPanel(self.db, self)
                panel.link_triggered.connect(self._handle_notification_link)
                panel.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
                self._notification_panel = panel
            panel.show_at(self.notification_bell.mapToGlobal(self.notification_bell.rect().topLeft()))
            if hasattr(self.main_window, "refresh_notification_bell"):
                self.main_window.refresh_notification_bell()
        except Exception as e:
            logger.warning("Notification panel open failed: %s", e, exc_info=True)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress:
            panel = getattr(self, "_notification_panel", None)
            if panel is not None and panel.isVisible():
                point = event.globalPosition().toPoint()
                bell_pos = self.notification_bell.mapToGlobal(QPoint(0, 0))
                bell_rect = QRect(bell_pos, self.notification_bell.size())
                if not panel.geometry().contains(point) and not bell_rect.contains(point):
                    panel.hide()
        return super().eventFilter(obj, event)

    def _handle_notification_link(self, link_id):
        try:
            if not link_id:
                return
            target, _, raw_id = str(link_id).partition(":")
            page_map = {
                "stock": 50,
                "customer": 20,
                "service": 40,
                "loan": 85,
                "finance": 90,
                "maintenance": 45,
                "vehicle": 45,
            }
            page_id = page_map.get(target.lower())
            if page_id is not None:
                self.main_window.on_menu_click(page_id)
        except Exception as e:
            logger.warning("Notification link handling failed: %s", e, exc_info=True)

    def _combo_style(self):
        if self._is_classic_appearance():
            return theme_qss("""
            QComboBox#HeaderCombo {
                background-color: @surface;
                color: @text;
                border: 1px solid @border;
                border-radius: 0px;
                padding: 3px 8px;
                min-height: 20px;
            }
            QComboBox#HeaderCombo:hover {
                border-color: @accent;
            }
            QComboBox#HeaderCombo::drop-down {
                border-left: 1px solid @border;
                width: 22px;
            }
            QComboBox#HeaderCombo QAbstractItemView {
                background-color: @surface;
                color: @text;
                border: 1px solid @border;
                selection-background-color: @selection_bg;
                selection-color: @selection_text;
            }
            QComboBox#HeaderCombo QAbstractItemView::item {
                color: @text;
                background-color: transparent;
                padding: 4px;
            }
            QComboBox#HeaderCombo QAbstractItemView::item:hover,
            QComboBox#HeaderCombo QAbstractItemView::item:selected {
                background-color: @selection_bg;
                color: @selection_text;
            }
            """)
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
            QComboBox#HeaderCombo QAbstractItemView::item {
                color: @text;
                background-color: transparent;
                padding: 4px;
            }
            QComboBox#HeaderCombo QAbstractItemView::item:hover,
            QComboBox#HeaderCombo QAbstractItemView::item:selected {
                background-color: @selection_bg;
                color: @selection_text;
            }
            """
        )

    def apply_theme_styles(self):
        classic = self._is_classic_appearance()
        for widget in (
            self.btn_settings,
            self.btn_theme_toggle,
            self.btn_web_sync,
            self.btn_interface_edit,
            self.btn_minimize,
            self.btn_maximize,
            self.btn_close,
            self.cmb_theme,
        ):
            try:
                widget.setProperty("skipThemeTransform", False)
            except Exception:
                pass
        if classic:
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
        else:
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
            (
                theme_qss("QLabel#AppNameLabel { color: @text; font-size: 12px; font-weight: 800; }")
                if classic
                else theme_qss("QLabel#AppNameLabel { color: @text; font-size: 13px; font-weight: 800; }")
            )
        )
        self.btn_settings.setStyleSheet(self._button_style())
        self.btn_theme_toggle.setStyleSheet(self._button_style())
        self.btn_web_sync.setStyleSheet(self._button_style())
        self.btn_interface_edit.setStyleSheet(self._action_button_style())
        self.cmb_theme.setStyleSheet(self._combo_style())
        self.btn_minimize.setStyleSheet(self._win_btn_style("minimize"))
        self.btn_maximize.setStyleSheet(self._win_btn_style("maximize"))
        self.btn_close.setStyleSheet(self._win_btn_style("close"))

    def _win_btn_style(self, kind: str) -> str:
        if self._is_classic_appearance():
            hover = "@surface_alt"
            if kind == "close":
                hover = "@danger_bg"
            return theme_qss(f"""
                QPushButton {{
                    background: @surface;
                    color: @text;
                    border: 1px solid @border;
                    border-radius: 0px;
                    font-size: 12px;
                    font-weight: 700;
                }}
                QPushButton:hover {{
                    background: {hover};
                    color: @text;
                    border-color: @accent;
                }}
                QPushButton:pressed {{ background: @selection_bg; }}
            """)
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

    def show_update_button(self, version, status, progress=0):
        self.btn_update.update_status = status
        self.btn_update.new_version = version
        if status == "downloading":
            self.btn_update.setText(f"\u23f3 \u0130ndiriliyor %{progress}")
            self.btn_update.setToolTip(f"Yeni g\u00fcncelleme (v{version}) arka planda indiriliyor...")
        elif status == "ready":
            self.btn_update.setText("\ud83c\udf89 G\u00fcncellemeyi Y\u00fckle")
            self.btn_update.setToolTip("Yeni s\u00fcr\u00fcm y\u00fcklenmeye haz\u0131r. Y\u00fcklemek i\u00e7in t\u0131klay\u0131n!")
        else:
            self.btn_update.setText(f"\ud83d\udce5 G\u00fcncelleme Var (v{version})")
            self.btn_update.setToolTip(f"Yeni s\u00fcr\u00fcm (v{version}) bulundu.")
        self.btn_update.show()

    def pulse_update_button(self):
        if not hasattr(self, "btn_update") or not self.btn_update.isVisible():
            return
        self.pulse_val += 2 * self.pulse_dir
        if self.pulse_val >= 40:
            self.pulse_dir = -1
        elif self.pulse_val <= 0:
            self.pulse_dir = 1

        alpha = 180 + self.pulse_val
        status = getattr(self.btn_update, "update_status", "found")
        if status == "downloading":
            self.btn_update.setStyleSheet(theme_qss(f"""
                QPushButton#UpdateHeaderBtn {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(52, 152, 219, {alpha/255.0:.2f}), stop:1 rgba(41, 128, 185, {alpha/255.0:.2f}));
                    color: white;
                    border: 1px solid rgba(41, 128, 185, 0.8);
                    border-radius: 10px;
                    font-size: 11px;
                    font-weight: bold;
                    padding: 0 12px;
                }}
            """))
        elif status == "ready":
            self.btn_update.setStyleSheet(theme_qss(f"""
                QPushButton#UpdateHeaderBtn {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(46, 204, 113, {alpha/255.0:.2f}), stop:1 rgba(39, 174, 96, {alpha/255.0:.2f}));
                    color: white;
                    border: 1px solid rgba(39, 174, 96, 0.8);
                    border-radius: 10px;
                    font-size: 11px;
                    font-weight: bold;
                    padding: 0 12px;
                }}
            """))
        else: # found
            self.btn_update.setStyleSheet(theme_qss(f"""
                QPushButton#UpdateHeaderBtn {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(230, 126, 34, {alpha/255.0:.2f}), stop:1 rgba(241, 196, 15, {alpha/255.0:.2f}));
                    color: #0f172a;
                    border: 1px solid rgba(230, 126, 34, 0.8);
                    border-radius: 10px;
                    font-size: 11px;
                    font-weight: 800;
                    padding: 0 12px;
                }}
            """))

    def on_update_clicked(self):
        if hasattr(self.main_window, "update_manager"):
            status = getattr(self.btn_update, "update_status", "found")
            if status == "ready":
                self.main_window.update_manager.install_update()

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
