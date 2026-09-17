# -*- coding: utf-8 -*-

"""
Database Mixins Package
Database metodlarını kategorilere ayıran mixin sınıfları
"""

from .settings_mixin import SettingsMixin
from .bank_mixin import BankMixin
from .reminders_mixin import RemindersMixin
from .support_mixin import SupportMixin
from .personnel_mixin import PersonnelMixin
from .appointments_mixin import AppointmentsMixin
from .services_mixin import ServicesMixin
from .customer_mixin import CustomerMixin
from .accounting_mixin import AccountingMixin
from .device_mixin import DeviceMixin
from .stock_mixin import StockMixin
from .stock_location_mixin import StockLocationMixin
from .logging_mixin import LoggingMixin
from .security_mixin import SecurityMixin
from .schema_mixin import SchemaMixin
from .reports_mixin import ReportsMixin
from .finance_mixin import FinanceMixin
from .project_mixin import ProjectMixin
from .label_mixin import LabelMixin
from .notification_mixin import NotificationMixin
from .product_bank_mapping_mixin import ProductBankMappingMixin
from .maintenance_mixin import MaintenanceMixin

__all__ = [
    'SettingsMixin', 'BankMixin', 'RemindersMixin', 'SupportMixin',
    'PersonnelMixin', 'AppointmentsMixin', 'ServicesMixin',
    'CustomerMixin', 'AccountingMixin', 'DeviceMixin', 'StockMixin', 'StockLocationMixin',
    'LoggingMixin', 'SecurityMixin', 'SchemaMixin', 'ReportsMixin',
    'FinanceMixin', 'ProjectMixin', 'LabelMixin', 'NotificationMixin',
    'ProductBankMappingMixin', 'MaintenanceMixin',
]
