# -*- coding: utf-8 -*-

import logging
from ._db_legacy_schema_mixin import DBLegacySchemaMixin
from ._db_legacy_maintenance_mixin import DBLegacyMaintenanceMixin
from ._db_legacy_crm_mixin import DBLegacyCRMMixin
from ._db_legacy_support_mixin import DBLegacySupportMixin

logger = logging.getLogger(__name__)

class DatabaseLegacyPart1Mixin(DBLegacySchemaMixin, DBLegacyMaintenanceMixin, DBLegacyCRMMixin, DBLegacySupportMixin):
    """
    AYEC Pro Legacy Database Mixin (Mod\u00fcler Versiyon).
    Schema, Bak\u0131m, CRM ve Destek fonksiyonlar\u0131n\u0131 orkestre eder.
    """
    pass
