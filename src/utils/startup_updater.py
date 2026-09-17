# -*- coding: utf-8 -*-

import os
import subprocess
import sys
import urllib.error

from PyQt6.QtCore import QObject, QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import QDialog as QtDialog, QLabel, QProgressBar, QVBoxLayout

from src.utils.logger import logger
from src.utils.path_helper import PathHelper
from src.utils.secure_update import (
    DEFAULT_UPDATE_BASE_URL,
    download_verified_update,
    fetch_update_manifest,
    verify_update_file,
)


class DownloadWorker(QThread):
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(int)

    def __init__(self, url, dest_path, expected_sha256):
        super().__init__()
        self.url = url
        self.dest_path = dest_path
        self.expected_sha256 = expected_sha256

    def run(self):
        try:
            path = download_verified_update(
                self.url,
                self.dest_path,
                self.expected_sha256,
                progress_callback=self.progress.emit,
            )
            self.finished.emit(True, path)
        except Exception as exc:
            self.finished.emit(False, str(exc))


class UpdateWorker(QThread):
    finished = pyqtSignal(bool, str, str, str, str)

    def __init__(self, current_version):
        super().__init__()
        self.current_version = current_version
        self.raw_url = f"{DEFAULT_UPDATE_BASE_URL}/version.json"

    def run(self):
        try:
            manifest = fetch_update_manifest(self.raw_url)
            if self._compare_versions(manifest.version, self.current_version):
                self.finished.emit(
                    True,
                    manifest.version,
                    manifest.url,
                    manifest.notes,
                    manifest.sha256,
                )
            else:
                self.finished.emit(
                    False,
                    manifest.version,
                    "",
                    manifest.notes,
                    "",
                )
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                logger.warning("Guncelleme sunucusu su an ulasilamiyor (404).")
            else:
                logger.error("Guncelleme kontrolu HTTP hatasi: %s", exc)
            self.finished.emit(False, "", "", "", "")
        except Exception as exc:
            logger.error("Startup update check failed: %s", exc)
            self.finished.emit(False, "", "", "", "")

    def _compare_versions(self, new, current):
        try:
            v1 = [int(x) for x in str(new).split(".")]
            v2 = [int(x) for x in str(current).split(".")]
            return v1 > v2
        except Exception as exc:
            logger.error("Startup version compare error: %s", exc)
            return False


class UpdateSplash(QtDialog):
    """Splash screen for checking updates."""

    def __init__(self, download_url, version, expected_sha256):
        super().__init__()
        self.expected_sha256 = expected_sha256
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setFixedSize(400, 150)
        self.setStyleSheet("background-color: #2c3e50; color: white; border: 2px solid #3498db;")

        layout = QVBoxLayout(self)

        self.lbl_status = QLabel(f"Yeni surum (v{version}) bulundu.\nIndiriliyor, lutfen bekleyiniz...")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self.lbl_status)

        self.pbar = QProgressBar()
        self.pbar.setStyleSheet(
            """
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                text-align: center;
                background-color: #ecf0f1;
                color: #2c3e50;
            }
            QProgressBar::chunk {
                background-color: #27ae60;
                width: 10px;
                margin: 0.5px;
            }
            """
        )
        self.pbar.setValue(0)
        layout.addWidget(self.pbar)

        download_path = os.path.join(PathHelper.get_app_data_dir(), "AYEC_Update.exe")
        self.worker = DownloadWorker(
            download_url,
            download_path,
            expected_sha256,
        )
        self.worker.progress.connect(self.pbar.setValue)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def on_finished(self, success, path):
        if success:
            self.lbl_status.setText("Indirme tamamlandi. Baslatiliyor...")
            QThread.msleep(1000)
            try:
                if not verify_update_file(path, self.expected_sha256):
                    raise RuntimeError("Update package verification failed.")
                subprocess.Popen(path)
                sys.exit(0)
            except Exception as exc:
                self.lbl_status.setText(f"Baslatma hatasi: {exc}")
                self.reject()
        else:
            self.lbl_status.setText(f"Indirme basarisiz: {path}")
            self.reject()


class StartupUpdater(QObject):
    check_finished = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.check_worker = None

    def check(self):
        try:
            with open("version.txt", "r", encoding="utf-8") as handle:
                current_version = handle.read().strip()
        except Exception as exc:
            logger.warning("Startup local version read failed, using fallback: %s", exc)
            current_version = "0.0.0"

        self.check_worker = UpdateWorker(current_version)
        self.check_worker.finished.connect(self.on_check_finished)
        self.check_worker.start()

    def on_check_finished(self, has_update, new_version, url, notes="", sha256=""):
        if has_update:
            splash = UpdateSplash(url, new_version, sha256)
            splash.exec()
            self.check_finished.emit(True)
            return

        self.check_finished.emit(True)
