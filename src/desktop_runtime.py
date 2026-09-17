"""Reusable desktop runtime services."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from src.utils.path_helper import PathHelper
from src.utils.desktop_service_policy import local_api_host


def prepare_external_runtime() -> None:
    executable_name = os.path.basename(sys.executable).lower()
    if executable_name == "python.exe":
        return
    runtime_dir = os.path.dirname(os.path.abspath(sys.executable))
    sys.path[:] = [entry for entry in sys.path if isinstance(entry, str)]
    if runtime_dir not in sys.path:
        sys.path.insert(0, runtime_dir)
    try:
        import site

        site.USER_SITE = runtime_dir
        site.getsitepackages = lambda: [runtime_dir]
    except Exception:
        pass


def setup_logging() -> None:
    handlers = [logging.StreamHandler(sys.stdout)]
    try:
        handlers.insert(0, logging.FileHandler(PathHelper.get_log_path(), encoding="utf-8"))
    except Exception as error:
        print(f"WARNING: file logging disabled, console-only fallback active: {error}", file=sys.stderr)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )
    from src.utils.logger import install_exception_hook

    install_exception_hook()


def run_backend_server() -> None:
    try:
        import uvicorn

        try:
            backend_root = Path(PathHelper.get_resource_path("backend"))
            backend_root_text = str(backend_root)
            if backend_root.is_dir() and backend_root_text not in sys.path:
                sys.path.insert(0, backend_root_text)
            from backend.main import app as backend_app
        except ImportError as error:
            logging.warning("Local API module could not be loaded: %s", error)
            return
        config = uvicorn.Config(
            backend_app,
            host=local_api_host(),
            port=8000,
            log_level="error",
            loop="asyncio",
            log_config=None,
            access_log=False,
        )
        uvicorn.Server(config).run()
    except Exception as error:
        logging.error("Server startup error: %s", error)


class DbFullInitWorker(QThread):
    completed = pyqtSignal(bool, str)

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self._db = db

    def run(self) -> None:
        try:
            self._db.ensure_full_initialized()
            self.completed.emit(True, "")
        except Exception as error:
            self.completed.emit(False, str(error))


def run_healthcheck() -> int:
    checks: list[bool] = []

    def record(name: str, ok: bool, detail: str = "") -> None:
        line = f"{name}={'OK' if ok else 'FAIL'}"
        if detail:
            line += f" detail={detail}"
        print(line)
        checks.append(ok)

    try:
        from core import SectorManager
        from src.database import Database
        from src.ui.main_window import MainWindow
        from src.utils.auth_manager import AuthManager
    except Exception as error:
        logging.exception("Compiled healthcheck imports failed")
        record("healthcheck_imports", False, str(error))
        return 1

    record("venv", True, sys.executable)
    try:
        db = Database(init_mode="auth")
        db.ensure_full_initialized()
        record("database", True, "full_schema")
    except Exception as error:
        record("database", False, str(error))
        return 1
    try:
        AuthManager(db)
        record("auth_manager", True)
    except Exception as error:
        record("auth_manager", False, str(error))
        return 1
    try:
        import pandas as pd
        import pytz

        pd.Timestamp("2026-01-01T00:00:00Z")
        record("pandas_runtime", True, str(pytz.__version__))
    except Exception as error:
        record("pandas_runtime", False, str(error))
        return 1
    try:
        import fitz

        document = fitz.open()
        document.close()
        record("pymupdf_runtime", True)
    except Exception as error:
        record("pymupdf_runtime", False, str(error))
        return 1
    try:
        import importlib

        runtime_modules = (
            "cv2",
            "easyocr",
            "edge_tts",
            "google.protobuf",
            "paddle",
            "paddleocr",
            "pdf2docx",
            "pdfplumber",
            "pytesseract",
            "pyaudio",
            "pyttsx3",
            "scipy",
            "skimage",
            "speech_recognition",
            "torch",
            "torchvision",
        )
        for runtime_module in runtime_modules:
            try:
                importlib.import_module(runtime_module)
            except Exception as module_error:
                raise RuntimeError(
                    f"{runtime_module}: {module_error}"
                ) from module_error

        record("ocr_ai_runtime", True)
    except Exception as error:
        record("ocr_ai_runtime", False, str(error))
        return 1
    try:
        current_sector = db.get_internal_setting("current_sector", "teknik_servis")
        sector_manager = SectorManager(db)
        sector_manager.load_sector(current_sector)
        record("sector_manager", True, current_sector)
    except Exception as error:
        record("sector_manager", False, str(error))
        return 1
    try:
        window = MainWindow(db=db, user_data=None, sector_manager=sector_manager)
        record("main_window", True, type(window).__name__)
        window.deleteLater()
    except Exception as error:
        record("main_window", False, str(error))
        return 1
    print(f"healthcheck={'PASS' if all(checks) else 'FAIL'}")
    return 0 if all(checks) else 1
