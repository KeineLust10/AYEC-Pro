# -*- coding: utf-8 -*-

from src.ui.dialogs.technician_panel import (
    TechnicalServiceTechnicianPanel as _TechnicalServiceTechnicianPanel,
)
from src.utils.sector_dialogs import scoped_sector_manager


class TechnicalServiceTechnicianPanel(_TechnicalServiceTechnicianPanel):
    """Public technician panel entrypoint for the technical service sector."""

    def __init__(self, db, device_data, parent=None, sector_manager=None, read_only=False):
        super().__init__(
            db,
            device_data,
            parent,
            sector_manager=scoped_sector_manager(
                "teknik_servis", db=db, sector_manager=sector_manager
            ),
            read_only=read_only
        )
