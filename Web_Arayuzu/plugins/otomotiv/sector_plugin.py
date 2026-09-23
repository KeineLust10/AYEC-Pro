"""Minimal web adapter for the automotive sector plugin."""


class OtomotivPlugin:
    """Compatibility adapter used by optional web plugin discovery."""

    sector_id = "otomotiv"

    def get_service_form_fields(self):
        return [
            {"name": "plate", "label": "Plate", "required": True},
            {"name": "vin", "label": "VIN", "required": False},
            {"name": "odometer", "label": "Odometer", "required": False},
        ]

    def get_quick_categories(self):
        return []

    def is_feature_available(self, feature):
        return str(feature or "").strip().lower() in {
            "vehicle_management",
            "plates",
            "chassis",
            "maintenance",
        }
