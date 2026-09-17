# -*- coding: utf-8 -*-

from src.ui.dialogs.add_customer_dialog import AddCustomerDialog
from src.utils.sector_dialogs import scoped_sector_manager


class TechnicalServiceCustomerDialog(AddCustomerDialog):
    """Public customer add/edit dialog for the technical service sector."""
    SECTOR_ID = "teknik_servis"

    def __init__(self, db, parent=None, customer_data=None, sector_manager=None):
        super().__init__(
            db,
            parent,
            customer_data=customer_data,
            sector_manager=scoped_sector_manager(
                "teknik_servis", db=db, sector_manager=sector_manager
            ),
        )
