# -*- coding: utf-8 -*-

from src.ui.dialogs.add_device_dialog import AddDeviceDialog


class TechnicalServiceNewServiceDialog(AddDeviceDialog):
    """Compatibility entry point for the compact technical service form."""

    SECTOR_ID = "teknik_servis"

    def __init__(
        self,
        db,
        parent=None,
        customer_name=None,
        device_data=None,
        sector_manager=None,
    ):
        del sector_manager
        super().__init__(
            db,
            parent=parent,
            customer_name=customer_name,
            device_data=device_data,
        )
