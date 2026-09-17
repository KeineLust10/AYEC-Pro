# -*- coding: utf-8 -*-

import logging
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget
from PyQt6.QtCore import QTimer, Qt, pyqtSignal

# Import Mixins
from .mixins._main_window_base_mixin import MainWindowBaseMixin
from .mixins._main_window_nav_mixin import MainWindowNavMixin
from .mixins._main_window_service_mixin import MainWindowServiceMixin
from .mixins._main_window_func_mixin import MainWindowFuncMixin

# Import Services & Components
from src.services.license_service import LicenseService
from src.services.fiscal_year_service import FiscalYearService
from src.utils.license_manager import LicenseManager
from src.ui.components.app_header import AppHeader
from src.ui.components.app_sidebar import AppSidebar
from src.ui.components.app_top_nav_bar import AppTopNavBar
from src.utils.page_config import PAGE_MAPPING
from src.utils.appearance_mode import AppearanceModeManager
from src.utils.theme_manager import ThemeManager
from src.utils.theme_colors import theme_qss

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow, MainWindowBaseMixin, MainWindowNavMixin, MainWindowServiceMixin, MainWindowFuncMixin):
    """
    AYEC Pro Ana Penceresi.
    Mixin yapılandırması ile modüler hale getirilmiştir.
    """
    
    stock_updated = pyqtSignal()
    financial_data_changed = pyqtSignal()
    runtime_setting_changed = pyqtSignal(str, object, bool)
    
    def __init__(self, db, user_data=None, sector_manager=None):
        super().__init__()
        self.db = db
        self.sector_manager = sector_manager
        self.current_user = user_data or {}
        self.user_data = user_data or {}
        self.username = self.user_data.get("username", "Kullanıcı")
        
        # State
        self.pages = {}
        self.page_mapping = PAGE_MAPPING
        self._is_closing = False
        self._ui_task_counters = {"immediate": 0, "soon": 0, "idle": 0}
        self.is_archive_mode = False
        self._active_db = db
        self._current_page_index = 40
        self._initial_page_loaded = False
        self._dialog_open = False
        self._web_sync_worker = None
        self._web_sync_startup_timer = None
        self._web_sync_hourly_timer = None
        self._web_sync_event_worker = None
        self._web_sync_event_pending = False
        self._sector_sync_worker = None
        self._pending_sector_sync = None
        self._web_sync_password = ""
        self._web_sync_username = ""
        self._web_sync_tenant_id = ""
        self._web_sync_provision_invite_code = ""
        self._settings_menu_refresh_pending = False

        # All transient notifications use one queue so the assistant FAB never
        # competes with independent toast widgets.
        from src.ui.widgets.toast_manager import ToastManager
        self.toast = ToastManager(self)

        self.runtime_setting_changed.connect(self._apply_runtime_setting_change)
        if hasattr(self.db, "subscribe_setting_changes"):
            self.db.subscribe_setting_changes(self._relay_runtime_setting_change)
        
        # Services
        self.assistant = None
        self.license_manager = LicenseManager(self.db)
        self.license_service = LicenseService(self)
        self.fiscal_service = FiscalYearService(self)
        self.assistant_sidebar = None
        
        self.init_ui()
        self.init_assistant_fab()
        
        # Instantiate Update Manager
        from src.utils.update_manager import UpdateManager
        self.update_manager = UpdateManager(self.db, self)
        
        self.start_initial_tasks()
        # Start the automatic first-run/hourly web sync from the saved setting.
        # This also sends the company location on the first successful sync.
        auto_sync = self.db.get_setting("desktop_auto_web_sync", "1") == "1"
        QTimer.singleShot(1200, lambda: self.configure_auto_web_sync(auto_sync))

    def init_ui(self):
        self.setWindowTitle("AYEC Pro")
        from src.utils.path_helper import PathHelper
        self.setWindowIcon(PathHelper.get_app_icon())
        self.setMinimumSize(1280, 800)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Window
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
        )
        
        self._apply_theme_early()
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        self.app_sidebar = AppSidebar(self)
        self.main_layout.addWidget(self.app_sidebar)
        
        self.right_container = QWidget()
        self.right_layout = QVBoxLayout(self.right_container)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(0)
        
        self.app_header = AppHeader(self)
        self.right_layout.addWidget(self.app_header)
        
        self.app_top_nav = AppTopNavBar(self)
        self.right_layout.addWidget(self.app_top_nav)
        
        self.content_area = QStackedWidget()
        self.right_layout.addWidget(self.content_area)
        
        self.main_layout.addWidget(self.right_container)
        self.main_layout.setStretch(1, 1)
        
        self._install_startup_placeholder()
        self.apply_theme_on_startup()
        
        self.schedule_ui_task("immediate", self.apply_nav_mode, "startup.apply_nav_mode")
        self.schedule_ui_task("immediate", self.apply_display_profile, "startup.apply_display_profile")
        self.schedule_ui_task("soon", self._load_initial_page, "startup.load_initial_page")

    def resizeEvent(self, event):
        self.reposition_fab()
        if hasattr(self, "toast"):
            self.toast.reposition_toasts()
        super().resizeEvent(event)

    def closeEvent(self, event):
        self._is_closing = True
        if hasattr(self.db, "unsubscribe_setting_changes"):
            self.db.unsubscribe_setting_changes(self._relay_runtime_setting_change)
        if self.assistant is not None:
            self.assistant.stop_voice_assistant()
        worker = getattr(self, "_web_sync_worker", None)
        if worker:
            try:
                if worker.isRunning() and not worker.wait(5000):
                    worker.terminate()
                    worker.wait(1500)
            except RuntimeError:
                pass
            self._web_sync_worker = None
        event_worker = getattr(self, "_web_sync_event_worker", None)
        if event_worker:
            try:
                event_worker.stop()
                event_worker.wait(1500)
            except RuntimeError:
                pass
            self._web_sync_event_worker = None
        sector_worker = getattr(self, "_sector_sync_worker", None)
        if sector_worker and sector_worker.isRunning() and not sector_worker.wait(5000):
            sector_worker.terminate()
            sector_worker.wait(1500)
        tax_worker = getattr(self, "_income_tax_tariff_worker", None)
        if tax_worker and tax_worker.isRunning() and not tax_worker.wait(5000):
            tax_worker.terminate()
            tax_worker.wait(1500)
        event.accept()

    def configure_auto_web_sync(self, enabled):
        for timer_name in ("_web_sync_startup_timer", "_web_sync_hourly_timer"):
            timer = getattr(self, timer_name, None)
            if timer is not None:
                timer.stop()
                timer.deleteLater()
                setattr(self, timer_name, None)
        if not enabled or self._is_closing:
            return

        hourly_timer = QTimer(self)
        hourly_timer.setInterval(60 * 60 * 1000)
        hourly_timer.timeout.connect(lambda: self.start_web_sync(silent=True))
        self._web_sync_hourly_timer = hourly_timer

        startup_timer = QTimer(self)
        startup_timer.setSingleShot(True)
        startup_timer.setInterval(15000)

        def run_first_sync():
            if self._is_closing:
                return
            self.start_web_sync(silent=True)
            if self._web_sync_hourly_timer is hourly_timer:
                hourly_timer.start()

        startup_timer.timeout.connect(run_first_sync)
        self._web_sync_startup_timer = startup_timer
        startup_timer.start()

    def start_web_sync(self, silent=False):
        if self._is_closing:
            return False

        active_worker = self._web_sync_worker
        if active_worker:
            try:
                if active_worker.isRunning():
                    if not silent:
                        self.show_notification("Senkronizasyon zaten devam ediyor.", "info")
                    return False
            except RuntimeError:
                self._web_sync_worker = None

        from src.utils.desktop_web_sync import DesktopWebSyncWorker

        configured_tenant_id = str(
            self._web_sync_tenant_id
            or (self.current_user or {}).get("tenant_id")
            or self.db.get_setting("web_sync_tenant_id", "")
            or ""
        ).strip()
        if hasattr(self, "app_header"):
            self.app_header.set_web_sync_state(running=True)
        worker = DesktopWebSyncWorker(
            db_name=getattr(self.db, "_db_name", "ayecpro.db"),
            username=(
                self._web_sync_username
                or str((self.current_user or {}).get("username") or "")
            ),
            password=self._web_sync_password,
            tenant_id=configured_tenant_id,
            provision_invite_code=self._web_sync_provision_invite_code,
            allow_new_tenant=bool(
                not configured_tenant_id
                and str(self.db.get_setting("setup_completed", "") or "").casefold()
                in {"1", "true", "yes"}
            ),
            parent=self,
        )
        self._web_sync_worker = worker
        app = QApplication.instance()
        if app:
            if not hasattr(app, "_active_threads"):
                app._active_threads = set()
            app._active_threads.add(worker)

        def completed(ok, result):
            details = dict(result or {})
            if self._web_sync_worker is worker:
                self._web_sync_worker = None
            sync_username = worker.username
            sync_password = worker.password
            sync_tenant_id = worker.tenant_id
            if ok:
                self._web_sync_password = ""
                self._web_sync_username = ""
                self._web_sync_tenant_id = ""
                self._web_sync_provision_invite_code = ""
            if app:
                app._active_threads.discard(worker)
            if self._is_closing:
                return
            if hasattr(self, "app_header"):
                self.app_header.set_web_sync_state(
                    running=False,
                    success=ok,
                    detail=str(details.get("error") or ""),
                )
            if ok:
                session = dict(details.get("session") or {})
                tenant_id = str(details.get("tenant_id") or session.get("tenant_id") or "").strip()
                if tenant_id:
                    try:
                        self.db.set_setting("web_sync_tenant_id", tenant_id)
                    except Exception:
                        pass
                self._start_web_sync_event_listener()
                try:
                    from src.utils.license_manager import LicenseManager
                    license_ok, _license_message, _license_payload = (
                        LicenseManager(self.db).refresh_server_entitlement(
                            sync_username,
                            sync_password,
                            tenant_id or sync_tenant_id,
                        )
                    )
                    lock_screen = getattr(self, "lock_screen", None)
                    if license_ok and lock_screen is not None and lock_screen.isVisible():
                        lock_screen.accept()
                except Exception as license_error:
                    logger.info("Server license refresh skipped after sync: %s", license_error)
                self._refresh_after_web_sync()
                pulled = int(details.get("pulled") or 0)
                pushed = int(dict(details.get("pushed") or {}).get("applied") or 0)
                self.show_notification(
                    f"Senkronizasyon tamamland\u0131. Al\u0131nan: {pulled}, g\u00f6nderilen: {pushed}",
                    "success",
                )
                conflicts = list(dict(details.get("pushed") or {}).get("conflicts") or [])
                conflicts.extend(list(details.get("preserved_conflicts") or []))
                if conflicts:
                    self.show_notification(
                        f"{len(conflicts)} e\u015fzamanl\u0131 de\u011fi\u015fiklik korundu. Sunucu kayd\u0131 sakland\u0131; inceleme gerekiyor.",
                        "warning",
                    )
                update_requests = list(details.get("update_requests") or [])
                if update_requests and getattr(self, "update_manager", None):
                    latest = dict(update_requests[-1] or {})
                    self.show_notification(
                        f"Y\u00f6netim merkezi {latest.get('version', 'yeni')} s\u00fcr\u00fcm\u00fc "
                        "i\u00e7in g\u00fcncelleme kontrol\u00fc istedi.",
                        "info",
                    )
                    self.update_manager.check_for_updates()
            else:
                error = str(details.get("error") or "Senkronizasyon tamamlanamad\u0131.")
                logger.warning("Desktop web synchronization failed: %s", error)
                if "Sunucu oturumu bulunamad" in error and not silent:
                    self._open_web_sync_login()
                elif not silent:
                    self.show_notification(error, "error")

        worker.completed.connect(completed)
        worker.finished.connect(worker.deleteLater)
        worker.start()
        return True

    def _start_web_sync_event_listener(self):
        if self._is_closing:
            return
        worker = getattr(self, "_web_sync_event_worker", None)
        if worker:
            try:
                if worker.isRunning():
                    return
                worker.start()
                return
            except RuntimeError:
                self._web_sync_event_worker = None
        from src.utils.desktop_sync_events import DesktopSyncEventWorker

        worker = DesktopSyncEventWorker(
            db_name=getattr(self.db, "_db_name", "ayecpro.db"),
            parent=self,
        )
        worker.event_received.connect(self._handle_web_sync_event)
        worker.connection_changed.connect(self._on_web_sync_event_connection_changed)
        self._web_sync_event_worker = worker
        worker.start()

    def _on_web_sync_event_connection_changed(self, connected):
        logger.info("Desktop sync event channel %s", "connected" if connected else "disconnected")

    def _handle_web_sync_event(self, event):
        payload = dict(event or {})
        if payload.get("type") != "license_updated" or self._is_closing:
            return
        try:
            from src.utils.license_manager import LicenseManager

            ok, message, _details = LicenseManager(self.db).refresh_server_entitlement()
            if not ok:
                logger.info("Live license refresh was not applied: %s", message)
                return
            lock_screen = getattr(self, "lock_screen", None)
            if lock_screen is not None and lock_screen.isVisible():
                lock_screen.accept()
            self.show_notification(
                "Lisans bilgisi yonetim merkezinden guncellendi.", "success"
            )
        except Exception as error:
            logger.info("Live license event could not be applied: %s", error)

    def _queue_web_sync_from_event(self):
        if self._is_closing or self._web_sync_event_pending:
            return
        self._web_sync_event_pending = True
        QTimer.singleShot(750, self._run_web_sync_from_event)

    def _run_web_sync_from_event(self):
        self._web_sync_event_pending = False
        if self._is_closing:
            return
        active_worker = self._web_sync_worker
        if active_worker:
            try:
                if active_worker.isRunning():
                    self._queue_web_sync_from_event()
                    return
            except RuntimeError:
                self._web_sync_worker = None
        self.start_web_sync(silent=True)

    def _open_web_sync_login(self):
        """Ask for remote credentials only when the encrypted session is absent."""
        from PyQt6.QtWidgets import QDialog, QFormLayout, QLabel, QLineEdit, QPushButton

        dialog = QDialog(self)
        dialog.setWindowTitle("Sunucu Senkronizasyonu")
        dialog.setModal(True)
        dialog.setMinimumWidth(440)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)
        title = QLabel("Sunucu Hesabini Bagla")
        title.setObjectName("DialogTitle")
        layout.addWidget(title)
        description = QLabel(
            "Web ve mobil verileriyle esitlemek icin sunucu hesabinizla guvenli oturum acin. "
            "Firma kodu hesaptan otomatik bulunur; parolaniz diskte saklanmaz."
        )
        description.setWordWrap(True)
        layout.addWidget(description)
        form = QFormLayout()
        username = QLineEdit(str((self.current_user or {}).get("username") or ""))
        username.setPlaceholderText("Kullanici adi veya e-posta")
        password = QLineEdit()
        password.setEchoMode(QLineEdit.EchoMode.Password)
        password.setPlaceholderText("Sifre")
        form.addRow("Kullanici / E-posta:", username)
        form.addRow("Sifre:", password)
        layout.addLayout(form)
        status = QLabel("")
        status.setWordWrap(True)
        layout.addWidget(status)
        actions = QHBoxLayout()
        actions.addStretch()
        cancel = QPushButton("Vazgec")
        connect = QPushButton("Bagla ve Senkronize Et")
        connect.setDefault(True)
        actions.addWidget(cancel)
        actions.addWidget(connect)
        layout.addLayout(actions)
        cancel.clicked.connect(dialog.reject)

        def begin_connect():
            identifier = username.text().strip()
            secret = password.text()
            if not identifier or not secret:
                status.setText("Kullanici adi ve sifre zorunludur.")
                return
            self._web_sync_username = identifier
            self._web_sync_password = secret
            # Device reset preserves the last authenticated tenant so the next
            # sync reconnects to the existing company instead of provisioning it.
            self._web_sync_tenant_id = str(
                self.db.get_setting("web_sync_tenant_id", "") or ""
            ).strip()
            self._web_sync_provision_invite_code = ""
            dialog.accept()
            self.start_web_sync(silent=False)

        connect.clicked.connect(begin_connect)
        password.returnPressed.connect(begin_connect)
        dialog.exec()

    def _refresh_after_web_sync(self):
        if hasattr(self.db, "invalidate_settings_cache"):
            self.db.invalidate_settings_cache()
        for page in list(self.pages.values()):
            try:
                if hasattr(page, "request_reload"):
                    page.request_reload()
                elif hasattr(page, "refresh_data"):
                    page.refresh_data()
            except Exception as exc:
                logger.debug("Post-sync page refresh skipped: %s", exc)
        self.stock_updated.emit()
        self.financial_data_changed.emit()
        QTimer.singleShot(0, self.refresh_side_menu)

    def _relay_runtime_setting_change(self, key, value, internal=False):
        self.runtime_setting_changed.emit(str(key), value, bool(internal))

    def _schedule_settings_menu_refresh(self):
        if self._settings_menu_refresh_pending:
            return
        self._settings_menu_refresh_pending = True

        def _refresh():
            self._settings_menu_refresh_pending = False
            self.refresh_side_menu()

        QTimer.singleShot(0, _refresh)

    def _apply_runtime_setting_change(self, key, value, internal=False):
        """Apply safe visual preferences without rebuilding the application."""
        if self._is_closing:
            return
        key = str(key or "")
        if internal:
            if (
                key.startswith("menu_label_page_")
                or key.startswith("hide_page_")
                or key.startswith("module_")
                or key.startswith("feature_")
            ):
                self._schedule_settings_menu_refresh()
            return

        if key in {"company_name", "site_title", "logo_path"}:
            side_menu = getattr(
                getattr(self, "app_sidebar", None),
                "side_menu",
                None,
            )
            if side_menu and hasattr(side_menu, "update_branding"):
                side_menu.update_branding(
                    self.db.get_setting("logo_path", "") or "",
                    self.db.get_setting("company_name", "AYEC Pro") or "AYEC Pro",
                    self.db.get_setting("site_title", "") or "",
                )
            return

        if key == "color_theme_full":
            normalized = ThemeManager.normalize_theme_name(value)
            if normalized != getattr(self, "_current_theme_name", "AYEC"):
                self.apply_theme(normalized)
            return

        if key == "assistant_fab_enabled":
            assistant_fab = getattr(self, "assistant_fab", None)
            enabled = str(value) == "1"
            if assistant_fab is not None:
                assistant_fab.setVisible(enabled)
                if enabled:
                    self.reposition_fab()
            if not enabled:
                assistant_sidebar = getattr(self, "assistant_sidebar", None)
                if assistant_sidebar is not None and assistant_sidebar.isVisible():
                    assistant_sidebar.close()
            return

        if key == "notifications_enabled":
            self.refresh_notification_bell()
            app_header = getattr(self, "app_header", None)
            panel = getattr(app_header, "_notification_panel", None)
            if panel is not None and hasattr(panel, "update_notification_state"):
                panel.update_notification_state()
            return

        if key == AppearanceModeManager.SETTING_KEY:
            self.apply_appearance_mode(value, force_tree=True)
            return

        if key == "nav_mode":
            self.apply_nav_mode(value)
            return

        if key == "display_profile" and hasattr(self, "apply_display_profile"):
            self.apply_display_profile()
            return

        if key == "combo_auto_popup":
            ThemeManager._combo_auto_popup_enabled = str(value) == "1"
            return

        if key == "ticker_text":
            for page in self.pages.values():
                if hasattr(page, "ticker"):
                    page.ticker.update_content()
                if hasattr(page, "marquee"):
                    page.marquee.setText(str(value or ""))
            return

        if key in {
            "default_vat_percent",
            "financial_defaults_revision",
        }:
            for page in self.pages.values():
                if hasattr(page, "refresh_financial_defaults"):
                    try:
                        page.refresh_financial_defaults()
                    except Exception as exc:
                        logger.debug(
                            "Financial defaults refresh skipped: %s",
                            exc,
                        )
            self.financial_data_changed.emit()
            return

        if key in {
            "app_lang",
            "date_format",
            "currency_format",
            "currency_precision",
            "bank_default_currency",
        }:
            self.financial_data_changed.emit()

    def _apply_shell_theme_styles(self):
        try:
            self.central_widget.setObjectName("CentralWidget")
            self.central_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            self.central_widget.setStyleSheet(theme_qss("""
                QWidget#CentralWidget {
                    background-color: @window;
                    color: @text;
                }
            """))
        except Exception as exc:
            logger.debug("Shell theme style apply failed: %s", exc)

    # Sector change logic moved from NavMixin for better coordination
    def apply_sector_change(self, sector_id, target_index=40):
        from src.utils.system_config import SystemConfig
        sector_id = SystemConfig.normalize_sector(sector_id)
        self.db.set_internal_setting("current_sector", sector_id)
        if self.sector_manager: self.sector_manager.load_sector(sector_id)
        self._reload_all_pages()
        self.refresh_side_menu()
        self._refresh_active_page(target_index)
        self._sync_sector_to_web(sector_id)

    def _sync_sector_to_web(self, sector_id):
        worker = getattr(self, "_sector_sync_worker", None)
        if worker and worker.isRunning():
            self._pending_sector_sync = sector_id
            return
        from src.utils.desktop_web_sync import DesktopSectorSyncWorker

        worker = DesktopSectorSyncWorker(sector_id, self)
        self._sector_sync_worker = worker

        def completed(ok, result):
            details = dict(result or {})
            if not ok:
                self.show_notification(
                    str(details.get("error") or "Sekt\u00f6r sunucuya g\u00f6nderilemedi."),
                    "error",
                )
            elif not details.get("skipped"):
                self.show_notification(
                    "Sekt\u00f6r web ve mobil \u00e7al\u0131\u015fma alan\u0131na uyguland\u0131.",
                    "success",
                )
            pending_sector = self._pending_sector_sync
            self._pending_sector_sync = None
            self._sector_sync_worker = None
            if pending_sector and pending_sector != sector_id:
                QTimer.singleShot(
                    0,
                    lambda: self._sync_sector_to_web(pending_sector),
                )

        worker.completed.connect(completed)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def apply_display_profile(self):
        profile = self.db.get_setting("display_profile", "auto")
        # Simplified logic for mixin
        if profile == "laptop": self.setMinimumSize(1080, 700)
        else: self.setMinimumSize(1280, 800)
