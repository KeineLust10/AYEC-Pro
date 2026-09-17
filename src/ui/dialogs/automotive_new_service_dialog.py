# -*- coding: utf-8 -*-

from src.ui.dialogs.new_service_dialog import NewServiceDialog
from src.utils.sector_dialogs import scoped_sector_manager


class AutomotiveNewServiceDialog(NewServiceDialog):
    """Public service form dialog for the automotive sector."""
    SECTOR_ID = "otomotiv"

    def __init__(self, db, parent=None, customer_name=None, device_data=None, sector_manager=None):
        super().__init__(
            db,
            parent,
            customer_name=customer_name,
            device_data=device_data,
            sector_manager=scoped_sector_manager(
                "otomotiv", db=db, sector_manager=sector_manager
            ),
        )
