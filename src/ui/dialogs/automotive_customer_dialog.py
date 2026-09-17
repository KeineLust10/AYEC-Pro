# -*- coding: utf-8 -*-

from src.ui.dialogs.add_customer_dialog import AddCustomerDialog
from src.utils.sector_dialogs import scoped_sector_manager


class AutomotiveCustomerDialog(AddCustomerDialog):
    """Public customer add/edit dialog for the automotive sector."""
    SECTOR_ID = "otomotiv"

    def __init__(self, db, parent=None, customer_data=None, sector_manager=None):
        super().__init__(
            db,
            parent,
            customer_data=customer_data,
            sector_manager=scoped_sector_manager(
                "otomotiv", db=db, sector_manager=sector_manager
            ),
        )
