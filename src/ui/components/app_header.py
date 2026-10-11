import logging
import os

from PyQt6.QtCore import Qt, QPoint, QSize, QRect, QEvent
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPainter, QFont
from PyQt6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QPushButton, QStyle, QToolButton, QWidget, QMenu

from src.ui.components.notification_center import NotificationBell, NotificationPanel
from src.ui.widgets.breadcrumb import Breadcrumb
from src.ui.widgets.modern_inputs import ModernComboBox
from src.utils.auth_manager import AuthManager
from src.utils.appearance_mode import AppearanceModeManager
from src.utils.theme_colors import theme_qss, tc
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

        self.setFixedHeight(70)
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

    def _go_back(self):
        if hasattr(self.main_window, "navigate_back"):
            self.main_window.navigate_back()

    def set_back_enabled(self, enabled):
        if hasattr(self, "btn_back"):
            self.btn_back.setEnabled(bool(enabled))

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
        layout.setContentsMargins(8, 0, 6, 0)
        layout.setSpacing(6)

        # ── Logo / İkon ──────────────────────────────────────────────────────
        self.lbl_logo = QLabel()
        self.lbl_logo.setFixedSize(28, 28)
        self.lbl_logo.setScaledContents(True)
        _icon_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "assets", "app_icon.png"
        )
        window_icon = self.main_window.windowIcon()
        if not window_icon.isNull():
            self.lbl_logo.setPixmap(window_icon.pixmap(QSize(22, 22)))
        elif os.path.exists(_icon_path):
            self.lbl_logo.setPixmap(QPixmap(_icon_path))
        else:
            self.lbl_logo.setText("*")
            self.lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_logo)

        self.lbl_brand_pro = QLabel('PRO')
        self.lbl_brand_pro.setObjectName('HeaderBrandPro')
        layout.addWidget(self.lbl_brand_pro)
        self.brand_separator = QFrame()
        self.brand_separator.setFixedSize(1, 18)
        layout.addWidget(self.brand_separator)

        self.btn_back = QPushButton("< Geri")
        self.btn_back.setObjectName("HeaderActionButton")
        self.btn_back.setFixedHeight(24)
        self.btn_back.setMinimumWidth(56)
        self.btn_back.setToolTip("Onceki sayfaya don")
        self.btn_back.setEnabled(False)
        self.btn_back.clicked.connect(self._go_back)
        layout.addWidget(self.btn_back)
        self.breadcrumb_separator = QFrame()
        self.breadcrumb_separator.setFixedSize(1, 18)
        layout.addWidget(self.breadcrumb_separator)

        # ── Uygulama adı ─────────────────────────────────────────────────────
        self.lbl_app_name = QLabel("AYEC Pro")
        self.lbl_app_name.setObjectName("AppNameLabel")
        self.lbl_app_name.setStyleSheet("font-size: 13px; font-weight: 800;")
        layout.addWidget(self.lbl_app_name)

        layout.addSpacing(4)

        self.lbl_module_path = QLabel("")
        self.lbl_module_path.setObjectName("HeaderModulePath")
        self.lbl_module_path.setStyleSheet(theme_qss(
            "color: @text_muted; font-size: 12px; font-weight: 500;"
        ))
        self.lbl_module_path.hide()
        layout.addWidget(self.lbl_module_path)

        self.breadcrumb = Breadcrumb(self.main_window)
        layout.addWidget(self.breadcrumb, 1)

        self.btn_invoice_integration = QPushButton("\u2699  Entegrasyon Ayarlar\u0131")
        self.btn_invoice_integration.setObjectName("InvoiceHeaderIntegration")
        self.btn_invoice_integration.setFixedSize(148, 48)
        self.btn_invoice_integration.clicked.connect(self._open_einvoice_integration_settings)
        self.btn_invoice_integration.hide()
        layout.addWidget(self.btn_invoice_integration)

        # --- Update Button ---
        self.btn_update = QPushButton("G\u00fcncelleme")
        self.btn_update.setObjectName("UpdateHeaderBtn")
        self.btn_update.setFixedHeight(26)
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
        self.btn_web_sync.setFixedSize(26, 26)
        self.btn_web_sync.setToolTip("Web ve mobil verilerini \u015fimdi senkronize et")
        self.btn_web_sync.clicked.connect(
            lambda: self.main_window.start_web_sync(silent=False)
        )
        layout.addWidget(self.btn_web_sync)

        self.notification_bell = NotificationBell()
        self.notification_bell.setFixedSize(26, 26)
        self.notification_bell.badge.move(10, 0)
        self.notification_bell.badge.setStyleSheet(theme_qss(
            'background: @finance_action_expense; color: @finance_action_expense_text; '
            'border: none; border-radius: 6px; font-weight: 700; font-size: 10px; padding: 0;'
        ))
        self.notification_bell.clicked.connect(self.open_notification_panel)
        layout.addWidget(self.notification_bell)
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

        self.btn_interface_edit = QPushButton("Aray\u00fcz D\u00fczenle")
        self.btn_interface_edit.setObjectName("HeaderActionButton")
        self.btn_interface_edit.setFixedHeight(26)
        self.btn_interface_edit.clicked.connect(self.main_window.open_interface_layout_editor)
        if not self._can_show_interface_editor():
            self.btn_interface_edit.hide()
        layout.addWidget(self.btn_interface_edit)

        self.btn_settings = QPushButton()
        self.btn_settings.setObjectName("HeaderIconButton")
        self.btn_settings.setFixedSize(26, 26)
        self.btn_settings.setToolTip("Sistem Ayarlar\u0131")
        self.btn_settings.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        self.btn_settings.setIconSize(self.btn_settings.size() * 0.52)
        self.btn_settings.clicked.connect(lambda: self.main_window.on_menu_click(130))
        layout.addWidget(self.btn_settings)

        self.btn_shortcuts = QPushButton("\u2605")
        self.btn_shortcuts.setObjectName("HeaderIconButton")
        self.btn_shortcuts.setFixedSize(26, 26)
        self.btn_shortcuts.setToolTip("Genel Bak\u0131\u015f k\u0131sayollar\u0131")
        self.btn_shortcuts.clicked.connect(self.main_window.toggle_dashboard_shortcuts)
        layout.addWidget(self.btn_shortcuts)

        self.btn_theme_toggle = QPushButton()
        self.btn_theme_toggle.setObjectName("HeaderIconButton")
        self.btn_theme_toggle.setFixedSize(26, 26)
        self.btn_theme_toggle.clicked.connect(self.main_window.toggle_theme_from_header)
        layout.addWidget(self.btn_theme_toggle)

        self.cmb_theme = ModernComboBox()
        self.cmb_theme.setObjectName("HeaderCombo")
        self.cmb_theme.setFixedHeight(34)
        self.cmb_theme.set_reference_chevron()
        self.cmb_theme.setMinimumWidth(120)
        self.cmb_theme.setMaximumWidth(180)
        self.cmb_theme.addItems(ThemeManager.get_available_themes(self.db))
        self.cmb_theme.currentTextChanged.connect(self.main_window.on_header_theme_changed)
        layout.addWidget(self.cmb_theme)


        # ── Pencere kontrol butonları (Frameless) ────────────────────────────
        layout.addSpacing(6)

        self.btn_minimize = QPushButton()
        self.btn_minimize.setObjectName("WinMinBtn")
        self.btn_minimize.setFixedSize(24, 24)
        self.btn_minimize.setIconSize(QSize(14, 14))
        self.btn_minimize.setToolTip("Küçült")
        self.btn_minimize.clicked.connect(self.main_window.window_minimize)
        layout.addWidget(self.btn_minimize)

        self.btn_maximize = QPushButton()
        self.btn_maximize.setObjectName("WinMaxBtn")
        self.btn_maximize.setFixedSize(24, 24)
        self.btn_maximize.setIconSize(QSize(14, 14))
        self.btn_maximize.setToolTip("Büyüt / Geri Al")
        self.btn_maximize.clicked.connect(self.main_window.window_maximize_restore)
        layout.addWidget(self.btn_maximize)

        self.btn_close = QPushButton()
        self.btn_close.setObjectName("WinCloseBtn")
        self.btn_close.setFixedSize(24, 24)
        self.btn_close.setIconSize(QSize(14, 14))
        self.btn_close.setToolTip("Kapat")
        self.btn_close.clicked.connect(self.main_window.window_close)
        layout.addWidget(self.btn_close)
        self._update_window_control_icons()

        self.service_profile = QToolButton(self)
        self.service_profile.setFixedSize(42, 38)
        self.service_profile.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.service_profile.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        company_name = self.db.get_setting("company_name", "Aslan Computer") or "Aslan Computer"
        self.service_profile.setText("")
        self.service_profile.setToolTip(company_name)
        avatar = QPixmap(36, 36)
        avatar.fill(Qt.GlobalColor.transparent)
        avatar_painter = QPainter(avatar)
        avatar_painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        avatar_painter.setPen(QColor("#0ea5e9"))
        avatar_painter.setBrush(QColor("#0b1220"))
        avatar_painter.drawRoundedRect(1, 1, 34, 34, 9, 9)
        avatar_painter.setPen(QColor("#bae6fd"))
        avatar_painter.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        avatar_painter.drawText(avatar.rect(), Qt.AlignmentFlag.AlignCenter, "AS")
        avatar_painter.end()
        self.service_profile.setIcon(QIcon(avatar))
        self.service_profile.setIconSize(QSize(36, 36))
        self.service_profile.setStyleSheet(theme_qss(
            "QToolButton { color: @text; background: transparent; border: none; "
            "text-align: left; font-size: 12px; font-weight: 700; padding: 0 4px; } "
            "QToolButton:hover { background: @surface_alt; border-radius: 7px; }"
        ))
        self.service_profile_menu = QMenu(self.service_profile)
        self.service_profile_menu.setMinimumWidth(250)
        for title, callback in (
            ("Sistem Ayarlar\u0131", self.btn_settings.click),
            ("Genel Bak\u0131\u015f K\u0131sayollar\u0131", self.btn_shortcuts.click),
            ("Temay\u0131 De\u011fi\u015ftir", self.btn_theme_toggle.click),
            ("Web ve mobil verilerini e\u015fle", self.btn_web_sync.click),
            ("Bildirimleri a\u00e7", self.open_notification_panel),
        ):
            self.service_profile_menu.addAction(title, callback)
        if self._can_show_interface_editor():
            self.service_profile_menu.addAction(
                "Aray\u00fcz d\u00fczenleyicisi", self.main_window.open_interface_layout_editor
            )
        self.service_profile_menu.addSeparator()
        self.service_profile_menu.addAction("K\u00fc\u00e7\u00fclt", self.btn_minimize.click)
        self.service_profile_menu.addAction("B\u00fcy\u00fct / Geri Al", self.btn_maximize.click)
        self.service_profile_menu.addAction("Pencereyi Kapat", self.btn_close.click)
        self.service_profile.setMenu(self.service_profile_menu)
        self.service_profile.hide()
        layout.addWidget(self.service_profile)

        for control in (self.btn_minimize, self.btn_maximize, self.btn_close):
            layout.removeWidget(control)
            layout.addWidget(control)

        layout.setContentsMargins(15, 0, 15, 0)
        layout.setSpacing(8)
        self.lbl_brand_pro.hide()
        self.breadcrumb_separator.hide()
        self.lbl_logo.setFixedSize(10, 10)
        self.lbl_logo.clear()
        self.lbl_logo.setText("\u25cf")
        self.lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_logo.setStyleSheet(theme_qss(
            "QLabel { color: @accent; border: none; font-size: 10px; font-weight: 800; }"
        ))
        self.lbl_app_name.setText("AYEC PRO")
        self.lbl_app_name.setFixedWidth(82)
        self.lbl_app_name.setStyleSheet(theme_qss("color: @text; font-size: 14px; font-weight: 800;"))
        self.btn_back.setFixedSize(80, 32)
        self.btn_back.setText("\u2190  Geri")
        self.btn_back.setStyleSheet(theme_qss(
            "QPushButton { background: transparent; color: @text; border: 1px solid @finance_outline; "
            "border-radius: 7px; font-size: 12px; font-weight: 600; padding: 0 8px; } "
            "QPushButton:hover { background: @surface_alt; border-color: @accent; }"
        ))
        left_header_items = (
            self.btn_back, self.lbl_logo, self.lbl_app_name, self.lbl_module_path, self.breadcrumb
        )
        for widget in left_header_items:
            layout.removeWidget(widget)
        for index, widget in enumerate(left_header_items):
            layout.insertWidget(index, widget, 1 if widget is self.breadcrumb else 0)
        self.reference_traffic_lights = QWidget(self)
        self.reference_traffic_lights.setFixedSize(83, 20)
        lights_layout = QHBoxLayout(self.reference_traffic_lights)
        lights_layout.setContentsMargins(7, 0, 7, 0)
        lights_layout.setSpacing(15)
        for color in ("#fb7185", "#fbbf24", "#34d399"):
            light = QFrame(self.reference_traffic_lights)
            light.setFixedSize(13, 13)
            light.setStyleSheet(f"background:{color};border:0;border-radius:6px;")
            lights_layout.addWidget(light)
        layout.insertWidget(0, self.reference_traffic_lights)
        self.service_header_spacer = QWidget(self)
        self.service_header_spacer.setFixedWidth(124)
        layout.insertWidget(4, self.service_header_spacer)
        self.brand_separator.hide()
        self.breadcrumb.setMinimumWidth(0)
        self._apply_service_header_presentation()

    def _open_einvoice_integration_settings(self):
        pages = getattr(self.main_window, "pages", {})
        page = pages.get(115) if isinstance(pages, dict) else None
        if page is None and hasattr(self.main_window, "content_area"):
            page = self.main_window.content_area.currentWidget()
        callback = getattr(page, "open_integration_settings", None)
        if callable(callback):
            callback()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_service_header_presentation()
        self._apply_compact_width_presentation()

    def _apply_compact_width_presentation(self):
        if not hasattr(self, "service_profile"):
            return
        page_id = getattr(self.main_window, "_current_page_index", None)
        compact = self.width() < 1400
        layout = self.layout()
        if compact:
            layout.setContentsMargins(8, 0, 8, 0)
            layout.setSpacing(4)
            self.lbl_app_name.setFixedWidth(64)
            self.btn_web_sync.setFixedSize(24, 24)
            self.notification_bell.setFixedSize(24, 24)
            self.btn_settings.setFixedSize(24, 24)
            self.btn_shortcuts.hide()
            self.btn_theme_toggle.hide()
            self.btn_interface_edit.hide()
            for control in (self.btn_minimize, self.btn_maximize, self.btn_close):
                control.setFixedSize(24, 24)
                control.show()
            self.cmb_theme.setFixedWidth(118)
            self.service_profile.setFixedSize(42, 38)
            self.service_profile.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            self.service_profile.setToolTip("Profil ve ek eylemler")
            self.breadcrumb.assistant_btn.setFixedSize(32, 32)
            self.breadcrumb.assistant_btn.setText("\U0001f916")
            self.breadcrumb.assistant_btn.show()
            self.breadcrumb.user_lbl.hide()
            self.breadcrumb.mute_btn.hide()
            self.btn_back.show()
            self.btn_web_sync.show()
            self.notification_bell.show()
            self.cmb_theme.show()
            self.service_profile.show()
        else:
            layout.setContentsMargins(15, 0, 15, 0)
            layout.setSpacing(8)
            self.lbl_app_name.setMinimumWidth(0)
            self.lbl_app_name.setMaximumWidth(16777215)
            self.lbl_app_name.setFixedWidth(82)
            self.btn_web_sync.setFixedSize(26, 26)
            self.notification_bell.setFixedSize(26, 26)
            self.btn_settings.setFixedSize(26, 26)
            self.cmb_theme.setMinimumWidth(120)
            self.cmb_theme.setMaximumWidth(180)
            self.service_profile.setFixedSize(42, 38)
            self.service_profile.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            self.btn_shortcuts.setVisible(True)
            self.btn_theme_toggle.setVisible(True)
            self.btn_interface_edit.setVisible(self._can_show_interface_editor())
            self.btn_minimize.show()
            self.btn_maximize.show()
            self.btn_close.show()

    def _update_window_control_icons(self):
        icon_color = QColor(tc("text"))

        def tinted_icon(pixmap_id):
            pixmap = self.style().standardIcon(pixmap_id).pixmap(QSize(16, 16))
            painter = QPainter(pixmap)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            painter.fillRect(pixmap.rect(), icon_color)
            painter.end()
            return QIcon(pixmap)

        self.btn_minimize.setIcon(tinted_icon(QStyle.StandardPixmap.SP_TitleBarMinButton))
        maximize_icon = (
            QStyle.StandardPixmap.SP_TitleBarNormalButton
            if self.main_window.isMaximized()
            else QStyle.StandardPixmap.SP_TitleBarMaxButton
        )
        self.btn_maximize.setIcon(tinted_icon(maximize_icon))
        self.btn_close.setIcon(tinted_icon(QStyle.StandardPixmap.SP_TitleBarCloseButton))

    def _apply_service_header_presentation(self):
        if not hasattr(self, "service_profile"):
            return
        self._apply_shared_header_presentation()
        return

    def _apply_shared_header_presentation(self):
        """Keep the same app bar controls and geometry on every menu."""
        layout = self.layout()
        self.setFixedHeight(70)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(6)

        while layout.count():
            layout.takeAt(0)
        self.reference_traffic_lights.hide()
        self.service_header_spacer.hide()
        for widget in (
            self.btn_back, self.lbl_logo, self.lbl_brand_pro,
            self.brand_separator, self.breadcrumb_separator,
            self.lbl_app_name, self.lbl_module_path, self.breadcrumb,
            self.btn_invoice_integration,
            self.btn_web_sync, self.btn_update,
            self.notification_bell, self.btn_interface_edit, self.btn_settings,
            self.btn_shortcuts, self.btn_theme_toggle, self.cmb_theme,
            self.service_profile,
            self.btn_minimize, self.btn_maximize, self.btn_close,
        ):
            layout.addWidget(widget, 1 if widget is self.breadcrumb else 0)
        self._shared_header_layout_ready = True

        self.btn_back.setFixedSize(68, 32)
        self.btn_back.setText("\u2190  Geri")
        self.btn_back.setStyleSheet(theme_qss(
            "QPushButton#HeaderActionButton { background: @surface_alt; color: @text; "
            "border: 1px solid @border; border-radius: 6px; font-size: 12px; font-weight: 600; }"
        ))
        self.lbl_logo.setPixmap(QPixmap())
        self.lbl_logo.setText("\u25cf")
        self.lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_logo.setFixedSize(24, 24)
        self.lbl_logo.setStyleSheet(theme_qss(
            "QLabel { color: @accent; background: transparent; border: none; "
            "font-size: 10px; font-weight: 800; }"
        ))
        self.lbl_logo.setFixedSize(10, 20)
        self.lbl_brand_pro.hide()
        self.brand_separator.hide()
        self.lbl_app_name.setText("AYEC Pro")
        self.lbl_app_name.setFixedWidth(72)
        self.lbl_app_name.setStyleSheet(theme_qss(
            "QLabel#AppNameLabel { color: @text; font-size: 13px; font-weight: 800; }"
        ))
        self.lbl_module_path.hide()
        self.breadcrumb_separator.hide()
        self.btn_invoice_integration.hide()

        for widget in (
            self.lbl_logo, self.btn_back,
            self.lbl_app_name, self.breadcrumb, self.service_profile,
            self.btn_web_sync, self.btn_update,
            self.notification_bell, self.btn_settings, self.btn_shortcuts,
            self.btn_theme_toggle, self.cmb_theme, self.btn_minimize,
            self.btn_maximize, self.btn_close,
        ):
            widget.show()
        self.lbl_brand_pro.hide()
        self.brand_separator.hide()
        self.btn_interface_edit.setVisible(self._can_show_interface_editor())
        self.btn_update.setVisible(self.btn_update.text().strip() not in ("", "G\u00fcncelleme"))
        self.cmb_theme.setFixedSize(112, 32)
        self.btn_web_sync.setFixedSize(26, 26)
        self.notification_bell.setFixedSize(26, 26)
        self.btn_settings.setFixedSize(26, 26)
        self.btn_shortcuts.setFixedSize(26, 26)
        self.btn_theme_toggle.setFixedSize(26, 26)
        self.btn_interface_edit.setFixedHeight(30)
        self.btn_minimize.setFixedSize(22, 22)
        self.btn_maximize.setFixedSize(22, 22)
        self.btn_close.setFixedSize(22, 22)
        self.service_profile.setFixedSize(42, 38)
        self.service_profile.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.breadcrumb.setMinimumWidth(0)
        self.breadcrumb.setMaximumWidth(16777215)
        self.breadcrumb.search_input.setMinimumWidth(120)
        self.breadcrumb.search_input.setMaximumWidth(340)
        self.btn_web_sync.setVisible(True)
        return

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
                background-color: @finance_surface_lowest;
                color: @finance_text_muted;
                border: 1px solid @finance_outline;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 700;
                padding: 0px;
            }
            QPushButton#HeaderIconButton:hover {
                background-color: @finance_surface_high;
                color: @finance_text;
                border-color: @finance_primary;
            }
            QPushButton#HeaderIconButton:pressed { background-color: @finance_active_bg; }
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
                background-color: @finance_surface_lowest;
                color: @finance_text;
                border: 1px solid @finance_outline;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 800;
                padding: 0 10px;
            }
            QPushButton#HeaderActionButton:hover {
                background-color: @finance_surface_high;
                border-color: @finance_primary;
            }
            QPushButton#HeaderActionButton:pressed { background-color: @finance_active_bg; }
            QPushButton#HeaderActionButton:disabled { color: @finance_text_muted; }
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
        if obj is self.main_window and event.type() == QEvent.Type.WindowStateChange:
            self._update_window_control_icons()
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
                width: 16px;
            }
            QComboBox#HeaderCombo::down-arrow { image: none; width: 0; height: 0; }
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
                background-color: @finance_surface_lowest;
                color: @finance_text;
                border: 1px solid @finance_outline;
                border-radius: 4px;
                padding: 4px 16px 4px 8px;
                min-height: 18px;
            }
            QComboBox#HeaderCombo:hover {
                border-color: @finance_primary;
            }
            QComboBox#HeaderCombo::drop-down {
                border: none;
                width: 16px;
            }
            QComboBox#HeaderCombo::down-arrow { image: none; width: 0; height: 0; }
            QComboBox#HeaderCombo QAbstractItemView {
                background-color: @finance_surface_lowest;
                color: @finance_text;
                border: 1px solid @finance_outline;
                selection-background-color: @finance_primary;
                selection-color: @finance_primary_text;
            }
            QComboBox#HeaderCombo QAbstractItemView::item {
                color: @finance_text;
                background-color: transparent;
                padding: 4px;
            }
            QComboBox#HeaderCombo QAbstractItemView::item:hover,
            QComboBox#HeaderCombo QAbstractItemView::item:selected {
                background-color: @finance_primary;
                color: @finance_primary_text;
            }
            """
        )

    def apply_theme_styles(self):
        classic = self._is_classic_appearance()
        for widget in (
            self.btn_settings,
            self.btn_shortcuts,
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
                        background-color: @finance_surface_lowest;
                        border-bottom: 1px solid @finance_outline;
                    }
                QLabel#HeaderBrandPro { color: @finance_primary; font-size: 11px; font-weight: 700; }
                QFrame { background-color: @finance_outline; border: none; }
                    """
                )
            )
        self.lbl_app_name.setStyleSheet(
            (
                theme_qss("QLabel#AppNameLabel { color: @text; font-size: 14px; font-weight: 800; }")
                if classic
                else theme_qss("QLabel#AppNameLabel { color: @text; font-size: 14px; font-weight: 800; }")
            )
        )
        self.btn_back.setFixedSize(80, 32)
        self.btn_back.setText("\u2190  Geri")
        self.lbl_logo.setFixedSize(10, 10)
        self.lbl_logo.setText("\u25cf")
        self.lbl_logo.setStyleSheet(theme_qss(
            "QLabel { color: @accent; border: none; font-size: 10px; font-weight: 800; }"
        ))
        self.lbl_app_name.setText("AYEC PRO")
        self.lbl_app_name.setFixedWidth(82)
        self.brand_separator.setFixedSize(1, 20)
        self.breadcrumb_separator.setFixedSize(1, 18)
        self.lbl_brand_pro.setStyleSheet(theme_qss(
            'QLabel#HeaderBrandPro { color: @finance_primary; font-size: 11px; font-weight: 700; '
            'padding: 2px 5px; background: @finance_active_bg; border: 1px solid @finance_outline; '
            'border-radius: 4px; }'
        ))
        for separator in (self.brand_separator, self.breadcrumb_separator):
            separator.setStyleSheet(theme_qss('background: @finance_outline; border: none;'))
        self.btn_settings.setStyleSheet(self._button_style())
        self.btn_shortcuts.setStyleSheet(self._button_style())
        self.btn_theme_toggle.setStyleSheet(self._button_style())
        self.btn_web_sync.setStyleSheet(self._button_style())
        self.btn_interface_edit.setStyleSheet(self._action_button_style())
        self.btn_back.setStyleSheet(theme_qss(
            "QPushButton { background: transparent; color: @text; border: 1px solid @finance_outline; "
            "border-radius: 7px; font-size: 12px; font-weight: 600; padding: 0 8px; } "
            "QPushButton:hover { background: @surface_alt; border-color: @accent; }"
        ))
        self.cmb_theme.setStyleSheet(self._combo_style())
        self.btn_minimize.setStyleSheet(self._win_btn_style("minimize"))
        self.btn_maximize.setStyleSheet(self._win_btn_style("maximize"))
        self.btn_close.setStyleSheet(self._win_btn_style("close"))
        self._update_window_control_icons()

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
        hover = '@finance_action_expense' if kind == 'close' else '@finance_surface_high'
        hover_text = '@finance_action_expense_text' if kind == 'close' else '@finance_text'
        return theme_qss(f'''
            QPushButton {{
                background: @finance_surface_container;
                color: @finance_text;
                border: 1px solid @finance_outline;
                border-radius: 4px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background: {hover}; color: {hover_text}; }}
            QPushButton:pressed {{ background: {hover}; color: {hover_text}; }}
        ''')

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
