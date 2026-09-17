# -*- coding: utf-8 -*-
# _tp_helpers.py

from PyQt6.QtWidgets import QApplication, QWidget, QComboBox, QLabel
from PyQt6.QtCore import Qt, QSettings
from src.utils.appearance_mode import AppearanceModeManager
from src.utils.system_config import SystemConfig
from src.utils.logger import logger
from src.utils.currency_helper import CurrencyHelper
from src.utils.automotive_defaults import (
    approval_db_to_label, approval_label_to_db,
    AUTOMOTIVE_CHECKLIST_CATEGORY, AUTOMOTIVE_PRESET,
    ensure_automotive_fast_notes,
)
from src.utils.technical_service_profiles import (
    DEFAULT_TECHNICAL_SERVICE_PROFILE, TECHNICAL_SERVICE_PROFILE_ORDER,
    build_profile_category, get_profile_labels,
    normalize_technical_service_profile
)

class _TpHelpers:
    def _is_classic_appearance(self):
        app = QApplication.instance()
        if app and app.property("appearanceMode") == AppearanceModeManager.CLASSIC:
            return True
        # Guard: self.db may not be set yet if called during super().__init__()
        db = getattr(self, "db", None)
        if db is None:
            return False
        return AppearanceModeManager.current(db) == AppearanceModeManager.CLASSIC


    def _is_automotive(self):
        """Otomotiv sektöründe olup olmadığını kontrol et"""
        try:
            if hasattr(self, "sector_manager") and self.sector_manager:
                if hasattr(self.sector_manager, "get_current_plugin"):
                    return self.sector_manager.get_current_plugin().sector_id == "otomotiv"
                if hasattr(self.sector_manager, "get_current_sector"):
                    sector = self.sector_manager.get_current_sector()
                    return getattr(sector, "value", sector) == "otomotiv"
            return SystemConfig.get_current_sector(self.db) == "otomotiv"
        except Exception:
            return False

    def _get_quick_categories(self):
        """🆕 Hızlı kategorileri plugin'den veya varsayılanlardan al"""
        if not self._is_automotive():
            return [], {}
        if self.sector_manager:
            try:
                quick_data = self.sector_manager.get_quick_categories()
                return quick_data.get("categories", []), quick_data.get("presets", {})
            except Exception:
                pass
        if self._is_automotive():
            return list(AUTOMOTIVE_PRESET.keys()), AUTOMOTIVE_PRESET
        return [], {}

    def get_technical_service_profile(self):
        return normalize_technical_service_profile(
            getattr(self, "technical_service_profile", DEFAULT_TECHNICAL_SERVICE_PROFILE)
        )

    def _resolve_fast_note_category(self, base_category):
        if self._is_automotive():
            return base_category
        return build_profile_category(self.get_technical_service_profile(), base_category)

    def _get_fast_notes_for_category(self, base_category):
        if self._is_automotive():
            ensure_automotive_fast_notes(self.db)
        categories = [self._resolve_fast_note_category(base_category)]
        if not self._is_automotive():
            categories.append(base_category)
        for category_name in categories:
            notes = self.db.get_fast_notes(category_name) or []
            if notes:
                return notes, category_name
        return [], categories[0]

    def _ensure_technical_service_profile_seed(self, profile_name=None):
        if self._is_automotive():
            return
        profile = normalize_technical_service_profile(
            profile_name or self.get_technical_service_profile()
        )
        db_key = (
            getattr(self.db, "db_path", None)
            or getattr(self.db, "database_path", None)
            or id(self.db)
        )
        cache_key = (str(db_key), profile)
        if cache_key in type(self)._profile_seed_cache:
            return
        for base_category in (
            "Arıza Hızlı Seçimi", "İşlem Detayı", "Gizli Not", "Aksesuar", "Cihaz Testi",
        ):
            scoped_category = build_profile_category(profile, base_category)
            if self.db.get_fast_notes(scoped_category):
                continue
            for idx, label in enumerate(get_profile_labels(profile, base_category)):
                self.db.add_fast_note(scoped_category, label, 1, idx)
        type(self)._profile_seed_cache.add(cache_key)

    def _sync_profile_selectors(self, profile_name):
        for combo_name in ("cmb_technical_profile_main", "cmb_technical_profile_test"):
            combo = getattr(self, combo_name, None)
            if combo is None or combo.currentText() == profile_name:
                continue
            combo.blockSignals(True)
            combo.setCurrentText(profile_name)
            combo.blockSignals(False)

    def _apply_technical_service_profile(self, profile_name, persist=True):
        if self._is_automotive():
            return

        normalized = normalize_technical_service_profile(profile_name)
        self.technical_service_profile = normalized
        self.device_dict["device_type"] = normalized
        self._ensure_technical_service_profile_seed(normalized)

        if persist:
            try:
                self.db.cursor.execute(
                    "UPDATE devices SET device_type=? WHERE tracking_no=?",
                    (normalized, self.tracking_no),
                )
                self.db.conn.commit()
            except Exception as exc:
                logger.warning("Technician profile persist failed: %s", exc)

        self._sync_profile_selectors(normalized)
        if hasattr(self, "wizard_page1"):
            self.wizard_page1.reload_accessories()
        if hasattr(self, "wizard_page2"):
            self.wizard_page2.reload_toggles()
        if hasattr(self, "lbl_test_profile_hint"):
            self.lbl_test_profile_hint.setText(f"Aktif profil: {normalized}")
        if hasattr(self, "test_header"):
            self.test_header.setText(f"{normalized} Test Formu")
        if hasattr(self, "general_profile_badge"):
            self.general_profile_badge.setText(normalized)
        self.reload_test_toggles()

    def _on_technical_service_profile_changed(self, profile_name):
        self._apply_technical_service_profile(profile_name, persist=False)

    def _get_checklist_category(self):
        """Kontrol listesi kategorisini panel tipine gore al."""
        if not self._is_automotive():
            return self._resolve_fast_note_category("Cihaz Testi")
        if self.sector_manager:
            try:
                categories, _ = self._get_quick_categories()
                for cat in categories:
                    if "kontrol" in cat.lower() or "checklist" in cat.lower():
                        return cat
            except Exception:
                pass
        return AUTOMOTIVE_CHECKLIST_CATEGORY

    def _approval_label_to_db(self, value):
        if self.sector_manager:
            try:
                plugin = self.sector_manager.get_current_plugin()
                if hasattr(plugin, "approval_label_to_db"):
                    return plugin.approval_label_to_db(value)
            except Exception:
                pass
        return approval_label_to_db(value)

    def _approval_db_to_label(self, value):
        if self.sector_manager:
            try:
                plugin = self.sector_manager.get_current_plugin()
                if hasattr(plugin, "approval_db_to_label"):
                    return plugin.approval_db_to_label(value)
            except Exception:
                pass
        return approval_db_to_label(value)

    def _fmt_try(self, amount, include_try_reference=False):
        return CurrencyHelper.format_try_for_display(
            amount, db=self.db, include_try_reference=include_try_reference,
        )

    def _device_data_to_dict(self, device_data):
        if isinstance(device_data, dict):
            return dict(device_data)
        try:
            if hasattr(device_data, "keys"):
                return {key: device_data[key] for key in device_data.keys()}
        except Exception:
            return None
        return None

    def _toggle_cache_key(self):
        return f"technician_panel.checklist_status.{self.tracking_no}"

    def _load_cached_checklist_status(self):
        key = self._toggle_cache_key()
        cache_owner = type(self)
        if key in cache_owner._session_toggle_cache:
            return cache_owner._session_toggle_cache.get(key, "")
        settings = QSettings("AYEC", "AYECPro")
        value = settings.value(key, "")
        return str(value) if value is not None else ""

    def _save_cached_checklist_status(self, value):
        key = self._toggle_cache_key()
        type(self)._session_toggle_cache[key] = value or ""
        settings = QSettings("AYEC", "AYECPro")
        settings.setValue(key, value or "")

    def get_cached_checklist_status(self):
        return self._load_cached_checklist_status()

    def _normalize_checklist_items(self, items):
        seen = set()
        normalized = []
        for item in items:
            text = str(item).strip()
            if not text:
                continue
            key = text.upper()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(text)
        return normalized

    def _persist_toggle_state(self, checklist_status, accessories=None):
        value = checklist_status or ""
        self.checklist_status = value
        self.device_dict["checklist_status"] = value
        self._save_cached_checklist_status(value)
        try:
            if accessories is None:
                self.db.cursor.execute(
                    "UPDATE devices SET checklist_status=? WHERE tracking_no=?",
                    (value, self.tracking_no),
                )
            else:
                self.db.cursor.execute(
                    "UPDATE devices SET checklist_status=?, accessories=? WHERE tracking_no=?",
                    (value, accessories, self.tracking_no),
                )
            self.db.conn.commit()
        except Exception:
            pass

    def _clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                widget = child.widget()
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
            elif child.layout():
                self._clear_layout(child.layout())
