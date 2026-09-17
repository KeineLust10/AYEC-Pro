# -*- coding: utf-8 -*-

"""
Settings Widgets Package
Ayarlar sayfası widget'larının modüler yapısı
"""

# Aktif widget'lar (taşınmış ve implement edilmiş)
from .company_settings import CompanySettingsWidget
from .sms_settings import SMSSettingsWidget, SMSTemplatesWidget, TemplateEditDialog
from .background_settings import BackgroundSettingsWidget
from .license_settings import LicenseManagementWidget
from .smtp_settings import SMTPSettingsWidget
from .backup_settings import BackupSettingsWidget

# Placeholder widget'lar (basit placeholder implementation)
from .bank_settings import BankSettingsWidget
from .cargo_settings import CargoSettingsWidget
from .stock_settings import StockSettingsWidget
from .language_settings import LanguageSettingsWidget

__all__ = [
    # Tam implement edilmiş widget'lar
    'CompanySettingsWidget',
    'SMSSettingsWidget',
    'SMSTemplatesWidget',
    'TemplateEditDialog',
    'BackgroundSettingsWidget',
    'LicenseManagementWidget',
    'SMTPSettingsWidget',
    'BackupSettingsWidget',
    
    # Placeholder widget'lar
    'BankSettingsWidget',
    'CargoSettingsWidget',
    'StockSettingsWidget',
    'LanguageSettingsWidget',
]
