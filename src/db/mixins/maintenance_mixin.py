# -*- coding: utf-8 -*-
from src.db.mixins._maint_schema_mixin import MaintenanceSchemaMixin
from src.db.mixins._maint_core_mixin import MaintenanceCoreMixin
from src.db.mixins._maint_forms_mixin import MaintenanceFormsMixin
from src.db.mixins._maint_quotes_mixin import MaintenanceQuotesMixin
from src.db.mixins._maint_notify_mixin import MaintenanceNotifyMixin
from src.db.mixins._maint_special_mixin import MaintenanceSpecialMixin
from src.db.mixins._maint_history_mixin import MaintenanceHistoryMixin

class MaintenanceMixin(
    MaintenanceSchemaMixin,
    MaintenanceCoreMixin,
    MaintenanceFormsMixin,
    MaintenanceQuotesMixin,
    MaintenanceNotifyMixin,
    MaintenanceSpecialMixin,
    MaintenanceHistoryMixin
):
    """
    Automotive vehicle registry, maintenance cards and reminder support.
    Modularized into specialized sub-mixins (<= 800 lines rule).
    """
    pass
