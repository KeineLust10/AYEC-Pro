# -*- coding: utf-8 -*-

from PyQt6 import sip
from PyQt6.QtCore import QObject, pyqtSignal
from src.utils.sector_presets import PRESETS
from src.utils.logger import logger

# Global instance storage
_LANGUAGE_MANAGER_INSTANCE = None

class LanguageManagerImpl(QObject):
    """
    Internal implementation of Language Manager.
    Do not instantiate directly. Use LanguageManager() factory instead.
    """
    labels_updated = pyqtSignal() # Sinyal: Etiketler değiştiğinde UI'ı uyarır

    def __init__(self, db=None):
        super().__init__()
        self.db = db
        self.labels = {}
        
        if self.db:
            self.reload_labels()

    def set_db(self, db):
        self.db = db
        self.reload_labels()

    def reload_labels(self):
        if self.db:
            try:
                self.labels = self.db.get_all_labels()
                self.labels_updated.emit()
            except Exception as e:
                logger.error("LanguageManager reload error: %s", e)

    def get(self, key, default_value=""):
        """
        Etiketi getirir. Eğer veritabanında yoksa, default_value döner 
        VE (opsiyonel) veritabanına bu yeni key'i kaydeder (Lazy Registration).
        """
        if key in self.labels:
            val = self.labels[key]
            return val if val else default_value
        
        # Key yoksa, veritabanına ekleyelim ki editörde görünsün (Auto-Discovery)
        if self.db and default_value:
            try:
                # Check if cache missed but DB has it (edge case) or insert new
                self.db.register_label(key, default_value, "Auto-Discovered")
                self.labels[key] = default_value # Cache'e ekle
            except Exception as e:
                logger.warning("Label register failed for key '%s': %s", key, e)
            
        return default_value

    def update_label(self, key, new_value):
        if self.db:
            if self.db.update_label(key, new_value):
                self.reload_labels() # Cache'i tazele ve sinyal yay
                return True
        return False

    def apply_preset(self, preset_name):
        """Seçilen sektör ayarlarını (preset) uygular (DB Üzerinden)"""
        if not self.db:
            return False

        try:
            # DB'den preset verisini çek
            preset_data = self.db.get_preset_data(preset_name) # list of (key, value)
            
            if not preset_data:
                # Fallback to local file if DB empty (Safety net)
                if preset_name in PRESETS:
                    data = PRESETS[preset_name]
                    preset_data = list(data.items())
                else:
                    return False

            # Batch update
            for key, value in preset_data:
                # Ensure key exists in app_labels first (Auto-register if missing from standard usage)
                self.db.register_label(key, value, f"Preset: {preset_name}")
                # Update current value
                self.db.update_label(key, value)
            
            self.reload_labels()
            return True
        except Exception as e:
            logger.error("Preset apply failed for '%s': %s", preset_name, e)
            return False

def LanguageManager(db=None):
    """
    Factory function acting as a Singleton Accessor.
    Returns the shared LanguageManagerImpl instance.
    """
    global _LANGUAGE_MANAGER_INSTANCE
    instance_deleted = False
    if _LANGUAGE_MANAGER_INSTANCE is not None:
        try:
            instance_deleted = sip.isdeleted(_LANGUAGE_MANAGER_INSTANCE)
        except Exception:
            instance_deleted = True

    if _LANGUAGE_MANAGER_INSTANCE is None or instance_deleted:
        _LANGUAGE_MANAGER_INSTANCE = LanguageManagerImpl(db)
    elif db is not None:
        # Update DB if provided in subsequent calls (optional feature)
        _LANGUAGE_MANAGER_INSTANCE.set_db(db)
    
    return _LANGUAGE_MANAGER_INSTANCE
