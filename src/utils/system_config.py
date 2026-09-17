"""
AYEC Pro dynamic system configuration utilities.
Only two sectors are supported: teknik_servis and otomotiv.
"""

SUPPORTED_SECTORS = ("teknik_servis", "otomotiv")
DEFAULT_SECTOR = "teknik_servis"

SYSTEM_MODES = {
    "teknik_servis": {
        "display_name": "Teknik Servis Modu",
        "icon": "TS",
        "active_modules": ["operations", "finance", "stock", "projects", "crm", "personnel", "asistan"],
        "labels": {
            "module_ops": "Servis Yönetimi",
            "primary_entity": "Cihaz / Ürün",
            "secondary_entity": "Teknisyen Paneli",
            "wizard_step3": "Garanti ve Servis Belgeleri",
        },
        "dashboard_widgets": [
            {"id": "pending_repair", "title": "Bekliyor", "icon": "!", "color": "warning"},
            {"id": "delivered_today", "title": "Bugün Teslim Edilen", "icon": "+", "color": "success"},
            {"id": "service_revenue", "title": "Servis Cirosu", "icon": "$", "color": "accent", "module": "finance"},
            {"id": "critical_parts", "title": "Kritik Yedek Parça", "icon": "#", "color": "danger", "module": "stock"},
        ],
    },
    "otomotiv": {
        "display_name": "Otomotiv Modu",
        "icon": "OT",
        "active_modules": ["operations", "crm", "stock", "finance", "personnel", "asistan"],
        "labels": {
            "module_ops": "Servis ve Araç Yönetimi",
            "primary_entity": "Araç / Plaka",
            "secondary_entity": "Bakım Kartı",
            "wizard_step3": "Bakım ve Araç Evrakları",
        },
        "dashboard_widgets": [
            {"id": "pending_repair", "title": "Açık İş Emirleri", "icon": "A", "color": "warning"},
            {"id": "delivered_today", "title": "Bugün Teslim Edilen Araçlar", "icon": "+", "color": "success"},
            {"id": "inspection_due", "title": "Yaklaşan Muayene", "icon": "M", "color": "accent"},
            {"id": "approval_pending", "title": "Müşteri Onayı Bekleyen", "icon": "O", "color": "warning"},
            {"id": "service_revenue", "title": "Servis Geliri", "icon": "$", "color": "accent", "module": "finance"},
            {"id": "critical_parts", "title": "Kritik Yedek Parça", "icon": "#", "color": "danger", "module": "stock"},
        ],
    },
}


class SystemConfig:
    @staticmethod
    def normalize_sector(sector):
        clean = str(sector or "").strip().lower()
        if clean not in SUPPORTED_SECTORS:
            return DEFAULT_SECTOR
        return clean

    @staticmethod
    def get_available_sectors():
        return {key: SYSTEM_MODES[key] for key in SUPPORTED_SECTORS}

    @staticmethod
    def get_default_active_modules(sector):
        normalized = SystemConfig.normalize_sector(sector)
        return list(SYSTEM_MODES.get(normalized, SYSTEM_MODES[DEFAULT_SECTOR]).get("active_modules", []))

    @staticmethod
    def is_module_active(db, module_key):
        sector = SystemConfig.get_current_sector(db)
        default_modules = set(SystemConfig.get_default_active_modules(sector))
        setting = db.get_internal_setting(
            f"module_{module_key}_active",
            "1" if module_key in default_modules else "0",
        )
        return setting == "1"

    @staticmethod
    def is_feature_active(db, feature_key):
        setting = db.get_internal_setting(f"feature_{feature_key}_active", "1")
        return setting == "1"

    @staticmethod
    def get_current_sector(db):
        try:
            sector = db.get_internal_setting("current_sector", "")
            if sector:
                normalized = SystemConfig.normalize_sector(sector)
                if normalized != sector:
                    db.set_internal_setting("current_sector", normalized)
                return normalized
        except Exception:
            pass

        try:
            row = db.cursor.execute(
                "SELECT value FROM settings WHERE key='current_sector'"
            ).fetchone()
            if row:
                try:
                    raw = row["value"]
                except Exception:
                    raw = row[0]
                normalized = SystemConfig.normalize_sector(raw)
                try:
                    db.set_internal_setting("current_sector", normalized)
                except Exception:
                    pass
                return normalized
        except Exception:
            pass

        return DEFAULT_SECTOR
