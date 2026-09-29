# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import json
from datetime import datetime
from PyQt6.QtCore import QObject, Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import QMessageBox
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

    def __init__(self, url, dest_path, expected_sha256, parent=None):
        super().__init__(parent)
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

    def __init__(self, current_version, parent=None):
        super().__init__(parent)
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
                
        except Exception as e:
            logger.error("Update check failed: %s", e)
            self.finished.emit(False, "", "", "", "")

    @staticmethod
    def _compare_versions(new, current):
        try:
            v1 = [int(x) for x in str(new).split('.')]
            v2 = [int(x) for x in str(current).split('.')]
            return v1 > v2
        except Exception as e:
            logger.error("Version compare error: %s", e)
            return False

class UpdateManager(QObject):
    def __init__(self, db, parent_window):
        super().__init__()
        self.db = db
        self.parent = parent_window
        self.check_worker = None
        self.download_worker = None
        self.download_path = ""
        self.new_version = ""
        self.download_url = ""
        self.download_sha256 = ""
        self.update_found = False
        self.download_completed = False
        self._ready_prompted_once = False

    def _state_path(self):
        return os.path.join(PathHelper.get_app_data_dir(), "update_state.json")

    def _save_ready_state(self):
        payload = {"version": self.new_version, "path": self.download_path, "sha256": self.download_sha256}
        try:
            with open(self._state_path(), "w", encoding="utf-8") as handle:
                json.dump(payload, handle)
        except Exception as exc:
            logger.warning("Update state save failed: %s", exc)

    def _load_ready_state(self):
        try:
            with open(self._state_path(), "r", encoding="utf-8") as handle:
                state = json.load(handle)
            path = str(state.get("path") or "")
            digest = str(state.get("sha256") or "")
            if path and os.path.isfile(path) and state.get("version") and verify_update_file(path, digest):
                return state
        except Exception:
            pass
        return None

    def _show_ready_dialog(self):
        if self._ready_prompted_once:
            return
        self._ready_prompted_once = True
        dialog = QMessageBox(self.parent)
        dialog.setWindowTitle("G\u00fcncelleme haz\u0131r")
        dialog.setText(f"v{self.new_version} g\u00fcncelleme dosyan\u0131z haz\u0131r.")
        dialog.setInformativeText("Uygulama kapanacak ve yeni s\u00fcr\u00fcm kurulacak.")
        install_button = dialog.addButton("\u015eimdi g\u00fcncelle", QMessageBox.ButtonRole.AcceptRole)
        dialog.addButton("Daha sonra g\u00fcncelle", QMessageBox.ButtonRole.RejectRole)
        dialog.exec()
        if dialog.clickedButton() is install_button:
            self.install_update()
        else:
            self._save_ready_state()

    def check_for_updates(self):
        if self.check_worker and self.check_worker.isRunning():
            return
        if self.download_worker and self.download_worker.isRunning():
            return
        try:
            version_path = PathHelper.get_resource_path("version.txt")
            with open(version_path, "r", encoding="utf-8") as handle:
                current_version = handle.read().strip()
        except Exception as exc:
            logger.warning("Local version read failed: %s", exc)
            current_version = "0.0.0"
        saved = self._load_ready_state()
        if saved:
            if not UpdateWorker._compare_versions(saved["version"], current_version):
                try:
                    os.remove(self._state_path())
                except OSError:
                    pass
                saved = None
        if saved:
            self.new_version = str(saved["version"])
            self.download_path = str(saved["path"])
            self.download_sha256 = str(saved.get("sha256") or "")
            self.download_completed = True
            if hasattr(self.parent, "app_header"):
                self.parent.app_header.show_update_button(self.new_version, "ready")
            self._show_ready_dialog()
            return
        self.check_worker = UpdateWorker(current_version, self)
        self.check_worker.finished.connect(self._on_check_finished)
        self.check_worker.start()

    def _on_check_finished(self, has_update, new_version, url, notes, sha256):
        if has_update:
            self.update_found = True
            self.new_version = new_version
            self.download_url = url
            self.download_sha256 = sha256
            
            # 1. Update App Header button
            if hasattr(self.parent, "app_header"):
                header = self.parent.app_header
                if hasattr(header, "show_update_button"):
                    header.show_update_button(new_version, "found")
            
            # 2. Notify user with toast
            self.parent.show_notification(
                f"Yeni Sürüm Bulundu: v{new_version}. Arka planda indiriliyor...",
                "info"
            )
            
            # 3. Start background download
            self._start_download()

    def _start_download(self):
        dest_folder = PathHelper.get_app_data_dir()
        filename = "AYEC_Update.exe"
        self.download_path = os.path.join(dest_folder, filename)

        if hasattr(self.parent, "app_header"):
            header = self.parent.app_header
            if hasattr(header, "show_update_button"):
                header.show_update_button(self.new_version, "downloading", 0)

        self.download_worker = DownloadWorker(
            self.download_url,
            self.download_path,
            self.download_sha256,
            self,
        )
        self.download_worker.progress.connect(self._on_download_progress)
        self.download_worker.finished.connect(self._on_download_finished)
        self.download_worker.start()

    def _on_download_progress(self, percent):
        if hasattr(self.parent, "app_header"):
            header = self.parent.app_header
            if hasattr(header, "show_update_button"):
                header.show_update_button(self.new_version, "downloading", percent)

    def _on_download_finished(self, success, path):
        if success:
            self.download_completed = True
            self._save_ready_state()
            if hasattr(self.parent, "app_header"):
                header = self.parent.app_header
                if hasattr(header, "show_update_button"):
                    header.show_update_button(self.new_version, "ready")
            
            self.parent.show_notification(
                "Yeni güncelleme yüklenmeye hazır!",
                "success"
            )
            self._show_ready_dialog()
        else:
            logger.error("Background update download failed: %s", path)
            self.parent.show_notification(
                "Güncelleme indirilemedi.",
                "error"
            )

    def install_update(self):
        if self.download_completed and os.path.exists(self.download_path):
            try:
                if not verify_update_file(
                    self.download_path,
                    self.download_sha256,
                ):
                    raise RuntimeError("Update package verification failed.")
                if hasattr(self.db, "backup_database"):
                    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_path = self.db.backup_database(
                        target_name=f"before_update_{stamp}.db"
                    )
                    if not backup_path:
                        raise RuntimeError("Pre-update database backup failed.")
                try:
                    os.remove(self._state_path())
                except OSError:
                    pass
                subprocess.Popen(self.download_path)
                sys.exit(0)
            except Exception as e:
                logger.error("Failed to run installer: %s", e)
