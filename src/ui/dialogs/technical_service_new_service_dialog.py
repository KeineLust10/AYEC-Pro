# -*- coding: utf-8 -*-

from src.ui.dialogs.new_service_dialog import NewServiceDialog


class TechnicalServiceNewServiceDialog(NewServiceDialog):
    """Compatibility entry point for the reference technical service form."""

    SECTOR_ID = "teknik_servis"

    def __init__(
        self,
        db,
        parent=None,
        customer_name=None,
        device_data=None,
        sector_manager=None,
    ):
        super().__init__(
            db,
            parent=parent,
            customer_name=customer_name,
            device_data=device_data,
            sector_manager=sector_manager,
        )
