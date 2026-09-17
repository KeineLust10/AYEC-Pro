# -*- coding: utf-8 -*-

from src.ui.dialogs.technician_panel import AutomotiveTechnicianPanel as _AutomotiveTechnicianPanel
from src.utils.sector_dialogs import scoped_sector_manager


class AutomotiveTechnicianPanel(_AutomotiveTechnicianPanel):
    """Public technician panel entrypoint for the automotive sector."""

    def __init__(self, db, device_data, parent=None, sector_manager=None, read_only=False):
        super().__init__(
            db,
            device_data,
            parent,
            sector_manager=scoped_sector_manager(
                "otomotiv", db=db, sector_manager=sector_manager
            ),
            read_only=read_only
        )
