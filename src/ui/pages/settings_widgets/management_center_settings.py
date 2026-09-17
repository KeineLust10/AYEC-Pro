from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QDesktopServices, QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.utils.desktop_web_sync import configured_sync_url
from src.utils.role_utils import is_admin_role
from src.utils.theme_colors import theme_qss


class ManagementCenterSettingsWidget(QWidget):
    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.current_user = dict(getattr(main_window, "current_user", {}) or {})
        self._init_ui()

    def _setting_enabled(self, key):
        try:
            default = "1" if key == "desktop_auto_web_sync" else "0"
            return str(self.db.get_setting(key, default) or default).strip().lower() in {
                "1",
                "true",
                "yes",
                "on",
            }
        except Exception:
            return False

    def _is_platform_owner(self):
        return bool(self.current_user.get("is_control_admin")) or self._setting_enabled(
            "web_is_control_admin"
        )

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(18)

        title = QLabel("Y\u00f6netim Merkezi")
        title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        root.addWidget(title)

        description = QLabel(
            "Firma, kullan\u0131c\u0131, rol ve sekt\u00f6r y\u00f6netimini merkezi sunucu \u00fczerinden y\u00f6netin."
        )
        description.setWordWrap(True)
        description.setStyleSheet(theme_qss("color: @text_muted; font-size: 14px;"))
        root.addWidget(description)

        panel = QFrame()
        panel.setObjectName("ManagementCenterPanel")
        panel.setStyleSheet(
            theme_qss(
                """
                QFrame#ManagementCenterPanel {
                    background: @surface_alt;
                    border: 1px solid @border;
                    border-radius: 8px;
                }
                QLabel { background: transparent; border: none; color: @text; }
                """
            )
        )
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(22, 22, 22, 22)
        panel_layout.setSpacing(14)

        scope_title = QLabel("Yetki Kapsam\u0131")
        scope_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        panel_layout.addWidget(scope_title)

        if self._is_platform_owner():
            scope_text = "Platform y\u00f6neticisi: T\u00fcm firmalar\u0131 ve kullan\u0131c\u0131lar\u0131 y\u00f6netebilirsiniz."
        else:
            scope_text = "Firma y\u00f6neticisi: Yaln\u0131zca kendi firman\u0131z\u0131 ve kullan\u0131c\u0131lar\u0131n\u0131 y\u00f6netebilirsiniz."
        scope = QLabel(scope_text)
        scope.setWordWrap(True)
        panel_layout.addWidget(scope)

        address = QLabel(configured_sync_url())
        address.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        address.setStyleSheet(theme_qss("color: @accent; font-weight: 700;"))
        panel_layout.addWidget(address)

        service_title = QLabel("Masa\u00fcst\u00fc Arka Plan Servisleri")
        service_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        panel_layout.addWidget(service_title)

        self.chk_auto_sync = QCheckBox(
            "A\u00e7\u0131l\u0131\u015fta 15 saniye sonra ve ard\u0131ndan saatte bir otomatik senkronize et"
        )
        self.chk_auto_sync.setChecked(
            self._setting_enabled("desktop_auto_web_sync")
        )
        self.chk_auto_sync.setEnabled(
            is_admin_role(self.current_user.get("role"))
        )
        self.chk_auto_sync.toggled.connect(
            lambda enabled: self._save_service_setting(
                "desktop_auto_web_sync",
                enabled,
            )
        )
        panel_layout.addWidget(self.chk_auto_sync)

        self.chk_local_api = QCheckBox(
            "Yerel API servisini program a\u00e7\u0131l\u0131rken ba\u015flat"
        )
        self.chk_local_api.setChecked(
            self._setting_enabled("desktop_local_api")
        )
        self.chk_local_api.setEnabled(
            is_admin_role(self.current_user.get("role"))
        )
        self.chk_local_api.toggled.connect(
            lambda enabled: self._save_service_setting(
                "desktop_local_api",
                enabled,
            )
        )
        panel_layout.addWidget(self.chk_local_api)

        actions = QHBoxLayout()
        self.btn_open = QPushButton("\U0001f5d6  Y\u00f6netim Merkezini A\u00e7")
        self.btn_open.setObjectName("openManagementCenterButton")
        self.btn_open.setMinimumHeight(44)
        self.btn_open.clicked.connect(self.open_management_center)
        self.btn_open.setEnabled(is_admin_role(self.current_user.get("role")))
        self.btn_open.setStyleSheet(
            theme_qss(
                """
                QPushButton {
                    background: @accent;
                    color: @selection_text;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 18px;
                    font-weight: 800;
                }
                QPushButton:hover { background: @accent_hover; }
                QPushButton:disabled { background: @disabled_bg; color: @disabled_text; }
                """
            )
        )
        actions.addWidget(self.btn_open)
        actions.addStretch()
        panel_layout.addLayout(actions)

        root.addWidget(panel)
        root.addStretch()

    def open_management_center(self):
        target = configured_sync_url().rstrip("/") + "/?page=control-center"
        return QDesktopServices.openUrl(QUrl(target))

    def _save_service_setting(self, key, enabled):
        self.db.set_setting(key, "1" if enabled else "0")
        if key == "desktop_auto_web_sync" and hasattr(
            self.main_window, "configure_auto_web_sync"
        ):
            self.main_window.configure_auto_web_sync(bool(enabled))
