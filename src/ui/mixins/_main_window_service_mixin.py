# -*- coding: utf-8 -*-

import os
import glob
import logging
import json
from datetime import datetime
from PyQt6.QtCore import QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication
from src.utils.logger import logger
from src.utils.performance_monitor import perf_span
from src.utils.startup_profiler import startup_mark
from src.utils.system_config import SystemConfig


class GeminiStartupModelListWorker(QThread):
    finished = pyqtSignal(bool, object)

    def __init__(self, keys_list, parent=None):
        super().__init__(parent)
        self.keys_list = keys_list

    def run(self):
        try:
            from src.utils.ai_service import AIService
            service = AIService(self.keys_list)
            models = service.get_available_models()
            self.finished.emit(bool(models), models or [])
        except Exception as exc:
            self.finished.emit(False, str(exc))


class IncomeTaxTariffRefreshWorker(QThread):
    completed = pyqtSignal(bool, object)

    def run(self):
        try:
            from src.utils.income_tax_tariff_service import IncomeTaxTariffService

            result = IncomeTaxTariffService().refresh_if_due()
            self.completed.emit(True, result)
        except Exception as exc:
            self.completed.emit(False, str(exc))


class MainWindowServiceMixin:
    """Background tasks, service management, and database context switching."""

    def schedule_ui_task(self, priority, callback, label=None):
        if not callable(callback): return
        pri = priority if priority in self._ui_task_counters else "idle"
        idx = self._ui_task_counters[pri]; self._ui_task_counters[pri] += 1
        base = {"immediate": 0, "soon": 500, "idle": 10000}[pri]
        step = {"immediate": 60, "soon": 220, "idle": 700}[pri]
        delay = base + (idx * step)
        lbl = label or getattr(callback, "__qualname__", str(callback))
        QTimer.singleShot(delay, lambda: self._run_ui_task(callback, pri, lbl))

    def _run_ui_task(self, cb, pri, lbl):
        with perf_span(f"ui_task.{pri}.{lbl}"): cb()

    def start_initial_tasks(self):
        # License verification is local/network-bound and must not delay the
        # first interactive page render.
        self.schedule_ui_task("soon", self.license_service.start_license_check, "startup.license_check")
        self.schedule_ui_task("soon", self.refresh_notification_bell, "startup.refresh_notification_bell")
        self.schedule_ui_task("soon", self._prewarm_theme_cache, "startup.prewarm_theme_cache")
        self.schedule_ui_task("soon", self._ensure_assistant_manager, "startup.assistant_manager")
        self.schedule_ui_task("idle", self._start_assistant_services, "startup.assistant_services")
        self.schedule_ui_task("idle", self.fiscal_service.run_startup_check, "startup.fiscal_check")
        self.schedule_ui_task("idle", self.refresh_gemini_models_once, "startup.gemini_models")
        self.schedule_ui_task("idle", self.update_manager.check_for_updates, "startup.update_check")
        self.schedule_ui_task("idle", self._start_web_sync_event_listener, "startup.web_sync_events")
        # Açılış selamı — UI tamamen hazır olduktan 5 saniye sonra çalışır
        QTimer.singleShot(8000, self._run_assistant_greeting)
        QTimer.singleShot(20000, self._run_assistant_greeting)
        QTimer.singleShot(180000, self._run_delayed_daily_backup)
        QTimer.singleShot(600000, self._refresh_income_tax_tariffs)
        self.notification_timer = QTimer(self); self.notification_timer.timeout.connect(self.refresh_notification_bell); self.notification_timer.start(60000)

    def _ensure_assistant_manager(self):
        assistant = getattr(self, "assistant", None)
        if assistant is not None:
            return assistant
        with perf_span("assistant_manager.create"):
            from src.services.assistant_manager import AssistantManager

            assistant = AssistantManager(self)
            self.assistant = assistant
        startup_mark("assistant_manager.ready")
        return assistant

    def _start_assistant_services(self):
        assistant = self._ensure_assistant_manager()
        assistant.start_voice_assistant()
        assistant.run_assistant_monitoring()

    def _run_assistant_greeting(self):
        self._ensure_assistant_manager().startup_greeting()

    def _prewarm_theme_cache(self):
        from src.utils.theme_manager import ThemeManager

        ThemeManager.prewarm_themes()

    def _refresh_income_tax_tariffs(self):
        worker = getattr(self, "_income_tax_tariff_worker", None)
        if worker and worker.isRunning():
            return
        worker = IncomeTaxTariffRefreshWorker(self)
        self._income_tax_tariff_worker = worker
        app = QApplication.instance()
        if app:
            if not hasattr(app, "_active_threads"):
                app._active_threads = set()
            app._active_threads.add(worker)

        def completed(ok, result):
            if app:
                app._active_threads.discard(worker)
            if ok:
                logger.info("Income tax tariffs checked: %s", result)
            else:
                logger.warning("Income tax tariff refresh failed: %s", result)
            self._income_tax_tariff_worker = None

        worker.completed.connect(completed)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def refresh_gemini_models_once(self):
        if getattr(self, "_gemini_startup_models_requested", False):
            return
        self._gemini_startup_models_requested = True
        try:
            keys_str = self.db.get_setting("gemini_api_key", "")
            keys_list = [k.strip() for k in str(keys_str or "").replace(",", "\n").split("\n") if k.strip()]
            if not keys_list:
                logger.info("Gemini startup model list skipped: API key is not configured.")
                return
            self._gemini_startup_model_worker = GeminiStartupModelListWorker(keys_list, self)
            self._gemini_startup_model_worker.finished.connect(self._on_gemini_startup_models_listed)
            self._gemini_startup_model_worker.finished.connect(self._gemini_startup_model_worker.deleteLater)
            self._gemini_startup_model_worker.start()
            logger.info("Gemini startup model list started.")
        except Exception as e:
            logger.warning(f"Gemini startup model list could not start: {e}")

    def _on_gemini_startup_models_listed(self, success, result):
        try:
            if success and result:
                models = [str(m).replace("models/", "") for m in result]
                payload = json.dumps(models, ensure_ascii=False)
                if hasattr(self.db, "set_internal_setting"):
                    self.db.set_internal_setting("gemini_available_models_cache", payload)
                else:
                    self.db.set_setting("gemini_available_models_cache", payload)
                logger.info("Gemini startup model list cached %s model(s).", len(models))
            else:
                logger.warning(f"Gemini startup model list failed: {result}")
        except Exception as e:
            logger.warning(f"Gemini startup model list result handling failed: {e}")
        finally:
            self._gemini_startup_model_worker = None


    def refresh_notification_bell(self):
        try:
            if str(self.db.get_setting("notifications_enabled", "1")) != "1":
                if hasattr(self.app_header, "notification_bell"):
                    self.app_header.notification_bell.set_count(0)
                return
            try: self.db.ensure_due_vehicle_maintenance_notifications(datetime.now().strftime("%Y-%m-%d"))
            except Exception as e: logger.debug(f"Vehicle maintenance notification refresh skipped: {e}")
            unread = int(self.db.get_unread_count() or 0)
            if hasattr(self.app_header, "notification_bell"): self.app_header.notification_bell.set_count(unread)
        except Exception as e: logger.warning(f"Notification refresh error: {e}")

    def refresh_currency_context(self):
        try:
            for p in list(self.pages.values()):
                if hasattr(p, "request_reload"): p.request_reload()
                elif hasattr(p, "refresh_data"): p.refresh_data()
            self._refresh_active_page()
            self.refresh_side_menu()
        except Exception as e: logger.warning(f"Currency context refresh failed: {e}")

    def load_archived_database(self, archive_name):
        from src.database import Database
        try:
            idx = getattr(self, "_current_page_index", 40)
            self._apply_database_context(Database(archive_name, init_mode="full"), archive_mode=True)
            self._reload_all_pages()
            self._refresh_active_page(idx)
            return True
        except Exception as e:
            logger.warning(f"Load archived database failed: {e}")
            return False

    def return_to_active_database(self):
        try:
            idx = getattr(self, "_current_page_index", 40)
            self._apply_database_context(self._active_db, archive_mode=False)
            self._reload_all_pages()
            self._refresh_active_page(idx)
            return True
        except Exception as e:
            logger.warning(f"Return to active database failed: {e}")
            return False

    def handle_wipe_completed(self):
        self.is_archive_mode = False
        self.db = self._active_db
        try:
            self.db.refresh_current_thread_connection()
            self.db.ensure_default_settings()
            self.db.ensure_full_initialized()
        except Exception as exc:
            logger.error(f"Post-wipe database refresh failed: {exc}")
            self.show_notification("Veritabani yenilenemedi. Programi yeniden baslatin.", "error")
            return
        self._current_page_index = 40
        if hasattr(self, "_install_startup_placeholder"):
            self._install_startup_placeholder()
        QTimer.singleShot(0, self._reload_all_pages)
        QTimer.singleShot(120, self.refresh_side_menu)
        QTimer.singleShot(260, lambda: self._refresh_active_page(40))

    def _apply_database_context(self, db, archive_mode):
        self.db = db; self.is_archive_mode = archive_mode
        from src.utils.currency_helper import CurrencyHelper
        CurrencyHelper.register_db(db)
        if hasattr(self, "fiscal_service"): self.fiscal_service.db = db
        if getattr(self, "assistant", None) is not None: self.assistant.db = db
        if hasattr(self, "assistant_sidebar") and self.assistant_sidebar: self.assistant_sidebar.db = db

    def _reload_all_pages(self):
        for w in list(self.pages.values()):
            self.content_area.removeWidget(w); w.deleteLater()
        self.pages.clear()
        while self.content_area.count():
            w = self.content_area.widget(0); self.content_area.removeWidget(w); w.deleteLater()

    def _refresh_active_page(self, target_index=None):
        idx = target_index or getattr(self, "_current_page_index", 40)
        if hasattr(self, "_install_startup_placeholder"): self._install_startup_placeholder()
        QTimer.singleShot(0, lambda: self.on_menu_click(idx))

    def refresh_loaded_page(self, index):
        p = self.pages.get(index)
        if not p: return False
        try:
            if hasattr(p, "request_reload"): p.request_reload(); return True
            if hasattr(p, "refresh_data"): p.refresh_data(); return True
        except Exception as e: logger.warning(f"Loaded page refresh failed for {index}: {e}")
        return False

    def _run_delayed_daily_backup(self):
        try:
            path = self._active_db.run_daily_local_backup_if_due(trigger="startup+3min")
            if path: self.show_notification("Günlük yedek oluşturuldu.", "info")
        except Exception as e: logger.warning(f"Delayed daily backup failed: {e}")
