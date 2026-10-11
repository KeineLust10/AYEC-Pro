"""Lazy exports for settings widgets."""

from importlib import import_module


_EXPORTS = {
    "CompanySettingsWidget": "company_settings",
    "SMSSettingsWidget": "sms_settings",
    "SMSTemplatesWidget": "sms_settings",
    "TemplateEditDialog": "sms_settings",
    "BackgroundSettingsWidget": "background_settings",
    "LicenseManagementWidget": "license_settings",
    "SMTPSettingsWidget": "smtp_settings",
    "BackupSettingsWidget": "backup_settings",
    "BankSettingsWidget": "bank_settings",
    "CargoSettingsWidget": "cargo_settings",
    "StockSettingsWidget": "stock_settings",
    "LanguageSettingsWidget": "language_settings",
}

__all__ = tuple(_EXPORTS)


def __getattr__(name):
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(name)
    value = getattr(
        import_module(f"{__name__}.{module_name}"),
        name,
    )
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__))
