# -*- coding: utf-8 -*-

import logging
from PyQt6.QtCore import QThread, QObject, QMetaObject, Qt, Q_ARG, QTimer, pyqtSignal, pyqtSlot

logger = logging.getLogger(__name__)


class LocalLicenseCheckWorker(QThread):
    completed = pyqtSignal(object, object, str)

    def __init__(self, license_manager, parent=None):
        super().__init__(parent)
        self.license_manager = license_manager

    def run(self):
        status = None
        identity = None
        errors = []
        try:
            status = self.license_manager.check_license_status()
        except Exception as exc:
            errors.append(f"Local license check failed: {exc}")
        try:
            identity = self.license_manager._license_device_identity()
        except Exception as exc:
            errors.append(f"License device identity unavailable: {exc}")
        self.completed.emit(status, identity, "; ".join(errors))


class LicenseEntitlementWorker(QThread):
    completed = pyqtSignal(bool, object, str)

    def __init__(self, device_identity=None, identifier="", password="", tenant_id="", parent=None):
        super().__init__(parent)
        self.device_identity = dict(device_identity or {})
        self.identifier = str(identifier or "")
        self.password = str(password or "")
        self.tenant_id = str(tenant_id or "")

    def run(self):
        try:
            from src.utils.license_api_client import LicenseApiClient

            client = LicenseApiClient(timeout=5)
            if self.identifier and self.password:
                payload = client.status_for_credentials(
                    self.identifier, self.password, self.tenant_id
                )
            else:
                payload = client.status_for_device(self.device_identity)
            self.completed.emit(True, payload or {}, "")
        except Exception as exc:
            self.completed.emit(False, {}, str(exc))


class LicenseService(QObject):
    """
    Uygulamanın lisans doğrulama ve sistem kilitleme işlemlerini yönetir.
    """
    
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self.db = main_window.db
        self.license_manager = getattr(main_window, 'license_manager', None)
        self.enforcement_timer = QTimer(self)
        self.enforcement_timer.setInterval(60 * 1000)
        self.enforcement_timer.timeout.connect(self._enforce_local_expiry)
        self._license_check_worker = None
        self._license_check_callback = None
        self._local_license_worker = None
        self._pending_entitlement_result = None

    def start_license_check(self):
        """Check local license state now and refresh server entitlement asynchronously."""
        if not self.enforcement_timer.isActive():
            self.enforcement_timer.start()
        manager = self.license_manager
        if not manager:
            logger.error("License manager is unavailable.")
            return
        worker = self._license_check_worker
        local_worker = self._local_license_worker
        if (worker is not None and worker.isRunning()) or (
            local_worker is not None and local_worker.isRunning()
        ):
            return
        local_worker = LocalLicenseCheckWorker(manager, parent=self)
        self._local_license_worker = local_worker
        local_worker.completed.connect(self._complete_startup_local_check)
        local_worker.finished.connect(local_worker.deleteLater)
        local_worker.start()

    @pyqtSlot(object, object, str)
    def _complete_startup_local_check(self, status, identity, error):
        self._local_license_worker = None
        if error:
            logger.warning("Startup local license check incomplete: %s", error)
        if status is not None:
            ok = status.get("status") == "active"
            message = str(status.get("message") or "License access is unavailable.")
            self.on_license_check_result(ok, message)
        if identity is not None:
            try:
                self._start_entitlement_worker(identity=identity)
            except Exception as exc:
                logger.exception("Could not start server license refresh: %s", exc)

    def _start_post_refresh_local_check(self, result_ok, result_message, payload):
        worker = LocalLicenseCheckWorker(self.license_manager, parent=self)
        self._pending_entitlement_result = (
            bool(result_ok),
            str(result_message or "License access is unavailable."),
            dict(payload or {}),
        )
        self._local_license_worker = worker
        worker.completed.connect(self._complete_post_refresh_local_check)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    @pyqtSlot(object, object, str)
    def _complete_post_refresh_local_check(self, status, _identity, error):
        self._local_license_worker = None
        if error:
            logger.warning("Post-refresh local license check incomplete: %s", error)
        if status is not None:
            ok = status.get("status") == "active"
            message = str(status.get("message") or "License access is unavailable.")
            self.on_license_check_result(ok, message)
        result = self._pending_entitlement_result
        self._pending_entitlement_result = None
        callback = self._license_check_callback
        self._license_check_callback = None
        if callback and result:
            callback(*result)

    def refresh_server_entitlement_async(
        self, identifier="", password="", tenant_id="", on_complete=None
    ):
        """Refresh server state without blocking the UI or sharing network work."""
        manager = self.license_manager
        if manager is None:
            if on_complete:
                on_complete(False, "License manager is unavailable.", {})
            return False
        if (
            self._license_check_worker is not None
            and self._license_check_worker.isRunning()
        ) or (
            self._local_license_worker is not None
            and self._local_license_worker.isRunning()
        ):
            if on_complete:
                on_complete(False, "License refresh is already running.", {})
            return False
        try:
            identity = (
                {}
                if identifier and password
                else manager._license_device_identity()
            )
            return self._start_entitlement_worker(
                identity=identity,
                identifier=identifier,
                password=password,
                tenant_id=tenant_id,
                on_complete=on_complete,
            )
        except Exception as exc:
            logger.exception("Could not start server license refresh: %s", exc)
            if on_complete:
                on_complete(False, str(exc), {})
            return False

    def _start_entitlement_worker(
        self, identity=None, identifier="", password="", tenant_id="", on_complete=None
    ):
        worker = LicenseEntitlementWorker(
            identity,
            identifier=identifier,
            password=password,
            tenant_id=tenant_id,
            parent=self,
        )
        self._license_check_worker = worker
        self._license_check_callback = on_complete
        worker.completed.connect(self._complete_license_check)
        worker.finished.connect(worker.deleteLater)
        worker.start()
        return True

    def shutdown(self):
        workers = (self._local_license_worker, self._license_check_worker)
        for worker in workers:
            if worker is None:
                continue
            try:
                if worker.isRunning() and not worker.wait(6000):
                    logger.warning("License check did not stop before shutdown timeout.")
                    return False
            except RuntimeError:
                logger.debug("License worker was already released during shutdown.")
        self._local_license_worker = None
        self._license_check_worker = None
        self._license_check_callback = None
        return True

    @pyqtSlot(bool, object, str)
    def _complete_license_check(self, online_ok, payload, error):
        manager = self.license_manager
        if manager is None:
            return
        result_ok = False
        result_message = str(error or "License access is unavailable.")
        if not online_ok:
            logger.info("Server license refresh skipped or unavailable: %s", error)
        else:
            try:
                result_ok, result_message = manager.apply_server_entitlement(
                    dict(payload or {})
                )
            except Exception as exc:
                logger.exception("Server entitlement could not be applied: %s", exc)
        self._license_check_worker = None
        self._start_post_refresh_local_check(result_ok, result_message, payload)

    def _enforce_local_expiry(self):
        if not self.license_manager:
            return
        try:
            status = self.license_manager.check_license_status()
        except Exception as error:
            logger.warning("Periodic license check failed: %s", error)
            return
        if str(status.get("status") or "") != "expired":
            return
        self.on_license_check_result(
            False,
            (
                "Lisans eri\u015fiminizin s\u00fcresi sona ermi\u015ftir. "
                "AYEC Pro \u00fczerindeki i\u015flemler ge\u00e7ici olarak "
                "durdurulmu\u015ftur. Kullan\u0131ma devam etmek i\u00e7in "
                "lisans talebinizi y\u00f6netime iletin."
            ),
        )

    def _license_check_callback(self, ok, msg):
        """Thread-safe callback for license results"""
        try:
            QMetaObject.invokeMethod(
                self,
                "_handle_license_check_result",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(bool, ok),
                Q_ARG(str, msg)
            )
        except Exception:
            self.on_license_check_result(ok, msg)

    @pyqtSlot(bool, str)
    def _handle_license_check_result(self, ok, msg):
        self.on_license_check_result(ok, msg)

    def on_license_check_result(self, ok, msg):
        """Lisans kontrol sonucu (Arka plandan gelir)"""
        if not ok:
            logger.error(f"SYSTEM LOCKED: {msg}")
            
            # Asistan sesli uyarı ver
            if hasattr(self.main_window, "assistant_service"):
                self.main_window.assistant_service._speak_async(
                    "Sistem kullanım süresi sona ermiştir. Lisans doğrulaması yapılana kadar tüm işlemler durdurulmuştur."
                )
            
            # Kilit Ekranını Göster
            try:
                from src.ui.dialogs.license_lock_screen import LicenseRequestDialog
                existing = getattr(self.main_window, "lock_screen", None)
                if existing is not None and existing.isVisible():
                    return
                hwid = self.license_manager.get_hwid()
                self.main_window.lock_screen = LicenseRequestDialog(
                    hwid=hwid,
                    parent=self.main_window,
                    locked=True,
                    warning_message=(
                        "Lisans eri\u015fiminizin s\u00fcresi sona ermi\u015ftir. "
                        "G\u00fcvenli ve kesintisiz kullan\u0131ma devam etmek "
                        "i\u00e7in a\u015fa\u011f\u0131daki paketlerden birini "
                        "se\u00e7erek lisans talebinizi iletin. Talebiniz "
                        "y\u00f6netim ekibimiz taraf\u0131ndan incelenecektir."
                    ),
                    product_code="teknik_servis",
                )
                
                # Full Lock Screen (modal & always on top)
                self.main_window.lock_screen.setModal(True)
                self.main_window.lock_screen.show()
                self.main_window.lock_screen.raise_()
                self.main_window.lock_screen.activateWindow()
            except Exception as e:
                logger.critical(f"Failed to show lock screen: {e}")
        else:
            logger.info("License verified successfully.")
