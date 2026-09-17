# -*- coding: utf-8 -*-

import logging
from PyQt6.QtCore import QObject, QMetaObject, Qt, Q_ARG, QTimer, pyqtSlot

logger = logging.getLogger(__name__)

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

    def start_license_check(self):
        """Lisans kontrolünü arka planda başlatır"""
        if not self.enforcement_timer.isActive():
            self.enforcement_timer.start()
        if not self.license_manager:
            logger.error("License manager is unavailable.")
            return
        try:
            online_ok, online_message, _payload = self.license_manager.refresh_server_entitlement()
            status = self.license_manager.check_license_status()
            if not online_ok:
                logger.info("Server license refresh skipped or unavailable: %s", online_message)
            ok = status.get("status") == "active"
            message = str(status.get("message") or "License access is unavailable.")
            self.on_license_check_result(ok, message)
        except Exception as exc:
            logger.exception("License check failed: %s", exc)
            self.on_license_check_result(False, "License verification failed.")

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
