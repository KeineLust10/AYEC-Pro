# -*- coding: utf-8 -*-

# --- VIRTUAL ENVIRONMENT REDIRECTION ---
import importlib
import logging
import os
import subprocess
import sys
import threading
import traceback
import faulthandler

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

from PyQt6.QtCore import QCoreApplication, QEventLoop, QThread, Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QApplication, QDialog, QSplashScreen

from core import SectorManager
from src.database import Database
from src.ui.main_window import MainWindow
from src.ui.modern_login_window import ModernLoginWindow
from src.utils.auth_manager import AuthManager
from src.utils.context_menu_guard import install_context_menu_guard
from src.utils.message_helper import install_modern_messagebox_hooks, show_error
from src.utils.path_helper import PathHelper


def _ensure_venv():
    if "RELAUNCHED_IN_VENV" in os.environ:
        return

    base_dir = os.path.dirname(os.path.abspath(__file__))
    venv_candidates = [
        os.path.join(base_dir, ".venv_active", "Scripts", "python.exe"),
        os.path.join(base_dir, ".venv", "Scripts", "python.exe"),
        os.path.join(base_dir, ".venv_ai", "Scripts", "python.exe"),
        os.path.join(base_dir, "venv", "Scripts", "python.exe"),
    ]

    for venv_python in venv_candidates:
        if (
            os.path.exists(venv_python)
            and sys.executable.lower() != venv_python.lower()
        ):
            os.environ["RELAUNCHED_IN_VENV"] = "1"
            subprocess.call([venv_python] + sys.argv)
            sys.exit()


_ensure_venv()
# --- END VIRTUAL ENVIRONMENT REDIRECTION ---


def setup_logging():
    handlers = [logging.StreamHandler(sys.stdout)]
    try:
        handlers.insert(
            0, logging.FileHandler(PathHelper.get_log_path(), encoding="utf-8")
        )
    except Exception as exc:
        print(
            f"WARNING: file logging disabled, console-only fallback active: {exc}",
            file=sys.stderr,
        )

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )
    from src.utils.logger import install_exception_hook

    install_exception_hook()


def run_backend_server():
    """Start the FastAPI backend in a daemon thread."""
    try:
        import uvicorn

        try:
            from backend.main import app as backend_app
        except ImportError:
            try:
                from src.utils.server_main import app as backend_app
            except ImportError:
                logging.warning("Backend module not found. Server will not start.")
                return

        config = uvicorn.Config(
            backend_app,
            host="0.0.0.0",
            port=8000,
            log_level="error",
            loop="asyncio",
        )
        server = uvicorn.Server(config)
        server.run()
    except Exception as exc:
        logging.error("Server startup error: %s", exc)


class DbFullInitWorker(QThread):
    finished = pyqtSignal(bool, str)

    def __init__(self, db):
        super().__init__()
        self._db = db

    def run(self):
        try:
            self._db.ensure_full_initialized()
            self.finished.emit(True, "")
        except Exception as exc:
            self.finished.emit(False, str(exc))


def run_healthcheck():
    """Run a short startup probe without entering the interactive login flow."""
    checks = []

    def record(name, ok, detail=""):
        status = "OK" if ok else "FAIL"
        line = f"{name}={status}"
        if detail:
            line += f" detail={detail}"
        print(line)
        checks.append(ok)

    record("venv", True, sys.executable)

    try:
        db = Database(init_mode="auth")
        record("database", True)
    except Exception as exc:
        record("database", False, str(exc))
        return 1

    try:
        AuthManager(db)
        record("auth_manager", True)
    except Exception as exc:
        record("auth_manager", False, str(exc))
        return 1

    try:
        current_sector = db.get_internal_setting("current_sector", "teknik_servis")
        sector_manager = SectorManager(db)
        sector_manager.load_sector(current_sector)
        record("sector_manager", True, current_sector)
    except Exception as exc:
        record("sector_manager", False, str(exc))
        return 1

    try:
        window = MainWindow(db=db, user_data=None, sector_manager=sector_manager)
        record("main_window", True, type(window).__name__)
        window.deleteLater()
    except Exception as exc:
        record("main_window", False, str(exc))
        return 1

    print(f"healthcheck={'PASS' if all(checks) else 'FAIL'}")
    return 0 if all(checks) else 1


def main():
    os.environ["QT_QUICK_BACKEND"] = "software"
    os.environ["QT_OPENGL"] = "software"
    os.environ["QT_DEVICE_PIXEL_RATIO"] = "0"

    existing_webengine_flags = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "").strip()
    fallback_flags = [
        "--disable-gpu",
        "--disable-gpu-compositing",
        "--disable-gpu-vsync",
        "--disable-features=Vulkan,UseSkiaRenderer",
    ]
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = " ".join(
        flag for flag in [existing_webengine_flags, *fallback_flags] if flag
    ).strip()

    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL, True)

    try:
        importlib.import_module("PyQt6.QtWebEngineWidgets")
    except Exception as exc:
        logging.warning("QtWebEngine preload failed: %s", exc)

    setup_logging()
    app = QApplication(sys.argv)
    install_context_menu_guard()

    if any(arg in ("--healthcheck", "--smoke") for arg in sys.argv[1:]):
        sys.exit(run_healthcheck())

    install_modern_messagebox_hooks()

    base_assets = os.path.join(os.path.dirname(__file__), "assets")
    splash_path = os.path.join(base_assets, "app_icon.png")
    splash = None
    if os.path.exists(splash_path):
        pixmap = QPixmap(splash_path)
        splash = QSplashScreen(pixmap, Qt.WindowType.WindowStaysOnTopHint)
        splash.show()
        splash.showMessage(
            "Baslatiliyor...",
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
            Qt.GlobalColor.white,
        )
        QApplication.processEvents()

    server_thread = threading.Thread(target=run_backend_server, daemon=True)
    server_thread.start()

    try:
        db = Database(init_mode="auth")
    except Exception as exc:
        show_error(None, "Hata", f"Veritabani baglantisi kurulamadi: {exc}")
        sys.exit(1)

    auth_manager = AuthManager(db)
    login_status = {"success": False, "user": None}
    saved_token = auth_manager.get_saved_token()

    if saved_token and auth_manager.auto_login(saved_token):
        login_status["success"] = True
        login_status["user"] = auth_manager.current_user
    else:
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

    if splash:
        splash.showMessage(
            "Veriler hazirlaniyor...",
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
            Qt.GlobalColor.white,
        )

    loop = QEventLoop()
    worker = DbFullInitWorker(db)
    worker.finished.connect(lambda ok, err: loop.quit())
    worker.start()
    loop.exec()

    try:
        sector_manager = SectorManager(db)
        current_sector = db.get_internal_setting("current_sector", "teknik_servis")
        sector_manager.load_sector(current_sector)
        logging.info("Plugin system initialized with sector: %s", current_sector)
    except Exception as exc:
        logging.warning("Plugin system init failed (using fallback): %s", exc)
        sector_manager = None

    try:
        main_window = MainWindow(
            db=db,
            user_data=login_status["user"],
            sector_manager=sector_manager,
        )
        try:
            main_window._load_initial_page()
            QApplication.processEvents()
        except Exception as preload_err:
            logging.warning("Initial page preload skipped: %s", preload_err)
        main_window.show()
        main_window.showMaximized()
        if splash:
            splash.finish(main_window)
    except Exception as exc:
        logging.critical(
            "Main window launch failed: %s\n%s", exc, traceback.format_exc()
        )
        show_error(None, "Hata", f"Uygulama baslatilamadi: {exc}")
        sys.exit(1)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
