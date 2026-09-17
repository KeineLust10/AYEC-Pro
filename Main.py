# -*- coding: utf-8 -*-

# --- VIRTUAL ENVIRONMENT REDIRECTION ---
import importlib
import logging
import multiprocessing
import os
import subprocess
import sys
import threading
import traceback
import faulthandler


def _configure_software_webengine():
    """Configure Chromium before any Qt module can initialize WebEngine."""
    os.environ["QT_QUICK_BACKEND"] = "software"
    os.environ["QT_OPENGL"] = "software"
    os.environ["QT_DEVICE_PIXEL_RATIO"] = "0"
    fallback_flags = [
        "--disable-gpu",
        "--disable-gpu-compositing",
        "--disable-gpu-vsync",
        "--disable-3d-apis",
        "--disable-accelerated-2d-canvas",
        "--disable-accelerated-video-decode",
        "--disable-features=Vulkan,UseSkiaRenderer",
    ]
    existing = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "").split()
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = " ".join(
        [*existing, *(flag for flag in fallback_flags if flag not in existing)]
    )


_configure_software_webengine()

# Segfault/C-level crash'ları da dosyaya yaz
try:
    _crash_log = open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "crash_segfault.log"),
        "w",
        encoding="utf-8",
    )
    faulthandler.enable(file=_crash_log)
except Exception:
    faulthandler.enable()

from src.utils.startup_profiler import startup_finish, startup_mark, startup_span

startup_mark("main.python_imports.ready")

from PyQt6.QtCore import QCoreApplication, QEventLoop, QThread, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import QApplication, QDialog, QSplashScreen

from src.utils.path_helper import PathHelper
from src.desktop_runtime import (
    DbFullInitWorker,
    prepare_external_runtime,
    run_backend_server,
    run_healthcheck,
    setup_logging,
)
from src.utils.desktop_service_policy import (
    auto_web_sync_enabled,
    local_api_enabled,
)

startup_mark("main.qt_imports.ready")
# Single-instance guard.
# ---------------------------------------------------------------------------
_shared_memory = None  # Keep a module-level reference for the application lifetime.

def _ensure_single_instance():
    """Return False when another AYEC Pro instance already owns the lock."""

    global _shared_memory
    try:
        from PyQt6.QtCore import QSharedMemory
        mem = QSharedMemory("AYECPro_SingleInstance_2026")
        if mem.attach():          # Another process already owns the shared memory.
            mem.detach()
            return False
        if not mem.create(1):     # Allocate the marker for this first instance.
            # An allocation failure without an attached peer is safe to ignore.
            return True
        _shared_memory = mem      # Keep the marker alive until program exit.
        return True
    except Exception as exc:
        logging.warning("Single-instance check failed (skipping): %s", exc)
        return True


def main():
    multiprocessing.freeze_support()
    startup_mark("main.enter")
    prepare_external_runtime()

    if os.name == "nt":
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "AYECPro.Desktop.2"
            )
        except Exception:
            pass

    from src.utils.web_sync_client import DEFAULT_WEB_SYNC_URL
    os.environ.setdefault("AYEC_WEB_SYNC_URL", DEFAULT_WEB_SYNC_URL)

    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL, True)

    try:
        importlib.import_module("PyQt6.QtWebEngineWidgets")
    except Exception as exc:
        logging.warning("QtWebEngine preload failed: %s", exc)
    startup_mark("qt_webengine.preload.ready")

    setup_logging()
    app = QApplication(sys.argv)
    app.setApplicationName("AYEC Pro")
    app.setOrganizationName("AYEC Pro")
    app.setApplicationDisplayName("AYEC Pro")
    startup_mark("qt_application.ready")
    from src.utils.context_menu_guard import install_context_menu_guard
    from src.utils.message_helper import install_modern_messagebox_hooks, show_error
    from src.utils.text_encoding import install_qt_text_sanitizer

    app.setWindowIcon(PathHelper.get_app_icon())
    install_qt_text_sanitizer()
    install_context_menu_guard()
    startup_mark("qt_guards.ready")

    if any(arg in ("--healthcheck", "--smoke") for arg in sys.argv[1:]):
        sys.exit(run_healthcheck())

    # --- Single-instance guard ---
    if not _ensure_single_instance():
        from PyQt6.QtWidgets import QMessageBox
        msg = QMessageBox()
        msg.setWindowTitle("AYEC Pro")
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setText("AYEC Pro zaten \u00e7al\u0131\u015f\u0131yor!")
        msg.setInformativeText(
            "Ayn\u0131 anda yaln\u0131zca bir AYEC Pro penceresi a\u00e7\u0131labilir.\n"
            "L\u00fctfen g\u00f6rev \u00e7ubu\u011fundaki mevcut pencereyi kullan\u0131n."
        )
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()
        sys.exit(0)
    # --- /Single-instance guard ---

    install_modern_messagebox_hooks()
    startup_mark("single_instance.ready")

    base_assets = PathHelper.get_resource_path("assets")
    splash_path = os.path.join(base_assets, "app_icon.png")
    splash = None
    show_splash = os.environ.get("AYEC_SHOW_SPLASH", "0") == "1"
    if show_splash and os.path.exists(splash_path):
        pixmap = QPixmap(splash_path)
        splash = QSplashScreen(pixmap, Qt.WindowType.WindowStaysOnTopHint)
        splash.show()
        splash.showMessage(
            "Baslatiliyor...",
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
            Qt.GlobalColor.white,
        )
    startup_mark("splash.ready")

    try:
        from src.utils.web_sync_client import apply_pending_restore

        restore_db_name = os.environ.get("AYEC_DB_NAME", "ayecpro.db")
        restore_result = apply_pending_restore(PathHelper.get_db_path(restore_db_name))
        if restore_result.get("applied"):
            logging.info("Remote support restore applied: %s", restore_result)
    except Exception as exc:
        logging.error("Pending remote restore was not applied: %s", exc)
    startup_mark("pending_restore.ready")

    try:
        from src.database import Database

        with startup_span("database.auth.open"):
            db = Database(init_mode="auth")
    except Exception as exc:
        show_error(None, "Hata", f"Veritabani baglantisi kurulamadi: {exc}")
        sys.exit(1)
    startup_mark("database.auth.ready")

    from src.utils.auth_manager import AuthManager

    auth_manager = AuthManager(db)
    login_status = {"success": False, "user": None}
    saved_token = auth_manager.get_saved_token()
    server_bound_tenant = str(
        db.get_setting("web_sync_tenant_id", "") or ""
    ).strip()
    login_window = None

    if saved_token and not server_bound_tenant and auth_manager.auto_login(saved_token):
        login_status["success"] = True
        login_status["user"] = auth_manager.current_user
    else:
        from src.ui.modern_login_window import ModernLoginWindow

        if splash:
            splash.hide()
        login_window = ModernLoginWindow(db)
        login_window.login_successful.connect(
            lambda user: login_status.update({"success": True, "user": user})
        )
        if (
            login_window.exec() != QDialog.DialogCode.Accepted
            or not login_status["success"]
        ):
            sys.exit(0)
        if splash:
            splash.show()
    startup_mark("authentication.ready")

    if splash:
        splash.showMessage(
            "Veriler hazirlaniyor...",
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
            Qt.GlobalColor.white,
        )

    if not hasattr(app, "_active_threads"):
        app._active_threads = set()
    loop = QEventLoop()
    worker = DbFullInitWorker(db)
    app._active_threads.add(worker)
    worker.completed.connect(lambda ok, err: loop.quit())
    worker.start()
    loop.exec()
    worker.wait()
    app._active_threads.discard(worker)
    startup_mark("database.full.ready")

    try:
        from core import SectorManager

        sector_manager = SectorManager(db)
        current_sector = db.get_internal_setting("current_sector", "teknik_servis")
        sector_manager.load_sector(current_sector)
        logging.info("Plugin system initialized with sector: %s", current_sector)
    except Exception as exc:
        logging.warning("Plugin system init failed (using fallback): %s", exc)
        sector_manager = None
    startup_mark("sector_manager.ready")

    try:
        from src.ui.main_window import MainWindow

        with startup_span("main_window.create"):
            main_window = MainWindow(
                db=db,
                user_data=login_status["user"],
                sector_manager=sector_manager,
            )
        main_window._web_sync_password = (
            getattr(login_window, "_last_login_password", "") if login_window else ""
        )
        main_window.show()
        main_window.showMaximized()
        PathHelper.apply_windows_taskbar_icon(main_window)
        startup_mark("main_window.shown")
        if splash:
            splash.finish(main_window)
    except Exception as exc:
        logging.critical(
            "Main window launch failed: %s\n%s", exc, traceback.format_exc()
        )
        show_error(None, "Hata", f"Uygulama baslatilamadi: {exc}")
        sys.exit(1)

    def start_backend_server_deferred():
        if getattr(app, "_backend_thread", None):
            return
        server_thread = threading.Thread(
            target=run_backend_server,
            name="AYEC-Local-API",
            daemon=True,
        )
        app._backend_thread = server_thread
        server_thread.start()
        startup_mark("backend.thread.started")

    def finish_first_paint():
        startup_mark("main_window.first_paint")
        startup_finish()

    QTimer.singleShot(0, finish_first_paint)
    main_window.configure_auto_web_sync(auto_web_sync_enabled(db))
    if local_api_enabled(db):
        QTimer.singleShot(2500, start_backend_server_deferred)
    if login_window:
        login_window._last_login_password = ""

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
